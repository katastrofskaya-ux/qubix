#!/usr/bin/env python3
"""Что ушло клиентам с рабочей почты — и где про это отметиться.

Читает папку «Отправленные» ящика на mail.qubix.pro, сопоставляет адресатов
с клиентами из админки и карточками лидов в YouTrack, показывает по каждому
письму готовую строку отметки. Только чтение: ничего не отправляет и ничего
не пишет в трекер — строку отметки ставит Анастасия после просмотра.

    scripts/mail.py                # письма за последние 7 дней
    scripts/mail.py --days 30      # за месяц
    scripts/mail.py --new          # только то, что не показывали раньше
    scripts/mail.py --all          # включая адресатов вне клиентской базы

Нужны переменные окружения:
    QUBIX_MAIL_PASSWORD  — пароль ящика (в репозитории его нет)
    ADMIN_QUBIX_COOKIE   — кука админки, для списка клиентов
    YOUTRACK_API_TOKEN   — для поиска карточки лида по почте

⚠️ Правило записи в трекер (Анастасия, 14.09.2026) действует и здесь: даже
при просьбе «отметь» — сначала показать точный текст, отправлять после «да».
"""
import argparse
import datetime
import email
import email.utils
import imaplib
import json
import os
import re
import ssl
import sys
from email.header import decode_header, make_header

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import touch  # список клиентов из админки и поиск карточки в SALES

HOST = os.environ.get("QUBIX_MAIL_HOST", "mail.qubix.pro")
USER = os.environ.get("QUBIX_MAIL_USER", "anastasiavoitenko@qubix.pro")
STATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "mail-state.json")

# Имя папки отправленных зависит от сервера — пробуем по очереди.
SENT_CANDIDATES = ["Sent", "INBOX.Sent", "Отправленные", "Sent Items", "Sent Messages"]


def connect():
    password = os.environ.get("QUBIX_MAIL_PASSWORD")
    if not password:
        sys.exit("нужна переменная окружения QUBIX_MAIL_PASSWORD — пароль ящика")
    try:
        conn = imaplib.IMAP4_SSL(HOST, 993, ssl_context=ssl.create_default_context(),
                                 timeout=30)
    except OSError as e:
        sys.exit(f"{HOST}:993 не отвечает ({type(e).__name__}). "
                 "Похоже, сервер ещё не пускает подключения — вопрос к Нику.")
    try:
        conn.login(USER, password)
    except imaplib.IMAP4.error as e:
        sys.exit(f"вход отклонён: {e}. Проверь, что в QUBIX_MAIL_PASSWORD "
                 "лежит актуальный пароль ящика.")
    return conn


def pick_sent(conn):
    """Найти папку отправленных: сначала по флагу \\Sent, потом по имени."""
    ok, boxes = conn.list()
    names = []
    if ok == "OK":
        for raw in boxes:
            line = raw.decode(errors="replace") if isinstance(raw, bytes) else raw
            m = re.search(r'"?([^"]+)"?$', line.strip())
            if not m:
                continue
            name = m.group(1)
            names.append(name)
            if "\\Sent" in line:
                return name
    for cand in SENT_CANDIDATES:
        if cand in names:
            return cand
    sys.exit("папка отправленных не нашлась. Что видно на сервере: "
             + ", ".join(names[:20]))


def hdr(value):
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def addresses(msg):
    out = []
    for field in ("To", "Cc"):
        for _, addr in email.utils.getaddresses(msg.get_all(field, [])):
            if addr:
                out.append(addr.lower())
    return out


def load_state():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"seen": []}


def save_state(state):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def main():
    p = argparse.ArgumentParser(description="Письма клиентам из «Отправленных»")
    p.add_argument("--days", type=int, default=7, metavar="N")
    p.add_argument("--new", action="store_true",
                   help="только письма, которых не было в прошлом запуске")
    p.add_argument("--all", action="store_true",
                   help="показывать и адресатов вне клиентской базы")
    a = p.parse_args()

    customers = {(c.get("email") or "").lower(): c for c in touch.load() if c.get("email")}
    print(f"Клиентов в админке: {len(customers)}")

    conn = connect()
    box = pick_sent(conn)
    conn.select(f'"{box}"', readonly=True)
    since = (datetime.datetime.now() - datetime.timedelta(days=a.days)).strftime("%d-%b-%Y")
    ok, data = conn.search(None, f'(SINCE {since})')
    ids = data[0].split() if ok == "OK" and data and data[0] else []
    print(f"Папка «{box}», писем за {a.days} дн.: {len(ids)}\n")

    state = load_state()
    seen = set(state.get("seen", []))
    fresh = []

    for num in ids:
        ok, raw = conn.fetch(num, "(RFC822)")
        if ok != "OK" or not raw or not raw[0]:
            continue
        msg = email.message_from_bytes(raw[0][1])
        key = msg.get("Message-ID") or f"{box}:{num.decode()}"
        if a.new and key in seen:
            continue
        when = email.utils.parsedate_to_datetime(msg.get("Date")) if msg.get("Date") else None
        for addr in addresses(msg):
            client = customers.get(addr)
            if client is None and not a.all:
                continue
            fresh.append((when, addr, hdr(msg.get("Subject")), client, key))

    conn.logout()

    if not fresh:
        print("Писем клиентам за этот период нет.")
        return

    fresh.sort(key=lambda t: t[0] or datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
    today = datetime.datetime.now().strftime("%d.%m.%Y")
    for when, addr, subject, client, _ in fresh:
        stamp = when.astimezone().strftime("%d.%m %H:%M") if when else "дата неизвестна"
        print("─" * 70)
        print(f"{stamp} → {addr}")
        print(f"  Тема:     {subject or '(без темы)'}")
        if client:
            card = touch.sales_card(addr)
            print(f"  Клиент:   #{client['number']} · "
                  f"https://admin.qubix.pro/customers/{client['id']}")
            print("  Карточка: " + (f"https://team.qubix.capital/issue/{card}" if card
                                    else "в SALES не нашлась — завести новую"))
            print("  ---- строка отметки, показать перед отправкой в трекер ----")
            print(f"  Письмо отправлено {stamp} на {addr}. Тема: «{subject}». "
                  f"Ответ ждём до {(datetime.datetime.now() + datetime.timedelta(days=3)):%d.%m}.")
        else:
            print("  Адресат вне клиентской базы")

    state["seen"] = sorted(seen | {k for *_, k in fresh})
    state["last_run"] = today
    save_state(state)
    print("─" * 70)
    print(f"Показано: {len(fresh)}. Отметки в трекер сами не уходят — "
          "скажи «да» на текст, тогда поставлю.")


if __name__ == "__main__":
    main()
