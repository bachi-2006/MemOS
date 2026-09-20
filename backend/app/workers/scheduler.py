import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from app.database.session import SessionLocal
from app.models.models import User, AnalysisJob
from app.services.analysis_service import analysis_service
from app.services.importance_service import importance_engine
from app.services.lifecycle_service import lifecycle_engine

scheduler = AsyncIOScheduler()


def enqueue_analysis_job(user_id: str, chat_id: str) -> None:
    db = SessionLocal()
    try:
        pending = db.query(AnalysisJob).filter(
            AnalysisJob.user_id == user_id,
            AnalysisJob.chat_id == chat_id,
            AnalysisJob.status.in_(["pending", "processing"]),
        ).first()
        if not pending:
            db.add(AnalysisJob(user_id=user_id, chat_id=chat_id))
            db.commit()
    finally:
        db.close()


async def process_analysis_jobs() -> None:
    db = SessionLocal()
    try:
        jobs = db.query(AnalysisJob).filter(
            AnalysisJob.status == "pending",
        ).order_by(AnalysisJob.created_at.asc()).limit(10).all()
        for job in jobs:
            job.status = "processing"
            job.attempts += 1
            db.commit()
            try:
                await analysis_service.analyze_chat(
                    db=db, user_id=job.user_id, chat_id=job.chat_id
                )
                job.status = "completed"
                job.error = None
            except Exception as exc:
                job.status = "failed" if job.attempts >= 3 else "pending"
                job.error = str(exc)[:1000]
            job.updated_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()

async def run_nightly_memory_lifecycle_tasks():
    """Phase 14: Periodic APScheduler Job for Compression, Importance Update, Forgetting & Cleanup.
    Interval is configured via LIFECYCLE_INTERVAL_HOURS (default: 24h).
    """
    print("[Scheduler] Memory lifecycle job starting...")
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            # 1. Recalculate Memory Importance Scores (pin bonus now preserved — Step 0.2)
            importance_engine.update_all_importance_scores(db, user.id)
            # 2. Memory Compression (guards against empty LLM summary — Step 1.3)
            compressed = await lifecycle_engine.compress_old_memories(db, user.id)
            # 3. Adaptive Forgetting
            forgotten = lifecycle_engine.adaptive_forgetting(db, user.id)
            print(f"[Scheduler] User {user.id[:8]}...: Compressed={compressed}, Forgotten={forgotten}")
    except Exception as e:
        print(f"[Scheduler] Job Exception: {e}")
    finally:
        db.close()
    print("[Scheduler] Memory lifecycle job complete.")

def start_scheduler():
    """Start the APScheduler with a configurable interval."""
    interval_hours = int(os.environ.get("LIFECYCLE_INTERVAL_HOURS", "24"))
    scheduler.add_job(
        run_nightly_memory_lifecycle_tasks,
        "interval",
        hours=interval_hours,
        id="memory_lifecycle",
        replace_existing=True
    )
    scheduler.add_job(
        process_analysis_jobs,
        "interval",
        minutes=1,
        id="analysis_jobs",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    print(f"[Scheduler] Memory lifecycle job scheduled every {interval_hours}h.")
