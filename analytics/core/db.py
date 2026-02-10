from tortoise import Tortoise
from analytics.core.config import settings
from analytics.core.logger import logger

DATABASE_URL = settings.DATABASE_URL

# Module-level flag indicating whether DB is usable
DB_AVAILABLE = False

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

async def init_db() -> None:
    """Initialize database connection (fault-tolerant).
    
    Sets DB_AVAILABLE = True on success. On failure, logs a warning
    and leaves DB_AVAILABLE = False so the rest of the app can degrade gracefully.
    """
    global DB_AVAILABLE

    if not settings.DB_ENABLED:
        logger.warning("⚠️ DATABASE_URL not configured, using local SQLite fallback. History features limited.")

    try:
        await Tortoise.init(config=TORTOISE_ORM)
        await Tortoise.generate_schemas()
        DB_AVAILABLE = True

        if "sqlite" in DATABASE_URL:
            logger.info(f"✅ Database connected: {DATABASE_URL}")
        else:
            logger.info("✅ Database connected: Remote PostgreSQL")
    except Exception as e:
        DB_AVAILABLE = False
        logger.error(f"❌ Database initialization failed: {e}")
        logger.warning("⚠️ Continuing without database — history/snapshot features disabled.")

async def close_db() -> None:
    """Close database connection"""
    if DB_AVAILABLE:
        await Tortoise.close_connections()
