"""Attendance check-in tools with QR code token verification and duplicate scan protection."""
import io
import base64
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import qrcode
from sqlalchemy.orm import Session
from src.db.models import Registration, RegistrationStatus, AttendanceRecord, Event
from src.tools.audit import record_audit

def generate_checkin_qr_png_base64(qr_token: str) -> str:
    """Generate base64 encoded PNG for a QR check-in token."""
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=2,
    )
    qr.add_data(qr_token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

def check_in_attendee(
    db: Session,
    qr_token: str,
    device_id: str = "SCANNER_ENTRY_GATE",
    agent_name: str = "RegistrationAgent",
) -> Dict[str, Any]:
    """Validate QR check-in token and record attendance with idempotency."""
    reg = db.query(Registration).filter(Registration.qr_token == qr_token).first()
    if not reg:
        return {
            "success": False,
            "error": "INVALID_TOKEN: QR token does not correspond to any active registration.",
        }

    if reg.status != RegistrationStatus.CONFIRMED:
        return {
            "success": False,
            "error": f"INELIGIBLE_STATUS: Registration is {reg.status.value}, not CONFIRMED.",
            "student_name": reg.student_name,
        }

    # Check for existing check-in (idempotency & fraud prevention)
    existing_record = db.query(AttendanceRecord).filter(
        AttendanceRecord.registration_id == reg.id
    ).first()

    if existing_record:
        # Flag duplicate scan attempt
        return {
            "success": False,
            "is_duplicate_attempt": True,
            "message": f"ALREADY_CHECKED_IN: {reg.student_name} was previously scanned at {existing_record.checked_in_at.isoformat()} on {existing_record.device_id}.",
            "student_name": reg.student_name,
            "checked_in_at": existing_record.checked_in_at.isoformat(),
        }

    # First valid scan
    record = AttendanceRecord(
        registration_id=reg.id,
        event_id=reg.event_id,
        checked_in_at=datetime.now(timezone.utc),
        device_id=device_id,
        is_duplicate_attempt=False,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    record_audit(
        db=db,
        agent_name=agent_name,
        tool_name="check_in_attendee",
        action_type="INSERT_CHECKIN",
        payload={"registration_id": reg.id, "student_name": reg.student_name, "device_id": device_id},
        success=True,
        event_id=reg.event_id,
    )

    return {
        "success": True,
        "is_duplicate_attempt": False,
        "student_name": reg.student_name,
        "student_id": reg.student_id,
        "checked_in_at": record.checked_in_at.isoformat(),
        "device_id": record.device_id,
    }

def generate_attendance_report(db: Session, event_id: int) -> Dict[str, Any]:
    """Produce comprehensive attendance audit report."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found.")

    confirmed_regs = db.query(Registration).filter(
        Registration.event_id == event_id,
        Registration.status == RegistrationStatus.CONFIRMED,
    ).all()

    total_confirmed = len(confirmed_regs)
    checkins = db.query(AttendanceRecord).filter(
        AttendanceRecord.event_id == event_id
    ).all()
    checked_in_ids = {c.registration_id for c in checkins}

    present_count = len(checked_in_ids)
    turnout_pct = round((present_count / total_confirmed * 100), 1) if total_confirmed > 0 else 0.0

    present_students = []
    absent_students = []

    for r in confirmed_regs:
        if r.id in checked_in_ids:
            present_students.append({"name": r.student_name, "student_id": r.student_id})
        else:
            absent_students.append({"name": r.student_name, "student_id": r.student_id})

    return {
        "event_id": event.id,
        "event_title": event.title,
        "total_confirmed": total_confirmed,
        "total_present": present_count,
        "turnout_pct": turnout_pct,
        "present_students": present_students,
        "absent_students": absent_students,
    }
