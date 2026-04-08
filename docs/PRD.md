# Capsule Web App — Product Requirements Document

> **Version:** 1.0  
> **Status:** Draft  
> **Last Updated:** 2026-04-08

---

## 1. Vision & Philosophy

**Capsule is your second brain that actually thinks.**

Every day you touch 40+ apps. You screenshot a recipe, copy an API key, save a research article, get a flight confirmation email. That information scatters across your digital life and disappears into the void. Capsule catches it all, understands what it means, protects sensitive data, and — critically — **surfaces it back to you intelligently**. It tells you things you forgot, notices patterns you missed, creates calendar events and to-do lists from your own data, and gets better at all of this every single day.

**Core principle:** Your information should work for *you*, not for the apps that captured it.

---

## 2. Problem Statement

Your digital life is a black hole:

1. **You can't find things later.** Where was that recipe? Which thread had the API key?
2. **Nobody connects the dots.** You research a topic across 5 apps — no tool notices that pattern.
3. **Your personal data is exposed.** You accidentally paste an address, phone number, or API key. It sits in plain text.
4. **Nothing acts on what you save.** A flight confirmation sits in your inbox. Nobody creates the calendar event.
5. **You forget things that mattered.** That recipe from last week? Gone from your mind.

---

## 3. Target Users

| Persona | Description | Primary Use Case |
|---------|-------------|------------------|
| **Knowledge Worker** | Developer, designer, researcher who saves content across many tools | Cross-app search & pattern detection |
| **Student** | Collects research, lecture notes, articles across platforms | Study synthesis & recall |
| **Power Browser** | Heavy tab user who screenshots and bookmarks constantly | Browsing history intelligence |
| **Privacy-Conscious User** | Wants to keep data but worries about PII exposure | Automatic PII protection |

---

## 4. Core Features

### 4.1 Data Capture (Input Methods)

Users must be able to provide their digital content to Capsule through multiple channels:

#### 4.1.1 Screenshot Upload
- **Drag-and-drop** image upload zone on the Capture page
- **Paste from clipboard** (Ctrl+V / Cmd+V) — paste screenshots directly
- **File picker** for selecting multiple images at once
- **Supported formats:** PNG, JPG, JPEG, WebP, GIF
- **Processing:** Server-side OCR extracts text content from images
- **Max file size:** 10 MB per image

#### 4.1.2 Clipboard / Text Content
- **Paste zone** for text content (code snippets, URLs, notes, copied text)
- **Rich text support** — preserves formatting context where possible
- **Auto-detection** of content type (URL, code, email, plain text)
- **Quick capture** — single-click paste button in the navigation bar

#### 4.1.3 URL / Bookmark Capture
- **URL input field** — paste a URL and Capsule fetches & summarizes the page
- **Metadata extraction** — title, description, Open Graph data, favicon
- **Content snapshot** — saves a text summary of the page content

#### 4.1.4 Browsing History Import
- **Manual CSV/JSON upload** of exported browsing history
- **Chrome history export** format support (JSON)
- **Batch processing** of imported URLs with metadata extraction
- **Deduplication** against existing captures

### 4.2 Intelligence Layer (Processing Pipeline)

Once data is captured, Capsule processes it through an AI pipeline:

```
Capture → Classify → Protect → Score → Reflect → Act
    ↑                                        |
    └──── Retry if confidence < 70% ─────────┘
```

#### 4.2.1 Classification
- **Category assignment:** code, recipe, research, shopping, personal, communication, documentation, reference, error
- **Tag generation:** 3-5 relevant tags per capture
- **Summary generation:** 1-2 sentence human-readable summary
- **Source detection:** Identify the originating app/context
- **Confidence scoring:** 0-100% confidence for each classification

#### 4.2.2 PII Protection
- **Automatic scanning** of all captured content for sensitive data
- **Detection types:** Email addresses, phone numbers, physical addresses, API keys, credit card numbers, SSN patterns
- **Redaction:** PII is flagged and can be auto-redacted before storage
- **User notification:** Feed card alerts when PII is detected and protected

#### 4.2.3 Self-Improvement Loop
- **Quality scoring:** Agent evaluates its own classification quality
- **Self-critique:** Low-confidence classifications trigger automatic re-evaluation
- **Human feedback:** User corrections train future classifications
- **Visible improvement:** Activity stream shows the agent's thinking process in real-time

#### 4.2.4 Autonomous Actions
- **Calendar events:** Extracted from time-sensitive captures (flights, appointments)
- **To-do lists:** Extracted from captures mentioning tasks ("need to", "don't forget")
- **Weekly digests:** Summary of where attention went, broken down by topic
- **Pattern detection:** Cross-capture insights surfaced proactively

### 4.3 Search & Retrieval

- **Full-text search** across all captures with synonym expansion
- **Category filtering** — browse by content type
- **AI-powered chat** — conversational interface to query your knowledge base
- **Cross-reference answers** — answers cite which captures they came from

### 4.4 User Model

- **Learned facts** — the agent builds a profile of your interests, projects, workflows
- **Confidence tracking** — how well the agent understands each area of your life
- **Active projects** — detected from capture patterns
- **Correction history** — all user feedback stored and applied

### 4.5 Feed & Dashboard

- **Intelligent feed** — proactive insights, protection alerts, pattern discoveries
- **Activity stream** — real-time visibility into agent processing
- **Metrics dashboard** — captures processed, confidence scores, PII protected
- **Quick actions** — respond to agent questions, dismiss cards, teach the agent

---

## 5. Technical Architecture

### 5.1 Frontend

| Technology | Purpose |
|-----------|---------|
| **React 18** | UI framework |
| **TypeScript** | Type safety |
| **Vite** | Build tool & dev server |
| **Tailwind CSS** | Utility-first styling |
| **shadcn/ui** | Component library (Radix UI primitives) |
| **Framer Motion** | Animations |
| **TanStack React Query** | Server state management |
| **React Router** | Client-side routing |

### 5.2 Backend

| Technology | Purpose |
|-----------|---------|
| **Python 3.11+** | Runtime |
| **FastAPI** | HTTP framework with async support |
| **SQLite** | Persistent storage (via `aiosqlite`) |
| **Pillow + pytesseract** | Server-side OCR for screenshots |
| **Google Gemini** | LLM for classification, chat, reflection, synthesis |
| **Pydantic** | Request/response validation |
| **python-multipart** | File upload handling |
| **uvicorn** | ASGI server |

### 5.3 API Design

#### Capture Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/captures/screenshot` | Upload screenshot image(s) |
| `POST` | `/api/captures/text` | Submit clipboard/text content |
| `POST` | `/api/captures/url` | Submit URL for capture |
| `POST` | `/api/captures/history` | Import browsing history (JSON/CSV) |
| `GET` | `/api/captures` | List all captures (paginated, filterable) |
| `GET` | `/api/captures/:id` | Get single capture detail |
| `DELETE` | `/api/captures/:id` | Delete a capture |

#### Intelligence Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/process` | Trigger processing pipeline |
| `GET` | `/api/processing` | Get processing status |
| `GET` | `/api/activity` | Get activity stream |
| `POST` | `/api/search` | Search across captures |
| `POST` | `/api/chat` | Chat with your knowledge base |

#### User Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/feed` | Get intelligent feed cards |
| `POST` | `/api/feed/:id/action` | Respond to feed card |
| `GET` | `/api/user-model` | Get learned user profile |
| `GET` | `/api/metrics` | Get agent metrics |
| `GET` | `/api/digest` | Get daily digest |
| `POST` | `/api/correct` | Submit correction |
| `POST` | `/api/feedback` | Submit thumbs up/down |

#### System Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/actions` | List generated actions |
| `GET` | `/api/actions/:filename` | Download action file |

### 5.4 Database Schema

```sql
-- Core captures table
CREATE TABLE captures (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,        -- 'screenshot', 'text', 'url', 'history'
    content     TEXT,                  -- Extracted/provided text content
    raw_path    TEXT,                  -- Path to original file (screenshots)
    source_app  TEXT,
    category    TEXT,
    summary     TEXT,
    tags        TEXT,                  -- JSON array
    has_pii     BOOLEAN DEFAULT FALSE,
    pii_details TEXT,                  -- JSON array
    confidence  REAL DEFAULT 0,
    quality     TEXT,                  -- A/B/C/D
    url         TEXT,                  -- For URL captures
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- User corrections
CREATE TABLE corrections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    capture_id  TEXT NOT NULL,
    field       TEXT NOT NULL,
    old_value   TEXT,
    new_value   TEXT NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (capture_id) REFERENCES captures(id)
);

-- User feedback (thumbs up/down)
CREATE TABLE feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    capture_id  TEXT NOT NULL,
    thumbs      TEXT NOT NULL,         -- 'up' or 'down'
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (capture_id) REFERENCES captures(id)
);

-- Agent activity log
CREATE TABLE activity_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,
    message     TEXT NOT NULL,
    capture_id  TEXT,
    metadata    TEXT,                   -- JSON
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Feed cards
CREATE TABLE feed_cards (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    title       TEXT NOT NULL,
    body        TEXT,
    reasoning   TEXT,
    actions     TEXT,                   -- JSON array
    dismissed   BOOLEAN DEFAULT FALSE,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- User model (learned facts)
CREATE TABLE user_model (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    confidence  REAL DEFAULT 0.5,
    source      TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 6. Pages & Navigation

| Route | Page | Description |
|-------|------|-------------|
| `/` | **Feed** | Dashboard with intelligent feed, activity stream, metrics |
| `/capture` | **Capture** *(new)* | Upload screenshots, paste text, submit URLs, import history |
| `/knowledge` | **Knowledge** | Search & browse all captures with filters |
| `/chat` | **Chat** | Conversational AI interface to query knowledge base |
| `/about-me` | **About Me** | View learned user model, facts, confidence |
| `/settings` | **Settings** *(new)* | API key configuration, preferences |

---

## 7. User Flows

### 7.1 First-Time Setup
1. User opens Capsule → lands on Feed (empty state)
2. Prompted to add first capture → navigated to Capture page
3. User uploads screenshot, pastes text, or submits URL
4. Capsule processes the capture → shows activity in real-time
5. Results appear in Knowledge + Feed

### 7.2 Screenshot Capture
1. User navigates to Capture page
2. Drags & drops screenshot OR pastes from clipboard OR uses file picker
3. Upload progress shown → OCR runs → classification begins
4. Capture appears in Knowledge with category, tags, summary
5. If PII detected → protection card appears in Feed

### 7.3 Clipboard Text Capture
1. User navigates to Capture page (or uses quick-capture button)
2. Pastes text content into the text capture area
3. Content type auto-detected (code, URL, note, etc.)
4. Classification pipeline runs
5. Capture stored and indexed

### 7.4 URL Capture
1. User pastes a URL into the URL capture field
2. Capsule fetches the page, extracts title + content summary
3. Stores as a capture with metadata
4. Available in search and knowledge base

### 7.5 Search & Chat
1. User types a question in Knowledge search or Chat
2. Capsule searches across all captures using semantic matching + synonym expansion
3. Returns relevant results with source citations
4. Chat mode provides conversational follow-up

---

## 8. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| **Page load** | < 2 seconds |
| **Capture processing** | < 10 seconds per item |
| **Search response** | < 1 second |
| **Uptime** | Local-first (no external dependencies required for basic use) |
| **Storage** | SQLite for simplicity, upgrade path to PostgreSQL |
| **Privacy** | All data stored locally by default, PII auto-detection |
| **Browser support** | Chrome, Firefox, Safari, Edge (latest 2 versions) |

---

## 9. Migration from Hackathon Version

### What Changes
| Aspect | Hackathon | Web App |
|--------|-----------|---------|
| **Data source** | Static JSON (113 pre-captured items) | User uploads, paste, URLs, history import |
| **Backend** | Python stdlib HTTP server | FastAPI with proper async |
| **Storage** | In-memory | SQLite database |
| **Classification** | Airia API (sponsor tool) | Google Gemini (self-hosted pipeline) |
| **DLP/PII** | Airia DLP API (sponsor tool) | Gemini-based + regex pattern detection |
| **Quality scoring** | Braintrust autoevals (sponsor tool) | Gemini self-evaluation |
| **OCR** | Pre-processed | Server-side Pillow + pytesseract |
| **File handling** | None | Multipart upload with validation |

### What Stays
- React + TypeScript frontend with shadcn/ui
- Feed, Knowledge, Chat, About Me pages
- Self-improvement loop architecture
- Category system (9 canonical categories)
- Activity stream with real-time updates
- User correction & feedback system
- Action generation (calendar, todos, digests)
- Synonym-expanded search

---

## 10. Future Enhancements (Out of Scope for V1)

- **Browser extension** for automatic capture (screenshots, clipboard, browsing)
- **User authentication** (currently single-user local app)
- **Cloud sync** across devices
- **Mobile app** (PWA or native)
- **Integrations** — Slack, email, Notion, etc.
- **Collaborative capsules** — shared knowledge bases
- **Advanced embeddings** — vector search with semantic similarity
- **Export** — download all data as JSON/CSV
