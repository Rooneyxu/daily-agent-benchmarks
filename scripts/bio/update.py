"""Discover, classify, persist, and export Bio & Medical benchmark artifacts."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

from .classify import classify
from .extract import fetch_document
from .export import write_snapshot
from .models import BioEntry, SourceCandidate, SourceDocument, canonical_id, slug_for, utc_now
from .sources import SourceAdapter, build_adapters
from .storage import SupabaseStore, load_local_entries, load_seed_entries, merge_entries

ROOT = Path(__file__).resolve().parents[2]
BIO_OUTPUT = ROOT / "docs" / "bio"
BIO_INDEX = BIO_OUTPUT / "data" / "index.json"
AGENT_INDEX = ROOT / "docs" / "data" / "index.json"
SEED_PATH = ROOT / "data" / "bio-seeds.json"


def _benchmark_names(text: str) -> list[str]:
    patterns = (
        r"\b[A-Z][A-Za-z0-9]*(?:[-_][A-Za-z0-9]+)*(?:Bench|Benchmark|QA|Eval)\b",
        r"\b(?:LAB-Bench|LABBench2|ProteinGym|BioMysteryBench|SpatialBench|LifeSciBench|GeneBench)\b",
    )
    names = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            name = match.group(0).strip()
            if name not in names:
                names.append(name)
    return names[:20]


def _access_status(candidate: SourceCandidate) -> str:
    explicit = str(candidate.metadata.get("access_status") or "").lower()
    if explicit in {"public", "partial", "restricted", "private", "unknown"}:
        return explicit
    license_name = str(candidate.metadata.get("license") or "")
    if license_name or candidate.metadata.get("is_open_access"):
        return "public"
    if candidate.source in {"arxiv", "biorxiv", "medrxiv", "openreview"}:
        return "public"
    return "unknown"


def _evaluation_contexts(categories: list[str]) -> list[str]:
    contexts = []
    if any(category != "biosafety" for category in categories):
        contexts.append("beneficial_capability")
    if "biosafety" in categories:
        contexts.append("biosecurity_misuse")
    return contexts


def document_to_entry(document: SourceDocument, seen_at: str) -> BioEntry | None:
    candidate = document.candidate
    result = classify(document)
    if result.collection_status == "excluded":
        return None
    entry_id = canonical_id(candidate.source, candidate.source_id, candidate.identifiers)
    source_text = f"{candidate.title}\n{candidate.abstract}\n{document.body}"
    published = candidate.published_at or seen_at
    return BioEntry(
        id=entry_id,
        slug=slug_for(entry_id),
        kind=candidate.kind,
        title=candidate.title,
        abstract=candidate.abstract,
        authors=candidate.authors,
        source=candidate.source,
        published_at=published,
        updated_at=candidate.updated_at or published,
        first_seen_at=seen_at,
        event_at=seen_at,
        priority=result.priority,
        categories=result.categories,
        collection_status=result.collection_status,
        access_status=_access_status(candidate),
        license=str(candidate.metadata.get("license") or ""),
        identifiers=candidate.identifiers,
        links=candidate.links,
        evidence=[
            {
                "term": row.term,
                "location": row.location,
                "excerpt": row.excerpt,
                "source_url": row.source_url,
            }
            for row in result.evidence
        ],
        related_benchmarks=_benchmark_names(source_text),
        related_agent_url="",
        evaluation_contexts=_evaluation_contexts(result.categories),
        classification_reason=result.reason,
        match_score=result.score,
        extraction_status=document.extraction_status,
        extraction_error=document.extraction_error,
        content_hash=document.content_hash,
    )


def _source_row(adapter: SourceAdapter, health: dict[str, Any]) -> dict[str, Any]:
    row = {
        "id": adapter.id,
        "name": adapter.name,
        "enabled": True,
        "last_error": health.get("error") or None,
        "updated_at": health.get("finished_at"),
    }
    if health.get("status") in {"success", "partial"}:
        row["last_success_at"] = health.get("finished_at")
    return row


def _run_adapter(
    adapter: SourceAdapter,
    client: httpx.Client,
    date_from: str,
    date_to: str,
    existing_ids: set[str],
    started_at: str,
    fetch_full_text: bool,
) -> tuple[list[tuple[SourceDocument, str]], list[BioEntry], dict[str, Any]]:
    documents: list[tuple[SourceDocument, str]] = []
    entries: list[BioEntry] = []
    try:
        candidates = adapter.discover(date_from, date_to)
        recent_existing_budget = 5
        for candidate in candidates:
            entry_id = canonical_id(candidate.source, candidate.source_id, candidate.identifiers)
            if candidate.kind == "evaluation_update" and entry_id in existing_ids:
                if recent_existing_budget <= 0:
                    continue
                recent_existing_budget -= 1
            if candidate.kind == "paper":
                metadata_document = SourceDocument(
                    candidate=candidate,
                    body=candidate.abstract,
                    content_hash="metadata",
                    extraction_status="metadata_only",
                )
                if classify(metadata_document).collection_status == "excluded":
                    continue
            if fetch_full_text:
                document = fetch_document(client, candidate)
            else:
                metadata_body = candidate.abstract or candidate.title
                document = SourceDocument(
                    candidate=candidate,
                    body=metadata_body,
                    content_hash=f"metadata:{entry_id}",
                    extraction_status="metadata_only",
                )
            documents.append((document, entry_id))
            entry = document_to_entry(document, utc_now())
            if entry is not None:
                entries.append(entry)
        finished_at = utc_now()
        warnings = getattr(adapter, "warnings", [])
        health = {
            "source": adapter.id,
            "name": adapter.name,
            "status": "partial" if warnings else "success",
            "started_at": started_at,
            "finished_at": finished_at,
            "discovered": len(candidates),
            "published": len(entries),
            "error": "; ".join(warnings)[:600],
        }
        return documents, entries, health
    except Exception as exc:  # noqa: BLE001 - source isolation is part of the product contract.
        health = {
            "source": adapter.id,
            "name": adapter.name,
            "status": "failed",
            "started_at": started_at,
            "finished_at": utc_now(),
            "discovered": 0,
            "published": 0,
            "error": str(exc)[:600],
        }
        return documents, entries, health


def run(
    days: int = 4,
    backfill: int | None = None,
    seed_only: bool = False,
    include_vendors: bool = True,
    source_ids: set[str] | None = None,
    fetch_full_text: bool = True,
    output_dir: Path = BIO_OUTPUT,
) -> dict[str, Any]:
    generated_at = utc_now()
    today = datetime.now(timezone.utc).date()
    lookback = backfill if backfill is not None else days
    date_from = (today - timedelta(days=lookback)).isoformat()
    date_to = today.isoformat()

    existing = [] if seed_only else load_local_entries(BIO_INDEX)
    seeds = load_seed_entries(SEED_PATH)
    base = merge_entries(existing, seeds, generated_at)
    source_health: list[dict[str, Any]] = []
    documents: list[tuple[SourceDocument, str]] = []
    incoming: list[BioEntry] = []

    transport = httpx.HTTPTransport(retries=2)
    with httpx.Client(transport=transport) as client:
        adapters = [] if seed_only else build_adapters(client, include_vendors=include_vendors)
        if source_ids:
            adapters = [adapter for adapter in adapters if adapter.id in source_ids]
        existing_ids = {entry.id for entry in base}
        for adapter in adapters:
            started_at = utc_now()
            source_docs, source_entries, health = _run_adapter(
                adapter,
                client,
                date_from,
                date_to,
                existing_ids,
                started_at,
                fetch_full_text,
            )
            documents.extend(source_docs)
            incoming.extend(source_entries)
            source_health.append(health)
            print(
                f"{adapter.id}: {health['status']} discovered={health['discovered']} published={health['published']}",
                flush=True,
            )

    if not seed_only and source_health and not any(
        row["status"] in {"success", "partial"} for row in source_health
    ):
        raise RuntimeError("All Bio/Medical sources failed; previous snapshot was preserved")

    merged = merge_entries(base, incoming, generated_at)
    store = SupabaseStore() if SupabaseStore.configured() else None
    if store is not None:
        adapters_by_id = {adapter.id: adapter for adapter in adapters}
        store.upsert_sources(
            [_source_row(adapters_by_id[row["source"]], row) for row in source_health]
        )
        store.upsert_documents(documents)
        store.upsert_entries(merge_entries(seeds, incoming, generated_at))
        store.upsert_benchmarks(merge_entries(seeds, incoming, generated_at))
        for health in source_health:
            store.record_run(
                {
                    "source_id": health["source"],
                    "started_at": health["started_at"],
                    "finished_at": health["finished_at"],
                    "status": health["status"],
                    "discovered": health["discovered"],
                    "published": health["published"],
                    "error": health["error"],
                    "details": {"date_from": date_from, "date_to": date_to},
                }
            )
        merged = merge_entries(store.list_entries(), [], generated_at)

    public_entries = [entry for entry in merged if entry.collection_status in {"confirmed", "watchlist"}]
    payload = write_snapshot(output_dir, public_entries, generated_at, source_health, AGENT_INDEX)
    print(
        f"Wrote {payload['total']} Bio/Medical entries across {len(payload['days'])} days -> {output_dir / 'data' / 'index.json'}",
        flush=True,
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Update the Bio & Medical benchmark index.")
    parser.add_argument("--days", type=int, default=4, help="Overlapping daily lookback window.")
    parser.add_argument("--backfill", type=int, default=None, help="Use a larger historical lookback window.")
    parser.add_argument("--seed-only", action="store_true", help="Export verified seed records without network discovery.")
    parser.add_argument("--no-vendors", action="store_true", help="Skip vendor model/system-card indexes.")
    parser.add_argument(
        "--source",
        action="append",
        default=[],
        help="Run only a named source adapter; repeat for multiple sources.",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Classify discovery metadata without downloading linked full text (research/backfill only).",
    )
    parser.add_argument("--output-dir", type=Path, default=BIO_OUTPUT, help="Alternate static output directory.")
    args = parser.parse_args()
    run(
        days=args.days,
        backfill=args.backfill,
        seed_only=args.seed_only,
        include_vendors=not args.no_vendors,
        source_ids=set(args.source) or None,
        fetch_full_text=not args.metadata_only,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    main()
