"""
Unlike the AWS-dependent modules, PyMuPDF needs no credentials and no
network access — these tests run against real PDF files on disk, right
here, no mocking.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingestion.classify import classify_document, has_usable_text_layer, DocType
from src.ingestion.pdf_extract import extract_text_from_pdf, extract_text_with_page_numbers

FIXTURES = Path(__file__).resolve().parent / "fixtures"
DIGITAL_PDF = str(FIXTURES / "digital_case_report.pdf")
SPARSE_PDF = str(FIXTURES / "scanned_no_text_layer.pdf")


def test_digital_pdf_has_usable_text_layer():
    assert has_usable_text_layer(DIGITAL_PDF) is True


def test_sparse_pdf_does_not_have_usable_text_layer():
    """A PDF with only one stray character should NOT pass as having a
    usable text layer — this is the exact failure mode that a naive
    'does it have any text at all' check would miss."""
    assert has_usable_text_layer(SPARSE_PDF) is False


def test_classify_digital_pdf_as_digital():
    result = classify_document(DIGITAL_PDF, source_channel="upload_portal")
    assert result == DocType.DIGITAL_PDF


def test_classify_sparse_pdf_as_scanned():
    """A PDF with effectively no real text routes to the OCR path, even
    though it technically 'is a PDF' — content, not file type, decides."""
    result = classify_document(SPARSE_PDF, source_channel="upload_portal")
    assert result == DocType.SCANNED_FAX


def test_classify_by_filename_marker_overrides_content_check():
    result = classify_document("/tmp/CIOMS_report_2026.pdf", source_channel="upload_portal")
    assert result == DocType.STRUCTURED_FORM


def test_classify_email_channel_short_circuits():
    result = classify_document("anything.pdf", source_channel="email")
    assert result == DocType.EMAIL


def test_classify_image_extensions_as_scanned():
    for ext in [".tiff", ".jpg", ".png"]:
        result = classify_document(f"/tmp/fax_intake{ext}", source_channel="upload_portal")
        assert result == DocType.SCANNED_FAX


def test_classify_unrecognized_format_raises():
    import pytest
    with pytest.raises(ValueError, match="Unrecognized"):
        classify_document("/tmp/something.docx", source_channel="upload_portal")


def test_extract_text_from_real_digital_pdf():
    text = extract_text_from_pdf(DIGITAL_PDF)
    assert "Drugamab" in text
    assert "Hospitalized" in text
    assert "rash" in text.lower()


def test_extract_with_page_numbers_matches_page_count():
    pages = extract_text_with_page_numbers(DIGITAL_PDF)
    assert len(pages) == 1
    assert pages[0]["page_number"] == 1
    assert "Drugamab" in pages[0]["text"]
