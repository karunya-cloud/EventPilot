"""Unit tests for Agent Chat Protocol (ACP) and Coordinator Agent Initialization."""
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
    chat_protocol_spec,
)
from src.agents.coordinator import create_coordinator_agent, process_coordinator_turn

def test_chat_protocol_schema_conformance():
    """Verify that ACP message schemas match the official specification."""
    msg_id = uuid4()
    text = "Organize a robotics workshop for 60 students on November 15, with a budget of ₹20,000."
    
    # 1. Create and validate ChatMessage
    msg = ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=msg_id,
        content=[TextContent(type="text", text=text)]
    )
    assert msg.msg_id == msg_id
    assert len(msg.content) == 1
    assert msg.content[0].text == text

    # 2. Create and validate ChatAcknowledgement
    ack = ChatAcknowledgement(
        timestamp=datetime.now(timezone.utc),
        acknowledged_msg_id=msg_id,
    )
    assert ack.acknowledged_msg_id == msg_id

def test_coordinator_agent_initialization():
    """Verify that coordinator agent registers the ACP protocol spec."""
    agent = create_coordinator_agent(seed="test_eventpilot_seed_test_123")
    assert agent.name == "eventpilot_coordinator"
    assert agent.address.startswith("agent1")
    assert any(p.name == "AgentChatProtocol" for p in agent.protocols.values())

@pytest.mark.asyncio
async def test_coordinator_elicits_missing_slots():
    """Verify that coordinator asks for missing year, venue, duration, timezone."""
    prompt = "Organize a robotics workshop for 60 students on November 15, with a budget of ₹20,000."
    response = await process_coordinator_turn(prompt, "sender_test")
    
    assert "Robotics Workshop" in response
    assert "Year & Timezone" in response
    assert "Venue" in response
    assert "Duration" in response
