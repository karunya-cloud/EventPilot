"""Risk and Recovery Agent for EventPilot AI.
Detects shortages, evaluates operational constraints, and proposes recovery plans.
"""
from datetime import datetime, timezone
from typing import Optional
from uagents import Agent, Context, Protocol
from src.config import settings
from src.agents.protocols import (
    AssessRiskRequest,
    AssessRiskResponse,
    MitigationOption,
)
from src.db.session import SessionLocal
from src.tools.risk_tools import detect_risks

risk_protocol = Protocol(name="RiskProtocol", version="1.0.0")

@risk_protocol.on_message(AssessRiskRequest)
async def handle_risk_assessment(ctx: Context, sender: str, msg: AssessRiskRequest):
    ctx.logger.info(f"[RiskAgent] Assessing risk for event {msg.event_id} (Item: {msg.item_name})")

    db = SessionLocal()
    try:
        risks = detect_risks(
            db=db,
            event_id=msg.event_id,
            required_item_name=msg.item_name,
            required_quantity=msg.required_quantity,
            agent_name="RiskAgent",
        )

        if risks:
            top_risk = risks[0]
            options = [
                MitigationOption(
                    option_id=opt["option_key"],
                    name=opt["name"],
                    description=opt["description"],
                    estimated_cost=opt["estimated_cost"],
                    feasibility="High" if opt["estimated_cost"] <= msg.budget_remaining else "Medium",
                )
                for opt in top_risk["mitigation_options"]
            ]
            response = AssessRiskResponse(
                correlation_id=msg.correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_id=msg.event_id,
                shortage=top_risk["shortage"],
                risk_level=top_risk["severity"],
                mitigation_options=options,
            )
        else:
            response = AssessRiskResponse(
                correlation_id=msg.correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_id=msg.event_id,
                shortage=0,
                risk_level="LOW",
                mitigation_options=[],
            )
        await ctx.send(sender, response)
    except Exception as e:
        ctx.logger.error(f"[RiskAgent] Risk assessment error: {e}")
        await ctx.send(
            sender,
            AssessRiskResponse(
                correlation_id=msg.correlation_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                event_id=msg.event_id,
                shortage=0,
                risk_level="ERROR",
                mitigation_options=[],
                error_message=str(e),
            ),
        )
    finally:
        db.close()

def create_risk_agent(
    name: str = "eventpilot_risk",
    seed: Optional[str] = None,
    port: Optional[int] = None,
) -> Agent:
    agent = Agent(
        name=name,
        seed=seed or settings.RISK_SEED,
        port=port or settings.RISK_PORT,
        mailbox=False,
    )
    agent.include(risk_protocol)
    return agent

if __name__ == "__main__":
    agent = create_risk_agent()
    print(f"🚀 Risk Agent started at {agent.address}")
    agent.run()
