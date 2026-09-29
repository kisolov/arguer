import pytest

from src.domain.models import Argue, ChatMessage, Reasoning, Speaker
from tests.cases.base import BaseTestGroup

CLIENT = Speaker("клиент")
OPPONENT = Speaker("оппонент")
ASSISTANT = Speaker("assistant")


class TestDisputeResolver(BaseTestGroup):
    @pytest.fixture
    def llm(self):
        llm = self.container.interfaces.llm()
        llm.reset()
        yield llm
        llm.reset()

    @pytest.fixture
    def resolver(self):
        return self.container.core.dispute_resolver()

    @pytest.mark.asyncio
    async def test_resolve_returns_model_text(self, resolver, llm):
        llm.set_return_value("аргументы")
        argue = Argue([Reasoning("Земля плоская", CLIENT)], CLIENT)

        assert await resolver.resolve(argue) == "аргументы"

    @pytest.mark.asyncio
    async def test_resolve_marks_sides_and_prepends_system_prompt(self, resolver, llm):
        argue = Argue(
            [
                Reasoning("Земля плоская", CLIENT),
                Reasoning("Нет, круглая", OPPONENT),
            ],
            CLIENT,
        )

        await resolver.resolve(argue)

        system, greeting, dialogue = llm.get_last_call()
        assert system == ChatMessage("system", resolver.base_prompt)
        assert greeting.role == "assistant"
        assert dialogue == ChatMessage(
            "user",
            "клиент - Земля плоская - ЗАЩИТИТЬ\nоппонент - Нет, круглая - ОПРОВЕРГНУТЬ\n",
        )

    @pytest.mark.asyncio
    async def test_previous_resolution_is_sent_as_assistant_turn(self, resolver, llm):
        argue = Argue(
            [
                Reasoning("Земля плоская", CLIENT),
                Reasoning("1. Горизонт выглядит плоским", ASSISTANT),
                Reasoning("Нет, круглая", OPPONENT),
            ],
            CLIENT,
        )

        await resolver.resolve(argue)

        _, _, first_user, assistant, second_user = llm.get_last_call()
        assert first_user == ChatMessage("user", "клиент - Земля плоская - ЗАЩИТИТЬ\n")
        assert assistant == ChatMessage("assistant", "1. Горизонт выглядит плоским")
        assert second_user == ChatMessage(
            "user", "оппонент - Нет, круглая - ОПРОВЕРГНУТЬ\n"
        )
