"""
Database connection and session management using SQLAlchemy.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import DATABASE_URL

_engine_options = {"echo": False}
if DATABASE_URL.startswith("sqlite:"):
    _engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_options)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    """Yield a database session, auto-close on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
