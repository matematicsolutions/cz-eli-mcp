# cz-eli-mcp

<!-- mcp-name: io.github.matematicsolutions/cz-eli-mcp -->

An MCP server for the Czech **e-Sbirka** legal database (`e-sbirka.gov.cz`), the official
Collection of Laws (Sbirka zakonu), via its open-data **SPARQL** endpoint. It searches acts and
fetches their full consolidated text, with verifiable citations.

Part of the MateMatic `eu-legal-mcp` production line - after PL, DE, AT, ES, FI, IE, NL, SE, FR,
LU and DK. Same citation contract, e-Sbirka source. This is the first connector in the line that
talks **SPARQL/RDF** rather than a REST/XML API.

> **Scope.** This MVP searches acts (by year and/or a citation substring), returns metadata, and
> assembles the full consolidated text of the latest version. ~92,000 acts, updated daily,
> licensed CC BY 4.0. Language: Czech. Every response carries a `dataset_note`.
>
> **ELI is national, not data.europa.eu.** The act IRI follows the ELI URI template
> (`eli/cz/sb/{year}/{number}`) but is minted by the e-Sbirka open-data graph
> (`opendata.eselpoint.gov.cz`), not resolvable on `data.europa.eu`. The readable page is on
> `e-sbirka.gov.cz`. Every response carries an `eli_note` saying so.
>
> **Text is assembled, not a single file.** e-Sbirka exposes the consolidated text as ordered
> HTML fragments over SPARQL; `cz_get_text` reconstructs the plain text from them. There is no
> single official XML/PDF manifestation.

## The tools

| Tool | What it does |
|---|---|
| `cz_search` | Find acts by year and/or a citation substring (discovery). |
| `cz_get_act` | Metadata for an act by year + number, plus the latest consolidated version date. |
| `cz_get_text` | Full consolidated text of an act, assembled from the latest version's fragments. |

Every response carries the contract: `eli_uri` (the national ELI IRI, e.g.
`https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/2019/110`), `human_readable_citation`
(e.g. `110/2019 Sb.`), and `source_url` (the `e-sbirka.gov.cz` page).

## Install

Run it with no install step (once published to PyPI):

```bash
uvx cz-eli-mcp
```

Or from source:

```bash
cd cz-eli-mcp
pip install -e .
```

## Configure (Claude Code / any MCP client)

```json
{
  "mcpServers": {
    "cz-eli-mcp": { "command": "cz-eli-mcp" }
  }
}
```

Environment:

- `CZ_ELI_ENDPOINT` - default `https://opendata.eselpoint.gov.cz/sparql`
- `CZ_ELI_CACHE_DIR` - default `~/.matematic/cache/cz-eli`
- `CZ_ELI_AUDIT_DIR` - default `~/.matematic/audit`

No API key. The e-Sbirka open-data SPARQL endpoint is keyless.

## Governance

- **Public data only** - read-only SPARQL against e-Sbirka; no client data leaves the machine.
- **Audit log** - every tool call appends one JSON line to `~/.matematic/audit/cz-eli-mcp.jsonl`.
- **Vendor-neutral** - talks only to `opendata.eselpoint.gov.cz`; no LLM provider, no telemetry.
- **Verifiable citations** - every response is independently checkable via `source_url`.

See `CONSTITUTION.md` and `DISCOVERY.md`.

## Tests

```bash
pip install -e ".[dev]"
pytest tests/test_instructions_drift.py tests/test_parse.py -v   # offline
pytest tests/test_smoke.py -v                                    # hits the live SPARQL endpoint
```

## Licence

Apache-2.0. © Matematic Solutions / Wieslaw Mazur. e-Sbirka data is CC BY 4.0 (Czech Ministry of
the Interior); relayed with attribution and a `source_url`.
