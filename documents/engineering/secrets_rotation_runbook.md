# Secrets Rotation Runbook — Engineering

## Scope

Rotates credentials for **Stripe Gateway**, **SendGrid API**, and internal service tokens.

## Procedure

1. Generate new secret in AWS Secrets Manager.
2. Update **Billing Service** deployment to reference new **Stripe Gateway** credential.
3. Update **Notification Service** for **SendGrid API** credential.
4. Validate checkout and email delivery in staging.
5. Revoke prior secret after 24-hour dual-read window.

## Owners

- **Platform Team**: **Stripe Gateway** and payment secrets
- **Platform Team**: **SendGrid API** secrets
- **SRE Team**: database and cache credentials

## References

See `internal_api_keys.md` for restricted key inventory (Engineering only).
