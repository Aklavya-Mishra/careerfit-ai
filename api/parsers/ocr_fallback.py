"""
OCR fallback for scanned PDFs using Tesseract via pytesseract.
"""
from __future__ import annotations

from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


class OCRFallback:
    def extract_text(self, path: Path) -> str:
        logger.info("ocr_start", path=str(path))
        try:
            import pytesseract
            from pdf2image import convert_from_path

            pages = convert_from_path(str(path), dpi=300)
            text_parts: list[str] = []
            for i, page_img in enumerate(pages):
                page_text = pytesseract.image_to_string(page_img, lang="eng")
                text_parts.append(page_text)
                logger.debug("ocr_page_done", page=i + 1)

            full_text = "\n".join(text_parts)
            logger.info("ocr_complete", chars=len(full_text))
            return full_text

        except ImportError as e:
            logger.error("ocr_dependency_missing", error=str(e))
            raise RuntimeError(
                "OCR dependencies not installed. "
                "Install pytesseract and pdf2image: pip install pytesseract pdf2image"
            ) from e
        except Exception as e:
            logger.exception("ocr_failed", error=str(e))
            raise
