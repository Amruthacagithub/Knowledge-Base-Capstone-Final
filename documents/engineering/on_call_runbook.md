# On-Call Runbook — TechNova Platform

## On-Call Rotation

Engineering maintains a **primary** and **secondary** on-call engineer via PagerDuty. Rotations change weekly (Monday 09:00 UTC). Calendar: `oncall.technova.com`.

## First 5 Minutes Checklist

1. Acknowledge PagerDuty alert within **5 minutes**.
2. Open incident channel `#incident-YYYYMMDD-shortname`.
3. Check Datadog dashboard **Platform Overview** for error rate, latency, saturation.
4. Assign yourself IC or delegate to senior if SEV-1.
5. Post initial status: "Investigating [alert name], impact unknown."

## Common Alerts

### High Error Rate — Billing Service

- Check recent deploys in GitHub Actions (last 2 hours).
- Review Stripe webhook failures in Billing admin.
- Roll back if deploy correlation > 80%: `kubectl rollout undo deployment/billing -n production`.
- See incident **INC-5023** for billing connector timeout pattern.

### API Gateway 502/503

- Verify Kong pod health: `kubectl get pods -n gateway`.
- Check upstream User/Billing service health endpoints.
- Scale gateway replicas if CPU > 85%: `kubectl scale deployment/kong --replicas=5`.

### Elasticsearch Cluster Yellow/Red

- Check disk usage on data nodes; delete old indices per retention policy.
- Pause heavy reindex jobs in Document Service.

### PostgreSQL Connection Pool Exhausted

- Identify long-running queries in Datadog DBM.
- Restart affected service pods after killing runaway queries (with TL approval).

## Escalation Path

Primary (15 min) → Secondary (15 min) → Engineering Manager → VP Engineering → CTO (SEV-1 only).

## Handoff

End of shift: post summary in `#engineering-oncall` with open incidents and flaky alerts.

## References

- `incident_response_process.md` — severity and PIR
- `monitoring_guide.md` — dashboards and SLOs
- `architecture_overview.md` — **tech stack** and service map
