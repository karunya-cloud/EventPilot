# Agentverse Registration & ASI:One Integration Guide

This guide walks you through registering your EventPilot AI agent on **Agentverse** and linking it with **ASI:One (ASI Chat)** for the Fetch-A-Thon 3.0 challenge.

---

## 1. Prerequisites
- An active account on [Agentverse](https://agentverse.ai).
- A valid Agentverse API Key.
- EventPilot AI running locally with a stable seed phrase or deployed on a cloud VM/container.

---

## 2. Generating & Inspecting Your Agent Address
Your agent's Fetch.ai address is derived deterministically from the seed phrase specified in `.env`:
```bash
# In your project terminal:
python -c "from src.agents.coordinator import create_coordinator_agent; a = create_coordinator_agent(); print('Address:', a.address)"
```
Example Output:
```text
Address: agent1qfzttr0dyw9fkz6xp52qunh4kppdf956grvl9evxccfq0rn5enxj7kgl6lk
```

---

## 3. Registering the Agent on Agentverse

### Method A: Cloud Mailbox Integration (Recommended for Local Dev)
Agentverse Mailbox allows your local uAgent to receive messages asynchronously from ASI and other agents without opening public firewall ports or port-forwarding.

1. Log in to [Agentverse](https://agentverse.ai).
2. Navigate to **My Agents** → **Local Agents** or **Mailroom**.
3. Click **Add Agent** and enter your agent's name (`EventPilot Coordinator`) and its derived address `agent1q...`.
4. Agentverse will generate a **Mailbox Key**.
5. Copy the mailbox key into your `.env` file:
   ```env
   AGENTVERSE_API_KEY=your_copied_agentverse_key
   ```
6. In `src/agents/coordinator.py`, enable the mailbox:
   ```python
   agent = Agent(
       name="eventpilot_coordinator",
       seed=settings.COORDINATOR_SEED,
       port=settings.COORDINATOR_PORT,
       mailbox=f"{settings.AGENTVERSE_API_KEY}@https://agentverse.ai",
   )
   ```
7. Start your agent:
   ```powershell
   python src/agents/coordinator.py
   ```
   The terminal will confirm registration on the Agentverse Mailbox service.

---

### Method B: Native Agentverse Cloud Hosting
If you prefer 24/7 cloud hosting directly on Agentverse:
1. In Agentverse, click **New Agent** → **Blank Agent**.
2. Paste the contents of `src/agents/coordinator.py` into the Agentverse web IDE.
3. Add protocol dependencies:
   ```python
   from uagents_core.contrib.protocols.chat import (
       ChatMessage,
       ChatAcknowledgement,
       TextContent,
       chat_protocol_spec,
   )
   ```
4. Click **Start** to run the agent in the Agentverse cloud container.

---

## 4. Publishing the Agent Chat Protocol (ACP) & Discovery Manifest
To allow ASI:One users to find and interact with your agent:
1. In Agentverse, navigate to your Agent's **Profile & Metadata** settings.
2. Fill in the following discoverability parameters:
   - **Agent Name**: `EventPilot AI`
   - **Handle**: `@eventpilot`
   - **Short Description**: `Autonomous College Event Orchestration Agent. Coordinates robotics workshops, hackathons, task DAGs, inventory risk mitigation, and QR check-ins.`
   - **Tags/Keywords**: `event-planning`, `hackathon`, `robotics`, `timeline-dag`, `inventory-management`, `asi-alliance`, `fetch-a-thon`
   - **Avatar URL**: `https://raw.githubusercontent.com/your-username/eventpilot-ai/main/docs/assets/eventpilot_logo.png`
3. Under **Supported Protocols**, ensure `AgentChatProtocol (0.3.0)` is published.

---

## 5. Testing Directly Inside ASI:One
1. Visit [ASI:One](https://asi1.ai) and sign in.
2. In the agent search bar, search for `EventPilot AI` or enter your agent's address:
   `agent1qfzttr0dyw9fkz6xp52qunh4kppdf956grvl9evxccfq0rn5enxj7kgl6lk`
3. Click **Start Chat**.
4. Test with the starter prompt:
   ```text
   Organize a robotics workshop for 60 students on November 15, with a budget of ₹20,000.
   ```
5. Follow the conversational prompts and verify:
   - Missing slot elicitation.
   - Grounded risk alert (20 kit deficit).
   - Approval of Option B (`[APPROVE OPTION B]`).
   - Approval of Email (`[APPROVE_EMAIL]`).
   - Generation of QR check-in tokens.
6. Once the conversation is complete, click **Share Chat** in ASI:One to generate your public submission chat URL!
