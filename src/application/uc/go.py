from logs import logger
from .charge_for_usage import ChargeForUsage
from .fetch_defendant import FetchDefendant
from .fetch_dialogue import FetchDialogue
from .handle_resolution import HandleResolution
from .process_unprocessed import ProcessUnprocessed

from src.domain.operations import LLMDisputeResolver, ArgueService, BillingService
from .process_argue import ProcessArgue
from .base import SessionRelatedUseCase
from .send_context_info import ShowContextInfo
from ..session import Session


class Go(SessionRelatedUseCase):
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

        dialogue = await FetchDialogue(self.session).execute()
        await FetchDefendant(self.session).execute()

        await ChargeForUsage(
            self.session, billing_service=self.billing_service
        ).execute(dialogue)

        await self.session.context_service.set_processing_state()

        progress_message_ctx = await self.session.message_service.send_progress_message(
            self.session.answer_message_context
        )

        argue = await ProcessUnprocessed(
            self.session, argue_service=self.argue_service
        ).execute()

        resolution = await ProcessArgue(self.dispute_resolver, argue).execute()

        await self.session.message_service.delete_message(progress_message_ctx)

        await HandleResolution(self.session).execute(argue, resolution)
        await ShowContextInfo(self.session).execute()

        await self.session.context_service.clear_state()
