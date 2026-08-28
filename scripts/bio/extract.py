"""HTML and PDF extraction with page/section markers for traceable evidence."""

from __future__ import annotations

import hashlib
import io
import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from .config import REQUEST_TIMEOUT_S, USER_AGENT
from .models import SourceCandidate, SourceDocument


def _hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _html_text(content: bytes, base_url: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(content, "html.parser")
    for element in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
        element.decompose()
    chunks: list[str] = []
    for element in soup.find_all(
        ["h1", "h2", "h3", "h4", "article-title", "title", "p", "li", "th", "td", "caption"]
    ):
        text = re.sub(r"\s+", " ", element.get_text(" ", strip=True))
        if not text:
            continue
        if element.name in {"h1", "h2", "h3", "h4", "article-title", "title", "caption"}:
            chunks.append(f"[[SECTION {text[:180]}]]")
        chunks.append(text)
    links = []
    for anchor in soup.find_all("a", href=True):
        href = urljoin(base_url, str(anchor["href"]))
        if href.startswith("http"):
            links.append(href)
    return "\n".join(chunks), list(dict.fromkeys(links))


def _pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content), strict=False)
    chunks = []
    extracted_chars = 0
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        extracted_chars += len(text.strip())
        chunks.append(f"[[PAGE {number}]]\n{text}")
    if not chunks or extracted_chars < 500:
        raise ValueError("PDF text layer is missing or too small; OCR is not enabled")
    return "\n".join(chunks)


def fetch_document(client: httpx.Client, candidate: SourceCandidate) -> SourceDocument:
    url = candidate.content_url or candidate.links.get("html") or candidate.links.get("pdf")
    if not url or candidate.content_type == "text":
        body = candidate.abstract or ""
        return SourceDocument(
            candidate=candidate,
            body=body,
            content_hash=_hash(body.encode("utf-8")),
            extraction_status="complete" if body else "metadata_only",
        )
    try:
        response = client.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf;q=0.9,*/*;q=0.5"},
            timeout=REQUEST_TIMEOUT_S,
            follow_redirects=True,
        )
        response.raise_for_status()
        content = response.content
        content_type = response.headers.get("content-type", "").lower()
        is_pdf = candidate.content_type == "pdf" or "application/pdf" in content_type or url.lower().endswith(".pdf")
        if is_pdf:
            body = _pdf_text(content)
        else:
            body, discovered_links = _html_text(content, str(response.url))
            for discovered in discovered_links:
                lowered = discovered.lower()
                if "github.com/" in lowered:
                    candidate.links.setdefault("code", discovered)
                elif "huggingface.co/datasets/" in lowered:
                    candidate.links.setdefault("data", discovered)
                elif lowered.endswith(".pdf"):
                    candidate.links.setdefault("pdf", discovered)
        return SourceDocument(candidate=candidate, body=body, content_hash=_hash(content))
    except Exception as exc:  # noqa: BLE001 - extraction failures are data, not fatal workflow errors.
        fallback = candidate.abstract or candidate.title
        return SourceDocument(
            candidate=candidate,
            body=fallback,
            content_hash=_hash(fallback.encode("utf-8")),
            extraction_status="incomplete",
            extraction_error=str(exc)[:500],
        )
