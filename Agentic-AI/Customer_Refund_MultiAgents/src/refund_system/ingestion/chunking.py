"""Split parsed SOP text into section chunks and example (code block) chunks."""


def chunk_document(text: str, document_id: str, document_title: str) -> list[dict]:
    """Split a markdown SOP into section chunks and example (code block) chunks."""
    chunks: list[dict] = []
    current_section = ""
    section_lines: list[str] = []
    in_code_block = False
    code_lines: list[str] = []

    def flush_section() -> None:
        content = "\n".join(section_lines).strip()
        if content:
            chunks.append(
                {
                    "document_id": document_id,
                    "document_title": document_title,
                    "section": current_section,
                    "chunk_type": "section",
                    "content": f"## {current_section}\n\n{content}"
                    if current_section
                    else content,
                }
            )

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code_block:
                chunks.append(
                    {
                        "document_id": document_id,
                        "document_title": document_title,
                        "section": current_section,
                        "chunk_type": "example",
                        "content": "\n".join(code_lines),
                    }
                )
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if stripped.startswith("## ") or stripped.startswith("### "):
            flush_section()
            current_section = stripped.lstrip("#").strip()
            section_lines = []
            continue

        section_lines.append(line)

    flush_section()
    return chunks
