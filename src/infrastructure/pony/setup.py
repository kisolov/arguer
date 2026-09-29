from enum import Enum

from .converters import EnumConverter
from .models import db
from ...domain.models import TransactionStatus


def setup_pony(config):
    # set_sql_debug(True)
    if config.provider == "sqlite":
        db.bind(
            provider="sqlite",
            filename=config.filename,
            create_db=getattr(config, "create_db", True),
        )
    else:
        db.bind(
            provider=config.provider,
            host=config.host,
            port=config.port,
            user=config.user,
            password=(
                config.password.get_secret_value()
                if hasattr(config.password, "get_secret_value")
                else config.password
            ),
            database=config.database,
            charset=getattr(config, "charset", "utf8mb4"),
        )
    db.provider.converter_classes.append((Enum, EnumConverter))
    db.provider.converter_classes.append((TransactionStatus, EnumConverter))
    db.generate_mapping(create_tables=True)
