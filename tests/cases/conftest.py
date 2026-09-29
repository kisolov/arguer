import os
import pytest

from dotenv import load_dotenv

from tests.test_di import TestContainer

load_dotenv(".env")
load_dotenv("tests/.env.test", override=True)


@pytest.fixture(scope="function", autouse=True)
def validate_environment():
    if os.getenv("ENVIRONMENT") == "production":
        pytest.fail("Tests cannot run in production environment!")


@pytest.fixture(scope="class")
def container():
    cont = TestContainer()
    cont.wire(packages=["tests"])
    yield cont
    cont.interfaces.media_handler.reset_override()
    cont.interfaces.llm.reset_override()
    cont.interfaces.user_repository.reset_override()
    cont.interfaces.transaction_repository.reset_override()
    cont.unwire()
