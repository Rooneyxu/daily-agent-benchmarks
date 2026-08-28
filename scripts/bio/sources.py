"""First-party source adapters for Bio & Medical benchmark discovery."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from .config import MODEL_LINK_RE, REQUEST_TIMEOUT_S, USER_AGENT, VENDOR_SOURCES
from .models import SourceCandidate

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


def _text(element: ET.Element | None) -> str:
    if element is None or element.text is None:
        return ""
    return re.sub(r"\s+", " ", element.text).strip()


def _iso_date(value: str | int | None) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, int) or str(value).isdigit():
        number = int(value)
        if number > 10_000_000_000:
            number //= 1000
        return datetime.fromtimestamp(number, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw = str(value).strip()
    if len(raw) == 10 and raw[4] == "-":
        return f"{raw}T00:00:00Z"
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    except ValueError:
        return raw


def _content_value(content: dict[str, Any], key: str, default: Any = "") -> Any:
    value = content.get(key, default)
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


class SourceAdapter(ABC):
    id: str
    name: str

    def __init__(self, client: httpx.Client) -> None:
        self.client = client

    def _get(self, url: str, **kwargs: Any) -> httpx.Response:
        headers = {"User-Agent": USER_AGENT, "Accept": "application/json,text/html,application/xml;q=0.9,*/*;q=0.5"}
        headers.update(kwargs.pop("headers", {}))
        response = self.client.get(
            url,
            headers=headers,
            timeout=REQUEST_TIMEOUT_S,
            follow_redirects=True,
            **kwargs,
        )
        response.raise_for_status()
        return response

    @abstractmethod
    def discover(self, date_from: str, date_to: str) -> list[SourceCandidate]:
        raise NotImplementedError


class ArxivAdapter(SourceAdapter):
    id = "arxiv"
    name = "arXiv"
    endpoint = "https://export.arxiv.org/api/query"
    queries = (
        '(ti:benchmark OR ti:bench OR ti:"evaluation suite") AND (all:biomedical OR all:medical OR all:clinical)',
        '(ti:benchmark OR ti:bench OR ti:"evaluation suite") AND (all:biology OR all:biological OR all:"life science")',
        '(ti:benchmark OR ti:bench) AND (all:genomics OR all:proteomics OR all:"protein design")',
        '(ti:benchmark OR ti:bench) AND (all:"wet lab" OR all:protocol OR all:biosecurity OR all:biosafety)',
    )

    def _entry(self, entry: ET.Element) -> SourceCandidate:
        abs_url = _text(entry.find(f"{ATOM}id")).replace("http://", "https://")
        arxiv_id = re.sub(r"v\d+$", "", abs_url.rsplit("/", 1)[-1])
        links = {
            "abs": f"https://arxiv.org/abs/{arxiv_id}",
            "html": f"https://arxiv.org/html/{arxiv_id}",
            "pdf": f"https://arxiv.org/pdf/{arxiv_id}",
        }
        for link in entry.findall(f"{ATOM}link"):
            href = link.attrib.get("href", "").replace("http://", "https://")
            if link.attrib.get("title") == "pdf" or href.endswith(".pdf"):
                links["pdf"] = href
            elif link.attrib.get("rel") == "alternate":
                links["abs"] = href
        authors = [
            _text(author.find(f"{ATOM}name"))
            for author in entry.findall(f"{ATOM}author")
            if _text(author.find(f"{ATOM}name"))
        ]
        doi = _text(entry.find(f"{ARXIV_NS}doi"))
        return SourceCandidate(
            source=self.id,
            source_id=arxiv_id,
            kind="paper",
            title=_text(entry.find(f"{ATOM}title")),
            abstract=_text(entry.find(f"{ATOM}summary")),
            authors=authors,
            published_at=_iso_date(_text(entry.find(f"{ATOM}published"))),
            updated_at=_iso_date(_text(entry.find(f"{ATOM}updated"))),
            identifiers={"arxiv": arxiv_id, **({"doi": doi} if doi else {})},
            links=links,
            content_url=links["html"],
            content_type="html",
        )

    def discover(self, date_from: str, date_to: str) -> list[SourceCandidate]:
        rows: dict[str, SourceCandidate] = {}
        for query in self.queries:
            response = self._get(
                self.endpoint,
                params={
                    "search_query": query,
                    "start": 0,
                    "max_results": 200,
                    "sortBy": "submittedDate",
                    "sortOrder": "descending",
                },
            )
            root = ET.fromstring(response.content)
            for entry in root.findall(f"{ATOM}entry"):
                candidate = self._entry(entry)
                day = candidate.published_at[:10]
                if date_from <= day <= date_to:
                    rows[candidate.source_id] = candidate
        return list(rows.values())


class EuropePmcAdapter(SourceAdapter):
    id = "europepmc"
    name = "Europe PMC"
    endpoint = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    def discover(self, date_from: str, date_to: str) -> list[SourceCandidate]:
        query = (
            f'FIRST_PDATE:[{date_from} TO {date_to}] AND '
            '((TITLE_ABS:"benchmark" OR TITLE_ABS:"evaluation suite" OR TITLE_ABS:"challenge set") AND '
            '(TITLE_ABS:"biomedical" OR TITLE_ABS:"medical" OR TITLE_ABS:"clinical" OR '
            'TITLE_ABS:"biology" OR TITLE_ABS:"biological" OR TITLE_ABS:"life science" OR '
            'TITLE_ABS:"genomics" OR TITLE_ABS:"proteomics" OR TITLE_ABS:"wet lab" OR '
            'TITLE_ABS:"biosecurity" OR TITLE_ABS:"biosafety"))'
        )
        cursor = "*"
        rows: list[SourceCandidate] = []
        for _ in range(5):
            response = self._get(
                self.endpoint,
                params={
                    "query": query,
                    "format": "json",
                    "resultType": "core",
                    "pageSize": 200,
                    "cursorMark": cursor,
                },
            )
            payload = response.json()
            results = payload.get("resultList", {}).get("result", [])
            for result in results:
                source_id = str(result.get("id") or result.get("pmid") or result.get("doi") or "")
                if not source_id:
                    continue
                pmcid = str(result.get("pmcid") or "")
                pmid = str(result.get("pmid") or "")
                doi = str(result.get("doi") or "")
                page_url = f"https://europepmc.org/article/{result.get('source', 'MED')}/{source_id}"
                links = {"abs": page_url}
                content_url = ""
                content_type = "text"
                if pmcid:
                    content_url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
                    content_type = "html"
                    links["html"] = page_url
                identifiers = {}
                if doi:
                    identifiers["doi"] = doi
                if pmid:
                    identifiers["pmid"] = pmid
                if pmcid:
                    identifiers["pmcid"] = pmcid
                author_text = result.get("authorString") or ""
                authors = [name.strip() for name in str(author_text).split(",") if name.strip()]
                rows.append(
                    SourceCandidate(
                        source=self.id,
                        source_id=source_id,
                        kind="paper",
                        title=str(result.get("title") or ""),
                        abstract=str(result.get("abstractText") or ""),
                        authors=authors,
                        published_at=_iso_date(result.get("firstPublicationDate") or result.get("firstIndexDate")),
                        updated_at=_iso_date(result.get("firstIndexDate")),
                        identifiers=identifiers,
                        links=links,
                        content_url=content_url,
                        content_type=content_type,
                        metadata={
                            "journal": result.get("journalTitle") or "",
                            "license": result.get("license") or "",
                            "is_open_access": str(result.get("isOpenAccess") or "").upper() == "Y",
                        },
                    )
                )
            next_cursor = payload.get("nextCursorMark")
            if not results or not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
        return rows


class BioRxivAdapter(SourceAdapter):
    name = "bioRxiv / medRxiv"

    def __init__(self, client: httpx.Client, server: str) -> None:
        super().__init__(client)
        self.server = server
        self.id = server

    def discover(self, date_from: str, date_to: str) -> list[SourceCandidate]:
        cursor = 0
        rows = []
        while cursor < 3000:
            url = f"https://api.biorxiv.org/details/{self.server}/{date_from}/{date_to}/{cursor}"
            payload = self._get(url).json()
            collection = payload.get("collection", [])
            if not collection:
                break
            for result in collection:
                doi = str(result.get("doi") or "")
                page_url = f"https://www.{self.server}.org/content/{doi}"
                rows.append(
                    SourceCandidate(
                        source=self.id,
                        source_id=doi,
                        kind="paper",
                        title=str(result.get("title") or ""),
                        abstract=str(result.get("abstract") or ""),
                        authors=[name.strip() for name in str(result.get("authors") or "").split(";") if name.strip()],
                        published_at=_iso_date(result.get("date")),
                        updated_at=_iso_date(result.get("date")),
                        identifiers={"doi": doi},
                        links={"abs": page_url, "html": f"{page_url}.full", "pdf": f"{page_url}.full.pdf"},
                        content_url=f"{page_url}.full",
                        content_type="html",
                        metadata={
                            "license": result.get("license") or "",
                            "category": result.get("category") or "",
                            "version": result.get("version") or "",
                        },
                    )
                )
            if len(collection) < 30:
                break
            cursor += len(collection)
        return rows


class OpenReviewAdapter(SourceAdapter):
    id = "openreview"
    name = "OpenReview"
    endpoint = "https://api2.openreview.net/notes/search"

    def discover(self, date_from: str, date_to: str) -> list[SourceCandidate]:
        rows: dict[str, SourceCandidate] = {}
        for query in ("benchmark biology", "benchmark biomedical", "benchmark medical", "benchmark biosecurity"):
            payload = self._get(
                self.endpoint,
                params={"query": query, "content": "all", "sort": "tmdate:desc", "limit": 200},
            ).json()
            for note in payload.get("notes", []):
                note_id = str(note.get("id") or "")
                content = note.get("content") or {}
                title = str(_content_value(content, "title", ""))
                abstract = str(_content_value(content, "abstract", ""))
                authors = _content_value(content, "authors", [])
                if isinstance(authors, str):
                    authors = [authors]
                published = _iso_date(note.get("cdate") or note.get("pdate") or note.get("tcdate"))
                day = published[:10]
                if not note_id or not (date_from <= day <= date_to):
                    continue
                forum = str(note.get("forum") or note_id)
                forum_url = f"https://openreview.net/forum?id={forum}"
                rows[note_id] = SourceCandidate(
                    source=self.id,
                    source_id=note_id,
                    kind="paper",
                    title=title,
                    abstract=abstract,
                    authors=[str(author) for author in authors],
                    published_at=published,
                    updated_at=_iso_date(note.get("tmdate")),
                    identifiers={"openreview": note_id},
                    links={"abs": forum_url, "pdf": f"https://openreview.net/pdf?id={note_id}"},
                    content_url=f"https://openreview.net/pdf?id={note_id}",
                    content_type="pdf",
                    metadata={"venue": _content_value(content, "venue", "")},
                )
        return list(rows.values())


class VendorAdapter(SourceAdapter):
    def __init__(self, client: httpx.Client, config: dict[str, object]) -> None:
        super().__init__(client)
        self.id = f"vendor:{config['id']}"
        self.name = str(config["name"])
        self.indexes = tuple(str(url) for url in config["indexes"])

    def discover(self, date_from: str, date_to: str) -> list[SourceCandidate]:
        del date_from, date_to  # Index pages are diffed by stable URL and content hash instead of date queries.
        rows: dict[str, SourceCandidate] = {}
        for index_url in self.indexes:
            response = self._get(index_url, headers={"Accept": "text/html"})
            soup = BeautifulSoup(response.content, "html.parser")
            accepted_from_index = 0
            for anchor in soup.find_all("a", href=True):
                href = urljoin(str(response.url), str(anchor["href"]))
                label = re.sub(r"\s+", " ", anchor.get_text(" ", strip=True))
                probe = f"{label} {href}"
                if not href.startswith("http") or not MODEL_LINK_RE.search(probe):
                    continue
                source_id = hashlib.sha256(href.encode("utf-8")).hexdigest()[:24]
                is_pdf = href.lower().split("?", 1)[0].endswith(".pdf")
                rows[source_id] = SourceCandidate(
                    source=self.id,
                    source_id=source_id,
                    kind="evaluation_update",
                    title=label or f"{self.name} model evaluation update",
                    published_at="",
                    updated_at="",
                    identifiers={},
                    links={"abs": href, **({"pdf": href} if is_pdf else {"html": href})},
                    content_url=href,
                    content_type="pdf" if is_pdf else "html",
                    metadata={"vendor": self.name, "index_url": index_url},
                )
                accepted_from_index += 1
                if accepted_from_index >= 12:
                    break
        return list(rows.values())


def build_adapters(client: httpx.Client, include_vendors: bool = True) -> list[SourceAdapter]:
    adapters: list[SourceAdapter] = [
        ArxivAdapter(client),
        EuropePmcAdapter(client),
        BioRxivAdapter(client, "biorxiv"),
        BioRxivAdapter(client, "medrxiv"),
        OpenReviewAdapter(client),
    ]
    if include_vendors:
        adapters.extend(VendorAdapter(client, config) for config in VENDOR_SOURCES)
    return adapters
