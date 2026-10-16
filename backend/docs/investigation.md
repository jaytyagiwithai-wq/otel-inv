# Notes from the local runs

I wanted to go beyond seeing spans appear in a console. These are the requests I generated, the timings I observed, and what I could reasonably infer from them.

The tables below were recorded during the lab on 16 October 2026. They are development-machine observations, not a capacity claim. The user count, spawn rate, and exact duration of the full order run were not saved, so I cannot reproduce that run exactly. Locust's **Current RPS** column is a point-in-time rate, not the run's average throughput.

## Readiness: a slow connection, a fast query

Readiness runs `SELECT 1`. In trace `747e5544405d6163a0ccc0c4cdd14137`, the spans were:

| Operation | Duration |
| --- | ---: |
| HTTP request | ~126 ms |
| Connection acquisition | 73.3 ms |
| `SELECT 1` | 1.63 ms |
| Time outside those two database spans | ~51.07 ms |

The displayed timestamps put the start of `connect` about 46 ms after the HTTP span began. I did not instrument that interval further. The SQLAlchemy connection span covers obtaining a connection; the span alone does not separate connection creation, authentication, pool waiting, or checks.

My working explanation was first-use connection setup. I repeated the readiness workload without restarting the API so its pool could reuse connections.

| Measurement | First readiness run | Later readiness run |
| --- | ---: | ---: |
| Requests | 157 | 298 |
| Failed requests | 0 | 0 |
| Median | 8 ms | 8 ms |
| p95 | 19 ms | 18 ms |
| p99 | 130 ms | 31 ms |
| Average | 10.83 ms | 9.43 ms |
| Maximum | 132 ms | 32 ms |
| Current RPS at capture | 3.4 | 3.5 |

The median barely changed while the slow tail improved. That supports warm-up affecting a few requests. The samples are small, especially for p99, and the second run alone does not prove the exact cause of the connection delay. I did not fix a slow SQL query here: SQL execution in the inspected request took only 1.63 ms.

## Orders: test the response as well as its timing

The order load test uses the two seeded tenants. Each simulated user keeps one tenant identity. Most requests fetch an order belonging to that tenant. The remaining requests try an order owned by the other tenant and expect the same 404 used for a missing order.

| Scenario | Requests | Failed checks | Median | p95 | p99 | Average | Maximum |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Own tenant | 1,241 | 0 | 9 ms | 18 ms | 32 ms | 10.02 ms | 91 ms |
| Cross tenant | 128 | 0 | 9 ms | 16 ms | 21 ms | 9.46 ms | 32 ms |
| Aggregate | 1,369 | 0 | 9 ms | 18 ms | 32 ms | 9.96 ms | 91 ms |

Current aggregate RPS at capture was 13.2. I do not interpret it as maximum throughput. Zero failed checks means the responses met this test's expectations, including the intentional 404s. It is not proof that the application has production authentication or that every possible isolation failure has been tested.

## Split the internal timings by tenant and outcome

I queried the `orders.lookup` spans using the tenant and outcome attributes added in the service. Tenant A and B are the UUIDs starting with `11111111` and `22222222` respectively.

| Tenant | Outcome | Lookup spans | Business-span p95 | Business-span maximum |
| --- | --- | ---: | ---: | ---: |
| A | not_found | 71 | 13.9 ms | 29.2 ms |
| A | success | 601 | 13.2 ms | 50.7 ms |
| B | not_found | 57 | 10.5 ms | 15.8 ms |
| B | success | 640 | 14.1 ms | 51.3 ms |

The successful span counts summed to 1,241, and the not-found counts to 128, matching the Locust scenarios. The success p95 values looked similar across tenants in this run. I would need repeated, controlled runs before treating a difference of about 1 ms as meaningful.

The business span covers a smaller interval than the full client request. The two p95 values describe different distributions; subtracting them would not give a reliable measurement of network overhead.

## What I took from this

- A successful SQL call does not mean the application found an order. I needed the `success` and `not_found` business outcomes.
- One HTTP request can produce several spans, all linked by context. Database calls are client spans even though the instrumented code runs in the API process.
- The completion log is emitted before the business span ends and carries that span's IDs. It does not wait for an entire trace to finish.
- ClickHouse's exporter derives span duration from the end and start timestamps. Grafana's trace query converts its stored nanoseconds to milliseconds.
- A load-test percentile tells me which requests to inspect. It does not explain why they were slow.

## Not completed

I seeded a larger dataset and added a repository query for newest orders. I stopped before exposing a listing endpoint or doing an `EXPLAIN ANALYZE` and index comparison. Infrastructure metrics, cross-service propagation, SLOs, sampling, and recovery experiments are left for a later AI project.

## Final verification

Before publishing, I checked the current code and running stack separately from the earlier performance runs:

- Six automated tests passed for own-tenant lookup, indistinguishable missing/cross-tenant responses, invalid or absent tenant headers, span/log context correlation, and disabling the tenant shortcut in production mode.
- Alembic reported revision `7e8226d67f4c` at head and no model/schema differences.
- Compose configuration validated and all four local containers were running.
- The live PostgreSQL table contained 100,000 orders for each tenant.
- Live requests returned 200 for readiness and own-tenant lookup, 404 for cross-tenant lookup, and 422 for a missing tenant header.
- ClickHouse contained the new success and not-found traces. Each had HTTP → business → database parentage, and each business span joined to one completion log using both trace ID and span ID.

The fresh checks verify the local path works; they do not replace the missing workload settings in the earlier benchmark tables or test restart durability.
