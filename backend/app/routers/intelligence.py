"""Intelligence endpoints — processing, search, chat."""

from fastapi import APIRouter

from backend.app import database as db
from backend.app.models import ChatRequest, ProcessRequest, SearchRequest
from backend.app.services import classifier, pipeline

router = APIRouter(prefix="/api", tags=["intelligence"])


@router.post("/process")
async def start_processing(req: ProcessRequest | None = None):
    """Trigger the classification pipeline on unprocessed captures."""
    batch_size = req.batch_size if req else 5
    if pipeline.is_processing():
        return {"message": "Already processing. Watch the activity stream for updates."}

    pipeline.process_captures(batch_size=batch_size)
    return {"message": f"Processing up to {batch_size} captures. Watch the activity stream!"}


@router.get("/processing")
async def processing_status():
    """Check if the pipeline is currently running."""
    return {"processing": pipeline.is_processing()}


@router.get("/activity")
async def get_activity(limit: int = 30):
    """Get recent activity log entries."""
    return db.list_activity(limit=limit)


@router.post("/search")
async def search(req: SearchRequest):
    """Search across all captures."""
    results = db.search_captures(req.query)
    return {"query": req.query, "count": len(results), "results": results}


@router.post("/chat")
async def chat(req: ChatRequest):
    """Chat with your knowledge base using RAG."""
    # Find relevant captures
    relevant = db.search_captures(req.message)[:10]

    # Generate answer
    answer = classifier.chat_with_context(req.message, relevant)

    return {
        "answer": answer,
        "sources": len(relevant),
        "captures_used": [c["id"] for c in relevant[:5]],
    }
