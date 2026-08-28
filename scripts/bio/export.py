"""Write validated static snapshots and per-entry pages for GitHub Pages."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .config import CATEGORY_LABELS
from .models import BioEntry


ENTRY_PAGE = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Bio &amp; Medical Benchmarks</title>
    <meta name="color-scheme" content="light dark" />
    <link rel="icon" href="../../favicon.svg" type="image/svg+xml" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;0,6..72,700&family=Public+Sans:wght@400;500;600&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="../../css/style.css" />
    <link rel="stylesheet" href="../css/bio.css" />
    <script>window.BIO_ENTRY_ID = {entry_id}; window.BIO_BASE = "../";</script>
  </head>
  <body>
    <header class="masthead masthead--simple">
      <div class="masthead__brand">
        <a class="wordmark" href="../"><span><span class="wordmark__kicker">Daily index</span><span class="wordmark__title">Bio &amp; Medical Benchmarks</span></span></a>
      </div>
      <nav class="site-switch" aria-label="Benchmark collections"><a href="../../">Agent</a><a href="../" aria-current="page">Bio &amp; Medical</a></nav>
    </header>
    <main id="main" class="paper-page"></main>
    <script src="../../js/bm25.js"></script>
    <script src="../js/i18n.js"></script>
    <script src="../js/item.js"></script>
  </body>
</html>
"""


def _agent_lookup(agent_index: Path) -> tuple[dict[str, str], dict[str, str]]:
    if not agent_index.exists():
        return {}, {}
    payload = json.loads(agent_index.read_text(encoding="utf-8"))
    arxiv = {}
    dois = {}
    for paper in payload.get("papers", []):
        paper_id = str(paper.get("id") or "")
        if paper_id:
            arxiv[paper_id.lower()] = paper_id
        doi = str(paper.get("doi") or "").lower()
        if doi:
            dois[doi] = paper_id
    return arxiv, dois


def attach_agent_links(entries: list[BioEntry], agent_index: Path) -> None:
    by_arxiv, by_doi = _agent_lookup(agent_index)
    for entry in entries:
        paper_id = by_arxiv.get(entry.identifiers.get("arxiv", "").lower())
        if not paper_id:
            paper_id = by_doi.get(entry.identifiers.get("doi", "").lower())
        if paper_id:
            safe = paper_id.replace("/", "_")
            entry.related_agent_url = f"../../p/{safe}.html"


def build_payload(entries: list[BioEntry], generated_at: str, source_health: list[dict[str, Any]]) -> dict[str, Any]:
    category_counts = Counter(category for entry in entries for category in entry.categories)
    priority_counts = Counter(entry.priority for entry in entries)
    status_counts = Counter(entry.collection_status for entry in entries)
    kind_counts = Counter(entry.kind for entry in entries)
    context_counts = Counter(context for entry in entries for context in entry.evaluation_contexts)
    by_day: dict[str, list[str]] = defaultdict(list)
    for entry in entries:
        day = (entry.event_at or entry.published_at or entry.first_seen_at)[:10]
        if day:
            by_day[day].append(entry.id)
    days = [
        {"date": day, "count": len(ids), "entry_ids": ids}
        for day, ids in sorted(by_day.items(), reverse=True)
    ]
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "total": len(entries),
        "counts": {
            "priorities": dict(priority_counts),
            "categories": dict(category_counts),
            "statuses": dict(status_counts),
            "kinds": dict(kind_counts),
            "evaluation_contexts": dict(context_counts),
        },
        "category_labels": CATEGORY_LABELS,
        "source_health": source_health,
        "days": days,
        "entries": [entry.to_dict() for entry in entries],
    }


def validate_payload(payload: dict[str, Any]) -> None:
    required_top = {"schema_version", "generated_at", "total", "counts", "days", "entries"}
    missing = required_top.difference(payload)
    if missing:
        raise ValueError(f"Bio index missing keys: {sorted(missing)}")
    if payload["total"] != len(payload["entries"]):
        raise ValueError("Bio index total does not match entries length")
    seen = set()
    for row in payload["entries"]:
        required = {
            "id",
            "slug",
            "kind",
            "title",
            "priority",
            "categories",
            "collection_status",
            "evidence",
            "links",
            "evaluation_contexts",
        }
        absent = required.difference(row)
        if absent:
            raise ValueError(f"Entry {row.get('id')} missing {sorted(absent)}")
        if row["id"] in seen:
            raise ValueError(f"Duplicate Bio entry id: {row['id']}")
        if row["priority"] not in {"P0", "P1", "P2"}:
            raise ValueError(f"Invalid priority for {row['id']}")
        if row["collection_status"] not in {"confirmed", "watchlist"}:
            raise ValueError(f"Invalid public collection status for {row['id']}")
        seen.add(row["id"])


def write_vendor_archive(
    output_dir: Path,
    entries: list[BioEntry],
    generated_at: str,
) -> dict[str, Any]:
    payload = {
        "schema_version": 1,
        "generated_at": generated_at,
        "total": len(entries),
        "entries": [entry.to_dict() for entry in entries],
    }
    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "vendor-archive.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def write_snapshot(
    output_dir: Path,
    entries: list[BioEntry],
    generated_at: str,
    source_health: list[dict[str, Any]],
    agent_index: Path,
) -> dict[str, Any]:
    attach_agent_links(entries, agent_index)
    payload = build_payload(entries, generated_at, source_health)
    validate_payload(payload)
    data_dir = output_dir / "data"
    day_dir = data_dir / "days"
    page_dir = output_dir / "p"
    day_dir.mkdir(parents=True, exist_ok=True)
    page_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "index.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    meta = {
        "schema_version": payload["schema_version"],
        "generated_at": generated_at,
        "total": payload["total"],
        "day_count": len(payload["days"]),
        "latest_date": payload["days"][0]["date"] if payload["days"] else "",
        "counts": payload["counts"],
        "source_health": source_health,
    }
    (data_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    by_id = {entry.id: entry.to_dict() for entry in entries}
    keep_days = set()
    for day in payload["days"]:
        keep_days.add(day["date"])
        rows = [by_id[entry_id] for entry_id in day["entry_ids"]]
        (day_dir / f"{day['date']}.json").write_text(
            json.dumps({"date": day["date"], "count": len(rows), "entries": rows}, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
    for path in day_dir.glob("*.json"):
        if path.stem not in keep_days:
            path.unlink()
    keep_pages = set()
    for entry in entries:
        keep_pages.add(entry.slug)
        (page_dir / f"{entry.slug}.html").write_text(
            ENTRY_PAGE.format(entry_id=json.dumps(entry.id)),
            encoding="utf-8",
        )
    for path in page_dir.glob("*.html"):
        if path.stem not in keep_pages:
            path.unlink()
    return payload
