"""Communication Agent for EventPilot AI.
Prepares drafts, enforces approval gates, and coordinates message delivery.
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from datetime import datetime, timezone
from typing import Optional
from uagents import Agent, Context, Protocol
from src.config import settings
from src.agents.protocols import (
    PrepareEmailRequest,
    PrepareEmailResponse,
    SendApprovedEmailRequest,
    SendApprovedEmailResponse,
)
from src.db.session import SessionLocal
from src.tools.communication_tools import draft_email, send_approved_email

comm_protocol = Protocol(name="CommunicationProtocol", version="1.0.0")

@comm_protocol.on_message(PrepareEmailRequest)
async def handle_prepare_email(ctx: Context, sender: str, msg: PrepareEmailRequest):
    ctx.logger.info(f"[CommunicationAgent] Preparing {msg.email_type} draft for event {msg.event_id}")

    db = SessionLocal()
    try:
        draft = draft_email(
            db=db,
            event_id=msg.event_id,
            email_type=msg.email_type,
            agent_name="CommunicationAgent",
        )
        response = PrepareEmailResponse(
            correlation_id=msg.correlation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_id=msg.event_id,
            draft_id=draft["draft_id"],
            subject=draft["subject"],
            preview_body=draft["preview_snippet"],
            approval_required=True,
        )
        await ctx.send(sender, response)
    except Exception as e:
        ctx.logger.error(f"[CommunicationAgent] Error drafting email: {e}")
        await ctx.send(
            sender,
            PrepareEmailResponse(
                correlation_id=msg.correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_id=msg.event_id,
                draft_id=0,
                subject="Error",
                preview_body="Error",
                approval_required=True,
                error_message=str(e),
            ),
        )
    finally:
        db.close()

@comm_protocol.on_message(SendApprovedEmailRequest)
async def handle_send_approved(ctx: Context, sender: str, msg: SendApprovedEmailRequest):
    ctx.logger.info(f"[CommunicationAgent] Sending approved draft {msg.draft_id} authorized by {msg.approver_name}")

    db = SessionLocal()
    try:
        sent_info = send_approved_email(
            db=db,
            draft_id=msg.draft_id,
            approver_name=msg.approver_name,
            agent_name="CommunicationAgent",
        )
        response = SendApprovedEmailResponse(
            correlation_id=msg.correlation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            draft_id=msg.draft_id,
            sent_count=sent_info["sent_count"],
            status=sent_info["status"],
            delivery_timestamp=sent_info["sent_at"],
        )
        await ctx.send(sender, response)
    except Exception as e:
        ctx.logger.error(f"[CommunicationAgent] Error sending email: {e}")
        await ctx.send(
            sender,
            SendApprovedEmailResponse(
                correlation_id=msg.correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                draft_id=msg.draft_id,
                sent_count=0,
                status="FAILED",
                delivery_timestamp="",
                error_message=str(e),
            ),
        )
    finally:
        db.close()

def create_communication_agent(
    name: str = "eventpilot_communication",
    seed: Optional[str] = None,
    port: Optional[int] = None,
) -> Agent:
    agent = Agent(
        name=name,
        seed=seed or settings.COMMUNICATION_SEED,
        port=port or settings.COMMUNICATION_PORT,
        mailbox=False,
    )
    agent.include(comm_protocol)
    return agent

if __name__ == "__main__":
    agent = create_communication_agent()
    print(f"🚀 Communication Agent started at {agent.address}")
    agent.run()
