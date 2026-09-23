Куда: YouTrack — новая задача для Ника (промокоды)

# Промокоды каналов: поправить настройки

Замер по админке на 23.09.2026. Правим 28 кодов. У всех `used_count = 0` —
правка ни на кого не влияет.

**Целевое состояние для всех кодов каналов и партнёров:**
скидка **50** · бонус-дни **0** · месяцев скидки **12** · тариф **пусто** · цикл **пусто**

---

## Группа A — 19 кодов: очистить два поля

Сейчас у всех: `50 / 0 / 12 / pwa_team / monthly`

Поменять:
- `applies_to_plans` → **пусто**
- `applies_to_cycle` → **пусто**

Скидка, бонус-дни и месяцы уже верные — не трогать.

```
VOITENKO1  FLOWBRO  KHOMENOK  APTEKA  CPARIP  PSHVETSOV  VLAD_R  VTRAFF
IVANOV  AFF_INSIDE  CPAGRAM1  IGAMING_NEWS  TGQUBIX  ADHUNT1
FBKILLA_SITE  PROTRAFFIC_SITE  TRAFFHUB_SITE  TRCARDINAL_SITE  ADSBASE_SITE
```

## Группа B — 8 кодов: поменять всё

Сейчас у всех: `99 / 30 / 0 / pwa_team / monthly`

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

---

## Не трогать

- **Июльские коды каналов:** `ADHUNT, AFFIN, AFFINSIDE, CPALIKE, CPARIP_old,
  FBKILLA, IGINSIDE, MONEYBEATSEVIL, PACAN, YELLOWWEB, ZOMBIE` + выключенные
  `CPALENTA, CPAGRAM, IGAMINGNEWS`. Это условия прежней акции, ссылки на них
  живут в июльских постах.
- **Коды Будды:** `AFFBUDDHA, AFFBUDDHA_IG, AFFBUDDHA_YT, AFFBUDDHA_TG` — уже
  стоят правильно.
- **Угадываемые и технические:** `FREE, PROMO, PROMOCODE, QUBIX30, MYCODE,
  MYCODE1, BOSS, PIRATE, POCKET, SERG, TEST100, SMOKE99, FREE30, TRON5, KBLLE`
  и случайные строки (`fs-…, fun-…, unused-…, used-…, EITMQ, AK7PU, H6ADQ,
  VKY4W, UI3AY, QNUPU, 52CXI, BGXVM`). Год со скидкой им не даём.
- **Выключенные:** `VOITENKO, LAUNCH30, FLOW` — оставить выключенными.

## Почему так

- **Тариф и цикл пустые** — иначе код не принимается вовсе при другом тарифе
  или годовой оплате. Живой случай: клиент #244 по `PARTNEROFF_SITE` покупает
  `tracker_pro` и висит в кассе с полной ценой $358.
- **Месяцев скидки 12** — отсчёт от первой оплаты.
- **Бонус-дни 0** — подарочный месяц приходит от привязки Telegram (DEV-1883),
  мимо таблицы промокодов. Дублировать не нужно.
- **Скидка 50%** — канон BRAND-5.
