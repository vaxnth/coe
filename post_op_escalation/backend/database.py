import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# In test mode or when testing without PostgreSQL, use SQLite test database
IS_TESTING = os.getenv("TESTING", "0") in ("1", "true", "True")

if IS_TESTING:
    DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./post_op_test.db")
else:
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/post_op_db"
    )

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Create database engine
engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)

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

