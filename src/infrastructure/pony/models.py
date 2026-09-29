import enum
from datetime import datetime

from pony.orm import Database, PrimaryKey, Required, Set, Optional

from src.domain.models import TransactionStatus, TransactionCategory
from src.infrastructure.pony.converters import EnumConverter

db = Database()


class User(db.Entity):
    _table_ = "users"
    id = PrimaryKey(int, auto=True)
    telegram_id = Required(int, auto=False, size=64)
    bal = Required(float, default=150.0)

    transactions = Set("Transaction")


class Transaction(db.Entity):
    _table_ = "transactions"

    id = PrimaryKey(int, auto=True)
    uuid = Optional(str, nullable=True, default=None)
    user = Required(User)
    status = Required(TransactionStatus)
    category = Required(TransactionCategory)
    amount = Required(float)
    created_at = Required(datetime, sql_default="CURRENT_TIMESTAMP")
