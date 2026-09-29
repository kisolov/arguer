import pytest

from src.domain.models import Token
from src.domain.operations import TokenService
from tests.cases.base import BaseTestGroup
from tests.mocks import InMemoryKeyValueStorage


class TestTokenService(BaseTestGroup):
    @pytest.fixture
    def storage(self):
        return InMemoryKeyValueStorage()

    @pytest.fixture
    def service(self, storage):
        return TokenService(storage, key_prefix="iam")

    def test_saved_token_is_readable_and_has_ttl(self, service, storage):
        service.save_token(Token("secret", 3600))

        assert service.get_token() == "secret"
        assert storage.ttls["iam:default"] == 3600

    def test_tokens_with_different_ids_do_not_clash(self, service):
        service.save_token(Token("one", 10), token_id="a")
        service.save_token(Token("two", 10), token_id="b")

        assert service.get_token("a") == "one"
        assert service.get_token("b") == "two"

    def test_token_exists_and_delete(self, service):
        assert not service.token_exists()

        service.save_token(Token("secret", 10))
        assert service.token_exists()

        service.delete_token()
        assert not service.token_exists()

    def test_prefix_can_be_changed(self, service, storage):
        service.set_key_prefix("other")

        service.save_token(Token("secret", 10))

        assert "other:default" in storage.data
