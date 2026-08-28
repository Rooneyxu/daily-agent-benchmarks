"""Local merge semantics and optional Supabase persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .models import BioEntry, SourceCandidate, SourceDocument, entry_from_dict


def load_local_entries(index_path: Path) -> list[BioEntry]:
    if not index_path.exists():
        return []
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    return [entry_from_dict(row) for row in payload.get("entries", [])]


def _meaningful_signature(entry: BioEntry) -> str:
    evidence = [
        {"term": row.get("term", ""), "excerpt": row.get("excerpt", "")}
        for row in entry.evidence
    ]
    return json.dumps(
        {
            "kind": entry.kind,
            "priority": entry.priority,
            "categories": sorted(entry.categories),
            "status": entry.collection_status,
            "evidence": evidence,
            "benchmarks": sorted(entry.related_benchmarks),
            "links": entry.links,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def merge_entries(existing: list[BioEntry], incoming: list[BioEntry], seen_at: str) -> list[BioEntry]:
    by_id = {entry.id: entry for entry in existing}
    for entry in incoming:
        previous = by_id.get(entry.id)
        if previous is None:
            by_id[entry.id] = entry
            continue
        entry.first_seen_at = previous.first_seen_at or entry.first_seen_at
        entry.is_seed = previous.is_seed or entry.is_seed
        if _meaningful_signature(previous) == _meaningful_signature(entry):
            entry.event_at = previous.event_at
        elif not entry.is_seed:
            entry.event_at = seen_at
        by_id[entry.id] = entry
    rows = list(by_id.values())
    rows.sort(key=lambda entry: (entry.event_at, entry.published_at, entry.id), reverse=True)
    return rows


def load_seed_entries(path: Path) -> list[BioEntry]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [entry_from_dict(row) for row in payload.get("entries", [])]


class SupabaseStore:
    """Trusted server-side store. The secret key must never reach the site bundle."""

    def __init__(self) -> None:
        url = os.environ.get("SUPABASE_URL", "").strip()
        secret = os.environ.get("SUPABASE_SECRET_KEY", "").strip()
        if not url or not secret:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SECRET_KEY are required")
        from supabase import create_client

        self.client = create_client(url, secret)

    @classmethod
    def configured(cls) -> bool:
        return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SECRET_KEY"))

    def upsert_sources(self, rows: list[dict[str, Any]]) -> None:
        if rows:
            self.client.table("sources").upsert(rows, on_conflict="id").execute()

    def upsert_documents(self, rows: list[tuple[SourceDocument, str]]) -> None:
        documents_by_id: dict[str, dict[str, Any]] = {}
        for document, document_id in rows:
            candidate = document.candidate
            documents_by_id[document_id] = {
                "id": document_id,
                "source_id": candidate.source,
                "source_record_id": candidate.source_id,
                "kind": candidate.kind,
                "title": candidate.title,
                "abstract": candidate.abstract,
                "authors": candidate.authors,
                "published_at": candidate.published_at or None,
                "updated_at_source": candidate.updated_at or None,
                "identifiers": candidate.identifiers,
                "links": candidate.links,
                "metadata": candidate.metadata,
                "content_hash": document.content_hash,
                "extraction_status": document.extraction_status,
                "extraction_error": document.extraction_error,
            }
        payload = list(documents_by_id.values())
        for offset in range(0, len(payload), 200):
            self.client.table("documents").upsert(payload[offset : offset + 200], on_conflict="id").execute()

    def upsert_entries(self, entries: list[BioEntry]) -> None:
        payload = []
        for entry in entries:
            row = entry.to_dict()
            row["document_id"] = None if entry.is_seed else entry.id
            row["evidence"] = entry.evidence
            payload.append(row)
        for offset in range(0, len(payload), 200):
            self.client.table("entries").upsert(payload[offset : offset + 200], on_conflict="id").execute()

    def upsert_benchmarks(self, entries: list[BioEntry]) -> None:
        benchmarks: dict[str, dict[str, Any]] = {}
        links: dict[tuple[str, str], dict[str, str]] = {}
        for entry in entries:
            for name in entry.related_benchmarks:
                benchmark_id = name.lower().replace("_", "-")
                benchmarks[benchmark_id] = {
                    "id": benchmark_id,
                    "name": name,
                    "aliases": [],
                    "categories": entry.categories,
                    "access_status": entry.access_status,
                }
                links[(entry.id, benchmark_id)] = {
                    "entry_id": entry.id,
                    "benchmark_id": benchmark_id,
                }
        if benchmarks:
            self.client.table("benchmarks").upsert(list(benchmarks.values()), on_conflict="id").execute()
        if links:
            self.client.table("entry_benchmarks").upsert(
                list(links.values()),
                on_conflict="entry_id,benchmark_id",
            ).execute()

    def record_run(self, row: dict[str, Any]) -> None:
        self.client.table("source_runs").insert(row).execute()

    def list_entries(self) -> list[BioEntry]:
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            response = self.client.table("entries").select("*").range(offset, offset + 999).execute()
            batch = response.data or []
            rows.extend(batch)
            if len(batch) < 1000:
                break
            offset += len(batch)
        return [entry_from_dict(row) for row in rows]
