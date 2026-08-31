import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "StudyOS"
    VERSION: str = "1.0.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Base Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    DATABASE_DIR: Path = BASE_DIR / "data" / "database"
    
    # Real Mode DB & Paths
    REAL_DATABASE_PATH: Path = BASE_DIR / "data" / "database" / "studyos.db"
    TEST_DATABASE_PATH: Path = BASE_DIR / "data" / "database" / "studyos_test.db"
    DEMO_DATABASE_PATH: Path = BASE_DIR / "data" / "database" / "studyos_demo.db"
    
    # Default Database Path (will be dynamically selected based on active env)
    DATABASE_PATH: Path = REAL_DATABASE_PATH
    DATABASE_URL: str = f"sqlite+aiosqlite:///{REAL_DATABASE_PATH}"
    
    # Reports Directories
    REPORTS_DIR: Path = BASE_DIR / "reports"
    DAILY_REPORTS_DIR: Path = BASE_DIR / "reports" / "daily"
    WEEKLY_REPORTS_DIR: Path = BASE_DIR / "reports" / "weekly"
    MONTHLY_REPORTS_DIR: Path = BASE_DIR / "reports" / "monthly"
    MILESTONE_REPORTS_DIR: Path = BASE_DIR / "reports" / "milestone"
    
    # Test & Demo Isolated Reports Directories
    TEST_REPORTS_DIR: Path = BASE_DIR / "reports" / "test"
    DEMO_REPORTS_DIR: Path = BASE_DIR / "reports" / "demo"
    
    # Other Directories
    STUDY_DIR: Path = BASE_DIR / "study"
    SENTINELAI_DIR: Path = BASE_DIR / "sentinelai"
    EXPORTS_DIR: Path = BASE_DIR / "exports"
    BACKUPS_DIR: Path = BASE_DIR / "data" / "backups"
    DAILY_BACKUPS_DIR: Path = BASE_DIR / "data" / "backups" / "daily"
    WEEKLY_BACKUPS_DIR: Path = BASE_DIR / "data" / "backups" / "weekly"
    TEST_BACKUPS_DIR: Path = BASE_DIR / "data" / "backups" / "test"
    DEMO_BACKUPS_DIR: Path = BASE_DIR / "data" / "backups" / "demo"
    CONFIG_DIR: Path = BASE_DIR / "config"
    
    # API Keys & Security
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    LAN_SECRET: str = "studyos-local-secret"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

def ensure_directories():
    """Ensure all system directories exist."""
    dirs = [
        settings.DATA_DIR,
        settings.DATABASE_DIR,
        settings.REPORTS_DIR,
        settings.DAILY_REPORTS_DIR,
        settings.WEEKLY_REPORTS_DIR,
        settings.MONTHLY_REPORTS_DIR,
        settings.MILESTONE_REPORTS_DIR,
        settings.TEST_REPORTS_DIR,
        settings.DEMO_REPORTS_DIR,
        settings.STUDY_DIR,
        settings.STUDY_DIR / "DSA",
        settings.STUDY_DIR / "ML",
        settings.STUDY_DIR / "DL",
        settings.STUDY_DIR / "ComputerVision",
        settings.STUDY_DIR / "College",
        settings.SENTINELAI_DIR,
        settings.SENTINELAI_DIR / "architecture",
        settings.SENTINELAI_DIR / "experiments",
        settings.SENTINELAI_DIR / "results",
        settings.SENTINELAI_DIR / "notes",
        settings.SENTINELAI_DIR / "milestones",
        settings.EXPORTS_DIR,
        settings.EXPORTS_DIR / "csv",
        settings.EXPORTS_DIR / "json",
        settings.EXPORTS_DIR / "markdown",
        settings.BACKUPS_DIR,
        settings.DAILY_BACKUPS_DIR,
        settings.WEEKLY_BACKUPS_DIR,
        settings.TEST_BACKUPS_DIR,
        settings.DEMO_BACKUPS_DIR,
        settings.CONFIG_DIR,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

ensure_directories()
