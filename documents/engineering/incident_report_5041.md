# Incident Report INC-5041 — Payment API Degradation

**Date:** 2025-11-14  
**Severity:** SEV-2  
**Status:** Resolved

## Summary

Incident **INC-5041** affected **Billing Service** during a **Stripe Gateway** timeout spike. Customer checkout success rate dropped to 82% for 47 minutes.

## Timeline

- 14:02 UTC — Datadog alert on Billing Service error rate.
- 14:08 UTC — On-call confirmed **Stripe Gateway** latency above 5 seconds.
- 14:35 UTC — **Billing Service** retry policy adjusted; success rate recovered.
- 14:49 UTC — Incident resolved.

## Root Cause

**Stripe Gateway** regional latency; no code defect in **Billing Service**.

## Follow-up

- **SRE Team** owns post-incident action items.
- **Platform Team** to add circuit breaker between **Billing Service** and **Stripe Gateway**.

## Related Systems

**Web App** → **API Gateway** → **Billing Service** → **Stripe Gateway**
