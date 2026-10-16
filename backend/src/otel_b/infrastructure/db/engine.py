from sqlalchemy import create_engine
from otel_b.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url.get_secret_value(),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    pool_timeout=5,
)
