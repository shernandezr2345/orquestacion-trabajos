from dataclasses import dataclass

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


@dataclass(frozen=True)
class Database:
    engine: Engine
    session_factory: sessionmaker[Session]

    def close(self) -> None:
        self.engine.dispose()


def create_database(database_url: str) -> Database:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_timeout=2,
        connect_args={"connect_timeout": 3, "options": "-c statement_timeout=3000"},
    )
    return Database(engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False))
