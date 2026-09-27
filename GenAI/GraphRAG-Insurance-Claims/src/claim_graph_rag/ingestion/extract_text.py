"""Extracts raw text from the downloaded PDF documents, page by page, and
saves the result to data/processed/ so extraction only has to run once."""

import json
from pathlib import Path

from pypdf import PdfReader

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"


def extract_pages(pdf_path: Path) -> list[dict]:
    reader = PdfReader(pdf_path)
    return [
        {"page_number": i + 1, "text": page.extract_text() or ""}
        for i, page in enumerate(reader.pages)
    ]


def save_extracted_text(pdf_path: Path, pages: list[dict]) -> Path:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / f"{pdf_path.stem}.json"
    out_path.write_text(json.dumps(pages, indent=2), encoding="utf-8")
    return out_path


if __name__ == "__main__":
    for pdf_file in RAW_DIR.glob("*.pdf"):
        pages = extract_pages(pdf_file)
        out_path = save_extracted_text(pdf_file, pages)
        non_empty = [p for p in pages if p["text"].strip()]
        print(
            f"{pdf_file.name}: {len(pages)} pages, {len(non_empty)} with text -> saved to {out_path}"
        )
