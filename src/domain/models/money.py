from decimal import ROUND_HALF_UP, Decimal
from typing import Union

# ✨ хранятся с точностью до сотых: столько же цифр видит пользователь
CENT = Decimal("0.01")


def money(value: Union[Decimal, int, str]) -> Decimal:
    """Сумма в ✨, округлённая до сотых по правилам арифметики.

    float не принимается: двоичная дробь уже несёт ошибку округления.
    """
    if isinstance(value, float):
        raise TypeError("Суммы задаются Decimal, int или строкой, не float")
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)
