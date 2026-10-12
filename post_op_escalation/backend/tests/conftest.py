import os
import pytest
from datetime import date, timedelta

# Force test mode and SQLite test DB before importing any backend modules
os.environ["TESTING"] = "1"
os.environ["TEST_DATABASE_URL"] = "sqlite:///./post_op_test.db"

from backend.database import engine, Base, SessionLocal, create_tables
from backend.models import Patient


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Session-level fixture ensuring SQLite database is initialized with all
    required tables and baseline test patients without requiring live PostgreSQL.
    """
    # Clean previous test database tables
    Base.metadata.drop_all(bind=engine)
    create_tables(target_engine=engine)

    # Seed baseline patients for deterministic test runs
    db = SessionLocal()
    try:
        today = date.today()
        for i in range(1, 15):
            p_code = f"PAT-{i:03d}"
            existing = db.query(Patient).filter(Patient.patient_code == p_code).first()
            if not existing:
                p = Patient(
                    patient_code=p_code,
                    name=f"Test Patient {i:03d}",
                    age=50 + i,
                    surgery_type="Laparoscopic Cholecystectomy",
                    surgery_date=today - timedelta(days=2)
                )
                db.add(p)
        db.commit()
    finally:
        db.close()

    yield

    # Clean up test database file after session
    Base.metadata.drop_all(bind=engine)
    test_db_file = "post_op_test.db"
    if os.path.exists(test_db_file):
        try:
            os.remove(test_db_file)
        except OSError:
            pass
