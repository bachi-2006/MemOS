from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.models import User
from app.services.importance_service import importance_engine
from app.services.lifecycle_service import lifecycle_engine

scheduler = AsyncIOScheduler()

async def run_nightly_memory_lifecycle_tasks():
    """Phase 14: Nightly APScheduler Job for Compression, Importance Update, Forgetting & Cleanup"""
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            # 1. Recalculate Memory Importance Scores
            importance_engine.update_all_importance_scores(db, user.id)
            # 2. Memory Compression
            compressed = await lifecycle_engine.compress_old_memories(db, user.id)
            # 3. Adaptive Forgetting
            forgotten = lifecycle_engine.adaptive_forgetting(db, user.id)
            print(f"Scheduled Job Complete for User {user.id}: Compressed={compressed}, Forgotten={forgotten}")
    except Exception as e:
        print(f"Scheduler Job Exception: {e}")
    finally:
        db.close()

def start_scheduler():
    # Schedule job every day at midnight (or configured interval)
    scheduler.add_job(run_nightly_memory_lifecycle_tasks, 'cron', hour=0, minute=0)
    scheduler.start()
