from time import perf_counter
from uuid import UUID

from opentelemetry.trace import Tracer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from otel_b.core.logging import log_event
from otel_b.modules.orders.repository import find_order
from otel_b.modules.orders.schemas import OrderResponse


class OrderNotFound(Exception):
    pass


class OrderLookupUnavailable(Exception):
    pass


def lookup_order(
    session: Session, *, tenant_id: UUID, order_id: UUID, tracer: Tracer
) -> OrderResponse:
    started = perf_counter()
    attributes = {
        "app.operation": "orders.lookup",
        "app.tenant.id": str(tenant_id),
        "app.order.id": str(order_id),
        "app.dependency": "postgresql",
    }
    with tracer.start_as_current_span("orders.lookup", attributes=attributes) as span:
        try:
            with session.begin():
                order = find_order(session, tenant_id=tenant_id, order_id=order_id)
                response = OrderResponse.model_validate(order) if order is not None else None
        except SQLAlchemyError as error:
            attributes.update({
                "app.outcome": "dependency_error",
                "error.type": type(error).__name__,
                "app.duration_ms": (perf_counter() - started) * 1000,
            })
            span.set_attributes(attributes)
            log_event("orders.lookup.completed", attributes, severity="ERROR")
            raise OrderLookupUnavailable() from error

        attributes.update({
            "app.outcome": "success" if response is not None else "not_found",
            "app.result.count": 1 if response is not None else 0,
            "app.duration_ms": (perf_counter() - started) * 1000,
        })
        if response is not None:
            attributes["app.order.status"] = response.status
        span.set_attributes(attributes)
        log_event("orders.lookup.completed", attributes)

    # An expected miss is a business outcome, not a failed database operation.
    if response is None:
        raise OrderNotFound()
    return response
