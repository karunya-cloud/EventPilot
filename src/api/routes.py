"""FastAPI REST routes for EventPilot AI.
Provides RESTful endpoints for organizers, scanners, and external dashboards.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.db.models import InventoryItem, TaskStatus, TaskPriority
from src.tools import (
    create_event,
    get_event,
    get_dashboard_summary,
    retrieve_historical_event_metrics,
    generate_timeline,
    create_task,
    update_task,
    list_overdue_tasks,
    register_participant,
    cancel_registration,
    promote_waitlisted_participant,
    check_in_attendee,
    generate_attendance_report,
    check_resource_shortages,
    update_inventory,
    record_expense,
    calculate_budget,
    detect_risks,
    apply_approved_mitigation,
    draft_email,
    send_approved_email,
)

router = APIRouter(prefix="/api")

# Pydantic Schemas for Request Bodies
class CreateEventSchema(BaseModel):
    title: str = Field(..., json_schema_extra={"example": "Advanced Autonomous Robotics Workshop"})
    target_date: datetime = Field(..., json_schema_extra={"example": "2026-11-15T10:00:00Z"})
    venue: str = Field(..., json_schema_extra={"example": "Robotics Lab 3, Engineering Block"})
    capacity: int = Field(60, ge=1)
    budget: float = Field(20000.0, ge=0.0)
    duration_hours: float = 4.0
    timezone_str: str = "Asia/Kolkata"

class CreateTaskSchema(BaseModel):
    event_id: int
    title: str
    due_date: datetime
    assigned_to: str = "Unassigned"
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    depends_on_task_ids: Optional[List[int]] = None

class UpdateTaskSchema(BaseModel):
    status: Optional[TaskStatus] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None

class RegisterParticipantSchema(BaseModel):
    student_name: str
    student_email: str
    student_id: str

class CheckInSchema(BaseModel):
    qr_token: str
    device_id: str = "SCANNER_API_DEVICE"

class MitigateSchema(BaseModel):
    chosen_option_key: str
    approver_name: str = "Lead Organizer"

class SendEmailSchema(BaseModel):
    approver_name: str = "Lead Organizer"

# Event Endpoints
@router.post("/events")
def api_create_event(data: CreateEventSchema, db: Session = Depends(get_db)):
    try:
        return create_event(
            db=db,
            title=data.title,
            target_date=data.target_date,
            venue=data.venue,
            capacity=data.capacity,
            budget=data.budget,
            duration_hours=data.duration_hours,
            timezone_str=data.timezone_str,
            agent_name="REST_API",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/events/{event_id}")
def api_get_event(event_id: int, db: Session = Depends(get_db)):
    ev = get_event(db, event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev

@router.get("/events/{event_id}/dashboard")
def api_get_dashboard(event_id: int, db: Session = Depends(get_db)):
    try:
        return get_dashboard_summary(db, event_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/events/{event_id}/timeline")
def api_generate_timeline(event_id: int, db: Session = Depends(get_db)):
    try:
        return generate_timeline(db, event_id, agent_name="REST_API")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Task Endpoints
@router.post("/tasks")
def api_create_task(data: CreateTaskSchema, db: Session = Depends(get_db)):
    return create_task(
        db=db,
        event_id=data.event_id,
        title=data.title,
        due_date=data.due_date,
        assigned_to=data.assigned_to,
        description=data.description,
        priority=data.priority,
        depends_on_task_ids=data.depends_on_task_ids,
        agent_name="REST_API",
    )

@router.patch("/tasks/{task_id}")
def api_update_task(task_id: int, data: UpdateTaskSchema, db: Session = Depends(get_db)):
    try:
        return update_task(
            db=db,
            task_id=task_id,
            status=data.status,
            assigned_to=data.assigned_to,
            due_date=data.due_date,
            agent_name="REST_API",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Registration Endpoints
@router.post("/events/{event_id}/registrations")
def api_register_participant(event_id: int, data: RegisterParticipantSchema, db: Session = Depends(get_db)):
    try:
        return register_participant(
            db=db,
            event_id=event_id,
            student_name=data.student_name,
            student_email=data.student_email,
            student_id=data.student_id,
            agent_name="REST_API",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/registrations/{registration_id}")
def api_cancel_registration(registration_id: int, db: Session = Depends(get_db)):
    try:
        return cancel_registration(db, registration_id, agent_name="REST_API")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# Attendance & Check-In Endpoints
@router.post("/attendance/checkin")
def api_check_in(data: CheckInSchema, db: Session = Depends(get_db)):
    result = check_in_attendee(
        db=db,
        qr_token=data.qr_token,
        device_id=data.device_id,
        agent_name="REST_API",
    )
    if not result.get("success") and not result.get("is_duplicate_attempt"):
        raise HTTPException(status_code=400, detail=result.get("error", "Check-in failed"))
    return result

@router.get("/events/{event_id}/attendance/report")
def api_attendance_report(event_id: int, db: Session = Depends(get_db)):
    try:
        return generate_attendance_report(db, event_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# Risk & Logistics Endpoints
@router.get("/events/{event_id}/risks")
def api_detect_risks(event_id: int, required_item: str = "Robotics Hardware Kit", db: Session = Depends(get_db)):
    try:
        return detect_risks(db, event_id, required_item_name=required_item, agent_name="REST_API")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/risks/{risk_alert_id}/mitigate")
def api_mitigate_risk(risk_alert_id: int, data: MitigateSchema, db: Session = Depends(get_db)):
    try:
        return apply_approved_mitigation(
            db=db,
            risk_alert_id=risk_alert_id,
            chosen_option_key=data.chosen_option_key,
            approver_name=data.approver_name,
            agent_name="REST_API",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Email Endpoints
@router.post("/emails/{draft_id}/send")
def api_send_approved_email(draft_id: int, data: SendEmailSchema, db: Session = Depends(get_db)):
    try:
        return send_approved_email(
            db=db,
            draft_id=draft_id,
            approver_name=data.approver_name,
            agent_name="REST_API",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# Inventory & Historical Metrics
@router.get("/inventory")
def api_get_inventory(db: Session = Depends(get_db)):
    items = db.query(InventoryItem).all()
    return [
        {
            "id": i.id,
            "name": i.name,
            "category": i.category,
            "total_quantity": i.total_quantity,
            "available_quantity": i.available_quantity,
            "unit_cost": i.unit_cost,
            "location": i.location,
        }
        for i in items
    ]

@router.get("/historical-metrics")
def api_historical_metrics(limit: int = 5, db: Session = Depends(get_db)):
    return retrieve_historical_event_metrics(db, limit=limit)
