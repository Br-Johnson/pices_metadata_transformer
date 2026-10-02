# Offline collection classification and independent source audit

This is source-only evidence, not remote record QA or release authority. All 4,206 original files were hashed without modification. The strict current original-XML artifact profile classified 4,200 as held and six as parse failures; none are publication-approved or remotely verified. Technical validation of actual prepared payloads, including original XML in notes, passed 4,089, held 105, and could not construct 12. Technical validity does not establish rights, creator identity, duplicate clearance or live compatibility.

There are 3,978 unique raw contents and 228 exact-copy groups involving 456 files. Preserve aliases; do not automatically delete or deposit each alias separately. Source rights text such as “None”, “Contact Source”, and authorization-dependent republication is not an explicit supported XML license. This narrow profile's zero supported records is not a legal determination that all sources are unusable.

## Reproduction and coverage

Run `python -m scripts.collection_qa --source-dir FGDC --output-dir /path/to/new/workspace --reviewed-at 2026-10-02T02:59:58Z`. The destination must be a separate derived workspace. The classifier copies original bytes, never uploads, and blocks socket connections in its CLI. Repeat the same timestamp to resume unchanged source/profile evidence. The full local report was byte-identical on a second run, SHA-256 `19755987bb15d9fbd36547e87191d0aa7b2b640e0ad90624388095e098c01e1f`.

`collection_summary.json` binds the rule profile and timestamp. `collection_classification.csv` records every source hash, status, technical result, exact-copy aliases and source strata; `collection_hold_codes.json` expands hold codes. The detailed reproducible report additionally retains raw source fields. No remote snapshots, upload ledgers or external absence evidence are invented.

Independent reviewer `review_fidelity` independently hashed all files and reproduced all six failures and exact-copy counts. Strict parse failures are FGDC-21, FGDC-3373, FGDC-3484, FGDC-4077, FGDC-4184 and FGDC-4185: four trailing-document errors and two invalid initial tokens.

## Independent risk-stratified semantic sample

| Sources | Risk and checked evidence |
| --- | --- |
| FGDC-1 | Compound personal origin “Sharon L. Smith and Peter V.Z. Lane”; acknowledgment terms do not establish a recognized XML license. |
| FGDC-100 | Full NOAA/NMFS/AFSC hierarchy preserved as one organization; rights “None” held. |
| FGDC-1839 | Actual primary date `122003`; mixed council/person creator text. Artifact date `2004-07-23` comes from metadata date, not an inferred dataset publication date. |
| FGDC-1007 | Primary date `72-88 thru 87-98`; departmental authorization and request-based access require decisions. |
| FGDC-1334 | Empty primary publication date; metadata date `2003-07-03`; “Check with Contributor” held. |
| FGDC-2837, FGDC-3065 | Byte-identical Food Habits Database, mixed creators and “Read only” access; identity adjudication held. |
| FGDC-10 | Origin `83 Havelock St.` is an address, not established author identity; title exceeds 250 characters. |
| FGDC-21, FGDC-3373 | Independently reproduced trailing-document error and initial NUL bytes. |

Ten targeted samples cover consequential strata, not every record's semantics or a random sample. All-file coverage proves hashes, strict parsing and byte-copy identity only. Priorities are XML-specific rights decisions, compound/address creator adjudication, alias identity decisions and reversible parse recovery that preserves original bytes.

## Sandbox authentication boundary

Sandbox is https://sandbox.zenodo.org; production is https://zenodo.org. Official documentation requires separate sandbox registration and access tokens: https://developers.zenodo.org/#testing and https://developers.zenodo.org/#authentication. This execution environment exposes no Zenodo/browser connector, has no `agent-browser` CLI, and neither Zenodo token environment key is present. Only key presence was inspected; no credential values, secret files or cookies were read. Another browser's login state is unknown.

A phone can sign into the sandbox website, but that session does not authenticate the Mac's Python pipeline. Live testing needs an authorized accessible desktop browser session or a securely configured sandbox API connection. Draft-only API access should use `deposit:write`, without publication actions where supported. No credentials were generated or stored, no live canary ran, and no existing production or sandbox records were changed. Older accidental production imports are to be retained, corrected and reused; this audit authorizes no deletion or release.
