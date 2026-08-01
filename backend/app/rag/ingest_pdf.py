# backend/app/rag/ingest_pdf.py

import html
from pathlib import Path

from docling.document_converter import DocumentConverter

# Source PDFs — the raw, HR-authored originals
SOURCE_DOCS_DIR = Path(__file__).parent / "source_docs"

# Destination — this is the ONLY folder NeMo Guardrails actually reads from
KB_DIR = Path(__file__).parent.parent.parent / "guardrails" / "kb"

# Map: source PDF filename -> destination markdown filename
DOCUMENTS = {
    "Quilltony_Technologies_Employee_Handbook.pdf": "employee_handbook.md",
    "Quilltony_Technologies_Compensation_Guidelines.pdf": "compensation_guidelines.md",
}


def clean_markdown(text: str) -> str:
    """
    Docling occasionally leaves HTML entities (&amp; instead of &) in headers
    pulled from PDF metadata/title text. html.unescape() converts all such
    entities back to plain characters in one pass.
    """
    return html.unescape(text)


def convert_pdf_to_markdown(pdf_path: Path) -> str:
    converter = DocumentConverter()
    result = converter.convert(str(pdf_path))
    doc = result.document
    markdown = doc.export_to_markdown()
    return clean_markdown(markdown)


def ingest_all() -> None:
    KB_DIR.mkdir(parents=True, exist_ok=True)

    for source_filename, dest_filename in DOCUMENTS.items():
        source_path = SOURCE_DOCS_DIR / source_filename

        if not source_path.exists():
            print(f"[SKIP] Source not found: {source_path}")
            continue

        print(f"[CONVERTING] {source_filename} -> {dest_filename}")
        markdown_content = convert_pdf_to_markdown(source_path)

        dest_path = KB_DIR / dest_filename
        dest_path.write_text(markdown_content, encoding="utf-8")

        word_count = len(markdown_content.split())
        print(f"[DONE] Wrote {dest_path} ({word_count} words)")


if __name__ == "__main__":
    ingest_all()