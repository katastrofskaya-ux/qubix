#!/usr/bin/env python3
"""Книга фактов: собирает FAKTY.md — единственное место, откуда документы берут цифры.

    scripts/fakty.py            — пересобрать FAKTY.md
    scripts/fakty.py --print    — то же, плюс вывести на экран

Что внутри (у каждой цифры — дата и источник):
  1. Клиенты и воронка — админка, живой счёт (без технических, тестовых и своих).
  2. Оплаты — реальные платежи из админки (тестовые отсеяны).
  3. Оплачено, не вышло — реестр scripts/ostatki.json + что нового в этих задачах за сутки.
  4. Новое от владельца и admin за сутки — по всем задачам YouTrack.
  5. Постоянные факты — FAKTY-ruchnye.md (правится руками, с источником в каждой строке).

Запускается каждое утро в разборе дня. Нужны ADMIN_QUBIX_COOKIE и YOUTRACK_API_TOKEN.
Недоступный источник не выдумывается: в разделе стоит «нет данных» и причина.
"""
import datetime
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
MSK = datetime.timezone(datetime.timedelta(hours=3))
NOW = datetime.datetime.now(MSK)
YT = "https://team.qubix.capital"
OUT = os.path.join(ROOT, "FAKTY.md")
HAND = os.path.join(ROOT, "FAKTY-ruchnye.md")
LEDGER = os.path.join(ROOT, "scripts", "ostatki.json")
WINDOW_H = 26  # окно «новое за сутки» с запасом на сдвиг запуска


def yt(path):
    out = subprocess.run(
        ["curl", "-sS", "-H", f"Authorization: Bearer {os.environ['YOUTRACK_API_TOKEN']}",
         "-H", "Accept: application/json", f"{YT}/api{path}"],
        capture_output=True, text=True, timeout=120)
    return json.loads(out.stdout)


def money(x):
    return f"${x:,.0f}".replace(",", " ")


def short(t, n=260):
    return " ".join((t or "").split())[:n]


def clients():
    if not os.environ.get("ADMIN_QUBIX_COOKIE"):
        return ["Нет данных: не задана ADMIN_QUBIX_COOKIE."]
    import touch
    from klienty import TEST_PAYMENTS
    allc = touch.load(keep_all=True)
    internal = [c for c in allc if c.get("is_internal")]
    rest = [c for c in allc if not c.get("is_internal")]
    ours = [c for c in rest if not touch.is_real(c)]
    real = [c for c in rest if touch.is_real(c)]
    stage = {"Оплатил": 0, "Сервер стоит": 0, "Лицензия без сервера": 0, "Только регистрация": 0}
    pays, abandoned = [], []
    for c in real:
        full = touch.get(f"/customers/{c['id']}")
        lic = full.get("licenses") or []
        seen = any(l.get("last_seen") for l in lic)
        paid = [p for p in (full.get("payments") or [])
                if p.get("status") == "paid" and (p.get("amount_usd") or 0) > 0
                and c["number"] not in TEST_PAYMENTS]
        if any(p.get("status") == "expired" and (p.get("amount_usd") or 0) > 0
               for p in (full.get("payments") or [])) and not paid:
            abandoned.append(c["number"])
        for p in paid:
            pays.append((c["number"], p.get("amount_usd"), p.get("plan_code"), (p.get("created_at") or "")[:10]))
        if paid:
            stage["Оплатил"] += 1
        elif seen:
            stage["Сервер стоит"] += 1
        elif lic:
            stage["Лицензия без сервера"] += 1
        else:
            stage["Только регистрация"] += 1
    src = f"админка admin.qubix.pro, {NOW:%d.%m.%Y %H:%M} МСК"
    lines = [
        f"| Показатель | Значение | Источник |", "|---|---|---|",
        f"| Записей в базе | {len(allc)} | {src} |",
        f"| Технические (is_internal, DEV-2555) | {len(internal)} | {src} |",
        f"| Наши и контрагенты, тестовые на публичной почте (scripts/touch.py) | {len(ours)} | {src} |",
        f"| **Клиентов** | **{len(real)}** | {src} |",
    ]
    for k, v in stage.items():
        lines.append(f"| — {k} | {v} | {src} |")
    lines.append(f"| Начали оплату и бросили счёт | {len(abandoned)}: " + ", ".join(f"№{n}" for n in sorted(abandoned)) + f" | {src} |")
    lines.append("")
    lines.append("Ступень: оплатил — платёж с суммой больше нуля (тестовые №" + ", ".join(map(str, sorted(TEST_PAYMENTS)))
                 + " не считаются); сервер стоит — есть сигнал сервера (last_seen); лицензия без сервера — лицензия есть, сигнала нет.")
    lines.append("")
    lines.append("**Оплаты (реальные):** " + ("нет" if not pays else "; ".join(
        f"№{n} — {money(a)} {pl} {d}" for n, a, pl, d in sorted(pays, key=lambda x: x[3]))) + f" · {src}")
    return lines


def ledger():
    data = json.load(open(LEDGER, encoding="utf-8"))
    since = NOW - datetime.timedelta(hours=WINDOW_H)
    lines = ["| Кто | Остаток | Основа | Новое в задаче за сутки |", "|---|---|---|---|"]
    total = 0
    cache = {}
    for r in data["rows"]:
        iid = r["issue"]
        if iid not in cache:
            cs = yt(f"/issues/{iid}/comments?fields=created,text,author(fullName)&$top=5000")
            new = [c for c in cs if datetime.datetime.fromtimestamp(c["created"] / 1000, MSK) >= since]
            cache[iid] = new
        new = cache[iid]
        note = "—" if not new else "⚠️ " + "; ".join(
            f"{datetime.datetime.fromtimestamp(c['created']/1000, MSK):%d.%m %H:%M} {c['author']['fullName']}: {short(c.get('text'), 120)}"
            for c in new[-3:])
        if r["ostatok"] is not None:
            total += r["ostatok"]
        ost = money(r["ostatok"]) if r["ostatok"] is not None else "в итог не входит"
        lines.append(f"| {r['who']} · {iid} | {ost} | {r['osnova']} | {note} |")
    lines.append(f"| **Итого** | **{money(total)}** | реестр scripts/ostatki.json | |")
    lines.append("")
    lines.append("⚠️ в последней колонке — в задаче появилось новое: сверить `scripts/sverka.py <задача>` "
                 "и при выходе размещения поправить остаток в scripts/ostatki.json.")
    return lines


def owner_news():
    since = NOW - datetime.timedelta(hours=WINDOW_H)
    q = f"updated: {since:%Y-%m-%d} .. {NOW:%Y-%m-%d}"
    import urllib.parse
    issues = yt(f"/issues?query={urllib.parse.quote(q)}&fields=idReadable,summary,project(shortName)&$top=500")
    out = []
    for i in issues if isinstance(issues, list) else []:
        cs = yt(f"/issues/{i['idReadable']}/comments?fields=created,text,author(fullName,login)&$top=5000")
        for c in cs:
            ts = datetime.datetime.fromtimestamp(c["created"] / 1000, MSK)
            if ts < since:
                continue
            who = (c.get("author") or {}).get("fullName") or ""
            text = c.get("text") or ""
            owner = who == "Владимир"
            admin_relevant = who == "admin" and i["project"]["shortName"] not in ("DEV",)  # DEV — продуктовые решения, не зона Анастасии
            if owner or admin_relevant:
                out.append((ts, i["idReadable"], who, short(text, 300)))
    out.sort(reverse=True)
    if not out:
        return [f"За {WINDOW_H} ч — нет комментариев владельца и значимых комментариев admin (YouTrack, {NOW:%d.%m %H:%M} МСК)."]
    return [f"- {ts:%d.%m %H:%M} · {iid} · {who}: {t}" for ts, iid, who, t in out]


def section(title, fn):
    try:
        body = fn()
    except Exception as e:  # источник упал — пишем, а не выдумываем
        body = [f"Нет данных: {type(e).__name__}: {e}"]
    return [f"## {title}", ""] + body + [""]


def main():
    parts = [
        "# Книга фактов",
        "",
        f"Собрано автоматически: {NOW:%d.%m.%Y %H:%M} МСК, `scripts/fakty.py` (каждое утро в разборе дня). "
        "Любая цифра в документах для Анастасии и владельца берётся отсюда. Поменялась цифра — правится "
        "источник (админка, scripts/ostatki.json, FAKTY-ruchnye.md), а не документ.",
        "",
    ]
    parts += section("1. Клиенты, воронка, оплаты", clients)
    parts += section("2. Оплачено, но не вышло", ledger)
    parts += section(f"3. Новое от владельца и admin за {WINDOW_H} ч", owner_news)
    parts += ["## 4. Постоянные факты (руками, с источником)", ""]
    parts += [open(HAND, encoding="utf-8").read().strip() if os.path.exists(HAND) else "FAKTY-ruchnye.md не найден.", ""]
    text = "\n".join(parts)
    open(OUT, "w", encoding="utf-8").write(text)
    if "--print" in sys.argv:
        print(text)
    else:
        print(f"FAKTY.md обновлён: {NOW:%d.%m.%Y %H:%M} МСК")


if __name__ == "__main__":
    main()
