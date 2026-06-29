# Constitution of cz-eli-mcp

Version: 0.1.0
Date: 2026-06-29
Licence: Apache-2.0

`cz-eli-mcp` is an MCP server for the Czech e-Sbirka legal database (`e-sbirka.gov.cz`), the
official Collection of Laws (Sbirka zakonu), via its open-data SPARQL endpoint. It searches acts
and fetches consolidated text with verifiable citations. Case law is not in this MVP.

The 4 principles below are inherited from the `eu-legal-mcp` line Constitution (Article IV).

---

## Art. 1. Public data only

The e-Sbirka open-data SPARQL endpoint (`opendata.eselpoint.gov.cz/sparql`) is the official,
public source of Czech legislation, published as open data (CC BY 4.0). The server is read-only
(SPARQL SELECT only) and sends nothing beyond the requested year / number / search filter.

## Art. 2. Mandatory audit log

Every tool call MUST append one JSON line to `~/.matematic/audit/cz-eli-mcp.jsonl`
(ts / tool / input_hash SHA-256 / output_count_or_size / duration_ms / status). Inability to write =
the tool returns an error, it does not silently skip.

## Art. 3. Vendor neutrality

No tool hardcodes an LLM provider, assumes a model, or adds commercial telemetry. The server talks
only to `opendata.eselpoint.gov.cz` and the local filesystem. Authentication: none; own backoff +
cache. TLS is verified normally (the LDH crawler config disables verification; it is not needed).

## Art. 4. ELI citations and a human-readable citation are mandatory

Every response MUST carry three fields:
- `eli_uri`: the act IRI, built from year + number and confirmed against the RDF citation
  (`opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/{year}/{number}`). NEVER invented. It is a Czech
  national ELI IRI following the ELI URI template, NOT a `data.europa.eu`-resolvable identifier -
  every response carries an `eli_note` stating this.
- `human_readable_citation`: the Czech official citation (e.g. "110/2019 Sb.").
- `source_url`: the human-readable page on `e-sbirka.gov.cz`.

---

## Open points

1. **National vs European ELI** - e-Sbirka mints ELI-template IRIs but they are not resolvable on
   `data.europa.eu`. Flagged via `eli_note` rather than hidden.
2. **Assembled text** - the consolidated text is reconstructed from ordered HTML fragments; there
   is no single official XML/PDF manifestation. Flagged via `dataset_note`.
3. **Full-text search** - `cz_search` matches the citation string, not the body of the law. A
   body full-text search over SPARQL is out of MVP scope.
4. **Case law** - Czech court decisions (NSS, Constitutional Court) are a later feature.

## Ewolucja konstytucji

Changes to art. 1-4 follow SEMVER + an entry in `CHANGELOG.md` + a `pyproject.toml` bump.

First version: 2026-06-29. Author: Wieslaw Mazur / MateMatic.
