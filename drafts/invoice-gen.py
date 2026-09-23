#!/usr/bin/env python3
"""Генератор инвойсов консультанта — по правилам владельца (23.09.2026):

- обычный белый лист A4, PDF, без бланка, без подписей и печатей;
- номер инвойса = дата + порядковый номер на эту дату: 2026-09-24-1;
- ⛔ задним числом не датировать (admin FIN-13, 23.09 21:34): дата выставления — сегодняшняя,
  период услуг и дата уже полученного платежа — отдельными строками внутри;
- реквизиты получения — Designated Wallet из договора (п. 4.8);
- суммы и даты — ровно те, что реально прошли (чеки в задачах FIN).

Запуск: python3 drafts/invoice-gen.py  → drafts/invoices/*.html
PDF: см. команду в конце файла.

Поля [ЗАПОЛНИТЬ] берутся из договора — их у агента нет намеренно.
"""
import datetime, pathlib, html

OUT = pathlib.Path(__file__).parent / "invoices"
OUT.mkdir(exist_ok=True)

CONSULTANT = {
    "name": "Anastassiya Voitenko",
    # Адрес — личные данные, в репозиторий не идёт: лежит в drafts/invoices/.consultant-address (gitignore)
    "address": (pathlib.Path(__file__).parent / "invoices" / ".consultant-address").read_text().strip()
               if (pathlib.Path(__file__).parent / "invoices" / ".consultant-address").exists() else "[ЗАПОЛНИТЬ — адрес консультанта, как в договоре]",
    "email": "Katastrofskaya@gmail.com",  # контакт консультанта по договору, п. 9.2
}
COMPANY = {
    "name": "YARD TECH S.A.S.",
    "address": "Potosi 1615, Montevideo, Oriental Republic of Uruguay",
    "reg": "RUT No. 219861600014, National Registry of Commerce No. 7718",
    "contact": "legal@qubix.pro",
}
CONTRACT = "Consulting Services Agreement dated 27 July 2026"
# Designated Wallet по договору, п. 4.8 (ERC-20). Туда прошли FIN-2 и FIN-7.
# Только оплаченные выплаты; неоплаченное (FIN-12) в пакет не идёт.
WALLET_1 = "USDT (ERC-20) 0xB7867007bDfe0e6c9Ff718489BD52604218fA3b7 (Designated Wallet, Clause 4.8)"
SERVICES = ("Consulting services under Schedule 1 of the Agreement: promotion and media, "
            "partnerships, public representation and events, sales management, "
            "HR and operational management of the commercial team.")

# Факты по выплатам — из задач FIN (чеки там). Дата инвойса — рабочий день за
# несколько дней до оплаты. Первый инвойс не может быть раньше даты договора.
INVOICES = [
    dict(inv_date="2026-09-24", seq=1,
         period="27–31 July 2026",
         lines=[("Consulting services under the Agreement, 27–31 July 2026", 2500.00)],
         paid="Paid on 28.07.2026 — USDT (ERC-20) to the Designated Wallet: 100 USDT (tx 0x922d980d75b79691bb0eec654cf26e4e3becaf1ce42360d76a58eeb1cfc3dec8) and 2,400 USDT (tx 0x0fabbb88c12f906e8fda60afeabfc8fca2d813d796b08cd016fcd6cb2da47abc)",
         paid_ref="FIN-2 · 28.07.2026 · $100 + $2 400 USDT (ERC-20)", note=""),
    dict(inv_date="2026-09-24", seq=2,
         period="August 2026",
         lines=[("Consulting services under the Agreement, August 2026 (monthly fee, Clause 4.2)", 5000.00),
                ("Less: set-off, as agreed by the Parties, of the unspent balance of funds provided by the Company for business trips to Moscow, August 2026 (RUB 92,734.53 at 84.2820, per the Company's calculation of 27.08.2026)", -1100.00)],
         paid="Paid on 27.08.2026 — 3,900 USDT (ERC-20) to the Designated Wallet (tx 0x6ad8d1a8b121f7ef67bdb29576fa8039d70a864d119b181fb457b379bc74cacc)",
         paid_ref="FIN-7 · 27.08.2026 · $3 900 USDT (ERC-20)", note=""),
]

def weekday(d):
    return datetime.date.fromisoformat(d).strftime("%A")

def check(inv):
    a = datetime.date.fromisoformat(inv["inv_date"])
    problems = []
    if a.weekday() >= 5: problems.append(f"дата инвойса {a} — выходной")
    today_msk = (datetime.datetime.utcnow() + datetime.timedelta(hours=3)).date()
    if a != today_msk: problems.append(f"дата инвойса не сегодняшняя по МСК ({today_msk}) — задним числом нельзя")
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
<tr><td>Basis</td><td>{contract}</td></tr>
<tr><td>Service period</td><td>{period}</td></tr>
<tr><td>Payment status</td><td>{paid}</td></tr>
</table>
<div class="parties">
<div><h3>From (Consultant)</h3>{c_name}<br>{c_addr}<br>{c_email}</div>
<div><h3>To (Company)</h3>{k_name}<br>{k_addr}<br>{k_reg}<br>{k_contact}</div>
</div>
<p>{services}</p>
<table class="lines">
<thead><tr><th>Description</th><th class="n">Amount, USD</th></tr></thead>
<tbody>{rows}
<tr class="total"><td>Total due</td><td class="n">{total}</td></tr>
</tbody></table>
<div class="pay"><h3>Payment details</h3>
Wallet: <b>{wallet}</b><br>
Settlement in USDT at 1 USDT = 1 USD (Clause 4.7 of the Agreement). This invoice documents a payment already received; no further payment is due under it.</div>
<p class="small">Issued by the Consultant to the Company under the Agreement on the date stated above. No signature or stamp required.</p>
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
        number=number, inv_date_h=fmt_date(inv["inv_date"]), paid=html.escape(inv["paid"]),
        contract=CONTRACT, period=html.escape(inv["period"]),
        c_name=CONSULTANT["name"], c_addr=CONSULTANT["address"], c_email=CONSULTANT["email"],
        k_name=COMPANY["name"], k_addr=COMPANY["address"], k_reg=COMPANY["reg"], k_contact=COMPANY["contact"],
        services=html.escape(SERVICES), rows=rows, total=money(total), wallet=WALLET_1)
    path = OUT / f"invoice-{number}.html"
    path.write_text(page, encoding="utf-8")
    probs = check(inv)
    made.append((number, inv["inv_date"], weekday(inv["inv_date"]), total, probs, inv["paid_ref"], inv["note"]))

print("Сгенерировано в", OUT)
for n, a, wa, t, p, ref, note in made:
    print(f"\n{n}  инвойс {a} ({wa})  итого ${t:,.2f}")
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
