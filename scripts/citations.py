"""Attach Semantic Scholar citation counts (academic heat)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from config import USER_AGENT

S2_BATCH = "https://api.semanticscholar.org/graph/v1/paper/batch"
CHUNK = 80
GAP_S = 1.2


def _post(url: str, payload: dict[str, Any], retries: int = 3) -> Any:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=40) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code in {429, 500, 502, 503} and attempt + 1 < retries:
                time.sleep(GAP_S * (attempt + 2))
                continue
            raise
        except urllib.error.URLError as exc:
            last_err = exc
            if attempt + 1 < retries:
                time.sleep(GAP_S * (attempt + 2))
                continue
            raise
    raise RuntimeError(f"Semantic Scholar request failed: {last_err}")


def attach_citations(papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not papers:
        return papers
    print(f"Fetching citation counts for {len(papers)} papers", flush=True)
    by_id = {p["id"]: p for p in papers}
    ids = [p["id"] for p in papers if p.get("citations") is None]
    for offset in range(0, len(ids), CHUNK):
        chunk = ids[offset : offset + CHUNK]
        if offset:
            time.sleep(GAP_S)
        try:
            rows = _post(
                S2_BATCH + "?fields=citationCount,externalIds",
                {"ids": [f"ARXIV:{arxiv_id}" for arxiv_id in chunk]},
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  citation batch {offset} failed: {exc}", flush=True)
            continue
        if not isinstance(rows, list):
            continue
        for arxiv_id, row in zip(chunk, rows):
            paper = by_id.get(arxiv_id)
            if paper is None:
                continue
            if not isinstance(row, dict):
                paper.setdefault("citations", 0)
                continue
            paper["citations"] = int(row.get("citationCount") or 0)
    for paper in papers:
        paper.setdefault("citations", 0)
    return papers
