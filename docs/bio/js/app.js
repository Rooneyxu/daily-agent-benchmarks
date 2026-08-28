(() => {
  const PAGE_SIZE = 24;
  const state = {
    lang: localStorage.getItem("dab-lang") || ((navigator.language || "").startsWith("zh") ? "zh" : "en"),
    theme: localStorage.getItem("dab-theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"),
    exact: localStorage.getItem("bio-exact") === "1",
    topic: localStorage.getItem("bio-topic") || "all",
    contribution: localStorage.getItem("bio-contribution") || "all",
    query: "",
    shown: PAGE_SIZE,
    data: null,
    index: null,
  };

  const elements = {
    hero: document.getElementById("bio-hero"),
    feed: document.getElementById("bio-feed"),
    rail: document.getElementById("bio-rail"),
    status: document.getElementById("bio-status"),
    query: document.getElementById("bio-q"),
    exact: document.getElementById("bio-exact"),
    generated: document.getElementById("bio-generated"),
  };

  function escape(value) { return BM25.escapeHtml(value == null ? "" : String(value)); }
  function dateOf(entry) { return entry.published_at || ""; }

  function setTheme(theme) {
    state.theme = theme;
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("dab-theme", theme);
    const button = document.getElementById("bio-theme-toggle");
    button.textContent = bioT(state.lang, theme === "dark" ? "themeToLight" : "themeToDark");
  }

  function setLanguage(lang) {
    state.lang = lang;
    localStorage.setItem("dab-lang", lang);
    applyBioI18n(lang);
    document.querySelectorAll(".lang button").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.lang === lang)));
    setTheme(state.theme);
    render();
  }

  function filteredEntries() {
    return (state.data.entries || []).filter((entry) => {
      if (state.topic !== "all" && entry.topic !== state.topic) return false;
      if (state.contribution !== "all" && entry.contribution_type !== state.contribution) return false;
      return true;
    });
  }

  function filterSearchHits(hits) {
    const allowed = new Set(filteredEntries().map((entry) => entry.id));
    return hits.filter((hit) => allowed.has(hit.paper.id));
  }

  function badge(entry) {
    return `<span class="bio-contribution bio-contribution--${entry.contribution_type}">${escape(bioContributionLabel(entry.contribution_type, state.lang))}</span>`;
  }

  function priorityBadge(entry) {
    return entry.priority ? `<span class="bio-priority bio-priority--${escape(entry.priority.toLowerCase())}">${escape(entry.priority)}</span>` : "";
  }

  function resourceLinks(entry) {
    const labels = { abs: "Paper", pdf: "PDF", code: "Code", data: "Data", project: "Project", leaderboard: "Leaderboard" };
    return Object.entries(entry.links || {})
      .filter(([key, value]) => value && labels[key])
      .map(([key, value]) => `<a href="${escape(value)}" target="_blank" rel="noopener">${labels[key]}</a>`)
      .join("");
  }

  function row(entry, query = "") {
    const title = query ? BM25.highlight(entry.title, query) : escape(entry.title);
    const topicChip = `<span class="chip">${escape(bioTopicLabel(entry.topic, state.lang))}</span>`;
    const inclusionEvidence = entry.evidence?.[0]?.term || entry.classification_reason || "";
    return `<article class="row bio-row">
      <div class="row__main">
        <div class="themes">${priorityBadge(entry)}${badge(entry)}${topicChip}</div>
        <h3><a href="./p/${encodeURIComponent(entry.slug)}.html">${title}</a></h3>
        <p class="bio-row__abstract">${escape(entry.abstract)}</p>
        ${inclusionEvidence ? `<p class="bio-row__reason"><span class="bio-row__reason-label">${bioT(state.lang, "inclusionEvidence")}</span><span class="bio-row__reason-text">${escape(inclusionEvidence)}</span></p>` : ""}
        <div class="bio-row__footer">
          <div class="meta"><span>${escape(dateOf(entry).slice(0, 10))}</span><span>· ${escape(entry.source)}</span></div>
          <div class="bio-row__links">${resourceLinks(entry)}</div>
        </div>
      </div>
      <div class="row__side"><a class="row__go" href="./p/${encodeURIComponent(entry.slug)}.html">${bioT(state.lang, "details")}</a></div>
    </article>`;
  }

  function filterButtons(labelKey, dataName, current, options) {
    return `<div class="bio-filter-group"><span>${bioT(state.lang, labelKey)}</span>${options.map(([value, key]) => `<button type="button" data-${dataName}="${value}" aria-pressed="${String(current === value)}">${bioT(state.lang, key)}</button>`).join("")}</div>`;
  }

  function filters() {
    return `<div class="bio-filters">
      ${filterButtons("contribution", "contribution-filter", state.contribution, [["all", "all"], ["new_benchmark", "newBenchmark"], ["methodology", "methodology"], ["audit", "audit"]])}
    </div>`;
  }

  function renderRail() {
    const entries = state.data.entries || [];
    const topics = ["all", ...Object.keys(BIO_TOPIC_LABELS).filter((id) => id !== "all")];
    elements.rail.innerHTML = topics.map((topic) => {
      const count = topic === "all" ? entries.length : entries.filter((entry) => entry.topic === topic).length;
      return `<a href="#${topic}" data-topic="${topic}"${state.topic === topic ? ' aria-current="true"' : ""}><span>${escape(bioTopicLabel(topic, state.lang))}</span><span class="n">${count}</span></a>`;
    }).join("");
  }

  function renderHero() {
    const entries = state.data.entries || [];
    const latest = entries.map(dateOf).sort().reverse()[0]?.slice(0, 10) || "—";
    elements.hero.innerHTML = `<h1>${bioT(state.lang, "docTitle")}</h1><p>${bioT(state.lang, "heroLead")}</p><div class="hero__stats"><div><b>${entries.length}</b><span>${bioT(state.lang, "records")}</span></div><div><b>${escape(latest)}</b><span>${bioT(state.lang, "latest")}</span></div></div>`;
    elements.generated.textContent = `${bioT(state.lang, "updated")} ${escape((state.data.generated_at || "").replace("T", " ").replace("Z", " UTC"))}`;
  }

  function renderFeed() {
    let entries;
    if (state.query.trim()) {
      const hits = BM25.search(state.index, state.query.trim(), 200, { exact: state.exact });
      entries = filterSearchHits(hits).map((hit) => hit.paper);
    } else {
      entries = filteredEntries().sort((a, b) => dateOf(b).localeCompare(dateOf(a)) || a.title.localeCompare(b.title));
    }
    const shown = entries.slice(0, state.shown);
    elements.feed.innerHTML = `${filters()}${shown.length ? `<div class="rows">${shown.map((entry) => row(entry, state.query.trim())).join("")}</div>` : `<p class="status">${bioT(state.lang, "noResults")}</p>`}${state.shown < entries.length ? `<button type="button" class="more" data-more>${bioT(state.lang, "loadMore")} (${state.shown} / ${entries.length})</button>` : ""}`;
  }

  function render() {
    if (!state.data) return;
    renderHero();
    renderRail();
    renderFeed();
  }

  function updateFilter(name, value) {
    state[name] = value;
    state.shown = PAGE_SIZE;
    localStorage.setItem(`bio-${name}`, value);
    render();
  }

  function bind() {
    document.querySelectorAll(".lang button").forEach((button) => button.addEventListener("click", () => setLanguage(button.dataset.lang)));
    document.getElementById("bio-theme-toggle").addEventListener("click", () => setTheme(state.theme === "dark" ? "light" : "dark"));
    document.getElementById("bio-search-form").addEventListener("submit", (event) => event.preventDefault());
    elements.exact.addEventListener("change", () => { state.exact = elements.exact.checked; localStorage.setItem("bio-exact", state.exact ? "1" : "0"); render(); });
    let timer = 0;
    elements.query.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => { state.query = elements.query.value; state.shown = PAGE_SIZE; render(); }, 120); });
    document.addEventListener("keydown", (event) => {
      if (event.key === "/" && document.activeElement !== elements.query && event.target.tagName !== "INPUT") { event.preventDefault(); elements.query.focus(); }
      if (event.key === "Escape" && state.query) { elements.query.value = ""; state.query = ""; render(); }
    });
    elements.feed.addEventListener("click", (event) => {
      const target = event.target.closest("button");
      if (!target) return;
      if (target.hasAttribute("data-more")) { state.shown += PAGE_SIZE; renderFeed(); }
      else if (target.dataset.contributionFilter) updateFilter("contribution", target.dataset.contributionFilter);
    });
    elements.rail.addEventListener("click", (event) => {
      const link = event.target.closest("[data-topic]");
      if (link) { event.preventDefault(); updateFilter("topic", link.dataset.topic); }
    });
  }

  async function init() {
    setTheme(state.theme);
    applyBioI18n(state.lang);
    document.querySelectorAll(".lang button").forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.lang === state.lang)));
    elements.exact.checked = state.exact;
    bind();
    try {
      const response = await fetch("./data/index.json", { cache: "no-store" });
      if (!response.ok) throw new Error(String(response.status));
      state.data = await response.json();
      state.index = BM25.build(state.data.entries || []);
      elements.status.hidden = true;
      render();
    } catch (error) {
      elements.status.textContent = bioT(state.lang, "loadError");
      console.error(error);
    }
  }

  init();
})();
