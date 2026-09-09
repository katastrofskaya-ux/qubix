# Проверка UTM-меток на лендинге qubix.pro — отчёт

**Дата замера:** 09.09.2026, ~15:38–15:45 UTC.
**Контур:** облачная сессия Claude Code (управляемое окружение с egress-прокси и сетевой политикой). Все факты ниже — класс «замер» из этой сессии; что не удалось замерить — перечислено явно.

## Главное одним абзацем (вывод)

**Проверка неполная.** Сетевая политика этого Claude Code-окружения не содержит хост `qubix.pro` (и домены Google Analytics/GTM), поэтому сам лендинг из этой сессии недостижим: ни HTML, ни поведение браузера, ни хиты GA проверить нельзя. Единственный доступный хост — `www.qubix.pro`, и его серверный редирект **метки НЕ теряет**: 301 на `https://qubix.pro/` с полностью сохранённым query (включая `r`, `utm_source`, `utm_medium`, `utm_campaign`). Дальше этого шага трафик из данной сессии не проходит. Не хватило: доступа в сетевой политике окружения к `qubix.pro` (порт 443 и 80), `www.googletagmanager.com`, `*.google-analytics.com`. Это тот же класс блокировки, что уже был зафиксирован 28.07.2026 для `dash.qubix.capital` (см. CLAUDE.md, раздел «Статус: Qubix MCP»). Чинится настройкой network policy окружения на claude.ai — либо перезапуском проверки с машины без такого прокси.

## 1. Редиректы (curl) — что показали замеры

### 1.1. `https://qubix.pro/?r=UTMCHECK&utm_source=UTMCHECK&utm_medium=telegram&utm_campaign=test`

Запрос не дошёл до сайта — CONNECT-туннель отклонён прокси окружения (ответ без заголовков Cloudflare, до origin дело не дошло):

```
> CONNECT qubix.pro:443 HTTP/1.1
< HTTP/1.1 403 Forbidden
< Content-Type: text/plain; charset=utf-8
< X-Content-Type-Options: nosniff
< Content-Length: 67
* CONNECT tunnel failed, response 403
```

Повторные попытки — код `000` (соединение не установлено), диагностика прокси:

```
[agent-proxy] qubix.pro:443 — connect_rejected (the egress proxy denied the
CONNECT (organization policy) or could not reach the destination) ×2
```

### 1.2. `http://qubix.pro/?...` (как в постах)

Тоже срезано прокси, причина названа явно:

```
HTTP/1.1 403 Forbidden
x-deny-reason: host_not_allowed
```

**Редирект http→https на стороне сайта не проверен** — до сайта запрос не дошёл.

### 1.3. `https://www.qubix.pro/?r=UTMCHECK&utm_source=UTMCHECK&utm_medium=telegram&utm_campaign=test` — единственный доступный хост

```
HTTP/2 301
location: https://qubix.pro/?r=UTMCHECK&utm_source=UTMCHECK&utm_medium=telegram&utm_campaign=test
server: cloudflare
```

Факт: серверный 301 с `www` на apex **сохраняет query целиком** — все четыре параметра на месте, посимвольно. Редирект отдаёт Cloudflare.

### 1.4. Следование по цепочке (`curl -L -w '%{http_code} %{url_effective}'`)

```
www:    301 https://www.qubix.pro/?r=UTMCHECK&utm_source=UTMCHECK&utm_medium=telegram&utm_campaign=test
apex:   000 https://qubix.pro/?r=UTMCHECK&...
www -L: 000 https://qubix.pro/?r=UTMCHECK&...  redirects=1
```

Цепочка обрывается на первом же переходе к `qubix.pro:443` — по той же причине `connect_rejected`.

## 2. HTML лендинга — НЕ ПРОВЕРЕН

Скачать HTML невозможно: `qubix.pro:443` не в сетевой политике (п. 1.1). Поиск `googletagmanager.com / gtag( / G-… / GTM- / replaceState( / pushState( / location.replace( / location.href=` не выполнялся — нечего искать. Сказать, есть ли тег GA в HTML, **нельзя ни в какую сторону**.

Исходников лендинга в репозитории `katastrofskaya-ux/qubix` нет (репозиторий — база знаний: docs/, drafts/, TASKS.md), так что проверить тег по коду тоже негде.

## 3. Браузерная проверка (Playwright) — НЕ ВЫПОЛНЯЛАСЬ

Запуск Chromium не проводился осознанно: страница `qubix.pro` не открылась бы по той же причине, что и curl (единый egress-прокси для всего окружения, `connect_rejected` на CONNECT). Замерить `page.url()` после load, подчистку адреса через 5 секунд и запросы `/g/collect` невозможно, пока домен не в политике.

Дополнительно замерено: домены тега тоже вне политики — «домен не в политике, хит проверить нельзя»:

```
www.googletagmanager.com:443    — connect_rejected
region1.google-analytics.com:443 — connect_rejected
```

## Что проверено / что нет — сводка

| Шаг | Статус | Результат |
|---|---|---|
| 301 www→apex, сохранность query | ✅ проверено | метки сохраняются полностью |
| Ответ apex `https://qubix.pro` (код, Location) | ❌ хост не в политике | неизвестно |
| Редирект `http://qubix.pro` (как в постах) | ❌ порт 80 срезан прокси | неизвестно |
| Тег GA/GTM в HTML | ❌ HTML недоступен | неизвестно |
| Подчистка URL клиентским кодом (replaceState и т.п.) | ❌ браузер не дошёл бы до страницы | неизвестно |
| Хит `/g/collect` (dl / page_location / cid) | ❌ GA-домены не в политике | неизвестно |

Итог: по единственному замеримому звену (www→apex) метки **не теряются**. Ответить, где они теряются дальше — на apex-редиректе, в клиентском коде или доезжают до тега, — эта сессия не может. Для полной проверки нужно либо добавить в network policy окружения хосты `qubix.pro`, `www.googletagmanager.com`, `*.google-analytics.com` (порт 443; проверку `http://` это всё равно не покроет, если политика не пускает порт 80), либо прогнать те же команды с обычной машины.
