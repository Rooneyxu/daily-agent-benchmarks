from __future__ import annotations

from bio.classify import classify
from bio.models import SourceCandidate, SourceDocument


def document(title: str, abstract: str, *, body: str = "", status: str = "complete") -> SourceDocument:
    candidate = SourceCandidate(
        source="test",
        source_id="1",
        kind="paper",
        title=title,
        abstract=abstract,
        links={"abs": "https://example.org/1"},
    )
    return SourceDocument(candidate=candidate, body=body or abstract, content_hash="abc", extraction_status=status)


def test_new_medical_knowledge_benchmark_is_included() -> None:
    result = classify(
        document(
            "ClinicQA: A New Benchmark for Medical Question Answering",
            "We introduce a benchmark for clinical knowledge and medical question answering.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P1"
    assert result.categories == ["general_text"]


def test_routine_scoring_on_existing_benchmark_is_excluded() -> None:
    result = classify(
        document(
            "A language model for clinical notes",
            "We evaluate our model on MedQA, a medical question answering benchmark, and report accuracy.",
        )
    )
    assert result.collection_status == "excluded"


def test_automated_construction_is_benchmark_methodology() -> None:
    result = classify(
        document(
            "AutoBioQA: A Benchmark Suite for Biology",
            "We introduce automated benchmark construction with automatic question generation, provenance, and an automated verifier.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P0"
    assert result.categories == ["general_text"]


def test_benchmark_audit_is_confirmed() -> None:
    result = classify(
        document(
            "Auditing contamination in biomedical benchmarks",
            "We audit data contamination and benchmark leakage in medical question answering benchmarks.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P2"
    assert result.categories == ["general_text"]


def test_full_text_cannot_promote_a_routine_evaluation() -> None:
    result = classify(
        document(
            "A language model for clinical notes",
            "We evaluate our model on an existing biomedical benchmark and report accuracy.",
            body="In the appendix, we present a new benchmark and an automated verifier.",
        )
    )
    assert result.collection_status != "confirmed"


def test_full_text_can_refine_topic_after_metadata_admission() -> None:
    result = classify(
        document(
            "CellScope: A new biomedical benchmark",
            "We introduce a new benchmark for biomedical research evaluation.",
            body="The tasks require microscopy images, pathology figures, and visual grounding.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.categories == ["multimodal"]


def test_benchmark_mention_without_explicit_contribution_stays_internal() -> None:
    result = classify(
        document(
            "Reliability on biomedical benchmarks",
            "We compare several clinical models on a standard medical benchmark.",
        )
    )
    assert result.collection_status == "watchlist"


def test_named_benchmark_in_title_is_explicit_admission_evidence() -> None:
    result = classify(
        document(
            "ProteinGym: Large-Scale Benchmarks for Protein Fitness Prediction",
            "ProteinGym provides experimentally grounded biological tasks and datasets.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P1"


def test_review_listing_benchmarks_is_not_a_new_benchmark() -> None:
    result = classify(
        document(
            "Multitask learning in predictive toxicology: methods, benchmarks, and applications",
            "This biomedical review examines benchmark datasets and clinical validation frameworks.",
        )
    )
    assert result.collection_status == "watchlist"


def test_framework_that_uses_benchmark_as_a_verb_is_not_promoted() -> None:
    result = classify(
        document(
            "A multi-scale framework for skin aging",
            "In this biomedical review, we introduce a hierarchical framework to systematically benchmark experimental models.",
        )
    )
    assert result.collection_status == "watchlist"


def test_internal_data_auditing_does_not_turn_a_new_suite_into_an_audit() -> None:
    result = classify(
        document(
            "RoboSurg-VQA: A Multimodal Benchmark for Surgical Question Answering",
            "We present RoboSurg-VQA, a biomedical benchmark built from public datasets with manual auditing to improve label consistency.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P1"
