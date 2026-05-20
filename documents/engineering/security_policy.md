# Security Policy — TechNova Engineering

## Scope

All employees, contractors, and systems accessing TechNova production or customer data.

## Access Control

- **Least privilege:** IAM roles scoped per service; no shared admin accounts.
- **MFA required** for AWS, GitHub, Google Workspace, and VPN.
- **Production access** via break-glass role with 4-hour expiry and audit log.
- Quarterly access reviews by Security + Engineering managers.

## Secrets Management

- Secrets stored in **AWS Secrets Manager**; never in git.
- `.env` files local-only; pre-commit hooks scan for keys.
- API keys rotated every **90 days** or immediately on suspected compromise.

## Data Classification

| Level | Examples | Handling |
|-------|----------|----------|
| Public | Marketing site | No restrictions |
| Internal | Architecture docs | Employee access |
| Confidential | Customer lists | Need-to-know, encrypted |
| Restricted | Compensation, unreleased financials | Role-based, logged access |

## Vulnerability Management

- Dependabot alerts triaged within **7 days** (critical: 24 hours).
- Annual penetration test by third party; findings tracked in Jira SEC-*.
- Container images scanned in CI; critical CVEs block deploy.

## Incident Reporting

Report suspected breaches to security@technova.com and `#security-incidents` immediately. Do not delete logs or notify external parties without Security approval.

## Secure Development

- OWASP Top 10 training required annually.
- PRs must pass SAST (Semgrep) and dependency scan.
- PII must not appear in application logs.

## Customer Data

Encrypt at rest (AES-256) and in transit (TLS 1.2+). Data residency: US-East primary, EU-West for EU customers per contract.
