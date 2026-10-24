# Reviewed clearing of the 37 held sources Brett decided on 2026-10-23

Date: 2026-10-23. Status: accepted for offline preparation; the members publish only after an
independent review approves the proposal and the bulk route runs. Extends
[ADR 0013](0013-bulk-draft-and-publication-route.md) and [ADR 0014](0014-v2-wire-and-in-place-update.md),
whose review, draft, release, publish and journal rules apply unchanged, and follows the
creators64 lane (`docs/readiness/2026-10-22/`) as its pattern.

## Context

45 sources were outside the published collection: 39 held by the QA rules and 6 malformed.
The evidence sheet [held_sources_evidence.md](../readiness/2026-10-22/held_sources_evidence.md)
put 14 questions to Brett; his answers are recorded in
[held_sources_decisions.json](../readiness/2026-10-23/held_sources_decisions.json). They clear
37 records: 22 access holds (A1, A2, A3), 10 creator holds (B1 to B4) and 5 metadata-date holds
(C1, C2). FGDC-909, 3850, 4185, 21, 4077 and 4184 stay held; FGDC-3373 and 3484 are retired.
A cleared hold is not a publication approval: each record still needs an AI accuracy review,
validation and the bulk route.

The holds come from three rules. `collection_qa` and `agent_qa` hold a metadata access text that
no pinned interpretation covers; `agent_qa` holds a citation origin that is a journal, an
instruction or empty; both hold a metadata date that is not an exact day. The modern mapper
(`scripts.modern_singleton`) admits only sources in a pinned reviewed policy, and its plan check
requires the frozen publication plan to call the source supported, which it does not for these 37.

A fresh classification of the 37 with the runbook manifest set (2026-10-20) raised exactly the
holds the sheet described, with one exception: FGDC-2817 has two blockers. Brett decided its
creators (B2), but its access text ("Check with Contributor" with the use text "Refer to
webstite URL: http://www.csa.com/") was not on the sheet and is not covered by the exact821
answer, which binds four identical fields.

## Decision

### Evidence the classification reads, one pinned file per concern

| Concern | File | Mechanism |
|---|---|---|
| Access (22) | `docs/readiness/2026-10-23/source_scope_decisions_926.json` | Third generation of the source-scope attestation: the reconciled904 verbatim plus one cohort per question (`held_access_A1`, `_A2`, `_A3`) with the four exact constraint elements and the title, abstract and purpose hashes of each member. `source_scope_attestation._manifest` checks the 904 object verbatim, the decisions file and the evidence sheet by SHA256, and that the added members are exactly the (question, source) pairs the decisions file clears, quoting its questions and answers verbatim. A decided member validates as `USER_ATTESTED` with Brett's answer and the decision date, and only at an assessment time after 2026-10-23. |
| Creators (10) | `docs/readiness/2026-10-23/source_citation_credits_436.json` | Tenth generation of the source-credit manifest: the 426 cohorts verbatim plus ten cohorts whose legacy creators are Brett's answers (three people for 1206, two for 2817, the issuing Navy office for 2586, JODC for the five RDMDB records, JMA for the two RRTDB records). Each binds the exact origin element (empty for seven), the contact and title elements and the decision, and preserves the original origin in the notes. `citation_creator_interpretation` pins it beside the 426. |
| Metadata dates (5) | `docs/readiness/2026-10-23/metadata_date_corrections_5.json` | New module `scripts/metadata_date_correction.py`: a correction applies to one source hash and one exact source value ("2080207" for 4139, 4161, 4181; blank for 1422, 1423) and gives an exact ISO day. `collection_qa` takes `--metadata-date-correction-manifest`, uses the corrected day for the publication date and the day-precision check, records `metadata_date_correction` and the source value in the artifact policy, and `agent_qa` honours that policy key. The original XML is unchanged. |

The 22 access members' constraint texts stay in the record exactly as they are; v2 maps them to
the rights statement and no licence is granted.

### The lane: proposal, mapping manifest, closed review

`docs/readiness/2026-10-23/build_held37_manifests.py` builds the evidence files (`evidence`) and,
from a fresh classification with those files at the lane's fixed time
`2026-10-23T22:00:00+00:00`, the lane documents (`lane`):

- `held37_proposals.json`: one row per source with the hold group, the question, Brett's answer,
  the holds the runbook classification raised and the holds that remain, the literal origin, the
  legacy creators the fresh classification produced and their authority (`credits` for the ten
  decided cohorts and the creator426 cohorts of 710, 4027 and 4063; `exxon` for 1994; `direct`
  for the organisations the transformer recognised and the DFO OSAP name the institutional policy
  publishes), the proposed modern creators, the resource type with its note, the date correction,
  the preservation paragraph and quoted evidence. 36 rows are admitted; FGDC-2817 is held for
  its undecided access text, with its decided creators recorded.
- `modern_reviewed_held37.json`: the admitted rows, each binding its proposal row by SHA256, its
  frozen plan target (status `held`), its creator authority object and its date correction.
- `modern_reviewed_held37_review.json`: starts as "proposal pending independent review" and
  admits nothing.
- `resource_types_r6.json`: r5 plus the 37 types (32 dataset, 5 report), pinned by
  `modern_bulk.RESOURCE_TYPES_SHA`; 870, 1318 and 4027 are listed as low confidence.

`modern_singleton.reviewed_held37_source_policy` (schema version 12, policy
`modern-xml-reviewed-held37-v1`) rebuilds every row from the proposal and requires the proposal
to pin the decisions file and the three evidence files by SHA256; a prepared input must carry the
lane's evidence for the hold it clears (the decided scope for access rows, the 436 credits or the
Exxon profile for its creator authority, the date correction for date rows). The plan check
accepts `held` for this policy only. The review must be approved, pinned, bound to the manifest
and the proposal by SHA256 and list the source as approved; until then every member is held.

### Creators outside Brett's decisions

The 22 access members and the 5 date members keep their literal credit, typed organisational
exactly as cited (the creator426 cohorts of 710, 4027 and 4063 and the Exxon821 projection of
1994 as published). Three records are proposed differently and the paragraph says so: 288
("Stacy Smith, Susan M. Henrichs of the University of Alaska, Fairbanks", typed as one
organisation by the transformer because of the word University) as two people with the shared
"of" affiliation, confirmed by the inverted contact name; 4027 as two organisations and three
people, as the creator426 cohort note reads; 1864 as the institute, with the role clause "Ed (by
support of ... as compilers)" preserved in the paragraph. The independent reviewer can hold any
of them.

### The public record

Every admitted row carries one paragraph that quotes the literal source values, states the
decision with its question, answer and date, and says what the record keeps. It enters the v1
preservation block (as the citations31 and creators64 policies do) and, for this lane only,
the v2 technical-info description through `prepare()`'s evidence (`public_notes`), so the
public record carries the source citation text and the date correction. `modern_wire_v2.build`
takes the correction and the notes: the corrected day is the publication date when the citation
gives no exact date, the catalogue line names the source value, and the notes come last.

### Sequence

1. Classify the 37 into the production prepared root with the runbook manifest set, the three
   evidence files and `--reviewed-at 2026-10-23T22:00:00+00:00`; copy only their inputs and
   originals (never reclassify a reviewed source).
2. An independent reviewer reads `held37_proposals.json` against the originals and the decisions
   file, approves or holds each row, and re-pins `HELD37_REVIEW_SHA`.
3. `plan`, review, `plan-v2`, review, `drafts`, `release`, `publish` as in ADR 0013 and 0014.

## Consequences

- Admission is finite: the proposal, the manifest, the review, the decisions file and the three
  evidence files hold each other by SHA256; a change to any one holds all 36 until the documents
  are rebuilt, re-reviewed and re-pinned.
- Every other prepared source is unchanged: the 4,148 production inputs give byte-identical v1
  wires, policies and evidence before and after this change (0 differences).
- The decided scope, the 436 credits and the date corrections are supersets or additions that the
  runbook manifest set can adopt for later classification runs; the production inputs already
  classified keep their 904 and 426 references.
- FGDC-2817 stays held until Brett decides its access text; its creators are ready in the 436
  credits and the proposal row.
- `metadata_date_correction` is a fourth evidence kind in the artifact policy; the single-record
  QA chain's `rules_sha256` list does not include the new module (it serves FGDC-141 only).
