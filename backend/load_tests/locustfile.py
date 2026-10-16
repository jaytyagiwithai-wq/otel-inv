"""Order lookup workload for the two tenants created by seed_orders.

Seed at least ORDERS_PER_TENANT orders for each tenant before running.
The task weights produce approximately 90% own-tenant lookups and 10%
cross-tenant checks. An expected 404 counts as a successful isolation check.
"""

import random
from uuid import UUID, uuid5

from locust import HttpUser, between, task

TENANT_IDS = (
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
)
SEED_NAMESPACE = UUID("f61ee310-7ec8-4c42-a265-f75c9cef40a7")
ORDERS_PER_TENANT = 1000


def seeded_order_id(tenant_id: str) -> str:
    index = random.randrange(ORDERS_PER_TENANT)
    return str(uuid5(SEED_NAMESPACE, f"{tenant_id}:order:{index}"))


class OrderLookupUser(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        # Each simulated user keeps the same tenant identity across requests.
        self.tenant_id = random.choice(TENANT_IDS)
        self.other_tenant_id = next(
            tenant_id for tenant_id in TENANT_IDS if tenant_id != self.tenant_id
        )
        self.client.headers.update({"X-Tenant-ID": self.tenant_id})

    @task(9)
    def lookup_own_order(self):
        order_id = seeded_order_id(self.tenant_id)
        with self.client.get(
            f"/api/v1/orders/{order_id}",
            name="GET /api/v1/orders/{order_id} [own tenant]",
            timeout=5,
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Expected 200, got {response.status_code}")
                return
            try:
                order = response.json()
            except ValueError:
                response.failure("Order response is not valid JSON")
                return
            if not isinstance(order, dict) or (
                order.get("id") != order_id
                or order.get("tenant_id") != self.tenant_id
            ):
                response.failure("Returned order ID or tenant does not match the request")

    @task(1)
    def reject_other_tenants_order(self):
        order_id = seeded_order_id(self.other_tenant_id)
        with self.client.get(
            f"/api/v1/orders/{order_id}",
            name="GET /api/v1/orders/{order_id} [cross tenant]",
            timeout=5,
            catch_response=True,
        ) as response:
            if response.status_code == 404:
                response.success()
            else:
                response.failure(
                    f"Expected 404 for another tenant's order, got {response.status_code}"
                )
