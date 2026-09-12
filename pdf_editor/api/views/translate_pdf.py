"""API views for pdf_editor — kept thin, business logic is in services."""

from __future__ import annotations

import logging

from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from pdf_editor.api.serializers import (
    TranslatePDFSerializer,
)
from pdf_editor.services.pdf_extractor import PDFExtractorService
from pdf_editor.services.pdf_generator import PDFGeneratorService

from pdf_editor.services.translator import get_translation_service

logger = logging.getLogger(__name__)


def _pdf_response(pdf_bytes: bytes, filename: str):
    """Return an HttpResponse containing a downloadable PDF."""
    from django.http import HttpResponse

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Content-Length"] = len(pdf_bytes)
    return response


class TranslatePDFView(APIView):
    """
    POST /api/translate-pdf
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request) -> Response:
        serializer = TranslatePDFSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        source_lang: str = serializer.validated_data["source_language"]
        target_lang: str = serializer.validated_data["target_language"]

        logger.info(
            "Translate request: %s → %s, file=%s (%d bytes)",
            source_lang,
            target_lang,
            uploaded_file.name,
            uploaded_file.size,
        )

        pdf_bytes = uploaded_file.read()

        # 1. Extract text from the uploaded PDF.
        extractor = PDFExtractorService()
        pages = extractor.extract(pdf_bytes)

        # 2. Translate each page's text.
        translator = get_translation_service()
        translated_pages = []
        for page in pages:
            translated_text = translator.translate(
                page.text, source_lang, target_lang
            )
            translated_pages.append((page.page_number, translated_text))

        # 3. Generate a new PDF with the translated content.
        generator = PDFGeneratorService()
        output_pdf = generator.generate(translated_pages)

        filename = f"translated_{source_lang}_to_{target_lang}.pdf"
        return _pdf_response(output_pdf, filename)
