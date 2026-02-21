# Capsule — Your Second Brain That Actually Thinks

## Elevator Pitch

Every day, you touch 40+ apps. You screenshot a recipe, copy an API key, save a research article, get a flight confirmation email. That information scatters across your digital life and disappears. Capsule catches it all, understands what it means, protects the sensitive stuff, and — here's the key part — **surfaces it back to you intelligently**. It tells you things you forgot. It notices patterns you missed. It creates calendar events and to-do lists from your own data without being asked. And it gets better at all of this every single day.

## The Problem

**Your digital life is a black hole.** You save things constantly — screenshots, links, clipboard copies, notes — across dozens of apps. But:

- **You can't find it later.** Where was that recipe? Which Slack thread had the API key? What was that article about?
- **Nobody connects the dots.** You researched AI agents for 3 days across Chrome, saved code in VS Code, and bookmarked 4 articles. No tool notices that pattern.
- **Your personal data is exposed.** You accidentally copy-paste an address, a phone number, an API key. It sits in plain text forever.
- **Nothing acts on what you save.** A flight confirmation sits in your inbox. A vet appointment is in a screenshot. Nobody creates the calendar event.
- **You forget things that mattered.** That recipe you saved last Tuesday? Gone from your mind. That to-do you mentioned in a note? Lost.

The core problem: **your information works for the apps that captured it, not for you.**

## What Capsule Does

Capsule is an AI agent that flips that relationship. Your data works for **you** now.

### 1. It Surfaces Your Data When You Ask

**Search:** Ask "what have I been researching about dogs?" and Capsule searches across ALL your saves — screenshots, clipboard, browser, notes — and answers using Gemini:

> "You've been looking at pomskies! You checked out a breeder listing on Good Dog, searched Amazon for puppy supplies, drafted an Instagram caption for Duke's Sunday photo, and saved his vet appointment with Dr. Patel at 142 Atlantic Ave in Brooklyn."

That answer came from 5 different apps, captured on 3 different days. No single app could have connected those dots.

**Chat:** Ask "what have I been up to this week?" and Capsule synthesizes your entire week:

> "You had a focused week. Most of your energy went into hackathon prep — 12 code snippets, 4 research articles. You also have Duke's vet appointment coming up, and you saved a jollof rice recipe you might want to try this weekend."

### 2. It Surfaces Insights Autonomously

Without being asked, Capsule notices things and tells you:

- **"I noticed a pattern in how you work"** — It detected that you research in Chrome then build in VS Code. A workflow pattern across 21 captures.
- **"I connected dots across your saves"** — 9 code snippets + 22 research articles = you're building an AI agent. It figured that out on its own.
- **"Remember this?"** — A recipe you saved but never came back to. Capsule tracks what you revisit and what you forget.
- **"Quick question — what are you building?"** — It asks targeted questions to fill gaps in its understanding, then uses your answers to get smarter.

### 3. It Protects You Automatically

- **"Heads up — I protected your personal info"** — Your apartment application had your email, phone, address, and full name. Capsule caught all 4 and scrubbed them before storing. You didn't have to think about it.

### 4. It Takes Real Actions From Your Data

After processing your saves, Capsule autonomously creates:

- **Calendar events** from time-sensitive captures (e.g., "JetBlue confirmation for SF trip in March" → downloadable .ics file)
- **A to-do list** extracted from captures that mention tasks ("need to", "don't forget", "pick up")
- **A weekly knowledge digest** summarizing where your attention went, broken down by topic and app

These are real files you can download and use. The agent didn't wait for you to ask — it saw actionable information and acted.

### 5. It Gets Smarter Every Day (Self-Improvement)

This is the part that makes Capsule an **agent**, not a tool. You can watch it happen in real-time:

1. Capsule classifies a save → "I think this is 'communication'"
2. It checks its own confidence → "Only 53%... that's not good enough"
3. It critiques itself → "Wait, this is actually a shopping item, not communication"
4. It reclassifies → confidence jumps to 78%
5. It does this **without any human input**

Every correction you make teaches it. Every question it asks fills a gap. Every low confidence score triggers self-reflection. The agent is always improving.

## How I Built It

**Architecture:** Python backend (pure stdlib HTTP server — starts in <1 second) + React/TypeScript frontend with real-time activity streaming.

**The Pipeline (runs autonomously):**
```
Your Saves → Understand (Airia) → Protect (Airia DLP) → Score (Braintrust) → Reflect (Gemini) → Act
                   ↑                                                              |
                   └───────────── Retry if confidence < 70% ─────────────────────┘
```

**Three Sponsor Tools — Each With a Real Job:**

| Tool | What It Does | Why It Matters |
|------|-------------|----------------|
| **Airia** (Understand Agent) | Classifies every capture — category, tags, summary, source app | The agent's ability to *comprehend* what it sees |
| **Airia** (DLP Agent) | Scans for sensitive data — emails, addresses, API keys | The agent's ability to *protect* you automatically |
| **Braintrust** (autoevals) | Scores the agent's own classification quality | The agent's ability to *judge its own work* |
| **Google Gemini 2.5 Flash** | Reflection, chat, synthesis, search answers | The agent's ability to *think, critique, and communicate* |

**Data:** 113 real captures from my actual digital life across 41 apps (Chrome, VS Code, Slack, Instagram, Amazon, iMessage, and more).

## Challenges

- **Making self-improvement visible, not abstract.** A confidence score means nothing to a user. I built a live activity stream where you literally watch the agent think: "Only 53% confident... that's not good enough. Let me critique myself..." That's what makes it feel alive.
- **Cold start performance.** Pydantic + FastAPI took 30+ seconds to import. Pivoted to pure stdlib HTTP server — starts instantly. Braintrust autoevals takes 72s to import — solved with background thread pre-loading.
- **Real data is messy.** OCR from screenshots produces garbled text. Tuned all prompts to look past noise and extract meaning anyway.
- **Cloudflare blocking.** Airia API returned 403 with Python's default User-Agent. 

## What I Learned

- The gap between "storing information" and "surfacing it intelligently" is enormous. Storage is solved. Intelligence is the hard part.
- Self-improvement isn't a metric — it's a visible behavior. When the agent says "that's not good enough, let me rethink," users understand what's happening instantly.
- Three tools forming a genuine pipeline (Airia classifies → Braintrust scores → Gemini critiques → Airia retries) is more powerful than any single tool alone.
- Real personal data makes the demo 10x more compelling than synthetic data.

## Built With
AiBrV
- **Google Gemini 2.5 Flash** — LLM backbone for reflection, chat, synthesis, search, and scoring
- **Google ADK** — Agent Development Kit architecture for multi-agent coordination
- **Airia** — External specialist agents: Understand (classification) + DLP (data protection)
- **Braintrust** — Quality scoring via autoevals LLMClassifier — the agent grades its own work
- **Python** — Backend (pure stdlib HTTP server, threading, urllib)
- **React + TypeScript** — Frontend with Tailwind CSS, shadcn/ui, Framer Motion
- **Vite** — Frontend build tool
