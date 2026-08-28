(() => {
  const base = window.BIO_BASE || "./";
  const lang = localStorage.getItem("dab-lang") || ((navigator.language || "").startsWith("zh") ? "zh" : "en");
  const theme = localStorage.getItem("dab-theme") || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  document.documentElement.dataset.theme = theme;
  applyBioI18n(lang);

  function escape(value) { return BM25.escapeHtml(value == null ? "" : String(value)); }
  function definition(label, value) { return value ? `<dt>${escape(label)}</dt><dd>${value}</dd>` : ""; }

  async function init() {
    const root = document.getElementById("main");
    try {
      const response = await fetch(`${base}data/index.json`, { cache: "no-store" });
      if (!response.ok) throw new Error(String(response.status));
      const data = await response.json();
      const entry = (data.entries || []).find((row) => row.id === window.BIO_ENTRY_ID);
      if (!entry) throw new Error("entry not found");
      document.title = entry.title;
      const topic = `<span class="chip">${escape(bioTopicLabel(entry.topic, lang))}</span>`;
      const identifiers = Object.entries(entry.identifiers || {}).map(([key, value]) => `${escape(key.toUpperCase())}: ${escape(value)}`).join(" · ");
      const contexts = (entry.evaluation_contexts || []).map((context) => bioT(lang, context === "biosecurity_misuse" ? "biosecurityMisuse" : "beneficialCapability")).join(" · ");
      const links = Object.entries(entry.links || {}).filter(([, value]) => value).map(([key, value]) => `<a href="${escape(value)}" target="_blank" rel="noopener">${escape(key)}</a>`).join("");
      const evidence = (entry.evidence || []).map((row) => `<article class="evidence-card"><div class="evidence-card__head"><strong>${escape(row.term)}</strong><span>${escape(row.location)}</span></div><p>${escape(row.excerpt)}</p>${row.source_url ? `<a class="row__go" href="${escape(row.source_url)}" target="_blank" rel="noopener">${bioT(lang, "source")}</a>` : ""}</article>`).join("");
      const agentLink = entry.related_agent_url ? `<a href="${escape(entry.related_agent_url)}">${bioT(lang, "relatedAgent")}</a>` : "";
      root.innerHTML = `<p class="crumb"><a href="${base}">${bioT(lang, "back")}</a></p><article class="paper paper--full">
        <div class="themes"><span class="bio-contribution bio-contribution--${entry.contribution_type}">${escape(bioContributionLabel(entry.contribution_type, lang))}</span>${topic}</div>
        <h1>${escape(entry.title)}</h1><div class="meta">${escape((entry.authors || []).join(", "))}</div>
        <div class="abstract"><p>${escape(entry.abstract)}</p></div>
        <dl class="bio-definition">
          ${definition(bioT(lang, "published"), escape((entry.published_at || "").slice(0, 10)))}
          ${definition(bioT(lang, "access"), escape(entry.access_status))}
          ${definition(bioT(lang, "topic"), escape(bioTopicLabel(entry.topic, lang)))}
          ${definition(bioT(lang, "contributionType"), escape(bioContributionLabel(entry.contribution_type, lang)))}
          ${definition(bioT(lang, "reason"), escape(entry.classification_reason))}
          ${definition(bioT(lang, "identifiers"), identifiers)}
          ${definition(bioT(lang, "context"), escape(contexts))}
          ${definition(bioT(lang, "extraction"), escape(entry.extraction_status))}
        </dl>
        <div class="links">${links}${agentLink}</div>
        <h2>${bioT(lang, "details")}</h2><div class="evidence-list">${evidence || `<p class="status">—</p>`}</div>
      </article>`;
    } catch (error) {
      root.innerHTML = `<p class="status">${bioT(lang, "loadError")}</p>`;
      console.error(error);
    }
  }
  init();
})();
