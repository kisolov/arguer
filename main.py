import asyncio
from datetime import timedelta
from aiogram import Dispatcher, Bot
from dependency_injector.wiring import inject, Provide
from di import container, Container
from logs import logger
from src.application import RefreshToken
from src.domain.operations import TokenService
from src.domain.ports import Scheduler
from src.domain.ports.repositories import UserRepository
from src.infrastructure import Database, YCCLIWrapper
from src.presentation.aiogram import (
    RegistrationMiddleware,
    setup_routes,
    MappingMiddleware,
    SessionMiddleware,
    ErrorHandlingMiddleware,
)


def refresh_token_and_schedule(
    scheduler: Scheduler,
    yccli_wrapper: YCCLIWrapper,
    token_service: TokenService,
):
    task = RefreshToken(yccli_wrapper, token_service).execute

    task()

    scheduler.schedule_every(timedelta(hours=1), task)


@inject
async def main(
    bot: Bot = Provide[Container.bot],
    dp: Dispatcher = Provide[Container.dp],
    scheduler: Scheduler = Provide[Container.interfaces.scheduler],
    yccli_wrapper: YCCLIWrapper = Provide[Container.adapters.yccli_wrapper],
    token_service: TokenService = Provide[Container.adapters.yandex_iam_repository],
    user_repo: UserRepository = Provide[Container.interfaces.user_repository],
    database: Database = Provide[Container.adapters.database],
):
    await database.create_schema()

    refresh_token_and_schedule(scheduler, yccli_wrapper, token_service)

    registration_mw = RegistrationMiddleware(user_repo)
    mapping_mw = MappingMiddleware()
    session_mw = SessionMiddleware()
    error_mw = ErrorHandlingMiddleware()

    dp.message.middleware.register(registration_mw)
    dp.callback_query.middleware.register(registration_mw)

    dp.message.middleware.register(mapping_mw)
    dp.callback_query.middleware.register(mapping_mw)

    dp.message.middleware.register(session_mw)
    dp.callback_query.middleware.register(session_mw)

    dp.message.middleware.register(error_mw)
    dp.callback_query.middleware.register(error_mw)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    setup_routes(dp)

    try:
        await dp.start_polling(bot)
    finally:
        await database.dispose()


def on_startup():
    logger.info("Бот запущен")


def on_shutdown():
    logger.info("Бот отключен")


if __name__ == "__main__":
    container.wire(modules=[__name__])
    asyncio.run(main())
