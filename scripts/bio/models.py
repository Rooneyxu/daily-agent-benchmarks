"""Small, serializable data contracts shared by the Bio pipeline."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import MISSING, asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stable_hash(value: str, length: int = 20) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def normalized_doi(value: str) -> str:
    doi = (value or "").strip().lower()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    return doi.removeprefix("doi:").strip()


def canonical_id(source: str, source_id: str, identifiers: dict[str, str]) -> str:
    doi = normalized_doi(identifiers.get("doi", ""))
    if doi:
        return f"doi:{doi}"
    for key in ("arxiv", "pmid", "pmcid", "openreview"):
        value = (identifiers.get(key) or "").strip()
        if value:
            return f"{key}:{value.lower()}"
    return f"{source}:{source_id or stable_hash(json.dumps(identifiers, sort_keys=True))}"


def slug_for(entry_id: str) -> str:
    readable = re.sub(r"[^a-z0-9]+", "-", entry_id.lower()).strip("-")
    readable = readable[:72].rstrip("-") or "entry"
    return f"{readable}-{stable_hash(entry_id, 10)}"


@dataclass(slots=True)
class SourceCandidate:
    source: str
    source_id: str
    kind: str
    title: str
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    published_at: str = ""
    updated_at: str = ""
    identifiers: dict[str, str] = field(default_factory=dict)
    links: dict[str, str] = field(default_factory=dict)
    content_url: str = ""
    content_type: str = "text"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceDocument:
    candidate: SourceCandidate
    body: str
    content_hash: str
    extraction_status: str = "complete"
    extraction_error: str = ""


@dataclass(slots=True)
class Evidence:
    term: str
    location: str
    excerpt: str
    source_url: str


@dataclass(slots=True)
class Classification:
    collection_status: str
    priority: str
    categories: list[str]
    reason: str
    score: int
    evidence: list[Evidence] = field(default_factory=list)


@dataclass(slots=True)
class BioEntry:
    id: str
    slug: str
    kind: str
    title: str
    abstract: str
    authors: list[str]
    source: str
    published_at: str
    updated_at: str
    first_seen_at: str
    event_at: str
    priority: str
    categories: list[str]
    collection_status: str
    access_status: str
    license: str
    identifiers: dict[str, str]
    links: dict[str, str]
    evidence: list[dict[str, str]]
    related_benchmarks: list[str]
    related_agent_url: str
    evaluation_contexts: list[str]
    classification_reason: str
    match_score: int
    extraction_status: str
    extraction_error: str
    content_hash: str
    is_seed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def entry_from_dict(row: dict[str, Any]) -> BioEntry:
    fields = BioEntry.__dataclass_fields__
    values: dict[str, Any] = {}
    for name, definition in fields.items():
        if name in row:
            values[name] = row[name]
        elif name == "evaluation_contexts":
            categories = row.get("categories", [])
            values[name] = (["beneficial_capability"] if any(category != "biosafety" for category in categories) else []) + (
                ["biosecurity_misuse"] if "biosafety" in categories else []
            )
        elif definition.default is not MISSING:
            values[name] = definition.default
        elif definition.default_factory is not MISSING:
            values[name] = definition.default_factory()
        else:
            raise ValueError(f"Bio entry is missing required field: {name}")
    return BioEntry(**values)
