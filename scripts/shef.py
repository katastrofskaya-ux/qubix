#!/usr/bin/env python3
"""Что владелец уже сказал по теме — до того, как нести ему текст или вопрос.

Ищет дословные слова владельца и решения, записанные с его слов:
  1) комментарии Владимира и admin во всех задачах YouTrack;
  2) реестр решений PRODUCT-35 (тело);
  3) RESHENIYA.md — решения из Telegram, выписанные со скринов;
  4) drafts/skriny/*.md — расшифровки переписки.

    scripts/shef.py "преленд"
    scripts/shef.py "менеджер оклад" --days 30

Совпадение — по всем словам запроса (по первым 5 буквам слова, чтобы ловить
падежи). Прецедент 07.10: агент спросил владельца про цель преленда, хотя тот
ответил ещё 03.10. Только чтение. Нужен YOUTRACK_API_TOKEN.
"""
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import urllib.parse

YT = "https://team.qubix.capital"
MSK = datetime.timezone(datetime.timedelta(hours=3))
OWNER = {"Владимир", "admin", "vladimir"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def yt(path):
    out = subprocess.run(
        ["curl", "-sS", "-H", f"Authorization: Bearer {os.environ['YOUTRACK_API_TOKEN']}",
         "-H", "Accept: application/json", f"{YT}/api{path}"],
        capture_output=True, text=True, timeout=120)
    return json.loads(out.stdout)


def stems(q):
    return [w.lower()[:5] for w in re.findall(r"\w+", q) if len(w) > 2]


def hit(text, ss):
    t = (text or "").lower()
    return all(s in t for s in ss)


def snippet(text, ss, n=320):
    t = " ".join((text or "").split())
    i = t.lower().find(ss[0]) if ss else 0
    i = max(0, i - 120)
    return ("…" if i else "") + t[i:i + n] + ("…" if len(t) > i + n else "")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    q = " ".join(args)
    ss = stems(q)
    days = None
    if "--days" in sys.argv:
        days = int(sys.argv[sys.argv.index("--days") + 1])
        args = [a for a in args if a != str(days)]
    since = (datetime.datetime.now(MSK) - datetime.timedelta(days=days)) if days else None
    print(f"Слова владельца по теме «{q}» — {datetime.datetime.now(MSK):%d.%m.%Y %H:%M} МСК\n")

    # 1) YouTrack: задачи, где встречаются слова, → комментарии владельца/admin
    query = urllib.parse.quote(q)
    issues = yt(f"/issues?query={query}&fields=idReadable,summary&$top=200")
    found = []
    for i in issues if isinstance(issues, list) else []:
        for c in yt(f"/issues/{i['idReadable']}/comments?fields=created,text,author(fullName,login)&$top=5000"):
            a = c.get("author") or {}
            if a.get("fullName") not in OWNER and a.get("login") not in OWNER:
                continue
            ts = datetime.datetime.fromtimestamp(c["created"] / 1000, MSK)
            if since and ts < since:
                continue
            if hit(c.get("text"), ss):
                found.append((ts, i["idReadable"], a.get("fullName"), snippet(c.get("text"), ss)))
    found.sort(reverse=True)
    print(f"== YouTrack, комментарии владельца и admin: {len(found)} ==")
    for ts, iid, who, sn in found[:40]:
        print(f"- {ts:%d.%m.%Y %H:%M} · {iid} · {who}: {sn}")

    # 2) PRODUCT-35 — реестр решений (тело)
    d = yt("/issues/PRODUCT-35?fields=description")
    body = d.get("description") or ""
    paras = [p for p in re.split(r"\n\s*\n", body) if hit(p, ss)]
    print(f"\n== PRODUCT-35, реестр решений: {len(paras)} ==")
    for p in paras[:20]:
        print("-", snippet(p, ss, 400))

    # 3–4) файлы: RESHENIYA.md и расшифровки скринов
    files = [os.path.join(ROOT, "RESHENIYA.md")] + sorted(glob.glob(os.path.join(ROOT, "drafts/skriny/*.md")))
    print("\n== RESHENIYA.md и расшифровки скринов ==")
    n = 0
    for f in files:
        if not os.path.exists(f):
            continue
        for k, line in enumerate(open(f, encoding="utf-8"), 1):
            if hit(line, ss):
                n += 1
                print(f"- {os.path.relpath(f, ROOT)}:{k}: {snippet(line, ss)}")
    if not n:
        print("- совпадений нет")
    print("\nНоль совпадений — это «в этих источниках не найдено», а не «владелец не говорил»: "
          "Telegram без скринов агенту не виден.")


if __name__ == "__main__":
    main()
