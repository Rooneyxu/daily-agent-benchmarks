const BIO_STRINGS = {
  en: {
    title: "Bio & Medical",
    kicker: "Daily index",
    docTitle: "Bio & Medical Benchmarks",
    searchLabel: "Search benchmarks",
    searchPlaceholder: "Search titles, abstracts, evidence…",
    exactMatch: "Exact / cover match",
    githubAria: "Open the GitHub repository",
    themeToggle: "Toggle color theme",
    themeToLight: "Light",
    themeToDark: "Dark",
    heroLead: "New biology and medical benchmarks, plus papers on automated construction, question generation, evaluation, quality control, and audits, checked daily.",
    records: "records",
    latest: "latest publication",
    updated: "Index generated",
    all: "All",
    contribution: "Contribution",
    newBenchmark: "New benchmark",
    methodology: "Construction, generation & QC",
    audit: "Audit",
    paper: "Papers",
    update: "Evaluation updates",
    loadMore: "Load more",
    noResults: "No matching records.",
    loadError: "Could not load the Bio & Medical index.",
    details: "Evidence",
    inclusionEvidence: "Included for",
    source: "Source",
    back: "All Bio & Medical benchmarks",
    access: "Access",
    reason: "Why included",
    published: "Published",
    topic: "Topic",
    contributionType: "Contribution",
    identifiers: "Identifiers",
    relatedAgent: "Also indexed under Agent Benchmarks",
    context: "Evaluation context",
    beneficialCapability: "Beneficial life-science capability",
    biosecurityMisuse: "Biosecurity / misuse evaluation",
    extraction: "Extraction",
    footer: "Public inclusion is decided from titles and abstracts. Full text only enriches topics and evidence.",
  },
  zh: {
    title: "生物与医学",
    kicker: "每日索引",
    docTitle: "生物与医学 Benchmark",
    searchLabel: "搜索 Benchmark",
    searchPlaceholder: "搜索标题、摘要、证据…",
    exactMatch: "精确 / 覆盖匹配",
    githubAria: "打开 GitHub 仓库",
    themeToggle: "切换配色",
    themeToLight: "浅色",
    themeToDark: "深色",
    heroLead: "每日收集生物与医学新 Benchmark，以及研究自动构建、自动出题、自动化评测、质检和审计的论文。",
    records: "条记录",
    latest: "最新发布日期",
    updated: "索引生成时间",
    all: "全部",
    contribution: "贡献类型",
    newBenchmark: "新 Benchmark",
    methodology: "构建 / 出题 / 质检",
    audit: "审计",
    paper: "论文",
    update: "评测更新",
    loadMore: "加载更多",
    noResults: "没有匹配的记录。",
    loadError: "无法加载生物与医学索引。",
    details: "查看证据",
    inclusionEvidence: "纳入依据",
    source: "来源",
    back: "全部生物与医学 Benchmark",
    access: "公开性",
    reason: "纳入理由",
    published: "发布日期",
    topic: "主题",
    contributionType: "贡献类型",
    identifiers: "标识符",
    relatedAgent: "同时收录于 Agent Benchmarks",
    context: "评测语境",
    beneficialCapability: "有益生命科学能力",
    biosecurityMisuse: "生物安全 / 滥用风险评测",
    extraction: "全文解析",
    footer: "是否公开收录只由标题和摘要决定；全文仅用于补充主题与证据。",
  },
};

const BIO_TOPIC_LABELS = {
  all: { en: "All topics", zh: "全部主题" },
  general_text: { en: "Bio/medical & text", zh: "生物医学与文本" },
  multimodal: { en: "Scientific multimodal", zh: "科学多模态" },
  experiment_agent: { en: "Experiment & agents", zh: "实验与 Agent" },
  biosafety: { en: "Biosafety & biorisk", zh: "生物安全与风险" },
};

const BIO_CONTRIBUTION_LABELS = {
  new_benchmark: { en: "New benchmark", zh: "新 Benchmark" },
  methodology: { en: "Automated construction, generation & evaluation", zh: "自动构建、出题与评测质检" },
  audit: { en: "Benchmark audit", zh: "Benchmark 审计" },
};

const SYNONYMS = {
  生物: ["biology", "biological", "biomedical"],
  医学: ["medical", "medicine", "clinical"],
  基准: ["benchmark", "benchmarks"],
  评测: ["evaluation", "benchmark", "eval", "grader", "verifier", "scoring", "judge"],
  实验: ["experiment", "laboratory", "wet-lab"],
  协议: ["protocol"],
  故障: ["troubleshooting", "failure", "error"],
  多模态: ["multimodal", "vision", "figure"],
  智能体: ["agent", "agentic"],
  安全: ["biosafety", "biosecurity", "risk"],
  出题: ["question generation", "construction", "synthetic"],
  自动化评测: ["automated evaluation", "automatic evaluation", "grader", "verifier", "scoring", "judge"],
  质检: ["quality", "verifier", "validation", "grader", "rubric", "judge calibration"],
};

function bioT(lang, key) {
  return (BIO_STRINGS[lang] || BIO_STRINGS.en)[key] || BIO_STRINGS.en[key] || key;
}

function bioTopicLabel(id, lang) {
  const row = BIO_TOPIC_LABELS[id] || { en: id, zh: id };
  return row[lang === "zh" ? "zh" : "en"];
}

function bioContributionLabel(id, lang) {
  const row = BIO_CONTRIBUTION_LABELS[id] || { en: id, zh: id };
  return row[lang === "zh" ? "zh" : "en"];
}

function applyBioI18n(lang) {
  document.documentElement.lang = lang === "zh" ? "zh-Hans" : "en";
  document.title = bioT(lang, "docTitle");
  document.querySelectorAll("[data-i18n]").forEach((element) => {
    element.textContent = bioT(lang, element.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((element) => {
    element.placeholder = bioT(lang, element.dataset.i18nPlaceholder);
  });
  document.querySelectorAll("[data-i18n-aria]").forEach((element) => {
    element.setAttribute("aria-label", bioT(lang, element.dataset.i18nAria));
  });
}
