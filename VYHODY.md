# Выходы размещений — ручная книга

Что это: список всех выходов по кругам закупки. Из него `scripts/zamer.py`
считает воронку по каждому выходу и собирает таблицу для реестра замеров.

Правится руками. Строка заводится, когда размещение **вышло**, а не когда
оплачено: пока факта выхода нет, ноль регистраций в замер не берётся.

Формат: `дата_выхода · канал · круг · задача · сумма · коды через запятую`

Коды — все варианты одного канала: старый реф-код без подарка и новый
подарочный. Если код один — один и пишем.

Источники строк: `BUDGET.md` (суммы и даты оплат), `CONTENT-40` (ссылки на
вышедшие листинги), `MARKETING-63` (июльская волна с датами выхода постов).

---

## Июль 2026 · launch, Фаза 1

- 2026-07-03 · CPAGRAM · посев · MARKETING-34 · 280 · CPAGRAM
- 2026-07-03 · Pacan · посев · MARKETING-32 · 500 · PACAN
- 2026-07-04 · Zombie Traffic · посев · MARKETING-62 · 280 · ZOMBIE
- 2026-07-07 · .Aff Inside · посев · MARKETING-28 · 1222 · AFFINSIDE
- 2026-07-08 · adhunt · посев · MARKETING-22 · 500 · ADHUNT
- 2026-07-09 · iGaming News · посев · MARKETING-23 · 900 · IGAMINGNEWS
- 2026-07-10 · FB-killa · посев · MARKETING-20 · 490 · FBKILLA

## Сентябрь 2026 · посевы

- 2026-08-31 · CPAGRAM · посев · CONTENT-24 · 800 · CPAGRAM, CPAGRAM1
- 2026-08-31 · iGaming News · посев · CONTENT-23 · 900 · IGAMINGNEWS, IGAMING_NEWS
- 2026-09-01 · .Aff Inside · посев · CONTENT-34 · 1222 · AFFINSIDE, AFF_INSIDE
- 2026-09-02 · adhunt · посев · CONTENT-37 · 500 · ADHUNT, ADHUNT1

## Сентябрь 2026 · листинги

- 2026-09-02 · FB-killa · листинг · CONTENT-26 · 1370 · FBKILLA_SITE
- 2026-09-02 · TraffHub · листинг · CONTENT-27 · 100 · TRAFFHUB_SITE
- 2026-09-07 · Partneroff · листинг · CONTENT-36 · 500 · PARTNEROFF_SITE
- 2026-09-10 · Партнеркин · листинг · CONTENT-35 · 299 · PARTNERKIN_SITE

## Оплачено, выход не зафиксирован — в замер не идёт

Строки заводятся сюда, пока в CONTENT-40 не проставлена ссылка на живую
карточку. Как появится — переносятся наверх с датой выхода.

- Traffic Cardinal · листинг + обзор · CONTENT-28 · 850 · TRCARDINAL_SITE
- ProTraffic · листинг + обзор · CONTENT-29 · 950 · PROTRAFFIC_SITE
- AffTimes · листинг + обзор · CONTENT-30 · 950 · —
- Pressaff · пакет услуг на год · CONTENT-31 · 2000 · PRESSAFF_SITE
- Хоменюк · интеграция · MARKETING-83 · 8900 · KHOMENOK
