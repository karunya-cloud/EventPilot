"""Registration Agent for EventPilot AI.
Enforces capacity quotas, waitlist ordering, duplicate rejection, and QR token issuance.
"""
from datetime import datetime, timezone
from typing import Optional
from uagents import Agent, Context, Protocol
from src.config import settings
from src.agents.protocols import (
    ProcessRegistrationRequest,
    ProcessRegistrationResponse,
)
from src.db.session import SessionLocal
from src.tools.registration_tools import register_participant

registration_protocol = Protocol(name="RegistrationProtocol", version="1.0.0")

@registration_protocol.on_message(ProcessRegistrationRequest)
async def handle_registration(ctx: Context, sender: str, msg: ProcessRegistrationRequest):
    ctx.logger.info(f"[RegistrationAgent] Processing registration for '{msg.participant_name}' ({msg.participant_email})")

    db = SessionLocal()
    try:
        reg_info = register_participant(
            db=db,
            event_id=msg.event_id,
            student_name=msg.participant_name,
            student_email=msg.participant_email,
            student_id=msg.student_id,
            agent_name="RegistrationAgent",
        )
        response = ProcessRegistrationResponse(
            correlation_id=msg.correlation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_id=msg.event_id,
            registration_id=reg_info["registration_id"],
            status=reg_info["status"],
            qr_token=reg_info["qr_token"],
        )
        await ctx.send(sender, response)
    except Exception as e:
        ctx.logger.error(f"[RegistrationAgent] Registration error: {e}")
        await ctx.send(
            sender,
            ProcessRegistrationResponse(
                correlation_id=msg.correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_id=msg.event_id,
                registration_id=None,
                status="REJECTED",
                qr_token=None,
                error_message=str(e),
            ),
        )
    finally:
        db.close()

def create_registration_agent(
    name: str = "eventpilot_registration",
    seed: Optional[str] = None,
    port: Optional[int] = None,
) -> Agent:
    agent = Agent(
        name=name,
        seed=seed or settings.REGISTRATION_SEED,
        port=port or settings.REGISTRATION_PORT,
        mailbox=False,
    )
    agent.include(registration_protocol)
    return agent

if __name__ == "__main__":
    agent = create_registration_agent()
    print(f"🚀 Registration Agent started at {agent.address}")
    agent.run()
