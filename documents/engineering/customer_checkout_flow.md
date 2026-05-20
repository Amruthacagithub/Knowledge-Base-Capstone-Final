# Customer Checkout Flow — TechNova Platform

## Steps

1. Customer opens **Web App** checkout page.
2. **Web App** depends on **API Gateway** for backend APIs.
3. **API Gateway** routes authentication to **Auth Service**.
4. **Auth Service** depends on **User Service** for identity.
5. **API Gateway** routes payment to **Billing Service**.
6. **Billing Service** depends on **Stripe Gateway** to capture funds.

## Success Criteria

Checkout completes only when **Stripe Gateway** returns an authorized charge.

## Observability

Trace IDs propagate from **Web App** through **API Gateway** to **Billing Service**.
