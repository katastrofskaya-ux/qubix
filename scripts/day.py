#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Разбор дня: что горит, что ждёт моего решения, что изменилось, что впереди.

    scripts/day.py            — сегодня
    scripts/day.py --week     — плюс вся неделя
    scripts/day.py --quiet    — без обращения к YouTrack (только PLAN.md)

Источники: PLAN.md (правится руками) + YouTrack (что изменилось и где меня зовут).
"""
import argparse, datetime, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN = os.path.join(ROOT, "PLAN.md")
YT = os.path.join(ROOT, "scripts", "youtrack.sh")
ME = "Anastasia"

TODAY = datetime.date.today()


def parse_plan():
    items, cal, monthly, focus = [], [], [], ""
    section = ""
    for raw in open(PLAN, encoding="utf-8"):
        line = raw.rstrip()
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if section.startswith("Фокус недели") and line.startswith("Одно предложение"):
            continue
        if section.startswith("Фокус недели") and line.startswith("**"):
            focus = line.strip("* ")
            continue
        m = re.match(r"- \[( |x)\] @(\S+) ·\s*([\d-]*)\s*· (.+)", line)
        if m:
            done, who, date, rest = m.groups()
            parts = [p.strip() for p in rest.split("·")]
            d = None
            if date:
                try:
                    d = datetime.date.fromisoformat(date)
                except ValueError:
                    d = None
            items.append({"done": done == "x", "who": who, "date": d,
                          "text": parts[0], "where": " · ".join(parts[1:]),
                          "section": section})
            continue
        if section == "Календарь" and line.startswith("- "):
            cal.append(line[2:])
        if section.startswith("Повторяется") and line.startswith("- "):
            monthly.append(line[2:])
    return items, cal, monthly, focus


def yt(*args):
    try:
        out = subprocess.run([YT, *args], capture_output=True, text=True, timeout=60)
        return out.stdout
    except Exception:
        return ""


def yt_changes():
    """Что изменилось со вчера и где меня зовут по имени."""
    raw = yt("search", "updated: Today or updated: Yesterday", "150")
    try:
        arr = json.loads(raw)
    except Exception:
        return None
    mine, other = [], []
    for i in arr:
        proj = i["idReadable"].split("-")[0]
        if proj == "DEV":
            continue  # шум разработки: смотрим только то, что заведено нами
        st = ""
        for c in i.get("customFields", []):
            v = c.get("value")
            if v and c["name"] == "State":
                st = v.get("name", "")
        rec = (i["idReadable"], st, i["summary"][:72],
               datetime.datetime.utcfromtimestamp(i["updated"] / 1000))
        (mine if proj in ("MARKETING", "CONTENT", "OP", "SUPPORT") else other).append(rec)
    mine.sort(key=lambda r: r[3], reverse=True)
    return mine[:15]


def hdr(t):
    print(f"\n\033[1m{t}\033[0m" if sys.stdout.isatty() else f"\n{t}")
    print("─" * len(t))


def show(items):
    for it in items:
        d = it["date"]
        mark = ""
        if d and d < TODAY:
            mark = f"  ⟵ просрочено на {(TODAY - d).days} дн."
        elif d == TODAY:
            mark = "  ⟵ сегодня"
        elif d:
            mark = f"  ⟵ через {(d - TODAY).days} дн."
        where = f"\n     {it['where']}" if it["where"] else ""
        print(f"  • {it['text']}{mark}{where}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", action="store_true")
    ap.add_argument("--quiet", action="store_true", help="без YouTrack")
    a = ap.parse_args()

    items, cal, monthly, focus = parse_plan()
    open_items = [i for i in items if not i["done"]]
    ru_day = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

    print(f"\n{TODAY.strftime('%d.%m.%Y')}, {ru_day[TODAY.weekday()]}")
    if focus:
        print(f"Фокус недели: {focus}")

    mine = [i for i in open_items if i["who"] == "я"]
    burning = [i for i in mine if i["date"] and i["date"] <= TODAY]
    week_end = TODAY + datetime.timedelta(days=(6 - TODAY.weekday()))
    soon = [i for i in mine if i["date"] and TODAY < i["date"] <= week_end]
    undated = [i for i in mine if not i["date"]]
    waiting = [i for i in open_items if i["who"] != "я"]

    if burning:
        hdr(f"Горит — {len(burning)}")
        show(burning)
    else:
        hdr("Горит — ничего")
        print("  Просроченного и назначенного на сегодня нет.")

    if soon and (a.week or len(burning) < 4):
        hdr(f"До конца недели — {len(soon)}")
        show(soon)

    if a.week and undated:
        hdr(f"Без срока — {len(undated)}")
        show(undated)

    if waiting:
        hdr(f"Жду других — {len(waiting)}")
        by = {}
        for w in waiting:
            by.setdefault(w["who"], []).append(w)
        for who, ws in by.items():
            print(f"  @{who}:")
            for w in ws:
                print(f"     – {w['text']}")

    # календарь
    up = []
    for c in cal:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", c)
        if not m:
            continue
        d = datetime.date.fromisoformat(m.group(1))
        horizon = 14 if a.week else 7
        if TODAY <= d <= TODAY + datetime.timedelta(days=horizon):
            up.append((d, c))
    if up:
        hdr("Календарь, ближайшее")
        for d, c in sorted(up):
            days = (d - TODAY).days
            when = "сегодня" if days == 0 else ("завтра" if days == 1 else f"через {days} дн.")
            print(f"  • {when}: {c.split('·', 1)[1].strip() if '·' in c else c}")

    if TODAY.day <= 8 and monthly:
        hdr("Ежемесячное — начало месяца, срок идёт")
        for m in monthly:
            print(f"  • {m}")

    if not a.quiet:
        ch = yt_changes()
        if ch is None:
            hdr("YouTrack")
            print("  Не ответил. Проверьте YOUTRACK_API_TOKEN.")
        elif ch:
            hdr("Изменилось в задачах за сутки")
            for idr, st, summ, t in ch:
                print(f"  {t.strftime('%d.%m %H:%M')}  {idr:<13} {st:<18} {summ}")

    hdr("Дальше")
    print("  Правьте PLAN.md руками — это ваш план, не мой.")
    print("  scripts/day.py --week — вся неделя. --quiet — без обращения к трекеру.")
    print()


if __name__ == "__main__":
    main()
