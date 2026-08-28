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


def test_benchmark_curation_framework_is_methodology() -> None:
    result = classify(
        document(
            "A framework for biomedical benchmark curation",
            "We study a pipeline for the curation of evaluation datasets with provenance and answerability checks.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P0"


def test_reproducible_benchmarking_platform_is_methodology() -> None:
    result = classify(
        document(
            "Flower Hub: A Reproducible Benchmarking Platform for Federated Learning",
            "The platform supports medical-imaging evaluation through versioned benchmark applications.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P0"


def test_corpus_centric_benchmark_diagnostics_is_audit() -> None:
    result = classify(
        document(
            "What Do Biomedical NER and Entity Linking Benchmarks Measure?",
            "We present a corpus-centric diagnostic framework for benchmark-relevant properties and train-test overlap.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P2"


def test_auditing_widely_used_biomolecular_benchmarks_is_audit() -> None:
    result = classify(
        document(
            "Auditing widely used biomolecular benchmarks reveals systematic data inconsistencies",
            "We analyze protein benchmark datasets and quantify label conflicts and structural leakage.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P2"


def test_harmonised_benchmarking_with_findings_is_audit() -> None:
    result = classify(
        document(
            "Harmonised benchmarking of foundation models for spatial transcriptomics reveals context-dependent generalisation",
            "The biomedical benchmark shows that rankings shift with modality, preprocessing, and domain shift.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P2"


def test_plain_model_robustness_is_not_a_benchmark_audit() -> None:
    result = classify(
        document(
            "Robustness validation of a clinical prediction model",
            "We validate a medical model across three hospitals and report calibration and sensitivity.",
        )
    )
    assert result.collection_status == "excluded"


def test_new_diagnostic_benchmark_is_not_mislabeled_as_an_audit() -> None:
    result = classify(
        document(
            "DDX-TRACE: A Benchmark for Medical Diagnostic Trajectories",
            "We introduce a benchmark for evaluating diagnostic reasoning in clinical cases.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P1"


def test_new_stress_testing_benchmark_is_not_mislabeled_as_an_audit() -> None:
    result = classify(
        document(
            "SafeMedBench: A Benchmark for Medical Safety Alignment",
            "We present a benchmark for stress testing language models on high-risk medical queries.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P1"


def test_new_contamination_free_benchmark_is_not_mislabeled_as_an_audit() -> None:
    result = classify(
        document(
            "LiveProteinBench: A Contamination-Free Benchmark for Protein Science",
            "Existing datasets risk data contamination, so we introduce a new biological benchmark with a future-only test set.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P1"


def test_using_an_llm_judge_does_not_make_a_paper_methodology() -> None:
    result = classify(
        document(
            "Benchmarking LLM recommendations for personalized health interventions",
            "We compare medical model responses using an LLM-as-a-Judge and a clinician-validated scoring rubric.",
        )
    )
    assert result.collection_status == "watchlist"


def test_proposing_automated_evaluation_is_methodology() -> None:
    result = classify(
        document(
            "Automating expert-level medical reasoning evaluation",
            "We introduce MedThink-Bench and propose a scalable evaluation framework with an automated verifier.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P0"


def test_automated_grader_is_benchmark_methodology() -> None:
    result = classify(
        document(
            "BioGrade-Bench: Evaluating Open Scientific Reasoning",
            "We introduce a biomedical benchmark with an LLM-based grader calibrated against expert rubrics.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P0"


def test_synthetic_evaluation_data_is_benchmark_methodology() -> None:
    result = classify(
        document(
            "GeneSynth-Bench: Controlled Genomics Evaluation",
            "We introduce a genomics benchmark and generate synthetic evaluation data with provenance checks.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P0"


def test_benchmark_for_an_auditing_task_is_still_a_new_benchmark() -> None:
    result = classify(
        document(
            "PhysDox: A Physical Feasibility Auditing Benchmark for Biomedical Protocols",
            "We introduce a benchmark for detecting infeasible physiological sensing procedures.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P1"


def test_benchmark_named_for_a_response_audit_is_not_an_audit_of_a_benchmark() -> None:
    result = classify(
        document(
            "MIRA: A Bilingual Benchmark for Medical Information Response Audit",
            "We introduce Medical Information Response Audit, a controlled clinical benchmark for evaluating model responses.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P1"


def test_systematic_model_comparison_is_not_a_benchmark_audit() -> None:
    result = classify(
        document(
            "A molecular structure prediction system",
            "Systematic benchmarking reveals strong performance on a biological benchmark dataset.",
        )
    )
    assert result.collection_status == "watchlist"


def test_incidental_medical_domain_mention_stays_internal() -> None:
    result = classify(
        document(
            "Benchmarking Speech-to-Speech Translation Models",
            "We introduce a reproducible benchmark and validate it across podcasts, dubbing, and medical domains.",
        )
    )
    assert result.collection_status == "watchlist"


def test_incidental_biological_word_stays_internal() -> None:
    result = classify(
        document(
            "A Synthetic Underwater Image Enhancement Benchmark",
            "The renderer uses biologically resolved absorption to construct an underwater benchmark dataset.",
        )
    )
    assert result.collection_status == "watchlist"


def test_cancer_biology_case_study_is_a_strong_domain_signal() -> None:
    result = classify(
        document(
            "Automated MCQA Benchmarking at Scale",
            "We propose automated benchmark construction from 22,000 papers in radiation and cancer biology.",
        )
    )
    assert result.collection_status == "confirmed"
    assert result.priority == "P0"


def test_missing_abstract_stays_internal() -> None:
    result = classify(document("Audit of Benchmark Contamination in Medical VLM Evaluation", ""))
    assert result.collection_status == "watchlist"


def test_biobench_name_is_a_strong_domain_signal() -> None:
    result = classify(
        document(
            "BioBench",
            "We introduce a benchmark for biology.",
        )
    )
    assert result.collection_status == "confirmed"


def test_biology_as_an_explicit_multidomain_task_is_included() -> None:
    result = classify(
        document(
            "A Capability-Oriented Benchmark for AI Scientists",
            "We introduce a benchmark across five domains: Biology, Chemistry, Environment, Geography, and Physics.",
        )
    )
    assert result.collection_status == "confirmed"


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
