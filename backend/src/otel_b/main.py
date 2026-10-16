from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from otel_b.infrastructure.telemetry.tracing import build_tracer_provider
from otel_b.api.router import router as api_router
from otel_b.core.config import get_settings
from otel_b.infrastructure.telemetry.tracing import instrument_database
from otel_b.core.logging import configure_event_logging

setting = get_settings()


app = FastAPI(
    title=setting.app_name,
    version="0.1.0"
)

app.include_router(api_router)
tracer_provider = build_tracer_provider()
app.state.tracer_provider = tracer_provider

configure_event_logging()
instrument_database(tracer_provider)

FastAPIInstrumentor.instrument_app(
    app,
    tracer_provider=tracer_provider,
    exclude_spans=["receive","send"]
)
