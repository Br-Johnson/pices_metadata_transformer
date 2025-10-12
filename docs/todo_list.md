# FGDC → Zenodo Sandbox TODO List

_Last updated: 2025-10-11_

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

- [ ] Run `python3 scripts/verify_uploads.py --sandbox --output output --log-dir logs --limit 20` to confirm metadata/file alignment.
- [ ] Publish a sandbox subset (`python3 scripts/publish_records.py --sandbox --output output --limit 10`) once verification passes; document results and issues.
- [ ] Optionally spot-check individual records using `python3 scripts/record_review.py <FGDC-ID>` and log observations beneath this item.

### 7. Orchestrated Runs

- [ ] Dry-run the orchestrator (`python3 scripts/orchestrate_pipeline.py --sandbox --limit 10 --interactive`) to validate step sequencing and state persistence.
- [ ] Execute a full orchestrator pass without limits once satisfied; ensure `output/pipeline_state_sandbox.json` and summary files show completion.

### 8. Final Review & Cleanup

- [ ] Review random records in the Zenodo sandbox UI to confirm community placement and metadata fidelity.
- [ ] Clear or refresh `output/cache/` when performing broader duplicate scans; record when cache resets occur.
- [ ] Capture lessons learned or production-readiness adjustments for inclusion in README/`AGENTS.md`.

## Commit & PR Guidelines

- One logical change per commit; reference checklist items in commit messages.
- Group related commits into focused PRs (e.g., “Pre-upload safeguards”) and include command outputs or log summaries in descriptions.
- Update this TODO list and supporting docs alongside code changes so the team always has an accurate view of project status.
