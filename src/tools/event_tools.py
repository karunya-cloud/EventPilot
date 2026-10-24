"""Event management tools for EventPilot AI."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from src.db.models import (
    Event,
    EventStatus,
    Registration,
    RegistrationStatus,
    Task,
    TaskStatus,
    Expense,
    ExpenseStatus,
    InventoryItem,
    EquipmentAllocation,
    HistoricalEventMetric,
)
from src.tools.audit import record_audit

def create_event(
    db: Session,
    title: str,
    target_date: datetime,
    venue: str,
    capacity: int,
    budget: float,
    duration_hours: float = 4.0,
    timezone_str: str = "Asia/Kolkata",
    description: Optional[str] = None,
    agent_name: str = "CoordinatorAgent",
) -> Dict[str, Any]:
    """Create a new validated event and persist to database."""
    if capacity <= 0:
        raise ValueError("Capacity must be a positive integer.")
    if budget < 0:
        raise ValueError("Budget cannot be negative.")
    if target_date <= datetime.now(timezone.utc):
        raise ValueError("Target date must be in the future.")

    event = Event(
        title=title,
        description=description or f"{title} organized via EventPilot AI",
        target_date=target_date,
        duration_hours=duration_hours,
        timezone=timezone_str,
        venue=venue,
        capacity=capacity,
        budget=budget,
        currency="INR",
        status=EventStatus.PROPOSED,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    record_audit(
        db=db,
        agent_name=agent_name,
        tool_name="create_event",
        action_type="INSERT",
        payload={"event_id": event.id, "title": title, "capacity": capacity, "budget": budget},
        success=True,
        event_id=event.id,
    )

    return {
        "event_id": event.id,
        "title": event.title,
        "target_date": event.target_date.isoformat(),
        "venue": event.venue,
        "capacity": event.capacity,
        "budget": event.budget,
        "status": event.status.value,
    }

def get_event(db: Session, event_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve full event details and metadata."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        return None
    
    confirmed_regs = db.query(Registration).filter(
        Registration.event_id == event_id,
        Registration.status == RegistrationStatus.CONFIRMED,
    ).count()
    
    waitlist_regs = db.query(Registration).filter(
        Registration.event_id == event_id,
        Registration.status == RegistrationStatus.WAITLISTED,
    ).count()

    return {
        "event_id": event.id,
        "title": event.title,
        "description": event.description,
        "target_date": event.target_date.isoformat(),
        "duration_hours": event.duration_hours,
        "timezone": event.timezone,
        "venue": event.venue,
        "capacity": event.capacity,
        "budget": event.budget,
        "currency": event.currency,
        "status": event.status.value,
        "confirmed_registrations": confirmed_regs,
        "waitlisted_registrations": waitlist_regs,
    }

def get_dashboard_summary(db: Session, event_id: int) -> Dict[str, Any]:
    """Compile comprehensive live operational dashboard metrics for an event."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event with id {event_id} not found.")

    confirmed_count = db.query(Registration).filter(
        Registration.event_id == event_id,
        Registration.status == RegistrationStatus.CONFIRMED,
    ).count()

    waitlist_count = db.query(Registration).filter(
        Registration.event_id == event_id,
        Registration.status == RegistrationStatus.WAITLISTED,
    ).count()

    tasks = db.query(Task).filter(Task.event_id == event_id).all()
    completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
    total_tasks = len(tasks)

    expenses = db.query(Expense).filter(
        Expense.event_id == event_id,
        Expense.status.in_([ExpenseStatus.APPROVED, ExpenseStatus.PAID]),
    ).all()
    total_spent = sum(e.amount for e in expenses)
    remaining_budget = event.budget - total_spent

    allocations = db.query(EquipmentAllocation).filter(
        EquipmentAllocation.event_id == event_id
    ).all()
    equipment_summary = [
        {"item_id": a.inventory_item_id, "allocated": a.quantity_allocated, "status": a.allocation_status}
        for a in allocations
    ]

    return {
        "event_id": event.id,
        "title": event.title,
        "target_date": event.target_date.isoformat(),
        "status": event.status.value,
        "capacity": event.capacity,
        "confirmed_attendees": confirmed_count,
        "waitlist_count": waitlist_count,
        "capacity_utilization_pct": round((confirmed_count / event.capacity) * 100, 1) if event.capacity > 0 else 0,
        "budget_total": event.budget,
        "budget_spent": total_spent,
        "budget_remaining": remaining_budget,
        "tasks_total": total_tasks,
        "tasks_completed": completed_tasks,
        "equipment_allocations": equipment_summary,
    }

def retrieve_historical_event_metrics(db: Session, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve historical benchmarks for grounded planning estimates."""
    metrics = db.query(HistoricalEventMetric).order_by(
        HistoricalEventMetric.recorded_at.desc()
    ).limit(limit).all()

    return [
        {
            "event_title": m.event_title,
            "event_type": m.event_type,
            "attendees": m.attendee_count,
            "budget_spent": m.budget_spent,
            "kits_used": m.kits_used,
            "turnout_pct": m.turnout_percentage,
            "key_takeaways": m.key_takeaways,
        }
        for m in metrics
    ]
