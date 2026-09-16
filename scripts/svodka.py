#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сводка: что двинулось в трекере и что стало с нашими черновиками.

⚠️ Отвечать на вопрос «что не отправлено» разрешено ТОЛЬКО выводом этого
скрипта. Прецедент 16.09: агент, уже написав скрипт, полез проверять руками с
отсечкой времени, посчитанной на глаз, — промахнулся на час и объявил
неотправленным комментарий, который стоял в задаче. Руками отсечки не считаем.

    scripts/svodka.py              # за сутки
    scripts/svodka.py --hours 72   # шире окно
    scripts/svodka.py --drafts     # только судьба черновиков

Зачем. Агент повадился объявлять «не отправлено», посмотрев комментарии двух-трёх
задач. Тело задачи при этом не читалось, а Telegram ему не виден вовсе — и человек
шёл перепроверять за ним. Скрипт закрывает обе дыры:

1. **Движение по задачам** — проходит ВСЕ проекты, а не выбранные, и для каждой
   тронутой задачи говорит, что именно изменилось: тело или комментарий, кто и когда.
2. **Судьба черновиков** — по каждому файлу в drafts/ ищет его опорную фразу в
   трекере и отвечает: ушло, не нашёл, или проверить нельзя.

Правило, ради которого всё сделано: **сказать «не сделано» можно только про то, что
проверено целиком — тело И комментарии. Про Telegram, почту и личные переписки агент
не утверждает ничего: они ему не видны.**

Черновик объявляет, куда он адресован, строкой в первых пятнадцати строках файла:

    Куда: CONTENT-3            — проверяется поиском по этой задаче
    Куда: Telegram — Ник       — внешний канал, проверить нельзя, так и пишем

Без такой строки скрипт ищет по всему трекеру и честно помечает находку как
предположение. Нужна переменная окружения YOUTRACK_API_TOKEN.
"""
import argparse, datetime, json, os, re, subprocess, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAFTS = os.path.join(ROOT, "drafts")
BASE = os.environ.get("YOUTRACK_URL", "https://team.qubix.capital")
PROJECTS = ("MARKETING", "CONTENT", "HR", "FIN", "SALES", "SUPPORT", "CONTRACT")
EXTERNAL = re.compile(r"telegram|почт|личк|переписк|чат", re.I)


def yt(path, **params):
    token = os.environ.get("YOUTRACK_API_TOKEN")
    if not token:
        return None
    url = f"{BASE}/api/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    r = subprocess.run(["curl", "-sS", "--max-time", "45",
                        "-H", f"Authorization: Bearer {token}",
                        "-H", "Accept: application/json", url],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def hdr(t):
    print(f"\n{t}\n" + "─" * len(t))


def moved(hours):
    """Задачи, тронутые за период, с разбором: тело или комментарий."""
    since = datetime.datetime.now() - datetime.timedelta(hours=hours)
    ms = int(since.timestamp() * 1000)
    out = []
    for proj in PROJECTS:
        issues = yt("issues", query=f"project: {proj} updated: {since:%Y-%m-%d} .. Today",
                    **{"$top": "200",
                       "fields": "idReadable,summary,updated,customFields(name,value(name))"})
        for i in issues or []:
            if i.get("updated", 0) < ms:
                continue
            cs = yt(f"issues/{i['idReadable']}/comments",
                    fields="created,author(fullName)") or []
            fresh = [c for c in cs if c.get("created", 0) >= ms]
            if fresh:
                last = max(fresh, key=lambda c: c["created"])
                who = (last.get("author") or {}).get("fullName") or "?"
                what = f"комментарий ({len(fresh)}) — {who}"
            else:
                what = "тело задачи"
            out.append((i["updated"], i["idReadable"], i.get("summary", ""), what))
    return sorted(out, reverse=True)


def norm(s):
    """Сравниваем по сути: трекер переносит строки и экранирует разметку."""
    s = re.sub(r"[\\*_`>#]", "", s)
    s = s.replace("—", "-").replace("–", "-").replace("\u00a0", " ")
    return " ".join(s.split()).lower()


def probes_of(text, limit=5):
    """Несколько опорных фраз черновика, равномерно по всему тексту.

    Одной фразы мало: отправляя, человек часто срезает хвост или правит абзац,
    и единственный пробник даёт ложное «не найдено». Поэтому берём до пяти и
    показываем долю совпавших.
    """
    body = re.sub(r"^#.*$|^>.*$|^\s*[-*|].*$", "", text, flags=re.M)
    good = [" ".join(s.split()) for s in re.split(r"(?<=[.!?])\s+", body)]
    good = [s for s in good if 40 <= len(s) <= 140 and not s.startswith("Куда")]
    if len(good) <= limit:
        return good
    step = len(good) / limit
    return [good[int(i * step)] for i in range(limit)]


def drafts_state():
    if not os.path.isdir(DRAFTS):
        return []
    rows = []
    for name in sorted(os.listdir(DRAFTS)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(DRAFTS, name)
        text = open(path, encoding="utf-8").read()
        head = "\n".join(text.splitlines()[:15])
        m = re.search(r"^\s*Куда:\s*(.+)$", head, re.M)
        target = m.group(1).strip() if m else ""
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path))
        if target and EXTERNAL.search(target):
            rows.append((name, mtime, target, "внешний канал — проверить нельзя"))
            continue
        probes = probes_of(text)
        if not probes:
            rows.append((name, mtime, target or "—", "опорных фраз нет"))
            continue
        if target and re.match(r"^[A-Z]+-\d+$", target.split()[0]):
            idr = target.split()[0]
            d = yt(f"issues/{idr}", fields="description") or {}
            cs = yt(f"issues/{idr}/comments", fields="text") or []
            hay = norm((d.get("description") or "") + "\n"
                       + "\n".join(c.get("text") or "" for c in cs))
            hits = sum(1 for pr in probes if norm(pr)[:60] in hay)
            if hits == len(probes):
                state = f"ушло в {idr} целиком"
            elif hits:
                state = f"ушло в {idr} частично — {hits} из {len(probes)}"
            else:
                state = f"в {idr} следов нет"
        else:
            found = yt("issues", query=probes[0][:70], **{"$top": "3", "fields": "idReadable"})
            ids = [i.get("idReadable") for i in found if isinstance(i, dict)] if isinstance(found, list) else []
            state = ("похоже, ушло: " + ", ".join(ids)) if ids \
                    else "в трекере не найдено (адрес не указан)"
        rows.append((name, mtime, target or "—", state))
    return rows


def main():
    p = argparse.ArgumentParser(description="Сводка движения и судьбы черновиков")
    p.add_argument("--hours", type=int, default=24)
    p.add_argument("--drafts", action="store_true", help="только черновики")
    p.add_argument("--days", type=int, default=3,
                   help="показывать черновики, тронутые за N дней (0 — все)")
    args = p.parse_args()
    if not os.environ.get("YOUTRACK_API_TOKEN"):
        sys.exit("нужна переменная окружения YOUTRACK_API_TOKEN")

    if not args.drafts:
        rows = moved(args.hours)
        hdr(f"Движение в трекере за {args.hours} ч — {len(rows)}")
        for u, idr, summ, what in rows:
            t = datetime.datetime.fromtimestamp(u / 1000).strftime("%d.%m %H:%M")
            print(f"  {t}  {idr:<14}{what:<34}{summ[:52]}")

    rows = drafts_state()
    if args.days:
        edge = datetime.datetime.now() - datetime.timedelta(days=args.days)
        rows = [r for r in rows if r[1] >= edge]
    hdr(f"Черновики за {args.days or 'всё'} дн. — {len(rows)}")
    for name, mtime, target, state in rows:
        mark = ("·" if "целиком" in state else "~") if "ушло" in state \
               else ("?" if "нельзя" in state else "‼")
        print(f"  {mark} {name[:44]:<46}{mtime:%d.%m %H:%M}  {target[:22]:<24}{state}")
    print("\n  · — ушло целиком · ~ — ушло частью, хвост срезан или правился")
    print("  ‼ — следов в трекере нет · ? — внешний канал, агент проверить не может")
    print("  Про Telegram, почту и личные переписки вывод не делается.\n")


if __name__ == "__main__":
    main()
