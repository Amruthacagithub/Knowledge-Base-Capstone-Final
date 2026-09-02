"""
EKIP — Enterprise Knowledge Intelligence Platform

FastAPI application entry point.
"""
import json
import logging
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from backend.config import ALLOWED_HOSTS, CORS_ORIGINS, VECTOR_SEARCH_ENABLED
from backend.routers.auth_router import router as auth_router
from backend.routers.search_router import router as search_router
from backend.routers.documents_router import router as documents_router
from backend.routers.graph_router import router as graph_router
from backend.routers.versions_router import router as versions_router

app = FastAPI(
    title="Knowledge Base",
    description="Internal document search with AI-powered answers and role-based access.",
    version="0.2.0",
)
logger = logging.getLogger("trust_rag.access")

_allowed_hosts = [host.strip() for host in ALLOWED_HOSTS.split(",") if host.strip()]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)

# CORS — localhost in dev; set CORS_ORIGINS in production (include your Vercel URL)
_cors_origins = [o.strip() for o in CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def secure_observable_responses(request, call_next):
    request_id = request.headers.get("X-Request-ID", "").strip()
    if len(request_id) > 100 or not request_id:
        request_id = str(uuid.uuid4())
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - started) * 1000)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    logger.info(
        json.dumps(
            {
                "event": "http_request",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
            separators=(",", ":"),
        )
    )
    return response

# Include routers
app.include_router(auth_router)
app.include_router(search_router)
app.include_router(documents_router)
app.include_router(graph_router)
app.include_router(versions_router)


def _check_postgres() -> bool:
    try:
        from backend.database import SessionLocal
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.close()
        return True
    except Exception:
        return False


def _check_qdrant() -> bool:
    try:
        from backend.services.embedder import get_qdrant_client
        from backend.config import QDRANT_COLLECTION
        client = get_qdrant_client()
        client.get_collection(QDRANT_COLLECTION)
        return True
    except Exception:
        return False


@app.get("/api/health")
def health_check():
    """Health check with dependency status."""
    pg_ok = _check_postgres()
    if VECTOR_SEARCH_ENABLED:
        qd_ok = _check_qdrant()
        qdrant_status = "up" if qd_ok else "down"
    else:
        qd_ok = True
        qdrant_status = "disabled"
    status = "ok" if pg_ok and qd_ok else "degraded"
    return {
        "status": status,
        "service": "knowledge-base",
        "components": {
            "postgres": "up" if pg_ok else "down",
            "qdrant": qdrant_status,
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_excludes=["frontend/node_modules/*", "frontend/dist/*", "indexdir/*"],
    )
