# Incident Report — INC-5023: Payment Service Outage

**Severity:** P1 (Critical)
**Date:** January 15, 2026
**Duration:** 2 hours 45 minutes (14:30 — 17:15 UTC)
**Affected Services:** Payment processing, Billing API, Customer checkout
**Incident Commander:** Raj Patel (Staff Engineer)

## Summary

The payment processing service experienced a complete outage for approximately 2 hours and 45 minutes. During this time, all customer transactions failed with error code 5023 ("Billing connector timeout"). The root cause was an expired TLS certificate on the connection between our billing microservice and the third-party payment gateway (Stripe).

## Timeline

| Time (UTC) | Event |
|-----------|-------|
| 14:30 | First alerts fired — payment success rate dropped below 50% |
| 14:35 | On-call engineer (Sarah) acknowledged the alert and began investigation |
| 14:45 | Error logs showed repeated "TLS handshake failure" errors on the billing connector |
| 15:00 | Incident escalated to P1; Raj Patel joined as Incident Commander |
| 15:15 | Root cause identified: TLS certificate for payment gateway connection expired at 14:28 UTC |
| 15:30 | New certificate generated and deployed to staging |
| 16:00 | Certificate deployed to production billing service |
| 16:15 | Payment success rate began recovering |
| 17:15 | Full recovery confirmed; incident resolved |

## Root Cause

The TLS certificate used for mutual authentication between our billing microservice and Stripe's API expired. The certificate had been manually provisioned 12 months ago and was not tracked in our automated certificate management system.

When the certificate expired, all outgoing connections from the billing service to Stripe failed with a TLS handshake error, which surfaced to users as error code **5023** ("Billing connector timeout").

## Impact

- **4,200 failed transactions** during the outage window.
- **$380,000 in delayed revenue** (transactions were retried successfully after recovery).
- **~1,500 customers** saw checkout errors.
- No data loss occurred.

## Action Items

1. **Migrate all certificates to automated management** (Let's Encrypt + cert-manager) — Owner: DevOps team, due Feb 15.
2. **Add certificate expiry monitoring** with alerts at 30, 14, and 7 days before expiry — Owner: SRE team, due Jan 30.
3. **Create a runbook** for certificate rotation in the billing service — Owner: Raj Patel, due Jan 25.
4. **Post-mortem review meeting** scheduled for January 20 with all stakeholders.

## Lessons Learned

- Manually managed certificates are a single point of failure. Automation is essential.
- Our monitoring detected the issue within 5 minutes, which is good, but the resolution took too long because the on-call engineer had to find the right certificate and regenerate it manually.
- We need better documentation for the billing service's infrastructure dependencies.
