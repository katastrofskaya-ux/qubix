#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Новые лиды и обращения за последние N часов.

    scripts/leads.py            — за последний час
    scripts/leads.py --hours 24 — за сутки
Отличает похожее на живого человека от технической записи бота.
"""
import argparse, datetime, json, os, re, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YT = os.path.join(ROOT, "scripts", "youtrack.sh")


def yt(*a):
    try:
        return subprocess.run([YT, *a], capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return ""


def looks_human(summary):
    """tg:123456789 — техническая запись. @handle или имя — вероятно живой."""
    if re.search(r"tg:\d+", summary):
        return False
    if re.search(r"@[A-Za-z][\w]{3,}", summary):
        return True
    tail = re.sub(r"^Лид\s*(#\d+)?\s*[—-]?\s*", "", summary).strip()
    return bool(re.match(r"[A-ZА-ЯЁ][\wа-яё]{2,}", tail))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=1.0)
    a = ap.parse_args()

    since = datetime.datetime.utcnow() - datetime.timedelta(hours=a.hours)
    out = []
    for proj in ("SALES", "SUPPORT"):
        raw = yt("search", f"project: {proj} created: Today or project: {proj} created: Yesterday", "100")
        try:
            arr = json.loads(raw)
        except Exception:
            print(f"{proj}: трекер не ответил")
            continue
        for i in arr:
            created = datetime.datetime.utcfromtimestamp(i["created"] / 1000)
            if created < since:
                continue
            out.append((created, proj, i["idReadable"], i["summary"]))

    if not out:
        print(f"За последние {a.hours:g} ч нового в SALES и SUPPORT нет.")
        return

    out.sort(reverse=True)
    human = [o for o in out if o[1] == "SALES" and looks_human(o[3])]
    tech = [o for o in out if o[1] == "SALES" and not looks_human(o[3])]
    sup = [o for o in out if o[1] == "SUPPORT"]

    if sup:
        print(f"\nОбращения в поддержку — {len(sup)}:")
        for c, p, idr, s in sup:
            print(f"  {c.strftime('%H:%M')}  {idr}  {s[:90]}")
    if human:
        print(f"\nЛиды, похожие на живых людей — {len(human)}:")
        for c, p, idr, s in human:
            print(f"  {c.strftime('%H:%M')}  {idr}  {s[:90]}")
    if tech:
        print(f"\nЛиды без имени (tg-идентификатор) — {len(tech)}: "
              + ", ".join(o[2] for o in tech[:12]) + ("…" if len(tech) > 12 else ""))


if __name__ == "__main__":
    main()
