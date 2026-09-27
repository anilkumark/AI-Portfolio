"""Parse raw market-insights documents to extract metadata (title, document ID)."""

import re


def extract_doc_metadata(text: str) -> tuple[str, str]:
    """Pull the document title (# heading) and Document ID out of the file header."""
    title_match = re.search(r"^#\s+(.*)$", text, re.MULTILINE)
    id_match = re.search(r"\*\*Document ID:\*\*\s*(\S+)", text)
    title = title_match.group(1).strip() if title_match else "Unknown"
    doc_id = id_match.group(1).strip() if id_match else "UNKNOWN"
    return doc_id, title
