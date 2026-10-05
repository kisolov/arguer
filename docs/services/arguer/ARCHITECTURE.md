# arguer: архитектура

Telegram-бот на aiogram 3. Слои: `endpoint → usecase → service → port ← adapter`. Порты лежат в [domain/ports](../../../src/domain/ports/), адаптеры в [infrastructure](../../../src/infrastructure/), сборка в [di.py](../../../di.py), запуск в [main.py](../../../main.py).

Связанные файлы: [DATA_FLOWS.md](DATA_FLOWS.md) · [INVARIANTS.md](INVARIANTS.md) · [FAILURE_MODES.md](FAILURE_MODES.md) · [DESIGN.md](DESIGN.md).

## Слои

| Слой | Путь | Что внутри | Знает о |
|---|---|---|---|
| presentation | [presentation/aiogram](../../../src/presentation/aiogram/) | роутер команд, 4 middleware | usecase, Session |
| application | [application](../../../src/application/) | `Session` и по одному юзкейсу на файл | сервисы и порты домена |
| domain | [domain](../../../src/domain/) | модели, сервисы, порты, исключения | только себя |
| infrastructure | [infrastructure](../../../src/infrastructure/) | адаптеры портов | порты, внешние библиотеки |

Оговорка по слоям: юзкейсы `RefreshBalance`, `SendPaymentLink`, `SendPricesMenu`, `EnsureUserExists` получают порты (`PaymentGateway`, репозитории) напрямую, а не через сервис. Строгое правило «usecase → только service» в проекте не выдержано.

## Сущности домена

Все в [domain/models](../../../src/domain/models/), `@dataclass`, без ORM.

| Сущность | Поля и смысл |
|---|---|
| [User](../../../src/domain/models/user.py) | `telegram_id` (он же id чата), `id` (внутренний, не мержится в БД), `bal` — баланс в ✨, по умолчанию 150 |
| [Transaction](../../../src/domain/models/transaction.py) | `user`, `category` (`TOP_UP`/`USAGE`), `amount` (знак: минус — списание), `status` (`PENDING`/`COMPLETED`/`CANCELED`), `uuid` — id платежа YooKassa, `created_at` |
| [Dialogue](../../../src/domain/models/dialogue.py) | накопленные пересланные сообщения (`UnprocessedMessage`) до `/go` |
| [UnprocessedMessage](../../../src/domain/models/unprocessed_message.py) | `speaker` + `text` или `media` |
| [Argue](../../../src/domain/models/argue.py) | обработанный диалог: список `Reasoning` + `defendant`; ответ модели дописывается как реплика `assistant` |
| [Reasoning](../../../src/domain/models/reasoning.py), [Speaker](../../../src/domain/models/speaker.py) | реплика; говорящий (равенство и хэш по имени) |
| [Media](../../../src/domain/models/media.py) | `url`, `duration` в секундах |
| [BuyOption](../../../src/domain/models/buy_option.py) | пакет пополнения: сколько ✨, цена в ₽ |
| [EventContext](../../../src/domain/models/event_ctx.py), [MessageContext](../../../src/domain/models/message_ctx.py), [PopupContext](../../../src/domain/models/popup_ctx.py) | нейтральное к Telegram описание события, адресата сообщения, всплывашки |
| [ChatMessage](../../../src/domain/models/chat_message.py), [Token](../../../src/domain/models/token.py) | сообщение для модели (`system`/`user`/`assistant`); IAM-токен с TTL |

Исключения — [domain/exceptions.py](../../../src/domain/exceptions.py): `BusinessLogicError` (текст показывается пользователю: `InsufficientFunds`, `ContextEmpty`, `UndefinedDefendant`, `MessagesLimitExceeded`, `MediaLimitExceeded`, `UnexpectedError`), `LanguageModelError`, `RecordNotFound`.

## Схема БД

Таблицы создаёт приложение при старте (`create_all`), модели — [db/models.py](../../../src/infrastructure/db/models.py).

| Таблица | Колонки |
|---|---|
| `users` | `id` PK, `telegram_id` BIGINT **UNIQUE** (`ix_users_telegram_id`), `bal` DECIMAL(14,2) (по умолчанию 150.00) |
| `transactions` | `id` PK, `uuid` VARCHAR(255) NULL, **`user`** FK→`users.id` (колонка так и называется), `status` и `category` VARCHAR(255) со значениями `.value` в нижнем регистре, `amount` DECIMAL(14,2), `created_at` DATETIME default `CURRENT_TIMESTAMP` |

## Порты → адаптеры

Привязка порта к адаптеру — только `.override` в [di.py](../../../di.py).

| Порт | Адаптер | Внешняя система |
|---|---|---|
| [LanguageModelInterface](../../../src/domain/ports/llm.py) | [GenAPIClient](../../../src/infrastructure/genapi.py) | GenAPI |
| [MediaHandler](../../../src/domain/ports/media_handler.py) | [WebMediaHandler](../../../src/infrastructure/web.py) | скачивание файла по URL Telegram, ffmpeg (pydub) |
| [SpeechRecognitionInterface](../../../src/domain/ports/speech_recognition.py) | [YandexSpeechKit](../../../src/infrastructure/yandex/s3/speechkit.py) | Yandex Object Storage + SpeechKit |
| [TokenProvider](../../../src/domain/ports/token_provider.py) | [YCCLIWrapper](../../../src/infrastructure/yandex/cloud_cli.py) | процесс `yc iam create-token` |
| [KeyValueStorage](../../../src/domain/ports/repositories/key_value_storage.py) | [RedisStorage](../../../src/infrastructure/redis.py) | Redis (синхронный клиент) |
| [Scheduler](../../../src/domain/ports/scheduler.py) | [CronScheduler](../../../src/infrastructure/cron.py) | APScheduler в фоновом потоке |
| [UserRepository](../../../src/domain/ports/repositories/user.py) | [SqlUserRepository](../../../src/infrastructure/db/repositories/user.py) | MySQL |
| [TransactionRepository](../../../src/domain/ports/repositories/transaction.py) | [SqlTransactionRepository](../../../src/infrastructure/db/repositories/transaction.py) | MySQL |
| [UnitOfWork](../../../src/domain/ports/unit_of_work.py) | [SqlUnitOfWork](../../../src/infrastructure/db/unit_of_work.py) | MySQL, `Factory` (новый экземпляр на сценарий) |
| [BuyOptionsRepository](../../../src/domain/ports/repositories/buy_options.py) | [InMemoryBuyOptionsRepository](../../../src/infrastructure/memory.py) | нет: четыре пакета зашиты в код |
| [PaymentGateway](../../../src/domain/ports/payment_gateway.py) | [YooKassaGateway](../../../src/infrastructure/yookassa.py) | YooKassa |
| [MessageService](../../../src/domain/ports/message_service.py) | [AiogramMessageService](../../../src/infrastructure/aiogram/message_service.py) | Telegram; тексты — `Texts` в порте, клавиатуры — в адаптере |
| [ContextService](../../../src/domain/ports/context_service.py) | [AiogramContextService](../../../src/infrastructure/aiogram/context_service.py) | FSM aiogram в Redis ([fsm_storage.py](../../../src/infrastructure/aiogram/fsm_storage.py)): контекст диалога и состояние |
| [PopupService](../../../src/domain/ports/popup_service.py) | [AiogramPopupService](../../../src/infrastructure/aiogram/popup_service.py) | `answerCallbackQuery` |

`MessageService`, `ContextService`, `PopupService` создаются на каждый апдейт в `SessionMiddleware`, а не через DI-контейнер.

## Сервисы домена

| Сервис | Ответственность |
|---|---|
| [BillingService](../../../src/domain/operations/services/billing_service.py) | стоимость диалога, списание, начисление платежа, отмена; транзакционная граница через `UnitOfWork` |
| [CostCalculator](../../../src/domain/operations/services/cost_calculator.py) | `default_cost + секунды_голоса·voice_second_cost + символы·text_symbol_cost` |
| [ArgueService](../../../src/domain/operations/services/argue_service.py) | превращает `Dialogue` в `Argue`, параллельно (`asyncio.gather`) распознавая голосовые |
| [LLMDisputeResolver](../../../src/domain/operations/services/llm_dispute_resolver.py) | собирает историю для модели и вызывает `LanguageModelInterface` |
| [TokenService](../../../src/domain/operations/services/token_service.py) | хранение IAM-токена в `KeyValueStorage` под ключом `<prefix>:<id>` |
| [UnprocessedMessageFactory](../../../src/domain/operations/factories/unprocessed_message_factory.py) | создаёт `UnprocessedMessage`; без текста и медиа — `ValueError` |

## Обработчики (роуты)

Все в [routes.py](../../../src/presentation/aiogram/routes.py). Зависимости в обработчики подставляет декоратор `with_deps` из глобального контейнера.

| Триггер | Юзкейс | Условие |
|---|---|---|
| `/start` | [SendInstructions](../../../src/application/uc/send_instructions.py) | — |
| `/bal` | [SendBalanceMenu](../../../src/application/uc/send_balance_menu.py) | — |
| `/ctx` | [ShowContextInfo](../../../src/application/uc/send_context_info.py) | — |
| `/clear` | [ClearContext](../../../src/application/uc/clear_context.py) | — |
| `/go` | [Go](../../../src/application/uc/go.py); при `UndefinedDefendant` — [SendDefendantSelection](../../../src/application/uc/send_defendant_selection.py) | — |
| пересланное сообщение | [AddMessageToUnprocessed](../../../src/application/uc/add_reasoning_to_unprocessed.py) | `forward_from` или `forward_sender_name` |
| `текст (id)` | `AddTestMessageToUnprocessed` | только при `APP_ENABLE_TEST_MESSAGES=true` |
| любое сообщение, кроме `/ctx`, `/start`, `/clear` | пустой обработчик `processing_input_protection` | состояние `processing` |
| кнопка выбора подзащитного | [SelectDefendant](../../../src/application/uc/select_defendant.py), затем `Go` | состояние `defendant_selection` |
| кнопка «Пополнить» (`top_up`) | [SendPricesMenu](../../../src/application/uc/send_prices_menu.py) | — |
| кнопка «Назад» (`buy_options_back`) | `SendBalanceMenu` в существующем сообщении | — |
| кнопка пакета | [SendPaymentLink](../../../src/application/uc/send_payment_link.py) | — |
| кнопка 🔄 (`update`) | [RefreshBalance](../../../src/application/uc/refresh_bal.py) | — |
| раз в час | [RefreshToken](../../../src/application/uc/refresh_token.py) | планировщик, запускается из `main` |

Кто вызывает: любой пользователь Telegram, авторизации нет. Ограничение доступа по спискам или ролям отсутствует.

## Middleware

Порядок регистрации в [main.py](../../../main.py) (для `message` и `callback_query` одинаковый): registration → mapping → session → error handling → обработчик.

| Middleware | Что делает |
|---|---|
| [RegistrationMiddleware](../../../src/presentation/aiogram/registration_middleware.py) | `get_or_create` пользователя по `chat.id`, кладёт в `data["user"]` |
| [MappingMiddleware](../../../src/presentation/aiogram/mapping_middleware.py) | Telegram-событие → `EventContext`; для голоса и кружков получает URL файла |
| [SessionMiddleware](../../../src/presentation/aiogram/session_middleware.py) | собирает `Session` (event + три сервиса Telegram); popup только для нажатий кнопок |
| [ErrorHandlingMiddleware](../../../src/presentation/aiogram/error_handling.py) | `BusinessLogicError` → текст ошибки пользователю; прочее → лог, «Ошибка!», сброс контекста и состояния |

## Жизненный цикл процесса

[main.py](../../../main.py): `create_schema()` → первый выпуск IAM-токена (синхронно, до старта) и расписание раз в 30 минут → регистрация middleware и роутов → `start_polling`. В `finally` — `database.dispose()`.

## Тесты

[tests/](../../../tests/): тесты по слоям с маркерами `application`/`domain`/`infrastructure`, SQL-репозитории и биллинг проверяются на sqlite (`aiosqlite`) в памяти и на файле; MySQL в тестах не участвует. Фикстуры и in-memory реализации портов — [tests/mocks](../../../tests/mocks/).
