from config import CostConfig


class CostCalculator:
    def __init__(self, cost_config: CostConfig):
        self.default_cost = cost_config.default_cost
        self.voice_second_cost = cost_config.voice_second_cost
        self.text_symbol_cost = cost_config.text_symbol_cost

    def get_formula_text(self):
        return (
            f"{int(self.default_cost)}✨ + "
            f"({int(self.text_symbol_cost * 5000)}✨ за 5000 символов контекста) + "
            f"({int(self.voice_second_cost * 60)}✨ за распознавание 1 минуты голоса)"
        )

    def calculate_cost(self, voice_seconds: int, text_symbols: int):
        return (
            self.default_cost
            + voice_seconds * self.voice_second_cost
            + text_symbols * self.text_symbol_cost
        )
