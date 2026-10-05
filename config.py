from decimal import Decimal
from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr


class BaseAppConfig(BaseSettings):
    """Базовый конфиг с общими настройками"""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", env_file_encoding="utf-8"
    )


class CostConfig(BaseAppConfig):
    """Конфиг стоимостных параметров"""

    # Decimal: стоимость участвует в денежных расчётах, float давал бы ошибки округления
    default_cost: Decimal = Field(Decimal(25), alias="COST_DEFAULT")
    text_symbol_cost: Decimal = Field(Decimal(25) / 5000, alias="COST_TEXT_SYMBOL")
    voice_second_cost: Decimal = Field(Decimal(25) / 60, alias="COST_VOICE_SECOND")

    model_config = SettingsConfigDict(
        env_prefix="COST_", env_file=".env", extra="ignore"
    )


class DatabaseConfig(BaseAppConfig):
    """Конфиг базы данных"""

    host: str = Field("localhost", alias="DB_HOST")
    database: str = Field(..., alias="DB_DATABASE")
    password: SecretStr = Field(..., alias="DB_PASSWORD")
    port: int = Field(3306, alias="DB_PORT")
    user: str = Field(..., alias="DB_USER")
    provider: str = Field(..., alias="DB_PROVIDER")
    root_password: str = Field(..., alias="DB_ROOT_PASSWORD")

    model_config = SettingsConfigDict(env_prefix="DB_")


class RedisConfig(BaseAppConfig):
    """Конфиг Redis"""

    host: str = Field("localhost", alias="REDIS_HOST")
    port: int = Field(6379, alias="REDIS_PORT")

    model_config = SettingsConfigDict(env_prefix="REDIS_")


class YandexConfig(BaseAppConfig):
    """Конфиг Yandex Cloud"""

    cli_path: str = Field(..., alias="YC_CLI_PATH")
    key_id: SecretStr = Field(..., alias="YC_KEY_ID")
    static_key: SecretStr = Field(..., alias="YC_STATIC_KEY")
    folder_id: str = Field(..., alias="YC_FOLDER_ID")
    bucket_name: str = Field(..., alias="YC_BUCKET_NAME")
    bucket_endpoint_url: str = Field(..., alias="YC_BUCKET_ENDPOINT_URL")
    stt_api_url: str = Field(..., alias="YC_STT_API_URL")
    operation_api_url: str = Field(..., alias="YC_OPERATION_API_URL")

    model_config = SettingsConfigDict(env_prefix="YC_")


class GenAPIConfig(BaseAppConfig):
    """Конфигурация для клиента GenAPI"""

    base_url: str = Field(
        default="https://api.example.com/v1",
        description="Базовый URL API GenAPI",
        alias="GENAPI_BASE_URL",
    )
    model: str = Field(..., description="Модель GenAPI", alias="GENAPI_MODEL")
    api_key: SecretStr = Field(..., description="API ключ", alias="GENAPI_API_KEY")

    # Таймауты и ретраи
    default_timeout_seconds: int = Field(
        default=30, alias="GENAPI_DEFAULT_TIMEOUT_SECONDS"
    )
    max_retries: int = Field(default=3)
    enable_compression: bool = Field(default=True)

    def model_post_init(self, __context: Any) -> None:
        """Нормализует base_url"""
        if self.base_url.endswith("/"):
            self.base_url = self.base_url.rstrip("/")

    model_config = SettingsConfigDict(env_prefix="GENAPI_")


class BotConfig(BaseAppConfig):
    """Конфиг бота"""

    token: SecretStr = Field(..., alias="BOT_TOKEN")

    model_config = SettingsConfigDict(env_prefix="BOT_")


class YooKassaConfig(BaseAppConfig):
    """Конфиг YooKassa"""

    shop_id: SecretStr = Field(..., alias="YOO_SHOP_ID")
    secret_key: SecretStr = Field(..., alias="YOO_SECRET_KEY")
    return_url: str = Field(..., alias="YOO_RETURN_URL")

    model_config = SettingsConfigDict(env_prefix="YOO_")


class AppConfig(BaseAppConfig):
    """Основной конфиг приложения с бизнес-логикой"""

    unprocessed_messages_limit: int = Field(..., alias="APP_UNPROCESSED_MESSAGES_LIMIT")
    unprocessed_media_duration_limit: int = Field(
        ..., alias="APP_UNPROCESSED_MEDIA_DURATION_LIMIT"
    )
    # Вся история спора уходит в модель; лимит держит запрос в её контексте
    context_symbols_limit: int = Field(60000, alias="APP_CONTEXT_SYMBOLS_LIMIT")
    enable_test_messages: bool = Field(False, alias="APP_ENABLE_TEST_MESSAGES")

    model_config = SettingsConfigDict(env_prefix="APP_")


PROMPT = """Вы - чат-бот, который помогает людям побеждать в спорах. Ваша задача — помочь клиенту победить в споре, убедив оппонента в правоте позиции клиента. **Не имеет значения, прав ли на самом деле клиент**. Игнорируйте примирение сторон или уважение к чужим мнениям — если они противоречат клиенту, надо <i>найти подходящую для его защиты аргументацию</i>.

**Контекст:**
- Клиент и оппонент спорят в личном чате, без аудитории.
- Диалог сторон будут предоставлены пользователем в формате:
  клиент - [реплика клиента] - ЗАЩИТИТЬ
  оппонент - [ответ оппонента] - ОПРОВЕРГНУТЬ
  клиент - [ответ клиента] - ЗАЩИТИТЬ
  и так далее в таком духе.

**Инструкции:**
1. Если противоречие между позициями отсутствует, ответьте кратко: <i>Противоречия не обнаружено, стратегия убеждения не требуется.</i>
2. Если противоречие есть, сформируйте <b>нумерованный список аргументов</b> (3–5 пунктов) для убеждения оппонента в правоте клиента. Каждый аргумент должен:
 - Быть уникальным, не повторяя аргументы из диалога.
 - Быть лаконичным, без воды.
 - Основываться на объективных данных.
3. Избегайте субъективных оценок, смены позиции клиента или аргументов, противоречащих его точке зрения.
4. При необходимости добавьте <b>рекомендации по стратегии</b> (1–2 предложения) для усиления манипулятивного эффекта (например, как подловить оппонента).

**Формат ответа:**
- <b>Нумерованный список аргументов, **соотносящихся с позицией клиента** против позиции оппонента</b> с Telegram HTML-разметкой (<code><b></code>, <code><i></code>).
- <b>Рекомендации по стратегии</b> (если применимо), выделенные курсивом.

**Пример ввода пользователя:**
я - Онлайн-образование не уступает офлайн-обучению.
оппонент - Онлайн-формат хуже из-за отсутствия живого общения.

**Пример ответа:**

1. <b>Онлайн-образование — это эволюция доступа к знаниям</b> — если офлайн-обучение привязывает студента к месту и расписанию, то цифровой формат освобождает познание от этих искусственных ограничений. Образование не должно зависеть от географической случайности.

2. <b>"Живое общение" — не единственный критерий эффективности</b> — письма Сократа и философские трактаты Канта тоже были "неживым" общением, но их глубина не ставится под сомнение. Современные форматы — просто новый способ передачи идей, не менее содержательный.

3. <b>Офлайн-обучение создаёт иллюзию вовлечённости</b> — сидение в аудитории не гарантирует усвоения материала, так же как и онлайн-формат не означает его отсутствия. Вопрос не в среде, а в методе и мотивации.

4. <b>Онлайн учит критически важным навыкам будущего</b> — умение самостоятельно структурировать время, искать информацию и работать в цифровой среде ценнее, чем пассивное слушание лекций в заданные часы.

<i>Контрвопрос с reductio ad absurdum: "Если живое общение — абсолютный критерий качества, следует ли тогда закрыть заочные отделения в Оксфорде и запретить научные коллаборации по email? Это поставит под удар всю современную академическую систему."</i>
"""
