from collections.abc import Generator
from sqlalchemy.orm import Session, sessionmaker
from otel_b.infrastructure.db.engine import engine

SessionFactory = sessionmaker(
    bind= engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False

)


def get_db_session() -> Generator[Session, None, None]:
    with SessionFactory() as session:
        yield session