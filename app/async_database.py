import os
import time
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Enhanced database URL handling with async support
def get_database_url():
    """Get the appropriate database URL for async operations"""
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        # Default to async SQLite for development
        return "sqlite+aiosqlite:///./test.db"
    
    # Convert PostgreSQL URL to async version
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    
    return database_url

SQLALCHEMY_DATABASE_URL = get_database_url()

# Create async engine with connection pooling
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    # SQLite configuration
    engine = create_async_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=False,  # Set to True for SQL logging
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL configuration with connection pooling
    engine = create_async_engine(
        SQLALCHEMY_DATABASE_URL,
        echo=False,  # Set to True for SQL logging
        pool_size=20,           # Number of connections to maintain
        max_overflow=30,        # Additional connections beyond pool_size
        pool_timeout=30,        # Timeout for getting connection from pool
        pool_recycle=1800,      # Recycle connections after 30 minutes
        pool_pre_ping=True,     # Verify connections before use
    )

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Dependency for FastAPI endpoints
async def get_async_db():
    """Async database session dependency"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_database():
    """Initialize database tables asynchronously with retry logic"""
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            async with engine.begin() as conn:
                # Import here to avoid circular imports
                from .models import Base
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created successfully (async)")
                return True
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection failed (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                return False
    
    return False

async def test_database_connection():
    """Test database connection"""
    try:
        async with AsyncSessionLocal() as session:
            # Simple query to test connection
            if "postgresql" in SQLALCHEMY_DATABASE_URL:
                result = await session.execute(text("SELECT version()"))
            else:
                result = await session.execute(text("SELECT sqlite_version()"))
            
            version = result.fetchone()[0]
            logger.info(f"Database connection successful. Version: {version}")
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

async def close_database():
    """Properly close database connections"""
    await engine.dispose()
    logger.info("Database connections closed")