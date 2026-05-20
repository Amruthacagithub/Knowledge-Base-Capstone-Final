# Internal API Keys — Engineering (RESTRICTED)

**Classification:** Restricted — Engineering and Admin only.

## Production Keys

- **Stripe Gateway** production key: stored in AWS Secrets Manager (`stripe/prod/api`).
- **SendGrid API** production key: stored in AWS Secrets Manager (`sendgrid/prod/api`).
- **Internal Admin API** master key: rotated quarterly; never shared with Sales.

## Access Rules

Only **Platform Team** engineers with break-glass approval may view production **Stripe Gateway** keys.

Sales and HR roles must not access this document or the referenced secrets.

## Rotation

All restricted keys rotate every 90 days or immediately after suspected compromise.
