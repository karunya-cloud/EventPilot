"""Unit tests for Database Models, Foreign Keys, and Constraints."""
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import IntegrityError

from src.db.session import SessionLocal, init_db, engine, Base
from src.db.models import (
    User,
    UserRole,
    Event,
    EventStatus,
    Task,
    TaskStatus,
    TaskPriority,
    TaskDependency,
    Registration,
    RegistrationStatus,
    AttendanceRecord,
    InventoryItem,
    EquipmentAllocation,
    Expense,
    ExpenseStatus,
    RiskAlert,
    MitigationPlan,
    AuditLog,
)
from src.db.seed import seed_database

@pytest.fixture(scope="module")
def setup_db():
    init_db()
    seed_database()
    yield
    # Cleanup in-memory / test artifacts if needed

def test_inventory_seed_robotics_kits(setup_db):
    """Verify that exactly 40 Robotics Hardware Kits are seeded."""
    db = SessionLocal()
    item = db.query(InventoryItem).filter(InventoryItem.name == "Robotics Hardware Kit").first()
    assert item is not None
    assert item.available_quantity == 40
    assert item.total_quantity == 40
    assert item.unit_cost == 450.0
    db.close()

def test_event_and_task_creation(setup_db):
    """Verify event creation and task dependency relationships."""
    db = SessionLocal()
    event = Event(
        title="Test Autonomous Robotics Workshop",
        description="A hands-on workshop",
        target_date=datetime.now(timezone.utc) + timedelta(days=20),
        duration_hours=4.0,
        venue="Lab 3",
        capacity=60,
        budget=20000.0,
        status=EventStatus.PROPOSED,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    task1 = Task(
        event_id=event.id,
        title="Procure Component Kits",
        due_date=event.target_date - timedelta(days=7),
        status=TaskStatus.PENDING,
        priority=TaskPriority.HIGH,
    )
    task2 = Task(
        event_id=event.id,
        title="Prepare Lab Workstations",
        due_date=event.target_date - timedelta(days=2),
        status=TaskStatus.PENDING,
        priority=TaskPriority.MEDIUM,
    )
    db.add_all([task1, task2])
    db.commit()

    # Create dependency: Task 2 depends on Task 1
    dep = TaskDependency(task_id=task2.id, depends_on_task_id=task1.id)
    db.add(dep)
    db.commit()

    # Query tasks
    event_tasks = db.query(Task).filter(Task.event_id == event.id).all()
    assert len(event_tasks) == 2
    assert len(task2.dependencies) == 1
    assert task2.dependencies[0].depends_on_task_id == task1.id

    db.close()

def test_registration_duplicate_email_constraint(setup_db):
    """Verify that duplicate registrations with the same email for an event are rejected."""
    db = SessionLocal()
    event = Event(
        title="Capacity Test Event",
        target_date=datetime.now(timezone.utc) + timedelta(days=5),
        venue="Hall B",
        capacity=2,
        budget=5000.0,
    )
    db.add(event)
    db.commit()

    reg1 = Registration(
        event_id=event.id,
        student_name="Student One",
        student_email="student1@college.edu",
        student_id="CS101",
        qr_token="token_unique_1",
    )
    db.add(reg1)
    db.commit()

    reg2 = Registration(
        event_id=event.id,
        student_name="Duplicate Student",
        student_email="student1@college.edu",  # Duplicate email
        student_id="CS102",
        qr_token="token_unique_2",
    )
    db.add(reg2)
    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()
    db.close()

def test_attendance_unique_checkin_constraint(setup_db):
    """Verify that multiple check-in records for the same registration are constrained."""
    db = SessionLocal()
    event = Event(
        title="Checkin Test Event",
        target_date=datetime.now(timezone.utc) + timedelta(days=1),
        venue="Room 101",
        capacity=10,
        budget=1000.0,
    )
    db.add(event)
    db.commit()

    reg = Registration(
        event_id=event.id,
        student_name="Attendee Alpha",
        student_email="alpha@college.edu",
        student_id="CS555",
        qr_token="qr_alpha_999",
    )
    db.add(reg)
    db.commit()

    checkin1 = AttendanceRecord(
        registration_id=reg.id,
        event_id=event.id,
        device_id="SCANNER_1",
    )
    db.add(checkin1)
    db.commit()

    # Attempt second check-in for the exact same registration
    checkin2 = AttendanceRecord(
        registration_id=reg.id,
        event_id=event.id,
        device_id="SCANNER_2",
    )
    db.add(checkin2)
    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()
    db.close()
