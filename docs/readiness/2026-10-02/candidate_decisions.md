# Decision packet: three technical candidates

These are schema passes, not approved uploads. The proposed deposited object for each is the **original descriptive FGDC XML**, classified `metadata_only` with resource type `other`. No underlying observations, database, soil survey maps or photographs would be deposited.

| Source | Raw publication date | Raw metadata date | Exact raw use constraints |
|---|---|---|---|
| FGDC-767 | 1980-1982 | 20020430 | Data not intended for site specific purposes |
| FGDC-832 | 1995 | 20020502 | Unknown |
| FGDC-854 | 1978-1986 | 20020502 | None, request that USGS be noted as data source. |

## Required human decisions

1. Confirm the archival object and whether a separate metadata-artifact DOI is appropriate.
2. Supply permission, license and access evidence for redistribution of the **XML itself**. A collection-wide authorization may cover these records if documented and applicable; no need to invent individual grants.
3. Choose the date meaning and exact value for the artifact. `1980-1982` and `1978-1986` are ranges; `1995` has year precision. The metadata dates shown above are leads for a source-metadata-date policy, not automatically approved values. Do not present a coverage start as an established publication day.
4. Decide creator roles for the metadata artifact; the raw origin names describe source institutions, not necessarily authors of this archival object.
5. Review existing-record and cross-repository disposition. Unknown or unavailable external inventory requires explicit adjudication, not a no-match claim.

Exact names:

- FGDC-767: Palmer Field Office, U.S. Natural Resource Conservation Service formerly Soil Conservation Service.
- FGDC-832: Alaska Department of Fish and Game (ADF&G), Division of Commercial Fisheries, Management and Development Division.
- FGDC-854: National Aeronautics and Space Administration (NASA). The baseline audit exposed splitting of this name; the current change preserves it as one organization, with a regression test.

## Engineering versus policy

Engineering now supplies opt-in immutable XML attachment, source/file/policy hash binding, metadata-only export, exact draft file/metadata readback, same-ID retry, QA invalidation on changes, and environment-safe bucket transfer. These have offline mock coverage. Legacy records are not automatically reclassified or given attachments. No licenses or dates are assigned by artifact activation.

Still needed operationally: authenticated sandbox access through a secure authorized session; live validation of the service contract on at most three approved draft candidates. No token values were read, no live records changed, and no community submission or publication is part of the canary. See [exact evidence](candidate_decisions.json) and [artifact contract](../../artifact_contract.md).
