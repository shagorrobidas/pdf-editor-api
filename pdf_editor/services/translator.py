"""Translation service abstraction with Google Translate (free) and mock implementations."""

from __future__ import annotations

import logging
import textwrap
from abc import ABC, abstractmethod

from django.conf import settings

from pdf_editor.exceptions import TranslationServiceError

logger = logging.getLogger(__name__)

# Google Translate free API has a per-request character limit (~5000 chars).
_CHUNK_SIZE = 4500


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class BaseTranslationService(ABC):
    """Abstract interface for a text translation service."""

    @abstractmethod
    def translate(self, text: str, source_language: str, target_language: str) -> str:
        """Translate *text* from *source_language* to *target_language*."""


# ---------------------------------------------------------------------------
# Google Translate (free, no API key required)
# ---------------------------------------------------------------------------


class GoogleTranslateService(BaseTranslationService):
    """
    Uses the unofficial googletrans library to call Google Translate for free.
    No API key is required — this uses the same endpoint as translate.google.com.

    Long texts are split into chunks to stay within the per-request limit.
    """

    def __init__(self) -> None:
        try:
            from googletrans import Translator
            self._translator = Translator()
        except ImportError as exc:
            raise TranslationServiceError(
                "googletrans is not installed. Run: pip install googletrans==4.0.0rc1"
            ) from exc

    def translate(self, text: str, source_language: str, target_language: str) -> str:
        if not text.strip():
            return text

        # Split into paragraphs first, then chunk if needed
        lines = text.splitlines()
        translated_lines = []

        # Group lines into chunks under _CHUNK_SIZE chars
        chunks: list[str] = []
        current_chunk: list[str] = []
        current_len = 0

        for line in lines:
            line_len = len(line) + 1  # +1 for newline
            if current_len + line_len > _CHUNK_SIZE and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_len = line_len
            else:
                current_chunk.append(line)
                current_len += line_len

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        translated_parts = []
        for chunk in chunks:
            if not chunk.strip():
                translated_parts.append(chunk)
                continue
            try:
                result = self._translator.translate(
                    chunk,
                    src=source_language,
                    dest=target_language,
                )
                translated_parts.append(result.text)
                logger.debug(
                    "Translated %d chars (%s→%s).", len(chunk), source_language, target_language
                )
            except Exception as exc:
                logger.error("googletrans error: %s", exc, exc_info=True)
                raise TranslationServiceError(
                    f"Google Translate failed: {exc}. "
                    "Check your internet connection."
                ) from exc

        return "\n".join(translated_parts)


# ---------------------------------------------------------------------------
# Mock implementation (offline, deterministic)
# ---------------------------------------------------------------------------

_MOCK_TRANSLATIONS: dict[tuple[str, str], dict[str, str]] = {
    ("en", "bn"): {
        "Hello": "হ্যালো",
        "Hello, World!": "হ্যালো, বিশ্ব!",
        "Good morning": "শুভ সকাল",
        "How are you?": "আপনি কেমন আছেন?",
        "Thank you.": "ধন্যবাদ।",
        "This is a test.": "এটি একটি পরীক্ষা।",
        "This is a test document.": "এটি একটি পরীক্ষামূলক নথি।",
    },
    ("bn", "en"): {
        "হ্যালো": "Hello",
        "ধন্যবাদ।": "Thank you.",
        "আপনি কেমন আছেন?": "How are you?",
        "এটি একটি বাংলা পরীক্ষামূলক বাক্য।": "This is a Bengali test sentence.",
    },
}


class MockTranslationService(BaseTranslationService):
    """
    Offline translation service for unit tests.
    Returns real translations for known phrases; prefixes unknown text
    with a clear tag so the PDF pipeline can still be exercised.
    """

    def translate(self, text: str, source_language: str, target_language: str) -> str:
        pair = (source_language.lower(), target_language.lower())
        lookup = _MOCK_TRANSLATIONS.get(pair, {})
        stripped = text.strip()

        if stripped in lookup:
            return lookup[stripped]

        lines = stripped.splitlines()
        translated_lines = []
        for line in lines:
            ls = line.strip()
            if ls in lookup:
                translated_lines.append(lookup[ls])
            elif not ls:
                translated_lines.append("")
            else:
                if target_language.lower() == "bn":
                    translated_lines.append(f"[অনুবাদ] {ls}")
                else:
                    translated_lines.append(f"[translated from {source_language}] {ls}")

        return "\n".join(translated_lines)


# ---------------------------------------------------------------------------
# External REST API (Google Cloud Translation v2)
# ---------------------------------------------------------------------------


class ExternalTranslationService(BaseTranslationService):
    """Calls a configured external REST translation API (e.g. Google Cloud v2)."""

    def __init__(self) -> None:
        import requests as _requests
        self._requests = _requests
        self._api_key = settings.TRANSLATION_API_KEY
        self._api_url = settings.TRANSLATION_API_URL
        if not self._api_key:
            raise TranslationServiceError(
                "TRANSLATION_API_KEY is not set. "
                "Use TRANSLATION_PROVIDER=google (free) or set the key."
            )

    def translate(self, text: str, source_language: str, target_language: str) -> str:
        if not text.strip():
            return text
        payload = {
            "q": text,
            "source": source_language,
            "target": target_language,
            "format": "text",
            "key": self._api_key,
        }
        try:
            response = self._requests.post(self._api_url, json=payload, timeout=30)
            if not response.ok:
                raise TranslationServiceError(
                    f"Translation API returned HTTP {response.status_code}."
                )
            data = response.json()
            return data["data"]["translations"][0]["translatedText"]
        except TranslationServiceError:
            raise
        except Exception as exc:
            raise TranslationServiceError(f"External translation failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_translation_service() -> BaseTranslationService:
    """
    Return the configured translation service based on ``TRANSLATION_PROVIDER``:

    - ``"google"`` (default) — Free Google Translate via googletrans (no API key needed).
    - ``"mock"``             — Offline mock, used in tests.
    - ``"external"``         — Google Cloud Translation v2 REST API (requires TRANSLATION_API_KEY).
    """
    provider = getattr(settings, "TRANSLATION_PROVIDER", "google").lower()

    if provider == "mock":
        logger.info("Using MockTranslationService (offline mode).")
        return MockTranslationService()

    if provider == "external":
        logger.info("Using ExternalTranslationService.")
        return ExternalTranslationService()

    # Default: free Google Translate
    logger.info("Using GoogleTranslateService (free, no API key).")
    return GoogleTranslateService()
