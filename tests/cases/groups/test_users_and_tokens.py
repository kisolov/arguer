from unittest.mock import Mock

import pytest

from src.application import EnsureUserExists, RefreshToken
from src.domain.models import Token
from src.domain.operations import TokenService
from tests.cases.base import BaseTestGroup
from tests.mocks import InMemoryKeyValueStorage


class TestEnsureUserExists(BaseTestGroup):
    @pytest.fixture
    def users(self):
        return self.container.interfaces.user_repository()

    @pytest.mark.asyncio
    async def test_registers_unknown_telegram_user(self, users):
        user = await EnsureUserExists(users, telegram_id=9001).execute()

        assert user.id is not None
        assert user.telegram_id == 9001
        assert user.bal == 150

    @pytest.mark.asyncio
    async def test_returns_existing_user_without_duplicating(self, users):
        first = await EnsureUserExists(users, telegram_id=9002).execute()
        first.bal = 5
        await users.store(first)

        second = await EnsureUserExists(users, telegram_id=9002).execute()

        assert second.id == first.id
        assert second.bal == 5


class TestRefreshToken(BaseTestGroup):
    @pytest.fixture
    def service(self):
        return TokenService(InMemoryKeyValueStorage(), key_prefix="iam")

    def test_saves_token_from_provider(self, service):
        provider = Mock()
        provider.create_token.return_value = Token("fresh", 3600)

        RefreshToken(provider, service).execute()

        assert service.get_token() == "fresh"

    def test_provider_failure_is_reraised_and_nothing_saved(self, service):
        provider = Mock()
        provider.create_token.side_effect = RuntimeError("yc is down")

        with pytest.raises(RuntimeError, match="yc is down"):
            RefreshToken(provider, service).execute()

        assert not service.token_exists()
