# DISCOVERY - cz-eli-mcp (Czechia / e-Sbirka)

Date: 2026-06-29. Source selection driven by Legal Data Hunter coverage data
(`worldwidelaw/legal-sources`): Czechia is a `has_consolidated_codes` jurisdiction whose
`preferred_legislation_source` is `CZ/eSbirka`, served over a clean, keyless SPARQL endpoint.
Confirmed by live probes below.

## Why Czechia, why this way

The earlier `eu-legal-mcp` sweep rejected CZ as "308 / SPA" - that was the **web portal**
(`www.e-sbirka.cz`), not the **open-data SPARQL endpoint**. The LDH crawler config pointed at
`opendata.eselpoint.gov.cz/sparql`, and live probes confirm a clean RDF source: ~92k acts,
CC BY 4.0, updated daily.

## Endpoint (keyless, CC BY 4.0)

- SPARQL: `https://opendata.eselpoint.gov.cz/sparql` - GET with `query=...` + `default-graph-uri=`,
  `Accept: application/json` -> SPARQL JSON results.
- TLS verifies normally (the LDH config sets `ssl_verify: false`; not needed - we keep verification on).
- RDF vocabulary prefix: `https://slovník.gov.cz/datový/sbírka/pojem/` (the predicate IRIs carry
  Czech diacritics; httpx percent-encodes them).

## RDF shape

- Act subject IRI: `https://opendata.eselpoint.gov.cz/esel-esb/eli/cz/sb/{year}/{number}` -
  an **ELI-template IRI** (cz = jurisdiction, sb = Sbirka zakonu). This is `eli_uri`.
- `a <vocab>právní-akt>` ; `<vocab>citace-právního-aktu>` (e.g. "110/2019 Sb.") ;
  `<vocab>rok-předpisu>` (xsd:gYear) ; `<vocab>číslo-předpisu>` (xsd:string).
- `<vocab>má-poslední-znění>` -> latest version IRI, e.g. `.../2019/110/2025-08-01` (the tail is
  the consolidation date = `version_date`).
- Version -> `<vocab>má-fragment-znění>` -> `<vocab>obsahuje-fragment>` -> `<vocab>text-fragmentu>`,
  ordered by `<vocab>pořadí-fragmentu-znění-právního-aktu>`. Fragments carry HTML markup (e.g.
  `<var>ČÁST PRVNÍ</var>`, `<a class="ext_odkaz">`), stripped on assembly.

Example probed: act 110/2019 Sb. (data protection) -> version `.../2025-08-01`, 641 fragments.

## Citation contract (Art. 4)

- `eli_uri` = the national ELI IRI (built from year + number, confirmed against the RDF citation).
- `human_readable_citation` = the Czech official citation, e.g. "110/2019 Sb.".
- `source_url` = `https://e-sbirka.gov.cz/eli/cz/sb/{year}/{number}` (the readable portal page).
- `eli_note` flags that the IRI is national, not `data.europa.eu`-resolvable.

## Tools (MVP)

- `cz_search(year?, contains?, limit, offset)` - discovery; filters on year and/or the citation
  substring (not the body of the law).
- `cz_get_act(year, number)` - metadata + latest `version_date`. The IRI is built directly, so no
  scan is needed.
- `cz_get_text(year, number)` - consolidated text assembled from the latest version's fragments.

## Deficiencies flagged (per WM's "some connectors may be deficient" steer)

- **National ELI, not European** - IRI follows the ELI template but is not on `data.europa.eu`.
- **Assembled text** - reconstructed from HTML fragments, not a verbatim single file.
- **Citation-only search** - `cz_search` matches the citation string, not the full body.

## Deferred

- **Case law / ECLI** - NSS, Constitutional Court (separate sources; feature 002 candidate).
- **Body full-text search** - heavy over SPARQL; out of MVP scope.
- **Sbirka mezinarodnich smluv** (international treaties) and other collections beyond `sb`.

## Licence / re-use

e-Sbirka open data is CC BY 4.0 (Czech Ministry of the Interior). Read-only SPARQL relay with
attribution + `source_url`. No key, no ToS gate. Distribution as a public connector is in line
with the keyless tier.
