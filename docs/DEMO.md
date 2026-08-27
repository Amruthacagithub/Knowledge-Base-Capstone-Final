# Demo Guide

Use the local setup in the root [README](../README.md). Confirm `GET http://127.0.0.1:8000/api/health` reports PostgreSQL and Qdrant as `up`, then open `http://127.0.0.1:5173`.

All seeded users use the `BOOTSTRAP_USER_PASSWORD` configured during setup.

## Suggested walkthrough

1. Log in as `amrutha@company.com` (HR) and ask: `What is the PTO policy?` Show the cited source panel and full document highlighting.
2. Log in as `harshini@company.com` (Engineer) and ask: `What are the salary bands?` The restricted Compensation Policy must remain hidden.
3. Log in as `bhaskar@company.com` (Admin) and repeat the salary query. Admin access demonstrates the RBAC difference.
4. As Engineer or Admin, ask: `How does a payment reach Stripe?` Expand the Trust details to show the selected route, claim-verification statuses, and evidence paths where available.
5. Ask: `How has remote work policy changed?` Open a Remote Work Policy document to show version history and the version-diff panel.
6. Ask: `What are our pricing tiers?` Show a PDF citation with its page number and open the document viewer.
7. As Admin, upload a small Markdown file and search for a distinctive phrase to demonstrate the ingestion flow.

## Reliable backup queries

| Purpose | Query |
|---|---|
| Local policy answer | `How many PTO days do full-time employees receive?` |
| Access denial | As Sales: `What are the internal API keys?` |
| Comparison route | `Compare Enterprise vs Professional pricing` |
| Engineering ownership | `What owns the notification pipeline?` |

## Honest presentation notes

- The graph improves traceability and permission-safe paths; it did not improve path recall over hybrid search in the checked-in comparison set.
- The local NLI verifier may label a relevant claim `Insufficient`, which causes a safe abstention. Engineering multi-hop queries are usually the strongest Trust-RAG demonstration.
- This is a local demonstration system. Enterprise SSO, shared distributed rate limiting, and an external penetration test are outside the project scope.
