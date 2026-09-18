#!/usr/bin/env python3
"""Карта касаний: все живые клиенты из админки + лиды из бота без регистрации.

Читает срезы из scratchpad (all-clients.json, bot-leads.json), собирает
HTML-карту с ссылками на карточки SALES, админку, Telegram и готовым текстом
под каждого. Только чтение; ничего не отправляет.
"""
import json, sys, datetime, html

S = sys.argv[1]
OUT_HTML = sys.argv[2]
OUT_MD = sys.argv[3]
TODAY = datetime.datetime(2026, 9, 18)

clients = json.load(open(f"{S}/all-clients.json", encoding="utf-8"))
leads = json.load(open(f"{S}/bot-leads.json", encoding="utf-8"))
_promo = json.load(open(f"{S}/promo3.json", encoding="utf-8"))
_items = _promo.get("data") or _promo.get("items") or _promo
if isinstance(_items, dict): _items = list(_items.values())[0]
DISCOUNT = {str(p["code"]): p.get("discount_pct") or 0 for p in _items}

PLATFORM = {"ADHUNT": "Adhunt", "ADHUNT1": "Adhunt", "AFF_INSIDE": "Aff Inside", "AFFINSIDE": "Aff Inside",
            "CPAGRAM": "CPAgram", "CPAGRAM1": "CPAgram", "FBKILLA": "FB killa", "FBKILLA_SITE": "FB killa",
            "IGAMINGNEWS": "iGaming News", "IGAMING_NEWS": "iGaming News", "FLOWBRO": "FLOW", "FLOW": "FLOW",
            "PARTNERKIN_SITE": "Partnerkin", "PARTNEROFF_SITE": "Partneroff", "CPARIP": "CPA.RIP",
            "SYSBITRAZH": "Сысоев", "TIKTOKILLER": "TikTokiller", "VTRAFF": "V Traff", "APTEKA": "Аптека",
            "TGQUBIX": "наш канал", "ZOMBIE": "Zombie Traff", "PACAN": "Пацан", "KHOMENOK": "Хоменюк"}
SKIP = {206: "Женя (наш подрядчик)", 233: "Хоменюк (блогер, наш)", 204: "АффБудда (партнёр)",
        241: "Partnerkin — площадка под своим кодом", 244: "Partneroff — площадка под своим кодом",
        212: "OneMedia, Дима — разговор уже идёт отдельно"}
CHECK = {55: "protectedpool11 — проверить, не наша ли запись", 93: "protectedpool1 — проверить, не наша ли запись"}

RELEASE_BASE = ("Здравствуйте{name}! Анастасия, Qubix. Обещала написать, когда выйдет большой релиз — он вышел.\n\n"
                "Qubix теперь суперапп: к трекеру и витринам добавились рабочий стол, документы и таблицы прямо в панели, "
                "скрипты к рекламному кабинету и домены на своих аккаунтах. Всё по-прежнему стоит на вашем сервере.\n\n"
                "{personal}\n\n"
                "Давайте так: я подниму вам доступ заново на 30 дней, и мы за один созвон дойдём до первой связки. Когда вам удобно?")
PERSONAL = {
    78: "Помню, на чём вы тогда встали: домен нельзя было взять из другого регистратора. Это закрыто — домен, купленный где угодно, подключается к панели за пару шагов, а через панель покупается на ваших же Cloudflare и Namecheap. Вторая заминка с доступами тоже снята: установка одной командой и мастер в браузере.",
    86: "Вы тогда споткнулись о привязку домена. Сейчас это мастер в одно окно: подо что домен, свой или новый, как отдавать трафик — и он встаёт с сертификатом сам. Хочу показать вам это лично, чтобы второй раз всё прошло за десять минут.",
    84: "Вы писали, что установка на сервер тогда не пошла. С тех пор её переделали: одна команда, установщик сам проверяет сервер и говорит, что не так, обновление кнопкой с откатом. Понимаю, что вы уже на другом инструменте — предлагаю поставить Qubix рядом на тестовый сервер и сравнить на одной кампании.",
    102: "Вы говорили, что подождёте релиза — вот он. Ваш аккаунт на месте, установка занимает минут двадцать. Скажите, какой у вас сервер, и я пришлю точную последовательность под него.",
    193: "Вы ждали релиза — он вышел, и ваш месяц я готова открыть заново, чтобы вы посмотрели уже на новую версию, а не на ту, что была летом.",
    53: "Мы с вами говорили в начале сентября — тогда вы присматривались. Теперь есть на что смотреть: {впиши одну вещь под его интерес}.",
    110: "Писала вам на почту в конце августа — продублирую сюда, здесь быстрее. Ваш месяц закончился как раз перед релизом, поэтому самое интересное вы не видели. Открою заново.",
    123: "Писала вам на почту в конце августа — продублирую сюда, здесь быстрее. Ваш месяц закончился как раз перед релизом, поэтому самое интересное вы не видели. Открою заново.",
    199: "Вы спрашивали про автоматические вайтпейджи — честно, их по-прежнему нет, и обещать не буду. Зато вайтпейдж теперь заводится перетаскиванием архива или записи страницы из браузера, а серверная логика на нём пишется скриптом. Покажу за пять минут.",
}
RELEASE_LEAD = "Мы с вами переписывались в августе, вы тогда присматривались к Qubix. Пишу, как обещала: релиз вышел, и посмотреть теперь есть на что."

T_EXPIRING = ("Здравствуйте! Анастасия, Qubix. У вас {date} заканчивается пробный месяц, и я хочу успеть до этого поговорить, а не после.\n\n"
              "Расскажите, что получилось: сервер стоит, первая связка пошла? Если где-то застряли — скажите где, разберём вместе, это моя работа.\n\n"
              "Если продукт вам подошёл, переведу на постоянный тариф так, что ничего не сдвинется: тот же сервер, те же настройки, те же данные.{disc}\n\nЧто скажете?")
T_EXPIRED = ("Здравствуйте! Анастасия, Qubix. Ваш пробный месяц закончился {ago}, и мне важно понять, каким он был.\n\n"
             "Вы довели продукт до своего сервера, значит смотрели всерьёз. Скажите прямо: что не зашло? Даже если ответ «не наш инструмент» — он мне полезен.\n\n"
             "А если просто не дошли руки — данные и настройки на вашем сервере целы, доступ я возвращаю одним шагом. Готова сделать это прямо сейчас и пройти с вами следующий шаг, если захотите.")
T_STUCK_NEW = ("Здравствуйте! Анастасия, Qubix. Вы завели аккаунт {ago}, а до установки на сервер дело пока не дошло — пишу спросить, где затормозило.\n\n"
               "Обычно это одно из трёх: нет сервера, непонятно с доменом, или просто отложили. На любой из вариантов у меня есть ответ за десять минут. Какой ваш?\n\n"
               "Первый месяц у вас бесплатный, со всеми возможностями — он никуда не делся)")
T_STUCK_PLATFORM = ("Здравствуйте! Анастасия, Qubix. Вы пришли к нам через {platform} и остановились на установке — хочу помочь пройти этот шаг.\n\n"
                    "Скажите, какой у вас сервер, и я пришлю точную последовательность под него. Или созвонимся на двадцать минут и поставим вместе — так быстрее всего.\n\n"
                    "За вашим аккаунтом закреплена скидка от {platform}: первый месяц бесплатно, дальше 50%)")
T_STUCK_OLD = ("Здравствуйте! Анастасия, Qubix. Вы регистрировались у нас в {month}, до установки тогда не дошло. С тех пор вышел большой релиз — продукт стал заметно другим, и я хочу задать один вопрос: что тогда остановило?\n\n"
               "Если дело в сервере, домене или просто «не разобрался» — это решается за один разговор, с меня инструкция под ваш случай. Если продукт был не о том — скажите, и я не буду больше писать.")
T_PAYING = ("Здравствуйте! Анастасия, Qubix. Вы с нами с июля и платите — таких, как вы, я знаю по именам, поэтому пишу лично.\n\n"
            "Хочу спросить две вещи: чего вам не хватает в продукте и что из релиза 28 августа вы уже попробовали. Ответ в любом виде — голосовым, парой слов, созвоном.")
T_BOT = ("Здравствуйте{name}! Анастасия, Qubix. Вы {when} смотрели нашего бота и демо, а до своего аккаунта дело не дошло — хочу спросить, что искали.\n\n"
         "Qubix ставится на ваш сервер: трекер, витрины PWA, автоправила и команда в одном месте, первый месяц бесплатно со всеми возможностями.\n\n"
         "Скажите, какая у вас задача — отвечу по делу, без презентаций)")
T_SILENT = "Здравствуйте! Оставляю дверь открытой и больше не беспокою.\n\nЕсли вернётесь к Qubix — напишите сюда, подниму доступ и пройду с вами любой шаг. Хорошего залива)"

MONTHS = {7: "июле", 8: "августе", 9: "сентябре"}
def days_word(n):
    n = abs(int(n))
    if n == 1: return "день"
    if 2 <= n <= 4: return "дня"
    return "дней"
def ago(n):
    n = int(n)
    if n == 0: return "сегодня"
    if n == 1: return "вчера"
    if n <= 6: return f"{n} {days_word(n)} назад"
    if n <= 13: return "неделю назад"
    if n <= 20: return "две недели назад"
    if n <= 45: return "месяц назад"
    return "больше двух месяцев назад"

people = []
for c in clients:
    n = c["num"]
    email = c["email"]
    reg = datetime.datetime.strptime(c["reg"] + ".2026", "%d.%m.%Y")
    seg, var = c["seg"], c["var"]
    note = ""
    if n in SKIP:
        group, txt, subj = "Не трогать", "", ""; note = SKIP[n]
    elif n in PERSONAL:
        group = "Обещала написать про релиз"
        txt = RELEASE_BASE.format(name="", personal=PERSONAL[n]); subj = "Qubix: релиз вышел — как обещала"
    elif seg == "истекает":
        group = "Месяц заканчивается — писать до даты"
        disc = " Со скидкой по вашему коду — 50%." if DISCOUNT.get(c["code"], 0) == 50 else ""
        txt = T_EXPIRING.format(date=c["paid_until"], disc=disc); subj = f"Qubix: ваш месяц заканчивается {c['paid_until']}"
    elif seg.startswith("истекла"):
        group = "Месяц закончился — самый тёплый возврат"
        pu = datetime.datetime.strptime(c["paid_until"] + ".2026", "%d.%m.%Y")
        txt = T_EXPIRED.format(ago=ago((TODAY - pu).days)); subj = "Qubix: как прошёл ваш месяц?"
        if n in CHECK: note = CHECK[n]
    elif seg == "застрял":
        group = "Зарегистрировался, не поставил"
        code = c["code"]
        if code in PLATFORM and c["days"] <= 21:
            txt = T_STUCK_PLATFORM.format(platform=PLATFORM[code]); subj = "Qubix: шаг установки — подскажу под ваш сервер"
        elif c["days"] <= 21:
            txt = T_STUCK_NEW.format(ago=ago(c["days"])); subj = "Qubix: помочь развернуть на вашем сервере?"
        else:
            txt = T_STUCK_OLD.format(month=MONTHS.get(reg.month, "летом")); subj = "Один вопрос про Qubix"
    elif seg == "платит":
        group = "Платит — лично"
        txt = T_PAYING; subj = "Qubix: два вопроса от CEO"
    else:
        group = "Пробный идёт — пока не пишем"
        txt = ""; subj = ""; note = f"вариант «заканчивается», когда останется 10 дней (до {c['paid_until']})"
    people.append(dict(key=f"a{n}", label=f"#{n}", name=email, group=group, when=(f"до {c['paid_until']}" if c["paid_until"] != "—" else f"рег. {c['reg']}"),
                       code=c["code"], sales=c["sales"], admin=f"https://admin.qubix.pro/customers/{c['cid']}",
                       tg=(f"tg://user?id={c['tg_id']}" if c["tg"] else ""), channel=("Telegram" if c["tg"] else "почта"),
                       text=txt, subj=subj, note=note, last=c.get("last") or ""))

for l in leads:
    nm = l["name"]
    handle = ""
    if "@" in nm and " " in nm: handle = nm.split("@")[-1]
    first = nm.split(" @")[0] if " @" in nm else ""
    if nm.startswith("tg:") or not nm: first = ""
    when_txt = "летом" if l["created"][3:5] in ("06", "07") else ("в августе" if l["created"][3:5] == "08" else "недавно")
    if l["anast"]:
        group = "Обещала написать про релиз"
        txt = RELEASE_BASE.format(name=(", " + first) if first else "", personal=RELEASE_LEAD); subj = "Qubix: релиз вышел — как обещала"
    else:
        group = "Писал боту, не зарегистрировался"
        txt = T_BOT.format(name=(", " + first) if first else "", when=when_txt); subj = "Qubix: что искали?"
    people.append(dict(key=f"s{l['sales']}", label=l["sales"], name=(nm if nm and not nm.startswith("tg:") else (l["email"] or f"tg {l['tg']}")),
                       group=group, when=f"лид {l['created']}", code="—", sales=l["sales"], admin="",
                       tg=(f"tg://user?id={l['tg']}" if l["tg"] else ""), channel=("Telegram" if l["tg"] else "почта"),
                       text=txt, subj=subj, note="", last=l.get("last") or ""))

ORDER = ["Месяц заканчивается — писать до даты", "Обещала написать про релиз", "Месяц закончился — самый тёплый возврат",
         "Зарегистрировался, не поставил", "Писал боту, не зарегистрировался", "Платит — лично", "Пробный идёт — пока не пишем", "Не трогать"]
groups = {g: [p for p in people if p["group"] == g] for g in ORDER}

# ---------- Markdown ----------
md = ["Куда: внутренняя карта касаний", "", "# Карта касаний — все клиенты и лиды", "",
      f"Срез 18.09.2026: админка 180 записей → 76 живых; SALES без регистрации → {len(leads)} лидов из бота. Отметок о касании после 14.09 в трекере нет; про Telegram и почту не знаю.", ""]
for g in ORDER:
    md.append(f"## {g} — {len(groups[g])}"); md.append("")
    for p in groups[g]:
        links = []
        if p["sales"]: links.append(f"[{p['sales']}](https://team.qubix.capital/issue/{p['sales']})")
        if p["admin"]: links.append(f"[админка]({p['admin']})")
        if p["tg"]: links.append(f"[Telegram]({p['tg']})")
        md.append(f"### {p['label']} · {p['name']} · {p['when']}" + (f" · код {p['code']}" if p['code'] not in ('—','') else ""))
        md.append(" · ".join(links) + (f" · посл. коммент {p['last']}" if p["last"] else ""))
        if p["note"]: md.append(f"_{p['note']}_")
        if p["text"]:
            if p["channel"] == "почта": md.append(f"**Почтой. Тема:** {p['subj']}")
            md.append(""); md.append("\n".join("> " + ln for ln in p["text"].split("\n")))
        md.append("")
    md.append("")
md.append("## Молчание — одно напоминание через три дня, всем одинаково"); md.append("")
md.append("\n".join("> " + ln for ln in T_SILENT.split("\n")))
open(OUT_MD, "w", encoding="utf-8").write("\n".join(md))

# ---------- HTML ----------
def esc(s): return html.escape(s or "")
cards = []
for g in ORDER:
    sec = [f'<section><h2>{esc(g)} <span class="cnt">{len(groups[g])}</span></h2>']
    for p in groups[g]:
        links = []
        if p["sales"]: links.append(f'<a href="https://team.qubix.capital/issue/{p["sales"]}" target="_blank">{p["sales"]}</a>')
        if p["admin"]: links.append(f'<a href="{p["admin"]}" target="_blank">админка</a>')
        if p["tg"]: links.append(f'<a href="{p["tg"]}">Telegram</a>')
        meta = f'{esc(p["when"])}' + (f' · код {esc(p["code"])}' if p["code"] not in ("—", "") else "") + (f' · посл. коммент {esc(p["last"])}' if p["last"] else "")
        body = ""
        if p["text"]:
            subj = f'<div class="subj">Почтой · тема: {esc(p["subj"])}</div>' if p["channel"] == "почта" else ""
            body = f'{subj}<pre class="txt">{esc(p["text"])}</pre><button class="copy" data-key="{p["key"]}">Скопировать текст</button>'
        note = f'<div class="note">{esc(p["note"])}</div>' if p["note"] else ""
        sec.append(f'''<article class="card" data-key="{p["key"]}">
<header><label class="chk"><input type="checkbox" data-key="{p["key"]}"> <span>отправлено</span></label>
<b>{esc(p["label"])}</b> <span class="name">{esc(p["name"])}</span><span class="meta">{meta}</span>
<span class="links">{" · ".join(links)}</span></header>{note}{body}</article>''')
    sec.append("</section>")
    cards.append("\n".join(sec))
total = sum(len(v) for v in groups.values())
page = f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Карта касаний Qubix</title>
<style>
:root{{--bg:#f6f7fb;--card:#ffffff;--ink:#141a2b;--muted:#5f6779;--line:#d9dde8;--accent:#1e5bd1;--accent-ink:#ffffff;--done:#e8f5ec;--note:#fff6dc;--code:#eef1f8}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#0f1420;--card:#171d2c;--ink:#e9ebf6;--muted:#a3abbe;--line:#2b3347;--accent:#84aef3;--accent-ink:#0f1420;--done:#17301f;--note:#3a3216;--code:#1f2637}}}}
:root[data-theme="dark"]{{--bg:#0f1420;--card:#171d2c;--ink:#e9ebf6;--muted:#a3abbe;--line:#2b3347;--accent:#84aef3;--accent-ink:#0f1420;--done:#17301f;--note:#3a3216;--code:#1f2637}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,"Segoe UI",Roboto,Inter,sans-serif}}
main{{max-width:880px;margin:0 auto;padding:24px 16px 80px}}
h1{{font-size:24px;margin:0 0 4px;text-wrap:balance}}.sub{{color:var(--muted);margin:0 0 20px}}
.bar{{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:20px;font-size:14px;color:var(--muted)}}
.bar label{{display:flex;gap:6px;align-items:center;cursor:pointer}}
h2{{font-size:17px;margin:28px 0 10px;display:flex;gap:8px;align-items:baseline}}.cnt{{color:var(--muted);font-weight:400;font-size:14px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-bottom:10px}}
.card.done{{background:var(--done);opacity:.75}}
header{{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:baseline}}
.chk{{display:flex;gap:6px;align-items:center;font-size:13px;color:var(--muted);cursor:pointer}}
.name{{font-weight:500}}.meta{{color:var(--muted);font-size:13px}}.links{{font-size:13px;margin-left:auto}}
a{{color:var(--accent)}}
.txt{{white-space:pre-wrap;font:inherit;background:var(--code);border-radius:8px;padding:10px 12px;margin:10px 0 8px}}
.subj{{font-size:13px;color:var(--muted);margin-top:8px}}
.note{{background:var(--note);border-radius:8px;padding:6px 10px;margin-top:8px;font-size:13px}}
.copy{{background:var(--accent);color:var(--accent-ink);border:0;border-radius:8px;padding:6px 12px;font:inherit;font-size:13px;cursor:pointer}}
.copy:focus-visible,input:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
body.hide-done .card.done{{display:none}}
</style></head><body><main>
<h1>Карта касаний Qubix</h1>
<p class="sub">Срез 18.09.2026 · {total} человек: 76 живых из админки и {len(leads)} лидов из бота без регистрации. Галочки живут в этом браузере.</p>
<div class="bar"><span id="stat"></span><label><input type="checkbox" id="hide"> скрыть отправленные</label></div>
{"".join(cards)}
<section><h2>Молчание — одно напоминание через три дня</h2><article class="card"><pre class="txt">{esc(T_SILENT)}</pre></article></section>
</main>
<script>
(function(){{
var KEY='qubix-karta-kasaniy';var state={{}};
try{{state=JSON.parse(localStorage.getItem(KEY)||'{{}}')}}catch(e){{state={{}}}}
function save(){{try{{localStorage.setItem(KEY,JSON.stringify(state))}}catch(e){{}}}}
function stat(){{var n=Object.keys(state).filter(function(k){{return state[k]}}).length;document.getElementById('stat').textContent='отправлено '+n+' из {total}'}}
document.querySelectorAll('input[type=checkbox][data-key]').forEach(function(cb){{
  var k=cb.dataset.key;cb.checked=!!state[k];if(cb.checked)cb.closest('.card').classList.add('done');
  cb.addEventListener('change',function(){{state[k]=cb.checked;cb.closest('.card').classList.toggle('done',cb.checked);save();stat()}});
}});
document.querySelectorAll('button.copy').forEach(function(b){{b.addEventListener('click',function(){{
  var t=b.parentElement.querySelector('.txt').textContent;
  navigator.clipboard.writeText(t).then(function(){{b.textContent='Скопировано';setTimeout(function(){{b.textContent='Скопировать текст'}},1500)}});
}})}});
var hide=document.getElementById('hide');try{{hide.checked=localStorage.getItem(KEY+'-hide')==='1'}}catch(e){{}}
document.body.classList.toggle('hide-done',hide.checked);
hide.addEventListener('change',function(){{document.body.classList.toggle('hide-done',hide.checked);try{{localStorage.setItem(KEY+'-hide',hide.checked?'1':'0')}}catch(e){{}}}});
stat();
}})();
</script></body></html>'''
open(OUT_HTML, "w", encoding="utf-8").write(page)
print("людей на карте:", total, {g: len(v) for g, v in groups.items()})
