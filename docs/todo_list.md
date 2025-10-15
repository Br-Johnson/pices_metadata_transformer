# FGDC → Zenodo Sandbox TODO List

_Last updated: 2025-10-14_

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
