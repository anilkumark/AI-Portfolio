"""Splits extracted PDF text into chunks — reads from the saved
data/processed/*.json files instead of re-running extraction every time."""

import json
from pathlib import Path

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

PROCESSED_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"

encoding = tiktoken.get_encoding("cl100k_base")


def token_length(text: str) -> int:
    return len(encoding.encode(text))


splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=40,
    length_function=token_length,
)


def chunk_document(processed_json_path: Path) -> list[dict]:
    pages = json.loads(processed_json_path.read_text(encoding="utf-8"))
    document_name = processed_json_path.stem
    chunks = []
    for page in pages:
        for piece in splitter.split_text(page["text"]):
            chunks.append(
                {
                    "document": document_name,
                    "page_number": page["page_number"],
                    "content": piece,
                }
            )
    return chunks


if __name__ == "__main__":
    for json_file in PROCESSED_DIR.glob("*.json"):
        chunks = chunk_document(json_file)
        total_tokens = sum(token_length(c["content"]) for c in chunks)
        print(f"{json_file.name}: {len(chunks)} chunks, {total_tokens:,} total tokens")
        print(chunks[len(chunks) // 2])
        print("---")
