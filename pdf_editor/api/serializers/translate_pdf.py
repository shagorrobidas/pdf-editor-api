"""DRF serializers for request validation."""

from __future__ import annotations

from rest_framework import serializers

from pdf_editor.validators import (
    validate_language_code,
    validate_pdf_file,
)


class TranslatePDFSerializer(serializers.Serializer):
    """Validates a PDF translation request."""

    file = serializers.FileField(help_text="PDF file to translate.")
    source_language = serializers.CharField(
        max_length=10,
        help_text="ISO 639-1 source language code, e.g. 'en'.",
    )
    target_language = serializers.CharField(
        max_length=10,
        help_text="ISO 639-1 target language code, e.g. 'bn'.",
    )

    def validate_file(self, value):
        validate_pdf_file(value)
        return value

    def validate_source_language(self, value: str) -> str:
        return validate_language_code(value, "source_language")

    def validate_target_language(self, value: str) -> str:
        return validate_language_code(value, "target_language")

    def validate(self, data: dict) -> dict:
        src = data.get("source_language")
        tgt = data.get("target_language")
        if src and tgt and src == tgt:
            raise serializers.ValidationError(
                "source_language and target_language must be different."
            )
        return data
