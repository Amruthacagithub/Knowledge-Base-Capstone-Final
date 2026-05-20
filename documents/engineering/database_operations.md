# Database Operations Guide — TechNova

## PostgreSQL (Primary OLTP)

**Version:** PostgreSQL 16 on AWS RDS (Multi-AZ).

### Connection

- Applications use PgBouncer in **transaction mode**.
- Max connections per service: 50 (configurable in Helm values).
- Read replicas: 2 replicas for reporting workloads only; no writes.

### Backup and Recovery

- Automated snapshots every **24 hours**; retention **35 days**.
- Point-in-time recovery (PITR) enabled to 5-minute granularity.
- Quarterly restore drill documented in SEC compliance folder.

### Maintenance

- Minor version upgrades: Sunday maintenance window.
- Index creation: use `CONCURRENTLY` in production.
- Long queries > 30s flagged in Datadog DBM.

## Redis

**Version:** Redis 7 (ElastiCache cluster mode).

Used for session cache, rate limiting, pub/sub. No persistent customer PII in Redis values. TTL required on all keys.

## Elasticsearch

**Version:** Elasticsearch 8 for document full-text and audit search.

Index lifecycle: hot 7 days → warm 30 days → delete. Reindex jobs run via Document Service worker queue.

## Runbooks

- Failover: RDS automatic; verify app reconnect via health checks.
- Connection storm: scale PgBouncer, restart affected pods.
- Disk full: expand storage + run `VACUUM` during low traffic.

## Contacts

DBA on-call: PagerDuty `dba-oncall`. Engineering questions: `#database` Slack.
