# arguer: сценарии

Обозначения: `MW` — middleware, `UC` — usecase, `→` — вызов, `⇒` — запись в хранилище. Состав шагов проверен по коду; ветки сбоев — в [FAILURE_MODES.md](FAILURE_MODES.md).

## 1. Любой апдейт (общий вход)

```
Telegram → aiogram Dispatcher
  → RegistrationMW: EnsureUserExists(chat.id) → UserRepository.get_or_create ⇒ users
  → MappingMW: Message/CallbackQuery → EventContext (голос/кружок: bot.get_file → URL)
  → SessionMW: Session(event, ContextService, MessageService[, PopupService])
  → ErrorHandlingMW
  → обработчик из routes.py → UC
```

Пользователь появляется в БД при первом же апдейте, в том числе при `/start`.

## 2. Сбор контекста (пересылка)

```
пересланное сообщение
  → AddMessageToUnprocessed
      UnprocessedMessageFactory.create(имя отправителя | "hidden", media, text)
      Dialogue из FSM (нет — новый) → проверка лимитов → add_message ⇒ FSM data["unprocessed"]
```

Лимиты из `AppConfig`: число сообщений и суммарная длительность медиа. Превышение — `MessagesLimitExceeded` / `MediaLimitExceeded`, сообщение не добавляется.

## 3. /go — основной сценарий

```
/go → Go
  1. FetchDialogue          нет "unprocessed" → ContextEmpty (ошибка пользователю)
  2. FetchDefendant         нет "defendant" → UndefinedDefendant
       └ route ловит → SendDefendantSelection: состояние defendant_selection + кнопки с именами
            кнопка → SelectDefendant (проверка, что имя среди участников; удаляет меню;
                     ⇒ FSM "defendant"; сброс состояния) → Go с шага 1
  3. ChargeForUsage         cost = default + секунды·k + символы·k
       BillingService.charge_for_dialogue → UnitOfWork: списание + запись транзакции (шаг 3а)
       MessageService.notify_charge
  4. состояние processing
  5. сообщение «Идёт обработка...»
  6. ProcessUnprocessed     ArgueService.create_from_dialogue (голос → текст параллельно)
                            clear_data; если был processed_before — склейка Argue
                            ⇒ FSM "processed", "defendant"
  7. ProcessArgue           LLMDisputeResolver.resolve → GenAPI
  8. finally: удалить «Идёт обработка...»
  9. HandleResolution       отправить ответ; Argue += реплика assistant ⇒ FSM "processed"
 10. ShowContextInfo        размер контекста
 11. сброс состояния
```

Шаг 3а, внутри одного `async with unit_of_work()`:

```
users.change_balance(user.id, -cost)    условный UPDATE, при нехватке — InsufficientFunds
transactions.store(status=COMPLETED, category=USAGE)
commit (выход без исключения) | rollback (любое исключение)
```

Повторный `/go` после ответа продолжает тот же спор: `processed` копится, новые пересланные сообщения добавляются к нему.

## 4. Пополнение

```
кнопка «Пополнить» → SendPricesMenu: BuyOptionsRepository.get_all → меню пакетов
кнопка пакета      → SendPaymentLink
    BuyOptionsRepository.get(index)
    PaymentGateway.create_payment(price, description)        → YooKassa
    BillingService.record_top_up ⇒ transactions (PENDING, uuid = id платежа)
    ссылка на оплату пользователю
пользователь платит вне бота
кнопка 🔄 (/bal → update) → RefreshBalance
    TransactionRepository.get_pending_transactions_for(user.id)
    для каждой с uuid: PaymentGateway.get_payment_status(uuid)
        COMPLETED → BillingService.apply_transaction  (шаг 4а)
                    session.event.user = transaction.user; обновить меню баланса
        CANCELED  → BillingService.cancel_transaction
        PENDING   → ничего
    popup «Обновлено»
```

Начисление происходит только по нажатию 🔄. Вебхука YooKassa нет, фонового опроса нет: оплаченный, но необновлённый платёж остаётся `PENDING`.

Шаг 4а, `apply_transaction` для существующей транзакции, один `unit_of_work`:

```
transactions.transition_pending(id, COMPLETED)     compare-and-set из PENDING
  True  → users.change_balance(user.id, +amount)
  False → баланс не трогаем, читаем текущие статус и баланс (её уже обработал параллельный вызов)
commit
```

## 5. Токен Yandex Cloud

```
main: RefreshToken(YCCLIWrapper, TokenService).execute() — синхронно, до polling
   yc iam create-token → Token(value, 3600) → TokenService.save_token ⇒ Redis "yandex_iam:default", TTL 3600
CronScheduler: то же раз в час в потоке APScheduler
YandexSpeechKit: перед каждым запросом TokenService.get_token()
```
