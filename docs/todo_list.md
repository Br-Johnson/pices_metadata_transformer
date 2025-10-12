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
- [ ] Document any new warnings that require mapping or policy decisions.
- [] Add Publisher = 'North Pacific Marine Science Oorganization' to all records

### 3. Pre-Upload Screening

- [ ] Execute `python3 scripts/pre_upload_duplicate_check.py --sandbox --output-dir output --log-dir logs --limit 50` to sanity check duplicate logic.
- [ ] Run the full scan, then compare `output/safe_to_upload.json`, `already_uploaded_to_zenodo.json`, and the uploads registry for consistency.
- [ ] Note titles flagged as similar/duplicate and determine remediation steps.

### 4. Upload Dry Run & Logging

- [ ] Perform `python3 scripts/batch_upload.py --sandbox --output-dir output --batch-size 5 --limit 5 --interactive` to validate registry/log updates and attachment handling.
- [ ] Review `output/uploads_registry.json`, `batch_upload_log_*.json`, and `upload_log.json` to confirm batch numbers, timestamps, and FGDC paths.
- [ ] Decide on batch sizing for the full upload, documenting rationale here.

### 5. Post-Upload Verification

- [ ] Immediately after each batch, run `python3 scripts/deduplicate_check.py --sandbox --output-dir output --log-dir logs --hours-back 6` and capture findings.
- [ ] Generate audits (`python3 scripts/upload_audit.py --output-dir output`) and metrics (`python3 scripts/metrics_analysis.py --output-dir output --save-report`) and compare to baseline.
- [ ] Produce enhanced metrics (`python3 scripts/enhanced_metrics.py --input output/zenodo_json --output output/enhanced_metrics_sandbox.json --log-dir logs`) and note regressions.

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
