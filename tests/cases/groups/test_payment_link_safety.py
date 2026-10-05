"""Ссылка на оплату уходит, только когда платёж записан в БД и привязан к транзакции."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from src.application import SendPaymentLink
from src.domain.models import TransactionStatus
from src.domain.operations import BillingService
from src.domain.ports import PaymentInfo
from tests.cases.groups.test_billing_usecases import BillingTestGroup
from tests.utils.factories import EventContextFactory


class TestPaymentLinkSafety(BillingTestGroup):
    @pytest.fixture
    def options_repo(self):
        return self.container.interfaces.buy_options_repository()

    @pytest.fixture
    def send_link(self, session, gateway, options_repo, billing):
        session.event = EventContextFactory(
            user=session.user, data=SimpleNamespace(option_index=1)
        )
        return SendPaymentLink(session, gateway, options_repo, billing)

    @pytest.mark.asyncio
    async def test_top_up_is_recorded_before_payment_is_created(
        self, session, send_link, gateway, transactions
    ):
        recorded_at_creation = []

        async def create_payment(*args):
            recorded_at_creation.extend(transactions._storage.values())
            return PaymentInfo("https://pay/1", "uuid-1")

        gateway.create_payment.side_effect = create_payment

        await send_link.execute()

        assert len(recorded_at_creation) == 1
        assert recorded_at_creation[0].status is TransactionStatus.PENDING

    @pytest.mark.asyncio
    async def test_gateway_failure_cancels_top_up_and_sends_no_link(
        self, session, send_link, gateway, transactions
    ):
        gateway.create_payment.side_effect = RuntimeError("yookassa down")

        with pytest.raises(RuntimeError, match="yookassa down"):
            await send_link.execute()

        assert await transactions.get_pending_transactions_for(session.user.id) == []
        [stored] = transactions._storage.values()
        assert stored.status is TransactionStatus.CANCELED
        session.message_service.send_payment_link.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_link_is_not_sent_when_payment_cannot_be_attached(
        self, session, send_link, gateway
    ):
        gateway.create_payment.return_value = PaymentInfo("https://pay/1", "uuid-1")

        with patch.object(
            BillingService, "attach_payment", side_effect=RuntimeError("db down")
        ):
            with pytest.raises(RuntimeError, match="db down"):
                await send_link.execute()

        session.message_service.send_payment_link.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_attached_payment_is_credited_by_refresh(
        self, session, send_link, gateway, billing, transactions
    ):
        gateway.create_payment.return_value = PaymentInfo("https://pay/1", "uuid-1")
        await send_link.execute()

        [pending] = await transactions.get_pending_transactions_for(session.user.id)
        await billing.apply_transaction(pending)

        assert pending.uuid == "uuid-1"
        assert (await self.container.interfaces.user_repository().get(session.user)).bal > 1000
