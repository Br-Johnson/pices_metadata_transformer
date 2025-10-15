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
  - 2025-10-15T05:21Z: Ran `python3 scripts/iteration_loop.py --limit 10` (transform, validate, duplicate check, verify, metrics). Sample JSON now preserves full organization creators, swaps placeholder abstracts/purposes for neutral text, and sets publisher to PICES. Duplicate check (sandbox) flagged 10/10 as already uploaded (expected), verification succeeded for the first five IDs but reported `record_not_found` for FGDC-3754–FGDC-3758 — investigate stale upload log entries before the next sandbox push.
- [ ] Clear or refresh `output/cache/` when performing broader duplicate scans; record when cache resets occur.
- [ ] Capture lessons learned or production-readiness adjustments for inclusion in README/`AGENTS.md`.
- [ ] Document and socialize production upload + publish strategy (draft-first, monitoring, recovery):
  - In production, keep uploads in draft (no `--publish-on-upload`); trigger publication via `scripts/publish_records.py` after QA sign-off.
  - Monitor publish failures via `batch_upload_log_*` (`publish_failures` list) and rerun `scripts/publish_records.py` for recovery.
  - Track community acceptance and DOI activation through `output/reports/publish/publish_log.json` and Zenodo notifications (no curator approval required for PICES sandbox/community).

### 9. Regression Gate & DTO Hardening

- [ ] Re-run post-merge regression sweep (`batch_transform`, `pre_upload_duplicate_check`, `verify_uploads`, `metrics_analysis`) and capture diffs in `logs/` + `output/` before enabling the new generator.
- [ ] Finalize canonical record DTO schema (document invariants, add unit coverage) and publish 10-sample fixtures under `contracts/examples/odc/` for regression tests.
- [ ] Capture any new anomalies discovered during regression in `docs/tech-debt.md` and schedule remediation tasks.

### 10. Bibliographic Linkage Enablement

- [ ] Build DataCite search adapter (`scripts/matching/datacite_adapter.py`) with documented rate-limit handling and response normalization.【F:docs/bibliographic_linkage_plan.md†L19-L49】
- [ ] Implement Crossref adapter and shared fuzzy matching engine (title/abstract/creator scoring) with configurable thresholds and tests.【F:docs/bibliographic_linkage_plan.md†L32-L44】
- [ ] Create curator review CLI (`scripts/matching/review_matches.py`) that writes decision trails to `output/reports/duplicates/` and supports accept/reject/defer states.【F:docs/bibliographic_linkage_plan.md†L45-L72】
- [ ] Integrate accepted matches into both Zenodo JSON and Plan B JSON-LD generation (`related_identifiers`, provenance notes) before uploads occur.【F:docs/bibliographic_linkage_plan.md†L52-L84】
- [ ] Produce linkage metrics + alerts (counts, confidence tiers, overrides) and surface them alongside existing pipeline dashboards.

### 11. Plan B JSON-LD Catalogue

- [ ] Implement JSON-LD generator and persist outputs to `docs/odc/records/` with deterministic filenames (`<zenodo_id>.jsonld`).
- [ ] Automate sitemap + hosting pipeline (GitHub Pages deploy, optional `w3id` redirects, timestamped `lastmod` values).
- [ ] Add CI validation gates (JSON Schema, schema.org validator, broken-link scan) and emit nightly health summary (`output/reports/odc/harvest_status.json`).
- [ ] Integrate JSON-LD generation into the orchestrator after bibliographic enrichment to ensure outputs reflect the latest DTO state.

### 12. LLM-Assisted Human QA

- [ ] Implement `scripts/extract_review_set.py` to package FGDC summaries, enriched DTO snippets, and anomaly rationale (`--limit` for sampling, default full corpus).
- [ ] Build prompt template + review CLI that logs observations to `output/reports/review/creator_anomalies_<timestamp>.json` without mutating source data.【F:docs/ODIS-plan.md†L90-L99】
- [ ] Pilot targeted run (≤25 records) post-regression to tune thresholds, then schedule full corpus review once JSON-LD validation passes.
- [ ] Create curator triage checklist so mapper adjustments and blacklist updates are captured deterministically before re-running the pipeline.
- [ ] Update orchestrator to include optional LLM review stage and ensure QC artefacts sync with nightly harvest status reports.

## Commit & PR Guidelines

- One logical change per commit; reference checklist items in commit messages.
- Group related commits into focused PRs (e.g., “Pre-upload safeguards”) and include command outputs or log summaries in descriptions.
- Update this TODO list and supporting docs alongside code changes so the team always has an accurate view of project status.
