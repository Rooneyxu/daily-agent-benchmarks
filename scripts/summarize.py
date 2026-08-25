"""Bilingual extractive daily reports — no LLM required."""

from __future__ import annotations

from collections import Counter
from typing import Any

from config import THEME_LABELS

_MONTH_ZH = (
    "",
    "1月",
    "2月",
    "3月",
    "4月",
    "5月",
    "6月",
    "7月",
    "8月",
    "9月",
    "10月",
    "11月",
    "12月",
)


def _ymd(date: str) -> tuple[int, int, int]:
    y, m, d = date.split("-")
    return int(y), int(m), int(d)


def format_date_en(date: str) -> str:
    y, m, d = _ymd(date)
    months = (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    )
    return f"{months[m - 1]} {d}, {y}"


def format_date_zh(date: str) -> str:
    y, m, d = _ymd(date)
    return f"{y}年{_MONTH_ZH[m]}{d}日"


def _first_sentence(text: str, limit: int = 220) -> str:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return ""
    for sep in (". ", "? ", "! "):
        idx = cleaned.find(sep)
        if 40 <= idx <= limit:
            return cleaned[: idx + 1]
    return cleaned[:limit].rstrip(" ,;:") + ("…" if len(cleaned) > limit else "")


def _theme_phrase(tags: list[str], lang: str) -> str:
    counted = Counter(tags)
    if not counted:
        return ""
    parts = []
    for theme, n in counted.most_common(4):
        label = THEME_LABELS.get(theme, {}).get(lang, theme)
        parts.append(f"{label} ({n})" if lang == "en" else f"{label}（{n}）")
    if lang == "en":
        if len(parts) == 1:
            return parts[0]
        return ", ".join(parts[:-1]) + f", and {parts[-1]}"
    return "、".join(parts)


def build_report(date: str, papers: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(papers)
    all_tags: list[str] = []
    for p in papers:
        all_tags.extend(p.get("tags") or [])
    theme_en = _theme_phrase(all_tags, "en")
    theme_zh = _theme_phrase(all_tags, "zh")
    ranked = sorted(papers, key=lambda p: (-int(p.get("score") or 0), p.get("title") or ""))
    highlights = ranked[: min(3, n)]

    if n == 0:
        en_summary = f"No new agent benchmarks were listed on arXiv on {format_date_en(date)}."
        zh_summary = f"{format_date_zh(date)}，arXiv 未出现新的 Agent Benchmark 论文。"
        headline_en = "Quiet day"
        headline_zh = "当日暂无新论文"
    elif n == 1:
        title = highlights[0]["title"]
        en_summary = (
            f"On {format_date_en(date)}, arXiv listed 1 new agent benchmark: {title}."
        )
        zh_summary = f"{format_date_zh(date)}，arXiv 新增 1 篇 Agent Benchmark：{title}。"
        headline_en = "1 new agent benchmark"
        headline_zh = "新增 1 篇 Agent Benchmark"
    else:
        cluster = f" Work clustered around {theme_en}." if theme_en else ""
        cluster_zh = f"当日主题集中在{theme_zh}。" if theme_zh else ""
        en_summary = (
            f"On {format_date_en(date)}, arXiv listed {n} new agent benchmarks.{cluster}"
        )
        zh_summary = f"{format_date_zh(date)}，arXiv 新增 {n} 篇 Agent Benchmark。{cluster_zh}"
        headline_en = f"{n} new agent benchmarks"
        headline_zh = f"新增 {n} 篇 Agent Benchmark"

    bullets_en = []
    bullets_zh = []
    for p in highlights:
        sent = _first_sentence(p.get("abstract") or "")
        bullets_en.append({"id": p["id"], "title": p["title"], "blurb": sent})
        bullets_zh.append({"id": p["id"], "title": p["title"], "blurb": sent})

    theme_counts = [
        {
            "id": theme,
            "count": count,
            "en": THEME_LABELS.get(theme, {}).get("en", theme),
            "zh": THEME_LABELS.get(theme, {}).get("zh", theme),
        }
        for theme, count in Counter(all_tags).most_common(8)
    ]

    return {
        "date": date,
        "count": n,
        "themes": theme_counts,
        "en": {
            "headline": headline_en,
            "summary": en_summary,
            "highlights": bullets_en,
        },
        "zh": {
            "headline": headline_zh,
            "summary": zh_summary,
            "highlights": bullets_zh,
        },
    }
