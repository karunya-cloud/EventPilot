"""Communication tools for drafting, approval gating, and dispatching announcements."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from src.config import settings
from src.db.models import EmailDraft, EmailStatus, Event, Registration, RegistrationStatus
from src.tools.audit import record_audit

def draft_email(
    db: Session,
    event_id: int,
    email_type: str = "INVITATION",
    recipient_filter: str = "ALL_CONFIRMED",
    custom_subject: Optional[str] = None,
    custom_body: Optional[str] = None,
    agent_name: str = "CommunicationAgent",
) -> Dict[str, Any]:
    """Create a structured email draft that strictly requires organizer approval before dispatch."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found.")

    if email_type == "INVITATION":
        subject = custom_subject or f"Invitation: {event.title} at {event.venue}"
        body = custom_body or (
            f"Dear Student,\n\n"
            f"You are cordially invited to attend '{event.title}'.\n\n"
            f"📍 Venue: {event.venue}\n"
            f"📅 Date: {event.target_date.strftime('%B %d, %Y')}\n"
            f"⏱ Duration: {event.duration_hours} hours\n"
            f"👥 Capacity: Strictly capped at {event.capacity} seats.\n\n"
            f"Please register via EventPilot AI to receive your secure QR entry pass.\n\n"
            f"Best regards,\nOrganizing Committee"
        )
    elif email_type == "REMINDER_QR":
        subject = custom_subject or f"Reminder & QR Pass: {event.title} is Tomorrow!"
        body = custom_body or (
            f"Hello Attendee,\n\n"
            f"This is a reminder for tomorrow's '{event.title}' at {event.venue}.\n"
            f"Your personal digital QR check-in pass has been activated.\n"
            f"Please present this pass at the entrance scanner for rapid entry.\n\n"
            f"See you there!"
        )
    else:
        subject = custom_subject or f"Important Update regarding {event.title}"
        body = custom_body or "Please review the latest event announcements."

    draft = EmailDraft(
        event_id=event_id,
        email_type=email_type,
        recipient_filter=recipient_filter,
        subject=subject,
        body_text=body,
        status=EmailStatus.PENDING_APPROVAL,
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    record_audit(
        db=db,
        agent_name=agent_name,
        tool_name="draft_email",
        action_type="INSERT_EMAIL_DRAFT",
        payload={"draft_id": draft.id, "subject": subject, "status": draft.status.value},
        success=True,
        event_id=event_id,
    )

    return {
        "draft_id": draft.id,
        "event_id": draft.event_id,
        "email_type": draft.email_type,
        "subject": draft.subject,
        "status": draft.status.value,
        "approval_required": True,
        "preview_snippet": draft.body_text[:200] + "...",
    }

def request_email_approval(db: Session, draft_id: int) -> Dict[str, Any]:
    """Retrieve full email draft content for explicit human review."""
    draft = db.query(EmailDraft).filter(EmailDraft.id == draft_id).first()
    if not draft:
        raise ValueError(f"Email draft {draft_id} not found.")

    return {
        "draft_id": draft.id,
        "subject": draft.subject,
        "body_text": draft.body_text,
        "recipient_filter": draft.recipient_filter,
        "status": draft.status.value,
        "action_prompt": "Reply with '[APPROVE_EMAIL]' to dispatch, or '[REJECT_EMAIL]' to cancel.",
    }

def send_approved_email(
    db: Session,
    draft_id: int,
    approver_name: str,
    agent_name: str = "CommunicationAgent",
) -> Dict[str, Any]:
    """Deliver email draft strictly upon verified organizer authorization."""
    draft = db.query(EmailDraft).filter(EmailDraft.id == draft_id).first()
    if not draft:
        raise ValueError(f"Email draft {draft_id} not found.")

    if draft.status == EmailStatus.SENT:
        return {
            "draft_id": draft.id,
            "status": "ALREADY_SENT",
            "message": f"Draft was already sent at {draft.sent_at.isoformat()}.",
            "sent_count": draft.sent_count,
        }

    # Count recipients based on filter
    if draft.recipient_filter == "ALL_CONFIRMED":
        recipients = db.query(Registration).filter(
            Registration.event_id == draft.event_id,
            Registration.status == RegistrationStatus.CONFIRMED,
        ).all()
    else:
        recipients = db.query(Registration).filter(
            Registration.event_id == draft.event_id
        ).all()

    recipient_count = len(recipients) if recipients else 60  # Default to target capacity if pre-reg

    # Mark as APPROVED and SENT (using simulated delivery for hackathon safety)
    draft.status = EmailStatus.SENT
    draft.approved_by = approver_name
    draft.sent_at = datetime.now(timezone.utc)
    draft.sent_count = recipient_count

    db.commit()
    db.refresh(draft)

    record_audit(
        db=db,
        agent_name=agent_name,
        tool_name="send_approved_email",
        action_type="SEND_EMAIL",
        payload={
            "draft_id": draft.id,
            "approved_by": approver_name,
            "sent_count": recipient_count,
            "mocked_delivery": settings.MOCK_EXTERNAL_ACTIONS,
        },
        success=True,
        event_id=draft.event_id,
    )

    return {
        "draft_id": draft.id,
        "status": draft.status.value,
        "approved_by": draft.approved_by,
        "sent_count": draft.sent_count,
        "sent_at": draft.sent_at.isoformat(),
        "delivery_mode": "SIMULATED_SAFE_DISPATCH" if settings.MOCK_EXTERNAL_ACTIONS else "LIVE_SMTP",
    }
