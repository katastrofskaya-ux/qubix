Куда: YouTrack — новая задача для Ника (промокоды)

# Промокоды каналов: привести к эталону AFFBUDDHA

Замер по админке на 23.09.2026. Коды Будды настроены правильно — берём их за
образец и приводим к нему остальные 28. У всех правимых `used_count = 0`,
правка ни на кого не влияет.

## Эталон — как должно быть

Карточка `AFFBUDDHA` (и три её брата `_IG`, `_YT`, `_TG`) целиком:

| Поле | Значение | Что означает |
|---|---|---|
| `discount_pct` | **50** | скидка 50% |
| `bonus_days` | **0** | бесплатных дней от кода не даём |
| `recurring_months` | **12** | скидка держится 12 месяцев с первой оплаты |
| `applies_to_plans` | **пусто** | код принимается на любом тарифе |
| `applies_to_cycle` | **пусто** | код принимается и на месячной, и на годовой оплате |
| `max_uses` | **пусто** | без лимита применений |
| `expires_at` | **пусто** | без срока годности |
| `is_active` | **да** | включён |
| `is_global` | **нет** | не общий |

Отдельно: у кодов Будды заполнены `partner_id` и `partner_email` — это
привязка к партнёрскому аккаунту, нужна для его выплат. **У кодов площадок
эти поля пустые, так и оставить** — площадкам мы платим напрямую, а не через
реферальную программу.

---

## Группа A — 19 кодов: отличаются двумя полями

Сейчас: `50 / 0 / 12 / pwa_team / monthly`

Поменять:
- `applies_to_plans` → **пусто**
- `applies_to_cycle` → **пусто**

Остальное уже как в эталоне.

```
VOITENKO1  FLOWBRO  KHOMENOK  APTEKA  CPARIP  PSHVETSOV  VLAD_R  VTRAFF
IVANOV  AFF_INSIDE  CPAGRAM1  IGAMING_NEWS  TGQUBIX  ADHUNT1
FBKILLA_SITE  PROTRAFFIC_SITE  TRAFFHUB_SITE  TRCARDINAL_SITE  ADSBASE_SITE
```

## Группа B — 8 кодов: отличаются пятью полями

Сейчас: `99 / 30 / 0 / pwa_team / monthly`

Поменять:
- `discount_pct` 99 → **50**
- `bonus_days` 30 → **0**
- `recurring_months` 0 → **12**
- `applies_to_plans` → **пусто**
- `applies_to_cycle` → **пусто**

```
PARTNEROFF_SITE  voienkoinst  ARBTRAF  PARTNERKIN_SITE
SYSBITRAZH  TIKTOKILLER  PRESSAFF_SITE  SBC_LISBON
```

⚠️ `SBC_LISBON` — вперёд остальных, конференция 29.09.

## Группа C — 1 код: `QIZENBERG`

Сейчас: `50 / 30 / 0 / пусто / monthly`

Поменять:
- `bonus_days` 30 → **0**
- `recurring_months` 0 → **12**
- `applies_to_cycle` → **пусто**

`partner_id` и `partner_email` у него заполнены (реф-код владельца) — **не трогать**.

---

## Не трогать

- **Июльские коды каналов:** `ADHUNT, AFFIN, AFFINSIDE, CPALIKE, CPARIP_old,
  FBKILLA, IGINSIDE, MONEYBEATSEVIL, PACAN, YELLOWWEB, ZOMBIE` + выключенные
  `CPALENTA, CPAGRAM, IGAMINGNEWS`. Условия прежней акции, ссылки на них живут
  в июльских постах.
- **Сам эталон:** `AFFBUDDHA, AFFBUDDHA_IG, AFFBUDDHA_YT, AFFBUDDHA_TG`.
- **Угадываемые и технические:** `FREE, PROMO, PROMOCODE, QUBIX30, MYCODE,
  MYCODE1, BOSS, PIRATE, POCKET, SERG, TEST100, SMOKE99, FREE30, TRON5, KBLLE`
  и случайные строки (`fs-…, fun-…, unused-…, used-…, EITMQ, AK7PU, H6ADQ,
  VKY4W, UI3AY, QNUPU, 52CXI, BGXVM`). Год со скидкой им не даём: иначе цена
  угаданного кода падает с половины одного платежа до половины за год.
- **Выключенные:** `VOITENKO, LAUNCH30, FLOW` — оставить выключенными.

## Почему эталон именно такой

- **Тариф и цикл пустые** — иначе код не принимается вовсе при другом тарифе
  или годовой оплате. Живой случай: клиент #244 по `PARTNEROFF_SITE` покупает
  `tracker_pro` и висит в кассе с полной ценой $358.
- **Месяцев скидки 12** — отсчёт от первой оплаты, не от регистрации.
- **Бонус-дни 0** — подарочный месяц приходит от привязки Telegram (DEV-1883),
  зашит в продукт мимо таблицы промокодов. Дублировать полем кода не нужно.
- **Скидка 50%** — канон BRAND-5.
