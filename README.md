# Capsule — Your Second Brain That Actually Thinks

Capsule is an autonomous AI agent that captures your digital activity, understands what it finds, protects your sensitive data, surfaces insights you missed, and takes real actions — all without being asked. It gets smarter every day.

## The Problem

Your digital life is scattered across 40+ apps. You screenshot recipes, copy API keys, save research articles, get flight confirmations. That information disappears into the void. You can't find it later, nobody connects the dots, and nothing acts on what you save.

## What Capsule Does

- **Surfaces your data when you ask** — Search across all your saves. Ask "what do I know about my puppy?" and get an answer that pulls from 5 different apps.
- **Notices patterns autonomously** — "You research in Chrome, then build in VS Code. Classic research→build cycle."
- **Protects you automatically** — Catches emails, addresses, API keys and scrubs them before storing.
- **Takes real actions** — Creates calendar events from flight confirmations, extracts to-do lists, generates weekly digests.
- **Gets smarter every day** — Checks its own work, critiques low-confidence classifications, and improves without human intervention.

## Architecture

```
Your Saves → Understand (Airia) → Protect (Airia DLP) → Score (Braintrust) → Reflect (Gemini) → Act
                   ↑                                                              |
                   └───────────── Retry if confidence < 70% ─────────────────────┘
```

## Sponsor Tools

| Tool | Role |
|------|------|
| **Google Gemini 2.5 Flash + ADK** | LLM backbone — reflection, chat, synthesis, search |
| **Airia** | Understand Agent (classification) + DLP Agent (data protection) |
| **Braintrust** | autoevals LLMClassifier — the agent grades its own work |

## Quick Start

### Backend
```bash
# Create .env with your API keys (see .env.template)
cp .env.template .env

# Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start the server (instant startup)
python backend/serve.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — the frontend connects to the backend on port 8000.

### Demo Flow
1. Open the app — feed shows Capsule's analysis of 113 captured items
2. Click **"Process Today's Saves"** — watch the agent think, decide, and act in real-time
3. See **real actions** generated (calendar events, to-do lists, weekly digest)
4. Go to **Chat** — ask "what do you know about my puppy?" — Gemini answers from captured knowledge
5. Answer the **learning question** — the agent updates its model of you

## Environment Variables

```
GEMINI_API_KEY=your_key
AIRIA_API_KEY=your_key
BRAINTRUST_API_KEY=your_key
```

## Built With

Python, React, TypeScript, Tailwind CSS, Google Gemini 2.5 Flash, Google ADK, Airia, Braintrust, Vite, shadcn/ui, Framer Motion
