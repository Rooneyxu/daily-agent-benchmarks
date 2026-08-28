/**
 * Fielded BM25 plus cover / exact-match ranking.
 * Exact title and phrase hits are stacked above ordinary BM25.
 */
const BM25 = (() => {
  const K1 = 1.5;
  const B = 0.75;
  const STOP = new Set([
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "are",
    "was",
    "were",
    "been",
    "being",
    "have",
    "has",
    "had",
    "not",
    "but",
    "can",
    "our",
    "their",
    "its",
    "into",
    "onto",
    "over",
    "under",
    "than",
    "then",
    "also",
    "using",
    "used",
    "based",
    "via",
    "we",
    "to",
    "of",
    "in",
    "on",
    "a",
    "an",
    "is",
    "as",
    "by",
    "or",
    "the",
    "的",
    "了",
    "在",
    "是",
    "和",
    "与",
    "及",
    "对",
    "中",
  ]);

  function tokenize(text) {
    const src = String(text || "").toLowerCase();
    const tokens = [];
    const latin = src.match(/[a-z0-9][a-z0-9+._-]{1,}/g) || [];
    for (const raw of latin) {
      const tok = raw.replace(/^[._-]+|[._-]+$/g, "");
      if (tok.length >= 2 && !STOP.has(tok)) tokens.push(tok);
      if (tok.length > 4 && tok.endsWith("s") && !tok.endsWith("ss")) {
        const stem = tok.slice(0, -1);
        if (!STOP.has(stem)) tokens.push(stem);
      }
    }
    const cjkRuns = src.match(/[\u3400-\u9fff]{1,}/g) || [];
    for (const run of cjkRuns) {
      for (const ch of run) {
        if (!STOP.has(ch)) tokens.push(ch);
      }
      for (let i = 0; i < run.length - 1; i += 1) tokens.push(run.slice(i, i + 2));
    }
    return tokens;
  }

  function expandQuery(q) {
    const extra = [];
    for (const [zh, en] of Object.entries(SYNONYMS)) {
      if (q.includes(zh)) extra.push(...en);
    }
    return `${q} ${extra.join(" ")}`.trim();
  }

  function normalize(text) {
    return String(text || "")
      .toLowerCase()
      .replace(/[^a-z0-9\u3400-\u9fff]+/g, " ")
      .trim();
  }

  function tfMap(tokens) {
    const tf = new Map();
    for (const tok of tokens) tf.set(tok, (tf.get(tok) || 0) + 1);
    return tf;
  }

  function build(papers) {
    const docs = papers.map((paper) => {
      const title = tokenize(`${paper.title} ${(paper.tags || []).join(" ")}`);
      const body = tokenize(
        `${paper.abstract} ${(paper.authors || []).join(" ")} ${(paper.categories || []).join(" ")} ${paper.topic || ""} ${paper.contribution_type || ""}`
      );
      return {
        id: paper.id,
        paper,
        titleTf: tfMap(title),
        bodyTf: tfMap(body),
        titleLen: title.length || 1,
        bodyLen: body.length || 1,
        titleNorm: normalize(paper.title),
        blobNorm: normalize(`${paper.title} ${paper.abstract} ${(paper.tags || []).join(" ")}`),
      };
    });

    const n = docs.length || 1;
    let titleDl = 0;
    let bodyDl = 0;
    const df = new Map();
    for (const doc of docs) {
      titleDl += doc.titleLen;
      bodyDl += doc.bodyLen;
      const seen = new Set([...doc.titleTf.keys(), ...doc.bodyTf.keys()]);
      for (const term of seen) df.set(term, (df.get(term) || 0) + 1);
    }

    return {
      docs,
      n,
      avgTitle: titleDl / n,
      avgBody: bodyDl / n,
      df,
    };
  }

  function idf(index, term) {
    const df = index.df.get(term) || 0;
    return Math.log((index.n - df + 0.5) / (df + 0.5) + 1);
  }

  function fieldScore(tf, dl, avgdl, idfValue) {
    const freq = tf || 0;
    if (!freq) return 0;
    const denom = freq + K1 * (1 - B + B * (dl / avgdl));
    return idfValue * ((freq * (K1 + 1)) / denom);
  }

  function search(index, query, limit = 50, opts = {}) {
    const raw = String(query || "").trim();
    const exactMode = !!opts.exact;
    const terms = tokenize(expandQuery(raw));
    if ((!terms.length && !raw) || !index.docs.length) return [];
    const uniq = [...new Set(terms)];
    const rawNorm = normalize(raw);
    const scored = [];
    for (const doc of index.docs) {
      const exactTitle = rawNorm.length > 1 && doc.titleNorm === rawNorm;
      const phraseTitle = rawNorm.length >= 3 && doc.titleNorm.includes(rawNorm);
      const phraseDoc = rawNorm.length >= 3 && doc.blobNorm.includes(rawNorm);
      const coverTitle = uniq.length > 0 && uniq.every((term) => doc.titleTf.has(term));
      const coverDoc =
        uniq.length > 0 && uniq.every((term) => doc.titleTf.has(term) || doc.bodyTf.has(term));

      if (exactMode && !exactTitle && !phraseTitle && !coverDoc) continue;

      let score = 0;
      for (const term of uniq) {
        const w = idf(index, term);
        score += 2.6 * fieldScore(doc.titleTf.get(term), doc.titleLen, index.avgTitle, w);
        score += fieldScore(doc.bodyTf.get(term), doc.bodyLen, index.avgBody, w);
      }
      if (exactTitle) score += 1000;
      else if (phraseTitle) score += 280;
      else if (coverTitle) score += 90;
      else if (phraseDoc) score += 45;
      else if (coverDoc) score += 18;

      if (score > 0) {
        scored.push({
          paper: doc.paper,
          score,
          match: exactTitle ? "exact" : phraseTitle || coverTitle ? "cover" : "bm25",
        });
      }
    }
    scored.sort((a, b) => b.score - a.score || (b.paper.announced_date || "").localeCompare(a.paper.announced_date || ""));
    return scored.slice(0, limit);
  }

  function highlight(text, query) {
    const raw = String(query || "").trim();
    const terms = tokenize(expandQuery(raw)).filter((tok) => tok.length >= 2);
    if (!terms.length && raw.length < 2) return escapeHtml(text);
    const uniq = [...new Set([raw, ...terms])].filter(Boolean).sort((a, b) => b.length - a.length);
    const escaped = uniq.map((tok) => tok.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    const re = new RegExp(`(${escaped.join("|")})`, "gi");
    return escapeHtml(text).replace(re, '<mark class="mark-hit">$1</mark>');
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  return { build, search, highlight, escapeHtml, tokenize, normalize };
})();
