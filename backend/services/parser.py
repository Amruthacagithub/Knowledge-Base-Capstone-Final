"""
Document parser — reads PDF, Markdown, and JSON files into text.
"""
from pathlib import Path
import pdfplumber
import json


def parse_document(file_path: Path) -> list[dict]:
    """
    Parse a document file into a list of text segments.

    Returns:
        List of dicts: [{"text": "...", "page": 1}, ...]
    """
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        return _parse_pdf(file_path)
    elif suffix in (".md", ".txt"):
        return _parse_markdown(file_path)
    elif suffix == ".json":
        return _parse_json(file_path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def _parse_pdf(file_path: Path) -> list[dict]:
    """Extract text page-by-page from a PDF."""
    segments = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            if text and text.strip():
                segments.append({"text": text.strip(), "page": i})
    return segments


def _parse_markdown(file_path: Path) -> list[dict]:
    """Read entire markdown/text file as one segment."""
    text = file_path.read_text(encoding="utf-8")
    if text.strip():
        return [{"text": text.strip(), "page": 1}]
    return []


def _parse_json(file_path: Path) -> list[dict]:
    """Extract text fields from a JSON file."""
    data = json.loads(file_path.read_text(encoding="utf-8"))

    if isinstance(data, dict):
        # Try common text fields
        text_parts = []
        for key in ("text", "content", "body", "description"):
            if key in data and isinstance(data[key], str):
                text_parts.append(data[key])
        if text_parts:
            return [{"text": "\n\n".join(text_parts), "page": 1}]

    elif isinstance(data, list):
        segments = []
        for i, item in enumerate(data, start=1):
            if isinstance(item, dict):
                for key in ("text", "content", "body"):
                    if key in item and isinstance(item[key], str):
                        segments.append({"text": item[key], "page": i})
                        break
            elif isinstance(item, str):
                segments.append({"text": item, "page": i})
        return segments

    return []
