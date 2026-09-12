from __future__ import annotations

import io
import logging
from typing import Tuple

import pymupdf

from pdf_editor.exceptions import InvalidPDFError, PDFProcessingError

logger = logging.getLogger(__name__)

# Default watermark font size if not specified (points)
_DEFAULT_FONT_SIZE = 36
_MIN_FONT_SIZE = 8
# Padding from page edge (points)
_EDGE_PADDING = 30


def _fit_font_size(text: str, max_width: float, max_height: float, start_size: float = _DEFAULT_FONT_SIZE) -> float:
    """
    Ensure `text` fits within max_width × max_height using Helvetica.
    If it overflows, shrink in steps of 2pt down to _MIN_FONT_SIZE.
    """
    size = float(start_size)
    while size >= _MIN_FONT_SIZE:
        w = pymupdf.get_text_length(text, fontname="helv", fontsize=size)
        h = size * 1.3
        if w <= max_width and h <= max_height:
            return size
        size -= 2
    return float(_MIN_FONT_SIZE)


def _stamp_page(
    page: pymupdf.Page,
    text: str,
    position: str,
    opacity: float,
    color: Tuple[float, float, float],
    font_size: int | None = None,
) -> None:
    
    pw = page.rect.width
    ph = page.rect.height
    pad = _EDGE_PADDING

    # Requested or default font size
    target_size = font_size if (font_size and font_size > 0) else _DEFAULT_FONT_SIZE

    # Usable area based on page dimensions
    max_w = pw - (2 * pad)
    max_h = ph - (2 * pad)
    actual_font_size = _fit_font_size(text, max_w, max_h, start_size=target_size)
    text_width = pymupdf.get_text_length(text, fontname="helv", fontsize=actual_font_size)

    # Horizontal coordinate (x)
    if "left" in position:
        x = pad
    elif "right" in position:
        x = pw - pad - text_width
    else:  # center, top-center, bottom-center
        x = (pw - text_width) / 2.0

    # Vertical baseline coordinate (y) - PyMuPDF uses top-left origin (y downwards)
    if position.startswith("top"):
        y = pad + actual_font_size
    elif position.startswith("bottom"):
        y = ph - pad
    else:  # center
        y = (ph / 2.0) + (actual_font_size / 3.0)

    # Insert text with native PDF fill_opacity
    page.insert_text(
        pymupdf.Point(x, y),
        text,
        fontname="helv",
        fontsize=actual_font_size,
        color=color,
        fill_opacity=opacity,
    )

    logger.debug(
        "Watermark stamped: text=%r pos=%s font_size=%.1f pt=(%.1f, %.1f) opacity=%.2f",
        text, position, actual_font_size, x, y, opacity,
    )


class WatermarkService:

    def apply(
        self,
        pdf_bytes: bytes,
        text: str,
        position: str,
        opacity: float,
        color: Tuple[float, float, float],
        font_size: int | None = None,
    ) -> bytes:
        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        except Exception as exc:
            raise InvalidPDFError(
                "Failed to open the uploaded file as a PDF."
            ) from exc

        try:
            logger.debug("Applying watermark '%s' to %d page(s).", text, len(doc))

            for page in doc:
                _stamp_page(
                    page,
                    text,
                    position,
                    opacity,
                    color,
                    font_size=font_size,
                )

            out_buf = io.BytesIO()
            doc.save(out_buf, garbage=3, deflate=True)
            doc.close()
            out_buf.seek(0)
            return out_buf.read()

        except (InvalidPDFError, PDFProcessingError):
            raise
        except Exception as exc:
            logger.error("Watermark error: %s", exc, exc_info=True)
            raise PDFProcessingError(
                f"An error occurred while applying the watermark: {exc}"
            ) from exc
