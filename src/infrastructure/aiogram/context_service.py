from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from src.domain.ports import ContextService


class States(StatesGroup):
    processing = State()
    defendant_selection = State()


class AiogramContextService(ContextService):
    def __init__(self, fsm: FSMContext):
        self.fsm = fsm

    async def get(self, key: str):
        data = await self.fsm.get_data()
        desired = data.get(key)
        if not desired:
            raise KeyError()
        return desired

    async def update(self, values: dict):
        await self.fsm.update_data(**values)

    async def set(self, values: dict):
        await self.fsm.set_data(values)

    async def clear_data(self):
        await self.fsm.set_data({})

    async def clear_state(self) -> None:
        await self.fsm.set_state(None)

    async def set_processing_state(self) -> None:
        await self.fsm.set_state(States.processing)

    async def set_defendant_selection_state(self) -> None:
        await self.fsm.set_state(States.defendant_selection)
