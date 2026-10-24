"""Task and timeline management tools with DAG dependency tracking."""
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from src.db.models import Task, TaskDependency, TaskStatus, TaskPriority, Event
from src.tools.audit import record_audit

def generate_timeline(
    db: Session,
    event_id: int,
    agent_name: str = "PlanningAgent",
) -> List[Dict[str, Any]]:
    """Generate a milestone timeline with explicit DAG dependencies."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise ValueError(f"Event {event_id} not found.")

    target = event.target_date

    # Define standard milestones backwards from target date
    milestones = [
        {
            "key": "t1_venue",
            "title": "Confirm Venue Readiness & Power Outlets",
            "description": f"Verify capacity for {event.capacity} students and sufficient 220V power strips in {event.venue}.",
            "days_before": 14,
            "priority": TaskPriority.HIGH,
            "assigned_to": "Alex Rivera (Logistics)",
            "depends_on": [],
        },
        {
            "key": "t2_inventory",
            "title": "Audit & Allocate Robotics Hardware Kits",
            "description": f"Verify inventory counts for {event.capacity} students and flag any kit deficits.",
            "days_before": 10,
            "priority": TaskPriority.CRITICAL,
            "assigned_to": "Alex Rivera (Logistics)",
            "depends_on": ["t1_venue"],
        },
        {
            "key": "t3_registration",
            "title": "Open Registration Portal with Strict Capacity & Waitlist",
            "description": f"Enforce maximum cap of {event.capacity} with automated waitlist.",
            "days_before": 8,
            "priority": TaskPriority.HIGH,
            "assigned_to": "Sarah Chen (Registration)",
            "depends_on": [],
        },
        {
            "key": "t4_invitations",
            "title": "Draft & Approve Attendee Invitations",
            "description": "Prepare announcement copy and obtain organizer approval before dispatch.",
            "days_before": 7,
            "priority": TaskPriority.MEDIUM,
            "assigned_to": "Sarah Chen (Registration)",
            "depends_on": ["t3_registration"],
        },
        {
            "key": "t5_qa",
            "title": "Pre-Workshop Hardware QA & Flash Firmware",
            "description": "Test sensors, servos, and microcontrollers to ensure 100% operational readiness.",
            "days_before": 3,
            "priority": TaskPriority.HIGH,
            "assigned_to": "Alex Rivera (Logistics)",
            "depends_on": ["t2_inventory"],
        },
        {
            "key": "t6_reminders",
            "title": "Send Reminder Broadcast & Digital QR Check-In Passes",
            "description": "Issue cryptographic QR codes to confirmed attendees with venue directions.",
            "days_before": 1,
            "priority": TaskPriority.HIGH,
            "assigned_to": "Sarah Chen (Registration)",
            "depends_on": ["t4_invitations"],
        },
        {
            "key": "t7_event_day",
            "title": "Event Execution: Live Lab & Real-Time Attendance Check-In",
            "description": "Conduct participant check-in and oversee hands-on robotics building.",
            "days_before": 0,
            "priority": TaskPriority.CRITICAL,
            "assigned_to": "Lead Organizer",
            "depends_on": ["t5_qa", "t6_reminders"],
        },
    ]

    created_tasks: Dict[str, Task] = {}
    created_list = []

    for m in milestones:
        due = target - timedelta(days=m["days_before"])
        task = Task(
            event_id=event.id,
            title=m["title"],
            description=m["description"],
            assigned_to=m["assigned_to"],
            due_date=due,
            status=TaskStatus.PENDING,
            priority=m["priority"],
        )
        db.add(task)
        db.flush()  # to obtain task.id
        created_tasks[m["key"]] = task

    # Wire DAG dependencies
    for m in milestones:
        current_task = created_tasks[m["key"]]
        for parent_key in m["depends_on"]:
            parent_task = created_tasks[parent_key]
            dep = TaskDependency(task_id=current_task.id, depends_on_task_id=parent_task.id)
            db.add(dep)

    db.commit()

    for key, task in created_tasks.items():
        created_list.append({
            "task_id": task.id,
            "title": task.title,
            "assigned_to": task.assigned_to,
            "due_date": task.due_date.isoformat(),
            "priority": task.priority.value,
            "status": task.status.value,
        })

    record_audit(
        db=db,
        agent_name=agent_name,
        tool_name="generate_timeline",
        action_type="INSERT_TIMELINE",
        payload={"event_id": event_id, "tasks_created": len(created_list)},
        success=True,
        event_id=event_id,
    )

    return created_list

def create_task(
    db: Session,
    event_id: int,
    title: str,
    due_date: datetime,
    assigned_to: str = "Unassigned",
    description: Optional[str] = None,
    priority: TaskPriority = TaskPriority.MEDIUM,
    depends_on_task_ids: Optional[List[int]] = None,
    agent_name: str = "PlanningAgent",
) -> Dict[str, Any]:
    """Create a single task with optional dependencies."""
    task = Task(
        event_id=event_id,
        title=title,
        description=description,
        assigned_to=assigned_to,
        due_date=due_date,
        priority=priority,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    db.flush()

    if depends_on_task_ids:
        for parent_id in depends_on_task_ids:
            dep = TaskDependency(task_id=task.id, depends_on_task_id=parent_id)
            db.add(dep)

    db.commit()
    db.refresh(task)

    record_audit(
        db=db,
        agent_name=agent_name,
        tool_name="create_task",
        action_type="INSERT",
        payload={"task_id": task.id, "title": title, "assigned_to": assigned_to},
        success=True,
        event_id=event_id,
    )

    return {
        "task_id": task.id,
        "title": task.title,
        "assigned_to": task.assigned_to,
        "due_date": task.due_date.isoformat(),
        "status": task.status.value,
        "priority": task.priority.value,
    }

def update_task(
    db: Session,
    task_id: int,
    status: Optional[TaskStatus] = None,
    assigned_to: Optional[str] = None,
    due_date: Optional[datetime] = None,
    agent_name: str = "PlanningAgent",
) -> Dict[str, Any]:
    """Update task progress, assignee, or deadline."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError(f"Task {task_id} not found.")

    if status:
        # Check if parent dependencies are completed before completing task
        if status == TaskStatus.COMPLETED:
            for dep in task.dependencies:
                parent = db.query(Task).filter(Task.id == dep.depends_on_task_id).first()
                if parent and parent.status != TaskStatus.COMPLETED:
                    task.status = TaskStatus.BLOCKED
                    db.commit()
                    raise ValueError(
                        f"Cannot complete task '{task.title}': Parent dependency '{parent.title}' is still {parent.status.value}."
                    )
        task.status = status

    if assigned_to:
        task.assigned_to = assigned_to
    if due_date:
        task.due_date = due_date

    db.commit()
    db.refresh(task)

    record_audit(
        db=db,
        agent_name=agent_name,
        tool_name="update_task",
        action_type="UPDATE",
        payload={"task_id": task.id, "new_status": task.status.value, "assigned_to": task.assigned_to},
        success=True,
        event_id=task.event_id,
    )

    return {
        "task_id": task.id,
        "title": task.title,
        "status": task.status.value,
        "assigned_to": task.assigned_to,
        "due_date": task.due_date.isoformat(),
    }

def list_overdue_tasks(db: Session, event_id: int) -> List[Dict[str, Any]]:
    """List all non-completed tasks past their due date."""
    now = datetime.now(timezone.utc)
    overdue = db.query(Task).filter(
        Task.event_id == event_id,
        Task.due_date < now,
        Task.status != TaskStatus.COMPLETED,
    ).all()

    return [
        {
            "task_id": t.id,
            "title": t.title,
            "due_date": t.due_date.isoformat(),
            "assigned_to": t.assigned_to,
            "priority": t.priority.value,
            "status": t.status.value,
        }
        for t in overdue
    ]
