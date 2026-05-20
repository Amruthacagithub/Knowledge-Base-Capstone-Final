# Data Residency Policy — Engineering

## Regions

Customer data for **User Service** and **Billing Service** resides in `us-east-1` by default.

Enterprise customers may select EU (`eu-west-1`) residency for **Document Service** and **PostgreSQL Database** replicas.

## Storage

**S3 Storage** buckets use SSE-KMS encryption in the selected region.

## Restrictions

Cross-region replication for **PostgreSQL Database** requires Security approval.

## Compliance

Data residency choices are documented in customer contracts and the **Enterprise Discount Policy**.
