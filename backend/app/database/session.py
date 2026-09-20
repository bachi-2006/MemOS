from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

import os

db_url = settings.DATABASE_URL
connect_args = {}

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30.0}

try:
    engine = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
    # Probe connection to verify DB accessibility; context manager ensures the
    # connection is returned to the pool immediately rather than leaking.
    from sqlalchemy import text as _text
    with engine.connect() as _probe:
        _probe.execute(_text("SELECT 1"))
except Exception as e:
    # Fallback to local SQLite DB in project root for standalone companion / unit test mode
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    db_file = os.path.join(PROJECT_ROOT, "memos_local.db")
    db_url = f"sqlite:///{db_file}"
    connect_args = {"check_same_thread": False, "timeout": 30.0}
    engine = create_engine(db_url, connect_args=connect_args)

# Enable WAL mode and busy timeout on SQLite to prevent "database is locked" errors
if db_url.startswith("sqlite"):
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        try:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()
        except Exception:
            pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

