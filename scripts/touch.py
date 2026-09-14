#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Кого касаться сегодня: три сегмента из админки (admin.qubix.pro).

    scripts/touch.py                 — все три сегмента
    scripts/touch.py --stuck         — только застрявшие без лицензии
    scripts/touch.py --expiring 10   — истекают в ближайшие 10 дней
    scripts/touch.py --expired 14    — истекли за последние 14 дней
    scripts/touch.py --csv спис.csv  — выгрузить показанное в файл

Сегменты:
  1. Застряли  — зарегистрировались, лицензию не взяли (установки на сервер нет).
  2. Истекают  — подписка кончается на днях, разговор нужен ДО даты.
  3. Истекли   — подписка кончилась, но человек продукт уже ставил.

Нужна переменная окружения ADMIN_QUBIX_COOKIE (кука сессии админки).
Только чтение. Ничего никому не отправляет — готовит списки.
"""
import argparse, csv, datetime, json, os, subprocess, sys

API = "https://admin.qubix.pro/api/admin/v1"
NOW = datetime.datetime.now(datetime.timezone.utc)


def get(path):
    """GET к админке через curl — тем же способом, что и остальные наши обращения."""
    cookie = os.environ.get("ADMIN_QUBIX_COOKIE")
    if not cookie:
        sys.exit("нужна переменная окружения ADMIN_QUBIX_COOKIE — кука сессии админки")
    r = subprocess.run(
        ["curl", "-sS", "-b", cookie, "-H", "Accept: application/json", f"{API}{path}"],
        capture_output=True, text=True, timeout=90)
    if r.returncode != 0:
        sys.exit(f"админка не ответила: {r.stderr.strip()}")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        sys.exit("админка вернула не JSON — проверь, жива ли кука (перелогинься)")


def dt(value):
    if not value:
        return None
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def days(value):
    """Сколько дней от сейчас до даты: отрицательное — уже прошла."""
    d = dt(value)
    return None if d is None else (d - NOW).days


# Технические и внутренние записи — в списки касания не идут.
TEST_DOMAINS = ("example.com", "x.com", "qubix.dev", "qubix.pro", "qubix.capital",
                ".test", "test.com", "partner.test", "dev161.test")
TEST_NAMES = ("pentest", "probe", "smoke", "selfverify", "strace", "vmp-",
              "cxx-", "cgo-", "aead-", "shape-test", "prod@")
# Свои и партнёры: пишем им лично, не рассылкой.
OURS = {201: "Будда", 107: "AdsPower", 228: "Хоменюк", 190: "Marta"}
OWN_EMAILS = ("katastrofskaya@gmail.com",)


def is_real(c):
    """Живой клиент, а не тестовая запись и не свой человек."""
    if c["number"] in OURS:
        return False
    email = (c.get("email") or "").lower()
    if email in OWN_EMAILS:
        return False
    if any(email.endswith(d) or d in email for d in TEST_DOMAINS):
        return False
    return not any(email.startswith(n) for n in TEST_NAMES)


def load(keep_all=False):
    customers = get("/customers?limit=1000&offset=0").get("rows", [])
    if not keep_all:
        customers = [c for c in customers if is_real(c)]
    codes = {c["code"].upper(): c for c in get("/promo-codes").get("rows", [])}
    for c in customers:
        code = (c.get("referred_by_code") or "").upper()
        c["_code"] = code or "—"
        c["_discount"] = codes.get(code, {}).get("discount_pct") or 0
        c["_tg"] = bool(c.get("telegram_chat_id"))
    return customers


def row(c, extra_label, extra_value):
    return {
        "номер": c["number"],
        "почта": c["email"],
        "код": c["_code"],
        "скидка": f"{c['_discount']}%" if c["_discount"] else "нет",
        "telegram": "есть" if c["_tg"] else "НЕТ",
        extra_label: extra_value,
    }


def show(title, note, rows):
    print(f"\n=== {title}: {len(rows)} ===")
    if note:
        print(note)
    if not rows:
        print("  пусто")
        return
    cols = list(rows[0].keys())
    widths = {k: max(len(k), max(len(str(r[k])) for r in rows)) for k in cols}
    print("  " + "  ".join(k.ljust(widths[k]) for k in cols))
    for r in rows:
        print("  " + "  ".join(str(r[k]).ljust(widths[k]) for k in cols))
    no_tg = [r for r in rows if r["telegram"] == "НЕТ"]
    if no_tg:
        print(f"  ⚠️ без Telegram — {len(no_tg)}: писать на почту "
              + ", ".join(f"#{r['номер']}" for r in no_tg))


LETTER_EXPIRING = """Здравствуйте! Ваш месяц на Qubix заканчивается {date} — пишу заранее, чтобы вы успели решить спокойно.

Расскажите, что получилось посмотреть за это время: развернули на своём сервере, дошли до первой связки? Если какой-то шаг остался мутным — разберём вместе. Поддержка на связи круглосуточно, живой человек — с 9:00 до 21:00 МСК.

Если продукт подошёл, помогу перевести аккаунт на постоянный тариф: всё останется на вашем сервере ровно так, как настроено сейчас."""

LETTER_EXPIRED = """Здравствуйте! Ваш доступ к Qubix закончился {days} назад — пишу узнать, как прошёл месяц.

Вы продукт до своего сервера довели, значит до сути добрались. Скажите честно: чего не хватило? Ответ полезен в любом случае, даже если вывод — «пока мимо».

Захотите вернуться — ваши данные и настройки на вашем сервере в целости, доступ возвращается одним шагом. Помогу пройти его, поддержка отвечает круглосуточно."""


def plural_days(n):
    """«1 день», «2 дня», «7 дней» — чтобы письмо не выглядело машинным."""
    if 11 <= n % 100 <= 14:
        return f"{n} дней"
    last = n % 10
    if last == 1:
        return f"{n} день"
    if last in (2, 3, 4):
        return f"{n} дня"
    return f"{n} дней"


def sales_card(email):
    """Карточка лида в YouTrack по почте — чтобы отметиться в правильной."""
    yt = os.path.join(os.path.dirname(os.path.abspath(__file__)), "youtrack.sh")
    try:
        out = subprocess.run([yt, "search", email], capture_output=True,
                             text=True, timeout=60).stdout
        found = [i["idReadable"] for i in json.loads(out)
                 if i["idReadable"].startswith("SALES-")]
        # Карточек на одну почту бывает несколько: берём самую полную (с описанием).
        return found[0] if found else None
    except Exception:
        return None


def letters(customers, expiring_days, expired_days):
    """Готовые касания: кому, куда, каким текстом и где отметиться."""
    plan = []
    for c in customers:
        left = days(c.get("paid_until"))
        if left is None or not c.get("last_license_at"):
            continue
        if 0 <= left <= expiring_days:
            when = dt(c["paid_until"]).astimezone().strftime("%d.%m")
            plan.append((c, "ИСТЕКАЕТ", LETTER_EXPIRING.format(date=when), left))
        elif -expired_days <= left < 0:
            plan.append((c, "ИСТЕКЛА",
                         LETTER_EXPIRED.format(days=plural_days(-left)), left))
    plan.sort(key=lambda t: -t[3])

    print(f"\n{'='*70}\nГОТОВЫЕ КАСАНИЯ: {len(plan)} чел. "
          f"Отправили — отметьтесь в карточке.\n{'='*70}")
    for n, (c, kind, text, left) in enumerate(plan, 1):
        card = sales_card(c["email"])
        if c["_tg"]:
            channel = f"Telegram: tg://user?id={c['telegram_chat_id']}"
        else:
            channel = f"почта: {c['email']} (Telegram не привязан)"
        when = ("осталось %d дн." % left) if left >= 0 else ("прошло %d дн." % -left)
        print(f"\n[{n}/{len(plan)}] #{c['number']} · {kind} · {when}")
        print(f"  Кому:     {c['email']}")
        print(f"  Куда:     {channel}")
        print(f"  Карточка: " + (f"https://team.qubix.capital/issue/{card}" if card
                                 else "в SALES не нашлась — завести новую"))
        print(f"  Клиент:   https://admin.qubix.pro/customers/{c['id']}")
        print("  ---- текст ----")
        for line in text.split("\n"):
            print(f"  {line}" if line else "")
        print("  ---- отметка в карточке ----")
        print(f"  Касание по истечению подписки отправлено {NOW.astimezone():%d.%m.%Y}. "
              f"Текст — вариант «{kind.lower()}». Ответ ждём до "
              f"{(NOW + datetime.timedelta(days=3)).astimezone():%d.%m}.")


def main():
    p = argparse.ArgumentParser(description="Списки клиентов для касания")
    p.add_argument("--stuck", action="store_true", help="только застрявшие без лицензии")
    p.add_argument("--expiring", type=int, default=10, metavar="ДНЕЙ")
    p.add_argument("--expired", type=int, default=14, metavar="ДНЕЙ")
    p.add_argument("--csv", metavar="ФАЙЛ", help="выгрузить показанное в CSV")
    p.add_argument("--all", action="store_true",
                   help="не отсеивать тестовые и внутренние аккаунты")
    p.add_argument("--letters", action="store_true",
                   help="готовые тексты касаний со ссылками на карточки")
    args = p.parse_args()
    only_stuck = args.stuck

    customers = load(keep_all=args.all)
    print(f"Срез админки на {NOW.astimezone().strftime('%d.%m.%Y %H:%M')} · "
          f"живых клиентов: {len(customers)}"
          + ("" if args.all else " (тестовые и свои отсеяны)"))

    stuck = sorted(
        (c for c in customers if not c.get("last_license_at")),
        key=lambda c: c["created_at"])
    stuck_rows = [row(c, "дней с регистрации", abs(days(c["created_at"]) or 0))
                  for c in stuck]

    expiring_rows, expired_rows = [], []
    for c in customers:
        left = days(c.get("paid_until"))
        if left is None or not c.get("last_license_at"):
            continue
        if 0 <= left <= args.expiring:
            expiring_rows.append(row(c, "дней осталось", left))
        elif -args.expired <= left < 0:
            expired_rows.append(row(c, "дней как истекла", -left))
    expiring_rows.sort(key=lambda r: r["дней осталось"])
    expired_rows.sort(key=lambda r: r["дней как истекла"])

    shown = []
    show("ЗАСТРЯЛИ — зарегистрировались, продукт не поставили",
         "Повод: подарочный месяц уже лежит на аккаунте и ждёт активации.",
         stuck_rows)
    shown += stuck_rows
    if not only_stuck:
        show(f"ИСТЕКАЮТ в ближайшие {args.expiring} дн.",
             "Разговор нужен ДО даты: после неё это уже возврат, а не продление.",
             expiring_rows)
        show(f"ИСТЕКЛИ за последние {args.expired} дн.",
             "Продукт ставили — значит доходили до сути. Самый тёплый возврат.",
             expired_rows)
        shown += expiring_rows + expired_rows

    if args.letters:
        letters(customers, args.expiring, args.expired)

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8-sig") as f:
            keys = sorted({k for r in shown for k in r})
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(shown)
        print(f"\nВыгружено в {args.csv}: {len(shown)} строк")


if __name__ == "__main__":
    main()
