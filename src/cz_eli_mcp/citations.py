"""Czech e-Sbirka (SPARQL/RDF) parsing + citation helpers.

e-Sbirka publishes the consolidated Collection of Laws (Sbirka zakonu) as RDF behind a
SPARQL endpoint. The act subject IRI follows the ELI URI template, e.g.
``https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/2019/110`` (cz = jurisdiction,
sb = Sbirka zakonu). That national ELI IRI is the stable identifier we expose as ``eli_uri``.

The full consolidated text is assembled from ordered HTML fragments (one act -> latest
version -> ordered fragments -> ``text-fragmentu``); there is no single official XML/PDF
manifestation, so ``cz_get_text`` returns plain text assembled from those fragments.

Citation contract:
- ``eli_uri``: the act IRI (national ELI URI). NEVER invented - built from year + number, and
  confirmed against the act's own ``citace-pravniho-aktu`` in the RDF.
- ``human_readable_citation``: the Czech official citation, e.g. "110/2019 Sb.".
- ``source_url``: the human-readable page on e-sbirka.gov.cz.
"""

from __future__ import annotations

import html as _html
import re
from typing import Any

# RDF vocabulary (slovnik.gov.cz) - kept as a literal Unicode string; httpx percent-encodes it.
VOCAB = "https://slovník.gov.cz/datový/sbírka/pojem/"

# Host that mints the ELI act IRIs (the SPARQL data graph).
OPENDATA_IRI_BASE = "https://opendata.eselpoint.gov.cz/esel-esb"
# Human-readable portal.
PORTAL_BASE = "https://e-sbirka.gov.cz"


def act_iri(year: int, number: int) -> str:
    """Build the act's national ELI IRI from year + number (Sbirka zakonu collection)."""
    return f"{OPENDATA_IRI_BASE}/eli/cz/sb/{year}/{number}"


def source_url_for(act_uri: str) -> str:
    """Map an act IRI to its e-sbirka.gov.cz portal page."""
    if "/esel-esb/" in act_uri:
        eli_path = act_uri.split("/esel-esb/", 1)[-1]
        return f"{PORTAL_BASE}/{eli_path}"
    return PORTAL_BASE


def version_date(version_uri: str | None) -> str | None:
    """Extract the consolidation date from a version IRI like '.../2019/110/2025-08-01'."""
    if not version_uri:
        return None
    tail = version_uri.rstrip("/").rsplit("/", 1)[-1]
    return tail if re.fullmatch(r"\d{4}-\d{2}-\d{2}", tail) else None


def clean_html(text: str) -> str:
    """Strip the HTML markup e-Sbirka embeds in fragment text and decode entities."""
    text = re.sub(r"</?var>", "", text)
    text = re.sub(r'<a[^>]*>([^<]*)</a>', r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = _html.unescape(text)
    return text.strip()


def assemble_text(fragment_bindings: list[dict[str, Any]]) -> str:
    """Join ordered fragment bindings (SPARQL JSON rows) into clean plain text.

    Each binding is expected to have a ``text`` key (SPARQL value object). Rows must already be
    ordered by the SPARQL query (``ORDER BY ?order``).
    """
    parts: list[str] = []
    for row in fragment_bindings:
        raw = (row.get("text") or {}).get("value") or ""
        cleaned = clean_html(raw)
        if cleaned:
            parts.append(cleaned)
    return "\n".join(parts)


def _b(binding: dict[str, Any], key: str) -> str | None:
    obj = binding.get(key)
    if obj and obj.get("value"):
        return str(obj["value"])
    return None


def build_act_record(
    binding: dict[str, Any], *, year: int | None = None, number: int | None = None
) -> dict[str, Any]:
    """Build a citation-bearing record from a SPARQL binding row of act metadata.

    The binding may carry: ``act``, ``citation``, ``year``, ``number``, ``ver`` (latest version).
    """
    act_uri = _b(binding, "act")
    citation = _b(binding, "citation")
    by = _b(binding, "year")
    bn = _b(binding, "number")
    ver = _b(binding, "ver")

    year = year if year is not None else (int(by) if by and by.isdigit() else None)
    number = number if number is not None else (int(bn) if bn and bn.isdigit() else None)

    if not act_uri and year is not None and number is not None:
        act_uri = act_iri(year, number)

    return {
        "year": year,
        "number": number,
        "citation": citation,
        "eli_uri": act_uri,
        "human_readable_citation": citation,
        "source_url": source_url_for(act_uri) if act_uri else PORTAL_BASE,
        "latest_version_uri": ver,
        "version_date": version_date(ver),
    }
