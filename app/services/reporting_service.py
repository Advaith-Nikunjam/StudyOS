from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_current_env_mode
from app.db.models import Task, DSALog, Mistake, Concept, SentinelAIMilestone, DayLog, ReportLog, WeeklyReview
from app.services.roadmap_service import RoadmapService
from app.services.revision_service import SpacedRevisionService
from app.services.weakness_service import WeaknessService
from app.services.recovery_service import RecoveryService

class ReportingService:
    @staticmethod
    def _get_reports_base_dir() -> Path:
        env = get_current_env_mode()
        if env == "TEST":
            return settings.TEST_REPORTS_DIR
        elif env == "DEMO":
            return settings.DEMO_REPORTS_DIR
        return settings.REPORTS_DIR

    @staticmethod
    async def generate_daily_report(session: AsyncSession, target_date_str: str = None) -> str:
        """Generates plain Markdown daily study report."""
        if not target_date_str:
            target_date_str = date.today().isoformat()
            
        dt = datetime.strptime(target_date_str, "%Y-%m-%d")
        year_str = dt.strftime("%Y")
        month_str = dt.strftime("%m")
        
        base_dir = ReportingService._get_reports_base_dir()
        target_dir = base_dir / "daily" / year_str / month_str
        target_dir.mkdir(parents=True, exist_ok=True)
        report_path = target_dir / f"{target_date_str}_daily_report.md"
        
        sprint_status = await RoadmapService.get_sprint_status(session)
        
        day_log_res = await session.execute(
            select(DayLog).where(DayLog.date == target_date_str)
        )
        day_log = day_log_res.scalar_one_or_none()
        
        tasks_res = await session.execute(
            select(Task).where(Task.due_date == target_date_str)
        )
        tasks_today = tasks_res.scalars().all()
        completed_tasks = [t for t in tasks_today if t.status == "completed"]
        
        dsa_today_res = await session.execute(select(DSALog))
        dsa_all = dsa_today_res.scalars().all()
        dsa_today = [d for d in dsa_all if d.created_at and d.created_at.strftime("%Y-%m-%d") == target_date_str]
        
        # New Feature Data
        revisions_data = await SpacedRevisionService.get_todays_revisions(session, today_str=target_date_str)
        weakness_data = await WeaknessService.get_weakness_radar_summary(session)
        recovery_data = await RecoveryService.get_recovery_plan(session, today_str=target_date_str)

        must_win_text = day_log.must_win_text if (day_log and day_log.must_win_text) else "Maintain 100% roadmap execution."
        must_win_result = day_log.must_win_result.upper() if (day_log and day_log.must_win_result) else "PENDING"

        md_content = f"""# Daily Study Report ({sprint_status['env_mode']} MODE)

**Date**: {target_date_str}  
**Day**: {'Day ' + str(sprint_status['day_number']) + ' of 120' if sprint_status['sprint_activated'] else 'PRE-SPRINT (NOT STARTED)'}  
**Week**: Week {sprint_status['current_week']} | **Month**: Month {sprint_status['current_month']}  
**Sprint Mode**: {sprint_status['current_mode']}  

---

## Today's Must Win
- **Outcome**: {must_win_text}
- **Status**: `{must_win_result}`

---

## Completed Tasks
"""
        if completed_tasks:
            for t in completed_tasks:
                md_content += f"- [{t.category}] **{t.title}** ({t.estimated_minutes} min)\n"
        else:
            md_content += "_No tasks marked completed for today._\n"
            
        md_content += f"""
## Quantitative Progress & Spaced Revisions
- **DSA Problems Solved Today**: {len(dsa_today)} (Total Solved: {sprint_status['dsa']['solved_independent']} / {sprint_status['dsa']['target']})
- **Focused Hours**: {day_log.focused_hours if day_log else 0.0} hrs / {day_log.available_hours if day_log else 4.0} hrs target
- **Revisions Due Today**: {revisions_data['today_count']} | **Overdue Revisions**: {revisions_data['overdue_count']}
- **SentinelAI Milestone**: {sprint_status['sentinelai']['active_version']} ({sprint_status['sentinelai']['percentage']}% complete)
- **Overall Roadmap Execution**: {sprint_status['tasks_summary']['completion_percentage']}%

## Weakness Radar Snapshot
"""
        if weakness_data["top_weaknesses"]:
            for w in weakness_data["top_weaknesses"]:
                md_content += f"- **[{w['category']}] {w['topic']}**: {w['mistake_count']} mistakes (Severity: {w['severity'].upper()})\n"
        else:
            md_content += "_No active top weaknesses recorded._\n"

        md_content += f"""
## Recovery Mode Status
- **Recovery Active**: {recovery_data['recovery_mode_active']}
- **Missed Hours**: {recovery_data['total_missed_hours']} hrs | **Today's Recovery Workload**: {recovery_data['recovery_workload_hours']} hrs (Cap: {recovery_data['recovery_cap_hours']} hrs)
- **Total Workload Today**: {recovery_data['total_workload_hours']} hrs

## Mistakes & Blockers
"""
        if day_log and day_log.mistakes_noted:
            md_content += f"{day_log.mistakes_noted}\n"
        elif sprint_status['unresolved_mistakes']:
            for m in sprint_status['unresolved_mistakes']:
                md_content += f"- [{m['type'].upper()}] {m['description']} (Occurred {m['count']}x)\n"
        else:
            md_content += "_No critical mistakes recorded today._\n"

        md_content += f"""
## What I Learned
{day_log.what_learned if day_log and day_log.what_learned else '_Consolidated study notes logged in repository notes._'}

## Tomorrow's Top Priorities
"""
        planned_tomorrow = [t for t in tasks_today if t.status == "planned"]
        if planned_tomorrow:
            for t in planned_tomorrow[:3]:
                md_content += f"1. [{t.category}] {t.title}\n"
        else:
            md_content += "1. Continue 16-week DSA & ML/DL/CV roadmap targets\n"

        md_content += f"""
---

## AI Assessment
**Status**: `{sprint_status['health']['status']}` ({sprint_status['health']['label']})  
**Evaluation**: Progress is adhering to sprint parameters. Maintain focus on independent DSA problem solving and SentinelAI baseline milestones.
"""

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        rep_log = ReportLog(
            report_type="daily",
            period_key=target_date_str,
            file_path=str(report_path)
        )
        session.add(rep_log)
        await session.commit()

        return str(report_path)

    @staticmethod
    async def generate_weekly_report(session: AsyncSession, week_number: int = None) -> str:
        """Generates plain Markdown weekly report."""
        sprint_status = await RoadmapService.get_sprint_status(session)
        if not week_number:
            week_number = max(1, sprint_status['current_week'])

        year_str = datetime.now().strftime("%Y")
        base_dir = ReportingService._get_reports_base_dir()
        target_dir = base_dir / "weekly" / year_str
        target_dir.mkdir(parents=True, exist_ok=True)
        report_path = target_dir / f"week_{week_number:02d}_report.md"

        weakness_data = await WeaknessService.get_weakness_radar_summary(session)
        recovery_data = await RecoveryService.get_recovery_plan(session)
        revisions_data = await SpacedRevisionService.get_todays_revisions(session)

        # Weekly Review Record
        period_key = f"{year_str}-W{week_number:02d}"
        w_res = await session.execute(select(WeeklyReview).where(WeeklyReview.period_key == period_key))
        review_obj = w_res.scalar_one_or_none()

        md_content = f"""# Weekly Study Report - Week {week_number:02d} ({sprint_status['env_mode']} MODE)

**Sprint Phase**: Month {sprint_status['current_month']} | **Mode**: {sprint_status['current_mode']}  
**Generated At**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  

---

## Executive Summary Table

| Metric Area | Target | Actual / Status | Health Verdict |
| :--- | :---: | :---: | :---: |
| **DSA Problems** | 18 / week | {sprint_status['dsa']['solved_independent']} Total | {sprint_status['health']['label']} |
| **ML / DL / CV Concepts** | Core Roadmap | {sprint_status['concepts']['mastered']} / {sprint_status['concepts']['total']} Mastered | On Track |
| **SentinelAI Milestone** | {sprint_status['sentinelai']['active_version']} | {sprint_status['sentinelai']['percentage']}% Complete | On Track |
| **Spaced Revisions** | Active Queue | {revisions_data['completed_count']} Completed | On Track |
| **Must Win Success Rate** | 100% | {review_obj.must_win_success_rate if review_obj else 100.0}% | On Track |
| **College Obligations** | 100% | Integrated | {sprint_status['current_mode']} |

---

## Focus Topics & Milestones
- **DSA Target**: {sprint_status['current_week_info']['focus_dsa']}
- **ML/DL/CV Focus**: {sprint_status['current_week_info']['focus_ml_dl']}
- **SentinelAI Objective**: {sprint_status['current_week_info']['focus_sentinelai']}

## Weakness Radar Summary
"""
        if weakness_data["top_weaknesses"]:
            for w in weakness_data["top_weaknesses"]:
                md_content += f"- **[{w['category']}] {w['topic']}**: {w['mistake_count']} mistakes (Severity: {w['severity'].upper()})\n"
        else:
            md_content += "_No active weaknesses recorded._\n"

        md_content += f"""
## Weekly Review Reflections
- **What caused missed work?**: {review_obj.q1_missed_work_cause if (review_obj and review_obj.q1_missed_work_cause) else 'N/A'}
- **Biggest difficulty**: {review_obj.q2_biggest_difficulty if (review_obj and review_obj.q2_biggest_difficulty) else 'N/A'}
- **Next week improvements**: {review_obj.q3_next_week_improvements if (review_obj and review_obj.q3_next_week_improvements) else 'N/A'}
- **#1 Priority Next Week**: {review_obj.q4_next_week_priority if (review_obj and review_obj.q4_next_week_priority) else 'N/A'}

---
## Roadmap Health Assessment
**Verdict**: `{sprint_status['health']['status']}`  
*The 16-week master roadmap remains authoritative. Sprint integrity is preserved.*
"""

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        rep_log = ReportLog(
            report_type="weekly",
            period_key=f"week_{week_number:02d}",
            file_path=str(report_path)
        )
        session.add(rep_log)
        await session.commit()

        return str(report_path)

    @staticmethod
    async def generate_monthly_report(session: AsyncSession, month_number: int = None) -> str:
        """Generates plain Markdown monthly report."""
        sprint_status = await RoadmapService.get_sprint_status(session)
        if not month_number:
            month_number = max(1, sprint_status['current_month'])

        year_str = datetime.now().strftime("%Y")
        month_key = f"{year_str}-{month_number:02d}"
        base_dir = ReportingService._get_reports_base_dir()
        target_dir = base_dir / "monthly" / year_str
        target_dir.mkdir(parents=True, exist_ok=True)
        report_path = target_dir / f"{month_key}_monthly_report.md"

        weakness_data = await WeaknessService.get_weakness_radar_summary(session)
        revisions_data = await SpacedRevisionService.get_todays_revisions(session)

        md_content = f"""# Monthly Retrospective Report - Month {month_number} ({sprint_status['env_mode']} MODE)

**Generated At**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  

---

## Monthly Sprint Overview
- **DSA Target Completed**: {sprint_status['dsa']['solved_independent']} Problems Solved
- **ML/DL/CV Concepts Mastered**: {sprint_status['concepts']['mastered']}
- **SentinelAI Version Completed**: {sprint_status['sentinelai']['active_version']}
- **Spaced Revisions Completed**: {revisions_data['completed_count']}
- **Unresolved Weaknesses**: {weakness_data['unresolved_count']}
- **Overall Schedule Adherence**: {sprint_status['tasks_summary']['completion_percentage']}%

---

## Final Monthly Verdict
**Verdict**: `{sprint_status['health']['status']}` ({sprint_status['health']['label']})  
*Report permanently archived on local filesystem.*
"""

        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        rep_log = ReportLog(
            report_type="monthly",
            period_key=month_key,
            file_path=str(report_path)
        )
        session.add(rep_log)
        await session.commit()

        return str(report_path)
