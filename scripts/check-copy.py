#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Проверка внешнего текста по нормативам Qubix перед подачей на согласование.

    scripts/check-copy.py текст.md
    cat текст.md | scripts/check-copy.py
    scripts/check-copy.py текст.md --author-voice   # голос автора в купленном размещении
    scripts/check-copy.py текст.md --table          # именная сравнительная таблица на главной

Источники правил: MARKETING-70 §9-10 (стоп-лист), MARKETING-9 / docs/tone-of-voice.md,
MARKETING-13 и MARKETING-2 (реф-ссылка), решения владельца 19.08 / 01.09 / 02.09.2026,
NDA Cl. 3.14 (цены). Свод: docs/normativy-vneshnih-tekstov.md

Выход: ❌ — нельзя, правило прямое. ⚠️ — проверь глазами, зависит от контекста.
Код возврата: 1, если есть хотя бы одна ❌.
"""
import argparse, re, sys

STOP = "❌"
WARN = "⚠️"

# Точные строки, согласованные владельцем: они выше запретов.
WHITELIST = [
    "от залива до созвонов и финансов",   # слоган-диапазон, CONTENT-3 02.09.2026
    "от задачи до созвона",               # слоган MARKETING-70 / CLAUDE.md
]

RULES = [
    # (уровень, регулярка, что нашли, чем чинить, источник, флаг-исключение)
    (STOP, r"my\.qubix\.pro/register\?r=|/register\?r=",
     "ссылка на страницу регистрации с реф-кодом",
     "реф-ссылка только qubix.pro/?r=КОД — кука qubix_ref ставится на лендинге и применяется при регистрации",
     "MARKETING-13, MARKETING-2, docs/resource-map.md", None),

    (STOP, r"всё в одном|все в одном|all-in-one",
     "формула «всё в одном»",
     "категория объясняется метафорой офиса: офис меряется тем, чей он, а не длиной списка",
     "MARKETING-70 §5 и стоп-лист п.1", None),

    (STOP, r"\bSuperapp\b",
     "написание «Superapp»",
     "по-английски SuperApp, по-русски Суперапп",
     "указание владельца 02.09.2026, CONTENT-3", None),

    (STOP, r"Keitaro|Кейтаро|Binom|Бином|Voluum|RedTrack|adset\.pro|AdsPower|Dolphin|Octo Browser|Multilogin|\bAIO\b",
     "имя конкурента в клиентском тексте",
     "конкуренты — контекст для автора, в текст не идут",
     "MARKETING-70 стоп-лист п.2", "author_voice"),

    (STOP, r"в отличие от трекер|лучше любого трекера|не просто трекер|не трекер, а|обычные трекеры",
     "сравнение с трекерами",
     "сравнение с трекером само кладёт нас на трекерную полку — запрещено в любом формате",
     "MARKETING-70 §6, docs/tone-of-voice.md п.8", None),

    (STOP, r"защит\w* от банов|избавит\w* от банов|не забанят",
     "обещание защиты от банов",
     "баны неизбежны, лишнего риска мы не добавляем — говорим честно",
     "MARKETING-70 стоп-лист п.3", None),

    (STOP, r"замена антидетект|вместо антидетект",
     "замена антидетекта",
     "работаем через антидетект, а не вместо него",
     "MARKETING-70 стоп-лист п.4", None),

    (STOP, r"рептильн\w+ мозг|неокортекс|бей-беги|подсознательн\w+ реш|\d+\s*%\s*решени\w+ принима",
     "ссылка на устройство мозга или доля «подсознательных» решений",
     "модель отвергнута специалистами, числа не существует — убрать",
     "MARKETING-70 стоп-лист п.6-7", None),

    (WARN, r"мессенджер|видеосвязь|видеозвон|звонк\w+|созвон\w*|командн\w+ (контур|слой)|таск-трекер|таск-менеджер|календар\w+|почт\w+ в Qubix|Google Ads|TikTok|мобильн\w+ приложени",
     "возможность, которая клиентам ещё не открыта",
     "невыпущенное как имеющееся не называем; документы, таблицы и диск называть можно",
     "MARKETING-70 стоп-лист п.5", None),

    (WARN, r"облак\w+ (видит|смотрит|хранит|доит)|сервис\w* (доя|забира|держ)|поставщик (видит|забирает|держит)|чужие держат",
     "действие, приписанное конкуренту (даже без имени)",
     "боль пишется состоянием покупателя, а не действием чужих: «связки лежат там, где вы не хозяин»",
     "MARKETING-70 стоп-лист п.2а и §9", "author_voice"),

    (WARN, r"(?<![\w])(без|нет|никаких|не нужно|никогда)(?![\w])",
     "отрицание внутри продающей фразы",
     "переформулировать через выгоду; прямой ответ «Нет» на заданный вопрос — исключение",
     "docs/tone-of-voice.md, железные правила п.1", None),

    (WARN, r"\bты\b|\bтебе\b|\bтвой\b|\bтвои\b|\bтвоя\b|\bлей\b(?!те)",
     "обращение на «ты»",
     "«вы» на всех наших поверхностях; «ты» — только в речи автора канала в купленном размещении",
     "MARKETING-70 §9", "author_voice"),

    (WARN, r"\b(Starter|Standard|Business|Enterprise|Ultimate|Agency)\b",
     "название тарифной ступени",
     "продаём доступ, не ступень — название ступени в текстах не звучит",
     "решение владельца 19.08.2026, MARKETING-83", None),

    (WARN, r"(?<![\d+])\b(\d{2,4})\s+(настро|шаблон|метрик|инструмент|экран|пол(е|я|ей))",
     "точное число возможностей без знака «+»",
     "такое число меняется от выпуска к выпуску — писать порядком величины: «50+», «25+»",
     "MARKETING-70 §9, решение владельца 19.08.2026", None),

    (WARN, r"\$\s?\d|\d+\s?\$|\d+\s?(долл|USD)",
     "цена или финансовая цифра",
     "требует явного письменного одобрения компании — молчанием не согласуется",
     "NDA Cl. 3.14", None),

    (WARN, r"—",
     "длинное тире",
     "в написании принят дефис; проверьте, что для этой поверхности так и надо",
     "MARKETING-70 §9 «Написание»", None),
]

YO = {"еще": "ещё", "ее": "её", "счет": "счёт", "идет": "идёт", "дает": "даёт",
      "берет": "берёт", "живет": "живёт", "зовет": "зовёт", "несет": "несёт",
      "растет": "растёт", "теряет": "теряет", "все ": "всё ", "чем": "чем"}
YO_CHECK = ["еще", "ее", "счет", "идет", "дает", "берет", "живет", "растет", "несет"]


def mask_whitelist(line):
    out = line
    for w in WHITELIST:
        out = out.replace(w, "·" * len(w))
    return out


def check(text, author_voice=False, table=False):
    findings = []
    for n, raw in enumerate(text.splitlines(), 1):
        line = mask_whitelist(raw)
        if not line.strip():
            continue
        for level, pat, what, fix, src, exempt in RULES:
            if exempt == "author_voice" and author_voice:
                continue
            if exempt == "table" and table:
                continue
            # правило написания категории регистрозависимое: верное «SuperApp»
            # не должно ловиться на неверном «Superapp»
            flags = 0 if pat == r"\bSuperapp\b" else re.I
            m = re.search(pat, line, flags)
            if m:
                findings.append((level, n, m.group(0), what, fix, src, raw.strip()))
        for w in YO_CHECK:
            if re.search(r"(?<![\w])" + w + r"(?![\w])", line, re.I):
                findings.append((WARN, n, w, "буква «ё» уронена в «е»",
                                 f"написать «{YO[w]}»", "MARKETING-70 §9", raw.strip()))
                break
    return findings


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("file", nargs="?", help="файл с текстом; без него читает stdin")
    ap.add_argument("--author-voice", action="store_true",
                    help="голос автора в купленном размещении: снимает запрет на конкурентов и «ты»")
    ap.add_argument("--table", action="store_true",
                    help="именная сравнительная таблица на главной")
    a = ap.parse_args()

    text = open(a.file, encoding="utf-8").read() if a.file else sys.stdin.read()
    res = check(text, a.author_voice, a.table)

    if not res:
        print("Чисто: правил, которые ловятся машиной, не нарушено.")
        print("Глазами всё равно проверьте: перечисление вместо выгоды, боль в лоб,")
        print("предположения о хозяйстве читателя — это машина не видит.")
        return 0

    stops = [r for r in res if r[0] == STOP]
    warns = [r for r in res if r[0] == WARN]
    for group, title in ((stops, "НЕЛЬЗЯ — правило прямое"), (warns, "ПРОВЕРЬ — зависит от контекста")):
        if not group:
            continue
        byrule = {}
        for level, n, hit, what, fix, src, line in group:
            byrule.setdefault(what, {"fix": fix, "src": src, "cases": []})
            cases = byrule[what]["cases"]
            if not any(c[0] == n for c in cases):
                cases.append((n, hit, line))
        print(f"\n=== {title} ({len(byrule)}) ===")
        for what, info in byrule.items():
            cases = info["cases"]
            lines = ", ".join(str(c[0]) for c in cases[:8]) + ("…" if len(cases) > 8 else "")
            print(f"\n{level} {what} — строк(и): {lines}")
            for n, hit, line in cases[:2]:
                print(f"   {n}: «{hit}» → {line[:100]}")
            if len(cases) > 2:
                print(f"   …и ещё {len(cases)-2}")
            print(f"   как надо: {info['fix']}")
            print(f"   источник: {info['src']}")

    print(f"\nИтого: {len(stops)} нельзя, {len(warns)} проверить.")
    print("Что машина НЕ проверяет: перечисление модулей вместо выгоды, боль в лоб,")
    print("фича без доказательства, предположения о хозяйстве читателя.")
    return 1 if stops else 0


if __name__ == "__main__":
    sys.exit(main())
