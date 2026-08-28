"""Deterministic, evidence-producing classifier for Bio benchmark artifacts."""

from __future__ import annotations

import re

from .config import (
    BENCHMARK_TERMS,
    BIO_TERMS,
    CATEGORY_PATTERNS,
    MAX_EVIDENCE,
    NEW_ARTIFACT_TERMS,
    ROUTINE_EVAL_TERMS,
    SUBSTANTIVE_UPDATE_TERMS,
)
from .models import Classification, Evidence, SourceDocument


def _contains(text: str, terms: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term in lowered]


def _category_hits(text: str) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for category, patterns in CATEGORY_PATTERNS.items():
        matches = []
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                matches.append(match.group(0))
        if matches:
            hits[category] = matches
    return hits


def _location_at(text: str, offset: int) -> str:
    prefix = text[:offset]
    page_matches = list(re.finditer(r"\[\[PAGE\s+(\d+)\]\]", prefix))
    if page_matches:
        return f"PDF page {page_matches[-1].group(1)}"
    section_matches = list(re.finditer(r"\[\[SECTION\s+([^\]]+)\]\]", prefix))
    if section_matches:
        return section_matches[-1].group(1).strip()[:120]
    return "Abstract / metadata"


def _evidence(text: str, terms: list[str], source_url: str) -> list[Evidence]:
    rows: list[Evidence] = []
    seen: set[tuple[str, str]] = set()
    for term in terms:
        match = re.search(re.escape(term), text, re.IGNORECASE)
        if not match:
            continue
        start = max(0, match.start() - 150)
        end = min(len(text), match.end() + 240)
        excerpt = re.sub(r"\s+", " ", text[start:end]).strip(" .")
        location = _location_at(text, match.start())
        key = (location, excerpt)
        if key in seen:
            continue
        seen.add(key)
        rows.append(Evidence(term=term, location=location, excerpt=excerpt, source_url=source_url))
        if len(rows) >= MAX_EVIDENCE:
            break
    return rows


def classify(document: SourceDocument) -> Classification:
    candidate = document.candidate
    title = candidate.title or ""
    text = f"{title}\n{candidate.abstract}\n{document.body}".strip()
    domain_hits = _contains(text, BIO_TERMS)
    benchmark_hits = _contains(text, BENCHMARK_TERMS)
    new_hits = _contains(text, NEW_ARTIFACT_TERMS)
    update_hits = _contains(text, SUBSTANTIVE_UPDATE_TERMS)
    routine_hits = _contains(text, ROUTINE_EVAL_TERMS)
    category_hits = _category_hits(text)
    categories = list(category_hits)

    title_benchmark = bool(_contains(title, BENCHMARK_TERMS)) or bool(
        re.search(r"\b[a-z0-9][a-z0-9_-]*(?:bench|benchmark|eval)\b", title, re.IGNORECASE)
    )
    source_update = candidate.kind == "evaluation_update"
    is_audit = bool(update_hits) and not bool(new_hits)

    score = 3 * len(set(domain_hits)) + 3 * len(set(benchmark_hits))
    score += 4 * int(title_benchmark) + 4 * len(set(new_hits)) + 2 * len(set(update_hits))
    score += 2 * len(categories)

    if source_update or is_audit:
        priority = "P2"
    elif any(category in categories for category in ("construction", "quality", "protocol")):
        priority = "P0"
    else:
        priority = "P1"

    if not domain_hits:
        status = "excluded"
        reason = "No explicit biological or medical domain signal."
    elif not benchmark_hits and not title_benchmark:
        status = "excluded"
        reason = "No benchmark or evaluation-artifact signal."
    elif source_update:
        if document.extraction_status != "complete" or not update_hits:
            status = "watchlist"
            reason = "Official model artifact is relevant, but full-text update evidence is incomplete."
        else:
            status = "confirmed"
            reason = "Official model artifact contains explicit biomedical evaluation evidence."
    elif new_hits or title_benchmark:
        status = "confirmed"
        reason = "Explicit biomedical benchmark contribution detected."
    elif update_hits:
        status = "confirmed"
        reason = "Substantive benchmark audit or evaluation-method update detected."
    elif routine_hits:
        status = "excluded"
        reason = "Routine scoring on existing benchmarks without a substantive evaluation contribution."
    else:
        status = "watchlist"
        reason = "Biomedical benchmark use is present, but the contribution type is not explicit."

    if not categories and status != "excluded":
        categories = ["text"]

    evidence_terms = []
    for group in (new_hits, update_hits, benchmark_hits, domain_hits):
        for term in group:
            if term not in evidence_terms:
                evidence_terms.append(term)
    source_url = candidate.links.get("html") or candidate.links.get("abs") or candidate.content_url
    evidence = _evidence(text, evidence_terms, source_url)
    if status == "confirmed" and not evidence:
        status = "watchlist"
        reason = "Relevant signals were found, but no traceable evidence window could be produced."

    return Classification(
        collection_status=status,
        priority=priority,
        categories=categories,
        reason=reason,
        score=score,
        evidence=evidence,
    )
