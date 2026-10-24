# EventPilot AI — Architecture & Data-Flow Specification

## 1. System Overview
**EventPilot AI** is an autonomous multi-agent event orchestration system designed for college clubs, robotics teams, student societies, and workshop organizers. It bridges the gap between natural language intent and reliable physical/digital event execution.

Built upon the **Fetch.ai uAgents Framework** and the **Agent Chat Protocol (ACP v0.3.0)**, EventPilot AI interfaces seamlessly with **ASI:One / Agentverse**, translating complex organizer requests into validated database transactions, dependency-ordered schedules, resource allocations, automated risk mitigation, and attendee check-in workflows.

---

## 2. Architecture Diagram

```mermaid
flowchart TD
    subgraph UserInterface["Organizer & Attendee Interfaces"]
        ASI["ASI Chat / Agentverse UI (ACP)"]
        REST["REST API / Admin Dashboard"]
        Scanner["QR Code Check-in Scanner"]
    end

    subgraph CoordinatorLayer["Orchestration Layer"]
        CA["Coordinator Agent\n(ACP Protocol Handler)"]
        Audit["Audit Trail & State Machine"]
    end

    subgraph MultiAgentCore["Specialized Agent Mesh"]
        PA["Planning Agent\n- Milestones & DAG Tasks\n- Capacity Planning"]
        LA["Logistics Agent\n- Equipment Inventory\n- Budget & Expenses"]
        RA["Registration Agent\n- Waitlist & Quota\n- QR Tokens & Attendance"]
        CommA["Communication Agent\n- Drafts & Approvals\n- Invitation Broadcast"]
        RiskA["Risk & Recovery Agent\n- Shortage Detection\n- Alternative Generation"]
    end

    subgraph PersistentStorage["Persistent Database (MySQL 8 / SQLite)"]
        DB[(Normalized Relational DB)]
        M_Users["Users & Roles"]
        M_Events["Events & Metrics"]
        M_Tasks["Tasks & Dependencies"]
        M_Regs["Registrations & Checkins"]
        M_Inv["Inventory & Allocations"]
        M_Budget["Budget & Expenses"]
        M_Comms["Email Drafts & Logs"]
        M_Risks["Risk Incidents & Actions"]
    end

    ASI <-->|ACP ChatMessage / Ack| CA
    REST <-->|FastAPI HTTP| CA
    Scanner -->|POST /checkin/verify| RA

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

## 3. Data Flow Diagram: From Intent to Action

The following sequence outlines the standard end-to-end lifecycle for an event organizer, demonstrating the strict approval gates and deterministic state changes:

```mermaid
sequenceDiagram
    autonumber
    actor Organizer as Organizer (via ASI)
    participant Coord as Coordinator Agent (ACP)
    participant Plan as Planning Agent
    participant Log as Logistics Agent
    participant Risk as Risk Agent
    participant Comm as Communication Agent
    participant DB as Persistent Database

    Organizer->>Coord: "Organize a robotics workshop for 60 students on Nov 15, budget ₹20,000"
    Coord->>Coord: Analyze intent & extract slots
    Coord-->>Organizer: Inquire missing slots: Venue, duration, equipment per team
    Organizer->>Coord: "Venue: Lab 3, Duration: 4 hrs, 1 kit per attendee"
    
    Coord->>Plan: Generate timeline & task dependencies
    Plan->>DB: Save Event, Tasks (DAG dependencies)
    
    Coord->>Log: Check equipment inventory & budget
    Log->>DB: Query inventory for "Robotics Kit"
    DB-->>Log: 40 kits available in stock
    
    Log->>Risk: Report Shortage: 60 required vs 40 in stock
    Risk->>Risk: Formulate mitigation options (Rent, Borrow, Pair-Up)
    Risk-->>Coord: Shortage Alert: 20 kits short! Options: A (Rent), B (Pair-up), C (Waitlist to 40)
    
    Coord-->>Organizer: Detailed Proposal + Risk Warning with 3 options
    Organizer->>Coord: "[APPROVE OPTION B] Pair students 2-per-kit, no extra cost"
    
    Coord->>Log: Update resource allocation (30 kits for 60 students)
    Coord->>Comm: Draft invitation & reminder email template
    Comm->>DB: Save email drafts (Status: PENDING_APPROVAL)
    
    Coord-->>Organizer: Action required: Approve invitation email broadcast?
    Organizer->>Coord: "[APPROVE_EMAIL]"
    Comm->>Comm: Dispatch simulated invitations with QR check-in links
    Comm->>DB: Update email status to SENT
    Coord-->>Organizer: "Confirmed: 30 kits allocated, 60 invitations queued!"
```

---

## 4. Multi-Agent Design & Separation of Concerns

1. **Coordinator Agent**:
   - Manages ACP sessions (`ChatMessage`, `ChatAcknowledgement`, `TextContent`).
   - Acts as the primary router and intent parser.
   - Enforces approval gates before executing any mutating tool.
2. **Planning Agent**:
   - Computes task dependencies using a Directed Acyclic Graph (DAG).
   - Generates milestone-driven event schedules.
3. **Logistics Agent**:
   - Manages venue readiness, equipment reserves, and expense ledgers.
   - Calculates remaining budget and validates expense transactions.
4. **Registration Agent**:
   - Manages capacity quotas, prevents duplicate registrations (atomic DB checks).
   - Handles waitlist queues and auto-promotion upon cancellations.
   - Generates cryptographically signed QR tokens for check-ins.
5. **Communication Agent**:
   - Drafts announcements, registration confirmations, and reminders.
   - Enforces human-in-the-loop approvals before external delivery.
6. **Risk & Recovery Agent**:
   - Continuously audits deadlines, overdue tasks, and inventory deficits.
   - Formulates grounded mitigation options with cost/impact projections.

---

## 5. Security & Reliability Architecture
- **Idempotency Keys**: All financial transactions, status transitions, and check-ins check deduplication hashes.
- **Signed QR Tokens**: HMAC-SHA256 signature verification prevents token forgery and double check-ins.
- **Strict Approval Gates**: No emails are sent, no funds committed, and no session formats altered without explicit user confirmation (`[APPROVE]` token).
- **Dual Database Support**: Fully tested on MySQL 8 with an automatic SQLite fallback for lightweight development and testing.
