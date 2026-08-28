"""Search terms, taxonomy, and first-party source registry."""

from __future__ import annotations

import re

USER_AGENT = (
    "daily-agent-benchmarks-bio/1.0 "
    "(+https://github.com/Rooneyxu/daily-agent-benchmarks; research indexer)"
)
REQUEST_TIMEOUT_S = 45
REQUEST_RETRIES = 3
MAX_EVIDENCE = 8

BENCHMARK_TERMS = (
    "benchmark",
    "benchmarks",
    "benchmarking",
    "evaluation suite",
    "eval suite",
    "challenge set",
    "test set",
    "leaderboard",
    "dataset for evaluating",
)
BIO_TERMS = (
    "biology",
    "biological",
    "biomedical",
    "medicine",
    "medical",
    "clinical",
    "healthcare",
    "life science",
    "life-science",
    "wet lab",
    "laboratory",
    "genomic",
    "genomics",
    "transcriptomic",
    "spatial transcriptomics",
    "single-cell",
    "proteomic",
    "proteomics",
    "protein design",
    "drug discovery",
    "pathology",
    "microscopy",
    "biosecurity",
    "biosafety",
)
CORE_BIO_TERMS = (
    "biomedical",
    "clinical",
    "healthcare",
    "life science",
    "life-science",
    "wet lab",
    "laboratory",
    "genomic",
    "genomics",
    "transcriptomic",
    "spatial transcriptomics",
    "single-cell",
    "proteomic",
    "proteomics",
    "protein",
    "peptide",
    "gene",
    "genome",
    "molecular",
    "molecule",
    "biomolecular",
    "biophysical",
    "drug discovery",
    "drug design",
    "pharmacology",
    "pathology",
    "microscopy",
    "medical imaging",
    "medical-imaging",
    "cancer",
    "patient",
    "disease",
    "antimicrobial",
    "immunology",
    "biosecurity",
    "biosafety",
)

NEW_BENCHMARK_PATTERNS = (
    r"\b(?:we|this (?:work|paper|study)) (?:introduce|present|release|construct|build|create|develop|propose) (?:(?:a|an|the|our|new|novel|first) )?(?:(?!(?:to|for|on|using|against)\b)[a-z0-9][a-z0-9+/_-]* ){0,6}(?:benchmarks?|dataset|evaluation suite|eval suite|challenge set|test set)\b",
    r"\b(?:we|this (?:work|paper|study)) (?:introduce|present|release|construct|build|create|develop|propose) [a-z0-9][a-z0-9_-]*(?:bench|benchmark|eval|qa)\b",
    r"\b(?:we|this (?:work|paper|study)) (?:introduce|present|release|construct|build|create|develop|propose) [a-z0-9][a-z0-9_-]{1,50}, (?:a|an|the) (?:[a-z0-9][a-z0-9+/_-]* ){0,6}(?:benchmarks?|dataset|evaluation suite|eval suite|challenge set|test set)\b",
    r"\b(?:introducing|presenting|releasing|constructing|building|creating|developing) (?:(?:a|an|the|our|new|novel|first) )?(?:[a-z0-9][a-z0-9+/_-]* ){0,6}(?:benchmarks?|dataset|evaluation suite|eval suite|challenge set|test set)\b",
    r"\b(?:new|novel|first) .{0,80}\b(?:benchmark|dataset|evaluation suite|eval suite|challenge set|test set)\b",
    r"\b(?:benchmark|dataset|evaluation suite|eval suite|challenge set|test set) (?:consists|comprises|contains)\b",
)

METHODOLOGY_PATTERNS = (
    r"\b(?:automatic|automated) (?:question|item|task) generation\b",
    r"\b(?:source[- ]grounded|evidence[- ]grounded|protocol[- ]grounded) (?:question|item|task) generation\b",
    r"\b(?:automatic|automated|programmatic|synthetic) benchmark construction\b",
    r"\bbenchmark (?:construction|curation|generation) (?:strategy|framework|method(?:ology)?|pipeline|process|workflow|protocol)\b",
    r"\bbenchmark (?:quality control|quality assurance|methodology)\b",
    r"\b(?:benchmark|evaluation (?:dataset|suite)) (?:design|construction|curation|generation|validation) (?:framework|method(?:ology)?|pipeline|workflow|protocol)\b",
    r"\b(?:framework|method(?:ology)?|pipeline|workflow|protocol|strategy) (?:for|to) (?:the )?(?:(?:design|construction|curation|generation|validation|quality (?:control|assurance)) of|(?:designing|developing|constructing|creating|curating|generating|validating)) .{0,80}\b(?:benchmarks?|evaluation (?:datasets?|suites?))\b",
    r"\b(?:benchmark|evaluation dataset) quality (?:assessment|control|assurance)\b",
    r"\b(?:automatic|automated|programmatic) verifier\b",
    r"\b(?:answerability|uniqueness|evidence entailment|answer provenance|citation grounding) (?:check|checking|verification|verifier)\b",
    r"\b(?:automatic|automated|programmatic) (?:grading|scoring|rubric generation)\b|\bautomatic rubric generation\b",
    r"\bjudge calibration\b|\b(?:introduce|propose|develop|present|calibrate|validate) .{0,100}\bllm[- ]as[- ]a[- ]judge\b",
    r"\b(?:introduce|propose|develop|present) .{0,100}\b(?:automatic|automated|scalable) (?:evaluation|grading|scoring) (?:framework|method|pipeline)\b",
    r"\b(?:item response theory|irt analysis) (?:for|of|on) .{0,80}\b(?:benchmarks?|evaluation datasets?|test items?)\b|\b(?:benchmark|item|difficulty) calibration (?:framework|method|procedure|protocol|decision rule|that|which)\b",
    r"\badversarial filtering\b|\bgenerator[- ]verifier\b",
    r"\breproducible benchmarking (?:platform|framework|pipeline|workflow|infrastructure)\b",
    r"\bbenchmark reliability (?:metric|measure|framework|method)\b",
)

AUDIT_PATTERNS = (
    r"\bbenchmark audit(?:ing)?\b|\baudit of (?:[a-z0-9-]+ ){0,10}benchmarks?\b|\baudit(?:ed|s) (?:[a-z0-9-]+ ){0,10}benchmarks?\b|\bauditing (?:of )?(?:existing|established|public|released|widely used|standard|biomedical|medical|biomolecular|scientific)\s+(?:[a-z0-9-]+ ){0,8}benchmarks?\b",
    r"\bauditing [^.;]{0,100}\bcontamination [^.;]{0,100}\bbenchmarks?\b",
    r"\bbenchmark reproducibility (?:audit|study|analysis)\b|\b(?:reproducibility|replication) (?:audit|study|analysis) (?:of|on) [^.;]{0,100}\bbenchmarks?\b",
    r"\b(?:reproducibility|replication) (?:of|across) [^.;]{0,80}\bbenchmarks?\b",
    r"\b(?:audit(?:s|ed|ing)?|detect(?:s|ed|ing|ion)?|measur(?:e|es|ed|ing)|quantif(?:y|ies|ied|ying)|assess(?:es|ed|ing)?|analy[sz](?:e|es|ed|ing|is)|investigat(?:e|es|ed|ing|ion)) [^.;]{0,100}\b(?:benchmark|data) (?:contamination|leakage)\b",
    r"\b(?:benchmark|data) (?:contamination|leakage) [^.;]{0,100}\b(?:audit(?:s|ed|ing)?|detect(?:s|ed|ing|ion)?|measur(?:e|es|ed|ing)|quantif(?:y|ies|ied|ying)|assess(?:es|ed|ing)?|analy[sz](?:e|es|ed|ing|is)|investigat(?:e|es|ed|ing|ion))\b",
    r"\bbenchmarking (?:the )?(?:impact|effect) of (?:data )?(?:contamination|leakage)\b",
    r"\bbenchmark (?:reliability|validity) (?:audit|analysis|study)\b",
    r"\bwhat do .{0,100}\bbenchmarks? measure\b",
    r"\b(?:benchmark|corpus|dataset)[- ]centric diagnostic framework\b",
    r"\bdiagnostic (?:analysis|assessment|framework|study) (?:of|for) .{0,100}\bbenchmarks?\b",
    r"\b(?:harmonized|harmonised) benchmarking [^.;]{0,120}\b(?:reveal|reveals|find|finds|show|shows)\b",
    r"\brethinking (?:the |our )?(?:use of )?benchmarks?\b",
    r"\b(?:robustness|reliability|validity|generalization|generalisation|sensitivity|stability) (?:analysis|assessment|audit|study) (?:of|in|across) .{0,100}\bbenchmarks?\b",
    r"\b(?:we|this (?:work|paper|study)) stress[- ]test(?:s|ed|ing)? .{0,100}\b(?:existing|established|standard|widely used) benchmarks?\b",
    r"\b(?:cross[- ]benchmark analysis|systematic benchmark comparison)\b",
    r"\b(?:shortcut|shortcuts|near[- ]duplicates?|train[- ]test overlap|dataset overlap) (?:in|of|across) .{0,100}\bbenchmarks?\b",
    r"\b(?:compromise|threaten|undermine|distort|inflate)(?:s|d|ing)? .{0,80}\bbenchmark (?:validity|reliability|scores?|performance)\b",
)

ROUTINE_EVAL_TERMS = (
    "we evaluate our model on",
    "evaluated on existing",
    "standard benchmarks",
    "outperforms on medqa",
    "achieves state-of-the-art on",
)

TOPIC_PATTERNS: dict[str, tuple[str, ...]] = {
    "multimodal": (
        r"\bmultimodal\b|\bvision[- ]language\b",
        r"\bmicroscop(?:y|ic)\b|\bpatholog(?:y|ical)\b",
        r"\bfig(?:ure)?qa\b|\btableqa\b|\bfigure reasoning\b",
        r"\bcross[- ]panel\b|\bvisual grounding\b|\bexperimental video\b",
        r"\bcaption[- ]only\b|\bmodality ablation\b",
    ),
    "experiment_agent": (
        r"\bprotocolqa\b|\bexperimental protocols?\b|\bexperimental procedure\b",
        r"\btroubleshoot(?:ing)?\b|\berror localization\b|\bfailure diagnosis\b",
        r"\bstep (?:ordering|dependency|sequence)\b|\bparameter grounding\b",
        r"\bwet[- ]lab protocols?\b|\blaboratory workflow\b|\bclosed[- ]loop experiment",
        r"\bbiomedical agents?\b|\bbiology agents?\b|\bresearch agents?\b",
        r"\btool[- ](?:use|using)\b|\bdatabase retrieval\b",
        r"\bbioinformatics agents?\b|\bautonomous (?:science|scientist|experiment)",
        r"\bautomated laborator(?:y|ies)\b|\bmulti[- ]agent\b",
    ),
    "biosafety": (
        r"\bbiosafety\b|\bbiosecurity\b|\bbiological risk\b|\bbiorisk\b",
        r"\bdual[- ]use\b|\bhazard recognition\b|\blab safety\b",
        r"\bsafe refusal\b|\bover[- ]refusal\b|\brisk assessment\b",
        r"\bvirolog(?:y|ical)\b|\bdna synthesis screening\b",
    ),
}

TOPIC_LABELS = {
    "general_text": {"en": "Bio/medical & text", "zh": "生物医学与文本"},
    "multimodal": {"en": "Scientific multimodal", "zh": "科学多模态"},
    "experiment_agent": {"en": "Experiment & agents", "zh": "实验与 Agent"},
    "biosafety": {"en": "Biosafety & biorisk", "zh": "生物安全与风险"},
}

CONTRIBUTION_BY_PRIORITY = {
    "P1": "new_benchmark",
    "P0": "methodology",
    "P2": "audit",
}

CONTRIBUTION_LABELS = {
    "new_benchmark": {"en": "New benchmark", "zh": "新 Benchmark"},
    "methodology": {"en": "Benchmark methodology", "zh": "构建与质检方法"},
    "audit": {"en": "Benchmark audit", "zh": "Benchmark 审计"},
}

VENDOR_SOURCES: tuple[dict[str, object], ...] = (
    {
        "id": "openai",
        "name": "OpenAI",
        "indexes": (
            "https://deploymentsafety.openai.com/",
            "https://openai.com/research/",
            "https://openai.com/news/",
        ),
    },
    {
        "id": "anthropic",
        "name": "Anthropic",
        "indexes": ("https://www.anthropic.com/system-cards", "https://www.anthropic.com/news"),
    },
    {
        "id": "deepmind",
        "name": "Google DeepMind",
        "indexes": ("https://deepmind.google/research/", "https://deepmind.google/models/"),
    },
    {"id": "meta", "name": "Meta AI", "indexes": ("https://ai.meta.com/research/",)},
    {
        "id": "microsoft",
        "name": "Microsoft Research",
        "indexes": ("https://www.microsoft.com/en-us/research/",),
    },
    {"id": "xai", "name": "xAI", "indexes": ("https://x.ai/news",)},
    {
        "id": "nvidia",
        "name": "NVIDIA",
        "indexes": ("https://research.nvidia.com/", "https://blogs.nvidia.com/blog/category/deep-learning/"),
    },
    {
        "id": "aws",
        "name": "Amazon / AWS",
        "indexes": ("https://aws.amazon.com/blogs/machine-learning/",),
    },
    {"id": "mistral", "name": "Mistral AI", "indexes": ("https://mistral.ai/news",)},
    {"id": "qwen", "name": "Qwen / Alibaba", "indexes": ("https://qwenlm.github.io/",)},
    {"id": "deepseek", "name": "DeepSeek", "indexes": ("https://api-docs.deepseek.com/news/",)},
    {"id": "ai2", "name": "AI2", "indexes": ("https://allenai.org/news",)},
    {"id": "huggingface", "name": "Hugging Face", "indexes": ("https://huggingface.co/blog",)},
)

MODEL_LINK_RE = re.compile(
    r"(?:system[-_ ]?card|model[-_ ]?card|technical[-_ ]?report|model[-_ ]?release|"
    r"release[-_ ]?notes?|research|evaluation|safety|benchmark)",
    re.IGNORECASE,
)
