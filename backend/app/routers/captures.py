"""Capture endpoints — screenshot upload, text, URL, and browsing history import."""

import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app import database as db
from backend.app.models import (
    HistoryImportRequest,
    TextCaptureRequest,
    UrlCaptureRequest,
)
from backend.app.services import ocr, pii

router = APIRouter(prefix="/api/captures", tags=["captures"])

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(Path(__file__).parent.parent.parent.parent / "data" / "uploads")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp", "image/gif"}


@router.post("/screenshot")
async def upload_screenshot(file: UploadFile = File(...)):
    """Upload a screenshot image for OCR and classification."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}. Allowed: {', '.join(ALLOWED_TYPES)}")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large ({len(contents) // (1024*1024)} MB). Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB. Try compressing or resizing the image.")

    # Save file
    cap_id = f"cap_{uuid.uuid4().hex[:8]}"
    ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "png"
    filename = f"{cap_id}.{ext}"
    filepath = UPLOAD_DIR / filename
    filepath.write_bytes(contents)

    # OCR
    text = ocr.extract_text(str(filepath))

    # PII check
    has_pii, pii_types = pii.detect_pii(text)

    capture = {
        "id": cap_id,
        "type": "screenshot",
        "content": text,
        "raw_path": str(filepath),
        "source_app": "",
        "category": "",
        "summary": "",
        "tags": [],
        "has_pii": has_pii,
        "pii_details": pii_types,
        "confidence": 0,
        "quality": "",
        "url": "",
        "created_at": "",
    }
    db.insert_capture(capture)
    db.add_activity("CAPTURE", f"Screenshot uploaded: {file.filename or 'image'}", cap_id)

    return {"id": cap_id, "message": "Screenshot captured. Run processing to classify.", "has_pii": has_pii}


@router.post("/text")
async def capture_text(req: TextCaptureRequest):
    """Capture text/clipboard content."""
    cap_id = f"cap_{uuid.uuid4().hex[:8]}"

    has_pii, pii_types = pii.detect_pii(req.content)

    capture = {
        "id": cap_id,
        "type": "text",
        "content": req.content,
        "raw_path": "",
        "source_app": req.source,
        "category": "",
        "summary": "",
        "tags": [],
        "has_pii": has_pii,
        "pii_details": pii_types,
        "confidence": 0,
        "quality": "",
        "url": "",
        "created_at": "",
    }
    db.insert_capture(capture)
    db.add_activity("CAPTURE", f"Text captured from {req.source} ({len(req.content)} chars)", cap_id)

    return {"id": cap_id, "message": "Text captured. Run processing to classify.", "has_pii": has_pii}


@router.post("/url")
async def capture_url(req: UrlCaptureRequest):
    """Capture a URL with metadata extraction."""
    import urllib.request
    import urllib.error

    cap_id = f"cap_{uuid.uuid4().hex[:8]}"
    title = ""
    content = ""

    try:
        url_req = urllib.request.Request(
            req.url,
            headers={"User-Agent": "Mozilla/5.0 (Capsule Bot)"},
        )
        with urllib.request.urlopen(url_req, timeout=10) as resp:
            html = resp.read(50000).decode("utf-8", errors="ignore")

        # Extract title
        import re
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else req.url

        # Extract meta description
        desc_match = re.search(r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']', html, re.IGNORECASE)
        desc = desc_match.group(1).strip() if desc_match else ""

        # Strip HTML tags for content
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        content = f"{title}\n\n{desc}\n\n{text[:2000]}"

    except Exception:
        content = f"URL: {req.url}"
        title = req.url

    has_pii, pii_types = pii.detect_pii(content)

    capture = {
        "id": cap_id,
        "type": "url",
        "content": content,
        "raw_path": "",
        "source_app": "Browser",
        "category": "",
        "summary": title,
        "tags": [],
        "has_pii": has_pii,
        "pii_details": pii_types,
        "confidence": 0,
        "quality": "",
        "url": req.url,
        "created_at": "",
    }
    db.insert_capture(capture)
    db.add_activity("CAPTURE", f"URL captured: {title[:60]}", cap_id)

    return {"id": cap_id, "message": f"URL captured: {title[:60]}", "has_pii": has_pii}


@router.post("/history")
async def import_history(req: HistoryImportRequest):
    """Import browsing history entries."""
    imported = 0
    for entry in req.entries:
        cap_id = f"cap_{uuid.uuid4().hex[:8]}"

        content = f"{entry.title}\n\nURL: {entry.url}"
        has_pii, pii_types = pii.detect_pii(content)

        capture = {
            "id": cap_id,
            "type": "history",
            "content": content,
            "raw_path": "",
            "source_app": "Browser",
            "category": "",
            "summary": entry.title or entry.url,
            "tags": [],
            "has_pii": has_pii,
            "pii_details": pii_types,
            "confidence": 0,
            "quality": "",
            "url": entry.url,
            "created_at": entry.visit_time or "",
        }
        db.insert_capture(capture)
        imported += 1

    db.add_activity("CAPTURE", f"Imported {imported} browsing history entries")

    return {"message": f"Imported {imported} history entries. Run processing to classify.", "imported": imported}


@router.get("")
async def list_captures(category: str | None = None, limit: int = 200):
    """List all captures, optionally filtered by category."""
    return db.list_captures(category=category, limit=limit)


@router.get("/{capture_id}")
async def get_capture(capture_id: str):
    """Get a single capture by ID."""
    capture = db.get_capture(capture_id)
    if not capture:
        raise HTTPException(404, "Capture not found")
    return capture


@router.delete("/{capture_id}")
async def delete_capture(capture_id: str):
    """Delete a capture."""
    if not db.delete_capture(capture_id):
        raise HTTPException(404, "Capture not found")
    return {"message": "Capture deleted"}
