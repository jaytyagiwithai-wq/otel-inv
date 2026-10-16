# Orders domain and telemetry fields

I use these names consistently in the service span and its completion log so I can ask the same question of either record.

## Domain

- A tenant represents a customer organisation.
- Each order belongs to one tenant.
- A lookup asks for one order ID under one supplied tenant identity.
- Every returned order must match both IDs.
- An absent order and an order owned by a different tenant produce the same 404 response.

The client-supplied tenant header is a local/test identity shortcut. It is not proof that the caller belongs to that tenant. UUID validation failures produce HTTP 422 before the lookup service runs.

## Spans

| Span | Kind | Scope |
| --- | --- | --- |
| `GET /api/v1/orders/{order_id}` | SERVER | Handling the HTTP request |
| `orders.lookup` | INTERNAL | Query, response conversion, transaction completion, and completion logging |
| `SELECT orders_db` | CLIENT | SQL cursor execution; the exact generated name depends on instrumentation |
| `connect` when present | CLIENT | Obtaining a SQLAlchemy connection |

The active context sets parentage. The provider supplies configuration and export behavior; it does not decide which operations share a trace.

## Business attributes

| Field | Type | Meaning |
| --- | --- | --- |
| `app.operation` | string | `orders.lookup` or `readiness.check` |
| `app.tenant.id` | string | Tenant supplied for an order lookup |
| `app.order.id` | string | Requested order ID |
| `app.dependency` | string | `postgresql` |
| `app.outcome` | string | `success`, `not_found`, or `dependency_error` |
| `app.result.count` | integer | 1 or 0 for a completed lookup; absent on dependency errors |
| `app.order.status` | string | Returned order status; present only on a successful lookup |
| `app.duration_ms` | number | Service elapsed time measured with `perf_counter`; stops before completion logging |
| `error.type` | string | Original SQLAlchemy exception type on order dependency errors |

`app.duration_ms` and the span duration have slightly different measurement boundaries. The span includes its completion logging. The readiness error path currently uses `app.error.type` rather than `error.type` and does not emit a failure completion log; that path has not been normalised with the orders event.

The service emits `orders.lookup.completed` for success, not-found, and handled database failures. It emits `readiness.check.completed` after a successful readiness check. JSON logs include `timestamp`, `name`, `severity`, `service.name`, `deployment.environment.name`, an `attributes` object, and trace/span IDs when an active span context exists.

Service name, version, and environment also appear as span resource attributes. Tenant and order IDs are operation attributes. Their high cardinality is useful for trace/log investigation; I would not automatically copy them into metric labels.

## Outcomes

- `success`: the requested tenant owns the order and the service returned it.
- `not_found`: no order matched both IDs. This is an expected business outcome, not a database exception. The service raises `OrderNotFound` after closing the business span.
- `dependency_error`: SQLAlchemy failed. The route returns 503, and the completion log has ERROR severity. This is implemented but was not exercised in the recorded load runs.

## Future listing experiment

`list_recent_orders()` exists in the repository but has no service or HTTP route. It filters by tenant, sorts by creation time and ID descending, and defaults to 50 rows. Pagination, a bounded API limit, listing telemetry, and index experiments are not implemented. Sorting and limit invariants from the earlier plan apply to that future feature, not to the current single-order endpoint.
