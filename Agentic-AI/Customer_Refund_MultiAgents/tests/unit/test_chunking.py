"""Unit tests for the SOP markdown chunking logic (no DB/API calls)."""

from refund_system.ingestion.chunking import chunk_document
from refund_system.ingestion.parsers import extract_doc_metadata

SAMPLE_DOC = """# Standard Operating Procedure: Sample Policy

**Document ID:** SOP-TEST-001

## 1. PURPOSE

This is a test policy document used for unit testing.

## 2. EXAMPLE CALCULATION

Here is an explanation before the example.

```
Base Price: $100
Fee: $10
Refund: $90
```

More text after the example.
"""


def test_extract_doc_metadata():
    doc_id, title = extract_doc_metadata(SAMPLE_DOC)
    assert doc_id == "SOP-TEST-001"
    assert title == "Standard Operating Procedure: Sample Policy"


def test_chunk_document_splits_sections_and_examples():
    chunks = chunk_document(SAMPLE_DOC, "SOP-TEST-001", "Sample Policy")

    section_chunks = [c for c in chunks if c["chunk_type"] == "section"]
    example_chunks = [c for c in chunks if c["chunk_type"] == "example"]

    # 3 section chunks: the title/metadata preamble (before the first "##"
    # heading) plus the two "##" sections.
    assert len(section_chunks) == 3
    assert len(example_chunks) == 1

    assert any("test policy document" in c["content"] for c in section_chunks)
    assert "Refund: $90" in example_chunks[0]["content"]

    for chunk in chunks:
        assert chunk["document_id"] == "SOP-TEST-001"
        assert chunk["document_title"] == "Sample Policy"


def test_chunk_document_empty_text_returns_no_chunks():
    assert chunk_document("", "SOP-TEST-002", "Empty Doc") == []
