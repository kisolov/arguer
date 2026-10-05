"""/go после списания: при любом сбое до ответа деньги и переписка возвращаются."""

from unittest.mock import patch

import pytest

from src.domain.exceptions import LanguageModelError, UnexpectedError
from src.domain.models import Speaker, TransactionCategory
from src.domain.operations import ArgueService, BillingService
from tests.cases.base import BaseTestGroup


class TestGoRefund(BaseTestGroup):
    @pytest.fixture
    def llm(self):
        llm = self.container.interfaces.llm()
        llm.reset()
        yield llm
        llm.reset()

    @pytest.fixture
    def transactions(self, container):
        repo = container.interfaces.transaction_repository()
        repo._storage.clear()
        return repo

    async def prepare(self, session, count=3):
        await self.add_messages(session, count)
        await session.context_service.set_defendant(Speaker("человек 0"))

    @pytest.mark.asyncio
    async def test_model_failure_refunds_and_releases_user(
        self, session, go_uc, llm, transactions
    ):
        await self.prepare(session)
        llm.set_side_effect(LanguageModelError("down"))

        with pytest.raises(UnexpectedError):
            await go_uc.execute()

        assert session.user.bal == pytest.approx(1000)
        assert session.context_service._current_state is None
        session.message_service.notify_refund.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_refund_is_a_separate_transaction(
        self, session, go_uc, llm, transactions
    ):
        await self.prepare(session)
        llm.set_side_effect(LanguageModelError("down"))

        with pytest.raises(UnexpectedError):
            await go_uc.execute()

        stored = sorted(transactions._storage.values(), key=lambda t: t.id)
        assert [t.category for t in stored] == [
            TransactionCategory.USAGE,
            TransactionCategory.REFUND,
        ]
        assert stored[0].amount == pytest.approx(-stored[1].amount)

    @pytest.mark.asyncio
    async def test_failure_restores_context_so_request_can_be_repeated(
        self, session, go_uc, llm, transactions
    ):
        await self.prepare(session)
        llm.set_side_effect(LanguageModelError("down"))
        with pytest.raises(UnexpectedError):
            await go_uc.execute()

        assert len((await session.context_service.get_unprocessed()).messages) == 3
        assert await session.context_service.get_defendant() == Speaker("человек 0")

        llm.reset()
        await go_uc.execute()

        session.message_service.send_resolution.assert_awaited_once()
        charges = [
            t
            for t in transactions._storage.values()
            if t.category is TransactionCategory.USAGE
        ]
        assert len(charges) == 2
        assert session.user.bal == pytest.approx(1000 + charges[0].amount)

    @pytest.mark.asyncio
    async def test_failure_keeps_previous_rounds_of_the_dispute(
        self, session, go_uc, llm, transactions
    ):
        await self.prepare(session)
        await go_uc.execute()
        processed = await session.context_service.get_processed()

        await self.add_messages(session, 2)
        llm.set_side_effect(LanguageModelError("down"))
        with pytest.raises(UnexpectedError):
            await go_uc.execute()

        assert await session.context_service.get_processed() == processed
        assert len((await session.context_service.get_unprocessed()).messages) == 2

    @pytest.mark.asyncio
    async def test_recognition_failure_refunds(
        self, session, go_uc, transactions
    ):
        await self.prepare(session)

        with patch.object(
            ArgueService, "create_from_dialogue", side_effect=RuntimeError("stt")
        ):
            with pytest.raises(RuntimeError, match="stt"):
                await go_uc.execute()

        assert session.user.bal == pytest.approx(1000)
        assert session.context_service._current_state is None

    @pytest.mark.asyncio
    async def test_undelivered_resolution_is_refunded(
        self, session, go_uc, transactions
    ):
        await self.prepare(session)
        session.message_service.send_resolution.side_effect = RuntimeError("tg")

        with pytest.raises(RuntimeError, match="tg"):
            await go_uc.execute()

        assert session.user.bal == pytest.approx(1000)

    @pytest.mark.asyncio
    async def test_success_is_not_refunded(self, session, go_uc, transactions):
        await self.prepare(session)

        await go_uc.execute()

        assert session.user.bal < 1000
        session.message_service.notify_refund.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_refund_failure_does_not_hide_original_error(
        self, session, go_uc, llm, transactions
    ):
        await self.prepare(session)
        llm.set_side_effect(LanguageModelError("down"))

        with patch.object(BillingService, "refund", side_effect=RuntimeError("db")):
            with pytest.raises(UnexpectedError):
                await go_uc.execute()

        session.message_service.notify_refund.assert_not_awaited()
        assert session.context_service._current_state is None

    @pytest.mark.asyncio
    async def test_processing_state_is_set_before_charging(
        self, session, go_uc, transactions
    ):
        await self.prepare(session)
        states_at_charge = []
        charge = BillingService.charge_for_dialogue

        async def spy(billing, *args):
            states_at_charge.append(session.context_service._current_state)
            return await charge(billing, *args)

        with patch.object(BillingService, "charge_for_dialogue", spy):
            await go_uc.execute()

        assert states_at_charge == ["processing"]
