"""High-precision quarantine for instruction-like retrieved source text."""
import html
import re
from dataclasses import dataclass


_INJECTION_PATTERNS = (
    (
        "instruction_override",
        re.compile(
            r"\b(?:ignore|disregard|forget)\s+(?:all\s+)?(?:the\s+)?"
            r"(?:previous|prior|above|system)\s+(?:instructions?|prompts?)\b",
            re.I,
        ),
    ),
    ("identity_override", re.compile(r"\byou\s+are\s+now\b", re.I)),
    (
        "role_tag",
        re.compile(r"<\s*(?:system|assistant|developer)\b", re.I),
    ),
    (
        "role_prefix",
        re.compile(r"(?:^|\n)\s*(?:system|assistant|developer)\s*:\s*", re.I),
    ),
    (
        "credential_exfiltration",
        re.compile(
            r"\b(?:please|now|must)\s+(?:reveal|print|return|exfiltrate)\s+"
            r"(?:the\s+)?(?:api\s+keys?|secrets?|credentials?|system\s+prompt)\b",
            re.I,
        ),
    ),
    (
        "developer_override",
        re.compile(
            r"\boverride\s+(?:the\s+)?(?:system|developer)\s+"
            r"(?:prompt|instructions?)\b",
            re.I,
        ),
    ),
)


@dataclass(frozen=True)
class SourceSafety:
    unsafe: bool
    reasons: tuple[str, ...]


def assess_source_text(text: str) -> SourceSafety:
    reasons = tuple(
        name for name, pattern in _INJECTION_PATTERNS if pattern.search(text)
    )
    return SourceSafety(bool(reasons), reasons)


def source_text_for_prompt(text: str) -> str:
    """Return escaped source data or a non-instructional quarantine notice."""
    if assess_source_text(text).unsafe:
        return "[Source quarantined: instruction-like content omitted.]"
    return html.escape(text, quote=False)