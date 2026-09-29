from src.domain.models import User, Transaction
from src.infrastructure.pony import models


class PonyDomainMapper:
    def user_to_domain(self, db_user: models.User):
        return User(
            id=db_user.id,
            telegram_id=db_user.telegram_id,
            bal=db_user.bal,
        )

    def transaction_to_domain(self, db_transaction: models.Transaction):
        return Transaction(
            id=db_transaction.id,
            uuid=db_transaction.uuid,
            user=self.user_to_domain(db_transaction.user),
            status=db_transaction.status,
            category=db_transaction.category,
            amount=db_transaction.amount,
            created_at=db_transaction.created_at,
        )
