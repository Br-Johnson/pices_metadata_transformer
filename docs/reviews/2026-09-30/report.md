# PICES metadata transformer bug review

Reviewed 2026-09-30. Revision: **4592f142b9c5be225254a0ad059c5cab7c6448ce**, current GitHub main, committed 2025-10-15. [Commit](https://github.com/Br-Johnson/pices_metadata_transformer/commit/4592f142b9c5be225254a0ad059c5cab7c6448ce). GitHub open issue/PR search returned no entries. Review only: no source edits, commits, PRs, issue comments, Zenodo requests, uploads, publication, deletion, or token-value access. The user explicitly requires production drafts until QA.

## Scope and evidence

An isolated clean clone is in the isolated review checkout. Its final `git status --short` is empty. No pre-existing checkout was located in bounded searches of Documents, code, Desktop, OneDrive/PICES, registered Codex projects, and Spotlight; therefore this report does **not** compare uncommitted local work or operational local logs. A broader home-directory search was stopped after making no progress. No existing user files were changed. Repository AGENTS.md was read; no repository `.agents` directory or additional AGENTS file was found. Testing-and-verification skill was used.

Existing suite: `python3 -m unittest discover -s tests -v`: **7/7 pass**, repeated in the isolated dependency environment. Tests cover DTO construction/copying and matching scores; they do not cover transformer/date/creator/license behavior, upload/publish controls, restart behavior, verifier, or JSON-LD semantics. Initial reproduction attempt failed because system Python lacked dateutil; an isolated `review-venv` installed repository requirements, and subsequent reproduction runs completed with exit 0. Exact dependency versions are in `dependency_versions.txt`.

`reproduce.py` and `evidence.json` provide safe fixtures and actual-source examples. Socket construction is blocked; network client constructors are bypassed or mocked. Temporary fixtures remain within this task workspace and are cleaned up. The harness demonstrates existing behavior; exit 0 means the demonstrations ran, **not** that the defects passed a correctness test. It scanned 4,206 source paths for date/creator leads, skips XML parse failures, and fully builds metadata for four named sources. It does not revalidate all 4,206 complete transformations or test live Zenodo API compatibility. Historical documentation of 4,204 transformed records and a sandbox run is not fresh execution evidence or proof of production completion.

## Priority findings

P1 means resolve before production publication; P2 means a concrete correctness/reliability defect requiring a planned correction. All behavior below was reproduced offline unless marked static evidence.

### 1. P1 — Sandbox state suppresses production uploads and contaminates publication selection

[batch_upload.py:273](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/batch_upload.py#L273) reads every successful registry/log entry by filename without environment checks. [Registry writing:459](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/batch_upload.py#L459) omits environment; [OutputPaths:266](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/path_config.py#L266) uses common state paths. A fixture sandbox-success entry makes a production uploader return zero remaining files. Shared safe lists and transformation prefilters have the same environmental scope problem.

[publish_records.py:57](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/publish_records.py#L57) aggregates all batch logs and legacy entries without checking their environment/URL. A publisher configured for production accepts an entry explicitly pointing to `sandbox.zenodo.org`. It would resolve that numeric ID against production; outcomes depend on remote ownership/existence and were not tested. This is a verified selection defect, not evidence that an unrelated record was actually published.

Remediation: environment-qualified ledger keys and output state; reject mismatched host/record provenance at upload, verification, and publication; provide a migration for existing state. Credential-key/base-URL selection itself is separate and correctly selects sandbox vs production in [zenodo_api.py:33](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/zenodo_api.py#L33) and [417](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/zenodo_api.py#L417). No credential values were read.

### 2. P1 — Rights statements are replaced by more permissive licenses

[License patterns:28](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/fgdc_to_zenodo.py#L28) and [detection:1063](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/fgdc_to_zenodo.py#L1063) match generic CC-BY before CC-BY-SA. `CC-BY-SA 4.0`, `Creative Commons Attribution-ShareAlike 4.0`, and `CC BY-NC 4.0` all become `cc-by-4.0`. `open access` becomes CC0. [Constraints:1034](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/fgdc_to_zenodo.py#L1034) defaults unrecognized use terms to CC0: `All rights reserved. Permission required.` remains open/CC0. Source text surviving in notes does not correct the structured license.

Remediation: explicit license parsing with specific variants first; treat unknown rights as an unresolved curator decision. Do not infer a grant of rights from access availability. This finding is about inaccurate metadata, with no claim that every source has these terms.

### 3. P1 — Duplicate inventory failures produce a safe-to-upload result

[pre_upload_duplicate_check.py:90](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/pre_upload_duplicate_check.py#L90) catches inventory API errors and returns an empty or incomplete inventory. [Checking:155](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/pre_upload_duplicate_check.py#L155) labels an unmatched file safe. Simulated API failure yields `safe_to_upload: true`, reason `No duplicates found`.

Static evidence: the inventory fetches **published community records only** at lines 65–87, not owned drafts; the same immutable inventory is used for each local file at lines 210–240, so within-batch duplicate titles are not added to it. A lost ledger or interrupted draft upload can therefore evade discovery. README's broader DOI/title-similarity claims do not describe this pre-upload checker, which performs exact lowercased title membership only.

Remediation: return an explicit incomplete/failed inventory result and block upload; include owned drafts and local candidates, persistent identifiers, source IDs, and inventory provenance.

### 4. P2 — Date interpretation accepts year 1220 and corrupts natural-language dates

[fgdc_to_zenodo.py:832](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/fgdc_to_zenodo.py#L832) assumes every six-character string is YYYYMM, without disambiguation or calendar/plausibility checks. **819 parsed source files** contain `pubdate=122003`; these normalize to `1220-03-01`. Full metadata builds for [FGDC-3413.xml:6](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/FGDC/FGDC-3413.xml#L6) and [FGDC-1990.xml:6](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/FGDC/FGDC-1990.xml#L6) reproduce this. The validator's [date check:199](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/validate_zenodo.py#L199) accepts a fixture with this date. Metrics separately penalize dates before 1900, but that is not a rejection gate.

Additional fixture failures: `December 20, 1994` becomes `1994-01-01` because the comma-years branch precedes date parsing; `1977 through 1978` becomes the invalid `1977-19-78` through digit concatenation at [799](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/fgdc_to_zenodo.py#L799). Ordinary `1994-12-20` and `2020-01-02` remain correct.

The source `122003` is ambiguous; do not silently reinterpret it as December 2003 or use dataset observation years as publication dates. Record a curator decision and preserve raw date/precision/provenance. Public year-1220 examples were not traced to an actual upload by this revision.

### 5. P2 — Creator splitting destroys personal and institutional identities

[fgdc_to_zenodo.py:374](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/fgdc_to_zenodo.py#L374) splits comma-separated tokens before the parser can handle `Family, Given`. `Smith, Jane` yields creators `Smith` and `Jane`. Abbreviated organizations escape the small regex list and get split/reversed: actual [FGDC-1284.xml](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/FGDC/FGDC-1284.xml) origin `Canadian Wildlife Service, Northern Forestry Research Centre` produces `Service, Canadian Wildlife` and `Centre, Northern Forestry Research`. FGDC-150 becomes only `Dept., U.S.` because the `of` cue truncates it. Full NOAA/Office organization text remains intact in the fixture, so the previously observed public NOAA tokenization is not established as a current-main defect.

Remediation: preserve source origin units, explicit person/organization classification and curator overrides; distinguish personal surname commas from list separators. Also bound origin lookup to the primary citation: current `.//origin` searches nested citations too (static evidence).

### 6. P2 — Failed metadata update loses the created draft ID and restart makes another draft

[batch_upload.py:95–134](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/batch_upload.py#L95) creates a draft before metadata update, but the exception result omits its deposition ID. Mock creation ID 999 followed by failed metadata update returns failure with no ID and no cleanup/reconciliation. `_update_registry` consequently records no recoverable remote ID; restart selects failed files and creates a fresh draft. The single-record uploader repeats this logic at [upload_to_zenodo.py:172](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/upload_to_zenodo.py#L172).

Remediation: persist draft ID immediately, then resume/update it. Treat uncertain POST response failures as reconciliation states. The client's generic retries also replay POST on request/server failures at [zenodo_api.py:135](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/zenodo_api.py#L135); duplicate creation from a remote successful-but-lost response is a risk supported by code, not a live incident proved here.

### 7. P2 — Verification contradicts metadata-only upload and misses meaningful losses

[verify_uploads.py:152](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/verify_uploads.py#L152) requires attached files for success, while current upload deliberately creates metadata-only records. Identical metadata with empty files yields verification failure and zero mismatches. [Comparison:211](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/verify_uploads.py#L211) ignores description, notes, relations, publisher, affiliations and many other fields; replacing description/notes/relations yields zero mismatches.

Remediation: verify the intended metadata-only contract, normalized complete payload, raw-FGDC preservation, environment, remote state and publication/community acceptance separately. Zero checked records should be reported as unverified, not a successful migration.

### 8. P2 — Accepted bibliographic links violate the local relation contract

[bibliographic_linkage.py:127](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/bibliographic_linkage.py#L127) defaults accepted decisions to `isAlternativeIdentifierOf`; candidate reports use that same relation at line 226. [Validator:36](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/validate_zenodo.py#L36) does not permit it. Applying an ordinary accepted decision produces `Related identifier 1 has invalid relation: isAlternativeIdentifierOf`. Reapplying the same decision deduplicates relation entries but appends another identical provenance note (reproduced).

Remediation: one checked relation vocabulary with human-selected semantics; make decision application idempotent by decision ID and payload hash. No claim about live API rejection is needed to establish the internal inconsistency. Cross-reference extraction also emits `isRelatedTo`, absent from this validator (static evidence).

### 9. P2 — Publication selection rejects custom output directories

[publish_records.py:78](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/publish_records.py#L78) and line 101 require paths beginning literally `output/data/zenodo_json/`, although `--output` supports arbitrary roots. A successful entry under the isolated custom output directory yields `No successful upload records found`. This prevents the intended QA-then-publication workflow with isolated/environment-specific outputs.

Remediation: resolve paths relative to the selected OutputPaths and identify records by stable IDs, not one textual directory prefix.

### 10. P2 — JSON-LD emits prose as a URL and organizations as people

[generate_jsonld_catalogue.py:75](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/generate_jsonld_catalogue.py#L75) uses notes as the fallback dataset URL. A DTO without DOI produces `url: Free text notes`. At line 52 all creators become `Person`, including explicit `type: Organization` NOAA. The local health check at line 118 checks only context/type/name, so it cannot catch these defects (static check of validator).

Remediation: use a verified persistent landing-page URL or omit the field, preserve Organization type, validate semantic URLs and relation types. `sameAs` is currently populated from every bibliographic link without checking relation/status; equivalence must not be inferred for a citation or derived subset.

### 11. P2 — Temporal/spatial notes are overwritten during transformation

[fgdc_to_zenodo.py:943](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/fgdc_to_zenodo.py#L943) adds temporal and spatial notes, then [line 963](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/fgdc_to_zenodo.py#L963) replaces notes with `_build_notes`. A fixture with explicit 1994 start/end and currentness produces final empty notes and no dates. Spatial coverage uses the same overwritten notes channel. Raw XML is later embedded by the uploader when available, which mitigates complete source loss but does not restore structured or extracted coverage to the transform/JSON-LD outputs.

Remediation: assemble notes once from explicit fragments; emit temporal/spatial structured fields where supported. Single-date coverage also checks `.//sngdate.text` rather than its child `caldate` (static evidence).

## Production policy and manual gates

[AGENTS.md:86](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/AGENTS.md#L86) says production should pass `--publish-on-upload`. [TODO:103–106](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/docs/todo_list.md#L103) says draft-first and publication after QA. Actual guards disable production auto-publication in the [batch constructor:58](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/batch_upload.py#L58), [batch CLI:851](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/batch_upload.py#L851), and [orchestrator CLI:903](https://github.com/Br-Johnson/pices_metadata_transformer/blob/4592f142b9c5be225254a0ad059c5cab7c6448ce/scripts/orchestrate_pipeline.py#L903). Production therefore stays draft under this interface, consistent with the user's explicit direction. Standalone `publish_records.py --production` publishes selected entries; it does not consume a durable QA approval artifact. Do not remove the existing draft guard to conform to stale AGENTS guidance.

A short runbook should document: environment and source/revision manifest; unresolved date/creator/license adjudications; duplicate decisions; exact draft IDs and normalized-payload hashes reviewed; QA approver and decision time; explicit publication approval; publication versus community acceptance versus DOI activation; and reconciliation after interrupted/uncertain writes. The QA approval should become stale when metadata changes. These are proposed refinements, not instructions executed in this review.

Determinism gap: planned/unpublished date values use `datetime.now().year` at transformer lines 636–647. Identical input can change output next year; dateutil partial-date parsing also inherits current defaults. Use explicit reviewed dates or a pinned run parameter, record provenance, and keep timestamps out of canonical metadata hashes. Existing character-preservation/field-presence metrics are diagnostic scores, not semantic accuracy evidence.

## Concrete simplification sequence — proposal only

1. Freeze offline regression fixtures for the confirmed bugs, including actual source examples; define one canonical metadata/relation/verification contract. Keep current draft-first behavior.
2. Consolidate `batch_upload.py` and `upload_to_zenodo.py` into one upload service. They duplicate create/update/files-disabled fallback, XML-note assembly, duplicate replacement and error/result handling. Keep the CLI wrappers thin. Use one environment-scoped ledger for draft-created, metadata-applied, QA-approved and published states.
3. Share publication and verification routines. Batch inline publication and RecordPublisher currently implement separate success interpretation; publisher custom path filtering and shared-log assumptions show drift. Use one explicit QA-approved manifest, one remote adapter, and one reconciliation path.
4. Centralize creator/date/license normalization and note assembly as pure functions; curate exceptions as versioned data. Separate raw source preservation from semantic validation. Share validation with metrics rather than maintaining conflicting date/rights checks.
5. Reduce competing orchestration/report layers (`iteration_loop`, `orchestrate_pipeline`, batch/single reports, registry, legacy upload log) to one deterministic staged runner plus reports derived from the ledger. Retain compatibility readers during migration; avoid maintaining several independently writable truths. Consolidate DOI-link decisions and provenance so reruns do not duplicate notes.
6. Add cross-repository adjudication as a distinct prepublication review stage, using the existing adapters where suitable. This should not become a second upload engine or automatic merge/delete mechanism.

Implement in small validated steps after separate authorization. No refactor was performed.

## AquaDocs concern: existing capability versus proposed workflow

The likely intended repository is **AquaDocs**: its [public homepage](https://aquadocs.org/) identifies itself as “Aquadocs Repository”; checked-in `docs/ODIS-Book.md` references an `aquadocs` graph namespace at lines 8209–8215. That supports the interpretation of “Aquadox,” but does not prove the user's intended collection or specific records. The homepage returned no readable body through the browsing tool, and a guessed IODE informational URL was inaccessible. AquaDocs API/OAI endpoints, collection inventory, coverage, and record-level duplication were **not verified**; no matching AquaDocs records are claimed.

Existing code queries DataCite and Crossref through title/creator/abstract adapters and supports curator acceptance decisions. This offers partial cross-repository discovery for records indexed there, but no AquaDocs-specific adapter or source/handle-ID inventory exists. MatchingEngine uses title/abstract similarity and exact normalized full-name overlap; it does not compare persistent/source identifiers, dates, spatial extent, version, or subset relationships. Pre-upload Zenodo dedup is separate and exact-title-only. Registry-link acceptance does not block publication of unresolved duplicates. Adapter failures become empty candidate lists in bibliographic_linkage lines 56–66, so “no candidates” cannot establish search completeness.

Proposed prepublication workflow: snapshot accessible AquaDocs/Zenodo/registry metadata through a verified read interface or supplied export; retain source URL, retrieval time and content hash. Normalize DOI, Handle/other persistent IDs and original source IDs first; then compare title, creators, dates, extent and description. Record evidence and classify **same work**, **alternate version**, **derived subset**, or **different dataset**, with human adjudication for uncertain cases. Reuse or link the existing persistent record when appropriate; preserve the selected relation and decision rationale. No automatic deletion, merging, or equivalence claim from similarity alone. Search failures or missing inventory coverage remain explicit QA blockers. Production remains draft until those decisions and metadata QA are approved.

## Remaining limits

No live Zenodo validation, API inventory, publication/community acceptance, DOI activation, existing operational ledger, complete source-regression sweep, or AquaDocs matching was performed. No production-completion claim is supported. These limits do not weaken the reproduced local bugs, but they prevent concluding that any particular production record was created or corrupted by this revision.
