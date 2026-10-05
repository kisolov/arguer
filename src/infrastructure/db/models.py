from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Numeric, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.domain.models import TransactionCategory, TransactionStatus

# Сумма в ✨ до сотых, как в домене (money)
MONEY = Numeric(14, 2, asdecimal=True)


def _enum(enum_cls):
    """Хранит .value в VARCHAR: так значения записаны в существующих таблицах."""
    return Enum(
        enum_cls,
        values_callable=lambda members: [m.value for m in members],
        native_enum=False,
        create_constraint=False,
        length=255,
    )


class Base(DeclarativeBase): ...


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    # Деньги в DECIMAL: в существующей БД колонка меняется через sql/002_money_decimal.sql
    bal: Mapped[Decimal] = mapped_column(MONEY, default=Decimal("150.00"))


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uuid: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    # Колонка называется "user": так она названа в существующих таблицах, они читаются как есть
    user_id: Mapped[int] = mapped_column("user", ForeignKey("users.id"))
    # Владелец грузится явно (selectinload): неявная ленивая загрузка в async запрещена
    user: Mapped[User] = relationship(lazy="raise")
    status: Mapped[TransactionStatus] = mapped_column(_enum(TransactionStatus))
    category: Mapped[TransactionCategory] = mapped_column(_enum(TransactionCategory))
    amount: Mapped[Decimal] = mapped_column(MONEY)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=text("CURRENT_TIMESTAMP")
    )
