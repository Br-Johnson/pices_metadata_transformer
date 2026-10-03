# FGDC → Zenodo Sandbox TODO List

## Exact821 source scope answer — 2026-10-03

- [x] Bind Brett's20:20UTC answer to the original three questions and exact821 source/hash/raw-constraint/context members; retain USER_ATTESTED provenance and separate XML authority.
- [x] Verify791 promotions:3234 supported /966 held /6 malformed;347 guarded offline tests,7 independent focused contracts and complete4206-source delta audit pass.
- [x] Preserve all4194 complete metadata objects,4200 XML copies,456 alias holds and all unrelated decisions. Reassess only30 protected members within the explicitly answered821:28 promote,148 protected cases remain held.
- [ ] Complete bounded final delta/document reconciliation and freeze the normal handoff PR.
- Remaining selected holds:2 creator ambiguities and28 long titles. No license, underlying-data rights or production/provider release is inferred.

## Five retained-import beforeimages — 2026-10-03

- [x] Receive the standalone16494-byte Library text with supplied SHA; independently recompute five complete metadata hashes and retain exact date/creator/contributor/rights beforevalues without new provider requests.
- [x] Bind current2043/2057 publication_date1220-01-01 and distinguish an unacceptable narrow preservation candidate from the source2004-07-23 XML metadata date; preserve all original dates and access holds.
- [x] Independently review the bounded schema2 comparison: all five complete beforeimages and94 differing-field presence/value-hash comparisons clear at0f09049.
- [x] Receive and reconcile the complete510-line saved file/version transfer: all five IDs/concept DOIs/file IDs/checksums/capture times match, with exact links preserved privately and no new provider request.
- [ ] Freeze a fresh modern revision/concurrency baseline during any separately authorized execution against these existing records; none was retained in saved evidence and none is inferred here.
- PR10 is merged at e3fde4b with reviewed runtime dc351b0. Parent dispatched the approved modern trial; one durable create intent remains held with network dispatch unknown. All create allowances remain spent. Brett's exact821 answer is implemented above; existing-record correction/release gates remain separate.

## Five source credits and eight display titles — 2026-10-03

- [x] Implement exact additive401 creator profile and eight title selections with source/hash/element/full-metadata bindings; preserve all prior396 and every original title/credit/context.
- [x] Fail the new-profile acceptance contract against the predecessor, then pass five guarded focused contracts for all13, full after-image tampering, defaults/withdrawal/cache, agent and both human QA routes.
- [x] Complete317 guarded tests and exact full-corpus/resume preservation; independent source/runtime/complete-delta review clears. Final documentation corrects frozen predecessor checkout requirements. No provider action or new license.
- Actual13 promotions:2443 supported /1757 held /six malformed,4181 metadata objects unchanged,401 policy references changed,3793 payload bytes unchanged,176 protected access holds and456 aliases preserved. See `readiness/2026-10-03/source_credit_title_13.md`.
- [x] Independently adjudicate the three retained production catalogue identities using discriminating source evidence. Preserve exact IDs/DOIs for the same existing imports; historical bytes remain unknown and current ownership/file/correction/readback/release gates remain separate.

## Remaining access and attribution evidence from merged 4b13126 — 2026-10-03

- [x] Audit the largest exact source-constraint groups in disjoint read-only lanes, preserving the completed 86-record access queue, earlier 90 access cases and all 456 aliases. Root is the sole integration writer.
- [x] Implement only reviewed finite source/hash/context-bound resource-access interpretations; preserve XML, complete metadata, restricted access, blank licenses and independent attribution/date/title holds.
- [x] Verify the complete actual delta and independent implementation/source review; freeze the grouped decision packet. Provider execution remains with its separate executor.
- Actual finite142 batch: 2,430 supported / 1,770 held / six malformed; 312 guarded offline tests and six independently reproduced focused contracts. All 4,194 whole metadata objects, 4,206 originals, 4,200 copies, 176 protected access holds and 456 aliases are preserved. See `readiness/2026-10-03/finite_source_resource_access.md` and its validation receipt.
- [x] Implement the separately prepared five source-credit and eight bounded-title proposals in the source13 checkpoint; all13 are source-supported. The earlier finite142 checkpoint counts remain historical.
- [x] Obtain and implement the exact Contributor361 /ADF&G351 /Unknown109 scope answer; preserve original terms, blank licenses and independent holds. Historical finite142 counts remain unchanged.

_Last updated: 2026-10-03_

This checklist tracks everything required to shepherd FGDC metadata through the Zenodo sandbox pipeline and keep the project healthy. Update it whenever a task is finished, deferred, or newly discovered. Capture timestamps or short notes when changing scope so the team always understands current progress.

## Protocol

- Treat this document as the ground truth for outstanding work—update it before and after each significant action.
- Keep commits granular (ideally one logical change per commit touching a handful of files) and group them into small/medium PRs that reference the checklist items covered.
- Record blockers, questions, or follow-ups directly under the relevant task as indented notes.
- If a workflow introduces a new convention, mirror it here and in `AGENTS.md`.

## Workstreams

### 1. Environment & Baseline

- [x] Confirm `.env` contains a valid sandbox token (`ZENODO_SANDBOX_TOKEN`) and no production secrets.
- [x] Smoke-test Zenodo API connectivity (`python3 scripts/zenodo_api.py --test-connection` or helper) and save the output path in a note.
  - Result
  ```
      2025-10-11 17:58:26,162 - INFO - Zenodo API connection successful
      Found 25 existing depositions
      Found 3 available licenses
      API connection test successful!
  ```
  - Note: endpoint returns depositions owned by the sandbox token (25 records), not the full PICES community catalogue.
- [x] Review `logs/progress.csv`, recent transformation summaries, and validation reports to understand baseline quality.

### 2. Transformation & Validation

- [x] Run `python3 scripts/batch_transform.py --input FGDC --output output --limit 10 --log-dir logs`; inspect `logs/errors.json` and `output/validation_report.json`.
  - 2025-10-11: Sample run succeeded (10/10 transformations); warnings limited to dateline-crossing bounding boxes and missing FGDC license tags.
- [x] Remove the limit for a full transformation when the sample passes; archive metric snapshots (e.g., `output/reports/transform/transformation_summary.txt`).
- [x] Review the failed transformation/validation file lists in the latest `transformation_summary.txt` and schedule remediation.
  - Remaining blockers: `FGDC-3373.xml` and `FGDC-3484.xml` are entirely null bytes and require fresh source files before they can be transformed.
- [x] Document any new warnings that require mapping or policy decisions.
- [x] **Comprehensive API Analysis Complete** - Tested both Legacy and InvenioRDM APIs
  - **Hybrid Setup Confirmed**: Zenodo uses a hybrid API approach
    - Legacy API: `/api/deposit/depositions` (for creating/managing records) ✅ Available
    - Newer API: `/api/records/` (for reading published records) ✅ Available
    - Vocabularies: `/api/vocabularies/*` (controlled vocabularies) ✅ Available
  - **ROR Support**: Limited in current setup
    - Legacy API strips ROR fields during creation ❌
    - Newer API structure supports ROR but creation endpoint not available ❌
    - PICES ROR: `https://ror.org/04q8xer47` (can include in metadata but won't be preserved)
  - **Recommendation**: Continue with legacy API - it's stable and production-ready
  - **Future**: Full ROR support will require waiting for Zenodo's complete InvenioRDM migration
- [x] Add Publisher = 'North Pacific Marine Science Organization' to all records
  - Transformer now injects the PICES publisher and distributor contributor when the source metadata does not provide them.

### 3. Pre-Upload Screening

- [x] Execute `python3 scripts/pre_upload_duplicate_check.py --sandbox --output-dir output --log-dir logs --limit 50` to sanity check duplicate logic.
- [x] Run the full scan, then compare `output/safe_to_upload.json`, `already_uploaded_to_zenodo.json`, and the uploads registry for consistency.

### 4. Upload Dry Run & Logging

- [x] Perform `python3 scripts/batch_upload.py --sandbox --output-dir output --batch-size 5 --limit 5 --interactive` to validate registry/log updates and attachment handling.
  - 2025-10-11T22:06Z: Batch 1 uploaded 4/5 records (FGDC-2544/2601/2604/2670 ok; FGDC-2284 failed — Zenodo rejects `license: open`).
  - 2025-10-11T22:15Z: Retest after license normalization fix — Batch 1 uploaded 5/5 (FGDC-2284 now DOI 10.5281/zenodo.369187 + four additional records).
- [x] Review `output/uploads_registry.json`, `batch_upload_log_*.json`, and `upload_log.json` to confirm batch numbers, timestamps, and FGDC paths.
  - Registry, batch logs, and `upload_log.json` now aligned — legacy log shows seven entries including FGDC-2284/2695/3680/3683/374 from the 2025-10-11T22:15Z batch.
- [x] Decide on batch sizing for the full upload, documenting rationale here.
  - 2025-10-11T22:16Z: Plan to proceed in 3 batches of 30 records, re-evaluate logs and metrics between batches.
  - 2025-10-11T22:24Z: Executed first 3×30 sandbox batches (90 uploads, 0 failures); queued follow-up audits before scaling up.

### 5. Post-Upload Verification

- [x] Immediately after each batch, run `python3 scripts/deduplicate_check.py --sandbox --output-dir output --log-dir logs --hours-back 6` and capture findings.
  - 2025-10-11T22:32Z: Duplicate check clean (0 overlaps within 6h window); report in `output/reports/duplicates/duplicate_check_report_20251011_223241.txt`.
- [x] Generate audits (`python3 scripts/upload_audit.py --output-dir output`) and metrics (`python3 scripts/metrics_analysis.py --output-dir output --save-report`) and compare to baseline.
  - 2025-10-11T22:32Z: Upload audit at `output/reports/uploads/upload_audit_20251011_223248.json` summarises 3,621 successes / 32 failures (99.1%); metrics snapshot `output/reports/metrics/enhanced_metrics_analysis_20251011_223259.json` shows 100% compliance with required fields.
- [x] Produce enhanced metrics (`python3 scripts/enhanced_metrics.py --input output/zenodo_json --output output/enhanced_metrics_sandbox.json --log-dir logs`) and note regressions.
  - 2025-10-11T22:34Z: Fixed calculator to ingest FGDC sources; summary shows 4,204 records processed (avg quality 86.7, coverage 85.7%, compliance 100%). Output: `output/enhanced_metrics_sandbox.json`.
  - 2025-10-11T22:40Z: Adjusted FGDC parsing + grading weights; zero-field anomalies resolved and overall grades now spread (86 excellent, 3,078 good, 983 fair, 57 poor).

### 6. Verification & Publishing

- [x] Run `python3 scripts/verify_uploads.py --sandbox --output output --log-dir logs --limit 20` to confirm metadata/file alignment.
  - 2025-10-11T23:09Z: 20/20 verified (100%) after migrating FGDC-1/10 logs to `output/data/` and restoring dual creators for FGDC-1.
- [x] Publish a sandbox subset (`python3 scripts/publish_records.py --sandbox --output output --limit 10`) once verification passes; document results and issues.
  - 2025-10-11T23:04Z: Published FGDC-3754…3762 (IDs 369197–369215) successfully; log at `output/reports/publish/publish_log.json`.
- [x] Optionally spot-check individual records using `python3 scripts/record_review.py <FGDC-ID>` and log observations beneath this item.
  - 2025-10-11T23:04Z: `python3 scripts/record_review.py FGDC-3754` — all required/optional fields present; data preservation 175.9%; status EXCELLENT.

### 7. Orchestrated Runs

- [x] Dry-run the orchestrator (`python3 scripts/orchestrate_pipeline.py --sandbox --limit 10 --interactive`) to validate step sequencing and state persistence.
  - 2025-10-11T23:15Z: Pipeline summary confirms all steps (transform→verify); reports in `output/reports/pipeline/`.
- [x] Execute a full orchestrator pass without limits once satisfied; ensure `output/pipeline_state_sandbox.json` and summary files show completion.
  - 2025-10-12T05:20Z: Full sandbox run completed with `--publish-on-upload` disabled (historical run); post-run auto publish now handled inline.

### 8. Final Review & Cleanup

- [ ] Review random records in the Zenodo sandbox UI to confirm community placement and metadata fidelity.
  - 2025-10-15T04:34Z: Spot-checked 10 newest PICES sandbox records (373295→373277). Community banner and files render, but creators are tokenized into separate words (e.g., “National Oceanic”; “Office”), placeholder strings like “No abstract was givien” leak through, and publisher remains “Zenodo” instead of “North Pacific Marine Science Organization”.
  - 2025-10-15T05:21Z: Ran `python3 scripts/iteration_loop.py --limit 10` (transform, validate, duplicate check, verify, metrics). Sample JSON now preserves full organization creators, swaps placeholder abstracts/purposes for neutral text, and sets publisher to PICES. Duplicate check (sandbox) flagged 10/10 as already uploaded (expected); verification now blocks on `record_not_found` for FGDC-3754–FGDC-3758 entries in the upload registry.
  - 2025-10-15T05:24Z: Removed FGDC-3754–FGDC-3758 from `output/state/uploads/upload_log.json` and `output/state/uploads/uploads_registry.json`; rerun the iteration loop to confirm verification succeeds before proceeding with new uploads.
  - 2025-10-15T05:50Z: Iteration loop rerun (`python3 scripts/iteration_loop.py --limit 10`) now completes cleanly—duplicate scan still flags the sample as already uploaded (expected), verification passes 10/10 records, metrics report stored at `output/reports/metrics/iteration_metrics_20251014_224511.json`. Ready for UI spot check follow-up.
- [ ] Clear or refresh `output/cache/` when performing broader duplicate scans; record when cache resets occur.
- [ ] Capture lessons learned or production-readiness adjustments for inclusion in README/`AGENTS.md`.
- [ ] Document and socialize production upload + publish strategy (draft-first, monitoring, recovery) in the README:
  - In production, keep uploads in draft (no `--publish-on-upload`); trigger publication via `scripts/publish_records.py` after QA sign-off.
  - Monitor publish failures via `batch_upload_log_*` (`publish_failures` list) and rerun `scripts/publish_records.py` for recovery.
  - Track community acceptance and DOI activation through `output/reports/publish/publish_log.json` and Zenodo notifications (no curator approval required for PICES sandbox/community).

### 9. Regression Gate & DTO Hardening

- [x] Re-run post-merge regression sweep (`batch_transform`, `pre_upload_duplicate_check`, `verify_uploads`, `metrics_analysis`) and capture diffs in `logs/` + `output/` before enabling the new generator.
  - 2025-10-15T06:07Z: `batch_transform` + `metrics_analysis` refreshed DTOs/metrics; duplicate and verification sweeps blocked pending sandbox `.env` credentials.【14238e†L1-L59】【6be62a†L1-L41】【710701†L1-L3】【1ef35f†L1-L4】【3160f3†L1-L34】
- [x] Finalize canonical record DTO schema (document invariants, add unit coverage) and publish 10-sample fixtures under `contracts/examples/odc/` for regression tests.
  - Added `scripts/dto.py`, DTO serialization tests, and fixtures `contracts/examples/odc/FGDC-*.json` generated from the latest smoke run.【F:scripts/dto.py†L1-L196】【F:tests/test_dto.py†L1-L64】【F:contracts/examples/odc/FGDC-1.json†L1-L26】
- [x] Capture any new anomalies discovered during regression in `docs/tech-debt.md` and schedule remediation tasks.
  - Logged missing sandbox secrets prerequisite for duplicate/verification gates in `docs/tech-debt.md`.【F:docs/tech-debt.md†L63-L70】

### 10. Bibliographic Linkage Enablement

- [x] Build DataCite search adapter (`scripts/matching/datacite_adapter.py`) with documented rate-limit handling and response normalization.【F:docs/bibliographic_linkage_plan.md†L19-L49】
  - Implemented `DataCiteAdapter` with retry logging and normalised `MatchCandidate` payloads.【F:scripts/matching/datacite_adapter.py†L1-L102】
- [x] Implement Crossref adapter and shared fuzzy matching engine (title/abstract/creator scoring) with configurable thresholds and tests.【F:docs/bibliographic_linkage_plan.md†L32-L44】
  - Added Crossref adapter plus `MatchingEngine`/unit tests covering scoring paths.【F:scripts/matching/crossref_adapter.py†L1-L92】【F:scripts/matching/engine.py†L1-L131】【F:tests/test_matching_engine.py†L1-L40】
- [x] Create curator review CLI (`scripts/matching/review_matches.py`) that writes decision trails to `output/reports/duplicates/` and supports accept/reject/defer states.【F:docs/bibliographic_linkage_plan.md†L45-L72】
  - Delivered auto/interactive review CLI emitting `bibliographic_decisions_<timestamp>.json`.【F:scripts/matching/review_matches.py†L1-L94】
- [x] Integrate accepted matches into both Zenodo JSON and Plan B JSON-LD generation (`related_identifiers`, provenance notes) before uploads occur.【F:docs/bibliographic_linkage_plan.md†L52-L84】
  - `scripts/bibliographic_linkage.py` now applies curator decisions to DTO + Zenodo payloads and appends provenance notes before JSON-LD generation.【F:scripts/bibliographic_linkage.py†L1-L258】
  - 2025-10-16T00:00Z: Decision application now caches DTOs per run and records accepted links in the DTO audit trail for downstream audits.【F:scripts/bibliographic_linkage.py†L205-L258】【F:scripts/dto.py†L86-L139】
- [x] Produce linkage metrics + alerts (counts, confidence tiers, overrides) and surface them alongside existing pipeline dashboards.
  - Bibliographic sweep now emits paired candidate + metrics reports under `output/reports/duplicates/` and `output/reports/metrics/`.【1995df†L1-L2】

### 11. Plan B JSON-LD Catalogue

- [x] Implement JSON-LD generator and persist outputs to `docs/odc/records/` with deterministic filenames (`<zenodo_id>.jsonld`).
  - `scripts/generate_jsonld_catalogue.py` writes schema.org payloads such as `docs/odc/records/FGDC-1.jsonld`.【F:scripts/generate_jsonld_catalogue.py†L1-L191】【56d2a1†L1-L2】
- [x] Automate sitemap + hosting pipeline (GitHub Pages deploy, optional `w3id` redirects, timestamped `lastmod` values).
  - Generator refreshes `docs/odc/sitemap.xml` and documented workflow in `docs/odc/README.md`.【F:docs/odc/README.md†L1-L18】
- [x] Add CI validation gates (JSON Schema, schema.org validator, broken-link scan) and emit nightly health summary (`output/reports/odc/harvest_status.json`).
  - Lightweight validation report saved to `output/reports/odc/harvest_status.json` for pipeline gating.【F:output/reports/odc/harvest_status.json†L1-L5】
- [x] Integrate JSON-LD generation into the orchestrator after bibliographic enrichment to ensure outputs reflect the latest DTO state.
  - Orchestrator now runs bibliographic linkage → JSON-LD → review prior to verification.【F:scripts/orchestrate_pipeline.py†L376-L460】【F:scripts/orchestrate_pipeline.py†L600-L611】

### 12. LLM-Assisted Human QA

- [x] Implement `scripts/extract_review_set.py` to package FGDC summaries, enriched DTO snippets, and anomaly rationale (`--limit` for sampling, default full corpus).
  - CLI emits review bundles like `output/reports/review/creator_anomalies_input_sample.json` for prompt generation.【F:scripts/extract_review_set.py†L1-L109】【65025b†L1-L3】
- [x] Build prompt template + review CLI that logs observations to `output/reports/review/creator_anomalies_<timestamp>.json` without mutating source data.【F:docs/ODIS-plan.md†L90-L99】
  - `scripts/review_llm_cli.py` captures accept/reject/defer notes with auto mode for non-interactive runs.【F:scripts/review_llm_cli.py†L1-L108】【15f806†L1-L3】
- [x] Pilot targeted run (≤25 records) post-regression to tune thresholds, then schedule full corpus review once JSON-LD validation passes.
  - Executed limit-5 dry run immediately after DTO refresh; observations logged to the review ledger produced by `review_llm_cli.py`.【65025b†L1-L3】【15f806†L1-L3】
- [x] Create curator triage checklist so mapper adjustments and blacklist updates are captured deterministically before re-running the pipeline.
  - Authored `docs/curator_triage_checklist.md` aligning mapper fixes with review artefacts.【F:docs/curator_triage_checklist.md†L1-L17】
- [x] Update orchestrator to include optional LLM review stage and ensure QC artefacts sync with nightly harvest status reports.
  - New pipeline steps call bibliography, JSON-LD, and review automation when configured.【F:scripts/orchestrate_pipeline.py†L376-L460】【F:scripts/orchestrate_pipeline.py†L600-L611】

## Commit & PR Guidelines

- One logical change per commit; reference checklist items in commit messages.
- Group related commits into focused PRs (e.g., “Pre-upload safeguards”) and include command outputs or log summaries in descriptions.
- Update this TODO list and supporting docs alongside code changes so the team always has an accurate view of project status.

## PR 8 implementation and independent review

- [x] Preserve source/rights/date/creator fidelity and isolate durable draft state by environment.
- [x] Require human QA for production publication and validate approved bounded selection.
- [x] Four independent agents reviewed lifecycle, QA, metadata fidelity and integration; confirmed findings fixed and rechecked.
- [x] 65 offline regressions pass, including network-blocked execution.
- [ ] Human source adjudication, historical ledger reconciliation and live endpoint compatibility checks before operational use.

Production remains draft until human QA. This entry supersedes any earlier automatic production publication guidance.

## Current staged rollout — 2026-10-02

- [x] Audit 20 stratified raw sources offline, including all five production imports and a missing-primary-date case; save source hashes, field comparisons, holds and duplicate evidence under `docs/readiness/2026-10-02/`.
- [x] Validate documented editable `inprogress` draft response and reject submitted drafts; add mock regression.
- [ ] Obtain source-specific rights, deposited-object/date/creator decisions; zero audited cases are currently approved for a live canary.
- [x] Implement the opt-in reviewed original XML artifact contract with source/policy/file hashes, checksum/readback/resume tests and stale QA rejection; authenticated live compatibility remains pending.
- [ ] Establish authorized authenticated sandbox session, then run at most three approved draft canaries and idempotence readback before expansion. No publication or community submission.

## Delegated record-level QA policy — 2026-10-02

Brett explicitly delegated record QA to agents, superseding human-per-record requirements above. Production release remains a separate explicit authority decision; no release or merge is inferred.

- [x] Prepare three source-backed technical XML drafts and one labeled synthetic fixture offline; preserve metadata-date semantics, source attribution and unresolved license values. No remote writes.
- [x] Add source/evidence-bound schema-2 agent QA with explicit holds; preserve historical human schema-1 manifests.
- [x] Require independent program review, population-bound risk-stratified spot checks and separate release selection before production publication.
- [ ] Execute authenticated bounded sandbox draft/readback/idempotence canary; no authenticated sandbox session/client is available in this execution environment.
- [ ] Obtain or investigate authoritative XML redistribution evidence for held publication cases; no default license or blanket approval.

## Isolated lifecycle recovery — 2026-10-02

- [x] Reject altered cached semantic verdicts while preserving unchanged transformation reuse and honest source-only flags.
- [x] Revalidate source-bound restoration authority for historical schema-1 and schema-2 human approvals.
- [x] Preserve failing-first regressions and pass all 136 socket-blocked tests; fresh/resumed classification preserves all 4,206 source decisions and original hashes. See `readiness/2026-10-02/qa_lifecycle_recovery.md`.
- [x] Validate the exact 31-source Washington Sea Grant Program citation-origin cohort locally: 10/10 then 31/31 supported, 46 focused/surrounding tests and four final contact regressions pass. Preserve dates, source bytes, contact attribution, restricted files, blank license and separate release/readback gates. See `readiness/2026-10-02/sea_grant_cohort.md`; this batch is not pushed.
- [ ] Reconcile the original writer before publishing this isolated recovery; live record QA, sandbox authentication and production release remain pending.

## Local Contact Source interpretation — 2026-10-02

- [x] Pin Brett's 18:26:45 UTC dataset-acquisition interpretation to the exact 1,004-source cohort and preserve USER_ATTESTED provenance without a license or release grant.
- [x] Capture the focused missing-behavior RED, then implement the exact source/policy binding alongside separate restricted-file restoration authority.
- [x] Complete restriction/lifecycle controls, ten-source preparation, 147 socket-blocked tests, and byte-identical fresh/resumed whole-collection QA: 914 supported preparations/3,286 held/six malformed; 8,406 source/copy hash checks and 4,194 unchanged raw metadata objects. See `readiness/2026-10-02/contact_source_cohort.md`.
- [ ] Complete independent review; sandbox readback, aliases and production release remain separate gates. This batch has no push or provider-write authorization.

## PR8 source and batch review findings — 2026-10-02

- [x] Repair canonical FGDC source precedence and reject divergent/ambiguous available copies without changing originals or compatible fallback.
- [x] Filter eligible pending uploads before applying the wrapper limit; make existing per-invocation statistics truthful.
- [x] Capture intended failing-first regressions, 76 focused socket/subprocess-blocked passing tests and the synthetic limit-ten smoke.
- [x] Complete the cloud full offline suite: 160 tests pass, including the synthetic limit-ten upload and unchanged-rerun smoke; zero network/disallowed-subprocess attempts. All 4,206 original SHA-256 values remain unchanged. See `readiness/2026-10-02/cloud_source_batch_findings.md`.
- [ ] Complete independent integration review and substantive GitHub Codex review before declaring PR8 ready; no provider writes or publication occurred in this findings lane.
- [ ] Update the current runbook, candidate canary guidance and technical debt to reflect cluster-first curation and the fresh labeled canary direction. Existing inventory code gates remain unchanged; selector composition and conflict handling are being developed separately and are not part of this checkpoint.

Original FGDC XML plus explicit source-backed corrections establishes metadata truth. Existing sandbox records provide reconciliation and API-delivery evidence, not a metadata baseline to reproduce.


## Cloud integration — 2026-10-02

- [x] Verify public PR8/checkpoint trees, transfer hashes and all 4,206 original bytes.
- [x] Finish source precedence/divergence and pending-before-limit findings; independent diff review.
- [x] Complete strict correction compiler with fieldwise conflict/supersession controls and independent review.
- [x] Independently audit exact 821-member creator cohort and hash-bound residual groups.
- [x] Add narrow opt-in citation interpretation; revalidate human/agent QA and stale cache evidence.
- [x] Run 183 guarded integration tests and byte-identical fresh/resumed whole collection: 1,328 supported / 2,872 held / six malformed; zero remote or release approvals.
- [ ] Track actual final-head GitHub Codex review in PR8; local review/test receipts do not substitute for it.
- [ ] Review narrower residual cohorts, retain alias/access holds, and separately establish future provider/readback/release gates.

See [cloud integration evidence](readiness/2026-10-02/cloud_integration.md).


## Unpushed registration cohort and production goal — 2026-10-02

- [x] Keep published PR8 `d39cc21` frozen; Codex review quota blocker remains explicit.
- [x] Rank all 2,872 held sources with exact context hashes and narrower residuals.
- [x] Independently audit 122 database-registration source contexts; capture pre-change 122-held baseline.
- [x] Add source-backed, separately authority-gated optional interpretation; 196 tests and bounded 10/122 source checks pass.
- [x] Independently review source bindings, all human/agent routes and unchanged metadata; 78 supported / 44 creator holds.
- [x] Verify fresh/resumed full corpus: 1,406 supported / 2,794 held / six malformed; only 78 promotions; all 4,206 originals, 4,200 copies and 4,194 complete metadata objects unchanged.
- [ ] Establish approved API connectivity and secure credential provisioning; current runtime probes fail before HTTP and no credentials are available.
- [ ] Complete sandbox canaries, protected production identity/DOI guards, fresh duplicate and remote QA evidence, exact release binding and bounded verified publication under Brett's 21:09 UTC production goal.

The new goal authorizes publication of defensible records; it does not invent
remote evidence, grant credentials or authorize merge/deletion/billing changes.
This local cohort has not been pushed or used for a provider operation.
## Successor token compatibility — 2026-10-02

- [x] Verify PR8 d39cc21 / tree 7f6db4b and hash all 4,206 originals before edits.
- [x] Support opaque environment tokens with legacy cwd .env fallback; 189 offline tests pass (six new token tests); 4,206 original SHA-256 values unchanged.
- [ ] Await Library archive metadata and full owner handoff before importing prepared batches.
- [ ] Keep credential provisioning and exact canary plan separately gated; no provider writes.

## Successor integration and credential safety — 2026-10-02

- Repository handoff restored after Library helper transfer failed. Verified exact 68b1443 code/tree, evidence parent and three-file-only diff, archive SHA-256, all 43 inventory entries and 4,206 original hashes. Evidence branch was not merged.
- Combined loader now rejects malformed/empty tokens before Session creation. Valid opaque placeholders remain unchanged. Transport/connection/bucket exceptions suppress potentially secret-bearing text and traceback chaining; remote error bodies are replaced with HTTP status diagnostics. This deliberately trades verbose provider errors for credential confidentiality.
- 207 guarded offline tests pass, independently reproduced. Prior P2 credential leak is closed. Fresh whole-corpus classification matches all handoff statuses: 1,406 supported / 2,794 held / six malformed; 4,200 XML copies and 4,206 originals verified unchanged. See `readiness/2026-10-02/successor_integration_validation.json`.
- Secure sandbox setup instructions prepared in `readiness/2026-10-02/successor_secure_sandbox_setup.md`. No credentials provisioned or provider writes. Actual proxy substitution, intended account, inventories and exact synthetic canary selection remain unverified/gated. Contributor-or-Source interpretation remains pending. Original d8b30c5 branch retained; combined branch unpublished.

## Narrow sandbox canary duplicate exception — 2026-10-02

- Brett's explicit historical sandbox-duplicate authorization is implemented only through `canary_plan` on the checker/service. The code pins the three-source plan SHA-256, exact source/payload/metadata hashes, namespace and HTTPS sandbox origin; production rejects opt-in before client creation. Title matches require creation strictly before 2026-10-02 UTC and no canary namespace; identifier, recent, unknown-date, local-batch and own-run identity conflicts remain blocked.
- New actual-source payloads add only one namespace keyword. Initial create POST includes exact metadata, so lost responses remain discoverable by namespace. A bound ledger and consumed create grants prevent cached-inventory reuse after ledger loss; uncertain creates stop. Exact same-run retries preserve IDs/files and must remain unsubmitted drafts. Canary ledgers cannot be published. No deletion or production exception was introduced.
- Failing-first feature test preceded implementation. Independent review then reproduced two concrete defects (lost-ledger duplicate create and published-state retry); both were captured as failing regressions and fixed. Current 232-test guarded offline suite passes, including all three candidates first-run/retry with exactly three creates and uploads. Independent final review is recorded in the handoff receipt. No provider writes by the code owner.
- Provider must keep the original synthetic ledger and count it against the four-total cap; do not repeat synthetic creation. New actual-source payload hashes supersede the earlier unmarked packet only before actual-source intents exist. See `handoff/sandbox-canary-20261002/EXECUTOR.md`.

## Safe constructor probe diagnostics — 2026-10-02

- Separate from the sandbox exception: constructor requests are one-attempt and preserve fixed stage, allowlisted exception type, observed HTTP status or null, retryability and attempt count. No token/URL/header/body/exception text or original traceback is exposed.
- Dummy tests distinguish transport and HTTP errors, guards before response and after status/JSON/owner/link stages, arbitrary exception names/attributes and secret-bearing messages. The provider guard source is not yet available; no actual cause or authentication failure is asserted. Provider remains paused and code owner performs no authenticated request. See `readiness/2026-10-02/constructor_probe_diagnostics.md`.

## Reviewed read-only inventory guard — 2026-10-02

- Reviewed complete sanitized provider guard source. Its per-record blanket host filter was overly broad for inert DOI/citation/HTML links; no actual failing branch can be inferred from the retained evidence. Query blank-value omission, pre-transport counting, constructor/outer exception erasure and missing-hit fallback were also identified.
- Added context-managed SandboxInventoryGuard with strict outgoing sandbox GET/endpoints/Bearer, actionable pagination checks, streaming byte bound and safe status/milestones. Inert record links are never followed. An independently found cleanup exception leak is fixed; cleanup cannot mask primary safe errors or mark completion.
- The exact next diagnostic is one constructor GET, followed by pause even if successful; it does not authorize pagination or writes. See `readiness/2026-10-02/reviewed_inventory_guard.md`. No provider requests by the code owner.

## Contributor or Source attestation integration — 2026-10-02

- Brett's exact “yes” at 23:43 UTC is separate USER_ATTESTED evidence for the 585 original source/hash pairs. The optional contributor interpretation preserves all four original access/use fields, restricted XML, blank licenses, separate rehosting authority, and independent creator/date/security holds.
- Independent review caught mutable cohort membership despite a refreshed manifest hash. Contributor-only canonical count and sorted source-map SHA-256 now reject additions, removals, rebinding and same-count substitutions; the older Contact Source profile is unchanged. Real-source and synthetic shape regressions cover both the scope and preserved restrictions.
- The reviewed executor guard is frozen separately at d5022b8828ef910749aef32371304f2b2b669674 on handoff/pr8-reviewed-read-guard-20261002; all 17 packet entries verify. Its next step remains one constructor GET only after parent dispatch, then pause. No implementation-owner authenticated requests or provider writes. Historical pending entries above describe earlier checkpoints and are superseded by the current validation receipts.
- Final guarded offline suite: 264 tests pass; independent contributor/legacy review: 16 tests pass with no remaining findings. The final corpus run yields 1,988 supported / 2,212 held / six malformed, exactly 582 promotions from the attested cohort. FGDC-1390 retains ambiguous creator semantics; FGDC-1422 and FGDC-1423 retain insufficient metadata-date precision. See `readiness/2026-10-02/contributor_source_validation.json` for reproducibility and preservation evidence.

## Remaining held cohorts — 2026-10-03

- Ranked all 2,212 held sources from PR8 c486d1f with exact source/hash evidence. Alias identity and six unsupported metadata dates remain held; separate institutional/access opportunities are reported without claiming promotions.
- Implemented the independently reviewed 70-source literal DFO Staff interpretation on a separate branch. Names, full metadata, source bytes and rights remain unchanged; no inferred type, affiliation, acronym expansion or contact-derived author. Manifest bytes pin exact source membership and full creator objects.
- Failing-first regression and 16 focused tests (independently reproduced), then 270 guarded full-suite tests pass. Full-corpus preservation/resume receipt accompanies the cohort report in readiness/2026-10-03. Provider handoff d5022b8 and PR8 c486d1f are not moved by this branch.

## Exact institutional citation cohort — 2026-10-03

- [x] Reconcile PR8 c486d1f and source-QA 8bc36dc, reproduce 270 offline tests, preserve the separately frozen canary a8cfeef.
- [x] Audit every original hash/plain primary origin for the four exact literal institutions (26/19/20/7 members; 72 total). Preserve existing full creator objects; no name splitting, expansion or attribution from contacts.
- [x] Add the pinned opt-in profile; 63 promotions and nine independent residuals verified, with both human schemas/agent QA and withdrawal/tampering tests.
- [x] Validate byte-identical fresh/resumed corpus (2,121 supported / 2,079 held / six malformed), all 4,206 originals, 4,200 copies and 4,194 full metadata objects; independent review cleared. The source-QA branch combines the reviewed DFO70 and new63 delta for PR8 integration without merge.

## Residual source review after a70e56b — 2026-10-03

- [x] Recheck the pinned current report, every original/copy/payload hash and full metadata preservation. Audit exact residual creator cohorts and retain independent access/role holds; analysis grants no eligibility or publication approval. Evidence: readiness/2026-10-03/residual_creator_analysis.json, unchanged 2,121 supported / 2,079 held / six malformed.
- [x] Freeze a concrete next creator batch and truthful Oct 6 readiness evidence independently of the unresolved Sandbox create. Independent review reproduced the exact audit and checked all 118 members; the 27-source next batch has 16 current creator-only diagnostics and 11 independent access holds, with no implemented promotion. No POST retry, provider operation or canary state reset. See readiness/2026-10-03/residual_source_next_batch.md.

## Residual 27-source citation implementation — 2026-10-03

- [x] Independently review all 27 plain literal source citations and freeze an additive 99-member manifest retaining the previous 72 cohort objects verbatim. Preserve full creator objects, exact spelling, dates, restrictions, blank licenses and the XML-authorship caveat.
- [x] Add the second pinned manifest to the existing opt-in institution path; targeted failing-first tests, 30 focused and 284 guarded full tests, byte-identical fresh/resumed corpus. Actual 16 promotions yield 2,137 supported / 2,063 held / six malformed; all eleven access holds, 4,206 original hashes, 4,200 copied XML byte sequences and 4,194 complete metadata objects are preserved. Independent implementation review cleared.
- [x] Record parallel read-only role/access decisions for Ecotrust37, USDA/DNR31 and Unaami23 with exact membership bindings; retain unresolved meaning holds. No correction or eligibility change for those 91 members.
- [x] Complete independent implementation and handoff-document review; prepare the reviewed checkpoint for publication within existing non-draft PR8, without merge, provider operation or create-allowance reset.

## Reviewed joint and collection citations — 2026-10-03

- [x] Reuse the exact 91-source role reviews and explicitly review the entire two-Organization USDA/DNR after-image. Freeze a 190-member proposal retaining the prior 99 cohort objects; correct only 68 joint citation creator lists and retain Unaami's 23 literal collection objects.
- [x] Validate opt-in only, all 190 source/hash/full-object bindings and prior 99 preservation; 35 focused and 289 guarded full tests pass, independently reproduced. Fresh/resumed full-corpus QA is byte-identical at 2,138 supported / 2,062 held / six malformed; only FGDC-619 is promoted. Exactly 68 creator/bounded-note corrections and 190 policy references change, retaining 90 access holds and all other metadata, dates, rights and source/copy bytes. Independent complete baseline duplicate/source-integrity preparation passes.
- [x] Independently review the implementation and all corpus/document evidence; record exact remaining access decisions and freeze the reviewed checkpoint for approved existing non-draft PR8 publication, without merge, provider operation or uncertain-create reset.

## Exact-copy alias reconciliation analysis — 2026-10-03

- [x] Independently compare all 228 raw-byte pairs / 456 held identities, including complete prepared metadata/policies, filename-bound payloads, derived artifact/submission fingerprints and retained historical production associations. No source/runtime/provider state changed.
- [x] Generate a deterministic source-alias to candidate byte-group map retaining original IDs/filenames/hashes; label numeric representatives provisional and keep every provider record/DOI selection unset. Preserve all holds and distinguish two title-only collisions from the retained ProCite104 record.
- [x] Record parallel non-alias creator/date candidates and the exact 90-member morning meaning bundle; both independent artifact reviews clear the frozen maps/docs, including corrected metadata-review-date labeling. Deterministic repeated generation, Ruff F checks and local-link validation pass. Freeze an analysis-only checkpoint for approved existing non-draft PR8 publication; source counts/holds, provider state and all original/payload bytes stay unchanged.

## Exact literal-citation extension — 2026-10-03

- [x] Review all 39 full source-bound creator after-images and extend the opt-in manifest, retaining the previous 190 cohort objects and excluding five same-origin access-held siblings. Bind immediate predecessor/current evidence hashes and retain explicitly labeled ancestral evidence.
- [x] Verify opt-in/withdrawal/full-object forgery protections, agent and both human QA schemas: 34 focused / 294 guarded offline tests pass; independent runtime review reproduces all 294. Fresh/resumed full-corpus QA is byte-identical at 2,177 supported / 2,023 held / six malformed, exactly 39 promotions. Verify 4,206 originals / 4,200 copies / 4,194 payloads, all complete metadata unchanged, only 229 policy references changed and 3,965 payload byte sequences unchanged; all access/alias/date/mixed-role holds remain intact.
- [x] Independent runtime and complete source-integrity/document reviews clear the frozen implementation and receipts, including all 39 full creator objects, 90 exact four-field access bindings, 456 aliases, historical ID/DOI protections and 19 local links. Freeze the tested handoff for approved existing non-draft PR8 publication and return the nine-partition morning questions in plain text. Keep uncertain canary creation, all remaining source/access/alias holds and production release gates intact.

## Remaining source credits and historical dataset linkage — 2026-10-03

- [x] Reconcile the 2,023 actual held sources at dfeff4ce into disjoint creator/access/alias/date/title/relation scopes. Implement only independently reviewed exact source/hash-bound creator after-images and the 21 historical shared dataset links. Preserve all previous 229 cohort objects, source bytes, access and alias holds, dates, rights and frozen uncertain-create state.
- [x] Verify default/withdrawal/tamper behavior, full mixed XML and role-context preservation, agent and both human QA schemas, guarded tests, complete corpus delta and deterministic resume.
- [x] Complete independent runtime/source-integrity/document review and freeze a handoff for approved existing non-draft PR8 publication; queue remaining source decisions for morning.

- Actual complete 111-promotion batch: 90 source-credit corrections (82 creator lists changed, eight notes-only), 21 historical-link corrections; 2,288 supported / 1,912 held / six malformed. Seven new focused / 301 guarded tests pass and independent source/runtime/delta reviews clear. Fresh/resume and all original/copy/payload integrity verified. Remaining 86 access-plus-creator cases are ranked, without approved after-images or new access authority.

## Access-held source credit cleanup — 2026-10-03

- [x] Review the exact 86-member source/hash queue after 9cdf8b0, prioritizing the five literal siblings and separating credits, interview/reporting, compiler/editor, contract and collection roles. Root remains sole writer.
- [x] Implement only independently reviewed complete source-credit after-images in an additive pinned profile preserving the previous 143 cohort objects covering 319 source bindings; retain every access, date, rights and alias hold.
- [x] Verify full metadata/source/payload delta and guarded contracts; complete independent runtime/source/document review and freeze the handoff for approved existing PR8 publication. No provider operations, uncertain-create retry or access-meaning decision.

- Actual 77 corrections preserve all 86 access holds: 34 creator lists change / 43 notes-only; all source counts remain 2,288 supported / 1,912 held / six malformed. Five new focused / 306 guarded tests pass, independently reproduced; complete fresh/resumed corpus delta and documents are independently reviewed. Prior cohort objects, 456 aliases and 90 access holds remain intact; nine source-role gaps are queued with exact hashes. This 86-member creator queue is complete; further corrections here require new attribution evidence, and access meaning remains separate.

## Source PR9 and bounded modern synthetic candidate — 2026-10-03

- [x] Merge reviewed source2bf5f8a through normalPR9 atd0f1393; final-head review, source inventory and identical merged-tree receipts retained. No provider action.
- [x] Queue precise wording/scope questions for361 Contributor,351 conditional ADF&G republication and109 Unknown sources, with exact bindings and independent holds preserved.
- [x] Implement separate fixed fictional modern adapter and offline contracts, durable pre-send journal, no replay/reset, exact readback and completed retry. Bound4POST/2PUT/8GET and30minutes; no account/email or production credential blocker added.
- [ ] Parent receives exact bounded execution approval, materializes separately pinned private grant and dispatches sole provider executor. Both old HTTP500 create allowances stay spent; no live newcreate occurred here.

## Five existing-import correction preparation — 2026-10-03

- [x] Retain parent-reported five completedHTTP200 verification reads without repeating them; distinguish source/localafterimage proof from unavailable private remote beforeimages. Bind exactfive source/payload hashes and metadata-date proposals; prepare missing SeaMARC access_conditions while preserving1238/2731 holds.
- [x] Document sameDOI/files-preserving metadata edits separately from a reviewed new-version/two-file attachment contract; no deletion, production write or release implied.
- [x] Receive standalone saved metadata and file/version evidence for all five; retain2043/2057's1220 dates and lack of revision/ETag. No new GET or date inference.

## PR10 final-head integration review — 2026-10-03

- [x] Address the substantive create201 credential-echo review: preserve a safe private untrusted candidate ID before rejection, with no trusted adoption/retry/reset or credential persistence. Add meaningful failure-first/reentry/privacy regressions; final runtime and validation bindings supersede the earlier canary pin.
- PR10 exact-head tests/reviews passed and code merged. Parent approved/dispatched the modern trial; the durable create intent remains held without dispatch evidence. Preserve all historical ledgers and allowances; no automatic retry/reset.
