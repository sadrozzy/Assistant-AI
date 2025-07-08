from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings
from collections.abc import AsyncGenerator
from app.utils.logger import logger

logger = logger("db-session")

engine = create_async_engine(settings.DATABASE_URL, echo=True)
logger.info(f"Database engine created")

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    connect_args={"statement_cache_size": 0},
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    try:
        async with AsyncSessionLocal() as session:
            logger.debug("Yielding new async DB session")
            yield session
    except Exception as e:
        logger.exception(f"Failed to get DB session: {e}")
        raise
