# Integration Map — TechNova Platform

## Customer-Facing Path

Clients connect to **Web App**. **Web App** depends on **API Gateway**.

**API Gateway** routes to **User Service** for authentication and profile APIs.

**API Gateway** routes to **Billing Service** for subscription and payment APIs.

## Payment Path

**Billing Service** depends on **Stripe Gateway** for card authorization and settlement.

**Billing Service** writes billing records to **PostgreSQL Database**.

## Document Search Path

**Document Service** depends on **Elasticsearch Cluster** for indexed search.

**Search Indexer** depends on **Document Service** for source documents.

## Notification Path

**Notification Service** depends on **SendGrid API** for outbound email.

**Notification Service** depends on **Slack API** for internal alerts.

## Auth Path

**Auth Service** depends on **User Service** for credential validation.

**User Service** depends on **PostgreSQL Database** for account storage.
