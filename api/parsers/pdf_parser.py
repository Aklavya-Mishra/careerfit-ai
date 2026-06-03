"""
PDF parser: extracts text and layout metadata using pdfplumber.
Falls back to Tesseract OCR for scanned (image-only) PDFs.
"""
from __future__ import annotations

import re
from pathlib import Path

import pdfplumber
import structlog

from core.models import DocumentType, ParsedResume, ResumeSection, StyleMetadata
from parsers.docx_parser import SECTION_HEADERS, _detect_section, _normalize

logger = structlog.get_logger(__name__)

_MIN_TEXT_CHARS = 100  # below this, assume scanned PDF


def _is_scanned(pdf) -> bool:
    total_chars = sum(len(p.extract_text() or "") for p in pdf.pages)
    return total_chars < _MIN_TEXT_CHARS


def _extract_fonts_colors(page) -> tuple[set[str], set[str]]:
    fonts: set[str] = set()
    colors: set[str] = set()
    try:
        for char in page.chars:
            if char.get("fontname"):
                fonts.add(char["fontname"])
            if char.get("non_stroking_color"):
                colors.add(str(char["non_stroking_color"]))
    except Exception:
        pass
    return fonts, colors


def _extract_margins(page) -> dict[str, float]:
    try:
        chars = page.chars
        if not chars:
            return {}
        left = min(c["x0"] for c in chars)
        right = max(c["x1"] for c in chars)
        top = min(c["top"] for c in chars)
        bottom = max(c["bottom"] for c in chars)
        return {
            "left": round(left, 1),
            "right": round(page.width - right, 1),
            "top": round(top, 1),
            "bottom": round(page.height - bottom, 1),
        }
    except Exception:
        return {}


class PdfParser:
    def parse(self, path: Path) -> ParsedResume:
        logger.info("pdf_parse_start", path=str(path))

        with pdfplumber.open(str(path)) as pdf:
            if _is_scanned(pdf):
                logger.info("scanned_pdf_detected_using_ocr")
                return self._parse_with_ocr(path)

            all_fonts: set[str] = set()
            all_colors: set[str] = set()
            all_lines: list[str] = []
            margins: dict[str, float] = {}

            for page in pdf.pages:
                fonts, colors = _extract_fonts_colors(page)
                all_fonts.update(fonts)
                all_colors.update(colors)

                if not margins:
                    margins = _extract_margins(page)

                text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped:
                        all_lines.append(stripped)

        style_meta = StyleMetadata(
            fonts=list(all_fonts),
            colors=list(all_colors),
            margins=margins,
        )

        sections = self._detect_sections(all_lines)
        full_text = "\n".join(all_lines)
        contact_info = self._extract_contact(full_text)

        logger.info("pdf_parse_complete", sections=len(sections))

        return ParsedResume(
            source_type=DocumentType.PDF,
            full_text=full_text,
            sections=sections,
            style_metadata=style_meta,
            contact_info=contact_info,
            raw_paragraphs=all_lines,
        )

    def _detect_sections(self, lines: list[str]) -> list[ResumeSection]:
        sections: list[ResumeSection] = []
        current_name = "contact"
        current_lines: list[str] = []

        for line in lines:
            detected = _detect_section(line)
            if detected and len(line) < 60 and detected != current_name:
                if current_lines:
                    sections.append(ResumeSection(
                        name=current_name,
                        raw_text="\n".join(current_lines),
                    ))
                current_name = detected
                current_lines = []
                continue
            current_lines.append(line)

        if current_lines:
            sections.append(ResumeSection(
                name=current_name,
                raw_text="\n".join(current_lines),
            ))

        return sections

    def _extract_contact(self, text: str) -> dict[str, str]:
        info: dict[str, str] = {}
        email = re.search(r"[\w.+-]+@[\w-]+\.\w+", text)
        phone = re.search(r"[\+\d][\d\s\-().]{8,}", text)
        linkedin = re.search(r"linkedin\.com/in/[\w-]+", text, re.I)
        if email:
            info["email"] = email.group()
        if phone:
            info["phone"] = phone.group().strip()
        if linkedin:
            info["linkedin"] = linkedin.group()
        # Attempt name: first short line with no digits and no @ symbol
        for line in text.splitlines()[:8]:
            line = line.strip()
            if line and 2 <= len(line.split()) <= 5 and "@" not in line and not any(c.isdigit() for c in line):
                info["name"] = line
                break
        return info

    def extract_text(self, path: Path) -> str:
        with pdfplumber.open(str(path)) as pdf:
            if _is_scanned(pdf):
                from parsers.ocr_fallback import OCRFallback
                return OCRFallback().extract_text(path)
            return "\n".join(
                p.extract_text() or "" for p in pdf.pages
            )

    def _parse_with_ocr(self, path: Path) -> ParsedResume:
        from parsers.ocr_fallback import OCRFallback
        text = OCRFallback().extract_text(path)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        sections = self._detect_sections(lines)
        contact_info = self._extract_contact(text)
        return ParsedResume(
            source_type=DocumentType.PDF,
            full_text=text,
            sections=sections,
            style_metadata=StyleMetadata(),
            contact_info=contact_info,
            raw_paragraphs=lines,
        )
