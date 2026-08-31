from datetime import datetime, date, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import SpacedRevision, Concept, DSALog

# Standard Spaced Revision Intervals (in days)
REVISION_INTERVALS = [1, 3, 7, 14, 30]

class SpacedRevisionService:
    @staticmethod
    async def create_schedule_for_concept(
        session: AsyncSession,
        concept_name: str,
        domain: str = "ML",
        start_date_str: Optional[str] = None
    ) -> List[SpacedRevision]:
        """
        Creates 5 spaced revision schedule entries (+1d, +3d, +7d, +14d, +30d) for a concept.
        Prevents creating duplicate schedules if entries already exist.
        """
        if not start_date_str:
            start_date_str = date.today().isoformat()
            
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        created_items = []
        
        for rev_num, days_offset in enumerate(REVISION_INTERVALS, start=1):
            target_date = (start_dt + timedelta(days=days_offset)).isoformat()
            
            # Check for existing schedule to prevent duplicates
            existing = await session.execute(
                select(SpacedRevision).where(
                    and_(
                        SpacedRevision.concept_name == concept_name,
                        SpacedRevision.revision_number == rev_num
                    )
                )
            )
            if existing.scalar_one_or_none() is None:
                rev_entry = SpacedRevision(
                    concept_name=concept_name,
                    domain=domain,
                    original_date=start_date_str,
                    revision_number=rev_num,
                    scheduled_date=target_date,
                    completed=False,
                    overdue=(target_date < date.today().isoformat())
                )
                session.add(rev_entry)
                created_items.append(rev_entry)
                
        await session.commit()
        return created_items

    @staticmethod
    async def get_todays_revisions(session: AsyncSession, today_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Returns today's due revisions and overdue revisions queue.
        Updates overdue flags dynamically for missed revisions.
        """
        if not today_str:
            today_str = date.today().isoformat()

        # Update overdue status for uncompleted past revisions
        all_uncompleted = await session.execute(
            select(SpacedRevision).where(SpacedRevision.completed == False)
        )
        for rev in all_uncompleted.scalars().all():
            if rev.scheduled_date < today_str:
                rev.overdue = True

        await session.commit()

        # Fetch today's scheduled revisions
        today_res = await session.execute(
            select(SpacedRevision).where(
                and_(
                    SpacedRevision.scheduled_date == today_str,
                    SpacedRevision.completed == False
                )
            ).order_by(SpacedRevision.revision_number)
        )
        today_revisions = today_res.scalars().all()

        # Fetch overdue revisions queue
        overdue_res = await session.execute(
            select(SpacedRevision).where(
                and_(
                    SpacedRevision.scheduled_date < today_str,
                    SpacedRevision.completed == False
                )
            ).order_by(SpacedRevision.scheduled_date)
        )
        overdue_revisions = overdue_res.scalars().all()

        # Fetch recently completed revisions
        completed_res = await session.execute(
            select(SpacedRevision).where(SpacedRevision.completed == True).order_by(SpacedRevision.completed_at.desc())
        )
        completed_revisions = completed_res.scalars().all()

        return {
            "today": [
                {
                    "id": r.id,
                    "concept_name": r.concept_name,
                    "domain": r.domain,
                    "revision_number": r.revision_number,
                    "scheduled_date": r.scheduled_date,
                    "completed": r.completed,
                    "overdue": r.overdue
                } for r in today_revisions
            ],
            "overdue": [
                {
                    "id": r.id,
                    "concept_name": r.concept_name,
                    "domain": r.domain,
                    "revision_number": r.revision_number,
                    "scheduled_date": r.scheduled_date,
                    "days_overdue": (datetime.strptime(today_str, "%Y-%m-%d").date() - datetime.strptime(r.scheduled_date, "%Y-%m-%d").date()).days
                } for r in overdue_revisions
            ],
            "completed_count": len(completed_revisions),
            "today_count": len(today_revisions),
            "overdue_count": len(overdue_revisions)
        }

    @staticmethod
    async def complete_revision(
        session: AsyncSession,
        revision_id: int,
        confidence_rating: str = "medium"
    ) -> Optional[SpacedRevision]:
        """
        Marks a scheduled revision as completed with optional confidence rating.
        Does NOT swallow or silently drop missed revisions.
        """
        res = await session.execute(
            select(SpacedRevision).where(SpacedRevision.id == revision_id)
        )
        rev = res.scalar_one_or_none()
        if rev:
            rev.completed = True
            rev.completed_at = datetime.now(timezone.utc)
            rev.overdue = False
            rev.confidence_rating = confidence_rating
            await session.commit()
        return rev
