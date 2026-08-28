from __future__ import annotations

import httpx

from bio.extract import fetch_document
from bio.models import SourceCandidate
from bio.sources import ArxivAdapter, BioRxivAdapter, EuropePmcAdapter, OpenReviewAdapter, VendorAdapter
from bio.update import _run_adapter


def client_for(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_arxiv_atom_parser() -> None:
    atom = b"""<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry><id>http://arxiv.org/abs/2608.12345v2</id><updated>2026-08-27T01:02:03Z</updated>
      <published>2026-08-26T01:02:03Z</published><title>BioBench: a medical benchmark</title>
      <summary>We introduce a benchmark for biology.</summary><author><name>A. Author</name></author>
      <arxiv:doi>10.1000/example</arxiv:doi><link rel="alternate" href="http://arxiv.org/abs/2608.12345v2" />
      <link title="pdf" href="http://arxiv.org/pdf/2608.12345v2" /></entry></feed>"""
    with client_for(lambda request: httpx.Response(200, content=atom, request=request)) as client:
        rows = ArxivAdapter(client).discover("2026-08-26", "2026-08-27")
    assert len(rows) == 1
    assert rows[0].identifiers == {"arxiv": "2608.12345", "doi": "10.1000/example"}
    assert rows[0].links["pdf"].startswith("https://")


def test_europe_pmc_core_and_jats_full_text() -> None:
    payload = {
        "resultList": {
            "result": [
                {
                    "id": "123456",
                    "source": "MED",
                    "pmid": "123456",
                    "pmcid": "PMC123456",
                    "doi": "10.1000/pmc",
                    "title": "ClinicalBench",
                    "abstractText": "We introduce a medical benchmark.",
                    "authorString": "A Author, B Author",
                    "firstPublicationDate": "2026-08-26",
                    "isOpenAccess": "Y",
                    "license": "CC BY",
                }
            ]
        },
        "nextCursorMark": "*",
    }
    jats = b"""<article><front><article-meta><title-group><article-title>ClinicalBench</article-title>
    </title-group></article-meta></front><body><sec><title>Evaluation</title>
    <p>We introduce a biomedical benchmark suite with source-grounded question generation.</p>
    </sec></body></article>"""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("fullTextXML"):
            return httpx.Response(200, content=jats, headers={"content-type": "application/xml"}, request=request)
        return httpx.Response(200, json=payload, request=request)

    with client_for(handler) as client:
        candidate = EuropePmcAdapter(client).discover("2026-08-26", "2026-08-27")[0]
        document = fetch_document(client, candidate)
    assert candidate.identifiers["pmcid"] == "PMC123456"
    assert "[[SECTION Evaluation]]" in document.body
    assert document.extraction_status == "complete"


def test_biorxiv_and_medrxiv_api_shape() -> None:
    payload = {
        "collection": [
            {
                "doi": "10.1101/2026.08.26.123456",
                "title": "BioBench",
                "abstract": "We introduce a biology benchmark.",
                "authors": "A Author; B Author",
                "date": "2026-08-26",
                "license": "cc_by",
                "category": "bioinformatics",
                "version": "1",
            }
        ]
    }
    with client_for(lambda request: httpx.Response(200, json=payload, request=request)) as client:
        bio = BioRxivAdapter(client, "biorxiv").discover("2026-08-26", "2026-08-27")
        med = BioRxivAdapter(client, "medrxiv").discover("2026-08-26", "2026-08-27")
    assert bio[0].source == "biorxiv"
    assert med[0].source == "medrxiv"
    assert bio[0].links["pdf"].endswith(".full.pdf")


def test_openreview_v2_wrapped_and_v1_plain_content() -> None:
    payload = {
        "notes": [
            {
                "id": "v2-note",
                "forum": "v2-forum",
                "cdate": 1787702400000,
                "tmdate": 1787702400000,
                "content": {
                    "title": {"value": "BioBench V2"},
                    "abstract": {"value": "We introduce a medical benchmark."},
                    "authors": {"value": ["A Author"]},
                    "venue": {"value": "ICLR 2027"},
                },
            },
            {
                "id": "v1-note",
                "forum": "v1-forum",
                "cdate": 1787702400000,
                "content": {
                    "title": "BioBench V1",
                    "abstract": "We introduce a biology benchmark.",
                    "authors": ["B Author"],
                    "venue": "Legacy venue",
                },
            },
        ]
    }
    with client_for(lambda request: httpx.Response(200, json=payload, request=request)) as client:
        rows = OpenReviewAdapter(client).discover("2026-08-25", "2026-08-27")
    assert {row.source_id for row in rows} == {"v1-note", "v2-note"}
    assert {row.title for row in rows} == {"BioBench V1", "BioBench V2"}


def test_vendor_index_failure_keeps_sibling_index_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/blocked":
            return httpx.Response(403, request=request)
        return httpx.Response(
            200,
            text='<a href="/biology-system-card">Biology benchmark system card</a>',
            request=request,
        )

    config = {
        "id": "example",
        "name": "Example AI",
        "indexes": ("https://vendor.test/good", "https://vendor.test/blocked"),
    }
    with client_for(handler) as client:
        adapter = VendorAdapter(client, config)
        _, entries, health = _run_adapter(
            adapter,
            client,
            "2026-08-27",
            "2026-08-28",
            set(),
            "2026-08-28T00:00:00Z",
            fetch_full_text=False,
        )

    assert health["status"] == "partial"
    assert health["discovered"] == 1
    assert health["published"] == 1
    assert "403 Forbidden" in health["error"]
    assert entries[0].kind == "evaluation_update"


def minimal_pdf(text: str) -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 10 Tf 72 720 Td ({escaped}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    data.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(data)


def test_html_and_pdf_card_full_text_extraction() -> None:
    html = b"""<html><body><h2>Biology evaluations</h2><p>We introduce a biomedical benchmark
    with automated verifier and troubleshooting.</p><a href="https://github.com/example/bench">Code</a></body></html>"""
    pdf = minimal_pdf(" ".join(["Biology benchmark system card evaluation with wet lab troubleshooting."] * 12))

    def handler(request: httpx.Request) -> httpx.Response:
        content = pdf if request.url.path.endswith(".pdf") else html
        content_type = "application/pdf" if request.url.path.endswith(".pdf") else "text/html"
        return httpx.Response(200, content=content, headers={"content-type": content_type}, request=request)

    html_candidate = SourceCandidate(
        source="vendor:test",
        source_id="html-card",
        kind="evaluation_update",
        title="HTML system card",
        content_url="https://example.test/card",
        content_type="html",
        links={"html": "https://example.test/card"},
    )
    pdf_candidate = SourceCandidate(
        source="vendor:test",
        source_id="pdf-card",
        kind="evaluation_update",
        title="PDF system card",
        content_url="https://example.test/card.pdf",
        content_type="pdf",
        links={"pdf": "https://example.test/card.pdf"},
    )
    with client_for(handler) as client:
        html_document = fetch_document(client, html_candidate)
        pdf_document = fetch_document(client, pdf_candidate)
    assert "[[SECTION Biology evaluations]]" in html_document.body
    assert html_candidate.links["code"] == "https://github.com/example/bench"
    assert "[[PAGE 1]]" in pdf_document.body
    assert pdf_document.extraction_status == "complete"
