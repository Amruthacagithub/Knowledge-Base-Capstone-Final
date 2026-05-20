# Payment Data Flow — TechNova Platform

## Checkout Authorization Chain

1. **Customer Checkout** submits payment details to **Web App**.
2. **Web App** depends on **API Gateway** to reach backend services.
3. **API Gateway** routes payment requests to **Billing Service**.
4. **Billing Service** depends on **Stripe Gateway** to authorize charges.
5. **Billing Service** persists transactions in **PostgreSQL Database**.

## Failure Modes

If **Stripe Gateway** is unavailable, **Billing Service** queues retries for up to 24 hours.

If **API Gateway** returns 502 errors, **Web App** displays a payment-unavailable message.

## Monitoring

Payment-path latency is tracked from **Web App** through **Billing Service** to **Stripe Gateway**.
