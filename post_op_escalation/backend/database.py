import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/post_op_db"
)

# Create database engine
engine = create_engine(DATABASE_URL, echo=False)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for SQLAlchemy models
Base = declarative_base()


def get_db():
    """Yield a database session context."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables(target_engine=None):
    """Create all configured database tables."""
    from . import models  # Ensure all model classes register with Base
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)
