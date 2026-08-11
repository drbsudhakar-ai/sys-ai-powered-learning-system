"""
Database Configuration
----------------------
SYS AI Lecturer System
Primary: Supabase (Managed PostgreSQL)
Future Scope: Neon, Render, Railway, or any PostgreSQL-compatible service

DATABASE_URL is loaded from the environment via app.config.settings.
Never hardcode database credentials in this module.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

DATABASE_URL = settings.DATABASE_URL

# Create SQLAlchemy engine
# pool_pre_ping keeps connections alive, useful for cloud DBs
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# Dependency for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
