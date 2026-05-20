# Incident Response Process — TechNova Engineering

## Purpose

This document defines how TechNova Engineering detects, responds to, and learns from production incidents. It applies to all services in the TechNova Platform.

## Severity Levels

| Severity | Definition | Response target | Example |
|----------|------------|-----------------|---------|
| **SEV-1** | Complete outage or data loss risk | 15 min acknowledge, exec bridge | Payment API down |
| **SEV-2** | Major degradation, no workaround | 30 min acknowledge | Search latency 10× normal |
| **SEV-3** | Partial impact, workaround exists | 2 hours | Email delay |
| **SEV-4** | Minor, next business day | Best effort | Dashboard typo |

## Roles

- **Incident Commander (IC):** Coordinates response, owns timeline, communicates status.
- **Technical Lead:** Drives mitigation and root cause investigation.
- **Communications Lead:** Updates status page and internal Slack `#incidents`.
- **Scribe:** Documents timeline in incident ticket (Jira INC-*).

## Lifecycle

### 1. Detection

Alerts from Datadog, PagerDuty, or customer reports create incidents. On-call engineer acknowledges within SLA.

### 2. Triage

IC assigns severity, opens Slack war room, notifies stakeholders per severity matrix.

### 3. Mitigation

Focus on customer impact reduction: rollback, feature flag, scale-up, traffic shift. Root cause analysis may follow mitigation.

### 4. Resolution

Service restored and monitored for 30 minutes. IC declares incident resolved.

### 5. Post-Incident Review (PIR)

Required for SEV-1 and SEV-2 within **5 business days**. PIR includes timeline, root cause, action items, and blameless learnings.

## Communication Templates

Status updates every **30 minutes** for SEV-1, **60 minutes** for SEV-2. Customer-facing updates via status.technova.com.

## Tooling

- PagerDuty schedules: `engineering-oncall` rotation
- Runbooks: `on_call_runbook.md`, `deployment_runbook.md`
- Incident tickets: Jira project INC

## Escalation

If IC unavailable after 15 minutes, escalate to Engineering Manager then VP Engineering.
