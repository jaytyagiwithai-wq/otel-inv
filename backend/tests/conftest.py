import os

# The app engine is configured at import time with PostgreSQL pool options.
# It never connects here: every test overrides the session with isolated SQLite.
os.environ["DATABASE_URL"] = "postgresql+psycopg://test:test@127.0.0.1:1/test"
os.environ["ENVIRONMENT"] = "test"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from otel_b.infrastructure.db.base import Base
from otel_b.infrastructure.db.session import get_db_session
from otel_b.modules.orders.models import Order
from otel_b.modules.orders.router import router
from otel_b.scripts.seed_orders import TENANT_A, TENANT_B, seed_order_id


@pytest.fixture
def lab():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        session.add_all([
            Order(id=seed_order_id(TENANT_A, 0), tenant_id=TENANT_A, status="pending"),
            Order(id=seed_order_id(TENANT_B, 0), tenant_id=TENANT_B, status="shipped"),
        ])

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    app = FastAPI()
    app.state.tracer_provider = provider
    app.include_router(router, prefix="/api/v1")

    def override_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    FastAPIInstrumentor.instrument_app(
        app, tracer_provider=provider, exclude_spans=["receive", "send"]
    )
    try:
        with TestClient(app) as client:
            yield client, exporter
    finally:
        FastAPIInstrumentor.uninstrument_app(app)
        provider.shutdown()
        engine.dispose()
