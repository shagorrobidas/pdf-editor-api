"""DRF serializers for request validation."""

from __future__ import annotations

from rest_framework import serializers

from pdf_editor.validators import (
    validate_pdf_file,
    validate_watermark_color,
    validate_watermark_font_size,
    validate_watermark_opacity,
    validate_watermark_position,
)


class WatermarkPDFSerializer(serializers.Serializer):
    """Validates a PDF watermark request."""

    file = serializers.FileField(help_text="PDF file to watermark.")
    text = serializers.CharField(
        max_length=200,
        help_text="Watermark text.",
    )
    position = serializers.CharField(
        max_length=30,
        help_text=(
            "Watermark position: top-left, top-center, top-right, "
            "center, bottom-left, bottom-center, bottom-right."
        ),
    )
    opacity = serializers.CharField(
        help_text="Opacity between 0.0 (transparent) and 1.0 (opaque).",
    )
    color = serializers.CharField(
        max_length=10,
        help_text="Hex color code, e.g. #FF0000.",
    )
    font_size = serializers.CharField(
        help_text="Font size in points (6–200). Default is 36.",
        required=False,
        default="36",
    )

    def validate_file(self, value):
        validate_pdf_file(value)
        return value

    def validate_text(self, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Watermark text must not be empty.")
        return stripped

    def validate_position(self, value: str) -> str:
        try:
            return validate_watermark_position(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_opacity(self, value: str) -> float:
        try:
            return validate_watermark_opacity(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_color(self, value: str):
        try:
            return validate_watermark_color(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc

    def validate_font_size(self, value: str) -> int:
        try:
            return validate_watermark_font_size(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc


