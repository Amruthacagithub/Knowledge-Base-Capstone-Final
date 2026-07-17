"""Deterministic, provenance-first baseline extraction for engineering text."""
import hashlib
import re
import uuid
from dataclasses import dataclass


EXTRACTOR_NAME = "trust-rag-engineering-rules"
EXTRACTOR_VERSION = "1.1.0"
EVIDENCE_SCHEMA_VERSION = "1.0"

_ENTITY_NAMESPACE = uuid.UUID("1fdfc404-3ee0-4e87-b92a-f68a23a9bc3c")
_MENTION_NAMESPACE = uuid.UUID("b411a1db-c253-4c64-ae18-4b5c7d174847")
_CLAIM_NAMESPACE = uuid.UUID("91782fc5-2572-446c-a7d5-7087142f7e4a")
_RELATIONSHIP_NAMESPACE = uuid.UUID("df6e1332-daac-4fd3-b780-b72b76bf2ccc")

_SYSTEM_ALIASES = (
    (r"\bTechNova Platform\b", "technova_platform", 0.98),
    (r"\bAWS Secrets Manager\b", "aws_secrets_manager", 0.99),
    (r"\bGitHub Actions\b", "github_actions", 0.99),
    (r"\bAWS RDS\b", "aws_rds", 0.99),
    (r"\bAWS EKS\b", "aws_eks", 0.99),
    (r"\bArgo CD\b", "argo_cd", 0.99),
    (r"\bPostgreSQL(?:\s+\d+(?:\.\d+)*)?\b", "postgresql", 0.98),
    (r"\bPostgres(?:\s+\d+(?:\.\d+)*)?\b", "postgresql", 0.96),
    (r"\bRDS\b", "aws_rds", 0.92),
    (r"\bRedis(?:\s+\d+(?:\.\d+)*)?\b", "redis", 0.98),
    (r"\bElasticsearch(?:\s+\d+(?:\.\d+)*)?\b", "elasticsearch", 0.98),
    (r"\bElastiCache\b", "elasticache", 0.98),
    (r"\bPgBouncer\b", "pgbouncer", 0.98),
    (r"\bKubernetes\b", "kubernetes", 0.98),
    (r"\bPagerDuty\b", "pagerduty", 0.98),
    (r"\bLaunchDarkly\b", "launchdarkly", 0.98),
    (r"\bSendGrid\b", "sendgrid", 0.98),
    (r"\bDatadog\b", "datadog", 0.98),
    (r"\bStripe\b", "stripe", 0.98),
    (r"\bDocument Search\b", "document_search", 0.92),
    (r"\bCustomer Checkout\b", "customer_checkout", 0.92),
    (r"\bSlack\b", "slack", 0.98),
    (r"\bKong\b", "kong", 0.98),
    (r"\bS3\b", "s3", 0.98),
    (r"\bEKS\b", "eks", 0.98),
    (r"\bgit\b", "git", 0.85),
)

_ENTITY_PATTERNS = (
    (
        "incident",
        re.compile(r"\bINC-\d+\b", re.IGNORECASE),
        0.99,
    ),
    (
        "system",
        re.compile(
            r"\b(?:[A-Z][A-Za-z0-9-]*\s+){1,3}"
            r"(?:Service|Microservice|Gateway|Database|Cluster|API)\b"
        ),
        0.90,
    ),
    (
        "system",
        re.compile(
            r"\b[a-z][a-z0-9-]*\s+"
            r"(?:service|microservice|gateway|database|cluster|api|engine)\b"
        ),
        0.78,
    ),
    (
        "document",
        re.compile(
            r"\b(?:[A-Z][A-Za-z0-9-]*\s+){0,4}"
            r"(?:Runbook|Policy|Process|Procedure|Guide)\b"
        ),
        0.88,
    ),
)

_RELATION_PATTERNS = (
    ("depends_on", re.compile(r"\bdepends?\s+on\b", re.IGNORECASE)),
    ("connected_to", re.compile(r"\bconnects?\s+to\b", re.IGNORECASE)),
    ("integrates_with", re.compile(r"\bintegrat(?:es?|ion)\b", re.IGNORECASE)),
    ("hosts", re.compile(r"\bhosts?\b", re.IGNORECASE)),
    ("routes_to", re.compile(r"\broutes?\b.*\bto\b", re.IGNORECASE)),
    ("powers", re.compile(r"\bpowers?\b", re.IGNORECASE)),
    ("uses", re.compile(r"\bsends?\b.*\bthrough\b", re.IGNORECASE)),
    ("stores_in", re.compile(r"\bwrites?\b.*\bto\b", re.IGNORECASE)),
    ("deployed_on", re.compile(r"\bdeployed\s+on\b|\bon\b", re.IGNORECASE)),
    ("depends_on", re.compile(r"\bconnections?\s+(?:from|between)\b", re.IGNORECASE)),
    ("affected", re.compile(r"\baffected\b", re.IGNORECASE)),
    ("mitigates", re.compile(r"\bmitigates?\b", re.IGNORECASE)),
    ("caused", re.compile(r"\bcaused?\b", re.IGNORECASE)),
    ("references", re.compile(r"\breferences?\b", re.IGNORECASE)),
    ("uses", re.compile(r"\buses?\b", re.IGNORECASE)),
)

_FACTUAL_CUE = re.compile(
    r"\b(?:is|are|was|were|has|have|must|should|will|affected|depend|depends|"
    r"caused|use|uses|mitigates|references|requires|allows|prohibits|expires|rotates?|"
    r"routes?|hosts?|connects?|writes?|sends?|store|stores|stored|processes?|"
    r"handles?|integrates?|powers?|creates?|"
    r"failed|check|checks|verify|verifies)\b",
    re.IGNORECASE,
)
_SENTENCE_PATTERN = re.compile(r"[^.!?\n]+(?:[.!?]+|(?=\n)|$)")


@dataclass(frozen=True)
class ExtractedEntity:
    id: str
    entity_type: str
    canonical_name: str
    display_name: str


@dataclass(frozen=True)
class ExtractedMention:
    id: str
    entity_id: str
    surface_text: str
    start_char: int
    end_char: int
    confidence: float


@dataclass(frozen=True)
class ExtractedClaim:
    id: str
    claim_hash: str
    claim_text: str
    subject_entity_id: str | None
    predicate: str
    object_text: str | None
    polarity: bool
    confidence: float


@dataclass(frozen=True)
class ExtractedRelationship:
    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    evidence_text: str
    confidence: float


@dataclass(frozen=True)
class ChunkEvidence:
    entities: tuple[ExtractedEntity, ...]
    mentions: tuple[ExtractedMention, ...]
    claims: tuple[ExtractedClaim, ...]
    relationships: tuple[ExtractedRelationship, ...]


@dataclass(frozen=True)
class _EntityCandidate:
    entity_type: str
    canonical_name: str
    display_name: str
    start_char: int
    end_char: int
    confidence: float


def extract_chunk_evidence(chunk_id: str, text: str) -> ChunkEvidence:
    """Extract explicitly evidenced engineering entities, claims, and relations."""
    if not chunk_id:
        raise ValueError("chunk_id is required")

    entities_by_id: dict[str, ExtractedEntity] = {}
    mentions = _extract_mentions(chunk_id, text, entities_by_id)
    relationships = _extract_relationships(chunk_id, text, mentions, entities_by_id)
    claims = _extract_claims(chunk_id, text, mentions, relationships, entities_by_id)
    entities = tuple(sorted(entities_by_id.values(), key=lambda entity: entity.id))
    return ChunkEvidence(
        entities=entities,
        mentions=tuple(mentions),
        claims=tuple(claims),
        relationships=tuple(relationships),
    )


def extraction_run_id(document_version_id: str) -> str:
    """Return the stable identity of this extractor configuration for a version."""
    source = (
        f"{document_version_id}:{EXTRACTOR_NAME}:"
        f"{EXTRACTOR_VERSION}:{EVIDENCE_SCHEMA_VERSION}"
    )
    return str(uuid.uuid5(_RELATIONSHIP_NAMESPACE, source))


def _extract_mentions(
    chunk_id: str,
    text: str,
    entities_by_id: dict[str, ExtractedEntity],
) -> list[ExtractedMention]:
    mentions: list[ExtractedMention] = []
    candidates: list[_EntityCandidate] = []
    for entity_type, pattern, confidence in _ENTITY_PATTERNS:
        for match in pattern.finditer(text):
            surface = match.group(0)
            candidates.append(
                _EntityCandidate(
                    entity_type=entity_type,
                    canonical_name=_canonicalize(surface),
                    display_name=surface,
                    start_char=match.start(),
                    end_char=match.end(),
                    confidence=confidence,
                )
            )
    for pattern_text, canonical_name, confidence in _SYSTEM_ALIASES:
        for match in re.finditer(pattern_text, text, re.IGNORECASE):
            candidates.append(
                _EntityCandidate(
                    entity_type="system",
                    canonical_name=canonical_name,
                    display_name=match.group(0),
                    start_char=match.start(),
                    end_char=match.end(),
                    confidence=confidence,
                )
            )
    candidates.extend(_slash_service_candidates(text))

    selected: list[_EntityCandidate] = []
    for candidate in sorted(
        candidates,
        key=lambda item: (
            -(item.end_char - item.start_char),
            -item.confidence,
            item.start_char,
        ),
    ):
        if any(_spans_overlap(candidate, existing) for existing in selected):
            continue
        selected.append(candidate)

    for candidate in sorted(selected, key=lambda item: item.start_char):
        canonical_name = candidate.canonical_name
        entity_id = _stable_id(
            _ENTITY_NAMESPACE,
            candidate.entity_type,
            canonical_name,
        )
        entities_by_id.setdefault(
            entity_id,
            ExtractedEntity(
                id=entity_id,
                entity_type=candidate.entity_type,
                canonical_name=canonical_name,
                display_name=candidate.display_name,
            ),
        )
        mentions.append(
            ExtractedMention(
                id=_stable_id(
                    _MENTION_NAMESPACE,
                    chunk_id,
                    entity_id,
                    str(candidate.start_char),
                    str(candidate.end_char),
                ),
                entity_id=entity_id,
                surface_text=candidate.display_name,
                start_char=candidate.start_char,
                end_char=candidate.end_char,
                confidence=candidate.confidence,
            )
        )
    return sorted(mentions, key=lambda mention: (mention.start_char, mention.end_char))


def _extract_relationships(
    chunk_id: str,
    text: str,
    mentions: list[ExtractedMention],
    entities_by_id: dict[str, ExtractedEntity],
) -> list[ExtractedRelationship]:
    relationships: list[ExtractedRelationship] = []
    previous_subject: ExtractedMention | None = None
    for sentence_start, sentence_end, sentence in _sentence_spans(text):
        sentence_mentions = [
            mention
            for mention in mentions
            if sentence_start <= mention.start_char and mention.end_char <= sentence_end
        ]
        if (
            previous_subject is not None
            and len(sentence_mentions) == 1
            and re.match(r"^Integrates?\s+with\b", sentence, re.IGNORECASE)
        ):
            target = sentence_mentions[0]
            relationships.append(
                _relationship(
                    chunk_id,
                    previous_subject,
                    target,
                    "integrates_with",
                    sentence,
                    confidence=0.84,
                )
            )
        for source_index, source in enumerate(sentence_mentions):
            if source_index + 1 >= len(sentence_mentions):
                continue
            target = sentence_mentions[source_index + 1]
            between = text[source.end_char : target.start_char]
            relationship_type = _relationship_type(
                between,
                sentence,
                entities_by_id[source.entity_id],
                entities_by_id[target.entity_id],
            )
            if relationship_type is None:
                continue
            relationships.append(
                _relationship(
                    chunk_id,
                    source,
                    target,
                    relationship_type,
                    sentence,
                )
            )
            relationships.extend(
                _list_fanout_relationships(
                    chunk_id,
                    text,
                    sentence,
                    source,
                    sentence_mentions,
                    source_index + 1,
                    relationship_type,
                )
            )
        if sentence_mentions:
            previous_subject = sentence_mentions[0]
    return relationships


def _extract_claims(
    chunk_id: str,
    text: str,
    mentions: list[ExtractedMention],
    relationships: list[ExtractedRelationship],
    entities_by_id: dict[str, ExtractedEntity],
) -> list[ExtractedClaim]:
    claims: list[ExtractedClaim] = []
    for sentence_start, sentence_end, sentence in _sentence_spans(text):
        sentence_mentions = _mentions_in_span(
            mentions,
            sentence_start,
            sentence_end,
        )
        claim = _claim_from_sentence(
            chunk_id,
            sentence,
            sentence_mentions,
            relationships,
            entities_by_id,
        )
        if claim is not None:
            claims.append(claim)
    return claims


def _mentions_in_span(
    mentions: list[ExtractedMention],
    start_char: int,
    end_char: int,
) -> list[ExtractedMention]:
    return [
        mention
        for mention in mentions
        if start_char <= mention.start_char and mention.end_char <= end_char
    ]


def _claim_from_sentence(
    chunk_id: str,
    sentence: str,
    sentence_mentions: list[ExtractedMention],
    relationships: list[ExtractedRelationship],
    entities_by_id: dict[str, ExtractedEntity],
) -> ExtractedClaim | None:
    if not sentence_mentions:
        return None
    primary_relationship = next(
        (
            relationship
            for relationship in relationships
            if relationship.evidence_text == sentence
        ),
        None,
    )
    if primary_relationship is None and not _is_assertive(sentence):
        return None

    subject_id = sentence_mentions[0].entity_id
    predicate = "states"
    object_text = None
    confidence = 0.75
    if primary_relationship is not None:
        subject_id = primary_relationship.source_entity_id
        predicate = primary_relationship.relationship_type
        object_text = entities_by_id[
            primary_relationship.target_entity_id
        ].display_name
        confidence = 0.85
    elif re.search(r"\bintegrates?\s+with\b", sentence, re.IGNORECASE):
        predicate = "integrates_with"

    claim_hash = hashlib.sha256(_normalize_claim(sentence).encode("utf-8")).hexdigest()
    return ExtractedClaim(
        id=_stable_id(_CLAIM_NAMESPACE, chunk_id, claim_hash),
        claim_hash=claim_hash,
        claim_text=sentence,
        subject_entity_id=subject_id,
        predicate=predicate,
        object_text=object_text,
        polarity=not _is_negated(sentence),
        confidence=confidence,
    )


def _sentence_spans(text: str):
    for match in _SENTENCE_PATTERN.finditer(text):
        raw = match.group(0)
        sentence = raw.strip()
        if not sentence:
            continue
        leading = len(raw) - len(raw.lstrip())
        start = match.start() + leading
        yield start, start + len(sentence), sentence


def _relationship_type(
    between: str,
    sentence: str,
    source_entity: ExtractedEntity,
    target_entity: ExtractedEntity,
) -> str | None:
    sentence_lower = sentence.lower()
    between_lower = between.lower()
    structural = _structural_relationship_type(
        between,
        sentence_lower,
        between_lower,
        source_entity,
        target_entity,
    )
    if structural is not None:
        return structural
    for relationship_type, pattern in _RELATION_PATTERNS:
        if pattern.search(between):
            return relationship_type
    return None


def _structural_relationship_type(
    between: str,
    sentence_lower: str,
    between_lower: str,
    source_entity: ExtractedEntity,
    target_entity: ExtractedEntity,
) -> str | None:
    if between.count("→") == 1:
        return _arrow_relationship_type(sentence_lower, source_entity)
    if "integration" in sentence_lower and "via" in between_lower:
        return "integrates_with"
    if "connection between" in sentence_lower and " and " in between_lower:
        return "connected_to"
    if "connections from" in sentence_lower and " to " in between_lower:
        return "connected_to"
    if _is_parenthetical_deployment(between, source_entity, target_entity):
        return "deployed_on"
    return None


def _arrow_relationship_type(
    sentence_lower: str,
    source_entity: ExtractedEntity,
) -> str:
    if "deploy" in sentence_lower:
        return "deploys_to"
    if source_entity.canonical_name.endswith("gateway"):
        return "routes_to"
    return "depends_on"


def _is_parenthetical_deployment(
    between: str,
    source_entity: ExtractedEntity,
    target_entity: ExtractedEntity,
) -> bool:
    return (
        source_entity.canonical_name in {"redis", "postgresql"}
        and "(" in between
        and target_entity.canonical_name in {"elasticache", "aws_rds"}
    )


def _list_fanout_relationships(
    chunk_id: str,
    text: str,
    sentence: str,
    source: ExtractedMention,
    mentions: list[ExtractedMention],
    first_target_index: int,
    relationship_type: str,
) -> list[ExtractedRelationship]:
    relationships = []
    previous_target = mentions[first_target_index]
    for target in mentions[first_target_index + 1 :]:
        separator = text[previous_target.end_char : target.start_char]
        if re.fullmatch(r"\s*(?:,\s*(?:and\s+)?|and\s+|or\s+)", separator) is None:
            break
        relationships.append(
            _relationship(
                chunk_id,
                source,
                target,
                relationship_type,
                sentence,
            )
        )
        previous_target = target
    return relationships


def _canonicalize(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    for prefix in ("the_", "our_", "third_party_"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
    return normalized.replace("_microservice", "_service")


def _normalize_claim(value: str) -> str:
    return " ".join(value.lower().split())


def _is_negated(sentence: str) -> bool:
    return re.search(r"\b(?:not|never|no longer|prohibited)\b", sentence, re.IGNORECASE) is not None


def _stable_id(namespace: uuid.UUID, *parts: str) -> str:
    return str(uuid.uuid5(namespace, ":".join(parts)))


def _is_assertive(sentence: str) -> bool:
    if _FACTUAL_CUE.search(sentence):
        return True
    if "—" in sentence:
        return True
    return sentence.lstrip().startswith("|") and any(character.isdigit() for character in sentence)


def _spans_overlap(left: _EntityCandidate, right: _EntityCandidate) -> bool:
    return left.start_char < right.end_char and right.start_char < left.end_char


def _slash_service_candidates(text: str) -> list[_EntityCandidate]:
    candidates = []
    pattern = re.compile(
        r"\b([A-Z][A-Za-z0-9-]*)/([A-Z][A-Za-z0-9-]*)\s+service\b"
    )
    for match in pattern.finditer(text):
        for group_index in (1, 2):
            descriptor = match.group(group_index)
            start = match.start(group_index)
            end = match.end() if group_index == 2 else match.end(group_index)
            candidates.append(
                _EntityCandidate(
                    entity_type="system",
                    canonical_name=f"{descriptor.lower()}_service",
                    display_name=text[start:end],
                    start_char=start,
                    end_char=end,
                    confidence=0.82,
                )
            )
    return candidates


def _relationship(
    chunk_id: str,
    source: ExtractedMention,
    target: ExtractedMention,
    relationship_type: str,
    evidence_text: str,
    *,
    confidence: float = 0.90,
) -> ExtractedRelationship:
    return ExtractedRelationship(
        id=_stable_id(
            _RELATIONSHIP_NAMESPACE,
            chunk_id,
            source.entity_id,
            target.entity_id,
            relationship_type,
        ),
        source_entity_id=source.entity_id,
        target_entity_id=target.entity_id,
        relationship_type=relationship_type,
        evidence_text=evidence_text,
        confidence=confidence,
    )