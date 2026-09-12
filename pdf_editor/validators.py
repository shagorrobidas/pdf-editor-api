"""Reusable validation helpers for pdf_editor."""

from __future__ import annotations

import re
from typing import Tuple

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from pdf_editor.exceptions import InvalidPDFError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_POSITIONS = frozenset(
    [
        "top-left",
        "top-center",
        "top-right",
        "center",
        "bottom-left",
        "bottom-center",
        "bottom-right",
    ]
)

# Basic BCP-47 / ISO 639-1 allow-list.  Extend as needed.
SUPPORTED_LANGUAGE_CODES = frozenset(
    [
        "af", "sq", "am", "ar", "hy", "az", "eu", "be", "bn", "bs",
        "bg", "ca", "ceb", "ny", "zh", "co", "hr", "cs", "da", "nl",
        "en", "eo", "et", "tl", "fi", "fr", "fy", "gl", "ka", "de",
        "el", "gu", "ht", "ha", "haw", "he", "hi", "hmn", "hu", "is",
        "ig", "id", "ga", "it", "ja", "jw", "kn", "kk", "km", "ko",
        "ku", "ky", "lo", "la", "lv", "lt", "lb", "mk", "mg", "ms",
        "ml", "mt", "mi", "mr", "mn", "my", "ne", "no", "ps", "fa",
        "pl", "pt", "pa", "ro", "ru", "sm", "gd", "sr", "st", "sn",
        "sd", "si", "sk", "sl", "so", "es", "su", "sw", "sv", "tg",
        "ta", "te", "th", "tr", "uk", "ur", "uz", "vi", "cy", "xh",
        "yi", "yo", "zu",
    ]
)

# PDF magic bytes
_PDF_MAGIC = b"%PDF-"


# ---------------------------------------------------------------------------
# File validators
# ---------------------------------------------------------------------------


def validate_pdf_file(file: UploadedFile) -> None:
    """
    Validate that *file* is a non-empty, properly-sized PDF.

    Raises:
        InvalidPDFError: on any validation failure.
    """
    if file is None:
        raise InvalidPDFError("A PDF file is required.")

    # Size check
    max_bytes: int = settings.MAX_PDF_SIZE_BYTES
    if file.size == 0:
        raise InvalidPDFError("The uploaded file is empty.")
    if file.size > max_bytes:
        raise InvalidPDFError(
            f"File size exceeds the maximum allowed size of "
            f"{settings.MAX_PDF_SIZE_MB} MB."
        )

    # Extension check (basic guard — real magic-byte check follows)
    name: str = (file.name or "").lower()
    if not name.endswith(".pdf"):
        raise InvalidPDFError("Only PDF files are accepted (must have a .pdf extension).")

    # Magic-bytes check: read first 5 bytes without consuming the stream
    file.seek(0)
    header = file.read(5)
    file.seek(0)
    if header != _PDF_MAGIC:
        raise InvalidPDFError("A valid PDF file is required (invalid PDF header).")


# ---------------------------------------------------------------------------
# Language validators
# ---------------------------------------------------------------------------


def validate_language_code(code: str, field_name: str = "language") -> str:
    """
    Validate and normalise a language code.

    Returns:
        The lower-cased language code.

    Raises:
        ValueError: if the code is missing or not supported.
    """
    if not code or not code.strip():
        raise ValueError(f"The '{field_name}' field is required.")

    normalized = code.strip().lower()
    if normalized not in SUPPORTED_LANGUAGE_CODES:
        raise ValueError(
            f"Unsupported language code '{code}'. "
            f"Please use a valid ISO 639-1 language code (e.g. 'en', 'bn', 'fr')."
        )
    return normalized


# ---------------------------------------------------------------------------
# Watermark validators
# ---------------------------------------------------------------------------


def validate_watermark_position(position: str) -> str:
    """
    Validate the watermark position string.

    Returns:
        The normalised position string.

    Raises:
        ValueError: for an unrecognised value.
    """
    if not position or not position.strip():
        raise ValueError("The 'position' field is required.")

    normalized = position.strip().lower()
    if normalized not in ALLOWED_POSITIONS:
        allowed = ", ".join(sorted(ALLOWED_POSITIONS))
        raise ValueError(
            f"Invalid position. Allowed values are: {allowed}."
        )
    return normalized


def validate_watermark_opacity(opacity_raw: str | float) -> float:
    """
    Validate and parse an opacity value in the range [0.0, 1.0].

    Returns:
        A float between 0.0 and 1.0 inclusive.

    Raises:
        ValueError: if the value is missing, non-numeric, or out of range.
    """
    if opacity_raw is None or opacity_raw == "":
        raise ValueError("The 'opacity' field is required.")

    try:
        opacity = float(opacity_raw)
    except (TypeError, ValueError):
        raise ValueError(
            f"Invalid opacity value '{opacity_raw}'. Must be a number between 0.0 and 1.0."
        )

    if not (0.0 <= opacity <= 1.0):
        raise ValueError(
            f"Opacity must be between 0.0 and 1.0, got {opacity}."
        )

    return opacity


def validate_watermark_color(color: str) -> Tuple[float, float, float]:
    """
    Validate a hex color string and convert it to a normalised (r, g, b) tuple.

    Accepts ``#RGB`` (shorthand) and ``#RRGGBB`` formats.

    Returns:
        Tuple of floats in [0.0, 1.0] representing (red, green, blue).

    Raises:
        ValueError: for an invalid format.
    """
    if not color or not color.strip():
        raise ValueError("The 'color' field is required.")

    hex_str = color.strip()

    # Match #RGB or #RRGGBB
    match = re.fullmatch(r"#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})", hex_str)
    if not match:
        raise ValueError(
            f"Invalid color '{color}'. Use a hex color like #FF0000 or #F00."
        )

    hex_digits = match.group(1)
    if len(hex_digits) == 3:
        # Expand shorthand
        hex_digits = "".join(c * 2 for c in hex_digits)

    r = int(hex_digits[0:2], 16) / 255.0
    g = int(hex_digits[2:4], 16) / 255.0
    b = int(hex_digits[4:6], 16) / 255.0

    return (r, g, b)


def validate_watermark_font_size(font_size_raw: str | int | float) -> int:
    """
    Validate and parse a watermark font size (integer points).

    Accepted range: 6 – 200 pt.

    Returns
    -------
    int
        Font size in points.

    Raises
    ------
    ValueError
        If the value is missing, non-numeric, or out of range.
    """
    if font_size_raw is None or font_size_raw == "":
        raise ValueError("The 'font_size' field is required.")

    try:
        size = int(float(str(font_size_raw)))
    except (TypeError, ValueError):
        raise ValueError(
            f"Invalid font_size value '{font_size_raw}'. "
            "Must be a whole number between 6 and 200."
        )

    if not (6 <= size <= 200):
        raise ValueError(
            f"font_size must be between 6 and 200 pt, got {size}."
        )

    return size
