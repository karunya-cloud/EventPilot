"""Logistics Agent for EventPilot AI.
Monitors inventory availability, venue readiness, and budget ledgers.
"""
from datetime import datetime, timezone
from typing import Optional
from uagents import Agent, Context, Protocol
from src.config import settings
from src.agents.protocols import (
    CheckLogisticsRequest,
    CheckLogisticsResponse,
)
from src.db.session import SessionLocal
from src.tools.logistics_tools import check_resource_shortages, calculate_budget

logistics_protocol = Protocol(name="LogisticsProtocol", version="1.0.0")

@logistics_protocol.on_message(CheckLogisticsRequest)
async def handle_logistics_check(ctx: Context, sender: str, msg: CheckLogisticsRequest):
    ctx.logger.info(f"[LogisticsAgent] Checking logistics for event {msg.event_id} (Item: {msg.required_item_name})")
    
    db = SessionLocal()
    try:
        shortage_info = check_resource_shortages(
            db=db,
            event_id=msg.event_id,
            item_name=msg.required_item_name,
            required_quantity=msg.required_quantity,
            agent_name="LogisticsAgent",
        )
        budget_info = calculate_budget(db, msg.event_id)

        response = CheckLogisticsResponse(
            correlation_id=msg.correlation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_id=msg.event_id,
            item_name=shortage_info["item_name"],
            required_quantity=shortage_info["required_quantity"],
            available_quantity=shortage_info["available_quantity"],
            shortage=shortage_info["shortage"],
            is_sufficient=shortage_info["is_sufficient"],
            current_expenses=budget_info["approved_expenses"],
            budget_remaining=budget_info["remaining_budget"],
        )
        await ctx.send(sender, response)
    except Exception as e:
        ctx.logger.error(f"[LogisticsAgent] Error in logistics check: {e}")
        await ctx.send(
            sender,
            CheckLogisticsResponse(
                correlation_id=msg.correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_id=msg.event_id,
                item_name=msg.required_item_name,
                required_quantity=msg.required_quantity,
                available_quantity=0,
                shortage=msg.required_quantity,
                is_sufficient=False,
                current_expenses=0.0,
                budget_remaining=0.0,
                error_message=str(e),
            ),
        )
    finally:
        db.close()

def create_logistics_agent(
    name: str = "eventpilot_logistics",
    seed: Optional[str] = None,
    port: Optional[int] = None,
) -> Agent:
    agent = Agent(
        name=name,
        seed=seed or settings.LOGISTICS_SEED,
        port=port or settings.LOGISTICS_PORT,
        mailbox=False,
    )
    agent.include(logistics_protocol)
    return agent

if __name__ == "__main__":
    agent = create_logistics_agent()
    print(f"🚀 Logistics Agent started at {agent.address}")
    agent.run()
