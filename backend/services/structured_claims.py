"""Strict model-claim parsing and evidence verification."""
import hashlib
import json
from dataclasses import dataclass
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from backend.services.claim_verifier import NLIScorer, VerificationLabel, verify_claim
from backend.services.prompt_safety import assess_source_text


MAX_STRUCTURED_OUTPUT_BYTES = 20_000


class StructuredOutputError(ValueError):
    """Raised when model output violates the structured claim contract."""


class ProposedClaim(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(min_length=1, max_length=500)
    evidence_markers: list[int] = Field(min_length=1, max_length=4)

    @field_validator("evidence_markers")
    @classmethod
    def markers_must_be_unique_and_positive(cls, markers: list[int]) -> list[int]:
        if any(marker < 1 for marker in markers):
            raise ValueError("evidence markers must be positive")
        if len(markers) != len(set(markers)):
            raise ValueError("evidence markers must be unique")
        return markers


class ProposedClaimBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[ProposedClaim] = Field(max_length=8)


@dataclass(frozen=True)
class VerifiedGeneratedClaim:
    id: str
    text: str
    status: VerificationLabel
    confidence: float
    evidence_markers: tuple[int, ...]
    evidence_ids: tuple[str, ...]


def parse_structured_claims(raw_output: str) -> ProposedClaimBundle:
    """Parse strict JSON only; Markdown fences and extra fields are invalid."""
    if len(raw_output.encode("utf-8")) > MAX_STRUCTURED_OUTPUT_BYTES:
        raise StructuredOutputError("structured output exceeds size limit")
    try:
        payload = json.loads(raw_output)
        return ProposedClaimBundle.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise StructuredOutputError("invalid structured claim output") from exc


def verify_structured_claims(
    bundle: ProposedClaimBundle,
    chunks: Sequence[dict],
    *,
    scorer: NLIScorer | None = None,
) -> tuple[VerifiedGeneratedClaim, ...]:
    """Verify proposed claims and retain only code-validated evidence identities."""
    verified = []
    seen_claims = set()
    for proposed in bundle.claims:
        claim_key = " ".join(proposed.text.casefold().split())
        if claim_key in seen_claims:
            continue
        seen_claims.add(claim_key)

        valid_markers = all(marker <= len(chunks) for marker in proposed.evidence_markers)
        if not valid_markers:
            verified.append(_invalid_citation_claim(proposed))
            continue

        safe_evidence = [
            (marker, chunks[marker - 1])
            for marker in proposed.evidence_markers
            if not assess_source_text(str(chunks[marker - 1].get("text", ""))).unsafe
        ]
        if not safe_evidence:
            verified.append(_invalid_citation_claim(proposed))
            continue
        result = verify_claim(
            proposed.text,
            [str(chunk.get("text", "")) for _marker, chunk in safe_evidence],
            scorer=scorer,
        )
        selected_markers = ()
        if result.evidence_index is not None:
            selected_markers = (safe_evidence[result.evidence_index][0],)
        evidence_ids = tuple(
            _chunk_evidence_id(chunks[marker - 1], marker)
            for marker in selected_markers
        )
        verified.append(
            VerifiedGeneratedClaim(
                id=_claim_id(proposed.text, evidence_ids),
                text=proposed.text,
                status=result.label,
                confidence=result.confidence,
                evidence_markers=selected_markers,
                evidence_ids=evidence_ids,
            )
        )
    return tuple(verified)


def _invalid_citation_claim(proposed: ProposedClaim) -> VerifiedGeneratedClaim:
    return VerifiedGeneratedClaim(
        id=_claim_id(proposed.text, ()),
        text=proposed.text,
        status="insufficient",
        confidence=1.0,
        evidence_markers=(),
        evidence_ids=(),
    )


def _chunk_evidence_id(chunk: dict, marker: int) -> str:
    chunk_id = chunk.get("chunk_id") or chunk.get("id")
    if chunk_id:
        return str(chunk_id)
    doc_id = str(chunk.get("doc_id", "unknown"))
    chunk_index = chunk.get("chunk_index", marker - 1)
    return f"{doc_id}:{chunk_index}"


def _claim_id(text: str, evidence_ids: Sequence[str]) -> str:
    material = json.dumps(
        {"text": text, "evidence_ids": list(evidence_ids)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()