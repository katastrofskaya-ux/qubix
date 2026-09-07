#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сторож саппорта: новые/обновлённые задачи SUPPORT за последние N часов,
с пометкой «СЕЙЛЗ/ПАРТНЁРСТВО — к Анастасии» по ключевым словам.

Зачем: по конструкции владельца (07.09.2026) Анастасия смотрит саппорт-таски
первой и забирает оттуда сейлзовое и партнёрское; бот и владелец ведут
остальное. Этот скрипт снимает ручной обход доски.

    scripts/support_watch.py --hours 1
"""
import json, subprocess, datetime, argparse, os, re, urllib.parse

KEYWORDS = re.compile(
    r"партн|скидк|реф\b|реферал|оплат|куп[ил]|сейл|цена|цен[ыу]|тариф|юрид|"
    r"инвойс|сч[её]т|человек|оператор|менедж|команда|team|демо|тест[оа]в",
    re.I)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=1)
    ap.add_argument("--top", type=int, default=40)
    args = ap.parse_args()
    tok = os.environ.get("YOUTRACK_API_TOKEN")
    if not tok:
        print("нет YOUTRACK_API_TOKEN"); return
    q = urllib.parse.quote("project: SUPPORT")
    out = subprocess.run(["curl", "-sS", "--max-time", "25",
        f"https://team.qubix.capital/api/issues?query={q}&$top={args.top}"
        "&fields=idReadable,summary,created,updated,"
        "customFields(name,value(name))",
        "-H", f"Authorization: Bearer {tok}", "-H", "Accept: application/json"],
        capture_output=True, text=True).stdout
    try:
        data = json.loads(out)
    except Exception:
        print("YouTrack не ответил"); return
    now = datetime.datetime.now().timestamp() * 1000
    fresh = [i for i in data
             if now - max(i.get("created", 0), i.get("updated", 0)) <= args.hours * 3600_000]
    if not fresh:
        print(f"Новых движений в SUPPORT за {args.hours:g} ч нет.")
        return
    for i in fresh:
        st = next(((f.get("value") or {}).get("name", "")
                   for f in i.get("customFields", []) if f.get("name") == "State"), "")
        flag = "🔔 СЕЙЛЗ/ПАРТНЁРСТВО — к Анастасии" if KEYWORDS.search(i["summary"]) else ""
        print(f"{i['idReadable']} | {st} | {i['summary'][:90]} {flag}")
        print(f"   https://team.qubix.capital/issue/{i['idReadable']}")

if __name__ == "__main__":
    main()
