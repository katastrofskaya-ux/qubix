#!/usr/bin/env python3
"""Сверка по задачам YouTrack: цена, оплата, что вышло, последний комментарий.

Зачем: ни одна таблица с деньгами или статусами не уходит Анастасии и владельцу
без сверки с первоисточником (прецедент 07.10: Traffic Cardinal посчитан
невышедшим, хотя карточка стояла в CONTENT-28; прероллов Хоменока взято 3
вместо 4 из устаревшего замера).

    scripts/sverka.py CONTENT-28 MARKETING-83 ...
    scripts/sverka.py --full CONTENT-28        # плюс все комментарии подряд

Только чтение. Нужен YOUTRACK_API_TOKEN.
"""
import datetime
import json
import os
import re
import subprocess
import sys

YT = "https://team.qubix.capital"
MSK = datetime.timezone(datetime.timedelta(hours=3))

PRICE = re.compile(r"(Цена|Итого к оплате|Сумма|Стоимость)\s*[:：]", re.I)
PAID = re.compile(r"(оплачен|оплатил|выплачен|tronscan)", re.I)
MONEY = re.compile(r"\$\s?\d[\d\s]*|\d[\d\s]*\s?(?:\$|usdt|USDT|долл)")
OUT_LABEL = re.compile(r"Ссылка на (карточку|обзор|пост|листинг|выпуск|ролик)", re.I)
URL = re.compile(r"https?://[^\s)>\]*]+")
SKIP_URL = re.compile(r"tronscan|docs\.google|team\.qubix|qubix\.pro/\?r=|dash\.qubix|my\.qubix")


def yt(path):
    out = subprocess.run(
        ["curl", "-sS", "-H", f"Authorization: Bearer {os.environ['YOUTRACK_API_TOKEN']}",
         "-H", "Accept: application/json", f"{YT}/api{path}"],
        capture_output=True, text=True, timeout=120)
    return json.loads(out.stdout)


def when(ms):
    return datetime.datetime.fromtimestamp(ms / 1000, MSK).strftime("%d.%m %H:%M")


def short(text, n=220):
    return " ".join((text or "").split())[:n]


def check(issue, full=False):
    d = yt(f"/issues/{issue}?fields=idReadable,summary,description,"
           "customFields(name,value(name))")
    if "idReadable" not in d:
        print(f"\n### {issue}: не найдена ({short(json.dumps(d), 120)})")
        return
    state = next((f["value"]["name"] for f in d.get("customFields", [])
                  if f["name"] == "State" and f.get("value")), "—")
    body = d.get("description") or ""
    comments = yt(f"/issues/{issue}/comments?fields=created,text,author(fullName)&$top=5000")

    print(f"\n### {issue} · {d['summary']} · стадия: {state} · комментариев: {len(comments)}")

    prices = [short(l, 160) for l in body.splitlines() if PRICE.search(l)]
    print("Цена (тело):", "; ".join(prices) if prices else "в теле не указана")

    pays = []
    for l in body.splitlines():
        if re.search(r"\[x\].*оплачен", l, re.I):
            pays.append(f"тело: {short(l, 120)}")
    for c in comments:
        t = c.get("text") or ""
        if PAID.search(t) and MONEY.search(t):
            pays.append(f"{when(c['created'])} {c['author']['fullName']}: {short(t, 160)}")
    print("Оплата:", "нет записей об оплате" if not pays else "")
    for p in pays:
        print("  -", p)

    outs = []
    for l in body.splitlines():
        if OUT_LABEL.search(l):
            urls = [u for u in URL.findall(l) if not SKIP_URL.search(u)]
            outs.append(f"{short(l, 80)} → {', '.join(urls) if urls else 'ПУСТО'}")
        elif l.strip().startswith("|"):
            urls = [u for u in URL.findall(l) if "t.me/" in u and re.search(r"/\d+", u)]
            if urls:
                outs.append(f"строка таблицы: {short(l, 80)} → {', '.join(urls)}")
    for c in comments:
        t = c.get("text") or ""
        if re.search(r"(вышел|вышло|опубликован|вышла|вышли)", t, re.I):
            urls = [u for u in URL.findall(t) if not SKIP_URL.search(u)]
            outs.append(f"{when(c['created'])} {c['author']['fullName']}: {short(t, 140)}"
                        + (f" → {', '.join(urls[:3])}" if urls else ""))
    print("Что вышло:", "следов выхода нет" if not outs else "")
    for o in outs:
        print("  -", o)

    if comments:
        c = comments[-1]
        print(f"Последний комментарий: {when(c['created'])} {c['author']['fullName']}: {short(c.get('text'))}")
    if full:
        print("Все комментарии подряд:")
        for c in comments:
            print(f"  [{when(c['created'])}] {c['author']['fullName']}: {short(c.get('text'), 400)}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    print(f"Сверка по YouTrack на {datetime.datetime.now(MSK):%d.%m.%Y %H:%M} МСК")
    for a in args:
        check(a.upper(), full="--full" in sys.argv)


if __name__ == "__main__":
    main()
