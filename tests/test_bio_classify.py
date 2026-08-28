from __future__ import annotations

from bio.classify import classify
from bio.models import SourceCandidate, SourceDocument


def document(title: str, abstract: str, *, kind: str = "paper", status: str = "complete") -> SourceDocument:
    candidate = SourceCandidate(
        source="test",
        source_id="1",
        kind=kind,
        title=title,
        abstract=abstract,
        links={"abs": "https://example.org/1"},
    )
    return SourceDocument(candidate=candidate, body=abstract, content_hash="abc", extraction_status=status)


def test_new_medical_knowledge_benchmark_is_included() -> None:
    result = classify(
        document(
            "ClinicQA: A New Benchmark for Medical Question Answering",
            "We introduce a benchmark for clinical knowledge and medical question answering.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P1"
    assert "text" in result.categories


def test_routine_scoring_on_existing_benchmark_is_excluded() -> None:
    result = classify(
        document(
            "A language model for clinical notes",
            "We evaluate our model on MedQA, a medical question answering benchmark, and report accuracy.",
        )
    )
    assert result.collection_status == "excluded"


def test_automated_construction_is_p0_but_priority_is_not_a_gate() -> None:
    result = classify(
        document(
            "AutoBioQA: A Benchmark Suite for Biology",
            "We introduce automated benchmark construction with automatic question generation, provenance, and an automated verifier.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P0"
    assert {"construction", "quality"}.issubset(result.categories)


def test_complete_system_card_update_is_confirmed_p2() -> None:
    result = classify(
        document(
            "Frontier Model System Card",
            "This system card reports a biology benchmark evaluation methodology, new scores, and a failure mode in biosecurity testing.",
            kind="evaluation_update",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P2"
    assert "biosafety" in result.categories


def test_incomplete_system_card_goes_to_watchlist_not_p2_bucket() -> None:
    result = classify(
        document(
            "Frontier Model System Card",
            "A biology benchmark is mentioned, but the linked PDF could not be extracted.",
            kind="evaluation_update",
            status="incomplete",
        )
    )
    assert result.collection_status == "watchlist"
    assert result.priority == "P2"
