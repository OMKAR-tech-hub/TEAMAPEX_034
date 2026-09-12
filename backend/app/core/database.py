from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import BACKEND_DIR, settings


def _database_url() -> str:
    """Anchor relative SQLite databases to backend/ for every start command."""
    url = settings.DATABASE_URL
    relative_sqlite_prefix = "sqlite:///./"
    if url.startswith(relative_sqlite_prefix):
        path = (BACKEND_DIR / url.removeprefix(relative_sqlite_prefix)).resolve().as_posix()
        return f"sqlite:///{path}"
    return url


DATABASE_URL = _database_url()
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
