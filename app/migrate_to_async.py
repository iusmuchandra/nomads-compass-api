#!/usr/bin/env python3
"""
Migration script to transition from sync to async database operations
and set up production environment.

Usage:
    python migrate_to_async.py --mode [development|production]
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
from typing import Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def test_async_database():
    """Test async database connection"""
    try:
        from .async_database import test_database_connection, init_database
        
        logger.info("Testing async database connection...")
        connection_ok = await test_database_connection()
        
        if connection_ok:
            logger.info("✅ Async database connection successful!")
            
            logger.info("Initializing database tables...")
            init_ok = await init_database()
            
            if init_ok:
                logger.info("✅ Database initialization successful!")
                return True
            else:
                logger.error("❌ Database initialization failed!")
                return False
        else:
            logger.error("❌ Async database connection failed!")
            return False
            
    except ImportError as e:
        logger.error(f"❌ Import error: {e}")
        logger.error("Make sure you've installed the async dependencies:")
        logger.error("pip install asyncpg aiosqlite sqlalchemy[asyncio]")
        return False
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

def create_env_file(mode: str = "development"):
    """Create a .env file with the necessary environment variables"""
    env_path = Path(".env")
    
    if env_path.exists():
        logger.info("📄 .env file already exists. Creating .env.example as template...")
        env_path = Path(".env.example")
    
    if mode == "production":
        env_content = """# Production Environment Configuration
# Copy this file to .env and update with your actual values

# Database Configuration (PostgreSQL recommended for production)
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/nomads_compass

# Security Configuration
SECRET_KEY=your_super_secret_jwt_key_here_make_it_very_long_and_random

# External API Keys
AERODATASPHERE_API_KEY=your_flight_api_key_here
HOTEL_API_KEY=your_hotel_api_key_here

# Optional: Redis for caching
REDIS_URL=redis://localhost:6379/0

# Application Settings
ENVIRONMENT=production
DEBUG=False
"""
    else:  # development
        env_content = """# Development Environment Configuration

# Database Configuration (SQLite for development)
DATABASE_URL=sqlite+aiosqlite:///./development.db

# Security Configuration
SECRET_KEY=development_secret_key_change_this_in_production

# External API Keys (get free keys from RapidAPI)
AERODATASPHERE_API_KEY=your_flight_api_key_here
HOTEL_API_KEY=your_hotel_api_key_here

# Application Settings
ENVIRONMENT=development
DEBUG=True
"""
    
    with open(env_path, "w") as f:
        f.write(env_content)
    
    logger.info(f"✅ Created {env_path}")
    logger.info("📝 Please update the API keys and database credentials!")

def create_directory_structure():
    """Create necessary directory structure"""
    directories = [
        "tests",
        ".github/workflows",
        "nginx",
        "db",
        "logs",
        "static"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Created directory: {directory}")

def create_github_actions_files():
    """Create necessary files for GitHub Actions"""
    
    # Create .github/workflows directory if it doesn't exist
    workflow_dir = Path(".github/workflows")
    workflow_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("📁 GitHub Actions workflow directory ready")
    logger.info("🔄 Use the GitHub Actions workflow artifact from the previous response")

def create_test_directory():
    """Create test directory structure"""
    test_dir = Path("tests")
    test_dir.mkdir(exist_ok=True)
    
    # Create __init__.py
    init_file = test_dir / "__init__.py"
    if not init_file.exists():
        init_file.touch()
    
    # Create conftest.py for shared test fixtures
    conftest_content = '''"""Shared test configuration and fixtures."""
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from async_database import Base

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_async.db"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def async_engine():
    """Create async engine for testing."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def async_session(async_engine):
    """Create async session for testing."""
    async_session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
'''
    
    conftest_file = test_dir / "conftest.py"
    if not conftest_file.exists():
        with open(conftest_file, "w") as f:
            f.write(conftest_content)
        logger.info("✅ Created tests/conftest.py")

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        "fastapi",
        "uvicorn",
        "sqlalchemy",
        "asyncpg",
        "aiosqlite",
        "pydantic",
        "jose",
        "passlib",
        "httpx"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error("❌ Missing required packages:")
        for package in missing_packages:
            logger.error(f"   - {package}")
        logger.error("\nInstall missing packages with:")
        logger.error(f"pip install {' '.join(missing_packages)}")
        return False
    
    logger.info("✅ All required dependencies are installed!")
    return True

async def run_async_tests():
    """Run basic async functionality tests"""
    try:
        logger.info("🧪 Running async functionality tests...")
        
        # Test async database
        db_test = await test_async_database()
        if not db_test:
            return False
        
        # Test async imports
        try:
            from .async_crud import get_user_by_email, create_user
            from .async_database import get_async_db
            logger.info("✅ Async modules imported successfully!")
        except ImportError as e:
            logger.error(f"❌ Failed to import async modules: {e}")
            return False
        
        logger.info("✅ All async tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Async tests failed: {e}")
        return False

def print_next_steps(mode: str):
    """Print next steps for the user"""
    logger.info("\n🎉 Migration setup complete!")
    logger.info("\n📋 NEXT STEPS:")
    
    if mode == "development":
        logger.info("1. Update your .env file with actual API keys")
        logger.info("2. Run: python async_main.py")
        logger.info("3. Test the API at: http://localhost:8000/docs")
        logger.info("4. Run tests with: pytest tests/ -v")
    else:  # production
        logger.info("1. Update your .env file with production values")
        logger.info("2. Set up your PostgreSQL database")
        logger.info("3. Configure your domain in nginx.conf")
        logger.info("4. Deploy with: docker-compose up -d")
        logger.info("5. Set up SSL certificates (Let's Encrypt recommended)")
    
    logger.info("\n🔧 Additional Setup:")
    logger.info("- Push your code to GitHub to trigger CI/CD")
    logger.info("- Monitor your application with the /health endpoint")
    logger.info("- Check API status with /api/status")
    
    logger.info("\n📚 Documentation:")
    logger.info("- API docs: /docs")
    logger.info("- Health check: /health")
    logger.info("- API status: /api/status")

async def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(description="Migrate to async database operations")
    parser.add_argument(
        "--mode", 
        choices=["development", "production"],
        default="development",
        help="Setup mode (default: development)"
    )
    
    args = parser.parse_args()
    
    logger.info(f"🚀 Setting up Nomad's Compass for {args.mode} mode...")
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Create directory structure
    create_directory_structure()
    
    # Create environment file
    create_env_file(args.mode)
    
    # Create test structure
    create_test_directory()
    
    # Create GitHub Actions structure
    create_github_actions_files()
    
    # Run async tests
    test_success = await run_async_tests()
    
    if test_success:
        print_next_steps(args.mode)
        logger.info("\n✅ Migration completed successfully!")
    else:
        logger.error("\n❌ Migration completed with errors. Check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())