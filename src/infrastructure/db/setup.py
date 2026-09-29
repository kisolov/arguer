from sqlalchemy import URL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from .models import Base


class Database:
    def __init__(self, url: URL, **engine_kwargs):
        self.engine = create_async_engine(url, **engine_kwargs)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    @classmethod
    def from_config(cls, config) -> "Database":
        if config.provider == "sqlite":
            # Только для тестов: aiosqlite стоит в requirements-dev.txt, в DatabaseConfig нет filename
            url = URL.create("sqlite+aiosqlite", database=config.filename)
            kwargs = {"poolclass": StaticPool} if config.filename == ":memory:" else {}
            return cls(url, **kwargs)

        if config.provider == "mysql":
            url = URL.create(
                "mysql+aiomysql",
                username=config.user,
                password=config.password.get_secret_value(),
                host=config.host,
                port=config.port,
                database=config.database,
                query={"charset": "utf8mb4"},
            )
            return cls(url, pool_pre_ping=True)

        raise ValueError(f"Unknown database provider: {config.provider}")

    async def create_schema(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        await self.engine.dispose()
