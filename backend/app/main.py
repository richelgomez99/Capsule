"""Capsule Web App — FastAPI backend.

Replaces the hackathon's stdlib HTTP server with a proper async web framework.
Provides data capture endpoints (screenshot upload, text, URL, history import),
an AI classification pipeline, and all the original API endpoints.
"""

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app import database as db
from backend.app.routers import captures, intelligence, user

# ── Logging ───────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("capsule")

# ── Load .env ─────────────────────────────────────────────
_env_file = Path(__file__).parent.parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

# ── App ───────────────────────────────────────────────────
app = FastAPI(
    title="Capsule",
    description="Your second brain that actually thinks",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(captures.router)
app.include_router(intelligence.router)
app.include_router(user.router)

# Serve uploaded files
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(Path(__file__).parent.parent.parent / "data" / "uploads")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")


@app.on_event("startup")
async def startup():
    logger.info("Initializing Capsule database...")
    db.init_db()

    # Seed from hackathon data if DB is empty
    data_path = Path(__file__).parent.parent.parent / "data" / "captures.json"
    count = db.seed_from_json(str(data_path))
    if count:
        logger.info("Seeded %d captures from hackathon data", count)

    # Load user model seed
    seed_path = Path(__file__).parent.parent.parent / "data" / "app_state_seed.json"
    if seed_path.exists():
        import json
        try:
            seed = json.loads(seed_path.read_text())
            for fact in seed.get("learned_facts", []):
                if isinstance(fact, dict) and "text" in fact:
                    db.upsert_user_model("fact", fact["text"], confidence=0.7, source="seed")
                elif isinstance(fact, str):
                    db.upsert_user_model("fact", fact, confidence=0.7, source="seed")
        except Exception as e:
            logger.warning("Failed to load user model seed: %s", e)

    total = db.capture_count()
    logger.info("Capsule ready — %d captures in database", total)


@app.on_event("shutdown")
async def shutdown():
    db.close_db()


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0.0",
        "captures": db.capture_count(),
        "name": "Capsule Web App",
    }


# ── Compatibility aliases for frontend ────────────────────
# The original frontend hits /api/agent/stream — provide a simple fallback
@app.get("/api/agent/stream")
async def agent_stream():
    """SSE-compatible endpoint (returns recent activity as JSON for now)."""
    return db.list_activity(limit=20)
