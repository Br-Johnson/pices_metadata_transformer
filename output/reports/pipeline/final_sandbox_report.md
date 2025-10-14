# PICES FGDC → Zenodo Sandbox Migration – Final Report (2025-10-12)

## Executive Summary
- Processed 4,204 FGDC records through the orchestrated sandbox pipeline and confirmed 4,096 successful uploads in Zenodo, with every deposition now published to the PICES sandbox community.
- Identified 108 FGDC packages already published in the sandbox prior to this run; preserved originals and documented them in `output/reports/uploads/duplicate_records_sandbox.csv`.
- Resolved 16 metadata verification mismatches caused by legacy character encoding (degree symbols, en dashes, and umlauts) via targeted JSON and deposition updates.
- Two FGDC sources (`FGDC-3373`, `FGDC-3484`) contain only null bytes and remain outstanding; new source files are required before they can enter the pipeline.
- Generated a comprehensive PDF briefing with charts at `output/reports/pipeline/final_sandbox_report.pdf` and packaged both data directories as `output/data/original_fgdc.zip` and `output/data/zenodo_json.zip` for hand-off.

## Orchestrated Run Timeline
- Batch sizes executed sequentially: 25 (limit 100), 50 (limit 500), 100, 150, 200, and 300.
- Duplicate lookback reduced to 2 hours for all production-scale runs per request.
- Final pipeline execution (`scripts/orchestrate_pipeline.py --skip-transform --skip-upload --resume`) completed with zero errors and produced `output/reports/pipeline/pipeline_summary_sandbox.json`.

## Upload & Audit Metrics
- Latest audit (`output/reports/uploads/upload_audit_20251012_052044.json`): 8,395 transfer attempts, 8,383 successes, 12 transient failures (broken pipes and simulated test entries later reprocessed). Overall success rate 99.86%.
- Verification (`output/reports/verification/verification_summary.txt`): 4,096 / 4,096 records confirmed 1:1 with Zenodo metadata and file inventories after remediation.
- Deduplication checks after each batch remained clean (no sandbox duplicates created).

## Data Quality Highlights
- Enhanced metrics (`output/enhanced_metrics_sandbox.json`): average quality score 86.5 with distribution – 86 excellent, 3,078 good, 983 fair, 57 poor.
- Field coverage: 100% critical & important fields, 66.7% optional, yielding 85.7% overall metadata coverage.
- Compliance: 100% adherence to Zenodo required & recommended fields, PICES community applied to all uploads, 4,198 open-access compliant records (six flagged below).
- Transformation preservation ratios average 99.4%; unmapped FGDC fields limited to 14 categories (dominated by calendar date variants).

## Discussion Points for Leadership & Data Managers
1. **Pre-existing Zenodo Content** – 108 FGDC records map to legacy sandbox DOIs. Decide whether to refresh those records with the latest transformation or maintain historical metadata. See `output/reports/uploads/duplicate_records_sandbox.csv` for detail.
2. **Open-Access Exceptions** – Six records (`FGDC-767`, `FGDC-779`, `FGDC-832`, `FGDC-854`, `FGDC-4037`, `FGDC-4039`) carry restricted or undefined access flags. Confirm policy alignment before promoting to production.
3. **Corrupted FGDC Sources** – `FGDC-3373.xml` and `FGDC-3484.xml` are null files; replacements from the source archive are required.
4. **Character Encoding Standards** – Degree symbols, en dashes, and umlauts triggered validation mismatches. Recommend adopting UTF-8 normalization in upstream tooling and documenting expected character sets in `AGENTS.md`.
5. **Workflow Artifacts** – Large orchestrator runs generate extensive logs (>8k entries). Capture a retention plan (archive path vs. active path) to keep future dedupe inventories performant.

## Recommended Visualizations
- Quality distribution (Excellent/Good/Fair/Poor) using `summary.quality_distribution` from `output/enhanced_metrics_sandbox.json`.
- Coverage heat map (critical/important/optional) leveraging `summary.field_coverage_stats`.
- Upload throughput per batch using `output/reports/uploads/batch_upload_log_20251012_010554.json` and `..._030621.json`.
- Error trend chart summarizing the 12 transient failures from `output/reports/uploads/batch_upload_errors_*.json`.

## Records & Issues Requiring Human Review
- **Duplicates:** 108 FGDC IDs listed in `output/reports/uploads/duplicate_records_sandbox.csv` (primarily historical sablefish tagging surveys and legacy PROBES datasets).
- **Access Policy Exceptions:** `FGDC-767`, `FGDC-779`, `FGDC-832`, `FGDC-854`, `FGDC-4037`, `FGDC-4039`.
- **Corrupted Sources:** `FGDC-3373`, `FGDC-3484` – request new XML exports.
- **Manual Metadata Fixes:** Degree-symbol & umlaut corrections applied to FGDC IDs 1022, 1027, 1068, 1069, 1124, 1125, 1166, 1200, 1225, 1236, 1780, 2570, 2583, 2588, 2589, 2591 (now synchronized with Zenodo).

## Next Steps
1. Review duplicate titles to determine refresh vs. archive approach and update `docs/todo_list.md` accordingly.
2. Resolve six non-open-access records through policy consultation or metadata updates.
3. Source clean XML replacements for the two null FGDC files and rerun targeted transformation/upload.
4. Document character normalization and duplication policies in `AGENTS.md` / `docs/adr` for cross-team alignment.
5. Prepare production-ready dashboards using the referenced JSON/CSV outputs for stakeholder briefings, and regenerate the PDF via `python scripts/generate_final_report.py` whenever new runs complete.
