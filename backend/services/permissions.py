"""
Permission resolver — builds Qdrant filters based on the user's roles.
"""
from qdrant_client.models import Filter, FieldCondition, MatchValue, MatchAny

from backend.services.auth import UserContext


def build_permission_filter(user_ctx: UserContext) -> Filter | None:
    """
    Build a Qdrant filter that enforces role-based access control.

    Logic:
    - Admin users see everything → return None (no filter).
    - Other users only see chunks where at least one of their roles
      is in the chunk's access_roles list.
    """
    if "Admin" in user_ctx.roles:
        return None  # Admin sees everything

    # Filter: access_roles must contain at least one of the user's roles
    return Filter(
        must=[
            FieldCondition(
                key="access_roles",
                match=MatchAny(any=user_ctx.roles),
            )
        ]
    )


def filter_bm25_results(results: list[dict], user_ctx: UserContext) -> list[dict]:
    """
    Post-filter BM25 results based on user permissions.

    Since Whoosh doesn't support role-based filtering natively,
    we filter results after retrieval.
    """
    if "Admin" in user_ctx.roles:
        return results  # Admin sees everything

    filtered = []
    for r in results:
        classification = r.get("classification", "public")
        department = r.get("department", "")

        if classification == "public":
            # Everyone can see public documents
            filtered.append(r)
        elif classification == "restricted":
            # Only users with the department role can see restricted docs
            from backend.services.embedder import department_to_role
            required_role = department_to_role(department)
            if required_role in user_ctx.roles:
                filtered.append(r)

    return filtered
