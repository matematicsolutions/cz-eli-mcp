"""Smoke tests - require internet, hit the live Czech e-Sbirka SPARQL endpoint.

Run manually:

    pytest tests/test_smoke.py -v
"""

from __future__ import annotations

import pytest

from cz_eli_mcp.server import cz_get_act, cz_get_text, cz_search

# Zakon c. 110/2019 Sb. - the Czech data protection act (o zpracovani osobnich udaju).
YEAR, NUMBER = 2019, 110


@pytest.mark.asyncio
async def test_smoke_get_act() -> None:
    act = await cz_get_act(YEAR, NUMBER)
    assert act.eli_uri == "https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/2019/110"
    assert act.citation == "110/2019 Sb."
    assert act.human_readable_citation == "110/2019 Sb."
    assert act.source_url == "https://e-sbirka.gov.cz/eli/cz/sb/2019/110"
    assert act.latest_version_uri and "/eli/cz/sb/2019/110/" in act.latest_version_uri
    assert act.version_date and act.version_date[:4].isdigit()


@pytest.mark.asyncio
async def test_smoke_get_text() -> None:
    text = await cz_get_text(YEAR, NUMBER)
    assert text.content and "zpracování osobních údajů" in text.content
    assert text.fragment_count and text.fragment_count > 100
    assert text.eli_uri == "https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/2019/110"
    assert text.byte_size and text.byte_size > 1000
    assert "<var>" not in text.content


@pytest.mark.asyncio
async def test_smoke_search() -> None:
    res = await cz_search(year=2019, contains="110", limit=10)
    assert res.total >= 1
    hit = next((h for h in res.items if h.citation == "110/2019 Sb."), None)
    assert hit is not None
    assert hit.eli_uri == "https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/2019/110"


@pytest.mark.asyncio
async def test_smoke_search_by_year_only() -> None:
    res = await cz_search(year=2026, limit=5)
    assert res.total >= 1
    for h in res.items:
        assert h.eli_uri and "/eli/cz/sb/2026/" in h.eli_uri
        assert h.citation and h.citation.endswith("Sb.")
