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

NEW_ARTIFACT_TERMS = (
    "we introduce",
    "we present",
    "we propose",
    "we release",
    "we construct",
    "we build",
    "introducing",
    "new benchmark",
    "benchmark consists",
    "benchmark comprises",
    "evaluation framework",
    "benchmark suite",
)

SUBSTANTIVE_UPDATE_TERMS = (
    "benchmark audit",
    "audit of",
    "reproducibility",
    "replication study",
    "data contamination",
    "benchmark contamination",
    "benchmark leakage",
    "evaluation methodology",
    "failure mode",
    "grading rubric",
    "llm-as-a-judge",
    "judge calibration",
    "inter-rater",
    "addendum",
    "system card",
    "model card",
)

ROUTINE_EVAL_TERMS = (
    "we evaluate our model on",
    "evaluated on existing",
    "standard benchmarks",
    "outperforms on medqa",
    "achieves state-of-the-art on",
)

CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "text": (
        r"\bliterature (?:understanding|question answering|reasoning)\b",
        r"\bscientific reasoning\b",
        r"\bmedical question answering\b",
        r"\bmechanis(?:m|tic) reasoning\b",
        r"\bresearch design\b",
        r"\bevidence citation\b",
        r"\bmedqa\b|\bpubmedqa\b|\bbioasq\b",
    ),
    "multimodal": (
        r"\bmultimodal\b|\bvision[- ]language\b",
        r"\bmicroscop(?:y|ic)\b|\bpatholog(?:y|ical)\b",
        r"\bfig(?:ure)?qa\b|\btableqa\b|\bfigure reasoning\b",
        r"\bcross[- ]panel\b|\bvisual grounding\b|\bexperimental video\b",
        r"\bcaption[- ]only\b|\bmodality ablation\b",
    ),
    "protocol": (
        r"\bprotocol(?:qa|s)?\b|\bexperimental procedure\b",
        r"\btroubleshoot(?:ing)?\b|\berror localization\b|\bfailure diagnosis\b",
        r"\bstep (?:ordering|dependency|sequence)\b|\bparameter grounding\b",
        r"\bwet[- ]lab\b|\blaboratory workflow\b|\bclosed[- ]loop experiment",
    ),
    "agent": (
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
    "construction": (
        r"\bautomatic question generation\b|\bautomated benchmark construction\b",
        r"\bsynthetic evaluation data\b|\bsource[- ]grounded qa\b",
        r"\bquestion mining\b|\bexam extraction\b|\bweak supervision\b",
        r"\bprogrammatic generation\b|\bparameter perturbation\b",
        r"\bcounterfactual generation\b|\bdistractor generation\b",
        r"\badversarial filtering\b|\bgenerator[- ]verifier\b|\bself[- ]refine\b",
        r"\bjats\b|\bsupplementary material\b|\bfigure[- ]to[- ]qa\b",
    ),
    "quality": (
        r"\banswerability\b|\buniqueness\b|\bevidence entailment\b",
        r"\bprovenance\b|\btraceab(?:le|ility)\b|\bunit validation\b",
        r"\bparaphrase consistency\b|\brepeated sampling\b",
        r"\bshortcut\b|\bleakage\b|\bnear[- ]duplicate\b|\bcontamination\b",
        r"\bitem response theory\b|\birt\b|\bdiscrimination index\b",
        r"\bllm[- ]as[- ]a[- ]judge\b|\bjudge calibration\b|\brubric generation\b",
        r"\bconfidence estimation\b|\bactive sampling\b|\brisk[- ]stratified review\b",
        r"\bautomated verifier\b|\bprogrammatic verifier\b",
    ),
}

CATEGORY_LABELS = {
    "text": {"en": "Bio/medical text", "zh": "生物医学文本"},
    "multimodal": {"en": "Scientific multimodal", "zh": "科学多模态"},
    "protocol": {"en": "Experiment & protocol", "zh": "实验与 Protocol"},
    "agent": {"en": "Research agents", "zh": "科研 Agent"},
    "biosafety": {"en": "Biosafety & biorisk", "zh": "生物安全与风险"},
    "construction": {"en": "Automated construction", "zh": "自动化出题与构建"},
    "quality": {"en": "Automated quality", "zh": "自动化质检与评测"},
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
