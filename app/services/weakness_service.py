from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import WeaknessRecord, Mistake, DSALog

SEVERITY_LEVELS = ["low", "medium", "high", "critical"]

class WeaknessService:
    @staticmethod
    def _calculate_severity(mistake_count: int, successful_revisions: int) -> str:
        """
        Evidence-based severity calculation.
        Increases progressively with mistakes, decreases only with sustained successful revisions.
        """
        if mistake_count >= 6:
            base_idx = 3 # Critical
        elif mistake_count >= 4:
            base_idx = 2 # High
        elif mistake_count >= 2:
            base_idx = 1 # Medium
        else:
            base_idx = 0 # Low

        # Sustained evidence reduction: every 3 successful revisions reduces severity index by 1
        reduction = successful_revisions // 3
        final_idx = max(0, base_idx - reduction)
        return SEVERITY_LEVELS[final_idx]

    @staticmethod
    async def record_mistake_for_topic(
        session: AsyncSession,
        topic: str,
        category: str = "DSA",
        description: str = "",
        severity: str = "medium"
    ) -> WeaknessRecord:
        """
        Records a mistake for a topic and updates/creates the persistent WeaknessRecord.
        """
        res = await session.execute(
            select(WeaknessRecord).where(
                and_(
                    WeaknessRecord.topic.ilike(topic),
                    WeaknessRecord.category.ilike(category)
                )
            )
        )
        record = res.scalar_one_or_none()
        
        now = datetime.now(timezone.utc)
        if not record:
            record = WeaknessRecord(
                topic=topic,
                category=category,
                mistake_count=1,
                successful_revisions_count=0,
                severity=severity,
                most_recent_mistake=now,
                resolved=False
            )
            session.add(record)
        else:
            record.mistake_count += 1
            record.most_recent_mistake = now
            record.resolved = False
            # Re-evaluate severity
            record.severity = WeaknessService._calculate_severity(
                record.mistake_count, record.successful_revisions_count
            )

        # Also create a Mistake entry for backward compatibility
        mistake_entry = Mistake(
            category=category,
            mistake_type=f"{topic} error",
            description=description or f"Mistake in {topic}",
            topic=topic,
            severity=record.severity,
            occurrences_count=record.mistake_count,
            resolved=False
        )
        session.add(mistake_entry)

        await session.commit()
        return record

    @staticmethod
    async def record_successful_revision(
        session: AsyncSession,
        topic: str,
        category: str = "DSA"
    ) -> Optional[WeaknessRecord]:
        """
        Evidence-based weakness improvement.
        Completing 1 revision increments count. Improvement requires sustained evidence (>=3 revisions).
        """
        res = await session.execute(
            select(WeaknessRecord).where(
                and_(
                    WeaknessRecord.topic.ilike(topic),
                    WeaknessRecord.category.ilike(category)
                )
            )
        )
        record = res.scalar_one_or_none()
        if record:
            record.successful_revisions_count += 1
            record.last_revision_at = datetime.now(timezone.utc)
            record.severity = WeaknessService._calculate_severity(
                record.mistake_count, record.successful_revisions_count
            )
            
            # Resolve only if sustained evidence reached (>= 5 successful revisions and severity low)
            if record.successful_revisions_count >= 5 and record.severity == "low":
                record.resolved = True

            await session.commit()
        return record

    @staticmethod
    async def get_weakness_radar_summary(session: AsyncSession) -> Dict[str, Any]:
        """
        Exposes top, unresolved, worsening, and improved weaknesses for controller and wall displays.
        """
        res = await session.execute(
            select(WeaknessRecord).order_by(WeaknessRecord.mistake_count.desc())
        )
        all_records = res.scalars().all()

        unresolved = [r for r in all_records if not r.resolved]
        top_weaknesses = unresolved[:5]

        now = datetime.now(timezone.utc)
        recent_threshold = now - timedelta(days=3)
        
        worsening = [
            r for r in unresolved 
            if r.most_recent_mistake and r.most_recent_mistake.tzinfo and r.most_recent_mistake >= recent_threshold
        ]

        improved = [
            r for r in all_records 
            if r.successful_revisions_count > 0 or r.resolved
        ]

        return {
            "top_weaknesses": [
                {
                    "id": r.id,
                    "topic": r.topic,
                    "category": r.category,
                    "mistake_count": r.mistake_count,
                    "severity": r.severity,
                    "successful_revisions": r.successful_revisions_count,
                    "resolved": r.resolved
                } for r in top_weaknesses
            ],
            "unresolved_count": len(unresolved),
            "worsening_count": len(worsening),
            "improved_count": len(improved),
            "all_unresolved": [
                {
                    "id": r.id,
                    "topic": r.topic,
                    "category": r.category,
                    "mistake_count": r.mistake_count,
                    "severity": r.severity,
                    "successful_revisions": r.successful_revisions_count,
                    "resolved": r.resolved
                } for r in unresolved
            ]
        }
