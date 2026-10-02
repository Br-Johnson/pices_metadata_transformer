# Source audit and sandbox canary gate — 2026-10-02

Initial transformation audit revision: `e85caaef8db418c6b4328122ec9fe83eea86aa75`. The saved JSON was rerun after the scoped NASA creator fix and identifies the exact transformer bytes with `transformer_sha256`. Twenty deliberately stratified original sources, including all five historical production imports. This is an offline strict-parser/build/validation audit, not a random sample, live-service test, or human publication approval. The public-to-source associations remain evidence-based associations, not proven upload provenance. No source edits or network operations.

Reproduce from repository root: `python docs/readiness/2026-10-02/audit_sources.py`. The script blocks socket connections and writes the two evidence JSON files beside itself. Dependencies are the project dependencies.

Compared primary title, origin, publication date, abstract, use constraints, and metadata date directly with raw XML; recorded source SHA-256, transformation status, date/creators/license/access/keywords, whitespace-normalized abstract fidelity, original XML in notes, and proposed XML file role. Substantive abstract comparisons normalize whitespace: a literal substring mismatch alone is not content loss.

## Results

| Source | Raw primary date | Verdict |
|---|---|---|
| FGDC-2057 | 122003 | transformation_hold |
| FGDC-2043 | 122003 | transformation_hold |
| FGDC-2725 | 19810101 | validation_hold |
| FGDC-1238 | 1990 | validation_hold |
| FGDC-2731 | 1988 - Present | transformation_hold |
| FGDC-120 | Unknown | transformation_hold |
| FGDC-122 | Unknown | transformation_hold |
| FGDC-1773 | September 2001 | transformation_hold |
| FGDC-1752 | October 2001 | transformation_hold |
| FGDC-1007 | 72-88  thru  87-98 | transformation_hold |
| FGDC-767 | 1980-1982 | offline_contract_pass |
| FGDC-832 | 1995 | offline_contract_pass |
| FGDC-854 | 1978-1986 | offline_contract_pass |
| FGDC-1220 | 20030501 | validation_hold |
| FGDC-1334 | absent | validation_hold |
| FGDC-2920 | 122003 | transformation_hold |
| FGDC-3148 | 122003 | transformation_hold |
| FGDC-633 | 199207-099301 | transformation_hold |
| FGDC-3373 | not parsed | raw_xml_parse_hold |
| FGDC-21 | not parsed | raw_xml_parse_hold |

11 transformation holds; four validation holds; three technical passes; two raw XML parse holds. All seven sources reaching validation preserve primary titles, substantive abstracts after whitespace normalization, and original XML in notes. No field-fidelity mismatch was found in these seven bounded checks. Held sources have no valid output to approve.

## Concrete findings

- FGDC-2057 and FGDC-2043: raw `122003` is held. Cited 1994/1977 and metadata date 2004 are different concepts; neither silently replaces the primary date.
- FGDC-2725 and FGDC-1238: the entire NOAA/OAR/PMEL organizational name is preserved as one organization, rather than split into people. Rights remain unresolved; validation blocks open access without a license.
- FGDC-1334: primary publication date is absent. The builder accepts metadata date as fallback; this is a technical behavior requiring a human deposited-object/date decision, not proof of the underlying publication date.
- FGDC-767 and FGDC-854: range dates become the first year under current normalization. They pass the schema but need semantic date QA; keep the original range as evidence.
- FGDC-2920 and FGDC-3148: byte-identical XML. The full byte scan found 228 copy groups (456 files), 3,978 unique raw contents among 4,206 files. Preserve all aliases and sources. Exact XML equality does not establish external work/version equivalence or authorize automatic deletion.
- FGDC-3373 and FGDC-21 fail strict raw parsing. Transformer recovery paths are outside this audit; no repaired source is represented as original.

## Live canary disposition

**Zero sources are currently approved for remote writes.** The three technical candidates are FGDC-767, FGDC-832, FGDC-854. Their restricted access permits technical validation without a license; it does not establish permission to redistribute the XML or underlying material. Negative date, license, parse and duplicate cases stay offline.

Required decisions before any positive canary:

1. Identify the deposited object: original descriptive XML artifact versus underlying research data; approve resource type, creator roles, and the date meaning. A metadata-artifact DOI must not be presented as the DOI of a cited research work.
2. Record source-specific permission/license and access decision for that actual artifact. “None”, “Contact Source”, and restricted access are not blanket grants.
3. Approve source aliases and existing-record disposition; preserve the five production IDs/DOIs. External AquaDocs inventory remains unchecked/unavailable, not checked-no-match.
4. Exercise the new opt-in original XML artifact contract against authenticated sandbox readback after the human object/rights/date decisions. Offline attachment, retry, readback and stale approval regressions now pass; no live compatibility claim is made. Do not use a dummy placeholder to bypass the file requirement.
5. Provide authenticated sandbox access through an authorized secure session. This execution environment exposes no authenticated Zenodo connector/session. No token values were read.

After these gates: at most three approved sandbox draft creates, exact file/metadata readback and unchanged rerun; record IDs, environment, source/metadata/file hashes, before/after results. No publication or community submission. Report evidence before expanding. Production remains a separate environment and draft-until-human-QA.

## Draft API compatibility correction

The API documentation describes `inprogress` with `submitted:false` as an editable draft. Shared response validation now accepts that documented state, retaining the prior `unsubmitted` representation. `inprogress` with submitted true is blocked. An offline mock regression verifies the eligible draft and the submitted-state rejection. No real publication was attempted.

Official references: [API and sandbox](https://developers.zenodo.org/), [file requirement](https://support.zenodo.org/help/en-gb/1-upload-deposit/36-do-you-support-metadata-only-records). Evidence: [sample JSON](representative_spotcheck.json), [exact-copy groups](exact_source_copy_groups.json).

## Subsequent scoped engineering checkpoint

The opt-in original XML artifact contract is implemented; see [contract and activation](../../artifact_contract.md). Source/file/policy/role evidence is bound through metadata and the environment ledger/QA manifest. The candidate review found NASA being split into two personal creators; a regression now preserves the full organizational name. The sample was rerun, preserving the 11/4/3/2 technical-status counts. All candidate source-policy decisions remain pending; see [decision packet](candidate_decisions.md).
