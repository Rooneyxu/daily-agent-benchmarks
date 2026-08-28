from __future__ import annotations

import json
from pathlib import Path

from bio.export import validate_payload, write_snapshot
from bio.models import BioEntry, slug_for


def sample_entry() -> BioEntry:
    entry_id = "arxiv:2601.00001"
    return BioEntry(
        id=entry_id,
        slug=slug_for(entry_id),
        kind="paper",
        title="BioBench: A New Benchmark for Biology",
        abstract="We introduce a benchmark.",
        authors=["A. Author"],
        source="arxiv",
        published_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        first_seen_at="2026-01-02T00:00:00Z",
        event_at="2026-01-02T00:00:00Z",
        priority="P1",
        categories=["text"],
        collection_status="confirmed",
        access_status="public",
        license="",
        identifiers={"arxiv": "2601.00001"},
        links={"abs": "https://arxiv.org/abs/2601.00001"},
        evidence=[{"term": "benchmark", "location": "Abstract", "excerpt": "benchmark", "source_url": ""}],
        related_benchmarks=["BioBench"],
        related_agent_url="",
        evaluation_contexts=["beneficial_capability"],
        classification_reason="Explicit biomedical benchmark contribution detected.",
        match_score=20,
        extraction_status="complete",
        extraction_error="",
        content_hash="abc",
    )


def test_static_snapshot_contains_index_meta_day_and_page(tmp_path: Path) -> None:
    payload = write_snapshot(
        tmp_path,
        [sample_entry()],
        "2026-01-03T00:00:00Z",
        [{"source": "arxiv", "status": "success"}],
        tmp_path / "missing-agent-index.json",
    )
    validate_payload(payload)
    assert json.loads((tmp_path / "data" / "index.json").read_text())["total"] == 1
    assert (tmp_path / "data" / "meta.json").exists()
    assert (tmp_path / "data" / "days" / "2026-01-02.json").exists()
    assert (tmp_path / "p" / f"{sample_entry().slug}.html").exists()


def test_committed_seed_catalog_has_sixty_confirmed_records() -> None:
    root = Path(__file__).resolve().parents[1]
    payload = json.loads((root / "data" / "bio-seeds.json").read_text())
    assert len(payload["entries"]) == 60
    assert all(row["collection_status"] == "confirmed" for row in payload["entries"])
    assert {row["priority"] for row in payload["entries"]} == {"P0", "P1", "P2"}
    assert len({category for row in payload["entries"] for category in row["categories"]}) == 7
