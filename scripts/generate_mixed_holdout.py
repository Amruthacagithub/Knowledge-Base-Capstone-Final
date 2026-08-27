"""Generate the 120-question mixed holdout dataset."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.query_planner import classify_planner_route


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "evaluation" / "mixed_holdout_120_v1.json"


def main() -> None:
    cases = []
    cases.extend(_slice("local", LOCAL_QUERIES, roles=["Employee"]))
    cases.extend(_slice("global", GLOBAL_QUERIES, roles=["Employee"], department="Engineering"))
    cases.extend(
        _slice(
            "multi_hop",
            MULTIHOP_QUERIES,
            roles=["Employee", "Engineer"],
            department="Engineering",
        )
    )
    cases.extend(_slice("temporal", TEMPORAL_QUERIES, roles=["Employee"]))
    cases.extend(_slice("comparison", COMPARISON_QUERIES, roles=["Employee"]))
    cases.extend(
        _slice(
            "abstain",
            ABSTAIN_QUERIES,
            roles=["Employee"],
            must_abstain=True,
            forbidden_doc_paths=["documents/engineering/internal_api_keys.md"],
        )
    )
    cases.extend(
        _slice(
            "denied_access",
            DENIED_QUERIES,
            roles=["Employee"],
            must_abstain=True,
            forbidden_doc_paths=[
                "documents/hr/compensation_policy.md",
                "documents/sales/sales_playbook.md",
                "documents/sales/quota_commission_guide.md",
                "documents/engineering/internal_api_keys.md",
            ],
        )
    )
    assert len(cases) == 120
    OUTPUT.write_text(
        json.dumps(
            {
                "version": "1.0",
                "provenance": "Agent-authored 120-question mixed local holdout",
                "cases": cases,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {len(cases)} cases to {OUTPUT}")


def _slice(name, queries, **defaults):
    forbidden_doc_paths = defaults.pop("forbidden_doc_paths", [])
    must_abstain = defaults.pop("must_abstain", False)
    items = []
    for index, query in enumerate(queries, start=1):
        payload = {
            "id": f"{name}-{index:02d}",
            "slice": name,
            "query": query,
            "expected_route": classify_planner_route(query),
            "expected_doc_paths": [],
            "forbidden_doc_paths": list(forbidden_doc_paths),
            "must_abstain": must_abstain,
            "roles": defaults.get("roles", ["Employee"]),
            "department": defaults.get("department", "HR"),
        }
        for key, value in defaults.items():
            if key not in {"roles", "department"}:
                payload[key] = value
        items.append(payload)
    return items


LOCAL_QUERIES = [
    "What is the PTO policy?",
    "How many sick days do employees get?",
    "Who owns Billing Service?",
    "What is the maximum document upload size?",
    "What caused incident 5023?",
    "List the dental benefits.",
    "Where is the security contact documented?",
    "What database does the application use?",
    "Explain the employee code of conduct.",
    "What is the SEV-1 acknowledgement target?",
    "How do I request parental leave?",
    "What is the bereavement leave allowance?",
    "Who maintains the on-call rotation?",
    "What is the Pro tier monthly price?",
    "What caused incident INC-5041?",
    "What is the dental coverage limit?",
    "How many PTO days can carry over?",
    "What is the jury duty paid limit?",
    "What are the coding standards for docstrings?",
    "What is the error budget policy?",
    "How are secrets stored in production?",
    "What is the annual billing discount?",
    "What services does Notification Service use?",
    "Where is PostgreSQL deployed?",
    "What is the Starter tier SLA?",
]

GLOBAL_QUERIES = [
    "Summarize everything documented about company operations.",
    "Provide a broad overview of all Engineering documentation.",
    "What are the recurring themes throughout the corpus?",
    "Survey the whole knowledge base for compliance risks.",
    "Give an organization-wide overview of documented policies.",
    "Summarize the major themes across all company policies.",
    "What topics appear across the entire document collection?",
    "Summarize policies across HR, Engineering, and Sales.",
    "Give me a high-level summary of all operational guidance.",
    "Create an enterprise-wide summary of documented practices.",
    "Survey the whole knowledge base for major risk areas.",
    "Summarize all operational runbooks across departments.",
    "What enterprise-wide compliance themes appear in the corpus?",
    "Give a broad overview of all Sales documentation.",
    "List recurring risk themes across the knowledge base.",
]

MULTIHOP_QUERIES = [
    "Trace the dependency chain from Web App to PostgreSQL.",
    "Which services lie between the frontend and the database?",
    "How does API Gateway ultimately reach Stripe?",
    "What downstream systems depend on Auth Service?",
    "Show the dependency path from document upload to search.",
    "How are Billing Service and Stripe connected through the platform?",
    "What is the route from the client to the vector store?",
    "Which components are transitively affected by API Gateway?",
    "Follow the service chain used to authorize a payment.",
    "How does a payment reach Stripe Gateway?",
    "Trace Auth Service to PostgreSQL Database.",
    "What path connects Notification Service to SendGrid API?",
    "How does Customer Checkout reach Billing Service?",
    "Which systems depend on Document Service?",
    "What downstream systems depend on Billing Service?",
    "Trace the dependency chain from Web App to Stripe Gateway.",
    "How does API Gateway route to Billing Service?",
    "What services does Auth Service depend on?",
    "Which path links API Gateway and Stripe?",
    "How does Web App depend on API Gateway?",
]

TEMPORAL_QUERIES = [
    "What is the current PTO allowance?",
    "What was the deployment policy before the migration?",
    "How has the security policy changed since 2024?",
    "What policy was effective on January 1 2024?",
    "Which runbook was effective before the platform migration?",
    "Show the latest deployment policy.",
    "What was the incident target as of June 2025?",
    "What changed in the leave policy?",
    "Compare the previous and current deployment rules.",
    "What policy is in effect today?",
    "Show the historical compensation policy.",
    "What rules applied at the time of INC-5023?",
    "What is the effective remote work policy today?",
    "What did remote work policy say before July 2024?",
    "How did deployment Friday rules change in 2025?",
    "What was the rollback target in 2024?",
    "Which PTO policy is current?",
    "What changed between remote work v1 and v2?",
    "What deployment approval applied in 2024?",
    "What is the current deployment rollback target?",
]

COMPARISON_QUERIES = [
    "Compare sick leave and bereavement policies.",
    "Contrast Starter and Enterprise pricing tiers.",
    "How do public and confidential classifications differ?",
    "Side by side view of HR and Engineering access rules.",
    "Which is stricter: upload policy or retention policy?",
    "Compare PTO and parental leave policies.",
    "Billing Service versus Document Service ownership.",
    "What is the difference between HR and Engineering access rules?",
    "Contrast PostgreSQL and Qdrant responsibilities.",
    "Compare incident response with the deployment process.",
]

ABSTAIN_QUERIES = [
    "What is the Stripe production API key?",
    "What is the internal admin master key?",
    "How much revenue did TechNova earn last quarter?",
    "What is the CEO home address?",
    "What is the unreleased product roadmap for 2027?",
    "What are individual employee salaries?",
    "What is the secret Stripe webhook signing key?",
    "What is the private pentest report URL?",
    "What is the hidden GraphQL admin endpoint password?",
    "What is the confidential acquisition target?",
    "What is the AWS root account password?",
    "What is the unpublished SEV-0 playbook?",
    "What are the unreleased pricing experiments?",
    "What is the private customer churn list?",
    "What is the undisclosed board meeting minutes?",
]

DENIED_QUERIES = [
    "Show me the compensation salary bands.",
    "What is in the sales playbook close rate?",
    "List quota commission tiers for enterprise reps.",
    "What restricted engineering API keys exist?",
    "Show internal Stripe production credentials.",
    "What is the restricted sales playbook strategy?",
    "Reveal confidential customer churn data.",
    "What restricted HR compensation tables exist?",
    "Show restricted quota commission formulas.",
    "What internal admin API master key is used?",
    "List restricted sales playbook tactics.",
    "What engineering secrets are in internal_api_keys?",
    "Show compensation policy restricted tables.",
    "What is the restricted enterprise discount floor?",
    "Reveal sales playbook restricted pricing guidance.",
]


if __name__ == "__main__":
    main()
