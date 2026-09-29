import re
from functools import wraps

from aiogram import Dispatcher, filters, Router, F
from aiogram.filters import StateFilter

from config import AppConfig
from di import container
from src.application import (
    SendInstructions,
    SendBalanceMenu,
    ClearContext,
    AddMessageToUnprocessed,
    SelectDefendant,
    Go,
    Session,
    SendPricesMenu,
    SendDefendantSelection,
    RefreshBalance,
    SendPaymentLink,
)
from src.application.uc.add_reasoning_to_unprocessed import AddTestMessageToUnprocessed
from src.application.uc.send_context_info import ShowContextInfo
from src.domain.exceptions import (
    UndefinedDefendant,
)
from src.domain.models import MessageContext
from src.infrastructure import Callbacks, States

container.wire(modules=[__name__])

router = Router()
test_router = Router()


def with_deps(*deps):
    def decorator(handler):
        @wraps(handler)
        async def wrapper(event, **kwargs):
            resolved_deps = {}
            for dep in deps:
                arg_name = dep.split(".")[-1]
                if arg_name in kwargs:
                    resolved_deps[arg_name] = kwargs[arg_name]
                else:
                    provider = container
                    for part in dep.split("."):
                        provider = getattr(provider, part)
                    resolved_deps[arg_name] = provider()
            return await handler(event, **{**kwargs, **resolved_deps})

        return wrapper

    return decorator


@router.message(filters.Command("ctx"))
async def show_ctx(session: Session):
    await ShowContextInfo(session).execute()


@router.message(filters.StateFilter(States.processing), flags={"priority": 100})
async def processing_input_protection(session: Session):
    pass


@router.message(filters.Command("start"))
async def start(session: Session):
    await SendInstructions(session).execute()


@router.message(filters.Command("bal"))
@with_deps("core.cost_calculator")
async def bal(session: Session, cost_calculator):
    await SendBalanceMenu(session, formula=cost_calculator.get_formula_text()).execute()


@router.message(filters.Command("clear"))
async def clear(session: Session):
    await ClearContext(session).execute()


@router.message(filters.Command("go"))
@with_deps("core.dispute_resolver", "core.billing_service", "core.argue_service")
async def go(session: Session, **kwargs):
    try:
        await Go(session, **kwargs).execute()
    except UndefinedDefendant:
        await SendDefendantSelection(session).execute()


@router.callback_query(
    Callbacks.DefendantSelectionCallback.filter(),
    StateFilter(States.defendant_selection),
)
@with_deps("core.dispute_resolver", "core.billing_service", "core.argue_service")
async def defendant_selection(session: Session, **kwargs):
    await SelectDefendant(session).execute()
    await Go(session, **kwargs).execute()


@router.message(F.forward_from | F.forward_sender_name)
@with_deps("config.app_config")
async def handle_forwarded_message(session: Session, **kwargs):
    await AddMessageToUnprocessed(session, **kwargs).execute()


@test_router.message(F.text.regexp(r"^(.*)\s+\((\d+)\)$"))
@with_deps("config.app_config")
async def handle_test_message(session: Session, app_config: AppConfig):
    """Имитация пересланного сообщения: `текст (id)`. Только при APP_ENABLE_TEST_MESSAGES=true."""
    match = re.match(r"^(.*)\s+\((\d+)\)$", session.event.data)
    if not match:
        return

    text_data = match.group(1).strip()
    sender_id = match.group(2)

    sender_name = f"User {sender_id}"

    await AddTestMessageToUnprocessed(session, app_config).execute(
        sender_name=sender_name, text_data=text_data, media=None
    )


@router.callback_query(F.data == "top_up")
@with_deps("interfaces.buy_options_repository")
async def top_up(session: Session, **kwargs):
    await SendPricesMenu(session, **kwargs).execute()


@router.callback_query(F.data == "buy_options_back")
@with_deps("core.cost_calculator")
async def buy_options_back(session: Session, cost_calculator):
    await SendBalanceMenu(session, formula=cost_calculator.get_formula_text()).execute(
        MessageContext(session.user, session.event.event_message_id)
    )


@router.callback_query(F.data == "update")
@with_deps(
    "interfaces.payment_gateway",
    "interfaces.transaction_repository",
    "core.billing_service",
    "core.cost_calculator",
)
async def refresh_balance(session: Session, cost_calculator, **kwargs):
    await RefreshBalance(
        session, formula=cost_calculator.get_formula_text(), **kwargs
    ).execute()


@router.callback_query(Callbacks.BuyOptionSelectionCallback.filter())
@with_deps(
    "interfaces.payment_gateway",
    "interfaces.buy_options_repository",
    "core.billing_service",
)
async def send_payment_link(session: Session, **kwargs):
    await SendPaymentLink(session, **kwargs).execute()


def setup_routes(dp: Dispatcher):
    dp.include_router(router)
    if container.config.app_config().enable_test_messages:
        dp.include_router(test_router)
