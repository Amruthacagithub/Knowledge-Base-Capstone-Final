# Vendor Integrations — TechNova Platform

## Payment

**Billing Service** integrates with **Stripe Gateway** for card payments and invoicing.

## Email

**Notification Service** integrates with **SendGrid API** for transactional email.

## Chat

**Notification Service** integrates with **Slack API** for internal incident channels.

## Search

**Document Service** integrates with **Elasticsearch Cluster** for enterprise search.

## Identity

**Auth Service** depends on **User Service**; **User Service** depends on **PostgreSQL Database**.

## Gateway

**API Gateway** routes external traffic to **User Service** and **Billing Service**.
