#!/usr/bin/env python3
"""Утренняя прогулка Маши по чатам: что говорят про Qubix.

Ходит в Машу (masha.qubix.pro) напрямую по HTTP JSON-RPC — без MCP-обвязки,
поэтому работает и в сессиях по расписанию. Токен — из MASHA_API_TOKEN.

Использование:
    scripts/masha-svodka.py             # за последние 24 часа
    scripts/masha-svodka.py --hours 48  # другое окно

Выводит сырые находки тремя блоками: упоминания Qubix текстом, посты со
ссылками на qubix.pro (наши выходы/перепосты), счётчик по конкурентам за
окно. Оценку «надо ли внимание» делает тот, кто читает (агент утреннего
разбора или Анастасия) — скрипт не интерпретирует.

⚠️ «Qubix Capital» — чужой инвестфонд-однофамилец: упоминания с «capital»,
«фонд», «инвест» помечаются [проверить: возможно чужой фонд].
⚠️ Покрытие базы = каналы, куда вступил парсер. Тишина = «не отслеживается»,
а не «никто не говорит».
"""
import argparse
import json
import os
import subprocess
import sys

URL = "https://masha.qubix.pro/"
TOKEN = os.environ.get("MASHA_API_TOKEN")

FUND_MARKERS = ("capital", "капитал", "фонд", "инвест")


def call(sql: str):
    # curl вместо urllib: агентский прокси окружения пропускает curl,
    # а запросы urllib отбивает 403.
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "analyst_sql", "arguments": {"sql": sql}},
    }
    out = subprocess.run(
        ["curl", "-sS", "--max-time", "60", "-X", "POST", URL,
         "-H", f"Authorization: Bearer {TOKEN}",
         "-H", "Content-Type: application/json",
         "-H", "Accept: application/json, text/event-stream",
         "-d", json.dumps(payload)],
        capture_output=True, text=True, check=True,
    ).stdout
    body = json.loads(out)
    if "error" in body:
        raise RuntimeError(body["error"])
    content = body["result"]["content"][0]["text"]
    return json.loads(content)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    args = ap.parse_args()
    h = args.hours

    if not TOKEN:
        sys.exit("MASHA_API_TOKEN не задан — проверь env | grep -i masha целиком, прежде чем говорить «доступа нет».")

    print(f"Прогулка Маши: окно {h} ч. (сейчас UTC)")

    # 1. Упоминания Qubix текстом
    rows = call(f"""
        SELECT c.title AS title, c.username AS username, m.peer_id AS peer_id,
               m.msg_id AS msg_id, m.date AS dt, m.from_id AS from_id,
               m.views AS views, substring(m.text, 1, 400) AS snippet
        FROM tg.messages m
        LEFT JOIN tg.channels c FINAL ON c.channel_id = m.peer_id
        WHERE m.date >= now() - INTERVAL {h} HOUR
          AND (positionCaseInsensitive(m.text, 'qubix') > 0
               OR positionCaseInsensitive(m.text, 'кубикс') > 0)
        ORDER BY m.date
        LIMIT 100""")
    print(f"\n== Упоминания Qubix текстом: {len(rows)} ==")
    for r in rows:
        mark = ""
        low = (r.get("snippet") or "").lower()
        if any(w in low for w in FUND_MARKERS):
            mark = "  [проверить: возможно чужой фонд Qubix Capital]"
        kind = "пост" if r.get("from_id") in (0, "0", None) else f"коммент от {r.get('from_id')}"
        print(f"- {r['dt']} · {r.get('title') or r['peer_id']} (@{r.get('username') or '—'}) · {kind} · "
              f"views={r.get('views')}{mark}\n  «{(r.get('snippet') or '').strip()}»"
              f"\n  (дочитать: get_context peer_id={r['peer_id']} msg_id={r['msg_id']})")

    # 2. Ссылки на qubix.pro — вышедшие размещения и перепосты
    rows = call(f"""
        SELECT c.title AS title, c.username AS username, m.peer_id AS peer_id,
               m.msg_id AS msg_id, m.date AS dt, m.views AS views,
               arrayStringConcat(m.external_links, ' ') AS links,
               substring(m.text, 1, 200) AS snippet
        FROM tg.messages m
        LEFT JOIN tg.channels c FINAL ON c.channel_id = m.peer_id
        WHERE m.date >= now() - INTERVAL {h} HOUR
          AND arrayExists(l -> positionCaseInsensitive(l, 'qubix.pro') > 0, m.external_links)
        ORDER BY m.date
        LIMIT 50""")
    print(f"\n== Посты со ссылкой на qubix.pro: {len(rows)} ==")
    for r in rows:
        print(f"- {r['dt']} · {r.get('title') or r['peer_id']} (@{r.get('username') or '—'}) · views={r.get('views')}"
              f"\n  ссылки: {r.get('links')}\n  «{(r.get('snippet') or '').strip()}»")

    # 3. Пульс конкурентов — только счётчики, для контекста
    rows = call(f"""
        SELECT t AS t, n AS n FROM (
          SELECT 'keitaro' AS t, countIf(positionCaseInsensitive(text,'keitaro')>0) AS n
            FROM tg.messages WHERE date >= now() - INTERVAL {h} HOUR
          UNION ALL SELECT 'binom', countIf(positionCaseInsensitive(text,'binom')>0)
            FROM tg.messages WHERE date >= now() - INTERVAL {h} HOUR
          UNION ALL SELECT 'adset', countIf(positionCaseInsensitive(text,'adset')>0)
            FROM tg.messages WHERE date >= now() - INTERVAL {h} HOUR
          UNION ALL SELECT 'redtrack', countIf(positionCaseInsensitive(text,'redtrack')>0)
            FROM tg.messages WHERE date >= now() - INTERVAL {h} HOUR
          UNION ALL SELECT 'voluum', countIf(positionCaseInsensitive(text,'voluum')>0)
            FROM tg.messages WHERE date >= now() - INTERVAL {h} HOUR
        ) ORDER BY n DESC""")
    pulse = " · ".join(f"{r['t']}: {r['n']}" for r in rows)
    print(f"\n== Пульс конкурентов за {h} ч.: {pulse} ==")
    print("\nПамятка читающему: тишина по Qubix = «не отслеживается или молчат», не «всё хорошо».")
    print("Внимание Анастасии нужно, если: негатив/скам-обвинение, вопрос без ответа в живом чате,")
    print("наш пост вышел без кода/с чужой ссылкой, упоминание конкурентом, чужой фонд рядом с нами.")


if __name__ == "__main__":
    main()
