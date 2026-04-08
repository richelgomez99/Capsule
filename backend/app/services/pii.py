"""PII detection service — regex patterns + optional Gemini enhancement."""

import re
import logging

logger = logging.getLogger(__name__)

# Compiled regex patterns for common PII types
_PATTERNS = {
    "email": re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
    "phone": re.compile(r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),
    "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    "credit_card": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
    "ip_address": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
    "api_key": re.compile(
        r'(?:api[_-]?key|token|secret|password|auth)\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{16,}',
        re.IGNORECASE,
    ),
    "address": re.compile(
        r'\b\d{1,5}\s+(?:[A-Z][a-z]+\s*){1,4}(?:St|Street|Ave|Avenue|Blvd|Boulevard|Dr|Drive|Ln|Lane|Rd|Road|Ct|Court|Way|Pl|Place)\b',
        re.IGNORECASE,
    ),
}


def detect_pii(text: str) -> tuple[bool, list[str]]:
    """Scan text for PII patterns.

    Returns (has_pii, list_of_pii_types_found).
    """
    if not text:
        return False, []

    found: list[str] = []
    for pii_type, pattern in _PATTERNS.items():
        if pattern.search(text):
            found.append(pii_type)

    return bool(found), found
