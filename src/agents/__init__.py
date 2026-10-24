"""EventPilot AI Agents Package."""
from src.agents.protocols import (
    BaseAgentMessage,
    PlanEventRequest,
    PlanEventResponse,
    CheckLogisticsRequest,
    CheckLogisticsResponse,
    AssessRiskRequest,
    AssessRiskResponse,
    PrepareEmailRequest,
    PrepareEmailResponse,
    SendApprovedEmailRequest,
    SendApprovedEmailResponse,
    ProcessRegistrationRequest,
    ProcessRegistrationResponse,
)
from src.agents.coordinator import create_coordinator_agent, process_coordinator_turn
from src.agents.planning_agent import create_planning_agent
from src.agents.logistics_agent import create_logistics_agent
from src.agents.risk_agent import create_risk_agent
from src.agents.communication_agent import create_communication_agent
from src.agents.registration_agent import create_registration_agent
