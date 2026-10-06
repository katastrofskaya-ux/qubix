#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сверка ведомости оплат: что оплачено, что вышло, чего не хватает.

    scripts/vedomost.py             # три проверки за последние 30 дней
    scripts/vedomost.py --days 60   # шире окно
    scripts/vedomost.py --quiet     # только строки, требующие действия

Зачем: оплаты живут комментариями в задачах CONTENT/MARKETING, а ведомость —
в BUDGET.md. Между ними легко потерять строку. Скрипт сводит три вещи:

1. **Оплата есть в трекере, строки в ведомости нет.** Ищет ссылки на
   транзакции в телах и комментариях задач и сверяет с BUDGET.md по началу
   хеша. Это главная проверка: она ловит новую оплату в день, когда Женя или
   Kit о ней отписались.
2. **Оплачено, а факта выхода нет.** Для листингов факт выхода — ссылка на
   карточку в задаче приёмки (CONTENT-40); для посевов — строка про выход
   в самой задаче. Пока выхода нет, ноль регистраций по коду площадки
   означает «ещё не вышло», а не «не сработало», и в замер такую строку
   брать нельзя.
3. **Рамка месяца.** Сколько оплачено и согласовано против $30 000.

Только чтение: ни YouTrack, ни BUDGET.md скрипт не правит — печатает, что
дописать руками. Нужна переменная окружения YOUTRACK_API_TOKEN.
"""
import argparse, datetime, json, os, re, sys, urllib.parse, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUDGET = os.path.join(ROOT, "BUDGET.md")
BASE = os.environ.get("YOUTRACK_URL", "https://team.qubix.capital")
PRIEMKA = "CONTENT-40"          # задача приёмки листингов: площадка → ссылка
MONTHS = {9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь",
          1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
          5: "Май", 6: "Июнь", 7: "Июль", 8: "Август"}
# Ссылки приходят в двух видах: tronscan.org/transaction/… и tronscan.org/#/transaction/…
# Вторую форму прежняя регулярка не ловила — 16.09 из-за этого мимо ведомости
# прошли три оплаты Кита на 2 400 USDT.
TX = re.compile(r"tronscan\.org/(?:#/)?transaction/([0-9a-f]{64})")
# «950$», «$950», «2 950$» — сумма рядом со словом об оплате.
SUM = re.compile(r"(\d[\d  ]{0,9})\s?\$|\$\s?(\d[\d  ]{0,9})"
                 r"|(\d[\d  ]{0,9})\s?(?:usdt|USDT)")


def yt(path, **params):
    """GET к YouTrack. Возвращает None, если токена нет или запрос не прошёл."""
    token = os.environ.get("YOUTRACK_API_TOKEN")
    if not token:
        return None
    url = f"{BASE}/api/{path}"
    if path.endswith("/comments") and "$top" not in params:
        params["$top"] = 5000  # YouTrack по умолчанию отдаёт 42 записи
    if params:
        url += "?" + urllib.parse.urlencode(params)
    r = subprocess.run(["curl", "-sS", "--max-time", "40",
                        "-H", f"Authorization: Bearer {token}",
                        "-H", "Accept: application/json", url],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def issue_text(idr):
    """Тело задачи плюс все комментарии одной строкой."""
    d = yt(f"issues/{idr}", fields="description")
    cs = yt(f"issues/{idr}/comments", fields="text")
    parts = [(d or {}).get("description") or ""]
    parts += [(c.get("text") or "") for c in (cs or [])]
    return "\n".join(parts)


def budget_rows():
    """Строки ведомости текущего месяца плюс ВСЕ известные транзакции файла.

    Транзакции собираются по всему BUDGET.md, а не по текущему месяцу: иначе
    сверка каждый раз поднимала бы августовские оплаты и внутренние переводы
    как «пропущенные». Строки для рамки месяца — только текущего.
    """
    month = f"{MONTHS[datetime.date.today().month]} {datetime.date.today().year}"
    rows, cur, all_tx = [], None, set()
    if not os.path.exists(BUDGET):
        return month, rows, all_tx
    for raw in open(BUDGET, encoding="utf-8"):
        line = raw.strip()
        m = re.match(r"## (\S+ \d{4}) · бюджет (\d+)", line)
        if m:
            cur = m.group(1)
            continue
        if line.startswith("## "):
            cur = None
            continue
        all_tx.update(re.findall(r"tx ([0-9a-f]{6,})", line))
        m = re.match(r"- (?:(\S+) · )?(\d+) · (\S+) · (.*)", line)
        if m and cur == month:
            tx = re.search(r"· tx ([0-9a-f]{6,})", m.group(4))
            rows.append({"when": m.group(1) or "", "sum": int(m.group(2)),
                         "state": m.group(3), "what": m.group(4),
                         "tx": tx.group(1) if tx else ""})
    return month, rows, all_tx


def find_payments(days):
    """Транзакции из задач, тронутых за последние N дней: tx → (задача, сумма)."""
    since = datetime.date.today() - datetime.timedelta(days=days)
    found = {}
    for proj in ("CONTENT", "MARKETING"):
        issues = yt("issues", query=f"project: {proj} updated: {since:%Y-%m-%d} .. Today",
                    **{"$top": "100", "fields": "idReadable,summary"})
        for i in issues or []:
            idr = i["idReadable"]
            text = issue_text(idr)
            lines = text.split("\n")
            for n, line in enumerate(lines):
                for h in TX.findall(line):
                    if h in found:
                        continue
                    # Сумма и ссылка часто стоят на РАЗНЫХ строках: Kit пишет
                    # «оплачено 1350 usdt:» и ссылку следующей строкой. Поэтому
                    # ищем сумму в окне вокруг строки с транзакцией, а не в ней.
                    window = " ".join(lines[max(0, n - 2):n + 2])
                    m = SUM.search(window)
                    amount = 0
                    if m:
                        amount = int(re.sub(r"\D", "",
                                            m.group(1) or m.group(2) or m.group(3)))
                    found[h] = (idr, i.get("summary", ""), amount)
    return found


def priemka_links():
    """Площадки из задачи приёмки: название → есть ли ссылка на карточку."""
    d = yt(f"issues/{PRIEMKA}", fields="description")
    out = {}
    for line in ((d or {}).get("description") or "").split("\n"):
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or cells[0] in ("Площадка", "---"):
            continue
        out[cells[0]] = bool(re.search(r"https?://", cells[2]))
    return out


def hdr(t):
    print(f"\n{t}\n" + "─" * len(t))


def main():
    p = argparse.ArgumentParser(description="Сверка ведомости оплат")
    p.add_argument("--days", type=int, default=30, help="окно поиска оплат, дней (по умолчанию 30)")
    p.add_argument("--quiet", action="store_true", help="только то, что требует действия")
    args = p.parse_args()

    if not os.environ.get("YOUTRACK_API_TOKEN"):
        sys.exit("нужна переменная окружения YOUTRACK_API_TOKEN")

    month, rows, known = budget_rows()
    today = datetime.date.today()
    todo = 0

    # 1. Оплата в трекере есть, строки в ведомости нет.
    pays = find_payments(args.days)
    missing = [(h, v) for h, v in pays.items()
               if not any(h.startswith(k) for k in known)]
    if missing:
        todo += len(missing)
        hdr(f"Оплата в трекере есть, строки в ведомости нет — {len(missing)}")
        for h, (idr, summ, amount) in sorted(missing, key=lambda x: x[1][0]):
            money = f"${amount:,}".replace(",", " ") if amount else "сумма не распознана"
            print(f"  {idr:<13} {money:<22} tx {h[:8]}  {summ[:52]}")
        print("  → допишите строку в BUDGET.md: дата оплаты · сумма · оплачено · что · задача · tx")
        print("  ⚠ сумма берётся из текста рядом со ссылкой — в плотном\n    комментарии может подхватиться соседнее число. Перед записью в\n    ведомость сверьте по самой ссылке.")
    elif not args.quiet:
        hdr("Оплаты и ведомость")
        print(f"  Расхождений нет: все транзакции за {args.days} дн. стоят в ведомости.")

    # 2. Оплачено, а факта выхода нет.
    links = priemka_links()
    if links:
        no_link = [n for n, ok in links.items() if not ok]
        if no_link:
            todo += len(no_link)
            hdr(f"Оплачено, факта выхода нет — {len(no_link)}")
            for n in no_link:
                print(f"  {n}")
            print(f"  → ссылка на карточку ставится в {PRIEMKA}; пока её нет,")
            print("    ноль регистраций по коду площадки в замер не берётся.")
        elif not args.quiet:
            hdr("Приёмка листингов")
            print(f"  Все {len(links)} площадок со ссылками на карточку.")

    # 3. Рамка месяца.
    paid = sum(r["sum"] for r in rows if r["state"] == "оплачено")
    appr = sum(r["sum"] for r in rows if r["state"] == "одобрено")
    if not args.quiet or paid + appr > 30000:
        hdr(f"Рамка месяца · {month}")
        f = lambda n: f"{n:,}".replace(",", " ")
        print(f"  оплачено {f(paid)} · согласовано и не потрачено {f(appr)} · "
              f"свободно {f(30000 - paid - appr)} из 30 000")
        if paid + appr > 30000:
            print("  ‼ занято больше рамки — проверьте состав строк")

    if args.quiet and not todo:
        return
    print(f"\n  Проверено {today:%d.%m.%Y}. Скрипт только читает — правки в BUDGET.md руками.\n")


if __name__ == "__main__":
    main()
