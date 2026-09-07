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


def build():
    blocks = []

    l, _, lines = front.block_sales()
    blocks.append(block("sales", 1, l, "Продажи", lines))

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
    blocks.append(block("mk", 7, front.Y, "Маркетинг и операционка",
                        [f"открыто: MARKETING {len(mk)} · OP {len(op)} · HR {len(hr)}"],
                        mk + op + hr))

    for i, sec in enumerate(("Подрядчики", "Согласования", "Риски")):
        items = manual_items(sec)
        if not items:
            continue
        worst = max((TODAY - datetime.date.fromisoformat(it["updated"])).days for it in items)
        l = front.R if worst >= 7 else (front.Y if worst >= 3 else front.G)
        titles = {"Подрядчики": "Подрядчики", "Согласования": "Согласования у шефа", "Риски": "Риски"}
        blocks.append(block(f"man{i}", 8 + i, l, titles[sec],
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
