#!/usr/bin/env python3
"""Генератор инвойсов консультанта — по правилам владельца (23.09.2026):

- обычный белый лист A4, PDF, без бланка, без подписей и печатей;
- номер инвойса = дата + порядковый номер на эту дату: 2026-08-01-1;
- между датой инвойса и датой оплаты — несколько дней, ни одна дата не на выходных;
- реквизиты получения — кошелёк, тот самый, что указан в договоре;
- суммы и даты — ровно те, что реально прошли (чеки в задачах FIN).

Запуск: python3 drafts/invoice-gen.py  → drafts/invoices/*.html
PDF: см. команду в конце файла.

Поля [ЗАПОЛНИТЬ] берутся из договора — их у агента нет намеренно.
"""
import datetime, pathlib, html

OUT = pathlib.Path(__file__).parent / "invoices"
OUT.mkdir(exist_ok=True)

CONSULTANT = {
    "name": "Anastasia Voitenko",
    "address": "[ЗАПОЛНИТЬ — адрес консультанта, как в договоре]",
    "email": "anastasiavoitenko@qubix.pro",
}
COMPANY = {
    "name": "YARD TECH S.A.S.",
    "address": "[ЗАПОЛНИТЬ — юридический адрес компании из договора, Уругвай]",
    "reg": "[ЗАПОЛНИТЬ — регистрационный номер / RUT, если есть в договоре]",
    "contact": "legal@qubix.pro",
}
CONTRACT = "Consulting Services Agreement dated 27 July 2026"
WALLET = "[ЗАПОЛНИТЬ — кошелёк из договора, сеть и адрес дословно]"
SERVICES = ("Consulting services under Schedule 1 of the Agreement: promotion and media, "
            "partnerships, public representation and events, sales management, "
            "HR and operational management of the commercial team.")

# Факты по выплатам — из задач FIN (чеки там). Дата инвойса — рабочий день за
# несколько дней до оплаты. Первый инвойс не может быть раньше даты договора.
INVOICES = [
    dict(inv_date="2026-07-27", pay_date="2026-07-28", seq=1,
         period="July 2026 (from 27 July) — advance payment",
         lines=[("Advance payment for consulting services, July–August 2026", 2500.00)],
         paid_ref="FIN-2 · 28.07.2026 · $100 + $2 400 USDT (ERC-20) · etherscan 0x922d…3dec8, 0x0fab…7abc",
         note="Договор подписан 27.07, аванс уплачен 28.07 — здесь между инвойсом и оплатой один день, и это правда, её не подгоняем."),
    dict(inv_date="2026-08-24", pay_date="2026-08-27", seq=1,
         period="August 2026",
         lines=[("Consulting services, August 2026", 3900.00)],
         paid_ref="FIN-7 · 27.08.2026 · $3 900 USDT (ERC-20) · etherscan 0x6ad8…4cacc",
         note=""),
    dict(inv_date="2026-09-22", pay_date="2026-09-25", seq=1,
         period="September 2026 (second part) and advance for October 2026",
         lines=[("Consulting services, September 2026 — second part", 2500.00),
                ("Advance payment for consulting services, October 2026", 2500.00),
                ("Less: Lisbon travel tickets paid by the Company (FIN-6), €599 at 1.14", -681.00)],
         paid_ref="FIN-12 · к оплате до 25.09.2026 · 4 319 USDT (ERC-20) · аппрув владельца 23.09",
         note="Сумма 4 319 — как в FIN-12: 5 000 минус 599 € по курсу 1,14. Оплата ещё не прошла; после оплаты в письмо-подтверждение ставится хеш."),
]

def weekday(d):
    return datetime.date.fromisoformat(d).strftime("%A")

def check(inv):
    a, b = datetime.date.fromisoformat(inv["inv_date"]), datetime.date.fromisoformat(inv["pay_date"])
    problems = []
    if a.weekday() >= 5: problems.append(f"дата инвойса {a} — выходной")
    if b.weekday() >= 5: problems.append(f"дата оплаты {b} — выходной")
    if (b - a).days < 1: problems.append("оплата раньше или в день инвойса")
    if a < datetime.date(2026, 7, 27): problems.append("инвойс раньше даты договора")
    return problems

TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Invoice {number}</title>
<style>
@page {{ size: A4; margin: 22mm 20mm; }}
body {{ font-family: Arial, Helvetica, sans-serif; font-size: 11pt; color: #000; background:#fff; }}
h1 {{ font-size: 20pt; margin: 0 0 4mm; letter-spacing: .5px; }}
.meta td {{ padding: 1mm 8mm 1mm 0; vertical-align: top; }}
.parties {{ display: flex; gap: 20mm; margin: 8mm 0; }}
.parties div {{ flex: 1; }}
.parties h3 {{ font-size: 9.5pt; text-transform: uppercase; color: #555; margin: 0 0 2mm; }}
table.lines {{ width: 100%; border-collapse: collapse; margin-top: 6mm; }}
table.lines th, table.lines td {{ border-bottom: 1px solid #999; padding: 2.5mm 2mm; text-align: left; }}
table.lines th {{ font-size: 9.5pt; text-transform: uppercase; color: #555; }}
table.lines td.n, table.lines th.n {{ text-align: right; white-space: nowrap; }}
table.lines tr.total td {{ border-bottom: none; border-top: 2px solid #000; font-weight: bold; }}
.pay {{ margin-top: 8mm; }}
.pay h3 {{ font-size: 9.5pt; text-transform: uppercase; color: #555; margin: 0 0 2mm; }}
.small {{ font-size: 9.5pt; color: #333; margin-top: 10mm; }}
</style></head><body>
<h1>INVOICE</h1>
<table class="meta">
<tr><td>Invoice No.</td><td><b>{number}</b></td></tr>
<tr><td>Invoice date</td><td>{inv_date_h}</td></tr>
<tr><td>Due date</td><td>{pay_date_h}</td></tr>
<tr><td>Basis</td><td>{contract}</td></tr>
<tr><td>Service period</td><td>{period}</td></tr>
</table>
<div class="parties">
<div><h3>From (Consultant)</h3>{c_name}<br>{c_addr}<br>{c_email}</div>
<div><h3>To (Client)</h3>{k_name}<br>{k_addr}<br>{k_reg}<br>{k_contact}</div>
</div>
<p>{services}</p>
<table class="lines">
<thead><tr><th>Description</th><th class="n">Amount, USD</th></tr></thead>
<tbody>{rows}
<tr class="total"><td>Total due</td><td class="n">{total}</td></tr>
</tbody></table>
<div class="pay"><h3>Payment details</h3>
Currency: USDT, in the amount equivalent to the total above.<br>
Wallet (as specified in the Agreement): <b>{wallet}</b><br>
Payment terms: within the term set by the Agreement.</div>
<p class="small">Issued by the Consultant to the Client under the Agreement. No signature or stamp required.</p>
</body></html>"""

def fmt_date(d):
    dt = datetime.date.fromisoformat(d)
    return dt.strftime("%d %B %Y")

def money(x):
    s = f"{abs(x):,.2f}"
    return f"−{s}" if x < 0 else s

made = []
for inv in INVOICES:
    number = f"{inv['inv_date']}-{inv['seq']}"
    rows = "".join(f"<tr><td>{html.escape(d)}</td><td class='n'>{money(a)}</td></tr>" for d, a in inv["lines"])
    total = sum(a for _, a in inv["lines"])
    page = TEMPLATE.format(
        number=number, inv_date_h=fmt_date(inv["inv_date"]), pay_date_h=fmt_date(inv["pay_date"]),
        contract=CONTRACT, period=html.escape(inv["period"]),
        c_name=CONSULTANT["name"], c_addr=CONSULTANT["address"], c_email=CONSULTANT["email"],
        k_name=COMPANY["name"], k_addr=COMPANY["address"], k_reg=COMPANY["reg"], k_contact=COMPANY["contact"],
        services=html.escape(SERVICES), rows=rows, total=money(total), wallet=WALLET)
    path = OUT / f"invoice-{number}.html"
    path.write_text(page, encoding="utf-8")
    probs = check(inv)
    made.append((number, inv["inv_date"], weekday(inv["inv_date"]), inv["pay_date"], weekday(inv["pay_date"]), total, probs, inv["paid_ref"], inv["note"]))

print("Сгенерировано в", OUT)
for n, a, wa, b, wb, t, p, ref, note in made:
    print(f"\n{n}  инвойс {a} ({wa}) → оплата {b} ({wb})  итого ${t:,.2f}")
    print("  оплата по факту:", ref)
    if p: print("  ⚠️", "; ".join(p))
    if note: print("  ·", note)

print("""
PDF (белый лист A4, без бланка) — встроенным Chromium:
  CHR=$(find /opt/pw-browsers -maxdepth 3 -type f -name chrome | head -1)
  for f in drafts/invoices/*.html; do
    "$CHR" --headless=new --no-sandbox --disable-gpu --no-pdf-header-footer \\
      --print-to-pdf="$PWD/${f%.html}.pdf" "file://$PWD/$f"
  done
""")
