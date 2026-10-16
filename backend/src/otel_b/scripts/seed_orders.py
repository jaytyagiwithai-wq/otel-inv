"""Create deterministic, repeatable local lab data without replacing existing orders."""

import argparse
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid5

from sqlalchemy.dialects.postgresql import insert

from otel_b.core.config import get_settings
from otel_b.infrastructure.db.engine import engine
from otel_b.modules.orders.models import Order

TENANT_A = UUID("11111111-1111-4111-8111-111111111111")
TENANT_B = UUID("22222222-2222-4222-8222-222222222222")
SEED_NAMESPACE = UUID("f61ee310-7ec8-4c42-a265-f75c9cef40a7")


def seed_order_id(tenant_id: UUID, index: int) -> UUID:
    return uuid5(SEED_NAMESPACE, f"{tenant_id}:order:{index}")


def seed_orders(orders_per_tenant: int) -> int:
    if get_settings().environment not in {"local", "test"}:
        raise RuntimeError("Seed data is only available in local/test environments")
    if orders_per_tenant < 1:
        raise ValueError("orders_per_tenant must be positive")

    inserted = 0
    statuses = ("pending", "shipped", "cancelled")
    origin = datetime(2026, 1, 1, tzinfo=timezone.utc)
    with engine.begin() as connection:
        for tenant_id in (TENANT_A, TENANT_B):
            for start in range(0, orders_per_tenant, 500):
                rows = [
                    {
                        "id": seed_order_id(tenant_id, index),
                        "tenant_id": tenant_id,
                        "status": statuses[index % len(statuses)],
                        "created_at": origin + timedelta(seconds=index),
                    }
                    for index in range(start, min(start + 500, orders_per_tenant))
                ]
                statement = (
                    insert(Order).values(rows)
                    .on_conflict_do_nothing(index_elements=[Order.id])
                    .returning(Order.id)
                )
                inserted += len(connection.execute(statement).scalars().all())
    return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orders-per-tenant", type=int, default=1000)
    args = parser.parse_args()
    if args.orders_per_tenant < 1:
        parser.error("--orders-per-tenant must be positive")
    try:
        inserted = seed_orders(args.orders_per_tenant)
    finally:
        engine.dispose()
    print(json.dumps({
        "inserted": inserted,
        "orders_per_tenant": args.orders_per_tenant,
        "tenant_a": str(TENANT_A),
        "tenant_b": str(TENANT_B),
        "tenant_a_order_id": str(seed_order_id(TENANT_A, 0)),
        "tenant_b_order_id": str(seed_order_id(TENANT_B, 0)),
    }, indent=2))


if __name__ == "__main__":
    main()
