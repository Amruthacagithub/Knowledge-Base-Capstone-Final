# Auth Service Overview — TechNova Platform

## Responsibilities

**Auth Service** issues JWT access tokens and validates session state for **Web App** clients.

## Dependencies

- **Auth Service** depends on **User Service** for account and role lookups.
- **User Service** depends on **PostgreSQL Database** for persistent identity records.
- **Auth Service** depends on **Redis Cache** for session revocation lists.

## Integration

**API Gateway** routes `/auth/*` requests to **Auth Service**.

Downstream services trust tokens signed by **Auth Service**.

## Security

MFA enforcement is coordinated with **User Service** profile flags.
