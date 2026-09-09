# Проверка UTM-меток на лендинге qubix.pro — отчёт, прогон 2

**Дата замера:** 09.09.2026, ~15:57–16:02 UTC.
**Контур:** облачная сессия Claude Code, egress-прокси; сетевая политика обновлена (qubix.pro и www доступны). Все факты — класс «замер» из этой сессии, кроме двух цитат кода лендинга (класс «документ», файл `https://qubix.pro/assets/js/qubix.js` на дату замера).

## Вывод одним абзацем

**Метки теряет сам сайт, на серверном языковом редиректе.** Любой вход — `http://qubix.pro/?...` (как в постах), `https://qubix.pro/?...`, `https://www.qubix.pro/?...` — сводится к одной цепочке: (1) переход на https/apex сохраняет query полностью; (2) edge отдаёт 302, забирает `r=UTMCHECK` в куку `qubix_ref` и оставляет все utm_* в Location; (3) следующий 302 `/` → `/en/` отдаёт `location: /en/` **без query вообще** — все utm_* умирают здесь, до загрузки страницы. Браузер подтверждает: `page.url()` после load и через 5 секунд — `https://qubix.pro/en/`, чистый; клиентский код ничего не подчищает (его `replaceState` убирает только служебный `cookies=1`). GA4-тег на лендинге есть (грузится динамически из `qubix.js`, ID `GT-TQKZHCKN`), но к моменту его загрузки адрес уже без меток — вот и «direct» в GA. Это вариант, близкий к (в), но фикс нужен не странице, а серверу: **языковой редирект `/` → `/en/` должен переносить query string**. Контрольный замер: прямой вход на `https://qubix.pro/en/?utm...` — 200 без редиректов, метки живут в адресе и после load, и через 5 секунд, и уезжают в собственную аналитику (`campaign_visit`). Не проверено одно: сам хит GA `/g/collect` — тег ходит на `www.googletagmanager.com` и `region1.google-analytics.com`, а политика окружения пускает только домены без этих поддоменов (`connect_rejected` на оба); впрочем, на вывод это не влияет — page_location тег берёт из адреса, который уже чист.

## 1. Редиректы (curl)

### 1.1. `https://qubix.pro/?r=UTMCHECK&utm_source=UTMCHECK&utm_medium=telegram&utm_campaign=test`

Шаг 1 — edge забирает `r` в куку, utm_* сохраняет:

```
HTTP/2 302
location: /?utm_campaign=test&utm_source=UTMCHECK&utm_medium=telegram
set-cookie: qubix_ref=UTMCHECK; Domain=.qubix.pro; Max-Age=2592000
set-cookie: piuid=...; qubix_geo=US
server: cloudflare
```

Шаг 2 — **точка потери**. Языковой редирект отбрасывает query целиком:

```
GET /?utm_campaign=test&utm_source=UTMCHECK&utm_medium=telegram
HTTP/2 302
location: /en/          ← query исчез полностью
```

Итог цепочки: `curl -L -w` → `200 https://qubix.pro/en/ redirects=2`. Меток в финальном адресе нет.

### 1.2. `http://qubix.pro/?...` (как в постах)

```
HTTP/1.1 301
location: https://qubix.pro/?r=UTMCHECK&utm_source=UTMCHECK&utm_medium=telegram&utm_campaign=test
```

http→https сохраняет query посимвольно, дальше — та же цепочка, что в 1.1. Итог: `200 https://qubix.pro/en/ redirects=3`.

### 1.3. `https://www.qubix.pro/?...`

```
HTTP/2 301
location: https://qubix.pro/?r=UTMCHECK&utm_source=UTMCHECK&utm_medium=telegram&utm_campaign=test
```

www→apex сохраняет query (подтверждает прогон 1), дальше та же цепочка. Итог: `200 https://qubix.pro/en/ redirects=3`.

### 1.4. Контроль: `https://qubix.pro/en/?utm_source=UTMCHECK&utm_medium=telegram&utm_campaign=test`

`HTTP/2 200`, `redirects=0` — при входе сразу на языковую страницу метки не трогаются.

## 2. HTML и JS лендинга

В самом HTML (~311 КБ) GA/GTM-тега **нет**: ноль совпадений по `googletagmanager.com`, `gtag(`, `G-…`, `GTM-…`, `replaceState(`, `pushState(`, `location.replace(`, `location.href=`. Внешних счётчиков нет вообще — только локальные скрипты (`/assets/js/app.js`, `qubix.js`, слайдеры).

Но счётчик есть — он живёт в `/assets/js/qubix.js` и вставляет тег динамически:

```js
var GA4_TAG_ID = 'GT-TQKZHCKN';
...
s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA4_TAG_ID;
...
window.gtag('config', GA4_TAG_ID);
window.gtag('config', GADS_TAG_ID, { linker: { domains: GADS_LINKER_DOMAINS } });
```

Там же Google Ads-тег `AW-18327723739` и собственная аналитика `campaign_visit` (шлёт `location.href` на `/pwa-api/event`). Единственный `replaceState` в коде вычищает **только** параметр `cookies=1` (открытие центра настроек cookie) — utm_* он не трогает. Для не-EEA гео (кука `qubix_geo`) трекеры стартуют сразу на load, согласия не ждут.

## 3. Браузер (Playwright, Chromium)

Вход: `https://qubix.pro/?r=UTMCHECK&utm_source=UTMCHECK&utm_medium=telegram&utm_campaign=test`.

- `page.url()` после `load`: `https://qubix.pro/en/` — **метки исчезли ещё до первого выполненного скрипта** (их убил редирект из п. 1.1, не клиентский код).
- `page.url()` через 5 секунд: `https://qubix.pro/en/` — без изменений.
- Перехват запросов: ушёл `GET https://www.googletagmanager.com/gtag/js?id=GT-TQKZHCKN` (тег реально пытается грузиться) и `POST /pwa-api/event` + серия `/pwa-api/event-stream` (session replay).
- Тело beacon'а собственной аналитики при этом входе: `{"event":"campaign_visit","url":"https://qubix.pro/en/",...}` — **и своя атрибуция получает адрес уже без меток**. При контрольном входе на `/en/?utm...` тот же beacon несёт полный URL с метками.
- `r=UTMCHECK` при этом не пропадает: он снят edge'ем в куку `qubix_ref` (Max-Age 30 дней) на первом же ответе — реферальная привязка через куку живёт, теряются именно utm_*.

**Что срезала сеть окружения:** загрузка тега упала — `ERR_TUNNEL_CONNECTION_FAILED` на `www.googletagmanager.com` (политика пускает `googletagmanager.com` и `google-analytics.com`, но не поддомены `www.` и `region1.` — оба дают `connect_rejected`). Поэтому хит `/g/collect` с параметрами `dl`/`en` из этой сессии пронаблюдать нельзя. На вывод не влияет: `page_location` тег берёт из адреса страницы, а адрес к этому моменту уже `https://qubix.pro/en/` без меток.

## 4. Что делать

Фикс серверный, не страницы: языковой редирект `/` → `/en/` (и, видимо, прочие локали) должен **переносить query string** в Location. После фикса — повторить этот же замер: финальный `page.url()` обязан быть `/en/?utm_source=...`, и тогда и GA, и собственный `campaign_visit` увидят источник. Задача для dev-команды (вне зоны Анастасии), в тикет достаточно пп. 1.1 и 3 этого отчёта. Для полного добивания проверки хитом `/g/collect` — добавить в network policy окружения `www.googletagmanager.com` и `region1.google-analytics.com` (именно с поддоменами), либо глянуть DebugView GA с обычной машины при входе на `/en/?utm...`.

## Сводка

| Шаг | Статус | Результат |
|---|---|---|
| http→https, сохранность query | ✅ | сохраняется полностью |
| 301 www→apex, сохранность query | ✅ | сохраняется полностью |
| 302 edge (снятие `r` в куку `qubix_ref`) | ✅ | utm_* сохраняются, `r` уходит в куку |
| 302 `/` → `/en/` | ✅ **точка потери** | query отбрасывается целиком |
| Тег GA/GTM | ✅ | есть, `GT-TQKZHCKN` + `AW-18327723739`, динамически из `qubix.js` |
| Подчистка URL клиентским кодом | ✅ | нет (replaceState — только `cookies=1`) |
| `page.url()` после load / +5с | ✅ | `https://qubix.pro/en/`, меток нет с самого начала |
| Хит `/g/collect` (dl, en) | ❌ | `www.googletagmanager.com` и `region1.google-analytics.com` — `connect_rejected` (поддомены не в политике) |

---

# Архив прогона 1

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
