"""Precision filter + theme tagging for agent-benchmark papers."""

from __future__ import annotations

import re
from typing import Any

from config import (
    FIELD_PRIORITY_PATTERNS,
    FIELD_RULES,
    FIELD_TITLE_PATTERNS,
    INTRO_BENCH_PATTERNS,
    METHOD_TITLE_DROP_PATTERNS,
    NAMED_BENCH_PATTERNS,
    NEGATIVE_PATTERNS,
    RL_TITLE_PATTERNS,
    STRONG_AGENT_PATTERNS,
    STRONG_BENCH_PATTERNS,
    THEMES,
    TITLE_BENCH_PATTERNS,
    WEAK_AGENT_PATTERNS,
    WEAK_BENCH_PATTERNS,
)

_COMPILED: dict[str, list[re.Pattern[str]]] = {}


def _compile(patterns: tuple[str, ...]) -> list[re.Pattern[str]]:
    key = "\n".join(patterns)
    if key not in _COMPILED:
        _COMPILED[key] = [re.compile(p, re.IGNORECASE) for p in patterns]
    return _COMPILED[key]


def _count(text: str, patterns: tuple[str, ...]) -> int:
    return sum(1 for p in _compile(patterns) if p.search(text))


def _hits(text: str, patterns: tuple[str, ...]) -> list[str]:
    return [p.pattern for p in _compile(patterns) if p.search(text)]


def tag_themes(blob: str) -> list[str]:
    tags: list[str] = []
    for theme, patterns in THEMES.items():
        if _count(blob, patterns):
            tags.append(theme)
    return tags


def assign_field(tags: list[str], title: str = "", abstract: str = "") -> str:
    blob = f"{title}\n{abstract}"
    for field, patterns in FIELD_PRIORITY_PATTERNS:
        if _count(blob, patterns):
            return field
    for field, patterns in FIELD_TITLE_PATTERNS:
        if _count(title, patterns):
            return field
    tagset = set(tags)
    for field, members in FIELD_RULES:
        if tagset.intersection(members):
            return field
    return "other"


def classify(paper: dict[str, Any]) -> dict[str, Any] | None:
    title = paper.get("title") or ""
    abstract = paper.get("abstract") or ""
    blob = f"{title}\n{abstract}"

    if _count(blob, NEGATIVE_PATTERNS):
        return None

    strong_agent = _count(blob, STRONG_AGENT_PATTERNS)
    weak_agent = _count(blob, WEAK_AGENT_PATTERNS)
    strong_bench = _count(blob, STRONG_BENCH_PATTERNS)
    weak_bench = _count(blob, WEAK_BENCH_PATTERNS)
    title_strong_agent = _count(title, STRONG_AGENT_PATTERNS)
    title_is_bench = _count(title, TITLE_BENCH_PATTERNS)
    named_title = _count(title, NAMED_BENCH_PATTERNS)
    introduces = _count(blob, INTRO_BENCH_PATTERNS)
    agent_in_title = bool(re.search(r"\bagents?\b|\bagentic\b", title, re.IGNORECASE))

    if _count(title, RL_TITLE_PATTERNS) and not strong_agent:
        return None

    if _count(title, METHOD_TITLE_DROP_PATTERNS) and not title_is_bench and not named_title:
        return None

    accepted = False
    if named_title:
        accepted = True
    elif title_is_bench and (agent_in_title or title_strong_agent):
        accepted = True
    elif title_is_bench and strong_agent >= 2:
        accepted = True
    elif introduces and (agent_in_title or title_strong_agent or strong_agent >= 2):
        accepted = True

    if not accepted:
        return None

    score = (
        4 * title_is_bench
        + 4 * named_title
        + 3 * title_strong_agent
        + 2 * introduces
        + 2 * strong_agent
        + 2 * strong_bench
        + weak_agent
        + weak_bench
    )
    tags = tag_themes(blob)
    paper = dict(paper)
    paper["score"] = score
    paper["tags"] = tags
    paper["field"] = assign_field(tags, title, abstract)
    paper["match_hints"] = {
        "strong_agent": _hits(blob, STRONG_AGENT_PATTERNS)[:6],
        "title_bench": _hits(title, TITLE_BENCH_PATTERNS)[:4],
    }
    return paper
