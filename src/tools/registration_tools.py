"""Registration management tools with capacity caps, waitlists, and auto-promotions."""
import secrets
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from src.config import settings
from src.db.models import Event, Registration, RegistrationStatus
from src.tools.audit import record_audit

def generate_signed_qr_token(event_id: int, student_id: str, email: str) -> str:
    """Generate a tamper-proof cryptographically signed HMAC token for QR check-in."""
    raw_payload = f"{event_id}:{student_id}:{email}:{secrets.token_hex(8)}"
    signature = hmac.new(
        settings.QR_SIGNING_SECRET.encode(),
        raw_payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    return f"EP-{raw_payload}-{signature[:16]}"

def register_participant(
    db: Session,
    event_id: int,
    student_name: str,
    student_email: str,
    student_id: str,
    agent_name: str = "RegistrationAgent",
) -> Dict[str, Any]:
    """Register a student with strict capacity limit and automated waitlisting."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found.")

    # Check for duplicate registration
    existing = db.query(Registration).filter(
        Registration.event_id == event_id,
        Registration.student_email == student_email,
    ).first()
    if existing:
        if existing.status == RegistrationStatus.CANCELLED:
            # Reactivate cancelled registration
            pass
        else:
            raise ValueError(f"Participant with email '{student_email}' is already registered (Status: {existing.status.value}).")

    # Current confirmed count
    confirmed_count = db.query(Registration).filter(
        Registration.event_id == event_id,
        Registration.status == RegistrationStatus.CONFIRMED,
    ).count()

    if confirmed_count < event.capacity:
        # Confirmed registration
        status = RegistrationStatus.CONFIRMED
        qr_token = generate_signed_qr_token(event_id, student_id, student_email)
        waitlist_pos = None
    else:
        # Capacity exceeded: append to waitlist
        status = RegistrationStatus.WAITLISTED
        # Next waitlist position
        last_waitlist = db.query(Registration).filter(
            Registration.event_id == event_id,
            Registration.status == RegistrationStatus.WAITLISTED,
        ).order_by(Registration.waitlist_position.desc()).first()
        waitlist_pos = (last_waitlist.waitlist_position + 1) if (last_waitlist and last_waitlist.waitlist_position) else 1
        qr_token = f"WAITLIST-{secrets.token_hex(12)}"

    reg = Registration(
        event_id=event_id,
        student_name=student_name,
        student_email=student_email,
        student_id=student_id,
        status=status,
        waitlist_position=waitlist_pos,
        qr_token=qr_token,
    )
    db.add(reg)
    db.commit()
    db.refresh(reg)

    record_audit(
        db=db,
        agent_name=agent_name,
        tool_name="register_participant",
        action_type="INSERT",
        payload={
            "registration_id": reg.id,
            "student_name": student_name,
            "status": status.value,
            "waitlist_position": waitlist_pos,
        },
        success=True,
        event_id=event_id,
    )

    return {
        "registration_id": reg.id,
        "event_id": event_id,
        "student_name": reg.student_name,
        "student_email": reg.student_email,
        "student_id": reg.student_id,
        "status": reg.status.value,
        "waitlist_position": reg.waitlist_position,
        "qr_token": reg.qr_token if reg.status == RegistrationStatus.CONFIRMED else None,
    }

def cancel_registration(
    db: Session,
    registration_id: int,
    agent_name: str = "RegistrationAgent",
) -> Dict[str, Any]:
    """Cancel registration and automatically promote the next waitlisted student."""
    reg = db.query(Registration).filter(Registration.id == registration_id).first()
    if not reg:
        raise ValueError(f"Registration {registration_id} not found.")

    previous_status = reg.status
    reg.status = RegistrationStatus.CANCELLED
    reg.waitlist_position = None
    db.commit()

    promoted_info = None
    if previous_status == RegistrationStatus.CONFIRMED:
        # Automatic waitlist promotion
        promoted = promote_waitlisted_participant(db, reg.event_id, agent_name=agent_name)
        promoted_info = promoted

    record_audit(
        db=db,
        agent_name=agent_name,
        tool_name="cancel_registration",
        action_type="UPDATE",
        payload={"registration_id": registration_id, "promoted_student": promoted_info},
        success=True,
        event_id=reg.event_id,
    )

    return {
        "registration_id": reg.id,
        "status": reg.status.value,
        "auto_promoted_waitlist_attendee": promoted_info,
    }

def promote_waitlisted_participant(
    db: Session,
    event_id: int,
    agent_name: str = "RegistrationAgent",
) -> Optional[Dict[str, Any]]:
    """Promote the top waitlisted attendee to confirmed status."""
    top_waitlisted = db.query(Registration).filter(
        Registration.event_id == event_id,
        Registration.status == RegistrationStatus.WAITLISTED,
    ).order_by(Registration.waitlist_position.asc()).first()

    if not top_waitlisted:
        return None

    # Promote to confirmed
    top_waitlisted.status = RegistrationStatus.CONFIRMED
    top_waitlisted.waitlist_position = None
    top_waitlisted.qr_token = generate_signed_qr_token(
        event_id=event_id,
        student_id=top_waitlisted.student_id,
        email=top_waitlisted.student_email,
    )

    # Shift remaining waitlisted positions
    remaining_waitlist = db.query(Registration).filter(
        Registration.event_id == event_id,
        Registration.status == RegistrationStatus.WAITLISTED,
    ).order_by(Registration.waitlist_position.asc()).all()

    for idx, item in enumerate(remaining_waitlist, start=1):
        item.waitlist_position = idx

    db.commit()
    db.refresh(top_waitlisted)

    record_audit(
        db=db,
        agent_name=agent_name,
        tool_name="promote_waitlisted_participant",
        action_type="UPDATE_PROMOTION",
        payload={
            "promoted_id": top_waitlisted.id,
            "student_name": top_waitlisted.student_name,
            "new_qr_token": top_waitlisted.qr_token,
        },
        success=True,
        event_id=event_id,
    )

    return {
        "registration_id": top_waitlisted.id,
        "student_name": top_waitlisted.student_name,
        "student_email": top_waitlisted.student_email,
        "status": top_waitlisted.status.value,
        "qr_token": top_waitlisted.qr_token,
    }
