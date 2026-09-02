"""
Sensitive-topic gate — block retrieval when a query targets restricted domains
the user cannot access, even if public documents mention related keywords.
"""
import re

from backend.services.auth import UserContext

_COMPENSATION_QUERY = re.compile(
    r"\b("
    r"salary|salaries|compensation|pay\s*band|salary\s*band|salary\s*range|"
    r"executive\s+salary|bonus\s+structure|equity\s+program|salary\s+review|"
    r"promotion\s+criteria|annual\s+bonus"
    r")\b",
    re.IGNORECASE,
)

_SALES_COMPENSATION_QUERY = re.compile(
    r"\b("
    r"commission|quota|sales\s+comp|commission\s+structure|commission\s+rate"
    r")\b",
    re.IGNORECASE,
)


def user_can_access_hr_compensation(user_ctx: UserContext) -> bool:
    return "Admin" in user_ctx.roles or "HR" in user_ctx.roles


def user_can_access_sales_compensation(user_ctx: UserContext) -> bool:
    return "Admin" in user_ctx.roles or "Sales" in user_ctx.roles


def is_hr_compensation_query(query: str) -> bool:
    return bool(_COMPENSATION_QUERY.search(query))


def is_sales_compensation_query(query: str) -> bool:
    return bool(_SALES_COMPENSATION_QUERY.search(query))


def blocks_sensitive_search(user_ctx: UserContext, query: str) -> bool:
    """
    Return True when the query targets a sensitive domain the user may not access.

  Engineers asking about salary bands must receive zero authorized results, not
  tangentially related public HR excerpts.
    """
    if is_hr_compensation_query(query) and not user_can_access_hr_compensation(user_ctx):
        return True
    if is_sales_compensation_query(query) and not user_can_access_sales_compensation(user_ctx):
        return True
    return False
