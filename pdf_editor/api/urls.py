from django.urls import path

from pdf_editor.api.views import TranslatePDFView, WatermarkPDFView

urlpatterns = [
    path("api/translate-pdf", TranslatePDFView.as_view(), name="translate-pdf"),
    path("editor/pdf/watermark", WatermarkPDFView.as_view(), name="watermark-pdf"),
    # path("editor/pdf/reformat", ReformatPDFView.as_view(), name="reformat-pdf"),
]
