#!/usr/bin/env python3
"""Замер воронки по выходам размещений.

Считает по конструкции, утверждённой владельцем 04.09.2026 (MARKETING-87):
регистрация → выдача лицензии → сервер отчитался → покупка,
окно N дней после выхода, цена ступени против лестницы $110 / $220 / $379.

Источники: VYHODY.md (какие выходы были) + admin.qubix.pro (что произошло).
Только чтение. Выдаёт готовую таблицу для тела задачи-реестра.

    scripts/zamer.py                 # таблица по всем выходам, окно 7 дней
    scripts/zamer.py --window 14     # другое окно
    scripts/zamer.py --all           # накопительно по коду, без окна
    scripts/zamer.py --voronka       # только общая воронка по базе
    scripts/zamer.py --cache         # взять клиентов из прошлого прогона

Нужна переменная окружения ADMIN_QUBIX_COOKIE.
"""
import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
VYHODY = ROOT / "VYHODY.md"
CACHE = ROOT / "data" / "zamer-clients.json"
API = "https://admin.qubix.pro/api/admin/v1"
LESTNICA = {"рег": 110, "лиц": 220, "покупка": 379}

sys.path.insert(0, str(ROOT / "scripts"))


def filters():
    """Списки отсева из touch.py — чтобы фильтр был один на все скрипты."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("touch", ROOT / "scripts" / "touch.py")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    return (
        getattr(mod, "TEST_DOMAINS", set()),
        getattr(mod, "TEST_NAMES", set()),
        getattr(mod, "OURS", set()),
        getattr(mod, "OWN_EMAILS", set()),
    )


def curl(url, cookie):
    out = subprocess.run(
        ["curl", "-sS", "--max-time", "40", url, "-H", f"Cookie: {cookie}"],
        capture_output=True, text=True,
    )
    try:
        return json.loads(out.stdout)
    except Exception:
        return None


def load_clients(cookie, use_cache):
    if use_cache and CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    rows = []
    for off in (0, 100, 200):
        page = curl(f"{API}/customers?limit=100&offset={off}", cookie)
        if not page or not page.get("rows"):
            break
        rows += page["rows"]
    full = []
    for i, r in enumerate(rows, 1):
        card = curl(f"{API}/customers/{r['id']}", cookie)
        if not card:
            continue
        lic = card.get("licenses") or []
        full.append({
            "num": r["number"],
            "email": r.get("email") or "",
            "code": (r.get("referred_by_code") or "").upper(),
            "created": r.get("created_at"),
            "lic": len(lic),
            "heartbeat": any(l.get("last_seen") for l in lic),
            "pays": [
                {"st": p.get("status"), "amt": p.get("amount_usd") or 0,
                 "plan": p.get("plan_code")}
                for p in (card.get("payments") or [])
            ],
        })
        if i % 40 == 0:
            print(f"  … {i}/{len(rows)}", file=sys.stderr)
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(full, ensure_ascii=False), encoding="utf-8")
    return full


def live_only(full):
    td, tn, ours, own_mails = filters()

    def mine(x):
        e = x["email"].lower()
        return (x["num"] in ours or e in own_mails
                or any(e.endswith("@" + d) for d in td)
                or any(n in e for n in tn))

    return [x for x in full if not mine(x)]


LINE = re.compile(
    r"^-\s*(\d{4}-\d{2}-\d{2})\s*·\s*(.+?)\s*·\s*(.+?)\s*·\s*([A-Z]+-\d+)\s*·\s*(\d+)\s*·\s*(.+?)\s*$"
)


def read_vyhody():
    outs = []
    for raw in VYHODY.read_text(encoding="utf-8").splitlines():
        m = LINE.match(raw.strip())
        if not m:
            continue
        date, channel, krug, task, spend, codes = m.groups()
        codes = [c.strip().upper() for c in codes.split(",") if c.strip() and c.strip() != "—"]
        if not codes:
            continue
        outs.append({"date": dt.date.fromisoformat(date), "channel": channel,
                     "krug": krug, "task": task, "spend": int(spend), "codes": codes})
    return outs


def paid(x):
    return [p for p in x["pays"] if p["st"] == "paid" and p["amt"] > 0]


def pending(x):
    return [p for p in x["pays"] if p["st"] == "pending" and p["amt"] > 0]


def measure(out, clients, window):
    hit = []
    for x in clients:
        if x["code"] not in out["codes"]:
            continue
        if window is not None:
            if not x["created"]:
                continue
            c = dt.datetime.fromisoformat(x["created"].replace("Z", "+00:00")).date()
            if not (out["date"] <= c < out["date"] + dt.timedelta(days=window)):
                continue
        hit.append(x)
    return {
        "рег": len(hit),
        "лиц": sum(1 for x in hit if x["lic"] > 0),
        "сервер": sum(1 for x in hit if x["heartbeat"]),
        "покупка": sum(1 for x in hit if paid(x)),
        "касса": sum(1 for x in hit if pending(x)),
    }


def price(spend, n):
    return f"${spend // n}" if n else "—"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--window", type=int, default=7, help="окно в днях после выхода")
    ap.add_argument("--all", action="store_true", help="накопительно по коду, без окна")
    ap.add_argument("--voronka", action="store_true", help="только общая воронка")
    ap.add_argument("--cache", action="store_true", help="клиенты из прошлого прогона")
    args = ap.parse_args()

    cookie = os.environ.get("ADMIN_QUBIX_COOKIE")
    if not cookie and not (args.cache and CACHE.exists()):
        sys.exit("нужна переменная окружения ADMIN_QUBIX_COOKIE")

    full = load_clients(cookie, args.cache)
    clients = live_only(full)
    window = None if args.all else args.window

    print(f"Срез {dt.date.today().strftime('%d.%m.%Y')} · "
          f"карточек {len(full)}, живых {len(clients)} · "
          f"{'накопительно, без окна' if window is None else f'окно {window} дней после выхода'}\n")

    print("## Воронка целиком\n")
    print("| Ступень | Человек |\n|---|---|")
    print(f"| Регистрация | {len(clients)} |")
    print(f"| Лицензия выдана | {sum(1 for x in clients if x['lic'] > 0)} |")
    print(f"| Сервер отчитался | {sum(1 for x in clients if x['heartbeat'])} |")
    print(f"| Покупка | {sum(1 for x in clients if paid(x))} |")
    print(f"| В оформлении, не оплачено | {sum(1 for x in clients if pending(x))} |")
    if args.voronka:
        return

    rows = []
    for out in read_vyhody():
        m = measure(out, clients, window)
        rows.append((out, m))
    rows.sort(key=lambda r: (r[1]["рег"] == 0, r[0]["spend"] // r[1]["рег"] if r[1]["рег"] else 10**9))

    print("\n## Замеры по выходам\n")
    print("| Канал | Круг | Задача | Оплачено | Выход | Рег | Лиц | Сервер | Покупка | В кассе | $/рег | $/лиц |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for out, m in rows:
        print(f"| {out['channel']} | {out['krug']} | {out['task']} | ${out['spend']} | "
              f"{out['date'].strftime('%d.%m')} | {m['рег']} | {m['лиц']} | {m['сервер']} | "
              f"{m['покупка']} | {m['касса']} | {price(out['spend'], m['рег'])} | "
              f"{price(out['spend'], m['лиц'])} |")

    print(f"\nЛестница из MARKETING-76: ${LESTNICA['рег']} за регистрацию, "
          f"${LESTNICA['лиц']} за лицензию, ${LESTNICA['покупка']} за покупку.")
    ok = [o["channel"] for o, m in rows if m["рег"] and o["spend"] // m["рег"] <= LESTNICA["рег"]]
    print("Проходят лестницу по регистрации: " + (", ".join(ok) if ok else "ни один выход."))

    print("\n## Сравнение кругов по одному каналу\n")
    by_ch = {}
    for out, m in rows:
        by_ch.setdefault(out["channel"], []).append((out, m))
    printed = False
    for ch, items in sorted(by_ch.items()):
        if len(items) < 2:
            continue
        printed = True
        items.sort(key=lambda r: r[0]["date"])
        parts = [f"{o['date'].strftime('%d.%m')} {o['krug']} — {price(o['spend'], m['рег'])}"
                 for o, m in items]
        print(f"- **{ch}**: " + " → ".join(parts))
    if not printed:
        print("Каналов с двумя и более выходами пока нет.")


if __name__ == "__main__":
    main()
