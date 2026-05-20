# Monitoring and SLO Guide — TechNova Platform

## Observability Stack

TechNova uses **Datadog** for metrics, logs, traces, and synthetics. **PagerDuty** routes alerts to on-call.

## Golden Signals (per service)

1. **Latency** — p50, p95, p99 request duration
2. **Traffic** — requests per second
3. **Errors** — 5xx rate and business error codes
4. **Saturation** — CPU, memory, connection pools

## Key Dashboards

| Dashboard | URL slug | Owner |
|-----------|----------|-------|
| Platform Overview | `platform-overview` | SRE |
| Billing Service | `billing-deep-dive` | Billing team |
| API Gateway | `kong-gateway` | Platform |
| Document Search | `document-search` | Search team |

## Service Level Objectives (SLOs)

| Service | Availability | p95 latency |
|---------|--------------|-------------|
| API Gateway | 99.9% | < 200 ms |
| Billing API | 99.95% | < 500 ms |
| Document Search | 99.5% | < 2 s |
| Notification Service | 99.0% | < 5 s (async) |

Error budget policy: if monthly budget exhausted, feature freeze until recovery plan approved.

## Alert Hygiene

- Every alert must link to a runbook section.
- No alert without owner team tag.
- Flapping alerts tuned or snoozed with ticket.

## Logging Standards

Structured JSON logs with `trace_id`, `user_id` (hashed), `service`, `level`. Retention: 30 days hot, 1 year cold (S3).

## Synthetic Checks

External probes every 5 minutes from US, EU on:

- `https://api.technova.com/health`
- `https://app.technova.com/login`

## Related Documents

- `on_call_runbook.md`
- `architecture_overview.md` — **platform tech stack**
- `incident_response_process.md`
