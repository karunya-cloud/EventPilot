"""Planning Agent for EventPilot AI.
Handles schedule requirements, milestone creation, and DAG task dependencies.
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
    PlanEventRequest,
    PlanEventResponse,
    TaskItem,
)
from src.db.session import SessionLocal
from src.tools.task_tools import generate_timeline

planning_protocol = Protocol(name="PlanningProtocol", version="1.0.0")

@planning_protocol.on_message(PlanEventRequest)
async def handle_plan_event(ctx: Context, sender: str, msg: PlanEventRequest):
    ctx.logger.info(f"[PlanningAgent] Received event plan request for '{msg.title}' (Correlation: {msg.correlation_id})")

    if not msg.event_id:
        await ctx.send(
            sender,
            PlanEventResponse(
                correlation_id=msg.correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_id=None,
                success=False,
                tasks=[],
                error_message="Event ID must be provided to generate timeline.",
            ),
        )
        return

    db = SessionLocal()
    try:
        tasks = generate_timeline(db, msg.event_id, agent_name="PlanningAgent")
        task_items = [
            TaskItem(
                title=t["title"],
                description=f"Due: {t['due_date']} (Priority: {t['priority']})",
                assigned_to=t["assigned_to"],
                estimated_hours=4.0,
                dependencies=[],
            )
            for t in tasks
        ]

        response = PlanEventResponse(
            correlation_id=msg.correlation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_id=msg.event_id,
            success=True,
            tasks=task_items,
        )
        await ctx.send(sender, response)
    except Exception as e:
        ctx.logger.error(f"[PlanningAgent] Error generating timeline: {e}")
        await ctx.send(
            sender,
            PlanEventResponse(
                correlation_id=msg.correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_id=msg.event_id,
                success=False,
                tasks=[],
                error_message=str(e),
            ),
        )
    finally:
        db.close()

def create_planning_agent(
    name: str = "eventpilot_planning",
    seed: Optional[str] = None,
    port: Optional[int] = None,
) -> Agent:
    agent = Agent(
        name=name,
        seed=seed or settings.PLANNING_SEED,
        port=port or settings.PLANNING_PORT,
        mailbox=False,
    )
    agent.include(planning_protocol)
    return agent

if __name__ == "__main__":
    agent = create_planning_agent()
    print(f"🚀 Planning Agent started at {agent.address}")
    agent.run()
