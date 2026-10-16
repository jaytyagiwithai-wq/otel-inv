-- Run each query separately in Grafana Explore using the ClickHouse data source.
-- $__timeFilter uses the selected Grafana time range. Choose the test's interval.
-- Duration in the exporter table is nanoseconds; trace visualizations expect ms.

-- 1. Table: newest spans.
SELECT Timestamp, ServiceName, SpanName, TraceId, SpanId,
       round(Duration / 1000000, 3) AS duration_ms
FROM otel.otel_traces
WHERE $__timeFilter(Timestamp)
ORDER BY Timestamp DESC
LIMIT 20;

-- 2. Table: slowest readiness HTTP spans.
SELECT Timestamp, TraceId, round(Duration / 1000000, 3) AS duration_ms
FROM otel.otel_traces
WHERE SpanName = 'GET /api/v1/health/ready'
  AND $__timeFilter(Timestamp)
ORDER BY Duration DESC
LIMIT 5;

-- 3. Traces: replace PASTE_TRACE_ID with one ID from a table query.
-- The aliases are the field names Grafana's trace panel expects.
SELECT TraceId AS traceID,
       SpanId AS spanID,
       ParentSpanId AS parentSpanID,
       ServiceName AS serviceName,
       SpanName AS operationName,
       Timestamp AS startTime,
       Duration / 1000000 AS duration,
       arrayMap(k -> map('key', k, 'value', SpanAttributes[k]),
                mapKeys(SpanAttributes)) AS tags,
       arrayMap(k -> map('key', k, 'value', ResourceAttributes[k]),
                mapKeys(ResourceAttributes)) AS serviceTags
FROM otel.otel_traces
WHERE TraceId = 'PASTE_TRACE_ID'
ORDER BY Timestamp ASC;

-- 4. Logs: use the SAME trace ID to find its correlated completion event.
SELECT Timestamp AS timestamp, Body AS body, SeverityText AS level,
       TraceId AS traceID, SpanId AS span_id, LogAttributes
FROM otel.otel_logs
WHERE TraceId = 'PASTE_TRACE_ID'
ORDER BY Timestamp ASC;

-- 5. Table: tenant and outcome breakdown of business spans.
SELECT SpanAttributes['app.tenant.id'] AS tenant_id,
       SpanAttributes['app.outcome'] AS outcome,
       count() AS lookups,
       round(avg(Duration) / 1000000, 2) AS avg_ms,
       round(quantile(0.95)(Duration) / 1000000, 2) AS p95_ms,
       round(max(Duration) / 1000000, 2) AS max_ms
FROM otel.otel_traces
WHERE SpanName = 'orders.lookup'
  AND $__timeFilter(Timestamp)
GROUP BY tenant_id, outcome
ORDER BY tenant_id, outcome;

-- 6. Table: logs joined to the exact span active when they were emitted.
-- File replay can duplicate logs after a Collector restart; this is not deduplication.
SELECT JSONExtractString(l.Body, 'name') AS event_name,
       t.SpanName AS operation,
       l.TraceId, l.SpanId,
       round(t.Duration / 1000000, 3) AS duration_ms
FROM otel.otel_logs AS l
INNER JOIN otel.otel_traces AS t
    ON l.TraceId = t.TraceId AND l.SpanId = t.SpanId
WHERE $__timeFilter(l.Timestamp)
ORDER BY l.Timestamp DESC
LIMIT 20;
