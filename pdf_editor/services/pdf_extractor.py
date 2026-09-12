"""PDF text extraction service using PyMuPDF."""

from __future__ import annotations

import logging
from typing import List

import pymupdf

from pdf_editor.exceptions import EmptyPDFError, InvalidPDFError

logger = logging.getLogger(__name__)


class PageText:
    """Holds the extracted text for a single PDF page."""

    __slots__ = ("page_number", "text")

    def __init__(self, page_number: int, text: str) -> None:
        self.page_number = page_number
        self.text = text

    def __repr__(self) -> str:  # pragma: no cover
        preview = self.text[:40].replace("\n", " ")
        return f"<PageText page={self.page_number} text={preview!r}>"


class PDFExtractorService:
    """
    Extracts text content from a PDF file, page by page.

    Notes
    -----
    * Scanned / image-only PDFs are *not* supported.  If a PDF contains no
      extractable text an :class:`~pdf_editor.exceptions.EmptyPDFError` is raised.
      OCR is explicitly *not* attempted.
    * Unicode text (including Bangla) is returned as-is; no normalisation is
      applied so the caller can decide how to handle it.
    """

    def extract(self, pdf_bytes: bytes) -> List[PageText]:
        """
        Extract text from *pdf_bytes* and return a list of :class:`PageText`.

        Parameters
        ----------
        pdf_bytes:
            Raw bytes of a PDF file.

        Returns
        -------
        list of PageText
            One entry per page that contains non-blank text.

        Raises
        ------
        InvalidPDFError
            If *pdf_bytes* cannot be parsed as a PDF.
        EmptyPDFError
            If no page contains any extractable text (e.g. scanned PDFs).
        """
        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        except Exception as exc:
            raise InvalidPDFError(
                "Failed to open the uploaded file as a PDF. "
                "Make sure the file is a valid, uncorrupted PDF document."
            ) from exc

        pages: List[PageText] = []
        total_pages = len(doc)
        logger.debug("Extracting text from %d page(s).", total_pages)

        for page_idx in range(total_pages):
            page = doc[page_idx]
            text = page.get_text("text").strip()
            if text:
                pages.append(PageText(page_number=page_idx + 1, text=text))
            else:
                logger.debug("Page %d has no extractable text.", page_idx + 1)

        doc.close()

        if not pages:
            raise EmptyPDFError(
                "No extractable text was found in the uploaded PDF. "
                "Scanned or image-only PDFs are not supported — OCR is required "
                "to process such documents, which is outside the scope of this service."
            )

        logger.info(
            "Extracted text from %d/%d page(s).", len(pages), total_pages
        )
        return pages
