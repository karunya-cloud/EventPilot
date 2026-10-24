# 🚀 EventPilot AI — Autonomous Multi-Agent College Event Orchestrator

[![Fetch-A-Thon 3.0](https://img.shields.io/badge/Fetch--A--Thon%203.0-ASI%20Agent%20Challenge-blueviolet?style=for-the-badge&logo=target)](https://fetch.ai)
[![ASI Alliance](https://img.shields.io/badge/ASI%20Alliance-Agent%20Chat%20Protocol%20v0.3.0-blue?style=for-the-badge)](https://asi1.ai)
[![Innovation Lab](https://img.shields.io/badge/Fetch.ai-Innovation%20Lab-orange?style=for-the-badge)](https://fetch.ai/innovation-lab)
[![Tests](https://img.shields.io/badge/Tests-17%20Passed-brightgreen?style=for-the-badge&logo=pytest)](https://pytest.org)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.13-blue?style=for-the-badge&logo=python)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

> **EventPilot AI** converts natural-language requests into executable college event plans, manages dependency-aware task DAGs, performs verified database mutations, detects physical equipment deficits, enforces strict human approval gates, and coordinates rapid QR-based attendee check-ins—all directly within an **ASI:One (ASI Chat)** conversation.

---

## 📌 Problem Statement
College clubs, robotics societies, and hackathon teams struggle to coordinate events across disconnected tools. Budgets live in spreadsheets, tasks in messaging apps, and equipment counts are outdated. A last-minute shortage of hardware kits or sudden capacity overrun frequently derails student workshops.

## 💡 Solution
EventPilot AI provides a specialized multi-agent mesh powered by **Fetch.ai uAgents** and the **Agent Chat Protocol (ACP v0.3.0)**. Organizers interact conversationally through **ASI:One**. EventPilot AI:
1. Translates intent into validated database records (MySQL 8 / SQLAlchemy).
2. Generates Directed Acyclic Graph (DAG) task milestones.
3. Automatically detects resource shortages (e.g. 40 kits in depot vs 60 needed).
4. Proposes grounded, data-backed recovery options (such as zero-cost student pairing).
5. Strictly enforces approval gates before external message dispatch.
6. Generates HMAC-signed cryptographic QR check-in passes and prevents duplicate scans.

---

## 🏗️ Architecture & Multi-Agent Design

```mermaid
flowchart TD
    subgraph UI["Organizer & Attendee Touchpoints"]
        ASI["ASI:One Chat (Agent Chat Protocol)"]
        Scanner["Mobile Gate Scanners / REST API"]
    end

    subgraph Coordinator["Orchestration Layer"]
        CA["Coordinator Agent\n(ACP v0.3.0 Engine)"]
        Audit["Audit Trail & Idempotency Store"]
    end

    subgraph SpecializedMesh["Specialized Agent Mesh"]
        PA["Planning Agent\n(DAG Timeline & Dependencies)"]
        LA["Logistics Agent\n(Inventory Audits & Budget Ledger)"]
        RA["Registration Agent\n(Capacity Quotas & Waitlist)"]
        CommA["Communication Agent\n(Drafting & Approval Gates)"]
        RiskA["Risk & Recovery Agent\n(Shortage Detection & Mitigations)"]
    end

    subgraph Storage["Persistent Relational Layer (MySQL 8 / SQLite)"]
        DB[(Normalized Database)]
        M1["Events & Metrics"]
        M2["Tasks & DAG Dependencies"]
        M3["Inventory & Allocations"]
        M4["Registrations & QR Checkins"]
        M5["Email Drafts & Approvals"]
    end

    ASI <-->|ChatMessage / Ack| CA
    Scanner -->|POST /attendance/checkin| RA

    CA <--> PA
    CA <--> LA
    CA <--> RA
    CA <--> CommA
    CA <--> RiskA

    CA --> Audit
    PA --> DB
    LA --> DB
    RA --> DB
    CommA --> DB
    RiskA --> DB
    Audit --> DB
```

---

## 🤖 Registered Agent Information

| Attribute | Details |
| :--- | :--- |
| **Agent Name** | `EventPilot AI` |
| **Agent Handle** | `@eventpilot` |
| **Agent Address** | `agent1qfzttr0dyw9fkz6xp52qunh4kppdf956grvl9evxccfq0rn5enxj7kgl6lk` |
| **Protocol** | `AgentChatProtocol` (v0.3.0 via `uagents_core.contrib.protocols.chat`) |
| **Supported Network** | Fetch.ai Mainnet / Agentverse Mailroom / ASI:One |
| **Seed Configuration** | Configured via `COORDINATOR_SEED` in `.env` |

---

## ⚡ Quickstart & Local Setup

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.11 and 3.13)
- Git
- (Optional) Docker & Docker Compose for MySQL 8

### 2. Clone Repository & Setup Virtual Environment
```powershell
# Clone the repository
git clone https://github.com/your-username/eventpilot-ai.git
cd eventpilot-ai

# Create and activate virtual environment (Windows PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# (For Linux / macOS)
# python3 -m venv venv && source venv/bin/activate
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Configure Environment
```powershell
# Copy the example environment file
cp .env.example .env
```
*(By default, `.env` runs in SQLite mode for frictionless zero-config local testing. To run on MySQL 8, start Docker Compose and set `DATABASE_URL=mysql+pymysql://eventpilot:eventpilot123@localhost:3306/eventpilot_db`)*.

### 5. Run Database Migrations & Seed Baseline Data
```powershell
# Apply Alembic schema migrations
alembic upgrade head

# Seed core team, historical benchmarks, and the 40 Robotics Hardware Kits
python -m src.db.seed
```

### 6. Run the Test Suite
```powershell
pytest tests -v
```
Expected output: **17 passed** covering ACP schemas, DAG dependency blocking, waitlist auto-promotions, duplicate check-in prevention, and end-to-end multi-turn scenarios.

### 7. Launch EventPilot AI
```powershell
# Terminal 1: Run the ACP Coordinator Agent (Listens on port 8000)
python src/agents/coordinator.py

# Terminal 2: Run the REST API & Dashboard Service (Listens on port 8080)
python src/api/app.py
```
Open your browser to `http://127.0.0.1:8080/docs` to explore the interactive OpenAPI / Swagger documentation.

---

## 💬 The ASI:One Workflow (From Intent to Action)

A user opens **ASI:One** and enters:
> *"Organize a robotics workshop for 60 students on November 15, with a budget of ₹20,000."*

### Step 1: Missing Slot Elicitation
EventPilot AI identifies missing parameters and asks for:
- Year & Timezone (`2026, Asia/Kolkata`)
- Venue (`Robotics Lab 3, Engineering Block`)
- Duration (`4 hours`)
- Kit Allocation ratio (`1 kit per participant`)

### Step 2: Database Persistence & The Shortage Dilemma
Once supplied, EventPilot AI:
- Saves the event with capacity 60 and budget ₹20,000.
- Constructs a 7-step dependency-aware DAG timeline.
- Reads depot inventory: finds **40 Robotics Hardware Kits** available vs **60 requested**.
- Flags a **CRITICAL DEFICIT of 20 kits**!
- Generates 3 grounded mitigation options:
  - **Option A:** Rent 20 kits for ₹9,000 (leaves ₹11,000 runway).
  - **Option B (Recommended):** Pair students 2-per-kit (uses 30 kits, ₹0 cost, supported by Fall 2025 metrics).
  - **Option C:** Cap workshop at 40 and waitlist 20 students.

### Step 3: Approval Gate & Mitigation Execution
The organizer replies:
> `[APPROVE OPTION B]`
- EventPilot reserves 30 kits from inventory (retaining 10 buffer spares).
- Adds a workstation setup task for logistics lead Alex Rivera.
- Marks the risk alert as `MITIGATED` in the database.
- Prepares an invitation email draft and halts at an approval gate.

### Step 4: Email Dispatch & QR Check-In
The organizer replies:
> `[APPROVE_EMAIL]`
- Email draft is marked as `SENT`.
- 60 invitations queued via simulated safe dispatch.
- Confirmed attendees receive cryptographically signed HMAC QR tokens.
- Gate scanners scan and record attendance without allowing duplicate entries.

---

## 🔒 Security & Reliability Guarantees
- **HMAC QR Signing:** Attendance tokens are cryptographically hashed using SHA-256 and verified upon entry.
- **Idempotency Keys:** Mutating database actions hash their payload to prevent double-billing and duplicate registrations.
- **Strict Approval Gating:** High-consequence actions (external email dispatch, budget expenditures) require explicit user tokens (`[APPROVE_...]`).
- **DAG Dependency Enforcement:** Tasks cannot be completed unless their prerequisite parent tasks are marked completed.

---

## 📂 Project Structure
```text
eventpilot-ai/
├── README.md                      # Public documentation and quickstart
├── requirements.txt               # Pinned dependencies
├── pyproject.toml                 # Package definition & pytest config
├── .env.example                   # Environment configuration template
├── docker-compose.yml             # MySQL 8 service definition
├── alembic.ini                    # Alembic migration configuration
├── alembic/                       # Migration scripts
│   ├── env.py
│   └── versions/                  # Schema migration versions
├── src/
│   ├── config.py                  # Environment variable configuration
│   ├── db/
│   │   ├── session.py             # SQLAlchemy session and engine factory
│   │   ├── models.py              # Normalized ORM entities
│   │   └── seed.py                # Synthetic seed data (40 kits, team users)
│   ├── tools/
│   │   ├── audit.py               # Idempotency and audit logging
│   │   ├── event_tools.py         # Event creation and dashboard summaries
│   │   ├── task_tools.py          # DAG timeline generator and task CRUD
│   │   ├── registration_tools.py  # Quotas, waitlists, and auto-promotions
│   │   ├── attendance_tools.py    # QR tokens, scanning, and duplicate blocks
│   │   ├── logistics_tools.py     # Inventory shortage calculation & budgets
│   │   ├── risk_tools.py          # Shortage detection and mitigation plans
│   │   └── communication_tools.py # Email drafts and approval gates
│   ├── agents/
│   │   ├── protocols.py           # Pydantic/uAgents request & response schemas
│   │   ├── coordinator.py         # ACP v0.3.0 Coordinator Agent for ASI
│   │   ├── planning_agent.py      # Specialized Planning Agent
│   │   ├── logistics_agent.py     # Specialized Logistics Agent
│   │   ├── registration_agent.py  # Specialized Registration Agent
│   │   ├── communication_agent.py # Specialized Communication Agent
│   │   └── risk_agent.py          # Specialized Risk & Recovery Agent
│   ├── api/
│   │   ├── app.py                 # FastAPI application
│   │   └── routes.py              # REST API route handlers
│   └── scheduler/
│       └── jobs.py                # APScheduler periodic deadline monitors
├── tests/
│   ├── conftest.py                # Test fixtures and clean DB setup
│   ├── test_acp.py                # Protocol schema conformance tests
│   ├── test_db_models.py          # Foreign keys and constraint tests
│   ├── test_tools.py              # Business logic unit tests
│   ├── test_scenarios.py          # End-to-end multi-turn ASI scenario test
│   └── test_api.py                # FastAPI REST endpoint integration tests
└── docs/
    ├── architecture.md            # Comprehensive architecture specification
    ├── asi_conversation_script.md # Verified ASI:One conversation transcript
    ├── agentverse_registration.md # Agentverse registration instructions
    ├── demo_video_script.md       # 3-5 minute demo video script
    └── submission_checklist.md    # Hackathon submission checklist
```

---

## ⚠️ Known Limitations & Future Roadmap
- **Production SMTP**: Outgoing email dispatch currently operates in simulated mode to prevent accidental spam during hackathon testing. Live Resend / SendGrid API integrations are supported via configuration.
- **Physical QR Scanner App**: A progressive web app (PWA) barcode scanner can be pointed directly at `/api/attendance/checkin`.
- **Decentralized Calendar Sync**: Planned integration with Google Calendar / Outlook via Agentverse sidecars.

---

## 📜 License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details. Built with pride for **Fetch-A-Thon 3.0**.
