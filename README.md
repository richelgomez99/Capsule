# Capsule — Your Second Brain That Actually Thinks

Capsule is an AI-powered web app that captures your digital life, understands what it finds, protects your sensitive data, surfaces insights you missed, and takes real actions — all without being asked. It gets smarter every day.

## The Problem

Your digital life is scattered across 40+ apps. You screenshot recipes, copy API keys, save research articles, get flight confirmations. That information disappears into the void. You can't find it later, nobody connects the dots, and nothing acts on what you save.

## What Capsule Does

- **Captures your data** — Upload screenshots, paste clipboard content, save URLs, or import browsing history
- **Surfaces your data when you ask** — Search across all your saves. Ask "what do I know about my puppy?" and get an answer that pulls from 5 different apps
- **Notices patterns autonomously** — "You research in Chrome, then build in VS Code. Classic research→build cycle."
- **Protects you automatically** — Catches emails, addresses, API keys and flags them before storing
- **Takes real actions** — Creates calendar events from flight confirmations, extracts to-do lists, generates weekly digests
- **Gets smarter every day** — Checks its own work, critiques low-confidence classifications, and improves without human intervention

## Architecture

```
Capture (Upload/Paste/URL) → Classify (Gemini) → Protect (PII Detection) → Score (Self-Eval) → Reflect → Act
           ↑                                                                                        |
           └──────────────────────── Retry if confidence < 70% ────────────────────────────────────┘
```

**Backend:** Python + FastAPI + SQLite  
**Frontend:** React + TypeScript + Tailwind CSS + shadcn/ui  
**AI:** Google Gemini for classification, chat, reflection, and synthesis

## Quick Start

### Backend
```bash
# Create .env with your API key (see .env.template)
cp .env.template .env
# Add your GEMINI_API_KEY to .env

# Install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start the server
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:8080 — the frontend connects to the backend on port 8000.

### Usage Flow
1. Go to **Capture** — upload screenshots, paste text, save URLs, or import browsing history
2. Go to **Feed** → click **"Process Today's Saves"** — watch the agent classify, protect, and act
3. Go to **Knowledge** — search and browse all your captures
4. Go to **Chat** — ask questions about your knowledge base
5. Go to **About Me** — see what the agent has learned about you

## Data Capture Methods

| Method | How |
|--------|-----|
| **Screenshots** | Drag & drop, file picker, or Ctrl+V paste |
| **Text / Clipboard** | Paste any text content — code, notes, copied text |
| **URLs** | Submit a URL — Capsule fetches and summarizes the page |
| **Browsing History** | Import a JSON array of browsing history entries |

## Environment Variables

```
GEMINI_API_KEY=your_key     # Required — Google Gemini API key
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application entry
│   │   ├── database.py          # SQLite database layer
│   │   ├── models.py            # Pydantic request/response models
│   │   ├── routers/
│   │   │   ├── captures.py      # Upload, text, URL, history endpoints
│   │   │   ├── intelligence.py  # Processing, search, chat endpoints
│   │   │   └── user.py          # Feed, metrics, feedback endpoints
│   │   └── services/
│   │       ├── classifier.py    # Gemini-based classification
│   │       ├── pii.py           # PII detection (regex patterns)
│   │       ├── pipeline.py      # Processing pipeline orchestrator
│   │       └── ocr.py           # OCR for screenshots
│   └── serve.py                 # Legacy hackathon server (preserved)
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Capture.tsx      # New — data capture UI
│       │   ├── Feed.tsx         # Dashboard with feed & activity
│       │   ├── Knowledge.tsx    # Search & browse captures
│       │   ├── Chat.tsx         # AI chat interface
│       │   └── AboutMe.tsx      # User model display
│       └── lib/
│           └── api.ts           # Backend API client
├── data/
│   ├── captures.json            # Seed data (113 captures)
│   └── app_state_seed.json      # User model seed
├── docs/
│   ├── PRD.md                   # Product Requirements Document
│   └── IMPLEMENTATION_PLAN.md   # Implementation plan
└── requirements.txt             # Python dependencies
```

## Built With

Python, FastAPI, SQLite, React, TypeScript, Tailwind CSS, Google Gemini, Vite, shadcn/ui, Framer Motion
