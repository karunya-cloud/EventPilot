"""Unit tests for EventPilot AI Business Logic Tools."""
import pytest
from datetime import datetime, timezone, timedelta
from src.db.session import SessionLocal, init_db
from src.db.seed import seed_database
from src.db.models import TaskStatus, RegistrationStatus, EmailStatus
from src.tools import (
    create_event,
    get_event,
    generate_timeline,
    create_task,
    update_task,
    register_participant,
    cancel_registration,
    promote_waitlisted_participant,
    check_resource_shortages,
    record_expense,
    calculate_budget,
    draft_email,
    send_approved_email,
    detect_risks,
    apply_approved_mitigation,
    check_in_attendee,
    generate_attendance_report,
    get_dashboard_summary,
)

@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()
    seed_database()

def test_event_creation_and_dashboard():
    db = SessionLocal()
    event_data = create_event(
        db=db,
        title="Robotics Workshop 2026",
        target_date=datetime.now(timezone.utc) + timedelta(days=20),
        venue="Robotics Lab 3",
        capacity=60,
        budget=20000.0,
    )
    assert event_data["event_id"] is not None
    assert event_data["capacity"] == 60
    assert event_data["budget"] == 20000.0

    summary = get_dashboard_summary(db, event_data["event_id"])
    assert summary["capacity"] == 60
    assert summary["confirmed_attendees"] == 0
    assert summary["budget_remaining"] == 20000.0
    db.close()

def test_timeline_dag_generation_and_dependency_blocking():
    db = SessionLocal()
    event = create_event(
        db=db,
        title="Timeline Test Event",
        target_date=datetime.now(timezone.utc) + timedelta(days=15),
        venue="Lab 1",
        capacity=30,
        budget=10000.0,
    )
    tasks = generate_timeline(db, event["event_id"])
    assert len(tasks) == 7

    # Find a child task that depends on a parent
    # t7 depends on t5 and t6
    t7 = [t for t in tasks if "Event Execution" in t["title"]][0]
    
    # Attempting to complete child task before parent completes must raise ValueError
    with pytest.raises(ValueError) as exc:
        update_task(db, t7["task_id"], status=TaskStatus.COMPLETED)
    assert "Parent dependency" in str(exc.value)
    db.close()

def test_capacity_enforcement_and_auto_waitlist_promotion():
    db = SessionLocal()
    event = create_event(
        db=db,
        title="Mini Capped Workshop",
        target_date=datetime.now(timezone.utc) + timedelta(days=10),
        venue="Seminar Room",
        capacity=2,
        budget=5000.0,
    )
    eid = event["event_id"]

    # 1. Register student 1 (Capacity 1/2) -> CONFIRMED
    r1 = register_participant(db, eid, "Alice Smith", "alice@test.edu", "ST01")
    assert r1["status"] == "CONFIRMED"
    assert r1["qr_token"] is not None

    # 2. Register student 2 (Capacity 2/2) -> CONFIRMED
    r2 = register_participant(db, eid, "Bob Jones", "bob@test.edu", "ST02")
    assert r2["status"] == "CONFIRMED"

    # 3. Register student 3 (Capacity 2/2 FULL) -> WAITLISTED pos 1
    r3 = register_participant(db, eid, "Charlie Brown", "charlie@test.edu", "ST03")
    assert r3["status"] == "WAITLISTED"
    assert r3["waitlist_position"] == 1
    assert r3["qr_token"] is None

    # 4. Student 1 cancels -> Charlie must be auto-promoted to CONFIRMED!
    cancel_res = cancel_registration(db, r1["registration_id"])
    assert cancel_res["status"] == "CANCELLED"
    promoted = cancel_res["auto_promoted_waitlist_attendee"]
    assert promoted is not None
    assert promoted["student_name"] == "Charlie Brown"
    assert promoted["status"] == "CONFIRMED"
    assert promoted["qr_token"] is not None

    db.close()

def test_inventory_shortage_detection():
    db = SessionLocal()
    event = create_event(
        db=db,
        title="Shortage Scenario Event",
        target_date=datetime.now(timezone.utc) + timedelta(days=12),
        venue="Hardware Lab",
        capacity=60,
        budget=20000.0,
    )
    # Check 60 kits against 40 available in depot
    check = check_resource_shortages(db, event["event_id"], "Robotics Hardware Kit", 60)
    assert check["is_sufficient"] is False
    assert check["available_quantity"] == 40
    assert check["shortage"] == 20
    db.close()

def test_risk_mitigation_and_approval_execution():
    db = SessionLocal()
    event = create_event(
        db=db,
        title="Mitigation Test Event",
        target_date=datetime.now(timezone.utc) + timedelta(days=14),
        venue="Lab 3",
        capacity=60,
        budget=20000.0,
    )
    eid = event["event_id"]

    # Detect risks
    risks = detect_risks(db, eid, "Robotics Hardware Kit", 60)
    assert len(risks) == 1
    alert = risks[0]
    assert alert["shortage"] == 20
    assert len(alert["mitigation_options"]) == 3

    # Option B: Pair students into 30 teams (0 cost, 30 kits)
    exec_result = apply_approved_mitigation(
        db=db,
        risk_alert_id=alert["alert_id"],
        chosen_option_key="OPTION_B",
        approver_name="Karunya Jajoo",
    )
    assert exec_result["status"] == "MITIGATED"
    assert exec_result["execution_details"]["format"] == "2-Person Teams"
    assert exec_result["execution_details"]["kits_allocated"] == 30
    assert exec_result["execution_details"]["cost_incurred"] == 0.0

    db.close()

def test_email_draft_and_strict_approval_gate():
    db = SessionLocal()
    event = create_event(
        db=db,
        title="Email Gate Test Event",
        target_date=datetime.now(timezone.utc) + timedelta(days=7),
        venue="Auditorium",
        capacity=50,
        budget=10000.0,
    )
    draft = draft_email(db, event["event_id"], email_type="INVITATION")
    assert draft["status"] == "PENDING_APPROVAL"
    assert draft["approval_required"] is True

    # Send upon explicit approval
    send_res = send_approved_email(db, draft["draft_id"], approver_name="Lead Organizer")
    assert send_res["status"] == "SENT"
    assert send_res["approved_by"] == "Lead Organizer"
    db.close()

def test_qr_checkin_and_duplicate_scan_prevention():
    db = SessionLocal()
    event = create_event(
        db=db,
        title="QR Attendance Event",
        target_date=datetime.now(timezone.utc) + timedelta(days=3),
        venue="Hall 1",
        capacity=10,
        budget=3000.0,
    )
    reg = register_participant(db, event["event_id"], "David Miller", "david@test.edu", "ST100")
    qr = reg["qr_token"]

    # First check-in scan: SUCCESS
    scan1 = check_in_attendee(db, qr, device_id="SCANNER_GATE_A")
    assert scan1["success"] is True
    assert scan1["is_duplicate_attempt"] is False
    assert scan1["student_name"] == "David Miller"

    # Second check-in scan (repeated / fraud): REJECTED
    scan2 = check_in_attendee(db, qr, device_id="SCANNER_GATE_B")
    assert scan2["success"] is False
    assert scan2["is_duplicate_attempt"] is True
    assert "ALREADY_CHECKED_IN" in scan2["message"]

    # Attendance report
    report = generate_attendance_report(db, event["event_id"])
    assert report["total_confirmed"] == 1
    assert report["total_present"] == 1
    assert report["turnout_pct"] == 100.0

    db.close()
