import json
import logging
from datetime import datetime, timezone

from opentelemetry import trace

from otel_b.core.config import get_settings
from pathlib import Path
from typing import Literal

logger = logging.getLogger("otel_b.events")


def log_event(
    name: str,
    attributes: dict[str, object],
    *,
    severity: Literal["INFO", "WARNING", "ERROR"] = "INFO",
) -> None:
    settings = get_settings()
    context = trace.get_current_span().get_span_context()

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "name": name,
        "severity": severity,
        "service.name": settings.service_name,
        "deployment.environment.name": settings.environment,
        "attributes": attributes,
    }

    if context.is_valid:
        event["trace_id"] = format(context.trace_id, "032x")
        event["span_id"] = format(context.span_id, "016x")

    logger.log(getattr(logging, severity), json.dumps(event))



def configure_event_logging() -> None:
    log_path = Path("logs/events.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("%(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        log_path,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
