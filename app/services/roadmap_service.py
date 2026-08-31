from datetime import datetime, date, timedelta
from typing import Dict, Any, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import SprintConfig, RoadmapWeek, Task, DSALog, Concept, SentinelAIMilestone, CollegeEvent, Mistake
from app.db.session import get_current_env_mode

class RoadmapService:
    @staticmethod
    async def get_sprint_status(session: AsyncSession) -> Dict[str, Any]:
        """Calculates sprint metrics, pre-sprint vs active sprint state, and health status."""
        config_res = await session.execute(select(SprintConfig))
        config = config_res.scalar_one_or_none()
        
        env_mode = get_current_env_mode()
        sprint_activated = config.sprint_activated if config else False
        actual_start_str = config.actual_start_date if (config and config.actual_start_date) else None
        actual_end_str = config.actual_end_date if (config and config.actual_end_date) else None
        
        today = date.today()
        
        if not sprint_activated:
            # PRE-SPRINT STATE
            current_day = 0
            current_week = 0
            current_month = 0
            health_color = "INDIGO"
            health_label = "PRE-SPRINT (NOT STARTED)"
        else:
            # ACTIVE SPRINT STATE
            start_dt = datetime.strptime(actual_start_str, "%Y-%m-%d").date() if actual_start_str else today
            days_elapsed = (today - start_dt).days + 1
            current_day = max(1, min(days_elapsed, 120))
            current_week = max(1, min(((current_day - 1) // 7) + 1, 16))
            current_month = max(1, min(((current_week - 1) // 4) + 1, 4))
            
            # Tasks Completion Percentage for Health calculation
            weekly_tasks_res = await session.execute(select(Task))
            all_tasks = weekly_tasks_res.scalars().all()
            total_tasks = len(all_tasks)
            completed_tasks = len([t for t in all_tasks if t.status == "completed"])
            completion_pct = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 100.0
            
            if completion_pct >= 90.0:
                health_color = "GREEN"
                health_label = "ON TRACK"
            elif completion_pct >= 70.0:
                health_color = "YELLOW"
                health_label = "SLIGHTLY BEHIND"
            else:
                health_color = "RED"
                health_label = "AT RISK"
        
        # 1. DSA Metrics
        dsa_count_res = await session.execute(
            select(func.count(DSALog.id)).where(DSALog.independent_solve == True)
        )
        dsa_solved_independent = dsa_count_res.scalar() or 0
        
        dsa_total_res = await session.execute(select(func.count(DSALog.id)))
        dsa_total_attempts = dsa_total_res.scalar() or 0
        dsa_target = 270
        
        # 2. Concepts Metrics
        concepts_mastered_res = await session.execute(
            select(func.count(Concept.id)).where(Concept.status == "mastered")
        )
        concepts_mastered = concepts_mastered_res.scalar() or 0
        
        concepts_total_res = await session.execute(select(func.count(Concept.id)))
        concepts_total = concepts_total_res.scalar() or 1
        
        # 3. SentinelAI Milestones
        milestones_done_res = await session.execute(
            select(func.count(SentinelAIMilestone.id)).where(SentinelAIMilestone.status == "completed")
        )
        milestones_completed = milestones_done_res.scalar() or 0
        
        milestones_total_res = await session.execute(select(func.count(SentinelAIMilestone.id)))
        milestones_total = milestones_total_res.scalar() or 14
        
        active_milestone_res = await session.execute(
            select(SentinelAIMilestone).where(SentinelAIMilestone.status != "completed").order_by(SentinelAIMilestone.target_week)
        )
        active_milestone = active_milestone_res.scalars().first()
        active_sentinel_version = active_milestone.version if active_milestone else "V1.4 Complete"
        
        # 4. Tasks Summary
        all_tasks_res = await session.execute(select(Task))
        tasks_list = all_tasks_res.scalars().all()
        completed_count = len([t for t in tasks_list if t.status == "completed"])
        total_count = len(tasks_list)
        completion_pct = round((completed_count / total_count * 100), 1) if total_count > 0 else 100.0
        
        # 5. Current Roadmap Week Data
        week_num_query = max(1, current_week)
        week_res = await session.execute(
            select(RoadmapWeek).where(RoadmapWeek.week_number == week_num_query)
        )
        current_week_data = week_res.scalar_one_or_none()
        
        # 6. Unresolved Mistakes
        unresolved_mistakes_res = await session.execute(
            select(Mistake).where(Mistake.resolved == False).order_by(Mistake.occurrences_count.desc())
        )
        unresolved_mistakes = unresolved_mistakes_res.scalars().all()
        
        # 7. College Events
        events_res = await session.execute(
            select(CollegeEvent).where(CollegeEvent.status == "upcoming").order_by(CollegeEvent.due_date)
        )
        upcoming_events = events_res.scalars().all()

        # 8. Daily Allocation Layer
        from app.services.daily_allocation_service import DailyAllocationService
        daily_allocation = await DailyAllocationService.get_daily_allocation(session, mode=env_mode)

        return {
            "env_mode": env_mode,
            "sprint_activated": sprint_activated,
            "actual_start_date": actual_start_str,
            "actual_end_date": actual_end_str,
            "current_date": today.isoformat(),
            "day_number": current_day,
            "total_days": 120,
            "current_week": current_week,
            "current_month": current_month,
            "current_mode": config.current_mode if config else "NORMAL",
            "exam_mode_active": config.exam_mode_active if config else False,
            "wall_sleep_mode": config.wall_sleep_mode if config else False,
            "daily_allocation": daily_allocation,
            "dsa": {
                "solved_independent": dsa_solved_independent,
                "total_attempts": dsa_total_attempts,
                "target": dsa_target,
                "percentage": round((dsa_solved_independent / dsa_target) * 100, 1)
            },
            "concepts": {
                "mastered": concepts_mastered,
                "total": concepts_total,
                "percentage": round((concepts_mastered / concepts_total) * 100, 1)
            },
            "sentinelai": {
                "active_version": active_sentinel_version,
                "milestones_completed": milestones_completed,
                "milestones_total": milestones_total,
                "percentage": round((milestones_completed / milestones_total) * 100, 1)
            },
            "tasks_summary": {
                "completed": completed_count,
                "total": total_count,
                "completion_percentage": completion_pct
            },
            "health": {
                "status": health_color,
                "label": health_label
            },
            "current_week_info": {
                "title": current_week_data.title if current_week_data else f"Week {week_num_query}",
                "focus_dsa": current_week_data.focus_dsa if current_week_data else "",
                "focus_ml_dl": current_week_data.focus_ml_dl if current_week_data else "",
                "focus_sentinelai": current_week_data.focus_sentinelai if current_week_data else ""
            },
            "unresolved_mistakes": [
                {
                    "id": m.id,
                    "type": m.mistake_type,
                    "description": m.description,
                    "count": m.occurrences_count,
                    "severity": m.severity
                } for m in unresolved_mistakes[:5]
            ],
            "upcoming_events": [
                {
                    "id": e.id,
                    "title": e.title,
                    "subject": e.subject_name,
                    "due_date": e.due_date,
                    "priority": e.priority
                } for e in upcoming_events[:5]
            ]
        }
