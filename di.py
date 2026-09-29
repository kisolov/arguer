import aiogram
from aiogram.client.default import DefaultBotProperties
from dependency_injector import containers, providers
from redis import Redis

from config import (
    CostConfig,
    GenAPIConfig,
    RedisConfig,
    YandexConfig,
    PROMPT,
    DatabaseConfig,
    BotConfig,
    YooKassaConfig,
    AppConfig,
)
from src.domain.operations import (
    TokenService,
    LLMDisputeResolver,
    CostCalculator,
    BillingService,
    ArgueService,
)
from src.domain.ports import (
    Scheduler,
    MediaHandler,
    LanguageModelInterface,
    PaymentGateway,
    UnitOfWork,
)

from src.domain.ports.repositories import (
    KeyValueStorage,
    UserRepository,
    TransactionRepository,
    BuyOptionsRepository,
)

from src.infrastructure import (
    RedisStorage,
    S3ClientSettings,
    YandexBucket,
    YandexSpeechKit,
    WebMediaHandler,
    GenAPIClient,
    CronScheduler,
    YCCLIWrapper,
    Database,
    SqlUserRepository,
    SqlTransactionRepository,
    SqlUnitOfWork,
    YooKassaGateway,
)
from src.infrastructure.memory import InMemoryBuyOptionsRepository


class ConfigContainer(containers.DeclarativeContainer):
    """Контейнер для хранения всех конфигураций приложения"""

    cost_config = providers.Singleton(CostConfig)
    genapi_config = providers.Singleton(GenAPIConfig)
    redis_config = providers.Singleton(RedisConfig)
    db_config = providers.Singleton(DatabaseConfig)
    bot_config = providers.Singleton(BotConfig)
    yandex_config = providers.Singleton(YandexConfig)
    yoo_config = providers.Singleton(YooKassaConfig)
    app_config = providers.Singleton(AppConfig)

    prompt = providers.Object(PROMPT)


class AdaptersContainer(containers.DeclarativeContainer):
    """Контейнер инфраструктурных адаптеров и внешних сервисов"""

    config = providers.DependenciesContainer()
    interfaces = providers.DependenciesContainer()

    # Redis
    redis_client = providers.Singleton(
        Redis,
        host=config.redis_config.provided.host,
        port=config.redis_config.provided.port,
    )
    redis_storage = providers.Singleton(RedisStorage, redis_client=redis_client)

    # Yandex Cloud
    s3_settings = providers.Singleton(
        S3ClientSettings,
        bucket_name=config.yandex_config.provided.bucket_name,
        access_key_id=config.yandex_config.provided.key_id.provided.get_secret_value.call(),
        secret_access_key=config.yandex_config.provided.static_key.provided.get_secret_value.call(),
        endpoint_url=config.yandex_config.provided.bucket_endpoint_url,
    )

    yandex_bucket = providers.Singleton(YandexBucket, settings=s3_settings)
    yccli_wrapper = providers.Singleton(
        YCCLIWrapper, yc_cli_path=config.yandex_config.provided.cli_path
    )

    yandex_iam_repository = providers.Singleton(
        TokenService, storage=interfaces.key_value_storage, key_prefix="yandex_iam"
    )

    speech_kit = providers.Singleton(
        YandexSpeechKit,
        bucket=yandex_bucket,
        settings=config.yandex_config.provided,
        iam_repo=yandex_iam_repository,
    )

    # GenAPI
    genapi_client = providers.Singleton(
        GenAPIClient, settings=config.genapi_config.provided
    )

    # Web
    web_media_handler = providers.Singleton(
        WebMediaHandler, speech_recognizer=speech_kit
    )

    # SQL (SQLAlchemy)
    database = providers.Singleton(Database.from_config, config.db_config)
    sql_user_repo = providers.Singleton(SqlUserRepository, database)
    sql_transaction_repo = providers.Singleton(SqlTransactionRepository, database)
    # UnitOfWork: новый экземпляр на сценарий (своя сессия и транзакция), поэтому Factory
    sql_unit_of_work = providers.Factory(SqlUnitOfWork, database)

    # Cron
    cron_scheduler = providers.Singleton(CronScheduler)

    # Yoo
    yookassa_payment_gateway = providers.Singleton(
        YooKassaGateway, config.yoo_config.provided
    )

    # In-memory
    in_memory_buy_options_repo = providers.Singleton(InMemoryBuyOptionsRepository)


class InterfacesContainer(containers.DeclarativeContainer):
    """Контейнер для абстрактных интерфейсов"""

    # Абстрактные интерфейсы
    scheduler = providers.AbstractSingleton(Scheduler)
    key_value_storage = providers.AbstractSingleton(KeyValueStorage)
    media_handler = providers.AbstractSingleton(MediaHandler)
    llm = providers.AbstractSingleton(LanguageModelInterface)
    user_repository = providers.AbstractSingleton(UserRepository)
    transaction_repository = providers.AbstractSingleton(TransactionRepository)
    buy_options_repository = providers.AbstractSingleton(BuyOptionsRepository)
    payment_gateway = providers.AbstractSingleton(PaymentGateway)
    unit_of_work = providers.AbstractFactory(UnitOfWork)


class CoreContainer(containers.DeclarativeContainer):
    """Контейнер бизнес-логики приложения"""

    config = providers.DependenciesContainer()
    interfaces = providers.DependenciesContainer()

    # Сервисы бизнес-логики
    cost_calculator = providers.Singleton(CostCalculator, config.cost_config)

    dispute_resolver = providers.Singleton(
        LLMDisputeResolver, llm=interfaces.llm, base_prompt=config.prompt
    )

    billing_service = providers.Singleton(
        BillingService,
        transaction_repository=interfaces.transaction_repository,
        unit_of_work=interfaces.unit_of_work.provider,
        cost_calculator=cost_calculator,
    )

    argue_service = providers.Singleton(
        ArgueService, media_handler=interfaces.media_handler
    )


class Container(containers.DeclarativeContainer):
    """Главный контейнер"""

    config = providers.Container(ConfigContainer)
    interfaces = providers.Container(InterfacesContainer)
    adapters = providers.Container(
        AdaptersContainer, config=config, interfaces=interfaces
    )
    core = providers.Container(CoreContainer, config=config, interfaces=interfaces)

    interfaces.scheduler.override(adapters.cron_scheduler)
    interfaces.key_value_storage.override(adapters.redis_storage)
    interfaces.media_handler.override(adapters.web_media_handler)
    interfaces.llm.override(adapters.genapi_client)
    interfaces.user_repository.override(adapters.sql_user_repo)
    interfaces.transaction_repository.override(adapters.sql_transaction_repo)
    interfaces.unit_of_work.override(adapters.sql_unit_of_work)
    interfaces.buy_options_repository.override(adapters.in_memory_buy_options_repo)
    interfaces.payment_gateway.override(adapters.yookassa_payment_gateway)
    bot = providers.Singleton(
        aiogram.Bot,
        token=providers.Callable(
            lambda bot_config: bot_config.token.get_secret_value(), config.bot_config
        ),
        default=DefaultBotProperties(parse_mode="html"),
    )
    dp = providers.Singleton(aiogram.Dispatcher)


container = Container()
