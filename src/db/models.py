"""SQLAlchemy ORM models for EventPilot AI."""
from datetime import datetime, timezone
import enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from src.db.session import Base

def utc_now():
    return datetime.now(timezone.utc)

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    ORGANIZER = "ORGANIZER"
    VOLUNTEER = "VOLUNTEER"
    ATTENDEE = "ATTENDEE"

class EventStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PROPOSED = "PROPOSED"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"

class TaskPriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RegistrationStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    WAITLISTED = "WAITLISTED"
    CANCELLED = "CANCELLED"

class ExpenseStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAID = "PAID"

class EmailStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SENT = "SENT"
    FAILED = "FAILED"

class RiskSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class RiskStatus(str, enum.Enum):
    DETECTED = "DETECTED"
    MITIGATED = "MITIGATED"
    DISMISSED = "DISMISSED"

# 1. Users
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    role = Column(SAEnum(UserRole), default=UserRole.ORGANIZER, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    memberships = relationship("EventMembership", back_populates="user", cascade="all, delete-orphan")

# 2. Events
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    target_date = Column(DateTime, nullable=False)
    duration_hours = Column(Float, default=4.0)
    timezone = Column(String(50), default="Asia/Kolkata")
    venue = Column(String(200), nullable=False)
    capacity = Column(Integer, nullable=False)
    budget = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    status = Column(SAEnum(EventStatus), default=EventStatus.DRAFT, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    tasks = relationship("Task", back_populates="event", cascade="all, delete-orphan")
    registrations = relationship("Registration", back_populates="event", cascade="all, delete-orphan")
    expenses = relationship("Expense", back_populates="event", cascade="all, delete-orphan")
    allocations = relationship("EquipmentAllocation", back_populates="event", cascade="all, delete-orphan")
    emails = relationship("EmailDraft", back_populates="event", cascade="all, delete-orphan")
    risk_alerts = relationship("RiskAlert", back_populates="event", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="event", cascade="all, delete-orphan")

# 3. Event Memberships
class EventMembership(Base):
    __tablename__ = "event_memberships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), default="ORGANIZER")

    user = relationship("User", back_populates="memberships")
    __table_args__ = (UniqueConstraint("event_id", "user_id", name="uq_event_user_membership"),)

# 4. Tasks & Dependencies
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    assigned_to = Column(String(100), default="Unassigned")
    due_date = Column(DateTime, nullable=False)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    priority = Column(SAEnum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    event = relationship("Event", back_populates="tasks")
    dependencies = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan",
    )

class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    depends_on_task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)

    task = relationship("Task", foreign_keys=[task_id], back_populates="dependencies")
    depends_on = relationship("Task", foreign_keys=[depends_on_task_id])

    __table_args__ = (UniqueConstraint("task_id", "depends_on_task_id", name="uq_task_dependency"),)

# 5. Registrations & Attendance
class Registration(Base):
    __tablename__ = "registrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    student_name = Column(String(100), nullable=False)
    student_email = Column(String(150), nullable=False, index=True)
    student_id = Column(String(50), nullable=False)
    status = Column(SAEnum(RegistrationStatus), default=RegistrationStatus.CONFIRMED, nullable=False)
    waitlist_position = Column(Integer, nullable=True)
    qr_token = Column(String(255), unique=True, nullable=False, index=True)
    registered_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    event = relationship("Event", back_populates="registrations")
    attendance = relationship("AttendanceRecord", back_populates="registration", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("event_id", "student_email", name="uq_event_student_email"),)

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    registration_id = Column(Integer, ForeignKey("registrations.id", ondelete="CASCADE"), unique=True, nullable=False)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    checked_in_at = Column(DateTime, default=utc_now)
    device_id = Column(String(100), default="GATE_SCANNER_1")
    is_duplicate_attempt = Column(Boolean, default=False)

    registration = relationship("Registration", back_populates="attendance")

# 6. Inventory & Allocations
class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(150), unique=True, nullable=False, index=True)
    category = Column(String(100), default="Hardware")
    total_quantity = Column(Integer, nullable=False)
    available_quantity = Column(Integer, nullable=False)
    unit_cost = Column(Float, default=0.0)
    location = Column(String(100), default="Central Hardware Depot")
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    allocations = relationship("EquipmentAllocation", back_populates="item")

class EquipmentAllocation(Base):
    __tablename__ = "equipment_allocations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    inventory_item_id = Column(Integer, ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False)
    quantity_allocated = Column(Integer, nullable=False)
    allocation_status = Column(String(50), default="RESERVED")
    created_at = Column(DateTime, default=utc_now)

    event = relationship("Event", back_populates="allocations")
    item = relationship("InventoryItem", back_populates="allocations")

# 7. Expenses & Budget Approvals
class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(100), default="General")
    description = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(SAEnum(ExpenseStatus), default=ExpenseStatus.PENDING, nullable=False)
    approved_by = Column(String(100), nullable=True)
    receipt_ref = Column(String(100), nullable=True)
    idempotency_key = Column(String(100), unique=True, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    event = relationship("Event", back_populates="expenses")

# 8. Communication & Email Drafts
class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    email_type = Column(String(50), default="INVITATION")
    recipient_filter = Column(String(100), default="ALL_CONFIRMED")
    subject = Column(String(255), nullable=False)
    body_text = Column(Text, nullable=False)
    status = Column(SAEnum(EmailStatus), default=EmailStatus.PENDING_APPROVAL, nullable=False)
    approved_by = Column(String(100), nullable=True)
    sent_at = Column(DateTime, nullable=True)
    sent_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)

    event = relationship("Event", back_populates="emails")

# 9. Risk Alerts & Mitigation Plans
class RiskAlert(Base):
    __tablename__ = "risk_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    risk_type = Column(String(100), nullable=False)
    severity = Column(SAEnum(RiskSeverity), default=RiskSeverity.HIGH, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(SAEnum(RiskStatus), default=RiskStatus.DETECTED, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    event = relationship("Event", back_populates="risk_alerts")
    mitigation_plans = relationship("MitigationPlan", back_populates="alert", cascade="all, delete-orphan")

class MitigationPlan(Base):
    __tablename__ = "mitigation_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    risk_alert_id = Column(Integer, ForeignKey("risk_alerts.id", ondelete="CASCADE"), nullable=False)
    option_key = Column(String(10), nullable=False)  # A, B, C
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    estimated_cost = Column(Float, default=0.0)
    is_chosen = Column(Boolean, default=False)
    chosen_at = Column(DateTime, nullable=True)

    alert = relationship("RiskAlert", back_populates="mitigation_plans")

# 10. Audit Logs
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="SET NULL"), nullable=True)
    agent_name = Column(String(100), nullable=False)
    tool_name = Column(String(100), nullable=False)
    action_type = Column(String(50), nullable=False)
    payload_summary = Column(Text, nullable=True)
    success = Column(Boolean, default=True)
    idempotency_key = Column(String(120), nullable=True)
    timestamp = Column(DateTime, default=utc_now)

    event = relationship("Event", back_populates="audit_logs")

# 11. Historical Event Metrics
class HistoricalEventMetric(Base):
    __tablename__ = "historical_event_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_title = Column(String(200), nullable=False)
    event_type = Column(String(100), default="Robotics Workshop")
    attendee_count = Column(Integer, nullable=False)
    budget_allocated = Column(Float, nullable=False)
    budget_spent = Column(Float, nullable=False)
    kits_used = Column(Integer, nullable=False)
    turnout_percentage = Column(Float, default=100.0)
    key_takeaways = Column(Text, nullable=True)
    recorded_at = Column(DateTime, default=utc_now)
