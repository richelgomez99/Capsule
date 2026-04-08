"""User-facing endpoints — feed, user model, metrics, feedback, corrections."""

from fastapi import APIRouter

from backend.app import database as db
from backend.app.models import CorrectionRequest, FeedActionRequest, FeedbackRequest

router = APIRouter(prefix="/api", tags=["user"])


@router.get("/feed")
async def get_feed():
    """Get feed cards for the dashboard."""
    return db.list_feed_cards()


@router.post("/feed/{card_id}/action")
async def feed_action(card_id: str, req: FeedActionRequest):
    """Respond to a feed card action."""
    if req.action_id == "dismiss":
        db.dismiss_feed_card(card_id)
        return {"message": "Card dismissed."}

    # Store any learning data
    if req.data:
        for key, value in req.data.items():
            if isinstance(value, str) and value.strip():
                db.upsert_user_model(key, value.strip(), confidence=0.8, source="user_input")
                db.add_activity("QUESTION", f"Learned: {key} = {value[:50]}")

    return {"message": "Thanks! I'll remember that."}


@router.get("/user-model")
async def get_user_model():
    """Get the learned user model."""
    return db.get_user_model()


@router.get("/metrics")
async def get_metrics():
    """Get agent metrics."""
    return db.get_metrics()


@router.get("/digest")
async def get_digest():
    """Get daily digest / greeting."""
    metrics = db.get_metrics()
    total = metrics["total_captures"]
    cats = metrics["categories"]
    sources = metrics["sources"]

    pills = [
        {"category": cat, "count": count, "emoji": _cat_emoji(cat)}
        for cat, count in sorted(cats.items(), key=lambda x: -x[1])[:6]
    ]

    return {
        "greeting": f"Here's what I've been thinking about your {total} saves",
        "total_captures": total,
        "total_apps": len(sources),
        "pii_protected": metrics["pii_protected"],
        "pills": pills,
    }


@router.post("/correct")
async def correct(req: CorrectionRequest):
    """Submit a user correction."""
    db.add_correction(req.capture_id, req.field, req.old_value, req.new_value)

    # Apply correction to the capture
    if req.field == "content_category":
        db.update_capture(req.capture_id, {"category": req.new_value})
    elif req.field == "topic_tags":
        db.update_capture(req.capture_id, {"tags": [t.strip() for t in req.new_value.split(",")]})

    db.add_activity("QUESTION", f"User corrected {req.field} on {req.capture_id} → {req.new_value}")

    return {"message": f"Got it! I'll classify similar content as '{req.new_value}' from now on."}


@router.post("/feedback")
async def feedback(req: FeedbackRequest):
    """Submit thumbs up/down feedback."""
    db.add_feedback(req.capture_id, req.thumbs)
    db.add_activity("QUESTION", f"User gave 👍" if req.thumbs == "up" else f"User gave 👎 on {req.capture_id}")
    return {"message": "Thanks for the feedback!"}


@router.get("/actions")
async def list_actions():
    """List generated action files."""
    from pathlib import Path
    actions_dir = Path(__file__).parent.parent.parent.parent / "data" / "actions"
    if not actions_dir.exists():
        return []

    actions = []
    for f in actions_dir.iterdir():
        if f.is_file():
            atype = "calendar" if f.suffix == ".ics" else "document"
            actions.append({
                "file": f.name,
                "type": atype,
                "title": f.stem.replace("_", " ").title(),
            })
    return actions


@router.get("/actions/{filename}")
async def download_action(filename: str):
    """Download a generated action file."""
    import os
    from pathlib import Path
    from fastapi.responses import FileResponse
    from fastapi import HTTPException

    actions_dir = Path(__file__).parent.parent.parent.parent / "data" / "actions"

    # Prevent path traversal by only allowing filenames that exist directly in actions_dir
    if not actions_dir.exists():
        raise HTTPException(404, "Action file not found")

    # List actual files and match by name — never construct path from user input
    available_files = {f.name: f for f in actions_dir.iterdir() if f.is_file()}
    if filename not in available_files:
        raise HTTPException(404, "Action file not found")

    return FileResponse(available_files[filename])


def _cat_emoji(cat: str) -> str:
    emojis = {
        "code": "💻", "recipe": "🍳", "error": "🐛", "documentation": "📄",
        "reference": "🔖", "research": "🔬", "communication": "💬",
        "shopping": "🛒", "personal": "👤",
    }
    return emojis.get(cat, "📋")
