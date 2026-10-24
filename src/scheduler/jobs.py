"""Background job scheduler for deadline monitoring and risk alerts."""
import logging
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from src.db.session import SessionLocal
from src.db.models import Task, TaskStatus, Event, EventStatus
from src.tools.logistics_tools import check_resource_shortages
from src.tools.risk_tools import detect_risks

logger = logging.getLogger("eventpilot.scheduler")

def audit_overdue_tasks():
    """Periodic audit for overdue tasks across all active events."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        overdue = db.query(Task).filter(
            Task.due_date < now,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
        ).all()
        if overdue:
            logger.warning(f"[SCHEDULER] Detected {len(overdue)} overdue tasks!")
            for t in overdue:
                logger.warning(f"  • Task #{t.id} '{t.title}' assigned to {t.assigned_to} was due at {t.due_date.isoformat()}")
    except Exception as e:
        logger.error(f"[SCHEDULER ERROR] Error in audit_overdue_tasks: {e}")
    finally:
        db.close()

def audit_equipment_reservations():
    """Periodic check to ensure all upcoming events have verified kit allocations."""
    db = SessionLocal()
    try:
        active_events = db.query(Event).filter(
            Event.status.in_([EventStatus.PROPOSED, EventStatus.CONFIRMED])
        ).all()
        for ev in active_events:
            risks = detect_risks(db, ev.id, "Robotics Hardware Kit", ev.capacity, agent_name="BackgroundScheduler")
            if risks:
                logger.warning(f"[SCHEDULER] Active risk for event #{ev.id} '{ev.title}': {len(risks)} alerts.")
    except Exception as e:
        logger.error(f"[SCHEDULER ERROR] Error in audit_equipment_reservations: {e}")
    finally:
        db.close()

def create_scheduler() -> BackgroundScheduler:
    """Initialize and configure APScheduler."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(audit_overdue_tasks, "interval", minutes=15, id="audit_overdue_tasks")
    scheduler.add_job(audit_equipment_reservations, "interval", minutes=30, id="audit_equipment")
    return scheduler

if __name__ == "__main__":
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("Background scheduler running. Press Ctrl+C to exit.")
    try:
        import time
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
