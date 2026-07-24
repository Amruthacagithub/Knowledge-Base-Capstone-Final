"""
Audit logging — records every search for compliance.
"""
import hashlib
from datetime import datetime, timezone
from backend.database import SessionLocal
from backend.models import AccessAuditLog


def query_fingerprint(query_text: str) -> str:
    """Return a stable query fingerprint without retaining query content."""
    return hashlib.sha256(query_text.encode("utf-8")).hexdigest()


def log_search(
    user_id: str,
    query_text: str,
    doc_ids: list[str],
    allowed: bool = True,
):
    """Log a search event to the audit log."""
    db = SessionLocal()
    try:
        entry = AccessAuditLog(
            user_id=user_id,
            query_text=f"sha256:{query_fingerprint(query_text)}",
            doc_ids=",".join(doc_ids),
            timestamp=datetime.now(timezone.utc),
            allowed=allowed,
        )
        db.add(entry)
        db.commit()
    finally:
        db.close()
