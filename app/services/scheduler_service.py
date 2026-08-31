import asyncio
from datetime import datetime, date
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import SprintConfig, DayLog
from app.services.reporting_service import ReportingService
from app.services.backup_service import BackupService
from app.services.roadmap_service import RoadmapService

scheduler = AsyncIOScheduler()

async def midnight_transition_job():
    """Runs at midnight to transition calendar day, generate reports, and backup data."""
    async with AsyncSessionLocal() as session:
        today_str = date.today().isoformat()
        
        # 1. Close previous day log if open
        day_res = await session.execute(
            select(DayLog).where(DayLog.date == today_str)
        )
        day_log = day_res.scalar_one_or_none()
        
        if not day_log:
            sprint_status = await RoadmapService.get_sprint_status(session)
            day_log = DayLog(
                date=today_str,
                day_number=sprint_status["day_number"],
                status="closed"
            )
            session.add(day_log)
        else:
            day_log.status = "closed"
            
        await session.commit()
        
        # 2. Generate Daily Report automatically
        try:
            await ReportingService.generate_daily_report(session, target_date_str=today_str)
        except Exception as e:
            print(f"Error generating daily report: {e}")
            
        # 3. Create Daily SQLite Backup
        try:
            BackupService.create_daily_sqlite_backup()
        except Exception as e:
            print(f"Error creating daily backup: {e}")

async def weekly_report_job():
    """Runs weekly on Sunday to generate weekly report & full ZIP backup."""
    async with AsyncSessionLocal() as session:
        sprint_status = await RoadmapService.get_sprint_status(session)
        week_num = sprint_status["current_week"]
        
        try:
            await ReportingService.generate_weekly_report(session, week_number=week_num)
            BackupService.create_weekly_zip_backup(week_number=week_num)
        except Exception as e:
            print(f"Error in weekly report job: {e}")

async def monthly_report_job():
    """Runs monthly to generate monthly retrospective report."""
    async with AsyncSessionLocal() as session:
        sprint_status = await RoadmapService.get_sprint_status(session)
        try:
            await ReportingService.generate_monthly_report(session, month_number=sprint_status["current_month"])
        except Exception as e:
            print(f"Error in monthly report job: {e}")

def start_scheduler():
    """Starts the background scheduler."""
    if not scheduler.running:
        # Midnight Job
        scheduler.add_job(midnight_transition_job, 'cron', hour=0, minute=0)
        # Weekly Job (Sunday 23:55)
        scheduler.add_job(weekly_report_job, 'cron', day_of_week='sun', hour=23, minute=55)
        # Monthly Job (Last day of month 23:55)
        scheduler.add_job(monthly_report_job, 'cron', day='last', hour=23, minute=55)
        
        scheduler.start()
        print("StudyOS Background Scheduler Started.")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
