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

Лимиты из `AppConfig`: число сообщений, суммарная длительность медиа и текст всего спора (`processed` + `unprocessed` + новое сообщение, `APP_CONTEXT_SYMBOLS_LIMIT`). Превышение — `MessagesLimitExceeded` / `MediaLimitExceeded` / `ContextLimitExceeded`, сообщение не добавляется.

## 3. /go — основной сценарий

```
/go → Go
  1. FetchDialogue          нет "unprocessed" → ContextEmpty (ошибка пользователю)
  2. FetchDefendant         нет "defendant" → UndefinedDefendant
       └ route ловит → SendDefendantSelection: ⇒ FSM "defendant_options" (участники по имени);
                       состояние defendant_selection + кнопки с номерами вариантов
            кнопка → SelectDefendant (номер → defendant_options; вариант должен быть среди
                     участников, иначе UnknownDefendant; удаляет меню;
                     ⇒ FSM "defendant"; сброс состояния) → Go с шага 1
  3. запомнить processed_before (для восстановления)
  4. состояние processing   снимается в finally при любом исходе (шаг 12)
  5. ChargeForUsage         cost = default + секунды·k + (символы новых + символы processed_before)·k,
                            Decimal, округление до сотых
       BillingService.charge_for_dialogue → UnitOfWork: списание + запись транзакции (шаг 5а)
       MessageService.notify_charge
  6. сообщение «Идёт обработка...»
  7. ProcessUnprocessed     ArgueService.create_from_dialogue (голос → текст параллельно)
                            clear_data; если был processed_before — склейка Argue
                            ⇒ FSM "processed", "defendant"
  8. ProcessArgue           LLMDisputeResolver.resolve → GenAPI
  9. finally: удалить «Идёт обработка...»
 10. HandleResolution       отправить ответ; Argue += реплика assistant ⇒ FSM "processed"
     сбой на шагах 6–10:    FSM ⇐ unprocessed, defendant, processed_before;
                            BillingService.refund ⇒ transactions (REFUND, +cost);
                            MessageService.notify_refund; исключение наружу
 11. ShowContextInfo        размер контекста
 12. finally: сброс состояния
```

Шаг 5а, внутри одного `async with unit_of_work()`:

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
    BillingService.open_top_up ⇒ transactions (PENDING, uuid пуст)
    PaymentGateway.create_payment(price, description)        → YooKassa
        ошибка → BillingService.cancel_transaction (CANCELED), исключение наружу
    BillingService.attach_payment ⇒ transactions (uuid = id платежа)
    ссылка на оплату пользователю (только после привязки uuid)
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
CronScheduler: то же раз в 30 минут (RefreshToken.INTERVAL) в потоке APScheduler
YandexSpeechKit: перед каждым запросом TokenService.get_token() в asyncio.to_thread;
                 None → SpeechRecognitionError
   загрузка аудио в бакет → распознавание → finally: удаление аудио из бакета
```
