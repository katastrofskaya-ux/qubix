#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Карта фронта: вся картина одним экраном, светофор по блокам.

Источники: admin.qubix.pro (ADMIN_QUBIX_COOKIE), YouTrack (YOUTRACK_API_TOKEN),
Masha (MASHA_API_TOKEN), BUDGET.md, FRONT.md. Любой недоступный источник
помечается «нет данных», карта строится из остального.
"""
import os, re, json, subprocess, datetime, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TODAY = datetime.date.today()
G, Y, R, N = "🟢", "🟡", "🔴", "⚪"

def curl(url, headers=None, cookie=None, timeout=25):
    cmd = ["curl", "-sS", "--max-time", str(timeout), url]
    for h in (headers or []): cmd += ["-H", h]
    if cookie: cmd += ["-b", cookie]
    p = subprocess.run(cmd, capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None

def d(s):
    if not s: return None
    try: return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception: return None

# ---------- Продажи (админка) ----------
def block_sales():
    cookie = os.environ.get("ADMIN_QUBIX_COOKIE")
    if not cookie:
        return (N, "Продажи", ["нет данных: переменная ADMIN_QUBIX_COOKIE не задана"])
    rows, seen = [], set()
    for off in (0, 100, 200, 300):
        out = curl(f"https://admin.qubix.pro/api/admin/v1/customers?limit=100&offset={off}",
                   headers=["accept: application/json"], cookie=cookie)
        try: batch = json.loads(out).get("rows", [])
        except Exception: return (N, "Продажи", ["админка не ответила"])
        new = [r for r in batch if r["id"] not in seen]
        if not new: break
        for r in new: seen.add(r["id"]); rows.append(r)
    tech = re.compile(r"@(qubix\.pro|qubix\.capital|qubix\.dev|example\.com|ex\.com|test\.com)$|\.test$")
    real = [r for r in rows if not tech.search((r.get("email") or "").lower())]
    exp_soon = [r for r in real if d(r.get("paid_until")) and 0 <= (d(r["paid_until"]) - TODAY).days <= 2]
    exp_past = [r for r in real if d(r.get("paid_until")) and -7 <= (d(r["paid_until"]) - TODAY).days < 0]
    new3 = [r for r in real if d(r.get("created_at")) and (TODAY - d(r["created_at"])).days <= 3]
    stuck = [r for r in new3 if not r.get("license_state")]
    nolic = [r for r in real if not r.get("license_state")]
    light = R if (exp_soon or exp_past or stuck) else (Y if nolic else G)
    lines = [f"истекает за 2 дня: {len(exp_soon)} · истекло за неделю: {len(exp_past)}",
             f"новых за 3 дня: {len(new3)}, из них застряло без лицензии: {len(stuck)}",
             f"всего зарегистрированных без лицензии: {len(nolic)} из {len(real)}"]
    if exp_soon or exp_past:
        lines.append("первым делом: касание истекающим (текст в drafts/kasanie-istekayushchim.md)")
    return (light, "Продажи", lines)

# ---------- Лиды (YouTrack) ----------
def yt(path):
    tok = os.environ.get("YOUTRACK_API_TOKEN")
    if not tok: return None
    out = curl(f"https://team.qubix.capital/api{path}",
               headers=[f"Authorization: Bearer {tok}", "Accept: application/json"])
    try: return json.loads(out)
    except Exception: return None

def yt_states(project, top=300):
    data = yt(f"/issues?query=project:{project}&$top={top}&fields=idReadable,customFields(name,value(name))")
    if data is None: return None
    st = {}
    for i in data:
        s = next(((f.get("value") or {}).get("name") for f in i.get("customFields", [])
                  if f.get("name") == "State"), None)
        st[s] = st.get(s, 0) + 1
    return st

def block_leads():
    st = yt_states("SALES")
    if st is None: return (N, "Очередь лидов", ["нет данных: YouTrack недоступен"])
    new, won = st.get("New", 0), st.get("Won", 0)
    total = sum(st.values())
    light = R if new > 80 else (Y if new > 30 else G)
    return (light, "Очередь лидов", [f"в New: {new} из {total} · выиграно: {won}",
            "решение «кто работает очередь» - на созвоне с шефом"])

# ---------- Канал (Masha) ----------
def block_channel():
    tok = os.environ.get("MASHA_API_TOKEN")
    if not tok: return (N, "Наш канал", ["нет данных: MASHA_API_TOKEN не задан"])
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "analyst_sql", "arguments": {"sql":
        "SELECT username, last_post, subscribers FROM v_channel_metrics WHERE username = 'qubix_pro'"}}})
    out = subprocess.run(["curl", "-sS", "--max-time", "25", "https://masha.qubix.pro/",
        "-H", f"Authorization: Bearer {tok}", "-H", "Content-Type: application/json",
        "-d", body], capture_output=True, text=True).stdout
    m = re.search(r'"last_post"\s*:\s*"([^"]+)"', out or "")
    subs = re.search(r'"subscribers"\s*:\s*(\d+)', out or "")
    if not m:
        return (N, "Наш канал", ["канал не виден в базе Маши (парсер не вступал) - смотреть руками"])
    last = d(m.group(1)[:10]); age = (TODAY - last).days if last else 99
    light = R if age > 3 else (Y if age >= 2 else G)
    lines = [f"последний пост: {last} ({age} дн. назад)" + (f" · подписчиков: {subs.group(1)}" if subs else "")]
    if age > 3: lines.append("канал молчит - трафик из посевов приходит в тишину")
    return (light, "Наш канал", lines)

# ---------- Закупка и бюджет (BUDGET.md) ----------
def block_budget():
    p = ROOT / "BUDGET.md"
    if not p.exists(): return (N, "Закупка и бюджет", ["BUDGET.md не найден"])
    month = TODAY.strftime("%Y-%m")
    names = {"09": "Сентябрь", "10": "Октябрь", "11": "Ноябрь"}
    sec = re.split(r"^## ", p.read_text(encoding="utf-8"), flags=re.M)
    cur = next((s for s in sec if s.startswith(names.get(TODAY.strftime('%m'), '???'))), "")
    paid = sum(int(m) for m in re.findall(r"^- (\d+) · оплачено", cur, re.M))
    appr = sum(int(m) for m in re.findall(r"^- (\d+) · одобрено", cur, re.M))
    frame = 30000
    window = (datetime.date(2026, 9, 26) - TODAY).days
    light = Y if appr > 0 else G
    lines = [f"оплачено месяцем: ${paid:,} · одобрено и не потрачено: ${appr:,} · рамка ${frame:,}",
             f"до края окна набора (26.09): {window} дн."]
    if appr > 0: lines.append("одобренные деньги стоят - закупка ждёт броней Жени")
    return (light, "Закупка и бюджет", lines)

# ---------- Финансы (FIN) ----------
def block_fin():
    st = yt_states("FIN", 100)
    if st is None: return (N, "Финансы", ["нет данных: YouTrack недоступен"])
    open_ = st.get("Submitted", 0)
    return (Y if open_ > 2 else G, "Финансы", [f"открытых заявок на оплату: {open_}"])

# ---------- Ручные блоки (FRONT.md) ----------
def manual_blocks():
    p = ROOT / "FRONT.md"
    if not p.exists(): return []
    txt = p.read_text(encoding="utf-8")
    out = []
    for sec in re.split(r"^## ", txt, flags=re.M)[1:]:
        title = sec.splitlines()[0].strip()
        items = []
        for m in re.finditer(r"^- (\d{4}-\d{2}-\d{2}) · (.+)$", sec, re.M):
            age = (TODAY - datetime.date.fromisoformat(m.group(1))).days
            items.append((age, m.group(2)))
        if not items: continue
        worst = max(a for a, _ in items)
        light = R if worst >= 7 else (Y if worst >= 3 else G)
        lines = [f"{'‼' if a >= 7 else '·'} {t} - {a} дн." for a, t in sorted(items, reverse=True)]
        out.append((light, title, lines))
    return out

def main():
    print(f"КАРТА ФРОНТА · {TODAY.strftime('%d.%m.%Y')}")
    print("=" * 64)
    blocks = [block_sales(), block_leads(), block_channel(), block_budget(), block_fin()] + manual_blocks()
    reds = [t for l, t, _ in blocks if l == R]
    for light, title, lines in blocks:
        print(f"\n{light} {title}")
        for ln in lines: print(f"   {ln}")
    print("\n" + "=" * 64)
    print(("ГОРИТ: " + ", ".join(reds)) if reds else "Красных блоков нет.")

if __name__ == "__main__":
    main()
