Куда: FIN-13 (тело задачи — заменить целиком; вставляет Анастасия сама, по слову владельца 23.09 «пиши всё сама, прикладывай свои доки к таске»)

# FIN-13 — тело задачи (вставить как есть)

**Подтверждение выплат по Consulting Services Agreement от 27.07.2026 — для проверки кошелька**

## Зачем

Кошелёк (кастодиальный сервис) поставил мой вывод на паузу и просит подтвердить, что поступления — это выплаты по договору, который я им показала. Принимают инвойсы и подтверждения оплаты. Я консультант по договору от 27.07.2026, не сотрудник: расчётных листков нет, подтверждаю инвойсами и письмом об оплате.

## Как устроено

Инвойсы компании выставляю **я** за услуги по договору (п. 2.5). Компания платит по ним на Designated Wallet (пп. 4.7–4.8). Инвойс — белый лист A4, PDF, без бланка, подписей и печатей. Подтверждение оплаты — отдельное простое письмо от компании.

## 1. Инвойсы — выставила, приложены к задаче

Номер = дата + порядковый номер за день. Между датой инвойса и оплатой — несколько дней, без выходных. Только оплаченные выплаты; суммы и даты — ровно те, что прошли по чекам в задачах FIN.

| Инвойс | Дата | За что | Сумма, $ | Оплата по факту | Задача |
|---|---|---|---|---|---|
| 2026-07-27-1 | 27.07 (пн) | июль–август, первая выплата по договорённости сторон | 2 500 | 28.07 (вт), $100 + $2 400 | FIN-2 |
| 2026-08-24-1 | 24.08 (пн) | август: фикс 5 000 (п. 4.2) минус зачёт остатка подотчёта по Москве 1 100 (расчёт Kit 27.08: 92 734,53 ₽ по 84,2820) | 3 900 | 27.08 (чт), $3 900 | FIN-7 |

Первый инвойс: договор подписан 27.07, оплата 28.07 — между ними один день, это факт. Слова «аванс» в договоре нет — в инвойсе «первая выплата по договорённости сторон».

Реквизиты в инвойсах — из договора: стороны как в преамбуле, кошелёк — Designated Wallet п. 4.8, ERC-20 0xB7867007bDfe0e6c9Ff718489BD52604218fA3b7. FIN-2 и FIN-7 пришли именно на него.

## 2. Письмо в компанию с просьбой подтвердить оплаты — приложено

По слову владельца: я пишу письмо в компанию с просьбой подтвердить оплаты по инвойсам, компания подтверждает ответом. Ответ — простой текст, по каждому инвойсу: номер, дата, сумма, дата оплаты, сеть и адрес получателя, хеш транзакции, основание — договор от 27.07.2026.

## Отдельно, не про инвойсы — FIN-12 и смена кошелька

FIN-12 (срок 25.09) выставлен на новый адрес 0x0C1E…3c25. По п. 4.8 смена Designated Wallet — письменное уведомление за подписью консультанта, подтверждение компанией звонком, вступает через 5 рабочих дней, перед первым платежом тест 50 USDT. Записи об этой процедуре в FIN-12 нет. Пока её нет — платить на договорный 0xB786…fA3b7 либо сначала оформить смену.

## Приложено

- invoice-2026-07-27-1.pdf, invoice-2026-08-24-1.pdf
- письмо в компанию с просьбой подтвердить оплаты (ниже)
- сопроводительное письмо в кошелёк (ниже)

---

# Письмо в компанию — просьба подтвердить оплаты (от Анастасии на legal@qubix.pro)

Subject: Request for payment confirmation — Consulting Services Agreement dated 27 July 2026

Dear Sirs,

Under the Consulting Services Agreement dated 27 July 2026 between YARD TECH S.A.S. and me as Consultant, I have issued the following invoices, which have been settled in USDT (ERC-20) to the Designated Wallet under Clause 4.8, 0xB7867007bDfe0e6c9Ff718489BD52604218fA3b7. Invoice 2026-08-24-1 is the August monthly fee of USD 5,000.00 less USD 1,100.00 set off against the unspent balance of my expense advance for the Moscow business trip, as calculated by the Company on 27.08.2026:

| Invoice No. | Invoice date | Amount, USD | Paid on | Transaction hash |
|---|---|---|---|---|
| 2026-07-27-1 | 27.07.2026 | 2,500.00 | 28.07.2026 | 0x922d980d75b79691bb0eec654cf26e4e3becaf1ce42360d76a58eeb1cfc3dec8 (100 USDT); 0x0fabbb88c12f906e8fda60afeabfc8fca2d813d796b08cd016fcd6cb2da47abc (2,400 USDT) |
| 2026-08-24-1 | 24.08.2026 | 3,900.00 | 27.08.2026 | 0x6ad8d1a8b121f7ef67bdb29576fa8039d70a864d119b181fb457b379bc74cacc |

My custodial wallet provider has paused a withdrawal and asks for confirmation of the source of these funds. Could you please confirm in writing that the above invoices were paid by YARD TECH S.A.S. to me as consideration for consulting services under the Agreement, stating for each invoice the number, date, amount accrued and amount paid (with the set-off for August), payment date, network, the Company's sending address and the recipient address, and the transaction hash — in the form of the calculation statement provided for in Clause 4.5(a)?

A plain reply by e-mail is sufficient.

Kind regards,
Anastassiya Voitenko
Consultant under the Consulting Services Agreement dated 27 July 2026

---

# Письмо в Wallet Support — черновик

Добрый день.

Уточняю по документу, который я направила ранее: это Consulting Services Agreement — договор об оказании консультационных услуг между мной как независимым консультантом и YARD TECH S.A.S., не трудовой договор. Расчётных листков по нему не существует: оплата идёт по инвойсам, которые я выставляю компании.

Прилагаю: инвойсы №№ 2026-07-27-1 и 2026-08-24-1 и подтверждение компании об оплате (.eml) с датами, суммами, адресами отправителя и получателя и хешами транзакций.

Какого из документов вам достаточно для завершения проверки, или нужен ещё какой-то?

С уважением,
Анастасия Войтенко
