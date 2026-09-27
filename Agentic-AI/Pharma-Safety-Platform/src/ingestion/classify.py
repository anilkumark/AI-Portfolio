"""
Document classification. Runs before extraction so each document routes
to the extraction path that actually fits it — a clean digital PDF does
not need OCR, a scanned fax does.

The text-layer check uses PyMuPDF, the same library used for extraction
itself (src/ingestion/pdf_extract.py) — one library for both the
detection and the extraction of digital PDF text, rather than a second
tool doing only the detection.
"""

from enum import Enum
from pathlib import Path

import pymupdf


class DocType(str, Enum):
    DIGITAL_PDF = "digital_pdf"
    SCANNED_FAX = "scanned_fax"
    STRUCTURED_FORM = "structured_form"
    EMAIL = "email"


# A structured CIOMS/MedWatch form is still a PDF, but its filename or a
# known source tag identifies it — this list is maintained alongside the
# partner intake configuration, not guessed from content.
STRUCTURED_FORM_FILENAME_MARKERS = ["cioms", "medwatch", "form3500"]

MIN_CHARS_FOR_USABLE_TEXT_LAYER = 20  # a PDF with a text layer but almost
                                       # no extractable text (e.g. a scanned
                                       # page saved with an empty OCR layer)
                                       # is still treated as needing OCR


def has_usable_text_layer(pdf_path: str) -> bool:
    """
    Opens the PDF and checks whether it has real, extractable text — not
    just whether it CLAIMS to have a text layer. Some scanned documents
    are saved with an empty or near-empty text layer, which would
    otherwise pass a naive check and skip OCR incorrectly.
    """
    doc = pymupdf.open(pdf_path)
    try:
        total_chars = 0
        for page in doc:
            total_chars += len(page.get_text().strip())
            if total_chars >= MIN_CHARS_FOR_USABLE_TEXT_LAYER:
                return True
        return total_chars >= MIN_CHARS_FOR_USABLE_TEXT_LAYER
    finally:
        doc.close()


def classify_document(file_path: str, source_channel: str) -> DocType:
    """
    file_path: local or S3-downloaded path to the document.
    source_channel: how it arrived — 'email', 'upload_portal', 'partner_api'.
    """
    if source_channel == "email":
        # the email body itself; any PDF attachment is classified
        # separately and routed back into this same function
        return DocType.EMAIL

    filename_lower = Path(file_path).name.lower()
    if any(marker in filename_lower for marker in STRUCTURED_FORM_FILENAME_MARKERS):
        return DocType.STRUCTURED_FORM

    if file_path.lower().endswith(".pdf"):
        return DocType.DIGITAL_PDF if has_usable_text_layer(file_path) else DocType.SCANNED_FAX

    # image formats (fax delivery is frequently TIFF or JPEG, not PDF)
    if file_path.lower().endswith((".tiff", ".tif", ".jpg", ".jpeg", ".png")):
        return DocType.SCANNED_FAX

    raise ValueError(f"Unrecognized document format: {file_path}")
