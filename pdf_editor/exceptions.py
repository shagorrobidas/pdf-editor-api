"""Custom exceptions and DRF exception handler for pdf_editor."""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class InvalidPDFError(ValueError):
    """Raised when the uploaded file is not a valid PDF."""


class EmptyPDFError(ValueError):
    """Raised when the PDF contains no extractable text."""


class PDFProcessingError(RuntimeError):
    """Raised for unexpected errors during PDF processing."""


class TranslationServiceError(RuntimeError):
    """Raised when the external translation service fails."""


# ---------------------------------------------------------------------------
# DRF exception handler
# ---------------------------------------------------------------------------


def custom_exception_handler(exc: Exception, context: dict) -> Response | None:
    """
    Returns a uniform ``{ "error": "<message>" }`` JSON body for all errors.

    Stack traces are never exposed in the response.
    """
    # Call DRF's default handler first so it processes authentication /
    # permission errors with the right status codes.
    response = exception_handler(exc, context)

    if response is not None:
        # Replace whatever DRF put into detail/non_field_errors with a flat
        # "error" key so the API surface is consistent.
        error_detail = _flatten_errors(response.data)
        response.data = {"error": error_detail}
        return response

    # Domain errors we want to surface as 400 Bad Request.
    if isinstance(exc, (InvalidPDFError, EmptyPDFError, ValueError)):
        logger.warning("Validation error: %s", exc)
        return Response(
            {"error": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Translation back-end errors → 502 Bad Gateway.
    if isinstance(exc, TranslationServiceError):
        logger.error("Translation service error: %s", exc)
        return Response(
            {"error": "Translation service is unavailable. Please try again later."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # Generic processing errors → 500, but without internal detail.
    if isinstance(exc, PDFProcessingError):
        logger.error("PDF processing error: %s", exc, exc_info=True)
        return Response(
            {"error": "An internal error occurred while processing the PDF."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Everything else: log it but return None so Django's 500 handler takes over.
    logger.exception("Unhandled exception in view: %s", exc)
    return None


def _flatten_errors(data: object) -> str:
    """Reduce DRF's nested error structure to a single readable string."""
    if isinstance(data, dict):
        parts = []
        for key, value in data.items():
            flat = _flatten_errors(value)
            if key == "non_field_errors" or key == "detail":
                parts.append(flat)
            else:
                parts.append(f"{key}: {flat}")
        return " | ".join(parts)
    if isinstance(data, list):
        return " ".join(_flatten_errors(item) for item in data)
    return str(data)
