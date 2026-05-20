# Notification Pipeline — TechNova Platform

## Architecture

**Notification Service** orchestrates outbound customer and internal messages.

## External Dependencies

- **Notification Service** depends on **SendGrid API** for transactional email.
- **Notification Service** depends on **Slack API** for on-call and incident channels.

## Internal Dependencies

- **Billing Service** publishes payment-receipt events consumed by **Notification Service**.
- **User Service** supplies recipient preferences to **Notification Service**.

## Failure Handling

If **SendGrid API** is unavailable, messages queue in SQS for up to 72 hours.
