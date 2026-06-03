"""
PDF generator: builds a visually faithful PDF from the tailored resume
using WeasyPrint (HTML → PDF), preserving original style metadata.
"""
from __future__ import annotations

from pathlib import Path

import structlog

from core.models import ParsedResume, StyleMetadata

logger = structlog.get_logger(__name__)


def _pick_font(style: StyleMetadata) -> str:
    preferred = ["Calibri", "Arial", "Georgia", "Times New Roman", "Helvetica", "Roboto"]
    for font in style.fonts:
        for pref in preferred:
            if pref.lower() in font.lower():
                return pref
    return "Arial"


def _pick_accent_color(style: StyleMetadata) -> str:
    # Use first non-black/white color from original, fallback to a professional blue
    for color in style.colors:
        if color not in {"#000000", "#FFFFFF", "#ffffff", "#000", "0", "1"}:
            if len(color) in {7, 4} and color.startswith("#"):
                return color
    return "#1F579C"


def _build_html(resume: ParsedResume) -> str:
    style = resume.style_metadata
    font = _pick_font(style)
    accent = _pick_accent_color(style)
    contact = resume.contact_info

    contact_parts = []
    for key, val in contact.items():
        if key != "name":
            contact_parts.append(val)
    contact_line = " · ".join(contact_parts)

    candidate_name = contact.get("name", "")

    sections_html = ""
    for sec in resume.sections:
        if sec.name == "contact":
            continue
        content = sec.rewritten_text or sec.raw_text
        lines_html = ""
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("•") or line.startswith("-"):
                lines_html += f'<li>{line.lstrip("•- ")}</li>\n'
            else:
                lines_html += f'<p>{line}</p>\n'

        sections_html += f"""
<div class="section">
  <h2>{sec.name.upper()}</h2>
  <hr>
  <div class="section-content">{lines_html}</div>
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page {{
    size: A4;
    margin: 20mm 18mm 20mm 18mm;
  }}
  body {{
    font-family: "{font}", Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.45;
    color: #222;
    margin: 0;
    padding: 0;
  }}
  .header {{
    text-align: center;
    margin-bottom: 8pt;
  }}
  .header h1 {{
    font-size: 20pt;
    font-weight: 700;
    color: {accent};
    margin: 0 0 4pt 0;
    letter-spacing: 0.5pt;
  }}
  .header .contact-line {{
    font-size: 9pt;
    color: #555;
  }}
  .section {{
    margin-top: 10pt;
  }}
  .section h2 {{
    font-size: 10.5pt;
    font-weight: 700;
    color: {accent};
    margin: 0 0 2pt 0;
    letter-spacing: 0.5pt;
    text-transform: uppercase;
  }}
  .section hr {{
    border: none;
    border-top: 1.2pt solid {accent};
    margin: 2pt 0 5pt 0;
  }}
  .section-content p {{
    margin: 2pt 0;
  }}
  .section-content li {{
    margin: 1.5pt 0 1.5pt 14pt;
    list-style-type: disc;
  }}
  ul {{
    margin: 0;
    padding: 0;
  }}
</style>
</head>
<body>
  <div class="header">
    <h1>{candidate_name or 'Resume'}</h1>
    <div class="contact-line">{contact_line}</div>
  </div>
  {sections_html}
</body>
</html>"""

    return html


class PdfGenerator:
    def generate(
        self,
        tailored_resume: ParsedResume,
        output_dir: Path,
        job_id: str,
    ) -> Path:
        out_path = output_dir / f"{job_id}_tailored.pdf"
        html = _build_html(tailored_resume)

        try:
            from weasyprint import HTML
            HTML(string=html).write_pdf(str(out_path))
            logger.info("pdf_generated_weasyprint", path=str(out_path))
        except Exception as e:
            logger.warning("weasyprint_failed_falling_back_to_reportlab", error=str(e))
            self._reportlab_fallback(tailored_resume, out_path)

        return out_path

    def _reportlab_fallback(self, resume: ParsedResume, out_path: Path) -> None:
        """ReportLab fallback if WeasyPrint is unavailable."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

        doc = SimpleDocTemplate(str(out_path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        for sec in resume.sections:
            if sec.name == "contact":
                continue
            story.append(Paragraph(f"<b>{sec.name.upper()}</b>", styles["Heading2"]))
            content = sec.rewritten_text or sec.raw_text
            for line in content.splitlines():
                if line.strip():
                    story.append(Paragraph(line.strip(), styles["Normal"]))
            story.append(Spacer(1, 8))

        doc.build(story)
        logger.info("pdf_generated_reportlab", path=str(out_path))
