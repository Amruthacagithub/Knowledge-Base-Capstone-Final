# CRM Workflow — TechNova Sales (Salesforce)

## Pipeline Stages

1. **Lead** — Inbound or outbound; BDR qualified
2. **Discovery** — AE held discovery call; BANT documented
3. **Demo** — Platform demo completed; technical champion identified
4. **Proposal** — Quote sent; pricing per `pricing_tiers.md`
5. **Negotiation** — Legal/procurement engaged
6. **Closed Won / Lost** — Contract signed or loss reason coded

## Required Fields

Every opportunity must have: amount, close date, next step, economic buyer, champion, competition, loss reason (if lost).

## Activity Standards

- **BDR:** 50 touches/week; 10 qualified meetings/month
- **AE:** 5 discovery calls/week; 2 demos/week minimum
- Log all calls and emails in Salesforce within 24 hours

## Lead Routing

| Segment | ARR potential | Owner |
|---------|---------------|-------|
| SMB | < $25k | Inside Sales |
| Mid-Market | $25k–$150k | Regional AE |
| Enterprise | > $150k | Enterprise AE + SE |

## Quote Approval

| Discount | Approver |
|----------|----------|
| 0–10% | AE manager |
| 11–15% | Sales Director |
| 16%+ | VP Sales + Finance |

## Integration with Engineering

SE requests for POC: Jira ticket `POC-*` with customer name, use case, end date. Auto-expire sandbox after 30 days.

## Reporting

Weekly pipeline review: commit, best case, pipeline coverage (3× quota rule).
