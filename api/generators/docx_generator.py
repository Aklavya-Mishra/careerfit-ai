"""
DOCX generator: produces a tailored resume DOCX.
If the original was DOCX, modifies it in-place to preserve formatting.
Otherwise builds a clean professional DOCX from scratch.
"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

import structlog
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

from core.models import ParsedResume

logger = structlog.get_logger(__name__)

_SECTION_HEADING_STYLE = "Heading 2"


def _is_content_para(para) -> bool:
    """True for bullet / body-text paragraphs that should be replaced.
    Structural paragraphs (headings, dates, company names, short labels) return False
    even if they use a list/bullet Word style."""
    text = para.text.strip()
    if not text:
        return False
    # Lines with date patterns are always structural (job entry headers)
    if re.search(r'\d{1,2}/\d{4}|20\d{2}\s*[-–]', text):
        return False
    # Short lines are structural regardless of style (company names, locations, labels)
    if len(text) <= 40:
        return False
    # Everything else that is long enough is content
    return True


def _set_para_text(para, new_text: str) -> None:
    """Replace paragraph text, using the first non-bold run as the format template.
    This prevents action-verb runs (bold) from making the entire new line bold."""
    if not para.runs:
        para.text = new_text
        return
    # Prefer a non-bold run so the whole replacement line isn't bold
    template = next((r for r in para.runs if not r.bold), para.runs[0])
    for run in para.runs:
        run.text = ""
    template.text = new_text


def _content_lines(text: str) -> list[str]:
    """Extract content lines from LLM output, filtering structural noise.
    Mirrors _is_content_para: drops date lines, short lines, and meta-notes so
    that structural lines the LLM echoes back don't displace real bullet content."""
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r'^(?:\*{0,2})?note[:\s*]', line, re.IGNORECASE):
            continue
        # Drop date-pattern lines echoed back from structural headers
        if re.search(r'\d{1,2}/\d{4}|20\d{2}\s*[-–]', line):
            continue
        # Drop short lines (company names, locations) echoed back by LLM
        if len(line) <= 40:
            continue
        out.append(line)
    return out


class DocxGenerator:
    def generate(
        self,
        tailored_resume: ParsedResume,
        original_path: Path | None,
        output_dir: Path,
        job_id: str,
    ) -> Path:
        out_path = output_dir / f"{job_id}_tailored.docx"

        if original_path and original_path.exists():
            result = self._modify_existing(tailored_resume, original_path, out_path)
        else:
            result = self._generate_new(tailored_resume, out_path)

        logger.info("docx_generated", path=str(result))
        return result

    def _modify_existing(
        self, tailored: ParsedResume, original_path: Path, out_path: Path
    ) -> Path:
        """
        Copy original DOCX and replace only bullet/body-text paragraphs with
        rewritten content, leaving all structural paragraphs (headings, job titles,
        company names, dates, locations) completely untouched.
        """
        shutil.copy2(original_path, out_path)
        doc = Document(str(out_path))

        from parsers.docx_parser import _detect_section, _is_heading

        # Map every paragraph index → its section name
        current_section = "contact"
        para_section: dict[int, str] = {}
        for i, para in enumerate(doc.paragraphs):
            if _is_heading(para):
                detected = _detect_section(para.text)
                if detected:
                    current_section = detected
            para_section[i] = current_section

        # Group paragraph indices by section
        section_groups: dict[str, list[int]] = {}
        for i, sec in para_section.items():
            section_groups.setdefault(sec, []).append(i)

        section_map = {s.name: (s.rewritten_text or s.raw_text) for s in tailored.sections}

        for section_name, new_text in section_map.items():
            if section_name == "contact":
                continue

            all_idx = section_groups.get(section_name, [])

            # Only update content/bullet paragraphs; skip headings + structural ones
            content_idx = [i for i in all_idx if _is_content_para(doc.paragraphs[i])]

            # Fall back: if no content paragraphs detected (e.g. summary is one long para),
            # use all non-heading non-empty paragraphs
            if not content_idx:
                content_idx = [
                    i for i in all_idx
                    if not _is_heading(doc.paragraphs[i]) and doc.paragraphs[i].text.strip()
                ]

            if not content_idx:
                continue

            new_lines = _content_lines(new_text)

            # If filtering left nothing to write, preserve the section as-is
            if not new_lines:
                continue

            # If section has a single content slot (e.g. summary), collapse all lines
            if len(content_idx) == 1:
                _set_para_text(doc.paragraphs[content_idx[0]], " ".join(new_lines))
                continue

            for slot, para_idx in enumerate(content_idx):
                para = doc.paragraphs[para_idx]
                if slot < len(new_lines):
                    _set_para_text(para, new_lines[slot])
                # If the LLM returned fewer usable lines than the original has
                # content slots, preserve the original paragraph instead of
                # leaving an empty bullet in the document.

        doc.save(str(out_path))
        return out_path

    def _generate_new(self, tailored: ParsedResume, out_path: Path) -> Path:
        """Build a clean professional DOCX when no original DOCX is available."""
        doc = Document()

        # Page margins
        for section in doc.sections:
            section.top_margin = Pt(36)
            section.bottom_margin = Pt(36)
            section.left_margin = Pt(54)
            section.right_margin = Pt(54)

        # Contact info as title block
        contact = tailored.contact_info
        if contact:
            name_para = doc.add_paragraph()
            name_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            name_run = name_para.add_run(contact.get("name", "Resume"))
            name_run.bold = True
            name_run.font.size = Pt(18)

            contact_line = " | ".join(
                v for k, v in contact.items() if k != "name"
            )
            if contact_line:
                c_para = doc.add_paragraph(contact_line)
                c_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for run in c_para.runs:
                    run.font.size = Pt(10)

        # Sections
        for resume_section in tailored.sections:
            if resume_section.name == "contact":
                continue

            # Section heading
            heading = doc.add_heading(resume_section.name.upper(), level=2)
            heading.runs[0].font.color.rgb = RGBColor(0x1F, 0x57, 0x9C)

            # Horizontal rule via border bottom on a paragraph
            content_text = resume_section.rewritten_text or resume_section.raw_text
            for line in content_text.splitlines():
                line = line.strip()
                if line:
                    doc.add_paragraph(line)

            doc.add_paragraph()  # spacing

        doc.save(str(out_path))
        return out_path
