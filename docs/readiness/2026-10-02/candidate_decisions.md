# Minimal decision packet: sandbox canary

## Cloud handoff scope update

The current resumed task permits offline repair, grouped source-backed curation,
tests and PR8 review. It excludes provider writes and credential creation or
transfer; the authentication instructions below describe a future operational
gate, not a request to provision access during this repair. A future labeled
sandbox cohort may duplicate historical test deposits, which remain delivery
evidence rather than authoritative metadata. Own-run retry idempotency and
production duplicate/DOI safeguards remain mandatory. The current inventory
guard is retained; no fresh-cohort bypass is implemented by this task.

Common FGDC transformations precede explicit source-ID/hash-bound correction
batches, overlap review and narrower residual groups. A successful synthetic
limit-ten upload test proves mocked selection/retry behavior only. Raw-source
license validation holds are not a reason to fabricate licenses or reinterpret
underlying dataset restrictions.

**No authentic candidate is currently configured for live execution under the explicit artifact contract, and sandbox authentication is unavailable here.** Final source-policy judgments are publication-readiness decisions, not a blanket prerequisite for every authorized nonpublishing sandbox transport test. A clearly labeled synthetic XML can separate transport validation from authentic-source QA. No substitutes or real sources have been uploaded.

## Exact source evidence

| Source | Exact raw use constraints | Primary date | Metadata date |
|---|---|---|---|
| FGDC-767 | Data not intended for site specific purposes | 1980-1982 | 20020430 |
| FGDC-832 | Unknown | 1995 | 20020502 |
| FGDC-854 | None, request that USGS be noted as data source. | 1978-1986 | 20020502 |

Full raw origin names:

- **767:** Palmer Field Office, U.S. Natural Resource Conservation Service formerly Soil Conservation Service.
- **832:** Alaska Department of Fish and Game (ADF&G), Division of Commercial Fisheries, Management and Development Division.
- **854:** National Aeronautics and Space Administration (NASA).

Access text for 767 says reports/maps/databases are available by request to the Palmer field office. For 832 and 854 it says non-restricted data is available on request at a cost depending on complexity/quantity. These statements describe the underlying data; they do not establish an XML license. No metadata-contact organization was found in the inspected contact fields.

Pinned source lines: [767](https://github.com/Br-Johnson/pices_metadata_transformer/blob/894fd00a92ff39f3b201d861d0e95ecfac20227f/FGDC/FGDC-767.xml#L5), [832](https://github.com/Br-Johnson/pices_metadata_transformer/blob/894fd00a92ff39f3b201d861d0e95ecfac20227f/FGDC/FGDC-832.xml#L5), [854](https://github.com/Br-Johnson/pices_metadata_transformer/blob/894fd00a92ff39f3b201d861d0e95ecfac20227f/FGDC/FGDC-854.xml#L5). Exact hashes and access text are in [decision JSON](candidate_decisions.json).

## What evidence resolves without Brett

We can preserve untouched original bytes and identities; identify these as descriptive XML rather than underlying research data; retain the source institutions intact; and distinguish the primary date from `metd`. NASA splitting is fixed with a regression. The [RFQ](../../rfq.txt) describes migrating the archived metadata catalogue into the PICES Zenodo collection, corroborating the project purpose. It supplies no explicit reusable XML license or metadata-artifact authorship/date rule. This is a bounded inspection of repository evidence, not a complete review of project communications or legal rights.

## Resolved by delegated source-backed preparation

Brett delegated routine curation and record-level QA to agents. No broad questionnaire or human-per-record approval is required. The prepared technical drafts use:

- One original XML metadata artifact, resource `other`, searchable `metadata_only`, no underlying research data.
- Exact source `metd` mapped to 2002-04-30 / 2002-05-02 / 2002-05-02, explicitly labeled as source metadata dates. The research dates/ranges remain in original XML and provenance.
- The three full institutional names intact as imported source attribution, with a note that independent metadata-artifact authorship has not been established.
- No assigned license; restricted access and explicit sandbox technical-test identity. No community submission or publication approval.

All three preparations pass current metadata/artifact validation offline. Their conservative technical mappings do not resolve XML publication rights or convert a metadata maintenance date into an underlying research publication date. Only genuinely unresolved consequential publication rights/scope requires authoritative evidence; a documented collection-level grant may cover multiple records. Agent QA must preserve that hold unless the evidence supports release.

Run `python docs/readiness/2026-10-02/prepare_canaries.py --output-dir NEW_LOCAL_WORKSPACE` from repo root to reproduce the three technical payloads plus one synthetic fixture without service access. The output is a new isolated sandbox workspace; originals stay untouched. The manifest records hashes and zero remote operations, and marks live eligibility false because authentication and current duplicate inventory are absent.

Duplicate/source-alias adjudication is an operational agent-review check supported by evidence, not a request for Brett to manually compare every record. Unavailable AquaDocs inventory remains unavailable, not checked-no-match. Record-level agent QA and separate publication release are documented in the [QA runbook](../../draft_qa_runbook.md).

## Transport-only alternative

**Recommendation:** first test one newly authored, unmistakably `[SYNTHETIC TEST ONLY]` XML draft while the source-policy evidence is settled. This can validate real authentication, file transfer, exact readback, same-ID retry and unchanged rerun. It cannot validate real-source rights, dates, authorship, transformations or duplicate clearance. The prepared fixture uses fictional content and an explicit fixture identity, actual UTC creation-date provenance, a clearly fictional creator and no assigned license (restricted technical draft). The existing repository synthetic example is a shape/offline fixture, not an approved real deposit; do not reuse its fictional institution/date as authentic evidence.

A synthetic draft is a defensible transport-only option under the already authorized staged testing scope; no repeated production-QA approval should be imposed on that test. It has not been uploaded or substituted for the authentic canary. Draft-only; no publication or community submission. The delegated current instruction holds live mutations while the actual gates are clarified.

## Authentication

Sandbox URL: **https://sandbox.zenodo.org/**. No authenticated Zenodo connector or sandbox browser session is exposed to this execution environment. Whether Brett is already logged into sandbox elsewhere is unknown; a production login does not establish sandbox access. Smallest user step: sign into the separate sandbox account in an authorized browser session. Then establish a supported secure execution connection; browser login alone is not assumed to give the Python process API access. Do not paste credentials or tokens into chat. No credential values have been read.

Engineering is implemented and mock-tested; see the [artifact contract](../../artifact_contract.md). PR8 remains unmerged. All live operations remain held at present. The immediate execution blocker is authenticated sandbox access; a fresh scoped duplicate check is also required before draft creation. Agent source-policy QA is separately required before authentic publication. The current upload service requires complete validated metadata and reviewed artifact evidence even for sandbox; these are implementation gates, not a statement that final production QA is an API prerequisite for creating a draft. API draft creation itself accepts an empty object. A synthetic fixture satisfies the current transport path without inventing authentic-source rights, dates or creators.
