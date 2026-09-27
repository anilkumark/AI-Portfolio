"""
Digital PDF text extraction via PyMuPDF. Used only when classify.py has
already determined the document has a usable text layer — this module
does not decide that, it trusts the classification step and extracts.
"""

import pymupdf


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extracts plain text from every page of a digital PDF, in reading
    order. Page breaks are preserved as double newlines so downstream
    steps can still reason about page boundaries if needed."""
    doc = pymupdf.open(pdf_path)
    try:
        pages = [page.get_text() for page in doc]
        return "\n\n".join(pages)
    finally:
        doc.close()


def extract_text_with_page_numbers(pdf_path: str) -> list[dict]:
    """Same extraction, but keeps each page separate with its page number
    attached — used when the downstream step (e.g. audit trail) needs to
    cite which page a piece of extracted text came from."""
    doc = pymupdf.open(pdf_path)
    try:
        return [
            {"page_number": i + 1, "text": page.get_text()}
            for i, page in enumerate(doc)
        ]
    finally:
        doc.close()
