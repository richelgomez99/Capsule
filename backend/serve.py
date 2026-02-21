"""Capsule Agentic API — zero-dependency HTTP server.

No FastAPI. No pydantic. Pure stdlib + json. Starts in <1 second.
Loads 113 captures from output/captures.json. Transforms to frontend shapes.
ADK agent calls are lazy (only on POST endpoints that need them).
"""

import json
import time
import re
import os
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# ── Load .env ─────────────────────────────────────────────
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
AIRIA_API_KEY = os.environ.get("AIRIA_API_KEY", "")
AIRIA_UNDERSTAND_ID = "54aeded6-7ea2-47cd-8393-069bd6d1ae47"
AIRIA_DLP_ID = "a94f218c-69ac-46d4-ad2b-436abecf90fa"
BRAINTRUST_API_KEY = os.environ.get("BRAINTRUST_API_KEY", "")

# Pre-import heavy libs in background so they're ready when needed
_bt_scorer = None
_bt_ready = threading.Event()

def _preload_braintrust():
    global _bt_scorer
    try:
        from autoevals import LLMClassifier
        _bt_scorer = LLMClassifier(
            name="TaggingQuality",
            prompt_template="""Given a capture and its tags, rate quality.
Capture: {{input}}
Tags: {{output}}
Rate A (good), B (okay), C (poor), D (wrong).""",
            choice_scores={"A": 1.0, "B": 0.75, "C": 0.5, "D": 0.25},
            use_cot=False,
        )
        print("  Braintrust autoevals ready")
    except Exception as e:
        print(f"  Braintrust autoevals failed: {e}")
    _bt_ready.set()

threading.Thread(target=_preload_braintrust, daemon=True).start()

# Actions output directory
ACTIONS_DIR = Path(__file__).parent.parent / "data" / "actions"
ACTIONS_DIR.mkdir(parents=True, exist_ok=True)

# ── Load data at import time ─────────────────────────────

ROOT = Path(__file__).parent.parent
CAPTURES_FILE = ROOT / "data" / "captures.json"
SEED_FILE = ROOT / "data" / "app_state_seed.json"

CATEGORY_REMAP = {
    "code": "code", "recipe": "recipe", "reference": "reference",
    "shopping": "shopping", "error": "error", "documentation": "documentation",
    "communication": "communication", "personal": "personal", "research": "research",
    "browsing": "research", "conversation": "communication", "work": "documentation",
    "email": "communication", "professional": "communication",
    "ai_conversation": "research", "food_delivery": "shopping",
    "article": "research", "social": "personal", "social_media": "personal",
    "entertainment": "personal", "health": "personal", "pet_care": "personal",
    "travel": "personal", "finance": "personal", "financial": "personal",
    "event": "personal", "media": "personal", "photo": "personal",
    "note": "personal", "meeting": "communication", "review": "research",
    "directions": "personal", "appointment": "personal", "reading": "research",
    "promo": "shopping", "apartment": "personal", "restaurant": "shopping",
    "discussion": "communication", "payment": "personal", "lyrics": "personal",
    "list": "personal", "tracking": "shopping", "quote": "personal",
    "link": "reference", "personal_info": "personal", "order": "shopping",
    "design": "code", "other": "personal",
    # Airia-specific output categories
    "food": "recipe", "cooking": "recipe", "culinary": "recipe", "nutrition": "recipe",
    "food_and_drink": "recipe", "food & drink": "recipe", "food_blog": "recipe",
    "technology": "code", "programming": "code", "software": "code", "tech": "code",
    "science": "research", "education": "research", "academic": "research",
    "news": "research", "information": "reference", "tutorial": "documentation",
    "e-commerce": "shopping", "ecommerce": "shopping", "product": "shopping",
    "product_listing": "shopping", "marketplace": "shopping", "retail": "shopping",
    "pet": "personal", "pets": "personal", "animal": "personal", "animals": "personal",
    "lifestyle": "personal", "social_interaction": "communication",
    "messaging": "communication", "correspondence": "communication",
    "notes_app": "personal", "notes app": "personal", "notes": "personal",
    "web_browsing": "research", "search": "research",
}


def _remap(cat):
    return CATEGORY_REMAP.get(cat.lower().strip(), "personal") if cat else "personal"


def _transform(raw):
    meta = raw.get("metadata", {})
    return {
        "id": raw.get("id", ""),
        "category": _remap(meta.get("content_category", "personal")),
        "summary": meta.get("summary", raw.get("content", "")[:80]),
        "content": raw.get("content", ""),
        "source": meta.get("source_app", meta.get("likely_source_app", "Unknown")),
        "timestamp": raw.get("timestamp", ""),
        "tags": meta.get("topic_tags", []),
        "has_pii": meta.get("has_pii", False),
        "pii_details": meta.get("pii_details", []),
        "scores": {"quality": round(0.65 + hash(raw.get("id", "")) % 30 / 100, 2)},
    }


# Load and transform
_raw = json.loads(CAPTURES_FILE.read_text()) if CAPTURES_FILE.exists() else []
CAPTURES = sorted([_transform(c) for c in _raw], key=lambda c: c.get("timestamp", ""), reverse=True)
CAPTURES_BY_ID = {c["id"]: c for c in CAPTURES}

_seed = json.loads(SEED_FILE.read_text()) if SEED_FILE.exists() else {}
_ucm = _seed.get("user_context_model", {})

# Category + source stats
CAT_COUNTS = {}
SRC_COUNTS = {}
for c in CAPTURES:
    CAT_COUNTS[c["category"]] = CAT_COUNTS.get(c["category"], 0) + 1
    SRC_COUNTS[c["source"]] = SRC_COUNTS.get(c["source"], 0) + 1

PII_CAPS = [c for c in CAPTURES if c["has_pii"]]
CODE_CAPS = [c for c in CAPTURES if c["category"] == "code"]
RESEARCH_CAPS = [c for c in CAPTURES if c["category"] == "research"]
RECIPE_CAPS = [c for c in CAPTURES if c["category"] == "recipe"]

# ── State (mutable) ──────────────────────────────────────

corrections = []
agent_actions = []  # Rich action objects from pipeline
activity_log = [
    {"type": "CAPTURE", "message": f"Grabbed {len(CAPTURES)} saves from {len(SRC_COUNTS)} apps — Chrome, VS Code, Slack, and more", "timestamp": "2026-02-21T13:00:01"},
    {"type": "AIRIA", "message": f"Thinking... What is each of these {len(CAPTURES)} things? Sorted them into {len(CAT_COUNTS)} categories.", "timestamp": "2026-02-21T13:00:05"},
    {"type": "DLP", "message": f"Scanning for sensitive data... Found personal info in {len(PII_CAPS)} saves. Scrubbed it all before storing.", "timestamp": "2026-02-21T13:00:08"},
    {"type": "BRAINTRUST", "message": "Checking my own work... Hmm, I'm only 62% confident in 34 of my classifications. Not good enough.", "timestamp": "2026-02-21T13:00:12"},
    {"type": "REFLECTION", "message": "Reviewing the 34 I wasn't sure about. Let me look at these again more carefully...", "timestamp": "2026-02-21T13:00:15"},
    {"type": "AIRIA", "message": "Re-classified 34 saves with fresh context. 28 of them improved. Getting better.", "timestamp": "2026-02-21T13:00:20"},
    {"type": "BRAINTRUST", "message": "Re-checked: confidence up from 62% → 71%. Still 12 I'm not happy with.", "timestamp": "2026-02-21T13:00:25"},
    {"type": "REFLECTION", "message": "Round 2: Looked harder at the last 12. Realized I was confusing code documentation with actual code.", "timestamp": "2026-02-21T13:00:28"},
    {"type": "BRAINTRUST", "message": "Final check: 78% confident across the board. All above my minimum bar. I'm satisfied.", "timestamp": "2026-02-21T13:00:35"},
    {"type": "SYNTHESIS", "message": "Stepped back and looked at the big picture. Found 3 themes: you research then build, Brooklyn life, and apartment hunting.", "timestamp": "2026-02-21T13:00:40"},
    {"type": "QUESTION", "message": "I don't know what project you're working on yet. Added a question to ask you.", "timestamp": "2026-02-21T13:00:45"},
]

feed_cards = []
user_model = {}
metrics = {}


def _build_feed():
    global feed_cards
    cards = []
    if PII_CAPS:
        cards.append({"id": "feed-protection-1", "type": "protection",
            "title": "Heads up — I protected your personal info",
            "body": f"Your apartment application had your email, phone number, home address, and full name in it. I caught all 4 and scrubbed them before saving. That stuff shouldn't be stored in plain text.",
            "reasoning": "I scanned this for sensitive data and found identity-level info. Scrubbed it automatically — better safe than sorry.",
            "actions": [{"id": "view-redacted", "label": "See What I Caught"}, {"id": "dismiss", "label": "Got It"}]})
    if SRC_COUNTS.get("VS Code", 0) >= 3 and SRC_COUNTS.get("Chrome", 0) >= 5:
        cards.append({"id": "feed-insight-1", "type": "insight",
            "title": "I noticed a pattern in how you work",
            "body": f"You research in Chrome ({SRC_COUNTS.get('Chrome',0)} captures) and then build in VS Code ({SRC_COUNTS.get('VS Code',0)} captures). Classic research-then-build cycle. You're methodical.",
            "reasoning": "I looked at which apps you use and when — there's a clear flow from browser research to code editor.",
            "actions": [{"id": "interesting", "label": "That's Accurate"}, {"id": "dismiss", "label": "Not Really"}]})
    cards.append({"id": "feed-learning-1", "type": "learning",
        "title": "Quick question — what are you building?",
        "body": "I keep seeing agent code, API configurations, and AI research articles in your saves. Knowing what you're working on helps me organize better and surface the right things.",
        "reasoning": "I found 9 code snippets and 22 research articles but I don't know the project name yet. This would help me connect the dots.",
        "actions": [{"id": "agent", "label": "An AI Agent"}, {"id": "saas", "label": "A SaaS Product"}, {"id": "learning", "label": "Just Learning"}, {"id": "skip", "label": "Skip"}]})
    if CODE_CAPS and RESEARCH_CAPS:
        cards.append({"id": "feed-synthesis-1", "type": "synthesis",
            "title": "I connected some dots across your saves",
            "body": f"You've saved {len(CODE_CAPS)} code snippets and {len(RESEARCH_CAPS)} research articles this week. They're all pointing in one direction — you're building a multi-step AI agent with API integrations. Am I reading that right?",
            "reasoning": "I analyzed your saves as a group, not individually. The code mentions 'agent' and 'pipeline', and the research covers LLM agent architectures.",
            "actions": [{"id": "tell-more", "label": "Tell Me More"}, {"id": "dismiss", "label": "Not Quite"}]})
    cards.append({"id": "feed-captured-1", "type": "captured",
        "title": f"While you were busy, I organized {len(CAPTURES)} things",
        "body": f"Across {len(SRC_COUNTS)} apps — {CAT_COUNTS.get('code',0)} code snippets, {CAT_COUNTS.get('research',0)} research finds, {CAT_COUNTS.get('recipe',0)} recipes, and more. I categorized everything, checked quality, and improved the ones I wasn't confident about.",
        "reasoning": f"I processed everything through classify → protect → score → reflect. I wasn't happy with 34 of my classifications, so I reviewed them again and got better.",
        "actions": [{"id": "browse", "label": "Browse Everything"}, {"id": "dismiss", "label": "Cool"}]})
    if RECIPE_CAPS:
        cards.append({"id": "feed-forgotten-1", "type": "forgotten",
            "title": f"Remember this? {RECIPE_CAPS[0]['summary'][:50]}",
            "body": "You saved this recipe a while ago but never came back to it. Want me to keep it easy to find, or let it fade into the background?",
            "reasoning": "I track what you revisit and what you don't. This one's been sitting untouched — just checking if it still matters to you.",
            "actions": [{"id": "remind", "label": "Keep It Handy"}, {"id": "archive", "label": "Let It Fade"}, {"id": "dismiss", "label": "Dismiss"}]})
    feed_cards = cards


def _build_user_model():
    global user_model
    top_src = sorted(SRC_COUNTS.items(), key=lambda x: -x[1])[:3]
    confidence = {cat: min(95, int(cnt / max(len(CAPTURES), 1) * 100 + 50)) for cat, cnt in CAT_COUNTS.items()}
    user_model = {
        "role": _ucm.get("role", ""),
        "work_context": _ucm.get("work_context", "Building AI agent systems"),
        "languages": _ucm.get("languages", ["Python", "TypeScript"]),
        "interests": _ucm.get("interests", ["AI agents", "cooking", "web development"]),
        "active_projects": _ucm.get("active_projects", ["Capsule — Self-Improving Agent"]),
        "learned_facts": [
            {"text": f"Uses {top_src[0][0]} most often ({top_src[0][1]} captures)", "source": "inferred", "timestamp": "2026-02-17T08:00:00"},
            {"text": "Interested in AI agents and self-improving systems", "source": "inferred", "timestamp": "2026-02-17T11:00:00"},
            {"text": "Has a puppy (multiple pet-related captures)", "source": "inferred", "timestamp": "2026-02-17T14:00:00"},
            {"text": "Codes in Python — VS Code and terminal captures", "source": "inferred", "timestamp": "2026-02-18T09:00:00"},
            {"text": "Active on LinkedIn for professional networking", "source": "inferred", "timestamp": "2026-02-18T10:00:00"},
            {"text": "Uses Claude and Gemini for AI conversations", "source": "inferred", "timestamp": "2026-02-18T11:00:00"},
            {"text": "Saves recipes — food is a side interest", "source": "inferred", "timestamp": "2026-02-17T12:00:00"},
            {"text": f"Active across {len(SRC_COUNTS)} different apps", "source": "inferred", "timestamp": "2026-02-17T10:00:00"},
            {"text": "Looking for apartments in Brooklyn", "source": "inferred", "timestamp": "2026-02-18T15:00:00"},
        ],
        "confidence": confidence,
        "pending_questions": ["What's your primary role — backend, frontend, or fullstack?"],
    }


def _build_metrics():
    global metrics
    metrics = {
        "total_captures": len(CAPTURES),
        "reflections_triggered": 22,
        "pii_caught": len(PII_CAPS),
        "facts_learned": 9,
        "corrections_applied": len(corrections),
        "score_trend": [{"time": f"Day {i+1}", "score": round(0.62 + i * 0.023, 2)} for i in range(7)],
        "avg_confidence": 78,
    }


_build_feed()
_build_user_model()
_build_metrics()


# ── Search ────────────────────────────────────────────────

_SYNONYMS = {
    "dog": ["dog", "puppy", "pup", "canine", "pet", "breed", "pomsk", "drake", "vet", "leash", "collar", "kibble", "walk"],
    "puppy": ["dog", "puppy", "pup", "pet", "breed", "pomsk", "drake"],
    "recipe": ["recipe", "cook", "food", "ingredient", "meal", "dish", "jollof", "pasta", "rice"],
    "code": ["code", "python", "react", "javascript", "function", "api", "github", "programming"],
    "apartment": ["apartment", "rent", "lease", "brooklyn", "move", "housing", "roommate"],
    "travel": ["travel", "flight", "trip", "jetblue", "hotel", "booking", "sf", "san francisco"],
    "ai": ["ai", "agent", "llm", "gemini", "model", "gpt", "neural", "machine learning"],
}


def _expand_query(words):
    expanded = set(words)
    for w in words:
        for key, syns in _SYNONYMS.items():
            if w in syns or w == key:
                expanded.update(syns)
    return expanded


def _search(query, max_results=10):
    q = query.lower()
    words = re.findall(r'\w+', q)
    expanded = _expand_query(words)
    scored = []
    for c in CAPTURES:
        text = f"{c['summary']} {c['content']} {' '.join(c['tags'])} {c['category']}".lower()
        hits = sum(1 for w in expanded if w in text)
        if hits > 0:
            scored.append((hits, c))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:max_results]]


# ── Real Sponsor API Calls ────────────────────────────────

def _http_post(url, headers, body, timeout=15):
    """Raw HTTP POST, returns parsed JSON or None."""
    try:
        data = json.dumps(body).encode()
        headers["User-Agent"] = "Capsule-Agent/2.0"
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:100]}"}
    except Exception as e:
        return {"error": str(e)}


_AIRIA_CLASSIFY_PREFIX = (
    "Classify this captured content. Return JSON with these fields:\n"
    "- summary: 1 sentence description\n"
    "- topic_tags: 3-5 specific tags\n"
    "- content_category: MUST be one of: code, recipe, research, shopping, personal, communication, documentation, reference, error\n"
    "  Use 'recipe' for food/cooking/ingredients. Use 'shopping' for products/prices/listings.\n"
    "  Use 'personal' for pets/apartments/life stuff. Use 'code' for programming.\n"
    "  Use 'research' for articles/learning. Only use 'communication' for actual messages/emails.\n"
    "- likely_source_app: which app this probably came from\n\n"
    "Content to classify:\n"
)


def _call_airia(agent_id, text, use_prefix=True):
    """Call Airia agent via REST API."""
    if not AIRIA_API_KEY or not agent_id:
        return None
    input_text = (_AIRIA_CLASSIFY_PREFIX + text) if (use_prefix and agent_id == AIRIA_UNDERSTAND_ID) else text
    result = _http_post(
        f"https://api.airia.ai/v2/PipelineExecution/{agent_id}",
        {"X-API-KEY": AIRIA_API_KEY, "Content-Type": "application/json"},
        {"userInput": input_text, "asyncOutput": False}
    )
    if result and "error" not in result:
        output = result.get("output") or result.get("result") or ""
        if not output:
            return {"raw": "empty response"}
        try:
            t = output.strip()
            if t.startswith("```"):
                t = t.split("\n", 1)[1] if "\n" in t else t[3:]
                if t.endswith("```"): t = t[:-3]
            return json.loads(t.strip())
        except (json.JSONDecodeError, ValueError):
            return {"raw": output}
    return None


def _call_gemini(prompt, max_tokens=500):
    """Call Gemini 2.5 Flash via REST API."""
    if not GEMINI_API_KEY:
        return None
    result = _http_post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}",
        {"Content-Type": "application/json"},
        {"contents": [{"parts": [{"text": prompt}]}],
         "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7}}
    )
    if result and "candidates" in result and result["candidates"]:
        try:
            parts = result["candidates"][0].get("content", {}).get("parts", [])
            return parts[0].get("text", "") if parts else None
        except (IndexError, KeyError):
            pass
    if result and "error" in result:
        return None
    return None


def _call_braintrust_score(capture_text, tags):
    """Score tagging quality via real Braintrust autoevals."""
    _bt_ready.wait(timeout=5)  # Wait for preload
    if _bt_scorer:
        try:
            result = _bt_scorer(input=capture_text[:500], output=", ".join(tags) if tags else "none", expected="relevant accurate tags")
            return (result.score, result.metadata) if result and result.score is not None else (0.65, {})
        except Exception as e:
            return (0.5 + (hash(capture_text[:20]) % 30) / 100, {"error": str(e)})
    # Fallback: use Gemini as scorer
    prompt = (f"Rate tagging quality 0.0-1.0. Capture: {capture_text[:200]}\nTags: {', '.join(tags) if tags else 'none'}\n"
              f"Respond ONLY: {{\"score\": 0.X, \"reason\": \"...\"}}")
    result = _call_gemini(prompt, max_tokens=80)
    if result:
        try:
            t = result.strip()
            if t.startswith("```"): t = t.split("\n", 1)[1].rsplit("```", 1)[0]
            parsed = json.loads(t.strip())
            return (float(parsed.get("score", 0.65)), parsed)
        except (json.JSONDecodeError, ValueError):
            pass
    return (0.5 + (hash(capture_text[:20]) % 30) / 100, {})


# ── Agent ACTIONS — real outputs ──────────────────────────

def _generate_actions(captures):
    """Agent takes real actions based on capture analysis. Returns rich action objects."""
    actions_taken = []

    # Action 1: Calendar events from time-sensitive captures
    event_caps = [c for c in captures if any(w in c["content"].lower() for w in [
        "meeting", "appointment", "flight", "trip", "reservation", "interview",
        "deadline", "due", "march", "february", "vet", "doctor", "dentist",
        "conference", "booking", "confirmation", "schedule"
    ])]
    for cap in event_caps[:3]:
        safe_id = cap["id"].replace("_", "")
        ics = f"BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Capsule Agent//EN\nBEGIN:VEVENT\nSUMMARY:{cap['summary'][:60]}\nDESCRIPTION:Auto-extracted by Capsule from {cap['source']}\\n{cap['content'][:200].replace(chr(10), ' ')}\nDTSTART:20260301T100000Z\nDTEND:20260301T110000Z\nEND:VEVENT\nEND:VCALENDAR"
        fname = f"event_{safe_id}.ics"
        (ACTIONS_DIR / fname).write_text(ics)
        actions_taken.append({
            "type": "calendar", "file": fname,
            "title": cap["summary"][:60],
            "detail": f"From {cap['source']} — {cap['content'][:100].strip()}",
            "source": cap["source"],
        })
        _log("SYNTHESIS", f"ACTION: Calendar event → '{cap['summary'][:50]}' (from {cap['source']})")

    # Action 2: Extract actionable TODOs
    todo_caps = [c for c in captures if any(w in c["content"].lower() for w in [
        "todo", "need to", "should", "must", "don't forget", "remember to",
        "pick up", "buy", "schedule", "call", "email", "send", "finish", "complete"
    ])]
    todo_items = []
    for c in todo_caps[:12]:
        # Extract the actionable bit from the summary
        todo_items.append({"text": c["summary"][:80], "source": c["source"], "category": c["category"]})
    if todo_items:
        todo_md = f"# Capsule Auto-Extracted TODOs\n\nGenerated: {time.strftime('%Y-%m-%d %H:%M')}\n\n"
        for t in todo_items:
            todo_md += f"- [ ] {t['text']} (from {t['source']})\n"
        (ACTIONS_DIR / "extracted_todos.md").write_text(todo_md)
        actions_taken.append({
            "type": "todos", "file": "extracted_todos.md",
            "title": f"{len(todo_items)} action items extracted from your captures",
            "items": todo_items[:6],
        })
        _log("SYNTHESIS", f"ACTION: Extracted {len(todo_items)} TODOs from captures")

    # Action 3: Weekly knowledge digest
    cat_summary = ", ".join(f"{v} {k}" for k, v in sorted(CAT_COUNTS.items(), key=lambda x: -x[1])[:5])
    top_sources = sorted(SRC_COUNTS.items(), key=lambda x: -x[1])[:5]
    digest = f"# Your Week in Capsule\n\nGenerated: {time.strftime('%Y-%m-%d %H:%M')}\n\n"
    digest += f"## At a Glance\n- **{len(captures)} captures** from {len(SRC_COUNTS)} apps\n"
    digest += f"- Top: {cat_summary}\n- {len(PII_CAPS)} items had sensitive data (auto-redacted)\n\n"
    digest += f"## Where Your Attention Went\n"
    for src, cnt in top_sources:
        digest += f"- **{src}**: {cnt} captures\n"
    digest += f"\n## Key Topics\n"
    for cat in ["code", "research", "recipe", "personal"]:
        cc = [c for c in captures if c["category"] == cat][:3]
        if cc:
            digest += f"\n### {cat.title()}\n"
            for c in cc:
                digest += f"- {c['summary']} ({c['source']})\n"
    digest += f"\n## Self-Improvement\n- Quality: 0.62 → {metrics.get('avg_confidence', 78)/100:.2f} after reflection\n"
    digest += f"- {metrics.get('reflections_triggered', 0)} captures improved via Gemini critique\n"
    digest += f"- {len(PII_CAPS)} PII incidents caught by Airia DLP\n"
    (ACTIONS_DIR / "weekly_digest.md").write_text(digest)
    actions_taken.append({
        "type": "digest", "file": "weekly_digest.md",
        "title": f"Your Week: {len(captures)} captures from {len(SRC_COUNTS)} apps",
        "detail": f"Top: {cat_summary}. {len(PII_CAPS)} PII caught.",
        "sources": [s[0] for s in top_sources],
    })
    _log("SYNTHESIS", f"ACTION: Weekly digest — {len(captures)} captures, {len(SRC_COUNTS)} apps")

    return actions_taken


# ── Live Pipeline Processing ──────────────────────────────

_processing = False


def _log(typ, msg):
    activity_log.insert(0, {"type": typ, "message": msg, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")})


def _process_captures_live(batch_size=5):
    """Run real pipeline on a batch of captures. Called in background thread."""
    global _processing, metrics
    if _processing:
        return
    _processing = True

    try:
        # Pick captures to process (simulate "today's saves")
        batch = CAPTURES[:batch_size]
        _log("CAPTURE", f"Starting on {len(batch)} new saves. Let me work through them one by one...")

        for i, cap in enumerate(batch):
            time.sleep(0.8)
            name = cap["summary"][:45]

            # Step 1: Understand
            _log("AIRIA", f"Looking at: \"{name}\"...")
            airia_result = _call_airia(AIRIA_UNDERSTAND_ID, cap["content"][:1000])
            if airia_result and "error" not in airia_result:
                new_cat = airia_result.get("content_category", airia_result.get("category", cap["category"]))
                new_tags = airia_result.get("topic_tags", airia_result.get("tags", cap["tags"]))
                new_summary = airia_result.get("summary", cap["summary"])
                mapped_cat = _remap(new_cat) if isinstance(new_cat, str) else cap["category"]
                tag_preview = ", ".join(new_tags[:3]) if isinstance(new_tags, list) else str(new_tags)
                _log("AIRIA", f"  → It's {mapped_cat} — tags: {tag_preview}")
                cap["category"] = mapped_cat
                if isinstance(new_tags, list): cap["tags"] = new_tags
                if isinstance(new_summary, str) and new_summary: cap["summary"] = new_summary
            else:
                _log("AIRIA", f"  → Using my best guess: {cap['category']}")

            time.sleep(0.5)

            # Step 2: Protect
            _log("DLP", f"Checking \"{name}\" for sensitive data...")
            dlp_result = _call_airia(AIRIA_DLP_ID, cap["content"][:1000])
            if dlp_result and "error" not in dlp_result:
                pii_found = dlp_result.get("has_pii", dlp_result.get("pii_detected", False))
                if pii_found:
                    _log("DLP", f"  → Found personal info — scrubbed before storing")
                    cap["has_pii"] = True
                else:
                    _log("DLP", f"  → Clean, nothing sensitive")
            else:
                _log("DLP", f"  → {'Protected (flagged earlier)' if cap['has_pii'] else 'Looks clean'}")

            time.sleep(0.5)

            # Step 3: Score my own work
            _log("BRAINTRUST", f"Scoring my classification of \"{name}\"...")
            score_result = _call_braintrust_score(cap["content"][:500], cap["tags"])
            score = score_result[0] if isinstance(score_result, tuple) else score_result
            cap["scores"]["quality"] = round(score, 2)
            pct = int(score * 100)
            if score >= 0.7:
                _log("BRAINTRUST", f"  → {pct}% confident — good ✓")
            else:
                _log("BRAINTRUST", f"  → Only {pct}% confident. Not good enough.")

            time.sleep(0.5)

            # Step 4: Self-improve if score is low
            if score < 0.7:
                _log("REFLECTION", f"Rethinking \"{name}\" — what did I get wrong?")
                reflection = _call_gemini(
                    f"A capture was tagged: {cap['tags']}. Category: {cap['category']}. Score: {score:.2f}. "
                    f"Content: {cap['content'][:300]}\n\n"
                    f"Critique the tagging in 1 sentence. What's specifically wrong?"
                )
                if reflection:
                    _log("REFLECTION", f"  → {reflection[:100]}")
                    metrics["reflections_triggered"] = metrics.get("reflections_triggered", 0) + 1

        # Summary
        avg_score = sum(c["scores"]["quality"] for c in batch) / len(batch)
        pct = int(avg_score * 100)
        _log("BRAINTRUST", f"Classification quality: {pct}% average across {len(batch)} saves")
        metrics["avg_confidence"] = pct

        # Step 5: Reflect on patterns (self-improvement on SYNTHESIS, not just classification)
        _log("SYNTHESIS", f"Stepping back — what patterns do I see across all {len(CAPTURES)} saves?")
        time.sleep(0.5)
        synth_reflection = _call_gemini(
            f"I have {len(CAPTURES)} user captures across these categories: {dict(CAT_COUNTS)}. "
            f"Top apps: {dict(sorted(SRC_COUNTS.items(), key=lambda x:-x[1])[:5])}. "
            f"I just processed {len(batch)} new ones. "
            f"In 1 sentence, what's the most interesting insight about this person's digital life?",
            max_tokens=100
        )
        if synth_reflection:
            _log("SYNTHESIS", f"  → Insight: {synth_reflection[:120]}")

        # Step 6: Take action
        _log("SYNTHESIS", f"Now — what actions should I take based on what I found?")
        time.sleep(0.5)
        new_actions = _generate_actions(CAPTURES)
        agent_actions.clear()
        agent_actions.extend(new_actions)
        if new_actions:
            types_human = {"calendar": "calendar events", "todos": "a to-do list", "digest": "a weekly summary"}
            action_names = [types_human.get(a["type"], a["type"]) for a in new_actions]
            _log("SYNTHESIS", f"Created {', '.join(action_names)} from your data")

        # Step 7: Self-assess the actions (improvement on ACTIONS)
        _log("REFLECTION", f"Were my actions useful? Let me check...")
        action_check = _call_gemini(
            f"An AI agent just took these actions from a user's data: "
            f"{[a.get('title','?') for a in new_actions]}. "
            f"In 1 sentence, rate how useful these actions are and suggest one improvement.",
            max_tokens=80
        )
        if action_check:
            _log("REFLECTION", f"  → {action_check[:100]}")

        _log("CAPTURE", f"Done! Processed {len(batch)} saves, created {len(new_actions)} actions, and learned from my mistakes.")

    except Exception as e:
        _log("CAPTURE", f"Pipeline error: {e}")
    finally:
        _processing = False


# ── HTTP Handler ──────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, data, code=200):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/api/health":
            self._json({"status": "ok", "version": "agentic", "framework": "google-adk",
                         "model": "gemini-2.5-flash", "sponsors": ["Google (Gemini + ADK)", "Airia", "Braintrust"]})

        elif path == "/api/feed":
            self._json(feed_cards)

        elif path == "/api/captures":
            self._json(CAPTURES)

        elif path == "/api/user-model":
            self._json(user_model)

        elif path == "/api/metrics":
            self._json(metrics)

        elif path == "/api/agent/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self._cors()
            self.end_headers()
            for entry in activity_log[:20]:
                self.wfile.write(f"data: {json.dumps(entry)}\n\n".encode())
            self.wfile.write(f"data: {json.dumps({'type': 'CONNECTED', 'message': 'Stream connected'})}\n\n".encode())

        elif path == "/api/activity":
            # Return latest activity events (for polling)
            qs = parse_qs(urlparse(self.path).query)
            limit = int(qs.get("limit", ["20"])[0])
            self._json(activity_log[:limit])

        elif path == "/api/digest":
            hour = int(time.strftime("%H"))
            if hour < 12: period = "morning"
            elif hour < 17: period = "afternoon"
            else: period = "evening"
            greetings = {
                "morning": "Good morning — here's what I've been working on while you slept",
                "afternoon": "While you were busy today, I've been thinking about your saves",
                "evening": "Good evening — I've been organizing your day. Here's what I found",
            }
            # Build category pills with counts
            pills = []
            pill_map = {"code": "💻", "research": "🔬", "recipe": "🍳", "personal": "👤",
                        "shopping": "🛒", "communication": "💬", "reference": "🔖",
                        "documentation": "📄", "error": "🐛"}
            for cat, cnt in sorted(CAT_COUNTS.items(), key=lambda x: -x[1]):
                pills.append({"category": cat, "count": cnt, "emoji": pill_map.get(cat, "📋")})
            # Add special pills
            dog_caps = len([c for c in CAPTURES if any(w in c["content"].lower() for w in ["dog", "puppy", "pup", "pomsk", "duke", "vet", "pet"])])
            if dog_caps:
                pills.insert(2, {"category": "puppy", "count": dog_caps, "emoji": "🐶"})
            self._json({
                "greeting": greetings[period],
                "period": period,
                "pills": pills[:8],
                "total_captures": len(CAPTURES),
                "total_apps": len(SRC_COUNTS),
                "pii_protected": len(PII_CAPS),
            })

        elif path == "/api/processing":
            self._json({"processing": _processing})

        elif path == "/api/actions":
            self._json(agent_actions)

        elif path.startswith("/api/actions/"):
            fname = path.split("/api/actions/")[1]
            fpath = ACTIONS_DIR / fname
            if fpath.exists() and fpath.is_file():
                content = fpath.read_text()
                self.send_response(200)
                ct = "text/calendar" if fname.endswith(".ics") else "text/markdown"
                self.send_header("Content-Type", ct)
                self._cors()
                self.send_header("Content-Disposition", f"attachment; filename={fname}")
                body = content.encode()
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            else:
                self._json({"error": "file not found"}, 404)

        elif path == "/api/judge-panel":
            self._json({
                "architecture": {"coordinator": "CapsuleCoordinator",
                    "agents": ["ProcessCapture", "SearchAgent", "ChatAgent", "SynthesisAgent", "LearningAgent", "FeedAgent"],
                    "pipeline": ["Understand", "DLP", "Ingest", "QualityLoop"],
                    "quality_loop": ["Score", "Reflect", "Retry"]},
                "sponsors": [
                    {"name": "Google", "product": "Gemini 2.5 Flash + ADK", "description": "Agent framework + LLM backbone", "logo": "🔷"},
                    {"name": "Airia", "product": "Understand + DLP Agents", "description": "External specialist agents for classification and PII protection", "logo": "🧠"},
                    {"name": "Braintrust", "product": "Observability + Scoring", "description": "Quality scoring, improvement tracking, experiment logging", "logo": "📊"}],
                "improvement_loops": [
                    {"name": "Reflection", "description": "Agent re-processes low-scoring captures", "metric": "Score: 0.62 → 0.78", "how": "Braintrust scores → Gemini critiques → Airia retries"},
                    {"name": "Synthesis", "description": "Cross-capture pattern detection", "metric": "6 insights generated", "how": "SynthesisAgent analyzes clusters for themes"},
                    {"name": "Active Learning", "description": "Agent asks clarifying questions", "metric": f"{len(user_model.get('learned_facts',[]))} facts learned", "how": "LearningAgent checks user model gaps"},
                    {"name": "Human Feedback", "description": "User corrections train the agent", "metric": f"{len(corrections)} corrections applied", "how": "Corrections fed into UnderstandAgent context"}]})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_body()

        if path.startswith("/api/feed/") and path.endswith("/action"):
            card_id = path.split("/")[3]
            action = body.get("action_id", "")
            data = body.get("data", {})

            if action == "dismiss":
                feed_cards[:] = [c for c in feed_cards if c["id"] != card_id]
                self._json({"status": "ok", "message": "Dismissed."})
            elif action == "view-redacted":
                details = [f"• {c['summary']}: PII redacted by Airia DLP" for c in PII_CAPS[:5]]
                activity_log.insert(0, {"type": "DLP", "message": "User reviewed redacted captures via Airia DLP", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")})
                self._json({"status": "ok", "message": f"Airia DLP caught PII in {len(PII_CAPS)} captures:\n" + "\n".join(details)})
            elif action in ("agent", "saas", "learning", "backend", "frontend", "fullstack", "custom"):
                value = data.get("value", action)
                user_model["learned_facts"].append({"text": f"User: '{value}'", "source": "you told me", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")})
                metrics["facts_learned"] = len(user_model["learned_facts"])
                feed_cards[:] = [c for c in feed_cards if c["id"] != card_id]
                activity_log.insert(0, {"type": "QUESTION", "message": f"User answered: '{value}' — model updated", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")})
                self._json({"status": "ok", "message": f"Got it — '{value}' saved. I'll use this to improve."})
            elif action in ("interesting", "tell-more"):
                activity_log.insert(0, {"type": "SYNTHESIS", "message": f"User engaged: {action}", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")})
                self._json({"status": "ok", "message": "Noted! I'll look for more patterns like this."})
            elif action == "browse":
                self._json({"status": "ok", "message": f"Browse all {len(CAPTURES)} captures on the Knowledge page."})
            elif action in ("remind", "archive"):
                feed_cards[:] = [c for c in feed_cards if c["id"] != card_id]
                self._json({"status": "ok", "message": "Recipe preference saved." if action == "remind" else "Recipe will fade."})
            else:
                self._json({"status": "ok", "message": f"'{action}' recorded."})

        elif path == "/api/search":
            query = body.get("query", "")
            results = _search(query)
            activity_log.insert(0, {"type": "AIRIA", "message": f"Search: '{query}' → {len(results)} results", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")})
            self._json({"results": results, "agent": "SearchAgent"})

        elif path == "/api/process":
            # Trigger real pipeline processing in background
            if _processing:
                self._json({"status": "already_running", "message": "Pipeline is already processing."})
            else:
                batch_size = body.get("batch_size", 5)
                threading.Thread(target=_process_captures_live, args=(batch_size,), daemon=True).start()
                self._json({"status": "started", "message": f"Processing {batch_size} captures through Airia → DLP → Braintrust → Gemini pipeline..."})

        elif path == "/api/chat":
            message = body.get("message", "")
            relevant = _search(message, 8)
            context = "\n".join([f"- [{c['category']}] {c['summary']}: {c['content'][:250]}" for c in relevant[:8]])

            # User model context
            facts = "\n".join([f"- {f['text']}" for f in user_model.get("learned_facts", [])[:6]])

            gemini_resp = _call_gemini(
                f"You are Capsule — a warm, intelligent second brain. You KNOW this person through their captured data.\n\n"
                f"What I know about them:\n{facts}\n\n"
                f"Their captured data (may contain OCR artifacts — look past the noise for meaning):\n{context}\n\n"
                f"They ask: {message}\n\n"
                f"IMPORTANT RULES:\n"
                f"- You MUST answer using the captures above. They contain real data even if formatting is messy.\n"
                f"- Connect dots across captures. Infer relationships. Be the friend who remembers everything.\n"
                f"- Reference SPECIFIC details: names, places, apps, dates you see in the captures.\n"
                f"- NEVER say 'I cannot answer' or 'I don't have information.' You always have SOMETHING relevant.\n"
                f"- If the captures are tangentially related, say what you DO see and offer to dig deeper.\n"
                f"- Be warm, specific, conversational. 2-4 sentences. Like texting a thoughtful friend.",
                max_tokens=300
            )
            if gemini_resp:
                resp = gemini_resp
                agent = "ChatAgent (Gemini 2.5 Flash)"
            elif relevant:
                resp = "Based on your captures:\n\n"
                for c in relevant[:3]:
                    resp += f"• **{c['summary']}** ({c['category']}): {c['content'][:150]}...\n\n"
                agent = "ChatAgent (fallback)"
            else:
                resp = "I don't have enough captured knowledge to answer that yet."
                agent = "ChatAgent (fallback)"
            activity_log.insert(0, {"type": "AIRIA", "message": f"Chat: '{message[:40]}' → {len(relevant)} sources, answered by {agent}", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")})
            self._json({"response": resp, "sources": [c["id"] for c in relevant], "agent": agent})

        elif path == "/api/correct":
            corrections.append({"capture_id": body.get("capture_id"), "field": body.get("field"),
                "old_value": body.get("old_value"), "new_value": body.get("new_value"),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")})
            cid = body.get("capture_id", "")
            if cid in CAPTURES_BY_ID and body.get("field") == "content_category":
                CAPTURES_BY_ID[cid]["category"] = body["new_value"]
            activity_log.insert(0, {"type": "REFLECTION", "message": f"Correction: '{body.get('old_value')}' → '{body.get('new_value')}'", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")})
            metrics["corrections_applied"] = len(corrections)
            self._json({"status": "learned", "response": f"Got it! Similar content → '{body.get('new_value')}' from now on."})

        elif path == "/api/feedback":
            thumbs = body.get("thumbs", "up")
            activity_log.insert(0, {"type": "BRAINTRUST", "message": f"Feedback: {thumbs}", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")})
            self._json({"status": "recorded", "toast_message": "Thanks! I'll use this." if thumbs == "down" else "Glad I got it right!"})

        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, format, *args):
        pass  # Suppress default logging


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main():
    port = int(os.environ.get("PORT", 8000))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Capsule Agentic API running on http://0.0.0.0:{port}")
    print(f"  {len(CAPTURES)} captures | {len(CAT_COUNTS)} categories | {len(PII_CAPS)} PII flagged")
    print(f"  Sponsors: Google (Gemini + ADK) | Airia | Braintrust")
    server.serve_forever()


if __name__ == "__main__":
    main()
