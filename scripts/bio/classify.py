"""Deterministic, evidence-producing classifier for Bio benchmark artifacts."""

from __future__ import annotations

import re

from .config import (
    AUDIT_PATTERNS,
    BENCHMARK_TERMS,
    BIO_TERMS,
    CORE_BIO_TERMS,
    MAX_EVIDENCE,
    METHODOLOGY_PATTERNS,
    NEW_BENCHMARK_PATTERNS,
    ROUTINE_EVAL_TERMS,
    TOPIC_PATTERNS,
)
from .models import Classification, Evidence, SourceDocument


def _contains(text: str, terms: tuple[str, ...]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term in lowered]


def _contains_phrases(text: str, terms: tuple[str, ...]) -> list[str]:
    return [
        term
        for term in terms
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text, re.IGNORECASE)
    ]


def _pattern_hits(text: str, patterns: tuple[str, ...]) -> list[str]:
    hits = []
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            hits.append(match.group(0))
    return hits


def _topic_hits(text: str) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for topic, patterns in TOPIC_PATTERNS.items():
        matches = []
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                matches.append(match.group(0))
        if matches:
            hits[topic] = matches
    return hits


def _primary_topic(hits: dict[str, list[str]]) -> str:
    if not hits:
        return "general_text"
    tie_order = {"biosafety": 3, "experiment_agent": 2, "multimodal": 1}
    return max(hits, key=lambda topic: (len(hits[topic]), tie_order.get(topic, 0)))


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
    metadata_text = re.sub(r"\s+", " ", f"{title}. {candidate.abstract}").strip()
    full_text = f"{title}\n{candidate.abstract}\n{document.body}".strip()
    core_domain_hits = _contains_phrases(metadata_text, CORE_BIO_TERMS)
    domain_hits = list(dict.fromkeys([*_contains(metadata_text, BIO_TERMS), *core_domain_hits]))
    title_domain_hits = list(
        dict.fromkeys([*_contains(title, BIO_TERMS), *_contains_phrases(title, CORE_BIO_TERMS)])
    )
    named_domain_artifact = bool(
        re.search(r"\b(?:bio|med|clinic|health|life)[a-z0-9_-]*(?:bench|benchmark|eval|qa)\b", title, re.IGNORECASE)
    )
    scoped_domain_signal = bool(
        re.search(
            r"\b(?:domains?|tasks?|datasets?)\s*(?::|\(|include(?:s|d)?|including|span(?:s|ned)?|spanning)\s*[^.;]{0,100}\b(?:biology|biomedical|medicine|medical)\b",
            metadata_text,
            re.IGNORECASE,
        )
    )
    strong_domain_signal = bool(
        title_domain_hits
        or core_domain_hits
        or named_domain_artifact
        or scoped_domain_signal
        or len(set(domain_hits)) >= 2
    )
    benchmark_hits = _contains(metadata_text, BENCHMARK_TERMS)
    new_hits = _pattern_hits(metadata_text, NEW_BENCHMARK_PATTERNS)
    methodology_hits = _pattern_hits(metadata_text, METHODOLOGY_PATTERNS)
    audit_hits = _pattern_hits(metadata_text, AUDIT_PATTERNS)
    routine_hits = _contains(metadata_text, ROUTINE_EVAL_TERMS)
    topic_hits = _topic_hits(full_text)
    categories = [_primary_topic(topic_hits)]

    title_benchmark = bool(_contains(title, BENCHMARK_TERMS))
    title_artifact = bool(
        re.search(r"\b[a-z0-9][a-z0-9_-]*(?:bench|benchmark|eval|qa)\b", title, re.IGNORECASE)
        or re.search(
            r"^[^:]{2,100}:\s*(?![^:]*\b(?:survey|review|taxonomy|taxonomies|methods|applications|open challenges)\b)(?:(?:a|an|the)\s+)?(?:[a-z0-9-]+\s+){0,8}(?:benchmarks?|dataset|evaluation suite|eval suite|challenge set|test set)\b",
            title,
            re.IGNORECASE,
        )
    )
    benchmark_signal = bool(benchmark_hits) or title_artifact or bool(new_hits)

    score = 3 * len(set(domain_hits)) + 3 * len(set(benchmark_hits))
    score += 4 * int(title_artifact) + 4 * len(set(new_hits))
    score += 4 * len(set(methodology_hits)) + 4 * len(set(audit_hits)) + 2 * len(topic_hits)

    if audit_hits and benchmark_signal:
        priority = "P2"
    elif methodology_hits and benchmark_signal:
        priority = "P0"
    else:
        priority = "P1"

    if not domain_hits:
        status = "excluded"
        reason = "No explicit biological or medical domain signal."
    elif not candidate.abstract.strip():
        status = "watchlist"
        reason = "The title may be relevant, but the source did not provide an abstract for admission review."
    elif not strong_domain_signal:
        status = "watchlist"
        reason = "Only a weak or incidental biological or medical domain signal appears in the title and abstract."
    elif audit_hits and benchmark_signal:
        status = "confirmed"
        reason = "Title or abstract explicitly identifies a biomedical benchmark audit."
    elif methodology_hits and benchmark_signal:
        status = "confirmed"
        reason = "Title or abstract explicitly studies biomedical benchmark construction or quality methodology."
    elif new_hits or title_artifact:
        status = "confirmed"
        reason = "Title or abstract explicitly identifies a new biomedical benchmark, dataset, or evaluation suite."
    elif routine_hits:
        status = "excluded"
        reason = "Routine scoring on existing benchmarks without a substantive evaluation contribution."
    elif not benchmark_signal:
        status = "excluded"
        reason = "No benchmark or evaluation-artifact signal in the title or abstract."
    else:
        status = "watchlist"
        reason = "A biomedical benchmark is mentioned, but the title and abstract do not state a qualifying contribution."

    evidence_terms = []
    enrichment_terms = [term for matches in topic_hits.values() for term in matches]
    for group in (new_hits, methodology_hits, audit_hits, benchmark_hits, domain_hits, enrichment_terms):
        for term in group:
            if term not in evidence_terms:
                evidence_terms.append(term)
    source_url = candidate.links.get("html") or candidate.links.get("abs") or candidate.content_url
    evidence = _evidence(full_text, evidence_terms, source_url)
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
