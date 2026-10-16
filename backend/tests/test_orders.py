import json
import logging
import pytest
from opentelemetry.trace import StatusCode

from otel_b.scripts.seed_orders import TENANT_A, TENANT_B, seed_order_id


def test_own_tenant_gets_its_order(lab):
    client, _ = lab
    order_id = seed_order_id(TENANT_A, 0)
    response = client.get(
        f"/api/v1/orders/{order_id}", headers={"X-Tenant-ID": str(TENANT_A)}
    )
    assert response.status_code == 200
    assert response.json()["id"] == str(order_id)
    assert response.json()["tenant_id"] == str(TENANT_A)


def test_other_tenants_order_and_missing_order_have_same_response(lab):
    client, exporter = lab
    headers = {"X-Tenant-ID": str(TENANT_B)}
    other = client.get(f"/api/v1/orders/{seed_order_id(TENANT_A, 0)}", headers=headers)
    missing = client.get(
        "/api/v1/orders/00000000-0000-4000-8000-000000000000", headers=headers
    )
    assert other.status_code == missing.status_code == 404
    assert other.json() == missing.json() == {"detail": "Order not found"}
    spans = [s for s in exporter.get_finished_spans() if s.name == "orders.lookup"]
    assert len(spans) == 2
    assert all(s.attributes["app.outcome"] == "not_found" for s in spans)
    assert all(s.status.status_code == StatusCode.UNSET and not s.events for s in spans)


@pytest.mark.parametrize("headers", [{}, {"X-Tenant-ID": "not-a-uuid"}])
def test_invalid_tenant_identity_does_not_enter_lookup(lab, headers):
    client, exporter = lab
    response = client.get(f"/api/v1/orders/{seed_order_id(TENANT_A, 0)}", headers=headers)
    assert response.status_code == 422
    assert not any(s.name == "orders.lookup" for s in exporter.get_finished_spans())


def test_business_span_and_completion_log_share_context(lab, caplog):
    client, exporter = lab
    with caplog.at_level(logging.INFO, logger="otel_b.events"):
        response = client.get(
            f"/api/v1/orders/{seed_order_id(TENANT_A, 0)}",
            headers={"X-Tenant-ID": str(TENANT_A)},
        )
    assert response.status_code == 200
    spans = exporter.get_finished_spans()
    business = next(s for s in spans if s.name == "orders.lookup")
    http = next(s for s in spans if s.kind.name == "SERVER")
    event = next(
        json.loads(record.getMessage())
        for record in caplog.records if record.name == "otel_b.events"
    )
    assert business.parent.span_id == http.context.span_id
    assert business.context.trace_id == http.context.trace_id
    assert event["trace_id"] == format(business.context.trace_id, "032x")
    assert event["span_id"] == format(business.context.span_id, "016x")
    assert event["attributes"]["app.outcome"] == business.attributes["app.outcome"] == "success"
    assert event["attributes"]["app.result.count"] == 1


def test_tenant_header_shortcut_is_disabled_in_production(lab, monkeypatch):
    from otel_b.core.config import get_settings

    client, exporter = lab
    monkeypatch.setattr(get_settings(), "environment", "production")
    response = client.get(
        f"/api/v1/orders/{seed_order_id(TENANT_A, 0)}",
        headers={"X-Tenant-ID": str(TENANT_A)},
    )
    assert response.status_code == 503
    assert not any(s.name == "orders.lookup" for s in exporter.get_finished_spans())
