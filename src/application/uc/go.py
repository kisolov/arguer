from logs import logger
from .charge_for_usage import ChargeForUsage
from .fetch_defendant import FetchDefendant
from .fetch_dialogue import FetchDialogue
from .handle_resolution import HandleResolution
from .process_unprocessed import ProcessUnprocessed

from src.domain.models import Transaction
from src.domain.operations import LLMDisputeResolver, ArgueService, BillingService
from .process_argue import ProcessArgue
from .base import SessionRelatedUseCase
from .send_context_info import ShowContextInfo
from ..session import Session


class Go(SessionRelatedUseCase):
    """Платный разбор спора.

    Состояние processing ставится до списания и снимается при любом исходе.
    Если ответ не дошёл до пользователя, списание возвращается, а переписка
    восстанавливается в контексте, чтобы запрос можно было повторить.
    """

    def __init__(
        self,
        session: Session,
        dispute_resolver: LLMDisputeResolver,
        billing_service: BillingService,
        argue_service: ArgueService,
    ):
        super().__init__(session)
        self.dispute_resolver = dispute_resolver
        self.argue_service = argue_service
        self.billing_service = billing_service

    async def execute(self):
        context = self.session.context_service
        dialogue = await FetchDialogue(self.session).execute()
        defendant = await FetchDefendant(self.session).execute()
        processed_before = await context.get_processed()

        await context.set_processing_state()
        try:
            charge = await ChargeForUsage(
                self.session, billing_service=self.billing_service
            ).execute(dialogue)
            try:
                argue = await self._resolve()
            except BaseException:
                await self._restore_context(dialogue, defendant, processed_before)
                await self._refund(charge)
                raise
        finally:
            await context.clear_state()

        await ShowContextInfo(self.session).execute()

        logger.info(
            "Спор обработан",
            extra={
                "user_id": self.session.user.id,
                "reasoning_count": len(argue.reasoning_list),
                "context_symbols": argue.total_symbols,
            },
        )

    async def _resolve(self):
        progress_message_ctx = await self.session.message_service.send_progress_message(
            self.session.answer_message_context
        )

        try:
            argue = await ProcessUnprocessed(
                self.session, argue_service=self.argue_service
            ).execute()
            resolution = await ProcessArgue(self.dispute_resolver, argue).execute()
        finally:
            await self.session.message_service.delete_message(progress_message_ctx)

        await HandleResolution(self.session).execute(argue, resolution)
        return argue

    async def _restore_context(self, dialogue, defendant, processed_before):
        values = dict(unprocessed=dialogue, defendant=defendant)
        if processed_before:
            values["processed"] = processed_before
        await self.session.context_service.set(values)

    async def _refund(self, charge: Transaction):
        try:
            await self.billing_service.refund(charge)
        except Exception:
            # Пробрасывается исходная ошибка, а невозвращённое списание видно в логах
            logger.error(
                "Не удалось вернуть списание",
                extra={"user_id": self.session.user.id, "transaction_id": charge.id},
                exc_info=True,
            )
            return
        await self.session.message_service.notify_refund(
            self.session.answer_message_context, -charge.amount
        )
