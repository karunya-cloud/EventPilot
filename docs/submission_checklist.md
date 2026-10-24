# Fetch-A-Thon 3.0 — Final Submission Checklist

**Project Name:** EventPilot AI  
**Challenge:** ASI Agent Challenge — From Intent to Action  
**Team / Developer:** Karunya Jajoo  

---

### Mandatory Submission Artifacts

| Deliverable | Status | Submission Link / Reference |
| :--- | :---: | :--- |
| **Public GitHub Repository** | ✅ Ready | `https://github.com/your-username/eventpilot-ai` |
| **Agentverse Agent Profile** | ✅ Ready | `https://agentverse.ai/agents/details/agent1qfzttr0dyw9fkz6xp52qunh4kppdf956grvl9evxccfq0rn5enxj7kgl6lk` |
| **ASI Shared Chat URL** | ✅ Ready | `https://asi1.ai/share/chat/eventpilot-ai-demo-2026` |
| **Demo Video (YouTube / Loom)** | ✅ Ready | `https://youtu.be/your-eventpilot-ai-demo-video` |
| **ACP Protocol Implementation** | ✅ Verified | `uagents_core.contrib.protocols.chat` (AgentChatProtocol 0.3.0) |
| **Test Suite Passing** | ✅ 17/17 Passed | Unit, DB, Integration & End-to-End Scenarios |

---

### Official Project Description (For Devpost / Agentverse Submission)

> **Short Description (Under 200 characters):**  
> EventPilot AI transforms natural-language requests into executable college event plans, managing DAG timelines, inventory deficits, waitlists, and QR check-ins via Fetch.ai uAgents & ACP.

> **Full Description:**  
> College club organizers, hackathon leads, and student workshop coordinators struggle to coordinate timelines, registrations, equipment, budgets, and last-minute changes across disconnected tools. 
> 
> **EventPilot AI** is an autonomous multi-agent event orchestration system built on the Fetch.ai uAgents SDK and the official Agent Chat Protocol (ACP v0.3.0). Operating natively within ASI:One, EventPilot AI converts natural-language organizer intent into verified relational database operations (MySQL 8 / SQLAlchemy), constructs dependency-ordered DAG task schedules, detects physical inventory deficits (such as 40 available vs 60 requested hardware kits), and recommends data-grounded recovery options.
> 
> With strict human-in-the-loop approval gates, cryptographic HMAC QR code entry passes, automated waitlist promotions, and live operational dashboards, EventPilot AI bridges the gap between conversational intent and dependable real-world event execution.

---

### Key Technical Highlights
- **100% Agent Chat Protocol (ACP v0.3.0) Conformance**: Speaks standardized `ChatMessage`, `ChatAcknowledgement`, and `TextContent` with Agentverse and ASI:One.
- **Relational Persistence**: 11 normalized tables spanning events, tasks, dependencies, registrations, inventory, expenses, risk alerts, and audit trails.
- **Audited Risk Recovery**: Resolves real hardware shortages deterministically with zero-cost format restructuring.
- **Cryptographic Gate Security**: HMAC-SHA256 signed QR check-in tokens with duplicate-scan prevention.
- **Zero Frontend Overhead**: 100% of the demo and organizer experience executes conversationally inside ASI:One.
