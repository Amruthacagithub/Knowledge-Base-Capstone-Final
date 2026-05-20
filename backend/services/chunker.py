"""
Text chunker — splits parsed text into overlapping chunks with page metadata.
"""
import re


def chunk_text(text: str, max_tokens: int = 200, overlap_tokens: int = 50) -> list[str]:
    """
    Split text into chunks of roughly max_tokens words with overlap.

    Returns:
        List of chunk strings.
    """
    paragraphs = re.split(r"\n\s*\n", text.strip())
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return []

    chunks = []
    current_chunk_words = []
    current_chunk_parts = []

    for para in paragraphs:
        para_words = para.split()

        if current_chunk_words and (len(current_chunk_words) + len(para_words)) > max_tokens:
            chunks.append("\n\n".join(current_chunk_parts))
            overlap_words = (
                current_chunk_words[-overlap_tokens:]
                if len(current_chunk_words) > overlap_tokens
                else current_chunk_words[:]
            )
            current_chunk_words = overlap_words + para_words
            current_chunk_parts = [" ".join(overlap_words), para]
        else:
            current_chunk_words.extend(para_words)
            current_chunk_parts.append(para)

    if current_chunk_parts:
        chunks.append("\n\n".join(current_chunk_parts))

    return chunks


def chunk_document_segments(
    segments: list[dict],
    max_tokens: int = 200,
    overlap_tokens: int = 50,
) -> list[dict]:
    """
    Chunk parsed document segments, preserving PDF page boundaries.

    Args:
        segments: List of {"text": "...", "page": N} from the parser.

    Returns:
        List of {"text", "page_start", "page_end"} dicts.
    """
    chunks_out: list[dict] = []

    for seg in segments:
        page = int(seg.get("page", 1))
        text = seg.get("text", "")
        for chunk_str in chunk_text(text, max_tokens=max_tokens, overlap_tokens=overlap_tokens):
            chunks_out.append(
                {
                    "text": chunk_str,
                    "page_start": page,
                    "page_end": page,
                }
            )

    return chunks_out
