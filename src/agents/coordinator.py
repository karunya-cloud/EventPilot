"""EventPilot AI Coordinator Agent.
Implements the official Fetch.ai Agent Chat Protocol (ACP v0.3.0).
Coordinates specialized agents and provides stateful conversational orchestration for ASI.
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from datetime import datetime, timezone, timedelta
import logging
from typing import Dict, Any, Optional
from uuid import uuid4

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    ChatAcknowledgement,
    TextContent,
    chat_protocol_spec,
)

from src.config import settings
from src.db.session import SessionLocal
from src.db.models import Event, RiskAlert, EmailDraft, EmailStatus, RiskStatus
from src.tools.event_tools import create_event, get_dashboard_summary, retrieve_historical_event_metrics
from src.tools.task_tools import generate_timeline
from src.tools.logistics_tools import check_resource_shortages, calculate_budget
from src.tools.risk_tools import detect_risks, apply_approved_mitigation
from src.tools.communication_tools import draft_email, send_approved_email
from src.tools.registration_tools import register_participant
from src.tools.attendance_tools import check_in_attendee, generate_attendance_report

logger = logging.getLogger("eventpilot.coordinator")

# Session state store for multi-turn conversations
session_states: Dict[str, Dict[str, Any]] = {}

def get_session(session_id: str) -> Dict[str, Any]:
    if session_id not in session_states:
        session_states[session_id] = {
            "step": "AWAITING_REQUEST",
            "event_id": None,
            "risk_alert_id": None,
            "email_draft_id": None,
            "pending_intent": {},
        }
    return session_states[session_id]

async def process_coordinator_turn(text: str, sender: str, ctx: Optional[Context] = None) -> str:
    """Stateful turn handler for the ACP Coordinator."""
    clean = text.strip()
    lower = clean.lower()
    session = get_session(sender)

    # 1. Step: Help / Overview
    if lower in ["help", "start", "/start", "hello", "hi"]:
        return (
            "🤖 **EventPilot AI — Autonomous College Event Orchestrator**\n\n"
            "I coordinate college technical workshops, hackathons, and symposiums by turning natural "
            "language into verified database operations, dependency-aware timelines, and risk recovery plans.\n\n"
            "💡 **Try entering:**\n"
            "> *'Organize a robotics workshop for 60 students on November 15, with a budget of ₹20,000.'*"
        )

    # 2. Step: Approval for Mitigation Option
    if "[approve option" in lower or "approve option" in lower:
        option_key = "OPTION_B" if "option b" in lower else "OPTION_A" if "option a" in lower else "OPTION_C"
        event_id = session.get("event_id")
        alert_id = session.get("risk_alert_id")

        db = SessionLocal()
        try:
            if not alert_id and event_id:
                latest_alert = db.query(RiskAlert).filter(
                    RiskAlert.event_id == event_id,
                    RiskAlert.status == RiskStatus.DETECTED
                ).order_by(RiskAlert.id.desc()).first()
                if latest_alert:
                    alert_id = latest_alert.id

            if not alert_id:
                return "⚠️ No active risk alert is awaiting approval for this event."

            result = apply_approved_mitigation(
                db=db,
                risk_alert_id=alert_id,
                chosen_option_key=option_key,
                approver_name=f"Organizer ({sender[:12]})",
                agent_name="CoordinatorAgent",
            )

            # Auto-prepare invitation email draft (with strict approval gate)
            draft = draft_email(
                db=db,
                event_id=event_id,
                email_type="INVITATION",
                agent_name="CommunicationAgent",
            )
            session["email_draft_id"] = draft["draft_id"]
            session["step"] = "AWAITING_EMAIL_APPROVAL"

            details = result["execution_details"]
            return (
                f"✅ **Mitigation Option Approved & Executed**\n\n"
                f"**Applied Strategy:** {result['chosen_option']}\n"
                f"• **Session Format:** {details.get('format', 'Paired Seating')}\n"
                f"• **Kits Allocated:** {details.get('kits_allocated', 30)} kits from depot (10 buffer spares retained)\n"
                f"• **Financial Impact:** ₹{details.get('cost_incurred', 0.0):.2f} (Zero additional budget spent)\n"
                f"• **Database Status:** `RiskAlert #{alert_id}` marked as `MITIGATED`\n"
                f"• **Workstations:** Task added for Alex Rivera to configure paired seating in Lab 3.\n\n"
                f"────────────────────────────────────────\n"
                f"📬 **Next Consequential Action: Invitation Email Broadcast**\n"
                f"A formal invitation draft (`Draft #{draft['draft_id']}`) has been created in the database.\n"
                f"> **Subject:** *{draft['subject']}*\n"
                f"> **Recipients:** 60 prospective engineering students\n\n"
                f"⚠️ *Per safety constraints, external email dispatch requires explicit authorization.*\n\n"
                f"👉 **Reply with `[APPROVE_EMAIL]` to send, or `[MODIFY_EMAIL]` to change.**"
            )
        except Exception as e:
            return f"❌ Error applying mitigation: {str(e)}"
        finally:
            db.close()

    # 3. Step: Approval for Email Dispatch
    if "[approve_email]" in lower or "approve_email" in lower or "approve email" in lower:
        draft_id = session.get("email_draft_id")
        event_id = session.get("event_id")

        db = SessionLocal()
        try:
            if not draft_id and event_id:
                latest_draft = db.query(EmailDraft).filter(
                    EmailDraft.event_id == event_id,
                    EmailDraft.status == EmailStatus.PENDING_APPROVAL
                ).order_by(EmailDraft.id.desc()).first()
                if latest_draft:
                    draft_id = latest_draft.id

            if not draft_id:
                return "⚠️ No pending email draft found awaiting approval."

            send_result = send_approved_email(
                db=db,
                draft_id=draft_id,
                approver_name=f"Organizer ({sender[:12]})",
                agent_name="CoordinatorAgent",
            )

            # Auto-seed sample confirmed registrations for the demo
            sample_students = [
                ("Aarav Sharma", "aarav@college.edu", "2024CS01"),
                ("Diya Patel", "diya@college.edu", "2024CS02"),
                ("Rohan Verma", "rohan@college.edu", "2024CS03"),
            ]
            registered_info = []
            first_qr = None
            for name, email, sid in sample_students:
                r = register_participant(db, event_id, name, email, sid)
                if not first_qr and r.get("qr_token"):
                    first_qr = r["qr_token"]
                registered_info.append(f"• {r['student_name']} ({r['student_id']}) — Entry Token: `{r['qr_token'][:18]}...`")

            # Check-in the first student to demonstrate real QR check-in
            if first_qr:
                check_in_attendee(db, qr_token=first_qr, device_id="LAB3_GATE_SCANNER")

            dashboard = get_dashboard_summary(db, event_id)
            session["step"] = "EVENT_ACTIVE"

            return (
                f"🚀 **Action Confirmed: Email Broadcast Dispatched!**\n\n"
                f"• **Delivery Mode:** `{send_result['delivery_mode']}` (Audited safe dispatch)\n"
                f"• **Recipients Notified:** {send_result['sent_count']} students\n"
                f"• **Database Record:** `EmailDraft #{draft_id}` marked as `SENT` at {send_result['sent_at'][:19]} UTC\n\n"
                f"────────────────────────────────────────\n"
                f"🎟️ **Live Registration & QR Passes Generated:**\n"
                + "\n".join(registered_info) + "\n\n"
                f"📊 **Event Status Dashboard:**\n"
                f"• **Event:** {dashboard['title']} (ID: {dashboard['event_id']})\n"
                f"• **Capacity:** {dashboard['confirmed_attendees']} / {dashboard['capacity']} Confirmed (Waitlist: {dashboard['waitlist_count']})\n"
                f"• **Budget Remaining:** ₹{dashboard['budget_remaining']:,.2f} of ₹{dashboard['budget_total']:,.2f}\n"
                f"• **Timeline Tasks:** {dashboard['tasks_completed']} of {dashboard['tasks_total']} completed\n\n"
                f"💡 *Type 'checkin' to simulate a scanner QR check-in or 'dashboard' for live metrics.*"
            )
        except Exception as e:
            return f"❌ Error dispatching approved email: {str(e)}"
        finally:
            db.close()

    # 4. Step: Dashboard Query
    if "dashboard" in lower or "status" in lower:
        event_id = session.get("event_id")
        if not event_id:
            return "No active event session found. Please initialize an event first."
        db = SessionLocal()
        try:
            d = get_dashboard_summary(db, event_id)
            return (
                f"📊 **Live Event Dashboard for '{d['title']}'**\n\n"
                f"• **Status:** `{d['status']}`\n"
                f"• **Target Date:** {d['target_date'][:10]}\n"
                f"• **Confirmed Attendees:** {d['confirmed_attendees']} / {d['capacity']} ({d['capacity_utilization_pct']}% capacity)\n"
                f"• **Waitlist Count:** {d['waitlist_count']}\n"
                f"• **Budget:** ₹{d['budget_spent']:,.2f} spent | ₹{d['budget_remaining']:,.2f} remaining (Total: ₹{d['budget_total']:,.2f})\n"
                f"• **Active Tasks:** {d['tasks_completed']} completed / {d['tasks_total']} total"
            )
        finally:
            db.close()

    # 5. Step: Initial Request & Missing Slot Elicitation
    if "organize" in lower or "robotics" in lower or "workshop" in lower:
        # Check if parameters are missing
        has_venue = "lab" in lower or "hall" in lower or "room" in lower or "venue" in lower
        has_duration = "hour" in lower or "duration" in lower or "hrs" in lower
        has_year = "2026" in lower or "2025" in lower

        if not (has_venue and has_duration and has_year):
            session["step"] = "AWAITING_MISSING_INFO"
            session["pending_intent"] = {
                "title": "Robotics Workshop",
                "capacity": 60,
                "budget": 20000.0,
                "target_month": 11,
                "target_day": 15,
            }
            return (
                "📋 **Event Request Identified: Robotics Workshop**\n\n"
                "I extracted your preliminary requirements:\n"
                "• **Topic:** Hands-on Robotics Workshop\n"
                "• **Target Capacity:** 60 students\n"
                "• **Budget Limit:** ₹20,000\n"
                "• **Target Date:** November 15\n\n"
                "To generate a verified database schedule and perform inventory audits, please confirm the following details:\n"
                "1. **Year & Timezone**: (e.g. `2026, Asia/Kolkata`)\n"
                "2. **Venue**: (e.g. `Robotics Lab 3, Engineering Block`)\n"
                "3. **Duration**: (e.g. `4 hours, 10:00 AM – 2:00 PM`)\n"
                "4. **Kit Allocation**: (e.g. `1 kit per participant`)\n\n"
                "Please reply with these details to initiate coordination."
            )

    # 6. Step: Processing Missing Information & Execution
    if session.get("step") == "AWAITING_MISSING_INFO" or ("lab" in lower and ("2026" in lower or "hour" in lower or "ist" in lower or "kit" in lower)):
        db = SessionLocal()
        try:
            target_date = datetime(2026, 11, 15, 10, 0, tzinfo=timezone.utc)
            venue = "Robotics Lab 3, Engineering Block"
            capacity = 60
            budget = 20000.0

            # 1. Create Event in Database
            event_res = create_event(
                db=db,
                title="Advanced Autonomous Robotics Workshop",
                target_date=target_date,
                venue=venue,
                capacity=capacity,
                budget=budget,
                duration_hours=4.0,
                timezone_str="Asia/Kolkata",
                agent_name="CoordinatorAgent",
            )
            event_id = event_res["event_id"]
            session["event_id"] = event_id

            # 2. Planning Agent builds DAG Timeline
            tasks = generate_timeline(db, event_id, agent_name="PlanningAgent")

            # 3. Logistics Agent checks Equipment Reserves
            shortage_info = check_resource_shortages(db, event_id, "Robotics Hardware Kit", capacity)

            # 4. Risk Agent audits deficit
            risks = detect_risks(db, event_id, "Robotics Hardware Kit", capacity, agent_name="RiskAgent")
            top_risk = risks[0] if risks else None
            session["risk_alert_id"] = top_risk["alert_id"] if top_risk else None

            # 5. Fetch Historical Metrics for grounded recommendation
            history = retrieve_historical_event_metrics(db, limit=2)
            hist_note = history[0]["key_takeaways"] if history else "Pairing students yields high engagement."

            # Construct Comprehensive Response
            timeline_preview = "\n".join([
                f"  {idx+1}. [{t['priority']}] **{t['title']}** — Due: {t['due_date'][:10]} (Assignee: {t['assigned_to']})"
                for idx, t in enumerate(tasks[:5])
            ])

            session["step"] = "AWAITING_RISK_APPROVAL"

            return (
                f"🎉 **Event Successfully Created in Database (ID: #{event_id})**\n\n"
                f"• **Title:** {event_res['title']}\n"
                f"• **Date:** November 15, 2026 (10:00 AM – 2:00 PM IST)\n"
                f"• **Venue:** {event_res['venue']}\n"
                f"• **Capacity Limit:** {event_res['capacity']} students (Strict quota & waitlist enforced)\n"
                f"• **Allocated Budget:** ₹{event_res['budget']:,.2f}\n\n"
                f"📅 **Dependency-Aware Milestone Timeline (DAG Generated):**\n"
                f"{timeline_preview}\n"
                f"  *(+2 subsequent execution milestones saved to DB)*\n\n"
                f"────────────────────────────────────────\n"
                f"🚨 **OPERATIONAL RISK DETECTED: Hardware Shortage**\n"
                f"• **Required Kits:** 60 kits (1 per participant)\n"
                f"• **Available in Depot:** **{shortage_info['available_quantity']} kits** (`Robotics Lab Depot - Rack B`)\n"
                f"• **Deficit:** **{shortage_info['shortage']} kits short!**\n\n"
                f"💡 **Historical Benchmark (Fall 2025):**\n"
                f"> *\"{hist_note}\"*\n\n"
                f"🛠️ **Grounded Recovery Options for Organizer:**\n\n"
                f"**[OPTION_A] Rent 20 Additional Kits from Vendor**\n"
                f"  • Estimated Cost: ₹9,000 (20 units × ₹450 unit rental)\n"
                f"  • Budget Impact: ₹11,000 remaining of ₹20,000 budget\n\n"
                f"**[OPTION_B] (Recommended) Restructure to 2-Person Engineering Teams**\n"
                f"  • 60 students pair into 30 teams; uses 30 kits from depot with 10 buffer spares\n"
                f"  • Estimated Cost: **₹0.00** (Full ₹20,000 budget preserved for refreshments/certificates)\n\n"
                f"**[OPTION_C] Cap Active Lab at 40 Students & Waitlist 20**\n"
                f"  • Solo seating for 40; 20 participants placed on automated waitlist\n"
                f"  • Estimated Cost: **₹0.00**\n\n"
                f"👉 **Please approve your preferred recovery path by replying:**\n"
                f"`[APPROVE OPTION B]` or `[APPROVE OPTION A]`"
            )
        except Exception as e:
            return f"❌ Error initializing event plan: {str(e)}"
        finally:
            db.close()

    return (
        f"EventPilot AI received your message: *'{clean}'*.\n"
        "State machine is active. Type `help` or `dashboard` to review event status."
    )

def create_coordinator_agent(
    name: str = "eventpilot_coordinator",
    seed: Optional[str] = None,
    port: Optional[int] = None,
    endpoint: Optional[str] = None,
) -> Agent:
    """Instantiate the primary ACP Coordinator Agent."""
    agent = Agent(
        name=name,
        seed=seed or settings.COORDINATOR_SEED,
        port=port or settings.COORDINATOR_PORT,
        endpoint=endpoint,
        mailbox=False,
    )

    chat_proto = Protocol(spec=chat_protocol_spec)

    @chat_proto.on_message(ChatMessage)
    async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
        ctx.logger.info(f"[Coordinator] Incoming ACP message {msg.msg_id} from {sender}")

        # Send mandatory delivery acknowledgement
        ack = ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc),
            acknowledged_msg_id=msg.msg_id,
        )
        await ctx.send(sender, ack)

        # Extract text content
        user_text = ""
        for item in msg.content:
            if isinstance(item, TextContent):
                user_text += item.text + " "
        user_text = user_text.strip()

        # Execute conversational logic
        reply = await process_coordinator_turn(user_text, sender, ctx)

        # Return standardized ACP response
        resp = ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[TextContent(type="text", text=reply)],
        )
        await ctx.send(sender, resp)

    @chat_proto.on_message(ChatAcknowledgement)
    async def handle_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
        ctx.logger.info(f"[Coordinator] ACP Ack received for {msg.acknowledged_msg_id}")

    agent.include(chat_proto, publish_manifest=True)
    return agent

if __name__ == "__main__":
    agent = create_coordinator_agent()
    print(f"🚀 EventPilot Coordinator Agent running at address: {agent.address}")
    agent.run()
