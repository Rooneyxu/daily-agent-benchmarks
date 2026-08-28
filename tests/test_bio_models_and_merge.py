from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from bio.models import BioEntry, SourceCandidate, SourceDocument, canonical_id, slug_for
from bio.storage import SupabaseStore, merge_entries
from bio.update import _source_row


def entry() -> BioEntry:
    return BioEntry(
        id="arxiv:1234.56789",
        slug=slug_for("arxiv:1234.56789"),
        kind="paper",
        title="BioBench",
        abstract="A benchmark for biology.",
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
        identifiers={"arxiv": "1234.56789"},
        links={"abs": "https://arxiv.org/abs/1234.56789"},
        evidence=[{"term": "benchmark", "location": "Abstract", "excerpt": "benchmark", "source_url": ""}],
        related_benchmarks=["BioBench"],
        related_agent_url="",
        evaluation_contexts=["beneficial_capability"],
        classification_reason="new benchmark",
        match_score=10,
        extraction_status="complete",
        extraction_error="",
        content_hash="one",
    )


def test_canonical_id_prefers_doi() -> None:
    assert canonical_id("arxiv", "1234.56789", {"doi": "https://doi.org/10.1/ABC", "arxiv": "1234.56789"}) == "doi:10.1/abc"


def test_metadata_only_change_does_not_resurface_entry() -> None:
    old = entry()
    new = deepcopy(old)
    new.updated_at = "2026-02-01T00:00:00Z"
    new.content_hash = "two"
    merged = merge_entries([old], [new], "2026-02-02T00:00:00Z")
    assert merged[0].event_at == old.event_at
    assert merged[0].first_seen_at == old.first_seen_at


def test_meaningful_evidence_change_resurfaces_entry() -> None:
    old = entry()
    new = deepcopy(old)
    new.evidence.append({"term": "failure mode", "location": "Page 5", "excerpt": "new failure mode", "source_url": ""})
    merged = merge_entries([old], [new], "2026-02-02T00:00:00Z")
    assert merged[0].event_at == "2026-02-02T00:00:00Z"


def test_failed_source_does_not_clear_last_success_timestamp() -> None:
    adapter = SimpleNamespace(id="arxiv", name="arXiv")
    row = _source_row(
        adapter,
        {
            "status": "failed",
            "finished_at": "2026-02-02T00:00:00Z",
            "error": "temporary failure",
        },
    )
    assert "last_success_at" not in row
    assert row["last_error"] == "temporary failure"


def test_document_upsert_deduplicates_canonical_ids_within_batch() -> None:
    captured: list[dict[str, object]] = []

    class Query:
        def upsert(self, rows: list[dict[str, object]], on_conflict: str) -> "Query":
            assert on_conflict == "id"
            captured.extend(rows)
            return self

        def execute(self) -> None:
            return None

    class Client:
        def table(self, name: str) -> Query:
            assert name == "documents"
            return Query()

    first = SourceDocument(
        SourceCandidate(source="arxiv", source_id="1234.5678", kind="paper", title="BioBench"),
        body="one",
        content_hash="one",
    )
    second = SourceDocument(
        SourceCandidate(source="europepmc", source_id="123456", kind="paper", title="BioBench"),
        body="two",
        content_hash="two",
    )
    store = object.__new__(SupabaseStore)
    store.client = Client()
    store.upsert_documents([(first, "doi:10.1/biobench"), (second, "doi:10.1/biobench")])

    assert len(captured) == 1
    assert captured[0]["source_id"] == "europepmc"


def test_benchmark_links_deduplicate_normalized_names() -> None:
    captured: dict[str, list[dict[str, object]]] = {"benchmarks": [], "entry_benchmarks": []}

    class Query:
        def __init__(self, table_name: str) -> None:
            self.table_name = table_name

        def upsert(self, rows: list[dict[str, object]], on_conflict: str) -> "Query":
            captured[self.table_name].extend(rows)
            return self

        def execute(self) -> None:
            return None

    class Client:
        def table(self, name: str) -> Query:
            return Query(name)

    row = entry()
    row.related_benchmarks = ["BioBench", "biobench"]
    store = object.__new__(SupabaseStore)
    store.client = Client()
    store.upsert_benchmarks([row])

    assert len(captured["benchmarks"]) == 1
    assert len(captured["entry_benchmarks"]) == 1
