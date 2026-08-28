from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import bio.update as bio_update
from bio.models import BioEntry, slug_for


def _entry(entry_id: str, source: str, kind: str = "paper") -> BioEntry:
    return BioEntry(
        id=entry_id,
        slug=slug_for(entry_id),
        kind=kind,
        title="BioBench",
        abstract="We introduce a biology benchmark.",
        authors=["A. Author"],
        source=source,
        published_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        first_seen_at="2026-01-02T00:00:00Z",
        event_at="2026-01-02T00:00:00Z",
        priority="P1",
        categories=["general_text"],
        collection_status="confirmed",
        access_status="public",
        license="",
        identifiers={},
        links={"abs": "https://example.test/biobench"},
        evidence=[
            {
                "term": "benchmark",
                "location": "Abstract",
                "excerpt": "benchmark",
                "source_url": "https://example.test/biobench",
            }
        ],
        related_benchmarks=["BioBench"],
        related_agent_url="",
        evaluation_contexts=["beneficial_capability"],
        classification_reason="new benchmark",
        match_score=10,
        extraction_status="complete",
        extraction_error="",
        content_hash="unchanged",
    )


def test_run_preserves_stored_event_time_and_archives_vendor_entries(
    monkeypatch,
    tmp_path: Path,
) -> None:
    existing = _entry("arxiv:1234.56789", "arxiv")
    vendor_update = _entry("vendor:anthropic:system-card", "vendor:anthropic", "evaluation_update")
    vendor_paper = _entry("vendor:anthropic:benchmark-paper", "vendor:anthropic")
    nonpaper = _entry("arxiv:evaluation-update", "arxiv", "evaluation_update")
    incoming = deepcopy(existing)
    incoming.first_seen_at = "2026-02-02T00:00:00Z"
    incoming.event_at = "2026-02-02T00:00:00Z"

    class FakeStore:
        last: "FakeStore | None" = None

        def __init__(self) -> None:
            self.entries = {
                row.id: deepcopy(row)
                for row in (existing, vendor_update, vendor_paper, nonpaper)
            }
            FakeStore.last = self

        @classmethod
        def configured(cls) -> bool:
            return True

        def list_entries(self) -> list[BioEntry]:
            return [deepcopy(row) for row in self.entries.values()]

        def upsert_entries(self, entries: list[BioEntry]) -> None:
            for row in entries:
                self.entries[row.id] = deepcopy(row)

        def upsert_sources(self, rows) -> None:
            return None

        def upsert_documents(self, rows) -> None:
            return None

        def upsert_benchmarks(self, entries) -> None:
            return None

        def record_run(self, row) -> None:
            return None

    adapter = SimpleNamespace(id="arxiv", name="arXiv")
    health = {
        "source": "arxiv",
        "name": "arXiv",
        "status": "success",
        "started_at": "2026-02-02T00:00:00Z",
        "finished_at": "2026-02-02T00:00:00Z",
        "discovered": 1,
        "published": 1,
        "error": "",
    }
    monkeypatch.setattr(bio_update, "SupabaseStore", FakeStore)
    monkeypatch.setattr(bio_update, "load_local_entries", lambda path: [])
    monkeypatch.setattr(bio_update, "load_seed_entries", lambda path: [])
    monkeypatch.setattr(bio_update, "build_adapters", lambda client, include_vendors: [adapter])
    monkeypatch.setattr(
        bio_update,
        "_run_adapter",
        lambda *args, **kwargs: ([], [deepcopy(incoming)], health),
    )
    monkeypatch.setattr(bio_update, "utc_now", lambda: "2026-02-02T00:00:00Z")

    payload = bio_update.run(include_vendors=False, output_dir=tmp_path)

    assert payload["total"] == 1
    assert payload["entries"][0]["id"] == existing.id
    assert payload["entries"][0]["topic"] == "general_text"
    assert payload["entries"][0]["contribution_type"] == "new_benchmark"
    assert payload["entries"][0]["event_at"] == existing.event_at
    assert FakeStore.last is not None
    assert FakeStore.last.entries[existing.id].event_at == existing.event_at
    archive = json.loads((tmp_path / "data" / "vendor-archive.json").read_text())
    assert archive["total"] == 2
    assert {row["id"] for row in archive["entries"]} == {
        vendor_update.id,
        vendor_paper.id,
    }


def test_scheduled_workflow_disables_vendor_discovery() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = (root / ".github" / "workflows" / "bio-update.yml").read_text()
    assert 'python scripts/bio_update.py --days "$LOOKBACK_DAYS" --no-vendors' in workflow


def test_stored_ambiguous_paper_moves_to_internal_review_queue() -> None:
    entry = _entry("arxiv:routine", "arxiv")
    entry.title = "Reliability on biomedical benchmarks"
    entry.abstract = "We compare clinical models on a standard medical benchmark."

    bio_update._refresh_stored_classification(entry)

    assert entry.collection_status == "watchlist"
