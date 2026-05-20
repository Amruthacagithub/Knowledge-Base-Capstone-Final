# Deployment Policy — 2025 Edition

**Effective:** 2025-01-01  
**Status:** Current

## Production Deploy Windows

Production deploys are allowed Monday through Thursday, 09:00–17:00 UTC.

Friday production deploys are not allowed without CTO approval.

## Approval

- Standard deploys: Engineering Manager approval.
- Database migrations: DBA + Engineering Manager approval.
- Payment-path changes involving **Billing Service** or **Stripe Gateway**: Platform Team lead approval.

## Rollback

All production deploys must support rollback within 10 minutes via GitHub Actions.

## Change from 2024

Friday deploys that were allowed with VP approval in 2024 now require CTO approval in 2025.
