# Platform Dependencies — TechNova Engineering

## Transitive Impact Map

If **API Gateway** fails, these user-facing flows are impacted:

- **Web App** login and checkout
- **Customer Checkout** payment submission

If **Auth Service** fails, **Web App** sessions cannot be validated.

If **User Service** fails, both **Auth Service** and **API Gateway** authenticated routes degrade.

If **PostgreSQL Database** fails, **User Service** and **Billing Service** lose persistence.

If **Elasticsearch Cluster** fails, **Document Service** search returns stale results only.

## External Vendors

- **Stripe Gateway** — payment authorization
- **SendGrid API** — email delivery
- **Slack API** — internal notifications

## Review Cadence

Dependency map reviewed quarterly by **SRE Team**.
