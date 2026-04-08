"""OCR service for extracting text from screenshots."""

import logging

logger = logging.getLogger(__name__)


def extract_text(image_path: str) -> str:
    """Extract text from an image file using Pillow + pytesseract.

    Falls back gracefully if pytesseract is not installed.
    """
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except ImportError:
        logger.warning("pytesseract not installed — returning empty OCR result. Install with: pip install pytesseract")
        return ""
    except Exception as e:
        logger.error("OCR failed for %s: %s", image_path, e)
        return ""
