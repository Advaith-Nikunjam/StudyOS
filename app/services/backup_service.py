import os
import shutil
import json
import csv
import zipfile
from datetime import datetime, date
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.models import Task, DSALog, Mistake, Concept, SentinelAIMilestone, CollegeEvent, DayLog

from app.db.session import get_current_env_mode

class BackupService:
    @staticmethod
    def create_daily_sqlite_backup() -> str:
        """Copies active SQLite database file to data/backups/(daily|test|demo)/."""
        today_str = date.today().isoformat()
        env = get_current_env_mode()
        
        if env == "TEST":
            src_path = settings.TEST_DATABASE_PATH
            dest_dir = settings.TEST_BACKUPS_DIR
        elif env == "DEMO":
            src_path = settings.DEMO_DATABASE_PATH
            dest_dir = settings.DEMO_BACKUPS_DIR
        else:
            src_path = settings.REAL_DATABASE_PATH
            dest_dir = settings.DAILY_BACKUPS_DIR
            
        backup_filename = f"studyos_{env.lower()}_{today_str}.sqlite"
        dest_path = dest_dir / backup_filename
        
        if src_path.exists():
            shutil.copy2(src_path, dest_path)
            return str(dest_path)
        return ""

    @staticmethod
    def create_weekly_zip_backup(week_number: int) -> str:
        """Zips DB, reports, study data, and sentinelai docs into data/backups/weekly/."""
        zip_filename = f"studyos_backup_week_{week_number:02d}_{date.today().isoformat()}.zip"
        zip_path = settings.WEEKLY_BACKUPS_DIR / zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 1. Database
            if settings.DATABASE_PATH.exists():
                zipf.write(settings.DATABASE_PATH, arcname=f"database/{settings.DATABASE_PATH.name}")
                
            # 2. Reports
            if settings.REPORTS_DIR.exists():
                for root, _, files in os.walk(settings.REPORTS_DIR):
                    for file in files:
                        full_p = Path(root) / file
                        arcname = f"reports/{full_p.relative_to(settings.REPORTS_DIR)}"
                        zipf.write(full_p, arcname=arcname)
                        
            # 3. Study Notes
            if settings.STUDY_DIR.exists():
                for root, _, files in os.walk(settings.STUDY_DIR):
                    for file in files:
                        full_p = Path(root) / file
                        arcname = f"study/{full_p.relative_to(settings.STUDY_DIR)}"
                        zipf.write(full_p, arcname=arcname)
                        
        return str(zip_path)

    @staticmethod
    async def export_json(session: AsyncSession) -> str:
        """Exports all database tables into a clean JSON file."""
        export_data = {}
        
        # Tasks
        tasks_res = await session.execute(select(Task))
        export_data["tasks"] = [
            {
                "id": t.id, "title": t.title, "category": t.category, 
                "priority": t.priority, "status": t.status, 
                "estimated_minutes": t.estimated_minutes, "due_date": t.due_date,
                "notes": t.notes, "contribution_tags": t.contribution_tags
            } for t in tasks_res.scalars().all()
        ]
        
        # DSA Logs
        dsa_res = await session.execute(select(DSALog))
        export_data["dsa_logs"] = [
            {
                "id": d.id, "problem_name": d.problem_name, "topic": d.topic,
                "difficulty": d.difficulty, "independent_solve": d.independent_solve,
                "mistake_type": d.mistake_type, "created_at": d.created_at.isoformat() if d.created_at else ""
            } for d in dsa_res.scalars().all()
        ]
        
        # Mistakes
        mistakes_res = await session.execute(select(Mistake))
        export_data["mistakes"] = [
            {
                "id": m.id, "category": m.category, "mistake_type": m.mistake_type,
                "description": m.description, "occurrences_count": m.occurrences_count,
                "resolved": m.resolved
            } for m in mistakes_res.scalars().all()
        ]
        
        out_path = settings.EXPORTS_DIR / "json" / f"studyos_export_{date.today().isoformat()}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2)
            
        return str(out_path)

    @staticmethod
    async def export_csv(session: AsyncSession) -> Dict[str, str]:
        """Exports key tables into separate CSV files."""
        csv_dir = settings.EXPORTS_DIR / "csv"
        paths = {}
        
        # 1. Tasks CSV
        tasks_res = await session.execute(select(Task))
        tasks_path = csv_dir / "tasks.csv"
        with open(tasks_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "title", "category", "priority", "status", "due_date", "notes"])
            for t in tasks_res.scalars().all():
                writer.writerow([t.id, t.title, t.category, t.priority, t.status, t.due_date, t.notes or ""])
        paths["tasks"] = str(tasks_path)
        
        # 2. DSA Logs CSV
        dsa_res = await session.execute(select(DSALog))
        dsa_path = csv_dir / "dsa_logs.csv"
        with open(dsa_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "problem_name", "topic", "difficulty", "independent_solve", "mistake_type"])
            for d in dsa_res.scalars().all():
                writer.writerow([d.id, d.problem_name, d.topic, d.difficulty, d.independent_solve, d.mistake_type or ""])
        paths["dsa_logs"] = str(dsa_path)
        
        return paths
