import asyncio
from backend.app.core.database import Base, engine
import backend.app.models.domain      # noqa: F401
import backend.app.models.snapshot    # noqa: F401
import backend.app.models.analysis    # noqa: F401
import backend.app.models.timeline    # noqa: F401
import backend.app.models.threat_intel  # noqa: F401
from backend.app.utils.logger import logger

async def recreate():
    logger.info("Dropping all existing database tables to apply new schema changes...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("All tables dropped successfully.")
        logger.info("Creating all database tables with the new schemas...")
        await conn.run_sync(Base.metadata.create_all)
        logger.info("All database tables created successfully.")

if __name__ == "__main__":
    asyncio.run(recreate())
