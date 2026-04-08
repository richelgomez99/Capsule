"""Gemini-based classification service for captures."""

import json
import logging
import os
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

VALID_CATEGORIES = [
    "code", "recipe", "research", "shopping", "personal",
    "communication", "documentation", "reference", "error",
]

CLASSIFY_PROMPT = """You are a content classifier for a personal knowledge management app called Capsule.
Analyze the following content and return a JSON object with:
- "category": one of {categories}
- "tags": array of 3-5 relevant tags (lowercase, single words or short phrases)
- "summary": a concise 1-2 sentence summary of the content
- "source_app": best guess at the source application (e.g., "Chrome", "VS Code", "Slack", etc.) or empty string if unknown
- "confidence": your confidence in the classification from 0.0 to 1.0

Content type: {content_type}
Content:
{content}

Return ONLY valid JSON, no markdown formatting."""

SELF_EVAL_PROMPT = """You are a quality evaluator. Rate this classification:

Content: {content}
Category: {category}
Tags: {tags}
Summary: {summary}

Rate the quality as one of: A (excellent), B (good), C (okay), D (poor).
Also provide a confidence score from 0.0 to 1.0.

Return ONLY valid JSON: {{"quality": "A/B/C/D", "confidence": 0.0-1.0, "reasoning": "brief explanation"}}"""

REFLECTION_PROMPT = """The classification below scored low confidence ({confidence}).
Please re-analyze and provide an improved classification.

Content: {content}
Original category: {category}
Original tags: {tags}

Return ONLY valid JSON with: "category", "tags", "summary", "confidence" (should be higher).
Categories must be one of: {categories}"""


def _call_gemini(prompt: str) -> str | None:
    """Call Gemini API and return response text."""
    api_key = os.environ.get("GEMINI_API_KEY", GEMINI_API_KEY)
    if not api_key:
        return None

    url = f"{GEMINI_URL}?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024},
    }).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return text.strip()
    except Exception as e:
        logger.error("Gemini API call failed: %s", e)
        return None


def _parse_json_response(text: str) -> dict | None:
    """Extract JSON from Gemini response (may be wrapped in markdown)."""
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first and last lines (```json and ```)
        json_lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(json_lines)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse Gemini JSON response: %s", text[:200])
        return None


def classify_content(content: str, content_type: str = "text") -> dict:
    """Classify content using Gemini. Returns classification dict.

    Falls back to basic heuristics if Gemini is unavailable.
    """
    prompt = CLASSIFY_PROMPT.format(
        categories=", ".join(VALID_CATEGORIES),
        content_type=content_type,
        content=content[:3000],  # Truncate very long content
    )

    result = _call_gemini(prompt)
    parsed = _parse_json_response(result)

    if parsed:
        # Validate category
        cat = parsed.get("category", "reference").lower()
        if cat not in VALID_CATEGORIES:
            cat = "reference"
        return {
            "category": cat,
            "tags": parsed.get("tags", [])[:5],
            "summary": parsed.get("summary", ""),
            "source_app": parsed.get("source_app", ""),
            "confidence": min(1.0, max(0.0, float(parsed.get("confidence", 0.5)))),
        }

    # Fallback: basic heuristic classification
    return _heuristic_classify(content, content_type)


def self_evaluate(content: str, category: str, tags: list[str], summary: str) -> dict:
    """Self-evaluate classification quality."""
    prompt = SELF_EVAL_PROMPT.format(
        content=content[:2000],
        category=category,
        tags=", ".join(tags),
        summary=summary,
    )

    result = _call_gemini(prompt)
    parsed = _parse_json_response(result)

    if parsed:
        return {
            "quality": parsed.get("quality", "B"),
            "confidence": min(1.0, max(0.0, float(parsed.get("confidence", 0.5)))),
            "reasoning": parsed.get("reasoning", ""),
        }

    return {"quality": "B", "confidence": 0.5, "reasoning": "Self-evaluation unavailable"}


def reflect_and_reclassify(content: str, category: str, tags: list[str], confidence: float) -> dict | None:
    """Re-classify if confidence is low."""
    if confidence >= 0.7:
        return None

    prompt = REFLECTION_PROMPT.format(
        confidence=confidence,
        content=content[:3000],
        category=category,
        tags=", ".join(tags),
        categories=", ".join(VALID_CATEGORIES),
    )

    result = _call_gemini(prompt)
    parsed = _parse_json_response(result)

    if parsed:
        cat = parsed.get("category", category).lower()
        if cat not in VALID_CATEGORIES:
            cat = category
        new_conf = min(1.0, max(0.0, float(parsed.get("confidence", confidence + 0.1))))
        if new_conf > confidence:
            return {
                "category": cat,
                "tags": parsed.get("tags", tags)[:5],
                "summary": parsed.get("summary", ""),
                "confidence": new_conf,
            }

    return None


def chat_with_context(message: str, context_captures: list[dict]) -> str:
    """Chat using captures as context (RAG-style)."""
    context_parts = []
    for cap in context_captures[:10]:
        context_parts.append(f"[{cap.get('category', '')}] {cap.get('summary', '')} — {cap.get('content', '')[:200]}")

    context_text = "\n\n".join(context_parts) if context_parts else "No relevant captures found."

    prompt = f"""You are Capsule, a personal knowledge assistant. Answer the user's question using ONLY the context from their saved captures below. Be helpful, concise, and cite which captures your answer comes from.

User's saved captures:
{context_text}

User's question: {message}

Answer:"""

    result = _call_gemini(prompt)
    return result or "I couldn't process that question right now. Make sure your Gemini API key is configured."


def _heuristic_classify(content: str, content_type: str) -> dict:
    """Basic heuristic classification when Gemini is unavailable."""
    low = content.lower()
    category = "reference"
    tags = []

    if content_type == "url":
        category = "reference"
        tags = ["bookmark", "link"]
    elif any(kw in low for kw in ["def ", "function ", "class ", "import ", "const ", "var ", "let ", "return "]):
        category = "code"
        tags = ["programming", "snippet"]
    elif any(kw in low for kw in ["recipe", "ingredient", "cook", "bake", "tablespoon", "cup of"]):
        category = "recipe"
        tags = ["food", "cooking"]
    elif any(kw in low for kw in ["error", "exception", "traceback", "failed", "stack trace"]):
        category = "error"
        tags = ["bug", "debug"]
    elif any(kw in low for kw in ["$", "price", "buy", "order", "cart", "shipping"]):
        category = "shopping"
        tags = ["purchase", "product"]
    elif any(kw in low for kw in ["research", "study", "paper", "journal", "abstract"]):
        category = "research"
        tags = ["article", "study"]
    elif any(kw in low for kw in ["hey", "hello", "dm", "message", "sent"]):
        category = "communication"
        tags = ["message", "chat"]

    return {
        "category": category,
        "tags": tags,
        "summary": content[:100] + ("..." if len(content) > 100 else ""),
        "source_app": "",
        "confidence": 0.4,
    }
