"""Resolve the reviewed arXiv seed selection into a reproducible static catalog."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

from .models import SourceCandidate, SourceDocument
from .sources import ATOM, ArxivAdapter
from .update import ROOT, document_to_entry


def build(selection_path: Path, output_path: Path) -> int:
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    arxiv_ids = selection.get("arxiv_ids", [])
    overrides = selection.get("overrides", {})
    entries = []
    with httpx.Client(transport=httpx.HTTPTransport(retries=2)) as client:
        adapter = ArxivAdapter(client)
        for offset in range(0, len(arxiv_ids), 20):
            chunk = arxiv_ids[offset : offset + 20]
            response = adapter._get(
                adapter.endpoint,
                params={"id_list": ",".join(chunk), "max_results": len(chunk)},
            )
            root = ET.fromstring(response.content)
            for element in root.findall(f"{ATOM}entry"):
                candidate = adapter._entry(element)
                document = SourceDocument(
                    candidate=candidate,
                    body=candidate.abstract,
                    content_hash=f"seed:{candidate.source_id}",
                    extraction_status="metadata_only",
                )
                entry = document_to_entry(document, candidate.published_at)
                if entry is None:
                    raise RuntimeError(f"Reviewed seed was excluded by current rules: {candidate.source_id}")
                override = overrides.get(candidate.source_id, {})
                for key, value in override.items():
                    setattr(entry, key, value)
                entry.evaluation_contexts = _contexts(entry.categories)
                entry.collection_status = "confirmed"
                entry.first_seen_at = candidate.published_at
                entry.event_at = candidate.published_at
                entry.is_seed = True
                entries.append(entry)
    for row in selection.get("manual_entries", []):
        candidate = SourceCandidate(
            source=row["source"],
            source_id=row["source_id"],
            kind=row["kind"],
            title=row["title"],
            abstract=row.get("abstract", ""),
            authors=row.get("authors", []),
            published_at=row["published_at"],
            updated_at=row.get("updated_at", row["published_at"]),
            identifiers=row.get("identifiers", {}),
            links=row.get("links", {}),
            content_url=row.get("links", {}).get("html") or row.get("links", {}).get("pdf", ""),
            content_type="html" if row.get("links", {}).get("html") else "pdf",
        )
        document = SourceDocument(
            candidate=candidate,
            body=row.get("body", row.get("abstract", "")),
            content_hash=f"seed:{candidate.source_id}",
            extraction_status="complete",
        )
        entry = document_to_entry(document, candidate.published_at)
        if entry is None:
            raise RuntimeError(f"Reviewed manual seed was excluded by current rules: {candidate.source_id}")
        for key, value in row.get("overrides", {}).items():
            setattr(entry, key, value)
        entry.evaluation_contexts = _contexts(entry.categories)
        entry.collection_status = "confirmed"
        entry.first_seen_at = candidate.published_at
        entry.event_at = candidate.published_at
        entry.is_seed = True
        entries.append(entry)
    resolved = {entry.identifiers.get("arxiv") for entry in entries}
    missing = [arxiv_id for arxiv_id in arxiv_ids if arxiv_id not in resolved]
    if missing:
        raise RuntimeError(f"arXiv did not resolve seed ids: {missing}")
    entries.sort(key=lambda entry: (entry.published_at, entry.id), reverse=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"schema_version": 1, "entries": [entry.to_dict() for entry in entries]}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return len(entries)


def _contexts(categories: list[str]) -> list[str]:
    contexts = ["beneficial_capability"] if any(category != "biosafety" for category in categories) else []
    if "biosafety" in categories:
        contexts.append("biosecurity_misuse")
    return contexts


def main() -> None:
    parser = argparse.ArgumentParser(description="Resolve reviewed Bio benchmark seed IDs.")
    parser.add_argument("--selection", type=Path, default=ROOT / "data" / "bio-seed-selection.json")
    parser.add_argument("--output", type=Path, default=ROOT / "data" / "bio-seeds.json")
    args = parser.parse_args()
    count = build(args.selection, args.output)
    print(f"Wrote {count} reviewed seed records -> {args.output}")


if __name__ == "__main__":
    main()
