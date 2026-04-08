"""Pydantic models for request/response validation."""

from pydantic import BaseModel, Field


class TextCaptureRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=50000)
    source: str = Field(default="clipboard", max_length=100)


class UrlCaptureRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2000)


class HistoryEntry(BaseModel):
    url: str
    title: str = ""
    visit_time: str = ""


class HistoryImportRequest(BaseModel):
    entries: list[HistoryEntry] = Field(..., min_length=1, max_length=1000)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class CorrectionRequest(BaseModel):
    capture_id: str
    field: str
    old_value: str = ""
    new_value: str


class FeedbackRequest(BaseModel):
    capture_id: str
    thumbs: str = Field(..., pattern="^(up|down)$")


class FeedActionRequest(BaseModel):
    action_id: str
    data: dict | None = None


class ProcessRequest(BaseModel):
    batch_size: int = Field(default=5, ge=1, le=50)


class CaptureResponse(BaseModel):
    id: str
    type: str
    content: str
    source: str = ""
    category: str = ""
    summary: str = ""
    tags: list[str] = []
    has_pii: bool = False
    confidence: float = 0
    timestamp: str = ""


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "2.0.0"
    captures: int = 0
    name: str = "Capsule Web App"
