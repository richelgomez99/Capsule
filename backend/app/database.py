"""SQLite database layer for Capsule web app."""

import json
import os
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DATABASE_PATH = os.environ.get("DATABASE_PATH", str(Path(__file__).parent.parent.parent / "data" / "capsule.db"))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS captures (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    content     TEXT,
    raw_path    TEXT,
    source_app  TEXT DEFAULT '',
    category    TEXT DEFAULT '',
    summary     TEXT DEFAULT '',
    tags        TEXT DEFAULT '[]',
    has_pii     INTEGER DEFAULT 0,
    pii_details TEXT DEFAULT '[]',
    confidence  REAL DEFAULT 0,
    quality     TEXT DEFAULT '',
    url         TEXT DEFAULT '',
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS corrections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    capture_id  TEXT NOT NULL,
    field       TEXT NOT NULL,
    old_value   TEXT,
    new_value   TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (capture_id) REFERENCES captures(id)
);

CREATE TABLE IF NOT EXISTS feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    capture_id  TEXT NOT NULL,
    thumbs      TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (capture_id) REFERENCES captures(id)
);

CREATE TABLE IF NOT EXISTS activity_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,
    message     TEXT NOT NULL,
    capture_id  TEXT,
    metadata    TEXT DEFAULT '{}',
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS feed_cards (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,
    title       TEXT NOT NULL,
    body        TEXT DEFAULT '',
    reasoning   TEXT DEFAULT '',
    actions     TEXT DEFAULT '[]',
    dismissed   INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS user_model (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    confidence  REAL DEFAULT 0.5,
    source      TEXT DEFAULT '',
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);
"""


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# Module-level connection for simple operations
_conn: sqlite3.Connection | None = None


def get_db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = _get_connection()
    return _conn


def init_db() -> None:
    """Initialize database schema."""
    db = get_db()
    db.executescript(_SCHEMA)
    db.commit()


def close_db() -> None:
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None


# ── CRUD helpers ──────────────────────────────────────────


def insert_capture(capture: dict) -> dict:
    db = get_db()
    db.execute(
        """INSERT INTO captures (id, type, content, raw_path, source_app, category,
           summary, tags, has_pii, pii_details, confidence, quality, url, created_at)
           VALUES (:id, :type, :content, :raw_path, :source_app, :category,
           :summary, :tags, :has_pii, :pii_details, :confidence, :quality, :url, :created_at)""",
        {
            "id": capture["id"],
            "type": capture.get("type", "text"),
            "content": capture.get("content", ""),
            "raw_path": capture.get("raw_path", ""),
            "source_app": capture.get("source_app", ""),
            "category": capture.get("category", ""),
            "summary": capture.get("summary", ""),
            "tags": json.dumps(capture.get("tags", [])),
            "has_pii": 1 if capture.get("has_pii") else 0,
            "pii_details": json.dumps(capture.get("pii_details", [])),
            "confidence": capture.get("confidence", 0),
            "quality": capture.get("quality", ""),
            "url": capture.get("url", ""),
            "created_at": capture.get("created_at", ""),
        },
    )
    db.commit()
    return capture


def update_capture(capture_id: str, updates: dict) -> None:
    db = get_db()
    set_parts = []
    params: dict = {"id": capture_id}
    for key, value in updates.items():
        if key in ("tags", "pii_details"):
            value = json.dumps(value)
        if key == "has_pii":
            value = 1 if value else 0
        set_parts.append(f"{key} = :{key}")
        params[key] = value
    set_parts.append("updated_at = datetime('now')")
    sql = f"UPDATE captures SET {', '.join(set_parts)} WHERE id = :id"
    db.execute(sql, params)
    db.commit()


def get_capture(capture_id: str) -> dict | None:
    db = get_db()
    row = db.execute("SELECT * FROM captures WHERE id = ?", (capture_id,)).fetchone()
    return _row_to_capture(row) if row else None


def list_captures(category: str | None = None, limit: int = 200) -> list[dict]:
    db = get_db()
    if category and category != "all":
        rows = db.execute(
            "SELECT * FROM captures WHERE category = ? ORDER BY created_at DESC LIMIT ?",
            (category, limit),
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM captures ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_capture(r) for r in rows]


def delete_capture(capture_id: str) -> bool:
    db = get_db()
    cursor = db.execute("DELETE FROM captures WHERE id = ?", (capture_id,))
    db.commit()
    return cursor.rowcount > 0


def search_captures(query: str) -> list[dict]:
    """Full-text search across captures with synonym expansion."""
    db = get_db()
    synonyms = _expand_synonyms(query)
    terms = [query.lower()] + synonyms

    all_rows = db.execute("SELECT * FROM captures ORDER BY created_at DESC").fetchall()
    scored = []
    for row in all_rows:
        cap = _row_to_capture(row)
        score = 0
        searchable = f"{cap['summary']} {cap['content']} {' '.join(cap['tags'])} {cap['category']}".lower()
        for term in terms:
            if term in searchable:
                score += searchable.count(term)
        if score > 0:
            cap["_score"] = score
            scored.append(cap)

    scored.sort(key=lambda x: x.get("_score", 0), reverse=True)
    return scored


def capture_count() -> int:
    db = get_db()
    return db.execute("SELECT COUNT(*) FROM captures").fetchone()[0]


def category_counts() -> dict[str, int]:
    db = get_db()
    rows = db.execute(
        "SELECT category, COUNT(*) as cnt FROM captures GROUP BY category"
    ).fetchall()
    return {r["category"]: r["cnt"] for r in rows}


# ── Activity Log ──────────────────────────────────────────


def add_activity(type_: str, message: str, capture_id: str = "", metadata: dict | None = None) -> None:
    db = get_db()
    db.execute(
        "INSERT INTO activity_log (type, message, capture_id, metadata) VALUES (?, ?, ?, ?)",
        (type_, message, capture_id, json.dumps(metadata or {})),
    )
    db.commit()


def list_activity(limit: int = 30) -> list[dict]:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    return [
        {
            "type": r["type"],
            "message": r["message"],
            "capture_id": r["capture_id"],
            "timestamp": r["created_at"],
        }
        for r in rows
    ]


# ── Feed Cards ────────────────────────────────────────────


def insert_feed_card(card: dict) -> None:
    db = get_db()
    db.execute(
        """INSERT OR REPLACE INTO feed_cards (id, type, title, body, reasoning, actions)
           VALUES (:id, :type, :title, :body, :reasoning, :actions)""",
        {
            "id": card["id"],
            "type": card["type"],
            "title": card["title"],
            "body": card.get("body", ""),
            "reasoning": card.get("reasoning", ""),
            "actions": json.dumps(card.get("actions", [])),
        },
    )
    db.commit()


def list_feed_cards() -> list[dict]:
    db = get_db()
    rows = db.execute(
        "SELECT * FROM feed_cards WHERE dismissed = 0 ORDER BY created_at DESC"
    ).fetchall()
    return [
        {
            "id": r["id"],
            "type": r["type"],
            "title": r["title"],
            "body": r["body"],
            "reasoning": r["reasoning"],
            "actions": json.loads(r["actions"]),
        }
        for r in rows
    ]


def dismiss_feed_card(card_id: str) -> None:
    db = get_db()
    db.execute("UPDATE feed_cards SET dismissed = 1 WHERE id = ?", (card_id,))
    db.commit()


# ── Corrections & Feedback ────────────────────────────────


def add_correction(capture_id: str, field: str, old_value: str, new_value: str) -> None:
    db = get_db()
    db.execute(
        "INSERT INTO corrections (capture_id, field, old_value, new_value) VALUES (?, ?, ?, ?)",
        (capture_id, field, old_value, new_value),
    )
    db.commit()


def add_feedback(capture_id: str, thumbs: str) -> None:
    db = get_db()
    db.execute(
        "INSERT INTO feedback (capture_id, thumbs) VALUES (?, ?)",
        (capture_id, thumbs),
    )
    db.commit()


def list_corrections() -> list[dict]:
    db = get_db()
    rows = db.execute("SELECT * FROM corrections ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


# ── User Model ────────────────────────────────────────────


def get_user_model() -> dict:
    """Return user model as a structured dict."""
    db = get_db()
    rows = db.execute("SELECT * FROM user_model ORDER BY updated_at DESC").fetchall()
    facts = [{"text": r["value"], "key": r["key"], "confidence": r["confidence"]} for r in rows]

    counts = category_counts()
    total = capture_count()

    return {
        "learned_facts": facts,
        "category_confidence": {k: min(0.95, 0.5 + v / max(total, 1) * 0.5) for k, v in counts.items()},
        "total_captures": total,
        "total_corrections": db.execute("SELECT COUNT(*) FROM corrections").fetchone()[0],
    }


def upsert_user_model(key: str, value: str, confidence: float = 0.5, source: str = "") -> None:
    db = get_db()
    existing = db.execute("SELECT id FROM user_model WHERE key = ? AND value = ?", (key, value)).fetchone()
    if existing:
        db.execute(
            "UPDATE user_model SET confidence = ?, updated_at = datetime('now') WHERE id = ?",
            (confidence, existing["id"]),
        )
    else:
        db.execute(
            "INSERT INTO user_model (key, value, confidence, source) VALUES (?, ?, ?, ?)",
            (key, value, confidence, source),
        )
    db.commit()


# ── Metrics ───────────────────────────────────────────────


def get_metrics() -> dict:
    db = get_db()
    total = capture_count()
    pii_count = db.execute("SELECT COUNT(*) FROM captures WHERE has_pii = 1").fetchone()[0]
    avg_conf = db.execute("SELECT AVG(confidence) FROM captures WHERE confidence > 0").fetchone()[0] or 0
    activity_count = db.execute("SELECT COUNT(*) FROM activity_log").fetchone()[0]
    corrections_count = db.execute("SELECT COUNT(*) FROM corrections").fetchone()[0]
    cats = category_counts()
    sources = db.execute(
        "SELECT source_app, COUNT(*) as cnt FROM captures WHERE source_app != '' GROUP BY source_app"
    ).fetchall()

    return {
        "total_captures": total,
        "pii_protected": pii_count,
        "avg_confidence": round(avg_conf, 2),
        "reflections": activity_count,
        "corrections": corrections_count,
        "categories": cats,
        "sources": {r["source_app"]: r["cnt"] for r in sources},
    }


# ── Seed Data ─────────────────────────────────────────────


def seed_from_json(json_path: str) -> int:
    """Load captures from the hackathon JSON file if DB is empty."""
    if capture_count() > 0:
        return 0

    path = Path(json_path)
    if not path.exists():
        return 0

    with open(path) as f:
        raw = json.load(f)

    count = 0
    for item in raw:
        meta = item.get("metadata", {})
        capture = {
            "id": item["id"],
            "type": item.get("type", "screenshot"),
            "content": item.get("content", ""),
            "raw_path": item.get("image_path", ""),
            "source_app": meta.get("source_app", ""),
            "category": _remap_category(meta.get("content_category", "")),
            "summary": meta.get("summary", ""),
            "tags": meta.get("topic_tags", []),
            "has_pii": meta.get("has_pii", False),
            "pii_details": meta.get("pii_details", []),
            "confidence": 0.65,
            "quality": "",
            "url": "",
            "created_at": item.get("timestamp", ""),
        }
        try:
            insert_capture(capture)
            count += 1
        except sqlite3.IntegrityError:
            pass

    return count


# ── Helpers ───────────────────────────────────────────────


CATEGORY_MAP = {
    "food": "recipe", "cooking": "recipe", "meal": "recipe", "baking": "recipe",
    "cuisine": "recipe", "restaurant": "recipe", "ingredients": "recipe",
    "programming": "code", "software": "code", "dev": "code", "coding": "code",
    "engineering": "code", "development": "code", "tech": "code", "api": "code",
    "bug": "error", "issue": "error", "debug": "error", "stack trace": "error",
    "exception": "error", "crash": "error", "failure": "error",
    "article": "research", "paper": "research", "study": "research",
    "investigation": "research", "analysis": "research", "learning": "research",
    "education": "research", "tutorial": "research", "guide": "research",
    "docs": "documentation", "readme": "documentation", "wiki": "documentation",
    "manual": "documentation", "specification": "documentation",
    "social": "communication", "chat": "communication", "message": "communication",
    "email": "communication", "slack": "communication", "text": "communication",
    "dm": "communication", "conversation": "communication",
    "purchase": "shopping", "buy": "shopping", "amazon": "shopping",
    "order": "shopping", "price": "shopping", "deal": "shopping",
    "bookmark": "reference", "link": "reference", "save": "reference",
    "note": "reference", "snippet": "reference",
    "me": "personal", "self": "personal", "life": "personal",
    "health": "personal", "fitness": "personal", "family": "personal",
    "pet": "personal", "travel": "personal", "home": "personal",
}

VALID_CATEGORIES = {"code", "recipe", "research", "shopping", "personal",
                    "communication", "documentation", "reference", "error"}


def _remap_category(raw: str) -> str:
    low = raw.lower().strip()
    if low in VALID_CATEGORIES:
        return low
    return CATEGORY_MAP.get(low, "reference")


def _row_to_capture(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "type": row["type"],
        "content": row["content"],
        "raw_path": row["raw_path"],
        "source": row["source_app"],
        "source_app": row["source_app"],
        "category": row["category"],
        "summary": row["summary"],
        "tags": json.loads(row["tags"]) if row["tags"] else [],
        "has_pii": bool(row["has_pii"]),
        "pii_details": json.loads(row["pii_details"]) if row["pii_details"] else [],
        "confidence": row["confidence"],
        "quality": row["quality"],
        "url": row["url"],
        "timestamp": row["created_at"],
        "scores": {"quality": row["quality"], "confidence": row["confidence"]},
    }


SYNONYM_MAP = {
    "dog": ["puppy", "pup", "canine", "pet", "vet", "pomsky", "husky"],
    "puppy": ["dog", "pup", "canine", "pet", "vet", "pomsky"],
    "food": ["recipe", "cooking", "meal", "restaurant", "ingredients"],
    "recipe": ["food", "cooking", "meal", "ingredients", "baking"],
    "code": ["programming", "coding", "software", "api", "developer"],
    "programming": ["code", "coding", "software", "developer"],
    "work": ["project", "task", "job", "career", "hackathon"],
    "ai": ["artificial intelligence", "machine learning", "ml", "agent", "llm"],
    "travel": ["flight", "trip", "vacation", "hotel", "airport"],
    "flight": ["travel", "trip", "airline", "airport", "jetblue"],
    "shopping": ["amazon", "purchase", "buy", "order", "deal"],
    "apartment": ["housing", "rent", "lease", "home", "address"],
}


def _expand_synonyms(query: str) -> list[str]:
    words = query.lower().split()
    expanded: list[str] = []
    for word in words:
        if word in SYNONYM_MAP:
            expanded.extend(SYNONYM_MAP[word])
    return expanded
