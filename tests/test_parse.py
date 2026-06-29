"""Offline parse tests - citation/text helpers against committed SPARQL JSON fixtures."""

from __future__ import annotations

import json
from pathlib import Path

from cz_eli_mcp.citations import (
    act_iri,
    assemble_text,
    build_act_record,
    clean_html,
    source_url_for,
    version_date,
)

FIX = Path(__file__).parent / "fixtures"


def _bindings(name: str) -> list[dict]:
    data = json.loads((FIX / name).read_text(encoding="utf-8"))
    return data["results"]["bindings"]


def test_act_iri_and_source_url():
    iri = act_iri(2019, 110)
    assert iri == "https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/2019/110"
    assert source_url_for(iri) == "https://e-sbirka.gov.cz/eli/cz/sb/2019/110"


def test_version_date():
    iri = "https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/2019/110"
    assert version_date(f"{iri}/2025-08-01") == "2025-08-01"
    assert version_date(iri) is None
    assert version_date(None) is None


def test_clean_html_strips_var_and_anchors():
    assert clean_html("<var>ČÁST PRVNÍ</var>") == "ČÁST PRVNÍ"
    anchor = 'text <a class="ext_odkaz" href="x">110/2019 Sb.</a> end'
    assert clean_html(anchor) == "text 110/2019 Sb. end"
    assert clean_html("S&#160;5 a&amp;b") == "S\xa05 a&b"  # entities decoded


def test_build_act_record_from_meta_fixture():
    rec = build_act_record(_bindings("act_2019_110_meta.json")[0], year=2019, number=110)
    assert rec["eli_uri"] == "https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/2019/110"
    assert rec["human_readable_citation"] == "110/2019 Sb."
    assert rec["citation"] == "110/2019 Sb."
    assert rec["source_url"] == "https://e-sbirka.gov.cz/eli/cz/sb/2019/110"
    assert rec["latest_version_uri"] and rec["latest_version_uri"].endswith("/2025-08-01")
    assert rec["version_date"] == "2025-08-01"


def test_assemble_text_from_fragments_fixture():
    text = assemble_text(_bindings("act_2019_110_fragments.json"))
    assert text, "assembled text must not be empty"
    # Fixture holds the opening fragments of the Czech data protection act.
    assert "zpracování osobních údajů" in text
    assert "<var>" not in text  # HTML markers stripped
