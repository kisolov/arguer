import pytest

from config import CostConfig
from src.domain.operations import CostCalculator
from tests.cases.base import BaseTestGroup


class TestCostCalculator(BaseTestGroup):
    @pytest.fixture
    def calculator(self):
        config = CostConfig(
            COST_DEFAULT=10.0, COST_TEXT_SYMBOL=0.01, COST_VOICE_SECOND=0.5
        )
        return CostCalculator(config)

    def test_empty_dialogue_costs_base_rate(self, calculator):
        assert calculator.calculate_cost(0, 0) == 10.0

    def test_cost_grows_with_text_and_voice(self, calculator):
        assert calculator.calculate_cost(voice_seconds=10, text_symbols=200) == pytest.approx(
            10.0 + 10 * 0.5 + 200 * 0.01
        )

    def test_formula_text_describes_all_components(self, calculator):
        assert calculator.get_formula_text() == (
            "10✨ + (50✨ за 5000 символов контекста) + (30✨ за распознавание 1 минуты голоса)"
        )
