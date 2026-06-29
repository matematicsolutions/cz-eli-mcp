"""Async httpx client for the Czech e-Sbirka SPARQL endpoint with cache.

The endpoint (opendata.eselpoint.gov.cz/sparql) is keyless, returns SPARQL JSON results, and
its TLS certificate verifies normally (the LDH crawler config disables verification, but it is
not needed). We keep our own backoff + cache.
"""

from __future__ import annotations

import json
from typing import Any

import anyio
import httpx

from .cache import HttpCache
from .citations import VOCAB, act_iri

DEFAULT_ENDPOINT = "https://opendata.eselpoint.gov.cz/sparql"
DEFAULT_TIMEOUT = httpx.Timeout(180.0, connect=15.0)
USER_AGENT = "cz-eli-mcp/0.1.0 (+https://github.com/matematicsolutions/cz-eli-mcp)"

_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 3


def _escape_literal(value: str) -> str:
    """Escape a value for safe inclusion inside a SPARQL string literal."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")


class CzSparqlClient:
    """Async SPARQL client. Use as ``async with CzSparqlClient() as c: ...``."""

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        cache: HttpCache | None = None,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
    ) -> None:
        self.endpoint = endpoint
        self._cache = cache or HttpCache()
        self._http = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )

    async def __aenter__(self) -> CzSparqlClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()
        self._cache.close()

    async def _select(self, query: str, *, category: str) -> list[dict[str, Any]]:
        cache_key = f"{self.endpoint}?{category}:{query}"
        cached = self._cache.get(cache_key)
        if cached is not None and isinstance(cached, str):
            return json.loads(cached)["results"]["bindings"]
        params = {"default-graph-uri": "", "query": query}
        last_exc: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                resp = await self._http.get(self.endpoint, params=params)
                resp.raise_for_status()
                self._cache.set(cache_key, resp.text, ttl=HttpCache.ttl_for(category))
                return json.loads(resp.text)["results"]["bindings"]
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code not in _RETRY_STATUS or attempt == _MAX_ATTEMPTS - 1:
                    raise
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt == _MAX_ATTEMPTS - 1:
                    raise
            await anyio.sleep(0.5 * (2**attempt))
        assert last_exc is not None
        raise last_exc

    async def get_act_meta(self, year: int, number: int) -> list[dict[str, Any]]:
        """Metadata for one act by year + number (citation, year, number, latest version)."""
        iri = act_iri(year, number)
        query = f"""
SELECT ?act ?citation ?year ?number ?ver WHERE {{
  BIND(<{iri}> AS ?act)
  ?act <{VOCAB}citace-právního-aktu> ?citation ;
       <{VOCAB}rok-předpisu> ?year ;
       <{VOCAB}číslo-předpisu> ?number .
  OPTIONAL {{ ?act <{VOCAB}má-poslední-znění> ?ver . }}
}} LIMIT 1
"""
        return await self._select(query, category="act")

    async def get_text_fragments(self, version_uri: str) -> list[dict[str, Any]]:
        """Ordered text fragments of a version (consolidated full text)."""
        query = f"""
SELECT ?text ?order WHERE {{
  <{version_uri}> <{VOCAB}má-fragment-znění> ?frag .
  ?frag <{VOCAB}obsahuje-fragment> ?innerFrag .
  ?frag <{VOCAB}pořadí-fragmentu-znění-právního-aktu> ?order .
  ?innerFrag <{VOCAB}text-fragmentu> ?text .
}}
ORDER BY ?order
"""
        return await self._select(query, category="act")

    async def search(
        self,
        year: int | None = None,
        contains: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List acts, optionally filtered by year and/or a citation substring."""
        filters = ""
        if year is not None:
            filters += f'  FILTER(STR(?year) = "{int(year)}")\n'
        if contains:
            esc = _escape_literal(contains)
            filters += f'  FILTER(CONTAINS(LCASE(STR(?citation)), LCASE("{esc}")))\n'
        query = f"""
SELECT ?act ?citation ?year ?number WHERE {{
  ?act a <{VOCAB}právní-akt> ;
       <{VOCAB}citace-právního-aktu> ?citation ;
       <{VOCAB}rok-předpisu> ?year ;
       <{VOCAB}číslo-předpisu> ?number .
{filters}}}
ORDER BY DESC(?year) DESC(?number)
OFFSET {int(offset)} LIMIT {int(limit)}
"""
        return await self._select(query, category="search")
