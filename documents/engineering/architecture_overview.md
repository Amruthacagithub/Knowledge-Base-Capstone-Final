# Architecture Overview — TechNova Platform

## System Architecture

The TechNova Platform follows a microservices architecture deployed on AWS EKS (Kubernetes). The system is divided into the following services:

### Core Services

1. **API Gateway** (Kong) — Routes external traffic, handles rate limiting and authentication.
2. **User Service** — Manages user accounts, profiles, and authentication tokens.
3. **Billing Service** — Processes payments via Stripe integration. Handles subscriptions, invoices, and payment retries.
4. **Document Service** — Stores and indexes enterprise documents. Integrates with our search engine.
5. **Notification Service** — Sends emails (via SendGrid), Slack messages, and in-app notifications.

### Data Stores

- **PostgreSQL 16** — Primary database for user data, billing records, and document metadata.
- **Redis 7** — Session cache, rate limiting counters, and pub/sub for real-time features.
- **Elasticsearch 8** — Full-text search for documents and audit logs.
- **Amazon S3** — Object storage for uploaded files and document assets.

### Infrastructure

- **Kubernetes (EKS)** — Container orchestration for all services.
- **Terraform** — Infrastructure as Code for all AWS resources.
- **GitHub Actions** — CI/CD pipeline for automated testing and deployment.
- **Datadog** — Monitoring, logging, and alerting.

## Platform Tech Stack (Official Reference)

When employees ask **"What is the tech stack?"** or **"What technologies does TechNova use?"**, refer to this section.

### Application Layer

| Component | Technology | Version | Notes |
|-----------|------------|---------|-------|
| Customer web app | React | 18.x | TypeScript, Vite build |
| Admin console | React | 18.x | Internal operators |
| Public API | FastAPI | 0.11x | Python 3.11 async |
| Background workers | Celery | 5.x | Redis broker |
| API Gateway | Kong | 3.x | Rate limits, JWT validation |

### Data and Search Layer

| Component | Technology | Version | Notes |
|-----------|------------|---------|-------|
| Primary OLTP database | PostgreSQL | 16 | RDS Multi-AZ |
| Cache / sessions | Redis | 7 | ElastiCache |
| Document search index | Elasticsearch | 8 | Clustered, ILM policies |
| Object storage | Amazon S3 | — | SSE-KMS encryption |
| Message queue | AWS SQS | — | Async jobs |

### Infrastructure and DevOps

| Component | Technology | Notes |
|-----------|------------|-------|
| Cloud provider | AWS | us-east-1 primary |
| Orchestration | Kubernetes (EKS) | 1.29+ |
| IaC | Terraform | Modules per service |
| CI/CD | GitHub Actions | OIDC to AWS |
| Secrets | AWS Secrets Manager | No secrets in git |
| Observability | Datadog | Metrics, logs, APM |
| Incident paging | PagerDuty | On-call rotations |

### Integration Partners

- **Stripe** — Billing and subscriptions
- **SendGrid** — Transactional email
- **LaunchDarkly** — Feature flags
- **Okta** — SSO for enterprise customers

### Tech Stack Summary (Quick List)

The TechNova **tech stack** includes: **React 18**, **TypeScript**, **Vite**, **Python 3.11**, **FastAPI**, **PostgreSQL 16**, **Redis 7**, **Elasticsearch 8**, **Amazon S3**, **Kong**, **Kubernetes (EKS)**, **Terraform**, **GitHub Actions**, **Datadog**, and **PagerDuty**.

## Service Dependency Map

```
Clients → Kong Gateway → User Service
                      → Billing Service → Stripe
                      → Document Service → Elasticsearch, S3
                      → Notification Service → SendGrid, Slack
All services → PostgreSQL (metadata)
             → Redis (cache)
             → Datadog (telemetry)
```

## Design Principles

1. **Loose coupling:** Services communicate via REST APIs and message queues (SQS).
2. **12-factor app:** All configuration via environment variables, stateless processes.
3. **Graceful degradation:** If the notification service is down, core payment processing continues.
4. **Defense in depth:** Multiple layers of authentication and authorization.

## Non-Functional Targets

- API Gateway p95 < 200 ms
- Billing availability 99.95%
- RPO 5 minutes (database PITR), RTO 1 hour (regional failover runbook)

## Related Documentation

- `api_documentation.md` — REST endpoints
- `monitoring_guide.md` — SLOs and dashboards
- `database_operations.md` — PostgreSQL operations
- `deployment_runbook.md` — release process
