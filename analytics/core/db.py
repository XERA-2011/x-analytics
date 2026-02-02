from tortoise import Tortoise
from analytics.core.config import settings
from analytics.core.logger import logger
import os

DATABASE_URL = settings.DATABASE_URL

TORTOISE_ORM = {
    "connections": {"default": DATABASE_URL},
    "apps": {
        "models": {
            "models": [
                "analytics.models.sentiment",
                "analytics.models.signal_history",
            ],
            "default_connection": "default",
        }
    },
}

async def init_db():
    """Initialize database connection"""
    try:
        await Tortoise.init(config=TORTOISE_ORM)
        # Generate schemas (create tables) if they don't exist
        await Tortoise.generate_schemas()
        if "sqlite" in DATABASE_URL:
             logger.info(f"✅ Database connected: {DATABASE_URL}")
        else:
             # Hide password in logs for safety
             logger.info("✅ Database connected: Remote PostgreSQL")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

async def close_db():
    """Close database connection"""
    await Tortoise.close_connections()
