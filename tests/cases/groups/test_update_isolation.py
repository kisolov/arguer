"""Состояние бота в Redis и последовательная обработка апдейтов одного пользователя."""

import asyncio

import pytest
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.fsm.storage.redis import RedisStorage

from di import container as app_container
from src.domain.models import (
    Argue,
    Dialogue,
    Media,
    Reasoning,
    Speaker,
    UnprocessedMessage,
)
from src.infrastructure.aiogram import fsm_storage
from src.presentation.aiogram import routes
from tests.cases.base import BaseTestGroup


def key(user_id: int) -> StorageKey:
    return StorageKey(bot_id=1, chat_id=user_id, user_id=user_id)


class TestDispatcherSetup(BaseTestGroup):
    @pytest.fixture
    def dp(self):
        return app_container.dp()

    def test_state_is_kept_in_redis(self, dp):
        assert isinstance(dp.fsm.storage, RedisStorage)

    def test_updates_of_one_user_are_isolated(self, dp):
        assert isinstance(dp.fsm.events_isolation, SimpleEventIsolation)

    @pytest.mark.asyncio
    async def test_same_user_updates_run_one_at_a_time(self, dp):
        running, overlaps = 0, 0

        async def handle(user_id):
            nonlocal running, overlaps
            async with dp.fsm.events_isolation.lock(key(user_id)):
                running += 1
                overlaps = max(overlaps, running)
                await asyncio.sleep(0.01)
                running -= 1

        await asyncio.gather(*(handle(1) for _ in range(5)))

        assert overlaps == 1

    @pytest.mark.asyncio
    async def test_different_users_are_not_blocked(self, dp):
        isolation = dp.fsm.events_isolation

        async with isolation.lock(key(1)):
            async with asyncio.timeout(1):
                async with isolation.lock(key(2)):
                    pass


class TestFsmSerialization(BaseTestGroup):
    def test_context_objects_survive_round_trip(self):
        dialogue = Dialogue()
        dialogue.add_message(
            UnprocessedMessage(Speaker("человек 1"), media=Media("voice.ogg", 7))
        )
        data = {
            "unprocessed": dialogue,
            "defendant": Speaker("человек 0"),
            "processed": Argue([Reasoning("довод", Speaker("человек 1"))], Speaker("человек 0")),
        }

        encoded = fsm_storage.dumps(data)

        assert isinstance(encoded, str)
        assert fsm_storage.loads(encoded) == data


class TestRouteOrder(BaseTestGroup):
    def handler_names(self):
        return [h.callback.__name__ for h in routes.router.message.handlers]

    def test_clear_and_start_work_in_processing_state(self):
        names = self.handler_names()
        guard = names.index("processing_input_protection")

        assert names.index("clear") < guard
        assert names.index("start") < guard

    def test_paid_and_intake_handlers_are_guarded(self):
        names = self.handler_names()
        guard = names.index("processing_input_protection")

        for name in ("go", "handle_forwarded_message", "bal"):
            assert names.index(name) > guard
