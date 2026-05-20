# Payment Outage Postmortem — November 2025

## Incident

**INC-5041** degraded **Billing Service** checkout flows when **Stripe Gateway** timeouts exceeded SLO thresholds.

## Impact

- 47 minutes of elevated payment failures
- **Web App** checkout funnel affected
- No data loss in **PostgreSQL Database**

## Dependency Chain Review

The payment authorization path runs:

**Customer Checkout** → **Web App** → **API Gateway** → **Billing Service** → **Stripe Gateway**

## Action Items

1. Add timeout budgets on **API Gateway** → **Billing Service** calls.
2. Document fallback messaging in **Web App**.
3. **Platform Team** to review **Stripe Gateway** webhook retries.

## Owner

**SRE Team** tracks remediation through Q1 2026.
