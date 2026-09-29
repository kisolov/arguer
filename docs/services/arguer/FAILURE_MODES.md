# arguer: поведение при сбоях

Описано как есть, включая нежелательное. Исправления здесь не обсуждаются: это отражение кода, а не план работ. Общая схема: исключение из юзкейса доходит до [ErrorHandlingMiddleware](../../../src/presentation/aiogram/error_handling.py).

| Тип исключения | Реакция middleware |
|---|---|
| `BusinessLogicError` | пользователю уходит текст исключения; контекст и **состояние не сбрасываются** |
| любое другое | лог `Неожиданная ошибка` с трассой, пользователю «Ошибка! Обратитесь в техподдержку», **сбрасываются весь контекст (`clear_data`) и состояние** |
| ошибка при отправке самого сообщения об ошибке | уходит в aiogram Dispatcher, который её логирует |

## Исходящие вызовы

| Внешняя система | Как ломается | Что происходит | Где |
|---|---|---|---|
| **GenAPI** | таймаут (`GENAPI_DEFAULT_TIMEOUT_SECONDS`, 30 с), сетевая ошибка, HTTP 4xx/5xx, поле `error` в теле, неожиданная форма ответа | `GenAPIError` (наследник `LanguageModelError`) → `ProcessArgue` логирует и бросает `UnexpectedError` → см. сценарий А | [genapi.py](../../../src/infrastructure/genapi.py), [process_argue.py](../../../src/application/uc/process_argue.py) |
| **GenAPI** | повторы | не выполняются: поля `max_retries` и `enable_compression` в [GenAPIConfig](../../../config.py) нигде не читаются | — |
| **YooKassa** `create_payment` | любая ошибка SDK | не перехватывается → «Неожиданная ошибка», контекст пользователя сброшен; в БД ничего не записано, платежа нет | [send_payment_link.py](../../../src/application/uc/send_payment_link.py) |
| **YooKassa** `create_payment` успех, дальше падает `record_top_up` (БД) | платёж создан в YooKassa, локальной записи нет | пользователь ссылку не получает; платёж остаётся «осиротевшим», обновление баланса его не увидит | там же |
| **YooKassa** `get_payment_status` | любая ошибка SDK | исключение обрывает `RefreshBalance`: уже применённые в этом проходе транзакции остаются применёнными, остальные — нет; popup «Обновлено» не отправляется; контекст диалога сбрасывается как при любой неожиданной ошибке | [refresh_bal.py](../../../src/application/uc/refresh_bal.py) |
| **YooKassa** незнакомый статус | — | трактуется как `PENDING`, транзакция ждёт следующего обновления | [yookassa.py](../../../src/infrastructure/yookassa.py) |
| **Yandex SpeechKit** | любой сбой на шагах загрузки, старта, опроса, разбора | оборачивается в `SpeechRecognitionError("Recognition failed: ...")`, дальше см. сценарий Б | [speechkit.py](../../../src/infrastructure/yandex/s3/speechkit.py) |
| **Yandex SpeechKit** | нет результата за 300 с (опрос раз в 5 с) | `SpeechRecognitionError("Recognition timeout")`; таймаутов на отдельные HTTP-запросы нет, действуют значения по умолчанию aiohttp | там же |
| **Yandex Object Storage** | ошибка загрузки | `Exception("Ошибка загрузки байт ...")` → внутри SpeechKit превращается в `SpeechRecognitionError`. Загруженные объекты не удаляются | [bucket.py](../../../src/infrastructure/yandex/s3/bucket.py) |
| **Скачивание файла Telegram** | не 200, сетевая ошибка | `ValueError("Download failed: ...")`, лог `ERROR` | [web.py](../../../src/infrastructure/web.py) |
| **Расширение файла** | не из списка `mp3/wav/ogg/oga/mp4` | `ValueError("Файлы с расширением ... не поддерживаются")` | там же |
| **Конвертация mp4** (pydub/ffmpeg) | ошибка декодирования, нет ffmpeg | исключение пробрасывается | там же |
| **Redis** | недоступен | `redis.ConnectionError` из `get_token`/`save_token`; внутри распознавания речи превращается в `SpeechRecognitionError` | [redis.py](../../../src/infrastructure/redis.py) |
| **Redis** | токена нет (истёк TTL, не выпускался) | `get_token` вызывает `.decode` у `None` → `AttributeError`; в распознавании речи превращается в `SpeechRecognitionError` | [token_service.py](../../../src/domain/operations/services/token_service.py) |
| **`yc` CLI** | ненулевой код, нет бинаря | `RuntimeError("Failed to create YC IAM token ...")` с командой, stdout и stderr | [cloud_cli.py](../../../src/infrastructure/yandex/cloud_cli.py) |
| **MySQL** | недоступна, дедлок, таймаут | исключение SQLAlchemy наружу; `pool_pre_ping` пересоздаёт «мёртвые» соединения перед использованием; открытый UnitOfWork откатывается | [unit_of_work.py](../../../src/infrastructure/db/unit_of_work.py) |
| **Telegram** | ошибка отправки, удаления, правки сообщения | исключение aiogram пробрасывается как неожиданное. Ошибка на `edit_message_text` при совпадении текста тоже | [message_service.py](../../../src/infrastructure/aiogram/message_service.py) |

## Сценарии

### А. Модель не ответила во время /go

Порядок в [go.py](../../../src/application/uc/go.py): списание → состояние `processing` → распознавание → запрос к модели.

| Что | Итог |
|---|---|
| Баланс | **списан**, возврата нет |
| Сообщение «Идёт обработка...» | удаляется (`finally`) |
| Контекст | накопленные сообщения уже перенесены в `processed`, `unprocessed` пуст. Ответа модели в `processed` нет |
| Состояние | остаётся `processing`: `UnexpectedError` — `BusinessLogicError`, middleware состояние не сбрасывает |
| Следующие сообщения | глотает `processing_input_protection`, **включая `/clear`**. Выход — перезапуск бота (FSM в памяти) |

### Б. Распознавание речи не удалось во время /go

| Что | Итог |
|---|---|
| Баланс | **списан**, возврата нет |
| Сообщение «Идёт обработка...» | **остаётся** в чате: `try/finally` в `Go` охватывает только вызов модели |
| Контекст и состояние | сбрасываются (исключение неожиданное) — накопленная переписка потеряна |

### В. Недостаточно средств

`InsufficientFunds` бросается атомарным `UPDATE` внутри UnitOfWork на шаге списания, до смены состояния. Записи транзакции нет, баланс не изменён, контекст остаётся; пользователь видит «Не хватает токенов! Пополнить баланс - /bal».

### Г. Сбой между двумя записями биллинга

Баланс и запись транзакции пишутся в одном UnitOfWork. Ошибка на записи транзакции откатывает и баланс; наружу уходит исходное исключение.

### Д. Параллельная обработка одной транзакции

Два одновременных «обновить»: `transition_pending` выигрывает один, второй читает уже проставленные статус и баланс и ничего не начисляет.

### Е. Падение на старте

| Что падает | Итог |
|---|---|
| `create_schema` (БД недоступна) | исключение из `main`, `finally` закрывает engine; процесс завершается |
| первый выпуск IAM-токена (`yc`, Redis) | исключение из `refresh_token_and_schedule` до polling; процесс завершается |
| регулярное обновление токена (раз в час) | исключение в потоке APScheduler логируется планировщиком, бот продолжает работать; старый токен живёт `lifetime_in_seconds` = 3600 с, интервал обновления тоже 3600 с, запаса нет — при задержке обновления ключ в Redis успевает истечь |

## Блокировка event loop

Вызовы, которые исполняются синхронно в потоке event loop и на время выполнения останавливают все остальные апдейты:

| Вызов | Где |
|---|---|
| весь клиент Redis (`get`/`set`/`delete`/`exists`) | [redis.py](../../../src/infrastructure/redis.py) |
| конвертация видео pydub/ffmpeg (`async def`, но работа синхронная) | [web.py](../../../src/infrastructure/web.py) `_convert_video_to_audio_bytes` |
| `subprocess.run` для `yc` | [cloud_cli.py](../../../src/infrastructure/yandex/cloud_cli.py); вызывается из потока планировщика и один раз при старте, поэтому на апдейты не влияет |

Вынесены в потоки (`asyncio.to_thread`): GenAPI (`requests`), YooKassa SDK, boto3.

## Известные несоответствия

| Что | Состояние |
|---|---|
| В теле запроса SpeechKit блок `specification` вложен дважды (`config.specification.specification`) — так собирается в [speechkit.py](../../../src/infrastructure/yandex/s3/speechkit.py) | Соответствие реальному API в этой версии не проверялось |
| Ключ идемпотентности YooKassa генерируется заново на каждый вызов | повтор `create_payment` = второй платёж |
