from uuid import UUID

from fastapi import APIRouter, HTTPException

from otel_b.api.dependencies import SessionDep, TenantDep, TracerDep
from otel_b.modules.orders.schemas import OrderResponse
from otel_b.modules.orders.service import (
    OrderLookupUnavailable,
    OrderNotFound,
    lookup_order,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: UUID, session: SessionDep, tenant_id: TenantDep, tracer: TracerDep
) -> OrderResponse:
    try:
        return lookup_order(session, tenant_id=tenant_id, order_id=order_id, tracer=tracer)
    except OrderNotFound as error:
        raise HTTPException(status_code=404, detail="Order not found") from error
    except OrderLookupUnavailable as error:
        raise HTTPException(status_code=503, detail="Order lookup unavailable") from error
