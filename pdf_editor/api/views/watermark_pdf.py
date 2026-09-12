"""API views for pdf_editor — kept thin, business logic is in services."""

from __future__ import annotations

import logging

from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from pdf_editor.api.serializers import (
    WatermarkPDFSerializer,
)
from pdf_editor.services.watermark import WatermarkService
from pdf_editor.api.views.translate_pdf import _pdf_response
logger = logging.getLogger(__name__)


class WatermarkPDFView(APIView):
    """
    POST /editor/pdf/watermark
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request) -> Response:
        serializer = WatermarkPDFSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        text: str = serializer.validated_data["text"]
        position: str = serializer.validated_data["position"]
        opacity: float = serializer.validated_data["opacity"]
        color: tuple = serializer.validated_data["color"]
        font_size: int = serializer.validated_data.get("font_size", 36)

        logger.info(
            "Watermark request: text=%r, position=%s, opacity=%.2f, font_size=%d, file=%s",
            text,
            position,
            opacity,
            font_size,
            uploaded_file.name,
        )

        pdf_bytes = uploaded_file.read()

        watermarker = WatermarkService()
        output_pdf = watermarker.apply(
            pdf_bytes,
            text,
            position,
            opacity,
            color,
            font_size=font_size,
        )

        return _pdf_response(output_pdf, "watermarked_document.pdf")
