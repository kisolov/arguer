# Карта системы

Состояние на текущей ветке. Что решено и почему — в [arguer/DESIGN.md](arguer/DESIGN.md).

Система состоит из **одного сервиса** — Telegram-бота [arguer](arguer/ARCHITECTURE.md). Микросервисов и общих межсервисных сценариев нет, поэтому корневых `DESIGN.md` и `DATA_FLOWS.md` нет: всё лежит в [arguer/](arguer/ARCHITECTURE.md).

## Что делает сервис

Пользователь пересылает боту переписку с оппонентом (текст, голосовые, кружки), выбирает, кого защищать, и командой `/go` получает от языковой модели список аргументов. Каждый запрос списывает «звёзды» ✨ с внутреннего баланса; баланс пополняется через YooKassa.

## Внешние системы

| Система | Зачем | Порт (домен) | Адаптер |
|---|---|---|---|
| Telegram Bot API | приём апдейтов, отправка сообщений | `MessageService`, `ContextService`, `PopupService` | [infrastructure/aiogram](../../src/infrastructure/aiogram/) |
| MySQL 8 | пользователи и транзакции | `UserRepository`, `TransactionRepository`, `UnitOfWork` | [infrastructure/db](../../src/infrastructure/db/) |
| Redis 7 | кэш IAM-токена Yandex Cloud; FSM aiogram (контекст диалога и состояния) | `KeyValueStorage`, `RedisStorage` aiogram | [redis.py](../../src/infrastructure/redis.py) |
| GenAPI | языковая модель | `LanguageModelInterface` | [genapi.py](../../src/infrastructure/genapi.py) |
| Yandex SpeechKit + Object Storage | распознавание голоса | `SpeechRecognitionInterface` | [yandex/s3/speechkit.py](../../src/infrastructure/yandex/s3/speechkit.py) |
| Yandex Cloud CLI (`yc`) | выпуск IAM-токена | `TokenProvider` | [yandex/cloud_cli.py](../../src/infrastructure/yandex/cloud_cli.py) |
| YooKassa | оплата пополнений | `PaymentGateway` | [yookassa.py](../../src/infrastructure/yookassa.py) |

## Развёртывание

| Что | Где |
|---|---|
| Контейнеры `telegram-bot`, `mysql`, `redis`, `phpmyadmin` (профиль `dev`) | [docker-compose.yaml](../../docker-compose.yaml) |
| Образ бота: python 3.12, `ffmpeg`, `yc` CLI, точка входа `python main.py` | [docker/bot/Dockerfile](../../docker/bot/Dockerfile) |
| Команды `make up`, `up-dev`, `down`, `log` | [Makefile](../../Makefile) |
| Конфигурация из `.env` (по классу на подсистему, секреты — `SecretStr`) | [config.py](../../config.py) |
| SQL-миграция для существующей БД (Alembic нет) | [sql/001_users_unique_telegram_id.sql](../../sql/001_users_unique_telegram_id.sql) |
| CI | [.github/workflows](../../.github/workflows/) |

Процесс один: aiogram long polling. Горизонтальное масштабирование не рассматривалось; что произойдёт при нескольких копиях — в [arguer/INVARIANTS.md](arguer/INVARIANTS.md).
