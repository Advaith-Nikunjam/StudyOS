from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

Base = declarative_base()

# Track active environment mode: "REAL", "TEST", "DEMO"
CURRENT_ENV_MODE = "REAL"

_engines = {
    "REAL": create_async_engine(f"sqlite+aiosqlite:///{settings.REAL_DATABASE_PATH}", echo=False, future=True, connect_args={"check_same_thread": False}),
    "TEST": create_async_engine(f"sqlite+aiosqlite:///{settings.TEST_DATABASE_PATH}", echo=False, future=True, connect_args={"check_same_thread": False}),
    "DEMO": create_async_engine(f"sqlite+aiosqlite:///{settings.DEMO_DATABASE_PATH}", echo=False, future=True, connect_args={"check_same_thread": False}),
}

_sessionmakers = {
    mode: async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False)
    for mode, engine in _engines.items()
}

def get_current_env_mode() -> str:
    return CURRENT_ENV_MODE

def set_current_env_mode(mode: str) -> str:
    global CURRENT_ENV_MODE
    mode_upper = mode.upper()
    if mode_upper in _engines:
        CURRENT_ENV_MODE = mode_upper
    return CURRENT_ENV_MODE

def get_engine(mode: str = None):
    m = (mode or CURRENT_ENV_MODE).upper()
    return _engines.get(m, _engines["REAL"])

def get_sessionmaker(mode: str = None):
    m = (mode or CURRENT_ENV_MODE).upper()
    return _sessionmakers.get(m, _sessionmakers["REAL"])

class AsyncSessionLocalContext:
    def __init__(self, mode: str = None):
        self.mode = mode

    async def __aenter__(self) -> AsyncSession:
        self.sessionmaker = get_sessionmaker(self.mode)
        self.session = self.sessionmaker()
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

def AsyncSessionLocal(mode: str = None):
    """Context manager returning an AsyncSession for active or specified environment mode."""
    return AsyncSessionLocalContext(mode)

async def get_db():
    """Dependency providing session for the active environment mode."""
    sessionmaker = get_sessionmaker(CURRENT_ENV_MODE)
    async with sessionmaker() as session:
        try:
            yield session
        finally:
            await session.close()

