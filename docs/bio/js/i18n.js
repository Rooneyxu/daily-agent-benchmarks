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
    heroLead: "New biology, medicine, life-science, protocol, agent, and biosafety benchmarks — plus substantive evaluation updates.",
    records: "records",
    confirmed: "main catalog",
    latest: "latest event",
    updated: "Index generated",
    all: "All",
    status: "Catalog",
    main: "Main",
    watchlist: "Watchlist",
    priority: "Priority",
    type: "Type",
    paper: "Papers",
    update: "Evaluation updates",
    loadMore: "Load more",
    noResults: "No matching records.",
    loadError: "Could not load the Bio & Medical index.",
    details: "Evidence",
    source: "Source",
    back: "All Bio & Medical benchmarks",
    access: "Access",
    reason: "Why included",
    published: "Published",
    firstSeen: "First seen",
    categories: "Categories",
    identifiers: "Identifiers",
    relatedAgent: "Also indexed under Agent Benchmarks",
    context: "Evaluation context",
    beneficialCapability: "Beneficial life-science capability",
    biosecurityMisuse: "Biosecurity / misuse evaluation",
    extraction: "Extraction",
    watchNotice: "This item is in the Watchlist because its relevance or full-text evidence is incomplete.",
    footer: "Sources are checked daily. Priority labels help navigation but never decide inclusion.",
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
    heroLead: "每日收集生物、医学、生命科学、实验 Protocol、科研 Agent 与生物安全 Benchmark，以及有实质内容的评测更新。",
    records: "条记录",
    confirmed: "条正式收录",
    latest: "最近事件",
    updated: "索引生成时间",
    all: "全部",
    status: "目录",
    main: "正式库",
    watchlist: "观察区",
    priority: "标记",
    type: "类型",
    paper: "论文",
    update: "评测更新",
    loadMore: "加载更多",
    noResults: "没有匹配的记录。",
    loadError: "无法加载生物与医学索引。",
    details: "查看证据",
    source: "来源",
    back: "全部生物与医学 Benchmark",
    access: "公开性",
    reason: "纳入理由",
    published: "发布日期",
    firstSeen: "首次发现",
    categories: "类别",
    identifiers: "标识符",
    relatedAgent: "同时收录于 Agent Benchmarks",
    context: "评测语境",
    beneficialCapability: "有益生命科学能力",
    biosecurityMisuse: "生物安全 / 滥用风险评测",
    extraction: "全文解析",
    watchNotice: "这条记录位于观察区，因为相关性或全文证据仍不完整。",
    footer: "系统每日巡检来源；P0/P1/P2 只用于浏览标记，不决定是否收录。",
  },
};

const BIO_CATEGORY_LABELS = {
  all: { en: "All categories", zh: "全部类别" },
  text: { en: "Bio/medical text", zh: "生物医学文本" },
  multimodal: { en: "Scientific multimodal", zh: "科学多模态" },
  protocol: { en: "Experiment & protocol", zh: "实验与 Protocol" },
  agent: { en: "Research agents", zh: "科研 Agent" },
  biosafety: { en: "Biosafety & biorisk", zh: "生物安全与风险" },
  construction: { en: "Automated construction", zh: "自动化出题与构建" },
  quality: { en: "Automated quality", zh: "自动化质检与评测" },
};

const SYNONYMS = {
  生物: ["biology", "biological", "biomedical"],
  医学: ["medical", "medicine", "clinical"],
  基准: ["benchmark", "benchmarks"],
  评测: ["evaluation", "benchmark", "eval"],
  实验: ["experiment", "laboratory", "wet-lab"],
  协议: ["protocol"],
  故障: ["troubleshooting", "failure", "error"],
  多模态: ["multimodal", "vision", "figure"],
  智能体: ["agent", "agentic"],
  安全: ["biosafety", "biosecurity", "risk"],
  出题: ["question generation", "construction", "synthetic"],
  质检: ["quality", "verifier", "validation"],
};

function bioT(lang, key) {
  return (BIO_STRINGS[lang] || BIO_STRINGS.en)[key] || BIO_STRINGS.en[key] || key;
}

function bioCategoryLabel(id, lang) {
  const row = BIO_CATEGORY_LABELS[id] || { en: id, zh: id };
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
