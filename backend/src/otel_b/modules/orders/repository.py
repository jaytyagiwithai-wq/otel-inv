from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from otel_b.modules.orders.models import Order


def find_order(session: Session, *, tenant_id: UUID, order_id: UUID) -> Order | None:
    statement = select(Order).where(
        Order.id == order_id,
        Order.tenant_id == tenant_id,
    )
    return session.scalar(statement)


def list_recent_orders(
    session: Session,
    *,
    tenant_id: UUID,
    limit: int = 50,
) -> list[Order]:
    """Future listing experiment; not exposed by the current API."""
    statement = (
        select(Order)
        .where(Order.tenant_id == tenant_id)
        .order_by(Order.created_at.desc(), Order.id.desc())
        .limit(limit)
    )
    return list(session.scalars(statement).all())
