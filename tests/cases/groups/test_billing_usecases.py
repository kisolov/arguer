from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.application import (
    ChargeForUsage,
    RefreshBalance,
    SendBalanceMenu,
    SendPaymentLink,
    SendPricesMenu,
)
from src.domain.exceptions import InsufficientFunds, RecordNotFound
from src.domain.models import MessageContext, TransactionStatus
from src.domain.ports import PaymentInfo
from tests.cases.base import BaseTestGroup
from tests.utils.factories import EventContextFactory, TestSessionFactory

FORMULA = "формула"


class BillingTestGroup(BaseTestGroup):
    @pytest.fixture(autouse=True)
    def clean_repositories(self, container):
        container.interfaces.transaction_repository()._storage.clear()

    @pytest.fixture
    def billing(self):
        return self.container.core.billing_service()

    @pytest.fixture
    def transactions(self):
        return self.container.interfaces.transaction_repository()

    @pytest.fixture
    def gateway(self):
        return AsyncMock()


class TestChargeForUsage(BillingTestGroup):
    @pytest.mark.asyncio
    async def test_charges_user_and_notifies_amount(self, session, billing):
        await self.add_messages(session, 2)
        dialogue = await session.context_service.get_unprocessed()
        cost = billing.calculate_dialogue_cost(dialogue)

        await ChargeForUsage(session, billing).execute(dialogue)

        assert session.user.bal == pytest.approx(1000 - cost)
        _, amount = session.message_service.notify_charge.await_args.args
        assert amount == pytest.approx(cost)

    @pytest.mark.asyncio
    async def test_insufficient_funds_does_not_notify(self, session, billing):
        session.user.bal = 1
        await self.add_messages(session, 2)
        dialogue = await session.context_service.get_unprocessed()

        with pytest.raises(InsufficientFunds):
            await ChargeForUsage(session, billing).execute(dialogue)

        session.message_service.notify_charge.assert_not_awaited()


class TestBalanceMenus(BillingTestGroup):
    @pytest.mark.asyncio
    async def test_balance_menu_replies_with_formula(self, session):
        await SendBalanceMenu(session, FORMULA).execute()

        call =session.message_service.send_balance_menu.await_args
        assert call.kwargs["formula"] == FORMULA
        assert call.args[0].message_id is None

    @pytest.mark.asyncio
    async def test_balance_menu_can_edit_given_message(self, session):
        target = MessageContext(session.user, 77)

        await SendBalanceMenu(session, FORMULA).execute(target)

        assert session.message_service.send_balance_menu.await_args.args[0] is target

    @pytest.mark.asyncio
    async def test_prices_menu_lists_all_options_and_edits_pressed_message(
        self, session
    ):
        options_repo = self.container.interfaces.buy_options_repository()
        session.event = EventContextFactory(user=session.user, event_message_id=55)

        await SendPricesMenu(session, options_repo).execute()

        ctx, options = session.message_service.send_prices_menu.await_args.args
        assert ctx.message_id == 55
        assert options == await options_repo.get_all()


class TestSendPaymentLink(BillingTestGroup):
    @pytest.fixture
    def options_repo(self):
        return self.container.interfaces.buy_options_repository()

    @pytest.mark.asyncio
    async def test_creates_payment_records_top_up_and_sends_link(
        self, session, gateway, options_repo, billing, transactions
    ):
        gateway.create_payment.return_value = PaymentInfo("https://pay/1", "uuid-1")
        session.event = EventContextFactory(
            user=session.user, event_message_id=9, data=SimpleNamespace(option_index=1)
        )
        option = await options_repo.get(1)

        await SendPaymentLink(session, gateway, options_repo, billing).execute()

        gateway.create_payment.assert_awaited_once_with(option.price, option.description)
        pending = await transactions.get_pending_transactions_for(session.user.id)
        assert [(t.uuid, t.amount) for t in pending] == [
            ("uuid-1", option.tokens_amount)
        ]
        ctx, link = session.message_service.send_payment_link.await_args.args
        assert (ctx.message_id, link) == (9, "https://pay/1")

    @pytest.mark.asyncio
    async def test_unknown_option_creates_nothing(
        self, session, gateway, options_repo, billing, transactions
    ):
        session.event = EventContextFactory(
            user=session.user, data=SimpleNamespace(option_index=99)
        )

        with pytest.raises(RecordNotFound):
            await SendPaymentLink(session, gateway, options_repo, billing).execute()

        gateway.create_payment.assert_not_awaited()
        assert await transactions.get_pending_transactions_for(session.user.id) == []


class TestRefreshBalance(BillingTestGroup):
    @pytest.fixture
    def popup_session(self, user):
        return TestSessionFactory(
            with_popup=True, event=EventContextFactory(user=user, event_message_id=5)
        )

    @pytest.fixture
    def refresh(self, popup_session, gateway, transactions, billing):
        return RefreshBalance(popup_session, gateway, transactions, billing, FORMULA)

    @pytest.mark.asyncio
    async def test_without_pending_only_shows_popup(
        self, popup_session, refresh, gateway
    ):
        await refresh.execute()

        gateway.get_payment_status.assert_not_awaited()
        assert len(popup_session.popup_service.get_shown_popups()) == 1

    @pytest.mark.asyncio
    async def test_completed_payment_credits_balance_and_refreshes_menu(
        self, popup_session, refresh, gateway, billing
    ):
        await billing.record_top_up(popup_session.user, 500, "uuid-ok")
        gateway.get_payment_status.return_value = TransactionStatus.COMPLETED

        await refresh.execute()

        assert popup_session.user.bal == 1500
        ctx, formula = popup_session.message_service.send_balance_menu.await_args.args
        assert (ctx.message_id, formula) == (5, FORMULA)
        assert len(popup_session.popup_service.get_shown_popups()) == 1

    @pytest.mark.asyncio
    async def test_canceled_payment_is_closed_without_credit(
        self, popup_session, refresh, gateway, billing, transactions
    ):
        await billing.record_top_up(popup_session.user, 500, "uuid-no")
        gateway.get_payment_status.return_value = TransactionStatus.CANCELED

        await refresh.execute()

        assert popup_session.user.bal == 1000
        assert await transactions.get_pending_transactions_for(popup_session.user.id) == []
        popup_session.message_service.send_balance_menu.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_still_pending_payment_is_left_alone(
        self, popup_session, refresh, gateway, billing, transactions
    ):
        await billing.record_top_up(popup_session.user, 500, "uuid-wait")
        gateway.get_payment_status.return_value = TransactionStatus.PENDING

        await refresh.execute()

        assert popup_session.user.bal == 1000
        pending = await transactions.get_pending_transactions_for(popup_session.user.id)
        assert len(pending) == 1

    @pytest.mark.asyncio
    async def test_transaction_without_uuid_is_not_sent_to_gateway(
        self, popup_session, refresh, gateway, billing
    ):
        await billing.record_top_up(popup_session.user, 500, None)

        await refresh.execute()

        gateway.get_payment_status.assert_not_awaited()
