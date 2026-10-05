from dependency_injector import providers

from di import Container
from tests.mocks import (
    MockMediaHandler,
    MockLanguageModel,
    InMemoryUserRepository,
    InMemoryTransactionRepository,
    InMemoryUnitOfWork,
)
from tests.test_config import TestSettings


class TestContainer(Container):
    __test__ = False  # контейнер зависимостей, а не набор тестов

    # ---- configs ----
    test_config = providers.Singleton(TestSettings)

    # ---- mocks ----
    media_handler_mock = providers.Singleton(MockMediaHandler)
    llm_mock = providers.Singleton(MockLanguageModel)
    user_repo_mock = providers.Singleton(InMemoryUserRepository)
    transaction_repo_mock = providers.Singleton(InMemoryTransactionRepository)
    uow_mock = providers.Factory(
        InMemoryUnitOfWork, user_repo_mock, transaction_repo_mock
    )

    # ---- overrides ----

    Container.interfaces.media_handler.override(media_handler_mock)
    Container.interfaces.llm.override(llm_mock)
    Container.interfaces.user_repository.override(user_repo_mock)
    Container.interfaces.transaction_repository.override(transaction_repo_mock)
    Container.interfaces.unit_of_work.override(uow_mock)


container = TestContainer()
container.wire(packages=["tests.cases"])
