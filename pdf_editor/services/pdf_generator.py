from __future__ import annotations

import io
import logging
import re
from pathlib import Path
from typing import List

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

logger = logging.getLogger(__name__)

_FONTS_REGISTERED = False


def _register_fonts() -> None:
    """Register the bundled Unicode fonts with ReportLab."""
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    fonts_dir: Path = settings.FONTS_DIR
    regular_path = fonts_dir / "NotoSansBengali-Regular.ttf"
    bold_path = fonts_dir / "NotoSansBengali-Bold.ttf"

    try:
        pdfmetrics.registerFont(
            TTFont("NotoSansBengali", str(regular_path), shapable=True)
        )
        pdfmetrics.registerFont(
            TTFont("NotoSansBengali-Bold", str(bold_path), shapable=True)
        )
        pdfmetrics.registerFontFamily(
            "NotoSansBengali",
            normal="NotoSansBengali",
            bold="NotoSansBengali-Bold",
        )
        from reportlab.lib.fonts import addMapping
        for key in ("NotoSansBengali", "notosansbengali"):
            addMapping(key, 0, 0, "NotoSansBengali")
            addMapping(key, 1, 0, "NotoSansBengali-Bold")
        for key in ("NotoSansBengali-Bold", "notosansbengali-bold"):
            addMapping(key, 0, 0, "NotoSansBengali-Bold")
            addMapping(key, 1, 0, "NotoSansBengali-Bold")

        _FONTS_REGISTERED = True
        logger.debug("Unicode fonts registered with ReportLab.")
    except Exception as exc:
        logger.warning("Font registration notice: %s", exc)


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas for adding running headers and 'Page X of Y' footers."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[dict] = []
        self.doc_title: str = "Translated Document"

    def showPage(self) -> None:
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_decorations(num_pages)
            super().showPage()
        super().save()

    def _draw_decorations(self, page_count: int) -> None:
        self.saveState()
        self.setFont("NotoSansBengali", 9)
        self.setFillColor(colors.HexColor("#718096"))

        # Running header on pages 2+
        if self._pageNumber > 1:
            title_text = self.doc_title[:60] if self.doc_title else "Document"
            self.drawString(2 * cm, A4[1] - 1.5 * cm, title_text)
            self.setStrokeColor(colors.HexColor("#E2E8F0"))
            self.setLineWidth(0.5)
            self.line(2 * cm, A4[1] - 1.6 * cm, A4[0] - 2 * cm, A4[1] - 1.6 * cm)

        # Running footer with page numbering on all pages
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(A4[0] - 2 * cm, 1.2 * cm, page_text)
        self.setStrokeColor(colors.HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(2 * cm, 1.6 * cm, A4[0] - 2 * cm, 1.6 * cm)

        self.restoreState()


def _make_styles() -> dict:
    """Build and return a dict of publication-quality ParagraphStyles."""
    _register_fonts()

    body = ParagraphStyle(
        name="UnicodeBody",
        fontName="NotoSansBengali",
        fontSize=10,
        leading=15,
        alignment=TA_JUSTIFY,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=8,
        shaping=True,
        wordWrap="LTR",
    )

    page_heading = ParagraphStyle(
        name="PageHeading",
        fontName="NotoSansBengali-Bold",
        fontSize=11,
        leading=15,
        spaceAfter=6,
        textColor=colors.HexColor("#4A5568"),
        shaping=True,
    )

    h2_heading = ParagraphStyle(
        name="SectionHeading",
        fontName="NotoSansBengali-Bold",
        fontSize=13,
        leading=17,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=12,
        spaceAfter=5,
        keepWithNext=True,
        shaping=True,
    )

    bullet = ParagraphStyle(
        name="BulletItem",
        fontName="NotoSansBengali",
        fontSize=10,
        leading=14,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#2D3748"),
        leftIndent=18,
        firstLineIndent=-12,
        spaceAfter=4,
        shaping=True,
    )

    return {
        "body": body,
        "page_heading": page_heading,
        "heading": h2_heading,
        "bullet": bullet,
    }


class PDFGeneratorService:

    def generate(self, pages: List[tuple[int, str]], title: str = "Translated Document") -> bytes:
        _register_fonts()
        styles = _make_styles()

        buf = io.BytesIO()
        margin = 2 * cm
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=2.2 * cm,
            bottomMargin=margin,
            title=title,
        )

        story = []

        for idx, (page_number, text) in enumerate(pages):
            if idx > 0:
                story.append(PageBreak())

            # Separator heading between pages
            heading_text = f"— Page {page_number} —"
            story.append(Paragraph(heading_text, styles["page_heading"]))
            story.append(Spacer(1, 0.2 * cm))

            blocks = _split_into_blocks(text)
            for block in blocks:
                cleaned = block.strip()
                if not cleaned:
                    continue

                escaped = _escape_xml(cleaned)

                # Classify block for typography
                if re.match(r"^[G•\-\*]\s+", cleaned) or re.match(r"^\d+[\.\)]\s+", cleaned):
                    bullet_text = re.sub(r"^[G•\-\*]\s*", "•  ", escaped)
                    story.append(Paragraph(bullet_text, styles["bullet"]))
                elif len(cleaned) < 80 and not cleaned.endswith((".", "!", "?", "।", ":", ";")):
                    story.append(Paragraph(escaped, styles["heading"]))
                else:
                    story.append(Paragraph(escaped, styles["body"]))

        class ConfiguredCanvas(NumberedCanvas):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.doc_title = title

        doc.build(story, canvasmaker=ConfiguredCanvas)
        buf.seek(0)
        return buf.read()


def _split_into_blocks(text: str) -> List[str]:
    """Split *text* into paragraph-like blocks on blank lines."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = []
    current_lines: List[str] = []

    for line in normalized.splitlines():
        if line.strip():
            current_lines.append(line.strip())
        else:
            if current_lines:
                blocks.append(" ".join(current_lines))
                current_lines = []

    if current_lines:
        blocks.append(" ".join(current_lines))

    return blocks if blocks else [text]


def _escape_xml(text: str) -> str:
    """Escape characters that would break ReportLab's XML parser."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
