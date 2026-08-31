from datetime import datetime, date, timezone
from typing import Dict, Any, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    WeeklyReview, DSALog, Concept, SentinelAIMilestone, Task, 
    SpacedRevision, DayLog, WeaknessRecord
)
from app.services.roadmap_service import RoadmapService

class WeeklyReviewService:
    @staticmethod
    async def create_or_update_weekly_review(
        session: AsyncSession,
        week_number: int,
        year: int = 2026,
        q1: str = "",
        q2: str = "",
        q3: str = "",
        q4: str = ""
    ) -> WeeklyReview:
        """
        Generates and saves a structured Weekly Review database record.
        """
        period_key = f"{year}-W{week_number:02d}"

        sprint_status = await RoadmapService.get_sprint_status(session)
        
        # DSA stats
        dsa_solved = sprint_status["dsa"]["solved_independent"]
        dsa_target = 18

        # Concepts stats
        concepts_completed = sprint_status["concepts"]["mastered"]
        concepts_target = 4

        # SentinelAI stats
        sentinel_ver = sprint_status["sentinelai"]["active_version"]
        sentinel_status = f"{sprint_status['sentinelai']['percentage']}% Complete"

        # College stats
        college_res = await session.execute(
            select(Task).where(Task.category == "College")
        )
        college_tasks = college_res.scalars().all()
        college_total = len(college_tasks)
        college_completed = len([t for t in college_tasks if t.status == "completed"])

        # Revisions stats
        rev_res = await session.execute(select(SpacedRevision))
        all_revs = rev_res.scalars().all()
        revs_scheduled = len(all_revs)
        revs_completed = len([r for r in all_revs if r.completed])

        # Top Weakness
        weakness_res = await session.execute(
            select(WeaknessRecord).where(WeaknessRecord.resolved == False).order_by(WeaknessRecord.mistake_count.desc())
        )
        top_w = weakness_res.scalars().first()
        top_weakness_str = top_w.topic if top_w else "None"

        # Must Win Success Rate
        day_logs_res = await session.execute(select(DayLog))
        day_logs = day_logs_res.scalars().all()
        must_win_logs = [d for d in day_logs if d.must_win_result]
        achieved_mw = len([d for d in must_win_logs if d.must_win_result == "achieved"])
        mw_rate = round((achieved_mw / len(must_win_logs) * 100), 1) if must_win_logs else 100.0

        # Existing record check
        rev_res = await session.execute(
            select(WeeklyReview).where(WeeklyReview.period_key == period_key)
        )
        review_obj = rev_res.scalar_one_or_none()

        if not review_obj:
            review_obj = WeeklyReview(
                week_number=week_number,
                year=year,
                period_key=period_key,
                dsa_target=dsa_target,
                dsa_solved=dsa_solved,
                ml_dl_cv_target=concepts_target,
                ml_dl_cv_completed=concepts_completed,
                sentinelai_version=sentinel_ver,
                sentinelai_status=sentinel_status,
                college_tasks_total=college_total,
                college_tasks_completed=college_completed,
                top_weakness=top_weakness_str,
                revisions_scheduled=revs_scheduled,
                revisions_completed=revs_completed,
                must_win_success_rate=mw_rate,
                q1_missed_work_cause=q1,
                q2_biggest_difficulty=q2,
                q3_next_week_improvements=q3,
                q4_next_week_priority=q4
            )
            session.add(review_obj)
        else:
            review_obj.dsa_solved = dsa_solved
            review_obj.ml_dl_cv_completed = concepts_completed
            review_obj.sentinelai_version = sentinel_ver
            review_obj.sentinelai_status = sentinel_status
            review_obj.college_tasks_total = college_total
            review_obj.college_tasks_completed = college_completed
            review_obj.top_weakness = top_weakness_str
            review_obj.revisions_scheduled = revs_scheduled
            review_obj.revisions_completed = revs_completed
            review_obj.must_win_success_rate = mw_rate
            if q1: review_obj.q1_missed_work_cause = q1
            if q2: review_obj.q2_biggest_difficulty = q2
            if q3: review_obj.q3_next_week_improvements = q3
            if q4: review_obj.q4_next_week_priority = q4

        await session.commit()
        return review_obj
