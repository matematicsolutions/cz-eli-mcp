"""Pydantic v2 models for the Czech e-Sbirka SPARQL API + cz-eli-mcp."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

DATASET_NOTE = (
    "e-Sbirka (the Czech Collection of Laws, Sbirka zakonu) is served as RDF via the "
    "opendata.eselpoint.gov.cz SPARQL endpoint (CC BY 4.0, ~92k acts, updated daily). Acts are "
    "addressed by year + number; the act IRI follows the ELI URI template "
    "(eli/cz/sb/{year}/{number}). cz_get_text returns the latest consolidated version's text, "
    "assembled from ordered HTML fragments - there is no single official XML/PDF file, so the "
    "text is reconstructed, not a verbatim document. Language: Czech."
)

ELI_NOTE = (
    "eli_uri is the Czech national ELI IRI minted by the e-Sbirka open-data graph "
    "(opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/...). It follows the ELI URI template but is "
    "not a data.europa.eu-resolvable identifier; the human-readable page is on e-sbirka.gov.cz."
)


class _Tolerant(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Act(_Tolerant):
    """A Czech legal act (from SPARQL metadata)."""

    year: int | None = None
    number: int | None = None
    citation: str | None = None
    latest_version_uri: str | None = None
    version_date: str | None = None

    # Citation contract (Art. 4 CONSTITUTION).
    eli_uri: str | None = None
    human_readable_citation: str | None = None
    source_url: str | None = None
    eli_note: str = ELI_NOTE
    dataset_note: str = DATASET_NOTE


class LawText(_Tolerant):
    """Result of ``cz_get_text`` (consolidated text assembled from fragments)."""

    year: int | None = None
    number: int | None = None
    citation: str | None = None
    version_date: str | None = None
    eli_uri: str | None = None
    human_readable_citation: str | None = None
    source_url: str | None = None
    format: str = "text/plain (assembled from consolidated HTML fragments)"
    content: str | None = None
    byte_size: int | None = None
    fragment_count: int | None = None
    eli_note: str = ELI_NOTE
    dataset_note: str = DATASET_NOTE


class SearchHit(_Tolerant):
    """A single act in a ``cz_search`` result."""

    year: int | None = None
    number: int | None = None
    citation: str | None = None
    eli_uri: str | None = None
    human_readable_citation: str | None = None
    source_url: str | None = None


class SearchResult(_Tolerant):
    """Result of ``cz_search``."""

    total: int
    items: list[SearchHit] = Field(default_factory=list)
    dataset_note: str = DATASET_NOTE
