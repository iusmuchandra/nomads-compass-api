import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

load_dotenv()

# Use SQLite as fallback for development
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./test.db"

# Remove the debug print that exposes sensitive information
# print(f"--- DEBUG: Connecting with URL: {SQLALCHEMY_DATABASE_URL} ---")

# SQLite requires this for proper threading
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    # Add connection pooling and retry logic for PostgreSQL
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()