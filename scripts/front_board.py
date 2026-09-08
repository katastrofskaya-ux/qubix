#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Выгрузка данных для живой доски «Карта фронта» (артефакт с базой).

Собирает те же блоки, что scripts/front.py, плюс все открытые задачи YouTrack
по блокам, и пишет JSON-документы в каталог --out:

    <out>/meta.json                — {updated_at, reds}
    <out>/blocks/<id>.json        — {title, light, order, metrics, items}

Дальше эти файлы заливаются в базу артефакта (Artifact write_db, batch):
блоки — в коллекцию blocks, meta — документом board/meta. Отметки-галочки
живут в коллекции checks и при обновлении блоков НЕ трогаются.

Источники и деградация — как у front.py: чего нет, то «нет данных».
"""
import os, re, json, sys, hashlib, datetime, pathlib, argparse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import front  # noqa: E402  (блоки-светофоры переиспользуем оттуда)

TODAY = datetime.date.today()
YT_URL = "https://team.qubix.capital"

LIGHTS = {front.R: "red", front.Y: "yellow", front.G: "green", front.N: "gray"}

# DEV-задачи, от которых зависит коммерция (правится руками по мере появления)
DEV_TRACKED = ["DEV-2508", "DEV-2621", "DEV-2622", "DEV-2625"]

# Партнёрства и события — курируемый список (правится руками)
PARTNER_IDS = {"MARKETING-81", "MARKETING-66", "MARKETING-65", "MARKETING-73",
               "MARKETING-78", "MARKETING-13"}

# CONTENT-задачи нашего TG-канала — остальное CONTENT уходит в закупку/контент
TG_CHANNEL_IDS = {"CONTENT-41", "CONTENT-44", "CONTENT-43", "CONTENT-42", "CONTENT-8"}


def yt_issues(query, top=100):
    import urllib.parse
    data = front.yt("/issues?query=" + urllib.parse.quote(query) + f"&$top={top}"
                    "&fields=idReadable,summary,updated,"
                    "customFields(name,value(name,fullName,login))")
    if data is None:
        return None
    items = []
    for i in data:
        state = assignee = ""
        for cf in i.get("customFields", []):
            v = cf.get("value")
            if cf.get("name") == "State" and isinstance(v, dict):
                state = v.get("name") or ""
            if cf.get("name") == "Assignee" and isinstance(v, dict):
                assignee = v.get("fullName") or v.get("login") or ""
        items.append({
            "id": i["idReadable"],
            "text": i["summary"],
            "url": f"{YT_URL}/issue/{i['idReadable']}",
            "tag": state,
            "who": assignee,
            "updated": (i.get("updated") or 0),
        })
    items.sort(key=lambda x: -x["updated"])
    for it in items:
        it["updated"] = datetime.date.fromtimestamp(it["updated"] / 1000).isoformat() if it["updated"] else ""
    return items


def manual_items(section_title):
    """Строки FRONT.md как items с устойчивыми id (hash текста)."""
    p = front.ROOT / "FRONT.md"
    if not p.exists():
        return []
    txt = p.read_text(encoding="utf-8")
    for sec in re.split(r"^## ", txt, flags=re.M)[1:]:
        if not sec.splitlines()[0].strip().startswith(section_title):
            continue
        out = []
        for m in re.finditer(r"^- (\d{4}-\d{2}-\d{2}) · (.+)$", sec, re.M):
            age = (TODAY - datetime.date.fromisoformat(m.group(1))).days
            h = hashlib.md5(m.group(2).encode()).hexdigest()[:10]
            out.append({"id": f"m-{h}", "text": m.group(2), "url": "",
                        "tag": f"{age} дн.", "who": "", "updated": m.group(1),
                        "hot": age >= 7})
        return out
    return []


def block(bid, order, light, title, metrics, items=None):
    return bid, {"title": title, "order": order, "light": LIGHTS.get(light, "gray"),
                 "metrics": metrics, "items": items or [], "as_of": TODAY.isoformat()}


def source_down(doc):
    """Источник недоступен (нет куки/токена) — такой блок не пишем поверх
    последнего живого среза: на доске останется старый с его датой as_of."""
    m = " ".join(doc["metrics"])
    return doc["light"] == "gray" and ("нет данных" in m or "не ответила" in m or "недоступен" in m)


def sales_items():
    """Поимённый список: истёкшие → истекающие → застрявшие без лицензии.
    Почты клиентов уходят только в приватную базу доски, в репозиторий — нет."""
    cookie = os.environ.get("ADMIN_QUBIX_COOKIE")
    if not cookie:
        return []
    rows, seen = [], set()
    for off in (0, 100, 200, 300):
        out = front.curl(f"https://admin.qubix.pro/api/admin/v1/customers?limit=100&offset={off}",
                         headers=["accept: application/json"], cookie=cookie)
        try:
            batch = json.loads(out).get("rows", [])
        except Exception:
            return []
        new = [r for r in batch if r["id"] not in seen]
        if not new:
            break
        for r in new:
            seen.add(r["id"]); rows.append(r)
    tech = re.compile(r"@(qubix\.pro|qubix\.capital|qubix\.dev|example\.com|ex\.com|test\.com|x\.com)$|\.test$|^pentest")
    real = [r for r in rows if not tech.search((r.get("email") or "").lower())]

    # карточки SALES: «Лид #228 — …» → ссылка по номеру клиента или почте
    by_num, by_mail = {}, {}
    for card in yt_issues("project: SALES", 400) or []:
        m = re.search(r"#(\d+)", card["text"])
        if m:
            by_num.setdefault(m.group(1), card["url"])
        e = re.search(r"[\w.+-]+@[\w.-]+", card["text"])
        if e:
            by_mail.setdefault(e.group(0).lower(), card["url"])

    def last_touch(card_url):
        """Дата последнего человеческого коммента в карточке (не бот) —
        чтобы доска не предлагала писать тому, кого уже касались."""
        iid = card_url.rsplit("/", 1)[-1]
        cs = front.yt(f"/issues/{iid}/comments?fields=created,author(fullName)") or []
        human = [c["created"] for c in cs
                 if (c.get("author") or {}).get("fullName", "") not in ("Qubix Support", "")]
        if not human:
            return ""
        return datetime.date.fromtimestamp(max(human) / 1000).strftime("%d.%m")

    import urllib.parse
    KASANIE = ("Привет! Я Анастасия из Qubix. {date} у вашего инстанса заканчивается "
               "бесплатный месяц со всеми возможностями. Пишу заранее, чтобы вы успели "
               "забрать из него максимум.\n\n"
               "Расскажите, что успели попробовать и что зашло? Если где-то застряли — "
               "напишите прямо здесь, помогу разобраться лично.\n\n"
               "И на всякий случай: после окончания периода сервер и данные остаются "
               "вашими — доступ переходит в режим чтения, всё сохраняется. Захотите "
               "продолжить — подскажу самый простой путь.")

    def mailto(email, pu):
        date = pu.strftime("%d.%m") if pu else "скоро"
        body = KASANIE.format(date=date)
        return ("mailto:" + email + "?" + urllib.parse.urlencode(
            {"subject": "Ваш инстанс Qubix — бесплатный месяц заканчивается " + date,
             "body": body}, quote_via=urllib.parse.quote))

    items = []
    for r in real:
        pu, cr = front.d(r.get("paid_until")), front.d(r.get("created_at"))
        days = (pu - TODAY).days if pu else None
        email = r.get("email") or f"#{r['id']}"
        plan = r.get("plan_code") or ""
        # карточки нет — ведём в список клиентов админки (поиск по номеру/почте)
        card = by_num.get(str(r.get("number") or "")) or by_mail.get(email.lower())
        url = card or f"https://admin.qubix.pro/customers/{r['id']}"
        touch = last_touch(card) if card else ""
        if days is not None and -7 <= days < 0:
            items.append((0, days, {"id": f"c-{r['id']}", "text": f"{email} · {plan}",
                          "url": url, "tag": f"истекла {pu.strftime('%d.%m')}" + (f" · касание {touch}" if touch else ""), "who": f"#{r.get('number', '')}",
                          "updated": "", "hot": True, "mailto": mailto(email, pu)}))
        elif days is not None and 0 <= days <= 2:
            items.append((1, days, {"id": f"c-{r['id']}", "text": f"{email} · {plan}",
                          "url": url, "tag": f"истекает {pu.strftime('%d.%m')}" + (f" · касание {touch}" if touch else ""), "who": f"#{r.get('number', '')}",
                          "updated": "", "hot": True, "mailto": mailto(email, pu)}))
        elif cr and (TODAY - cr).days <= 3 and not r.get("license_state"):
            items.append((2, 0, {"id": f"c-{r['id']}", "text": f"{email} · рег. {cr.strftime('%d.%m')}",
                          "url": url, "tag": "без лицензии", "who": f"#{r.get('number', '')}",
                          "updated": "", "hot": False}))
    items.sort(key=lambda x: (x[0], x[1]))
    return [it for _, _, it in items]


def build():
    blocks = []

    l, _, lines = front.block_sales()
    si = sales_items()
    no_card = sum(1 for i in si if not i["url"])
    if no_card:
        lines = lines + [f"⚠ у {no_card} из {len(si)} в списке нет карточки в SALES — "
                         "ссылка ведёт в никуда, работать из админки (дырка DEV-2625)"]
    blocks.append(block("sales", 1, l, "Продажи", lines, si))

    l, _, lines = front.block_leads()
    leads = yt_issues("project: SALES #Unresolved State: New", 200) or []
    blocks.append(block("leads", 2, l, "Очередь лидов", lines, leads))

    l, _, lines = front.block_traffic()
    dev = yt_issues(" ".join(f"issue id: {i}" for i in DEV_TRACKED)) or []
    blocks.append(block("traffic", 3, l, "Трафик по каналам",
                        lines + ["зависимости от разработки — ниже списком"], dev))

    l, _, lines = front.block_channel()
    content = yt_issues("project: CONTENT #Unresolved", 100)
    tg = [i for i in (content or []) if i["id"] in TG_CHANNEL_IDS]
    rest = [i for i in (content or []) if i["id"] not in TG_CHANNEL_IDS]
    blocks.append(block("channel", 4, l, "Наш TG-канал", lines, tg))

    l, _, lines = front.block_budget()
    blocks.append(block("procure", 5, l, "Закупка и контент", lines, rest))

    l, _, lines = front.block_fin()
    fin = yt_issues("project: FIN #Unresolved", 50) or []
    blocks.append(block("fin", 6, l, "Финансы", lines, fin))

    mk = yt_issues("project: MARKETING #Unresolved", 100) or []
    op = yt_issues("project: OP #Unresolved", 50) or []
    hr = yt_issues("project: HR #Unresolved", 50) or []
    partner = [i for i in mk if i["id"] in PARTNER_IDS] + \
              [i for i in fin if i["id"] == "FIN-6"]
    mk_rest = [i for i in mk if i["id"] not in PARTNER_IDS]
    blocks.append(block("mk", 7, front.Y if mk_rest else front.G, "Маркетинг",
                        [f"открытых задач: {len(mk_rest)} (свежие сверху)"], mk_rest))
    blocks.append(block("partner", 8, front.Y if partner else front.G,
                        "Партнёрства и события",
                        ["AffBuddha, AdsPower, VK WS, Hetzner, Broconf, Лиссабон"], partner))
    blocks.append(block("op", 9, front.Y if op else front.G, "Операционка и отчётность",
                        [f"открытых задач: {len(op)} · месячный отчёт по договору — до 5-го числа"], op))
    blocks.append(block("hr", 10, front.Y if hr else front.G, "Найм и команда",
                        [f"открытых задач: {len(hr)}"], hr))

    for i, sec in enumerate(("Подрядчики", "Согласования", "Риски")):
        items = manual_items(sec)
        if not items:
            continue
        worst = max((TODAY - datetime.date.fromisoformat(it["updated"])).days for it in items)
        l = front.R if worst >= 7 else (front.Y if worst >= 3 else front.G)
        titles = {"Подрядчики": "Подрядчики", "Согласования": "Согласования у шефа", "Риски": "Риски"}
        blocks.append(block(f"man{i}", 11 + i, l, titles[sec],
                            [f"пунктов: {len(items)}, самому старому {worst} дн."], items))

    return blocks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    (out / "blocks").mkdir(parents=True, exist_ok=True)
    blocks = build()
    reds = [b["title"] for _, b in blocks if b["light"] == "red"]
    now = datetime.datetime.now(datetime.timezone.utc)
    (out / "meta.json").write_text(json.dumps(
        {"updated_at": now.isoformat(timespec="minutes"), "reds": reds},
        ensure_ascii=False), encoding="utf-8")
    written = 0
    for bid, doc in blocks:
        if source_down(doc):
            print(f"  ПРОПУСК {bid}: источник недоступен, на доске остаётся прошлый срез")
            continue
        (out / "blocks" / f"{bid}.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        written += 1
    print(f"OK: {written} блоков → {out}")
    for bid, doc in blocks:
        if not source_down(doc):
            print(f"  {doc['light']:6} {bid:8} {doc['title']} · items: {len(doc['items'])}")


if __name__ == "__main__":
    main()
