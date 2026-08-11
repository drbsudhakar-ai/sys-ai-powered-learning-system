"""
Database Configuration
----------------------
SYS AI Lecturer System
Primary: Supabase (Managed PostgreSQL)
Future Scope: Neon, Render, Railway, or any PostgreSQL-compatible service
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Example Supabase connection string:
# postgresql://postgres:<PASSWORD>@db.<PROJECT_REF>.supabase.co:5432/postgres
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL not set in .env file")

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
