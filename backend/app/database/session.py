from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

db_url = settings.DATABASE_URL
connect_args = {}

try:
    engine = create_engine(db_url, pool_pre_ping=True)
    # Test connection driver load
    engine.connect()
except Exception as e:
    # Fallback to local SQLite DB for standalone companion / unit test mode
    db_url = "sqlite:///./memos_local.db"
    connect_args = {"check_same_thread": False}
    engine = create_engine(db_url, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

