import asyncio
import os
import sys
from datetime import date, datetime, timedelta, timezone

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import _sessionmakers, set_current_env_mode
from app.db.init_db import init_db_for_mode
from app.db.models import SprintConfig, Task, DayLog, SpacedRevision, TimetableSlot
from app.services.daily_allocation_service import DailyAllocationService
from app.services.revision_service import SpacedRevisionService
from sqlalchemy import select

async def main():
    print("Initializing & activating 120-Day Sprint for REAL mode...")
    set_current_env_mode("REAL")
    
    # First, initialize base database tables and default timetable slots if not present
    await init_db_for_mode("REAL", force_recreate=False)

    sessionmaker = _sessionmakers["REAL"]
    async with sessionmaker() as session:
        # Activate Sprint
        cfg_res = await session.execute(select(SprintConfig))
        cfg = cfg_res.scalar_one_or_none()
        today_str = date.today().isoformat()
        
        if not cfg:
            cfg = SprintConfig(env_mode="REAL")
            session.add(cfg)

        start_dt = datetime.strptime(today_str, "%Y-%m-%d").date()
        end_dt = start_dt + timedelta(days=119)

        cfg.sprint_activated = True
        cfg.actual_start_date = today_str
        cfg.actual_end_date = end_dt.isoformat()
        cfg.activated_at = datetime.now(timezone.utc)
        await session.commit()
        print(f"[SUCCESS] Sprint Activated: {cfg.actual_start_date} to {cfg.actual_end_date}")

        # Materialize Today's Tasks
        created_tasks = await DailyAllocationService.ensure_today_tasks_exist(session, mode="REAL", target_date_str=today_str)
        print(f"[SUCCESS] Materialized {len(created_tasks)} tasks for today ({today_str}):")
        for t in created_tasks:
            print(f"  - [{t.category}] {t.title} ({t.estimated_minutes} mins)")

        # Verify Timetable Slots
        tt_res = await session.execute(select(TimetableSlot))
        tt_slots = tt_res.scalars().all()
        print(f"[SUCCESS] Timetable slots count: {len(tt_slots)}")

        # Verify Revisions
        rev_res = await session.execute(select(SpacedRevision))
        revisions = rev_res.scalars().all()
        print(f"[SUCCESS] Spaced Revisions count: {len(revisions)}")
        for r in revisions[:5]:
            print(f"  - [{r.domain}] {r.concept_name} (Scheduled: {r.scheduled_date})")

    print("\n[COMPLETE] REAL Mode Activation & Materialization Successful!")

if __name__ == "__main__":
    asyncio.run(main())
