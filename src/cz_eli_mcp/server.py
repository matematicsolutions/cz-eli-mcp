"""FastMCP entry point - Czech e-Sbirka (SPARQL) tools.

Run:

    python -m cz_eli_mcp.server

Configuration via env:

- ``CZ_ELI_CACHE_DIR`` (default ``~/.matematic/cache/cz-eli``)
- ``CZ_ELI_AUDIT_DIR`` (default ``~/.matematic/audit``)
- ``CZ_ELI_ENDPOINT`` (default ``https://opendata.eselpoint.gov.cz/sparql``)
"""

from __future__ import annotations

import os

import httpx
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .audit import AuditLogger, hash_input, timer
from .citations import assemble_text, build_act_record
from .client import DEFAULT_ENDPOINT, CzSparqlClient
from .models import Act, LawText, SearchHit, SearchResult

INSTRUCTIONS = """\
This MCP server exposes the Czech e-Sbirka legal database (e-sbirka.gov.cz), the official Collection of Laws (Sbirka zakonu), via its open-data SPARQL endpoint. It searches acts and returns their metadata and full consolidated text. Every response carries a stable `eli_uri`, a `human_readable_citation` and a `source_url` (the citation contract).

## Call order

1. `cz_search` - find acts by `year` and/or a `contains` substring matched against the citation (e.g. `year=2019`, `contains="110"`). Returns hits with `eli_uri`, `citation` and `source_url`. This is the discovery step - use it to find the `year` + `number` of an act.
2. `cz_get_act` - metadata for an act by `year` + `number` (e.g. 2019 / 110): citation, the latest consolidated `version_date`, `eli_uri`.
3. `cz_get_text` - the full consolidated text of an act by `year` + `number`, assembled from the latest version's ordered fragments.

## Hard constraints

- **ELI is national, not data.europa.eu** - `eli_uri` is the Czech ELI IRI minted by the e-Sbirka graph (`opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/{year}/{number}`). It follows the ELI URI template but is not a `data.europa.eu`-resolvable identifier; the readable page is on `e-sbirka.gov.cz`. Relay the `eli_note`. Do not invent it - it is built from year + number and confirmed against the act's RDF citation.
- **Text is assembled, not a single file** - `cz_get_text` reconstructs the consolidated text from ordered HTML fragments; there is no official single XML/PDF manifestation. Relay the `dataset_note`.
- **Search matches the citation, not full text** - `contains` filters the citation string (e.g. "110/2019 Sb."), not the body of the law.
- **Every response has `human_readable_citation` + `source_url`** - cite both to the user.
- **Audit log JSONL** - every tool call appends to `~/.matematic/audit/cz-eli-mcp.jsonl`.

## Error iteration

Tools return a structured error with a `[code]` prefix:
- `invalid_arg` - a parameter is missing or invalid (e.g. bad year, non-positive number, limit out of range).
- `not_found` - no act exists for that year / number, or it has no consolidated version.
- `upstream_error` - a SPARQL endpoint error (HTTP, timeout, malformed JSON). Retry once before surfacing.

## Response style

- Cite as `human_readable_citation` with the ELI URL: "110/2019 Sb., https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/2019/110".
- NEVER invent an ELI, a citation, a number or a year - take each from the tool output.
"""


class ToolError(Exception):
    """Structured error for cz-eli MCP tools - visible to the LLM with a [code] prefix."""

    VALID_CODES = frozenset({"invalid_arg", "not_found", "upstream_error"})

    def __init__(self, code: str, message: str):
        if code not in self.VALID_CODES:
            raise ValueError(f"Unknown ToolError code: {code}. Valid: {sorted(self.VALID_CODES)}")
        self.code = code
        super().__init__(f"[{code}] {message}")


READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    idempotentHint=True,
    destructiveHint=False,
    openWorldHint=True,
)

mcp: FastMCP = FastMCP(name="cz-eli-mcp", instructions=INSTRUCTIONS)


def _endpoint() -> str:
    return os.environ.get("CZ_ELI_ENDPOINT", DEFAULT_ENDPOINT).rstrip("/")


def _audit() -> AuditLogger:
    return AuditLogger()


def _map_upstream(exc: Exception) -> Exception:
    if isinstance(exc, (httpx.HTTPStatusError, httpx.TransportError, httpx.TimeoutException)):
        return ToolError("upstream_error", f"e-Sbirka SPARQL error: {type(exc).__name__}: {exc}")
    if isinstance(exc, (KeyError, ValueError)):
        return ToolError("upstream_error", f"Malformed SPARQL response: {type(exc).__name__}: {exc}")
    return exc


def _check_year(year: int) -> None:
    if not 1500 <= year <= 2100:
        raise ToolError("invalid_arg", f"year={year} is out of range (1500..2100).")


def _check_number(number: int) -> None:
    if number <= 0:
        raise ToolError("invalid_arg", f"number={number} must be positive.")


# ---------------------------------------------------------------------------
# cz_search
# ---------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def cz_search(
    year: int | None = None, contains: str | None = None, limit: int = 50, offset: int = 0
) -> SearchResult:
    """Search Czech acts by year and/or a citation substring.

    Args:
        year: restrict to a publication year, e.g. ``2019``.
        contains: substring matched (case-insensitive) against the citation, e.g. ``"110"``.
        limit: max hits (1..500, default 50).
        offset: pagination offset (default 0).

    Returns:
        ``SearchResult`` with ``items: list[SearchHit]``, each carrying the citation contract.
    """
    audit = _audit()
    if year is not None:
        _check_year(year)
    if not 1 <= limit <= 500:
        raise ToolError("invalid_arg", "limit must be between 1 and 500.")
    if offset < 0:
        raise ToolError("invalid_arg", "offset must be >= 0.")
    input_hash = hash_input({"year": year, "contains": contains, "limit": limit, "offset": offset})

    with timer() as t:
        try:
            async with CzSparqlClient(endpoint=_endpoint()) as client:
                rows = await client.search(year=year, contains=contains, limit=limit, offset=offset)
        except Exception as exc:
            audit.log(tool="cz_search", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error=f"{type(exc).__name__}: {exc}")
            raise _map_upstream(exc) from exc

    items = []
    for row in rows:
        rec = build_act_record(row)
        items.append(SearchHit(
            year=rec["year"], number=rec["number"], citation=rec["citation"],
            eli_uri=rec["eli_uri"], human_readable_citation=rec["human_readable_citation"],
            source_url=rec["source_url"],
        ))
    result = SearchResult(total=len(items), items=items)
    audit.log(tool="cz_search", input_hash=input_hash, output_count_or_size=len(items),
              duration_ms=t.duration_ms, status="ok")
    return result


# ---------------------------------------------------------------------------
# cz_get_act
# ---------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def cz_get_act(year: int, number: int) -> Act:
    """Fetch Czech act metadata by year and number.

    Args:
        year: e.g. ``2019``.
        number: e.g. ``110``.

    Returns:
        ``Act`` with ``eli_uri``, ``human_readable_citation``, ``source_url`` and the latest
        consolidated ``version_date``.
    """
    audit = _audit()
    _check_year(year)
    _check_number(number)
    input_hash = hash_input({"year": year, "number": number})

    with timer() as t:
        try:
            async with CzSparqlClient(endpoint=_endpoint()) as client:
                rows = await client.get_act_meta(year, number)
        except Exception as exc:
            audit.log(tool="cz_get_act", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error=f"{type(exc).__name__}: {exc}")
            raise _map_upstream(exc) from exc

    if not rows:
        raise ToolError("not_found", f"No act {number}/{year} in e-Sbirka.")
    act = Act.model_validate(build_act_record(rows[0], year=year, number=number))
    audit.log(tool="cz_get_act", input_hash=input_hash, output_count_or_size=1,
              duration_ms=t.duration_ms, status="ok")
    return act


# ---------------------------------------------------------------------------
# cz_get_text
# ---------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def cz_get_text(year: int, number: int) -> LawText:
    """Fetch the full consolidated text of a Czech act by year and number.

    The text is assembled from the latest consolidated version's ordered HTML fragments.

    Args:
        year: e.g. ``2019``.
        number: e.g. ``110``.

    Returns:
        ``LawText`` with the citation contract and ``content`` (plain text).
    """
    audit = _audit()
    _check_year(year)
    _check_number(number)
    input_hash = hash_input({"year": year, "number": number})

    with timer() as t:
        try:
            async with CzSparqlClient(endpoint=_endpoint()) as client:
                meta_rows = await client.get_act_meta(year, number)
                if not meta_rows:
                    raise ToolError("not_found", f"No act {number}/{year} in e-Sbirka.")
                rec = build_act_record(meta_rows[0], year=year, number=number)
                version_uri = rec.get("latest_version_uri")
                if not version_uri:
                    raise ToolError("not_found", f"Act {number}/{year} has no consolidated version.")
                frags = await client.get_text_fragments(version_uri)
        except ToolError:
            audit.log(tool="cz_get_text", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error="not_found")
            raise
        except Exception as exc:
            audit.log(tool="cz_get_text", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error=f"{type(exc).__name__}: {exc}")
            raise _map_upstream(exc) from exc

    text = assemble_text(frags)
    if not text:
        raise ToolError("not_found", f"Act {number}/{year} returned no text fragments.")
    result = LawText(
        year=rec["year"],
        number=rec["number"],
        citation=rec["citation"],
        version_date=rec["version_date"],
        eli_uri=rec["eli_uri"],
        human_readable_citation=rec["human_readable_citation"],
        source_url=rec["source_url"],
        content=text,
        byte_size=len(text.encode("utf-8")),
        fragment_count=len(frags),
    )
    audit.log(tool="cz_get_text", input_hash=input_hash, output_count_or_size=result.byte_size or 0,
              duration_ms=t.duration_ms, status="ok")
    return result


def main() -> None:
    """Run the MCP server over stdio (default for Claude Code)."""
    mcp.run()


if __name__ == "__main__":
    main()
