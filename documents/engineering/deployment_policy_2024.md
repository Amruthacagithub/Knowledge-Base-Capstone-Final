# Deployment Policy — 2024 Edition

**Effective:** 2024-01-01 to 2024-12-31  
**Status:** Superseded by 2025 policy

## Production Deploy Windows

Production deploys are allowed Monday through Thursday, 09:00–17:00 UTC.

Friday production deploys are allowed with VP Engineering approval.

## Approval

- Standard deploys: Engineering Manager approval.
- Database migrations: DBA + Engineering Manager approval.

## Rollback

All production deploys must support rollback within 15 minutes via GitHub Actions.

## Notes

This policy was replaced on 2025-01-01. See `deployment_policy_2025.md` for current rules.
