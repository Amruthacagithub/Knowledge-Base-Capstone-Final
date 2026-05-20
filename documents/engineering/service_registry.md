# Service Registry — TechNova Platform

## Core Services

| Service | Owner Team | Upstream Dependencies |
|---------|------------|----------------------|
| Web App | Frontend Team | API Gateway |
| API Gateway | Platform Team | User Service, Billing Service |
| User Service | Identity Team | PostgreSQL Database |
| Auth Service | Identity Team | User Service, Redis Cache |
| Billing Service | Platform Team | Stripe Gateway, PostgreSQL Database |
| Document Service | Search Team | Elasticsearch Cluster, S3 Storage |
| Notification Service | Platform Team | SendGrid API, Slack API |
| Search Indexer | Search Team | Document Service, Elasticsearch Cluster |

## Dependency Notes

- **Web App** depends on **API Gateway** for all external API calls.
- **API Gateway** routes traffic to **User Service** and **Billing Service**.
- **Auth Service** depends on **User Service** for account lookups.
- **Billing Service** depends on **Stripe Gateway** for payment authorization.
- **Document Service** depends on **Elasticsearch Cluster** for full-text indexing.
- **Notification Service** depends on **SendGrid API** for email delivery.

## Change Control

Update this registry when a new service is added or ownership changes. Security reviews required for new external integrations.
