# arguer: инварианты и неочевидные правила

Только то, что не читается из имён и сигнатур. Таблицы сущностей — в [ARCHITECTURE.md](ARCHITECTURE.md).

## Деньги

| Правило | Где |
|---|---|
| Баланс меняется приращением в БД: `UPDATE users SET bal = bal + :delta WHERE id = :id AND bal + :delta >= 0`. Снимок баланса из памяти в БД не пишется, поэтому параллельные начисления не теряются | [user.py](../../../src/infrastructure/db/repositories/user.py) `change_balance` |
| Баланс не может стать отрицательным. Нет строки → `RecordNotFound`, есть, но не хватает → `InsufficientFunds` | там же |
| Списание — `amount < 0`, пополнение и возврат — `amount > 0`; `BillingService` знак не проверяет, `open_top_up` берёт `tokens_amount` из пакета. Возврат (`REFUND`) — отдельная транзакция на сумму списания, само списание не меняется | [billing_service.py](../../../src/domain/operations/services/billing_service.py) |
| Новая транзакция (`id is None`) применяется как `COMPLETED` сразу: баланс и запись — в одном UnitOfWork, откат затрагивает обе | `_apply_new` |
| Существующая `PENDING` применяется через compare-and-set `UPDATE ... SET status = :s WHERE id = :id AND status = 'pending'`; побеждает ровно один вызов (`rowcount == 1`), остальные баланс не трогают | [transaction.py](../../../src/infrastructure/db/repositories/transaction.py) `transition_pending` |
| Переданные объекты (`transaction`, `transaction.user`) обновляются только после успешного коммита | `_apply_new`, `_apply_pending` |
| Отмена тоже через compare-and-set: уже `COMPLETED` транзакция отменой не переоткрывается, объекту присваивается фактический статус из БД | `cancel_transaction` |
| `cancel_transaction` идёт не через UnitOfWork: это одна запись без связанных изменений | там же |
| Стоимость запроса — новые сообщения (`unprocessed`: текст и секунды голоса) плюс символы прошлых раундов (`processed`, вместе с прошлыми ответами модели): модель получает всю историю. Голос прошлых раундов уже распознан и считается как текст, поэтому каждый следующий `/go` в том же споре дороже | [billing_service.py](../../../src/domain/operations/services/billing_service.py) `calculate_dialogue_cost` |
| Формула: `default_cost + voice_seconds·voice_second_cost + text_symbols·text_symbol_cost`. Значения по умолчанию: 25✨ + 25✨ за 5000 символов + 25✨ за минуту голоса | [cost_calculator.py](../../../src/domain/operations/services/cost_calculator.py), [config.py](../../../config.py) `CostConfig` |
| Деньги — `Decimal` до сотых (`money()`, округление половины вверх) от конфига до БД. `float` в `money()` — `TypeError`. Цена считается точно и округляется один раз, в конце | [money.py](../../../src/domain/models/money.py) |
| Текст спора ограничен `APP_CONTEXT_SYMBOLS_LIMIT` (60 000): пересылка, после которой история + новые сообщения длиннее лимита, отклоняется `ContextLimitExceeded`. Голос до распознавания не считается, его объём за раунд держит лимит длительности | [add_reasoning_to_unprocessed.py](../../../src/application/uc/add_reasoning_to_unprocessed.py) |

## Транзакции и UnitOfWork

| Правило | Где |
|---|---|
| Выход из `async with uow` без исключения коммитит, с исключением откатывает; коммитом управляет только UnitOfWork | [unit_of_work.py](../../../src/domain/ports/unit_of_work.py) |
| Репозитории внутри UnitOfWork привязаны к его сессии и сами ничего не коммитят. Вне UnitOfWork одна операция репозитория = одна сессия = один коммит | [db/repositories/base.py](../../../src/infrastructure/db/repositories/base.py) |
| `SqlUnitOfWork` — `Factory`: экземпляр на сценарий. `BillingService` получает `unit_of_work.provider` и вызывает его сам. Повторное использование одного экземпляра ломается | [di.py](../../../di.py) |
| `Database` — `Singleton`, не `Resource`: engine создаётся без I/O, закрывает его `main()` в `finally` | [di.py](../../../di.py), [main.py](../../../main.py) |
| Транзакции БД не пересекают вызовы внешних сервисов: платёж в YooKassa создаётся до записи `PENDING`, статус спрашивается до `apply_transaction` | [send_payment_link.py](../../../src/application/uc/send_payment_link.py), [refresh_bal.py](../../../src/application/uc/refresh_bal.py) |

## Пользователи

| Правило | Где |
|---|---|
| `telegram_id` уникален (индекс `ix_users_telegram_id`). В БД, созданной до индекса, он появляется только вручную: [sql/001_users_unique_telegram_id.sql](../../../sql/001_users_unique_telegram_id.sql). `create_all` индекс в существующую таблицу не добавляет | [models.py](../../../src/infrastructure/db/models.py) |
| `get_or_create` защищён двумя слоями: `asyncio.Lock` внутри процесса (действует и без индекса) и уникальный индекс между процессами (проигравший ловит `IntegrityError` и перечитывает запись). Уже зарегистрированный пользователь читается без замка, замок берётся только на регистрацию | `SqlUserRepository.get_or_create` |
| Поиск по `telegram_id` берёт запись с наименьшим `id` (`ORDER BY id LIMIT 1`): при унаследованных дублях всегда выбирается самая старая | `SqlUserRepository._get` |
| Пользователь регистрируется по `chat.id`. В личном чате он равен id пользователя; в группе это был бы id группы, но роуты рассчитаны на личный чат | [registration_middleware.py](../../../src/presentation/aiogram/registration_middleware.py) |
| Стартовый баланс — 150✨: значение по умолчанию в `User.bal` и `models.User.bal`; `_create` берёт `bal` из доменного объекта | [user.py](../../../src/domain/models/user.py) |
| Поля `User.id` и `Transaction.user` помечены `metadata={"ignore": True}` и не переносятся из домена в БД при слиянии (`store` существующей записи) | [base.py](../../../src/infrastructure/db/repositories/base.py) `_merge` |

## Формат данных в БД

| Правило | Где |
|---|---|
| Enum'ы хранятся как VARCHAR(255) со значениями `.value` в нижнем регистре (`pending`, `top_up`, ...), без нативного ENUM и CHECK-ограничения. Формат совместим со строками, записанными ORM, которая была до SQLAlchemy | `_enum` в [models.py](../../../src/infrastructure/db/models.py) |
| FK-колонка `transactions.user` называется `user`, а не `user_id`, по той же причине | там же |
| Деньги (`users.bal`, `transactions.amount`) — `DECIMAL(14,2)`. В БД, созданной с `DOUBLE`, тип меняется вручную: [sql/002_money_decimal.sql](../../../sql/002_money_decimal.sql); `create_all` существующие колонки не трогает | там же |
| `Transaction.user` загружается явно (`selectinload`), `relationship(lazy="raise")`: забытая загрузка падает сразу, а не тихо делает блокирующий запрос | `_WITH_USER` в [transaction.py](../../../src/infrastructure/db/repositories/transaction.py) |
| `created_at` пишется с клиента (`datetime.now()` в домене), `server_default` нужен только для строк, вставленных мимо приложения | [transaction.py](../../../src/domain/models/transaction.py) |
| Провайдер БД: `mysql` (прод, `mysql+aiomysql`, `utf8mb4`, `pool_pre_ping`) и `sqlite` (только тесты, `filename` в `DatabaseConfig` отсутствует). Любое другое значение — `ValueError` | [setup.py](../../../src/infrastructure/db/setup.py) |

## Контекст диалога и состояния

| Правило | Где |
|---|---|
| Контекст хранится в FSM aiogram: ключи `unprocessed` (Dialogue), `defendant` (Speaker), `processed` (Argue), `defendant_options` (варианты, показанные в меню выбора) | [context_service.py](../../../src/infrastructure/aiogram/context_service.py) |
| Хранилище FSM — Redis (`aiogram` `RedisStorage`, асинхронный клиент): контекст и состояния переживают перезапуск. Значения сериализуются pickle + base64, потому что в контексте лежат доменные объекты | [fsm_storage.py](../../../src/infrastructure/aiogram/fsm_storage.py), [di.py](../../../di.py) `dp` |
| Апдейты одного пользователя обрабатываются по очереди (`SimpleEventIsolation`): чтение и запись контекста в Redis не перемежаются, повторный `/go` не начинается, пока идёт первый | [di.py](../../../di.py) `dp` |
| `get` считает «пусто» любое ложное значение (`if not desired`): пустая коллекция или `None` → `KeyError` → `ContextEmpty`/`UndefinedDefendant` | `AiogramContextService.get` |
| Состояния: `processing` (идёт `/go`), `defendant_selection` (ждём выбор кнопкой). Обработчик `processing_input_protection` глотает в `processing` все сообщения, для которых не нашлось обработчика выше | [routes.py](../../../src/presentation/aiogram/routes.py) |
| Порядок обработчиков имеет значение, aiogram проверяет их в порядке регистрации: `/ctx`, `/start` и `/clear` зарегистрированы до защиты и работают в `processing`, остальные команды и пересылки — нет | routes.py |
| `/go` ставит `processing` до списания и снимает его в `finally` при любом исходе | [go.py](../../../src/application/uc/go.py) |
| Кнопка подзащитного несёт номер в `defendant_options`, сохранённых при показе меню, а не имя: имя не помещается в 64 байта `callback_data` и не может содержать `:`. Участники в меню отсортированы по имени. Номер вне меню или участник, которого уже нет в переписке, — `UnknownDefendant` | [select_defendant.py](../../../src/application/uc/select_defendant.py), [send_defendant_selection.py](../../../src/application/uc/send_defendant_selection.py) |
| Пересланное сообщение без имени отправителя (скрытый профиль без `forward_sender_name`) получает имя `hidden`; сообщения всех скрытых сливаются в одного говорящего | [unprocessed_message_factory.py](../../../src/domain/operations/factories/unprocessed_message_factory.py) |
| Сообщение без текста и без голоса/кружка → `ValueError`, а не бизнес-ошибка: попадёт в общий обработчик как «Неожиданная ошибка» | там же |
| Голос и кружок берутся из `voice`/`video_note`; аудио из видео-файла (`mp4`) конвертируется в OGG/Opus через pydub и ffmpeg | [mapping_middleware.py](../../../src/presentation/aiogram/mapping_middleware.py), [web.py](../../../src/infrastructure/web.py) |
| Расширение файла определяется по суффиксу URL; поддерживаются `mp3`, `wav`, `ogg`, `oga`, `mp4` | `WebMediaHandler` |

## Запрос к языковой модели

| Правило | Где |
|---|---|
| Сообщение для модели: `system` (промпт `PROMPT` из [config.py](../../../config.py)) → `assistant` (приветствие-заготовка) → пары `user`/`assistant` | [llm_dispute_resolver.py](../../../src/domain/operations/services/llm_dispute_resolver.py) |
| Реплики защищаемого превращаются в `клиент - <текст> - ЗАЩИТИТЬ`, остальных говорящих — в `оппонент - <текст> - ОПРОВЕРГНУТЬ`, накапливаются в одно `user`-сообщение до ближайшей реплики `assistant` | `_build_dialogue` |
| Реплика говорящего с именем `assistant` считается ответом бота. Пересланный собеседник с именем «assistant» был бы принят за ответ модели | там же, [argue.py](../../../src/domain/models/argue.py) |
| Порт возвращает только текст ответа; при любом сбое — `LanguageModelError`. Формат запроса GenAPI: `POST {base_url}/networks/{model}`, `{"messages": [...], "is_sync": true}`, ответ читается из `response[0].message.content` | [genapi.py](../../../src/infrastructure/genapi.py) |
| Ответ модели — недоверенный HTML (бот создан с `parse_mode="html"`, промпт просит `<b>` и `<i>`). Остаются только `<b> <i> <u> <s> <code>` без атрибутов, остальное экранируется; при несбалансированных тегах часть уходит без разметки. Ответ длиннее 4096 символов режется на несколько сообщений, по строкам | [telegram_html.py](../../../src/infrastructure/aiogram/telegram_html.py) |

## Платежи

| Правило | Где |
|---|---|
| Сумма платежа — `BuyOption.price` в ₽, форматируется `"{:.2f}"`; валюта `RUB`, `capture: true`. Ключ идемпотентности YooKassa — новый `uuid4` на каждый вызов, то есть повтор запроса создаёт второй платёж | [yookassa.py](../../../src/infrastructure/yookassa.py) |
| Статусы YooKassa: `pending`, `waiting_for_capture` → `PENDING`; `succeeded` → `COMPLETED`; `canceled` → `CANCELED`; любой незнакомый → `PENDING` | `STATUS_MAPPING` |
| Транзакция пополнения без `uuid` при обновлении баланса пропускается | `RefreshBalance.execute` |
| Пакеты пополнения зашиты в [memory.py](../../../src/infrastructure/memory.py); в кнопке хранится индекс пакета, поэтому изменение порядка списка ломает кнопки в уже отправленных сообщениях | `Callbacks.BuyOptionSelectionCallback` |

## Несколько экземпляров бота

Один процесс — единственная поддерживаемая конфигурация. Состояние FSM в Redis общее, но очередь апдейтов пользователя (`SimpleEventIsolation`) и замок регистрации локальны процессу. Финансовые операции (`change_balance`, `transition_pending`) атомарны на уровне БД и от числа процессов не зависят.
