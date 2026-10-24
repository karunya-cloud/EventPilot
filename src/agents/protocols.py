"""Inter-agent communication protocol models and message schemas."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
from uagents import Model

class BaseAgentMessage(Model):
    """Base message containing tracing correlation ID and timestamp."""
    correlation_id: str
    timestamp: str

    @classmethod
    def create(cls, **kwargs):
        if "correlation_id" not in kwargs:
            kwargs["correlation_id"] = str(uuid4())
        if "timestamp" not in kwargs:
            kwargs["timestamp"] = datetime.now(timezone.utc).isoformat()
        return cls(**kwargs)

# Planning Agent Schemas
class PlanEventRequest(BaseAgentMessage):
    event_id: Optional[int] = None
    title: str
    target_date: str
    capacity: int
    duration_hours: float
    venue: str

class TaskItem(Model):
    title: str
    description: str
    assigned_to: str
    estimated_hours: float
    dependencies: List[str] = []

class PlanEventResponse(BaseAgentMessage):
    event_id: Optional[int] = None
    success: bool
    tasks: List[TaskItem] = []
    error_message: Optional[str] = None

# Logistics Agent Schemas
class CheckLogisticsRequest(BaseAgentMessage):
    event_id: int
    required_item_name: str
    required_quantity: int
    budget_limit: float

class CheckLogisticsResponse(BaseAgentMessage):
    event_id: int
    item_name: str
    required_quantity: int
    available_quantity: int
    shortage: int
    is_sufficient: bool
    current_expenses: float
    budget_remaining: float
    error_message: Optional[str] = None

# Risk Agent Schemas
class AssessRiskRequest(BaseAgentMessage):
    event_id: int
    item_name: str
    required_quantity: int
    available_quantity: int
    budget_remaining: float

class MitigationOption(Model):
    option_id: str
    name: str
    description: str
    estimated_cost: float
    feasibility: str

class AssessRiskResponse(BaseAgentMessage):
    event_id: int
    shortage: int
    risk_level: str  # LOW, MEDIUM, CRITICAL
    mitigation_options: List[MitigationOption] = []
    error_message: Optional[str] = None

# Communication Agent Schemas
class PrepareEmailRequest(BaseAgentMessage):
    event_id: int
    email_type: str  # INVITATION, REMINDER, ANNOUNCEMENT
    recipient_count: int
    event_details: Dict[str, Any] = {}

class PrepareEmailResponse(BaseAgentMessage):
    event_id: int
    draft_id: int
    subject: str
    preview_body: str
    approval_required: bool = True
    error_message: Optional[str] = None

class SendApprovedEmailRequest(BaseAgentMessage):
    draft_id: int
    approver_name: str

class SendApprovedEmailResponse(BaseAgentMessage):
    draft_id: int
    sent_count: int
    status: str
    delivery_timestamp: str
    error_message: Optional[str] = None

# Registration Agent Schemas
class ProcessRegistrationRequest(BaseAgentMessage):
    event_id: int
    participant_name: str
    participant_email: str
    student_id: str

class ProcessRegistrationResponse(BaseAgentMessage):
    event_id: int
    registration_id: Optional[int] = None
    status: str  # CONFIRMED, WAITLISTED, REJECTED
    qr_token: Optional[str] = None
    error_message: Optional[str] = None
