import math
from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Task, SpacedRevision, SprintConfig, DayLog

# Maximum daily recovery workload cap (in hours)
NORMAL_RECOVERY_CAP_HOURS = 1.0
EXAM_RECOVERY_CAP_HOURS = 0.25

class RecoveryService:
    @staticmethod
    async def get_recovery_plan(
        session: AsyncSession,
        today_str: str = None
    ) -> Dict[str, Any]:
        """
        Calculates a controlled, realistic Recovery Plan for missed work and overdue revisions.
        CRITICAL: Capped and realistic. Does NOT modify the master roadmap or remove targets.
        Reduces recovery workload during Exam Mode.
        """
        if not today_str:
            today_str = date.today().isoformat()

        # Check Exam Mode & Sprint Config
        config_res = await session.execute(select(SprintConfig))
        config = config_res.scalar_one_or_none()
        exam_mode_active = config.exam_mode_active if config else False

        # 1. Fetch overdue tasks
        overdue_tasks_res = await session.execute(
            select(Task).where(
                and_(
                    Task.due_date < today_str,
                    Task.status != "completed"
                )
            )
        )
        overdue_tasks = overdue_tasks_res.scalars().all()

        # 2. Fetch overdue revisions
        overdue_revs_res = await session.execute(
            select(SpacedRevision).where(
                and_(
                    SpacedRevision.scheduled_date < today_str,
                    SpacedRevision.completed == False
                )
            )
        )
        overdue_revisions = overdue_revs_res.scalars().all()

        # Calculate total estimated missed hours (tasks in mins + revisions at ~20m each)
        tasks_missed_mins = sum(t.estimated_minutes for t in overdue_tasks)
        revs_missed_mins = len(overdue_revisions) * 20
        total_missed_hours = round((tasks_missed_mins + revs_missed_mins) / 60.0, 1)

        # Workload Cap Logic
        recovery_cap = EXAM_RECOVERY_CAP_HOURS if exam_mode_active else NORMAL_RECOVERY_CAP_HOURS
        today_recovery_workload = min(total_missed_hours, recovery_cap)

        # Normal daily workload baseline
        day_log_res = await session.execute(
            select(DayLog).where(DayLog.date == today_str)
        )
        day_log = day_log_res.scalar_one_or_none()
        normal_workload_hours = day_log.available_hours if day_log else 4.0

        total_workload_hours = round(normal_workload_hours + today_recovery_workload, 1)

        # Estimated days required to clear remaining backlog at capped rate
        remaining_backlog_hours = max(0.0, total_missed_hours - today_recovery_workload)
        days_to_clear = math.ceil(remaining_backlog_hours / recovery_cap) if recovery_cap > 0 else 0

        # Build missed items summary
        missed_items_summary = []
        for t in overdue_tasks[:4]:
            missed_items_summary.append({
                "type": "task",
                "id": t.id,
                "title": t.title,
                "category": t.category,
                "due_date": t.due_date
            })
        for r in overdue_revisions[:4]:
            missed_items_summary.append({
                "type": "revision",
                "id": r.id,
                "title": f"Revision #{r.revision_number}: {r.concept_name}",
                "category": r.domain,
                "scheduled_date": r.scheduled_date
            })

        return {
            "recovery_mode_active": len(overdue_tasks) > 0 or len(overdue_revisions) > 0,
            "exam_mode_active": exam_mode_active,
            "overdue_tasks_count": len(overdue_tasks),
            "overdue_revisions_count": len(overdue_revisions),
            "total_missed_hours": total_missed_hours,
            "normal_workload_hours": normal_workload_hours,
            "recovery_workload_hours": today_recovery_workload,
            "total_workload_hours": total_workload_hours,
            "recovery_cap_hours": recovery_cap,
            "remaining_backlog_hours": remaining_backlog_hours,
            "days_to_clear_backlog": days_to_clear,
            "missed_items": missed_items_summary,
            "notice": "Recovery workload is strictly capped. Master roadmap targets remain authoritative and unchanged."
        }
