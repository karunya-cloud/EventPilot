# EventPilot AI — 3 to 5 Minute Demo Video Script

**Title:** EventPilot AI: From Natural-Language Intent to Physical Action  
**Track:** Fetch-A-Thon 3.0 — ASI Agent Challenge  
**Target Video Duration:** 4 minutes 15 seconds  

---

## Visual & Voiceover Breakdown

### [00:00 - 00:35] Scene 1: The Problem & The Solution
- **Visual:** Split screen showing frantic college club organizers juggling disparate tools (spreadsheets, WhatsApp groups, budget notes, Google Forms). Transition to the EventPilot AI logo and architecture banner.
- **Voiceover:**
  > *"College event organizers, robotics clubs, and hackathon teams face a common nightmare: fragmented coordination. Budgets are tracked on one sheet, tasks on another, equipment inventory is out of date, and last-minute shortages cause chaos.*
  > *Meet **EventPilot AI** — an autonomous multi-agent event orchestrator built on Fetch.ai's uAgents SDK and Agent Chat Protocol (ACP). It converts pure natural-language intent directly into executable timelines, verified database transactions, operational risk mitigation, and cryptographic attendee check-ins—entirely inside an ASI:One conversation."*

---

### [00:35 - 01:25] Scene 2: Natural-Language Intent & Slot Elicitation
- **Visual:** Screen recording of the ASI:One chat interface. The user enters:
  `"Organize a robotics workshop for 60 students on November 15, with a budget of ₹20,000."`
- **Voiceover:**
  > *"Let's test EventPilot live in ASI:One. We tell the agent to organize a robotics workshop for 60 students on November 15 with ₹20,000 budget.*
  > *Notice that EventPilot doesn't hallucinate missing details. It accurately identifies the intent and immediately asks for critical operational parameters: the year, timezone, venue, duration, and kit allocation ratio.*
  > *We reply: 'Venue: Robotics Lab 3, Engineering Block, Duration: 4 hours, Year: 2026, IST, 1 kit per student.' Watch what happens in the background."*

---

### [01:25 - 02:20] Scene 3: Multi-Agent Coordination & The Shortage Dilemma
- **Visual:** Close-up of ASI chat rendering the created Event (#1), the 7 DAG milestone tasks, followed by the highlighted **CRITICAL OPERATIONAL RISK ALERT**. Cut to terminal/DB inspector showing the `inventory_items` table with 40 kits.
- **Voiceover:**
  > *"Instantly, EventPilot persists the event into our relational database. The Planning Agent constructs a dependency-aware Directed Acyclic Graph (DAG) with 7 milestones.*
  > *Simultaneously, the Logistics Agent audits the physical inventory depot. It discovers that while 60 kits are required, our storage depot only has **40 Robotics Hardware Kits available**—a deficit of 20 units!*
  > *Instead of crashing or ignoring the issue, the Risk Agent analyzes historical workshop data and formulates three grounded recovery options: rent 20 units at ₹9,000; pair students into 2-person teams at ₹0; or cap attendance at 40.*
  > *It recommends Option B based on Fall 2025 data showing paired robotics work boosts student collaboration."*

---

### [02:20 - 03:05] Scene 4: Explicit Approval Gates & State Execution
- **Visual:** User inputs `[APPROVE OPTION B]`. EventPilot returns the execution confirmation and immediately presents the invitation draft with `[APPROVE_EMAIL]`. The user inputs `[APPROVE_EMAIL]`.
- **Voiceover:**
  > *"EventPilot strictly enforces human-in-the-loop approval gates. No money is spent, no session formats changed, and no emails sent without explicit authorization.*
  > *We reply with `[APPROVE OPTION B]`. The agent allocates 30 kits from inventory, preserves 10 safety spares, adds a workstation configuration task for logistics lead Alex Rivera, and marks the risk alert as MITIGATED.*
  > *Next, it drafts the attendee invitation. Again, it stops at an approval gate. When we enter `[APPROVE_EMAIL]`, the Communication Agent dispatches the broadcast, registers students with strict capacity limits, and issues HMAC-signed cryptographic QR check-in tokens."*

---

### [03:05 - 03:45] Scene 5: Cryptographic Check-In & Live Verification
- **Visual:** Terminal showing FastAPI server logs receiving check-in scans. First scan succeeds (`200 OK - PRESENT`). A repeated scan of the exact same QR code is flagged and rejected (`ALREADY_CHECKED_IN`).
- **Voiceover:**
  > *"On event day, gate scanners interface with EventPilot's REST API. When attendee Aarav presents his QR code, attendance is instantly verified and recorded.*
  > *If a student attempts to reuse or scan a duplicate token, EventPilot detects the collision and blocks duplicate entry.*
  > *Typing `dashboard` in ASI gives the organizer live metrics: 100% attendance, remaining budget, and completed milestones."*

---

### [03:45 - 04:15] Scene 6: Conclusion & GitHub Repository
- **Visual:** GitHub repository overview showing `README.md`, Innovation Lab and Fetch-A-Thon badges, test suite passing 17/17 tests, and Docker setup.
- **Voiceover:**
  > *"EventPilot AI is 100% open-source, fully tested with 17 passing integration tests across MySQL, SQLAlchemy, FastAPI, and Fetch.ai uAgents.*
  > *It turns complex event planning from scattered intent into reliable, audited, multi-agent action.*
  > *Check out the public repository and try EventPilot today. Thank you!"*
