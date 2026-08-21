from datetime import datetime, time
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app
from models import Base, DowntimeCategory, DowntimeEvent, DowntimeReason, Machine, ProductionRun, Shift


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def machine_factory(db_session: Session):
    def _create_machine(**kwargs) -> Machine:
        defaults = {
            "code": f"M-{datetime.now().timestamp()}",
            "name": "CNC Milling Station",
            "description": "Standard production line",
            "ideal_cycle_time_seconds": 30.0,
            "is_active": True,
        }
        defaults.update(kwargs)
        machine = Machine(**defaults)
        db_session.add(machine)
        db_session.commit()
        db_session.refresh(machine)
        return machine

    return _create_machine


@pytest.fixture
def shift_factory(db_session: Session):
    def _create_shift(**kwargs) -> Shift:
        defaults = {
            "name": "Standard Morning Shift",
            "start_time": time(8, 0),
            "end_time": time(16, 0),
            "planned_break_minutes": 30,
            "is_active": True,
        }
        defaults.update(kwargs)
        shift = Shift(**defaults)
        db_session.add(shift)
        db_session.commit()
        db_session.refresh(shift)
        return shift

    return _create_shift


@pytest.fixture
def downtime_reason_factory(db_session: Session):
    def _create_reason(**kwargs) -> DowntimeReason:
        defaults = {
            "name": f"Reason-{datetime.now().timestamp()}",
            "category": DowntimeCategory.BREAKDOWN,
            "is_planned": False,
            "color_code": "#EF4444",
            "is_active": True,
        }
        defaults.update(kwargs)
        reason = DowntimeReason(**defaults)
        db_session.add(reason)
        db_session.commit()
        db_session.refresh(reason)
        return reason

    return _create_reason


@pytest.fixture
def downtime_event_factory(db_session: Session):
    def _create_event(**kwargs) -> DowntimeEvent:
        defaults = {
            "start_time": datetime(2026, 8, 20, 9, 0, 0),
            "end_time": datetime(2026, 8, 20, 10, 0, 0),
            "operator_name": "John Doe",
            "notes": "Valve leakage",
        }
        defaults.update(kwargs)
        event = DowntimeEvent(**defaults)
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)
        return event

    return _create_event


@pytest.fixture
def production_run_factory(db_session: Session):
    def _create_run(**kwargs) -> ProductionRun:
        defaults = {
            "product_code": "PART-A1",
            "product_name": "Precision Housing",
            "start_time": datetime(2026, 8, 20, 8, 0, 0),
            "end_time": datetime(2026, 8, 20, 16, 0, 0),
            "target_units": 500,
            "total_units": 480,
            "scrap_units": 20,
            "ideal_cycle_time_seconds": 30.0,
            "notes": "Routine batch",
        }
        defaults.update(kwargs)
        run = ProductionRun(**defaults)
        db_session.add(run)
        db_session.commit()
        db_session.refresh(run)
        return run

    return _create_run
