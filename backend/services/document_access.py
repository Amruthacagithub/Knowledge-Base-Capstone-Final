"""
Document access helpers — RBAC for document list and full-file reads.
"""
from backend.models import Document
from backend.services.auth import UserContext
from backend.services.embedder import department_to_role


def user_can_access_document(doc: Document, user_ctx: UserContext) -> bool:
    """Return True if the user may read this document."""
    if "Admin" in user_ctx.roles:
        return True
    if doc.classification == "public":
        return True
    if doc.classification == "restricted":
        required = department_to_role(doc.department)
        return required in user_ctx.roles
    return False
