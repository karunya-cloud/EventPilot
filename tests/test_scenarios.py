"""End-to-End Scenario Test: Full Multi-Turn ACP Conversation with Real DB Mutations & Risk Recovery."""
import pytest
from src.db.session import SessionLocal, init_db
from src.db.seed import seed_database
from src.db.models import Event, Task, RiskAlert, RiskStatus, EmailDraft, EmailStatus, InventoryItem, Registration
from src.agents.coordinator import process_coordinator_turn

@pytest.fixture(autouse=True)
def setup_test_env():
    init_db()
    seed_database()

@pytest.mark.asyncio
async def test_full_robotics_workshop_scenario():
    sender_id = "test_asi_organizer_user_123"

    # -------------------------------------------------------------
    # TURN 1: Initial vague user request
    # -------------------------------------------------------------
    turn1_prompt = "Organize a robotics workshop for 60 students on November 15, with a budget of ₹20,000."
    turn1_reply = await process_coordinator_turn(turn1_prompt, sender_id)

    assert "Robotics Workshop" in turn1_reply
    assert "Year & Timezone" in turn1_reply
    assert "Venue" in turn1_reply
    assert "Duration" in turn1_reply

    # -------------------------------------------------------------
    # TURN 2: Supplying missing parameters -> Event created & Shortage detected
    # -------------------------------------------------------------
    turn2_prompt = "Venue: Robotics Lab 3, Engineering Block, Duration: 4 hours, Year: 2026, IST, 1 kit per participant."
    turn2_reply = await process_coordinator_turn(turn2_prompt, sender_id)

    assert "Event Successfully Created in Database" in turn2_reply
    assert "OPERATIONAL RISK DETECTED: Hardware Shortage" in turn2_reply
    assert "40 kits" in turn2_reply
    assert "20 kits short!" in turn2_reply
    assert "[OPTION_A] Rent 20 Additional Kits" in turn2_reply
    assert "[OPTION_B] (Recommended) Restructure to 2-Person Engineering Teams" in turn2_reply
    assert "[APPROVE OPTION B]" in turn2_reply

    # Verify DB state after Turn 2
    db = SessionLocal()
    event = db.query(Event).filter(Event.venue.like("%Robotics Lab 3%")).order_by(Event.id.desc()).first()
    assert event is not None
    assert event.capacity == 60
    assert event.budget == 20000.0

    tasks = db.query(Task).filter(Task.event_id == event.id).all()
    assert len(tasks) == 7

    alert = db.query(RiskAlert).filter(RiskAlert.event_id == event.id).first()
    assert alert is not None
    assert alert.status == RiskStatus.DETECTED
    db.close()

    # -------------------------------------------------------------
    # TURN 3: Approving Option B -> Execute Mitigation & Gate Email Draft
    # -------------------------------------------------------------
    turn3_prompt = "[APPROVE OPTION B]"
    turn3_reply = await process_coordinator_turn(turn3_prompt, sender_id)

    assert "Mitigation Option Approved & Executed" in turn3_reply
    assert "2-Person Teams" in turn3_reply
    assert "30 kits from depot" in turn3_reply
    assert "Invitation Email Broadcast" in turn3_reply
    assert "[APPROVE_EMAIL]" in turn3_reply

    # Verify DB state after Turn 3
    db = SessionLocal()
    alert = db.query(RiskAlert).filter(RiskAlert.event_id == event.id).first()
    assert alert.status == RiskStatus.MITIGATED

    item = db.query(InventoryItem).filter(InventoryItem.name == "Robotics Hardware Kit").first()
    # Initial was 40, allocated 30 for pairs -> 10 buffer remaining
    assert item.available_quantity == 10

    email_draft = db.query(EmailDraft).filter(EmailDraft.event_id == event.id).first()
    assert email_draft is not None
    assert email_draft.status == EmailStatus.PENDING_APPROVAL
    db.close()

    # -------------------------------------------------------------
    # TURN 4: Approving Email Dispatch -> Delivery & Registration Passes
    # -------------------------------------------------------------
    turn4_prompt = "[APPROVE_EMAIL]"
    turn4_reply = await process_coordinator_turn(turn4_prompt, sender_id)

    assert "Email Broadcast Dispatched!" in turn4_reply
    assert "SIMULATED_SAFE_DISPATCH" in turn4_reply
    assert "Live Registration & QR Passes Generated:" in turn4_reply
    assert "Aarav Sharma" in turn4_reply

    # Verify DB state after Turn 4
    db = SessionLocal()
    email_draft = db.query(EmailDraft).filter(EmailDraft.event_id == event.id).first()
    assert email_draft.status == EmailStatus.SENT
    assert email_draft.sent_count > 0

    regs = db.query(Registration).filter(Registration.event_id == event.id).all()
    assert len(regs) >= 3
    assert all(r.qr_token is not None for r in regs)
    db.close()

    # -------------------------------------------------------------
    # TURN 5: Query Live Dashboard
    # -------------------------------------------------------------
    turn5_prompt = "dashboard"
    turn5_reply = await process_coordinator_turn(turn5_prompt, sender_id)

    assert "Live Event Dashboard" in turn5_reply
    assert "Advanced Autonomous Robotics Workshop" in turn5_reply
    assert "Confirmed Attendees" in turn5_reply
    assert "Budget" in turn5_reply
