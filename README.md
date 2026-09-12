# PDF Editor API

A production-ready REST API built with Django and Django REST Framework (DRF) for manipulating PDF documents. Provides endpoints for PDF text extraction & language translation with full Bangla (Bengali) Unicode rendering, as well as customizable PDF watermarking.

🚀 **Live API Base URL:** [https://pdf-editor-api.vercel.app/](https://pdf-editor-api.vercel.app/)

---

## Features

### 1. PDF Language Translator (`POST /api/translate-pdf`)

- Extracts text page-by-page from text-based PDFs using **PyMuPDF**.
- Translates extracted text using pluggable translation providers:
  - **Google Translate (`google`)** — Free automatic translation via `googletrans` (default, no API key required).
  - **Mock (`mock`)** — Offline dictionary-based translation for testing.
  - **External (`external`)** — Google Cloud Translation v2 REST API (requires API key).
- Generates a fresh, publication-quality PDF with translated text using **ReportLab**.
- Native **Bangla (Bengali) Unicode** shaping powered by **HarfBuzz (`uharfbuzz`)** and bundled **Noto Sans Bengali** fonts.
- Supports 70+ ISO 639-1 language pairs (including English ↔ Bengali).

### 2. PDF Watermark (`POST /editor/pdf/watermark`)

- Applies custom text watermarks to **every page** of a PDF.
- Seven configurable positions: `top-left`, `top-center`, `top-right`, `center`, `bottom-left`, `bottom-center`, `bottom-right`.
- Customizable opacity (`0.0` – `1.0`), hex color (`#RRGGBB` or `#RGB`), and font size (`6`–`200` pt).
- Returns the newly watermarked PDF in-stream without modifying the original document.

### 3. PDF Reformatting Service (`pdf_editor.services.pdf_reformatter`)

- Core service for fixing heading hierarchies, unwrapping broken lines into justified paragraphs, and adding running headers/footers with dynamic page numbering.

---

## Requirements

- Python 3.12+
- `pip` / virtualenv

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/shagorrobidas/pdf-editor-api.git
cd pdf-editor
```

### 2. Create and activate a virtual environment

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note:** `uharfbuzz` provides Python bindings to the HarfBuzz shaping engine, enabling correct rendering of complex scripts like Bengali (conjuncts/যুক্তবর্ণ and vowel signs/matras).

---

## Environment Configuration

Copy the example environment template:

```bash
cp .env.example .env
```

Open `.env` and configure your settings:

```env
# ============================================================
# PDF Editor API — Environment Variables
# ============================================================

# Django Settings
SECRET_KEY=django-insecure-dev-key-change-in-production-please
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost,testserver

# PDF Upload Limit (in megabytes)
MAX_PDF_SIZE_MB=10

# Translation Service
# Options:
#   "google"   — Free Google Translate (default, no API key needed)
#   "mock"     — Offline mode for tests
#   "external" — Official Google Cloud Translation API (requires key)
TRANSLATION_PROVIDER=google

# Required only when TRANSLATION_PROVIDER=external
TRANSLATION_API_KEY=
TRANSLATION_API_URL=https://translation.googleapis.com/language/translate/v2
```

---

## Database Migration & Running the Server

Run migrations to set up the database:

```bash
python manage.py migrate
```

Start the development server:

```bash
python manage.py runserver
```

The server will start at `http://127.0.0.1:8000/`.

---

## API Endpoints & Usage

### 1. Translate PDF

- **Endpoint:** `POST /api/translate-pdf`
- **Content-Type:** `multipart/form-data`

#### Request Parameters

| Parameter         | Type          | Required | Description                                           |
| :---------------- | :------------ | :------- | :---------------------------------------------------- |
| `file`            | File (`.pdf`) | **Yes**  | Text-based PDF file (max 10 MB by default)            |
| `source_language` | String        | **Yes**  | ISO 639-1 language code (e.g. `en`, `bn`, `es`, `fr`) |
| `target_language` | String        | **Yes**  | ISO 639-1 language code (e.g. `bn`, `en`, `de`)       |

#### cURL Example

**Live (Vercel):**

```bash
curl -X POST https://pdf-editor-api.vercel.app/api/translate-pdf \
  -F "file=@sample.pdf" \
  -F "source_language=en" \
  -F "target_language=bn" \
  --output translated.pdf
```

**Local:**

```bash
curl -X POST http://127.0.0.1:8000/api/translate-pdf \
  -F "file=@sample.pdf" \
  -F "source_language=en" \
  -F "target_language=bn" \
  --output translated.pdf
```

#### Success Response (HTTP 200)

- **Content-Type:** `application/pdf`
- **Content-Disposition:** `attachment; filename="translated_en_to_bn.pdf"`
- Returns the generated translated PDF binary.

#### Error Response (HTTP 400)

```json
{
  "error": "A valid PDF file is required (invalid PDF header)."
}
```

---

### 2. Watermark PDF

- **Endpoint:** `POST /editor/pdf/watermark`
- **Content-Type:** `multipart/form-data`

#### Request Parameters

| Parameter   | Type          | Required | Default | Description                                                                                     |
| :---------- | :------------ | :------- | :------ | :---------------------------------------------------------------------------------------------- |
| `file`      | File (`.pdf`) | **Yes**  | —       | PDF file to watermark                                                                           |
| `text`      | String        | **Yes**  | —       | Text to overlay (e.g. `CONFIDENTIAL`)                                                           |
| `position`  | String        | **Yes**  | —       | `top-left`, `top-center`, `top-right`, `center`, `bottom-left`, `bottom-center`, `bottom-right` |
| `opacity`   | Float         | **Yes**  | —       | Opacity from `0.0` (invisible) to `1.0` (solid)                                                 |
| `color`     | String        | **Yes**  | —       | Hex color code (e.g. `#FF0000` or `#F00`)                                                       |
| `font_size` | Integer       | No       | `36`    | Font size in points (`6`–`200`)                                                                 |

#### cURL Example

**Live (Vercel):**

```bash
curl -X POST https://pdf-editor-api.vercel.app/editor/pdf/watermark \
  -F "file=@document.pdf" \
  -F "text=CONFIDENTIAL" \
  -F "position=center" \
  -F "opacity=0.3" \
  -F "color=#FF0000" \
  -F "font_size=48" \
  --output watermarked.pdf
```

**Local:**

```bash
curl -X POST http://127.0.0.1:8000/editor/pdf/watermark \
  -F "file=@document.pdf" \
  -F "text=CONFIDENTIAL" \
  -F "position=center" \
  -F "opacity=0.3" \
  -F "color=#FF0000" \
  -F "font_size=48" \
  --output watermarked.pdf
```

#### Success Response (HTTP 200)

- **Content-Type:** `application/pdf`
- **Content-Disposition:** `attachment; filename="watermarked_document.pdf"`
- Returns the watermarked PDF binary.

#### Error Response (HTTP 400)

```json
{
  "error": "Invalid position. Allowed values are: bottom-center, bottom-left, bottom-right, center, top-center, top-left, top-right."
}
```

---

## Bangla (Bengali) Unicode & Complex Script Support

Bengali is a complex Brahmic script requiring glyph reordering, matra positioning, and conjunct (যুক্তবর্ণ) ligature substitution. Standard PDF generators render disconnected or broken characters without OpenType shaping.

### How It Works Here:

1. **Bundled Fonts**: `NotoSansBengali-Regular.ttf` and `NotoSansBengali-Bold.ttf` are provided in the `fonts/` directory.
2. **ReportLab + HarfBuzz**: Fonts are registered with `shapable=True` via ReportLab's `TTFont`.
3. **OpenType Shaping**: `uharfbuzz` performs full OpenType layout shaping on every text paragraph, ensuring authentic ligature composition and conjunct rendering.

---

## Running Tests

Run the test suite using Django's test runner:

```bash
python manage.py test
```

Or using `pytest`:

```bash
pytest
```

---

## Project Structure

```
pdf-editor/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── fonts/
│   ├── NotoSansBengali-Regular.ttf
│   └── NotoSansBengali-Bold.ttf
├── core/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── pdf_editor/
    ├── __init__.py
    ├── admin.py
    ├── apps.py
    ├── exceptions.py
    ├── models.py
    ├── tests.py
    ├── validators.py
    ├── views.py
    ├── api/
    │   ├── urls.py
    │   ├── serializers/
    │   │   ├── __init__.py
    │   │   ├── translate_pdf.py
    │   │   └── watermark_pdf.py
    │   └── views/
    │       ├── __init__.py
    │       ├── translate_pdf.py
    │       └── watermark_pdf.py
    └── services/
        ├── __init__.py
        ├── pdf_extractor.py
        ├── pdf_generator.py
        ├── pdf_reformatter.py
        ├── translator.py
        └── watermark.py
```

---

## License

This project is open-source and available under the [MIT License](LICENSE).
