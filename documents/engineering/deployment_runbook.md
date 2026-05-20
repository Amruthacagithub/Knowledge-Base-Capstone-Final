# Deployment Runbook — TechNova Platform

## Overview

Production deployments use **GitHub Actions** → **Argo CD** → **EKS**. All production changes require peer review and automated checks.

## Pre-Deploy Checklist

- [ ] PR approved by 2 engineers (1 must be code owner)
- [ ] CI green: unit tests, integration tests, SAST scan
- [ ] Change ticket linked (CHG-* for production)
- [ ] Rollback plan documented in PR description
- [ ] On-call notified if deploy outside business hours

## Standard Deploy (Blue/Green)

1. Merge to `main` triggers build pipeline.
2. Image tagged `sha-<git-sha>` pushed to ECR.
3. Argo CD syncs staging; smoke tests run automatically.
4. Manual promotion to production via Argo UI or `argocd app sync billing-prod`.
5. Watch Datadog deploy markers for 15 minutes.
6. Mark change ticket complete.

## Rollback Procedure

```bash
kubectl rollout undo deployment/<service> -n production
argocd app rollback <app-name> <revision>
```

Verify error rate returns to baseline within 10 minutes. If not, escalate to SEV-2 incident.

## Database Migrations

- Forward-only migrations in `migrations/` folder.
- Run via dedicated job **before** app deploy.
- Breaking migrations require maintenance window (Sundays 02:00–06:00 UTC).
- Never run manual SQL in production without TL + DBA review.

## Feature Flags

Use LaunchDarkly for risky features. Default off in production; enable for internal dogfood first.

## Freeze Periods

No optional production deploys during:

- Last week of quarter (sales close)
- Black Friday week
- Active SEV-1/SEV-2 incident

## Post-Deploy

Update `#engineering-releases` Slack with version and notable changes.
