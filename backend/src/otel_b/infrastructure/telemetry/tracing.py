from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from otel_b.infrastructure.db.engine import engine
from otel_b.core.config import get_settings

from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Resource = describes who produces the telemetry: which service, version, and environment.
# TracerProvider = - holds the SDK configuration used to create tracers.

def build_tracer_provider() -> TracerProvider:
    settings = get_settings()

    resource = Resource.create({
        "service.name":settings.service_name,
        "service.version":"0.1.0",
        "deployment.environment.name":settings.environment
    })

    provider = TracerProvider(resource=resource)
    #provider contains share config and supplies tracer
    #tracer create spans

    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(
            #BatchSpanProcessor - Instead of sending a separate HTTP export request every time a span ends, it collects completed spans in a queue
            endpoint = settings.otel_traces_endpoint
        ),
        schedule_delay_millis=1000)
    )

    #add_span_processor we are registring a begavoir for span in this case we exports a span when it ends
    return provider



'''
ConsoleSpanExporter()
    Creates an exporter that prints spans.

SimpleSpanProcessor(exporter)
    Sends each completed, recorded span directly to that exporter.

provider.add_span_processor(processor)
    Registers that behaviour with the provider.

'''


def instrument_database(provider: TracerProvider) -> None:
    SQLAlchemyInstrumentor().instrument(
        engine=engine,
        tracer_provider=provider
    )