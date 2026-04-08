# Capsule Web App — Implementation Plan

> **Version:** 1.0  
> **Status:** In Progress  
> **Last Updated:** 2026-04-08

---

## Overview

This document outlines the concrete implementation plan to transform Capsule from a hackathon demo (static data, sponsor tools) into a functional web app where users can actually capture, organize, and query their digital life.

---

## Phase 1: Backend Foundation ✅

**Goal:** Replace stdlib HTTP server with FastAPI + SQLite, remove hackathon sponsor dependencies.

### 1.1 FastAPI Server Setup
- [x] Replace `http.server` with FastAPI + uvicorn
- [x] Add Pydantic models for request/response validation
- [x] Set up CORS middleware for frontend communication
- [x] Implement proper error handling with HTTP status codes

### 1.2 SQLite Database
- [x] Create database schema (captures, corrections, feedback, activity_log, feed_cards, user_model)
- [x] Implement database initialization on first run
- [x] Migrate seed data loading (from `data/captures.json`) to populate initial DB
- [x] Add CRUD operations for all tables

### 1.3 Replace Sponsor Tools
- [x] Replace Airia classification → Gemini-based classification
- [x] Replace Airia DLP → Gemini + regex PII detection
- [x] Replace Braintrust scoring → Gemini self-evaluation
- [x] Keep Gemini API as the single LLM dependency (optional — falls back gracefully)

---

## Phase 2: Data Capture Endpoints ✅

**Goal:** Enable users to provide their own data through multiple input methods.

### 2.1 Screenshot Upload
- [x] `POST /api/captures/screenshot` — multipart file upload
- [x] File validation (type, size limits)
- [x] Server-side OCR (Pillow + pytesseract, with graceful fallback)
- [x] Store original image, extract text, trigger classification

### 2.2 Clipboard / Text Capture
- [x] `POST /api/captures/text` — accept raw text content
- [x] Auto-detect content type (code, URL, note, email)
- [x] Trigger classification pipeline

### 2.3 URL Capture
- [x] `POST /api/captures/url` — accept URL string
- [x] Fetch page content (title, meta description, text extract)
- [x] Store as capture with URL metadata

### 2.4 Browsing History Import
- [x] `POST /api/captures/history` — accept JSON array of history entries
- [x] Batch processing with deduplication
- [x] Create captures from history entries

---

## Phase 3: Frontend Capture UI ✅

**Goal:** Add a Capture page for users to provide data + update navigation.

### 3.1 New Capture Page
- [x] Drag-and-drop upload zone for screenshots
- [x] Clipboard paste support (Ctrl+V on the page)
- [x] Text input area for clipboard content / notes
- [x] URL input field with submit button
- [x] Browsing history JSON upload
- [x] Real-time processing status feedback
- [x] Recent captures list

### 3.2 Navigation Updates
- [x] Add "Capture" to sidebar navigation (with Upload icon)
- [x] Add to mobile bottom tab bar
- [x] Route: `/capture`

### 3.3 API Client Updates
- [x] Add capture methods to `api.ts` (uploadScreenshot, submitText, submitUrl, importHistory)
- [x] Handle multipart form data for file uploads

---

## Phase 4: Integration & Polish ✅

**Goal:** Connect all pieces, ensure everything works end-to-end.

### 4.1 Pipeline Integration
- [x] Processing pipeline works with new SQLite-stored captures
- [x] Activity stream reflects real processing events
- [x] Feed cards generated from processing results

### 4.2 Existing Pages
- [x] Feed page works with new backend
- [x] Knowledge page shows user's captures from DB
- [x] Chat works with Gemini against user's captures
- [x] About Me shows learned model

### 4.3 Configuration
- [x] Updated `.env.template` (only GEMINI_API_KEY needed)
- [x] Updated `requirements.txt` with new dependencies
- [x] Updated `README.md` with new setup instructions

---

## File Changes Summary

### New Files
| File | Description |
|------|-------------|
| `docs/PRD.md` | Product Requirements Document |
| `docs/IMPLEMENTATION_PLAN.md` | This file |
| `backend/app/main.py` | FastAPI application entry point |
| `backend/app/database.py` | SQLite database layer |
| `backend/app/models.py` | Pydantic models |
| `backend/app/routers/captures.py` | Capture endpoints (upload, text, URL, history) |
| `backend/app/routers/intelligence.py` | Processing, search, chat endpoints |
| `backend/app/routers/user.py` | Feed, user model, metrics, feedback endpoints |
| `backend/app/services/classifier.py` | Gemini-based classification service |
| `backend/app/services/pii.py` | PII detection service (regex + Gemini) |
| `backend/app/services/pipeline.py` | Processing pipeline orchestrator |
| `backend/app/services/ocr.py` | OCR service for screenshots |
| `frontend/src/pages/Capture.tsx` | New capture page |

### Modified Files
| File | Changes |
|------|---------|
| `frontend/src/App.tsx` | Add Capture route |
| `frontend/src/components/Layout.tsx` | Add Capture nav item |
| `frontend/src/lib/api.ts` | Add capture API methods |
| `requirements.txt` | Add FastAPI, SQLite, Pillow deps |
| `.env.template` | Simplify to just GEMINI_API_KEY |
| `.gitignore` | Add uploads directory, SQLite DB |
| `README.md` | Update setup instructions |

### Preserved Files (Unchanged)
- `frontend/src/pages/Feed.tsx` — works as-is with API compatibility
- `frontend/src/pages/Knowledge.tsx` — works as-is
- `frontend/src/pages/Chat.tsx` — works as-is
- `frontend/src/pages/AboutMe.tsx` — works as-is
- `frontend/src/components/FeedCard.tsx` — works as-is
- `frontend/src/components/ActivityStream.tsx` — works as-is
- `data/captures.json` — retained as seed data
- `data/app_state_seed.json` — retained as seed data
- `DEVPOST.md` — retained as hackathon documentation

### Retired Files
| File | Reason |
|------|--------|
| `backend/serve.py` | Replaced by `backend/app/` FastAPI application |

---

## Dependency Changes

### Python (requirements.txt)
```
# Web framework
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
python-multipart>=0.0.18

# Database
aiosqlite>=0.21.0

# OCR (optional — graceful fallback)
Pillow>=11.0.0

# LLM
google-genai>=1.0.0
```

### Removed Dependencies
- `autoevals` — was for Braintrust scoring (hackathon sponsor)
- `openai` — was used by autoevals
- `braintrust` — was for observability (hackathon sponsor)

---

## Environment Variables

```bash
# Required
GEMINI_API_KEY=your_gemini_api_key

# Optional
DATABASE_PATH=data/capsule.db     # Default: data/capsule.db
UPLOAD_DIR=data/uploads            # Default: data/uploads
```
