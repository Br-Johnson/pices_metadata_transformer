# Tech Debt Log

## 2025-10-11

### Upload log drift
- **Observation:** `python3 scripts/batch_upload.py --sandbox --output-dir output --batch-size 5 --limit 5 --interactive` left `output/state/uploads/upload_log.json` unchanged (`len(entries)=2`, last timestamp 2025-10-11T02:29Z) despite four successful uploads in Batch 1.
- **Impact:** Monitoring and audit tooling depending on the log will miss sandbox activity, masking partial failures.
- **Next step:** Inspect `scripts/batch_upload.py` logging flow; ensure both registry and upload log stay aligned in interactive mode.
- **Resolution (2025-10-11T22:15Z):** `_append_to_upload_log` now runs for every outcome; `upload_log.json` shows seven entries after sandbox retest.

### License mapping gap
- **Observation:** FGDC-2284 failed with `Invalid license provided: open`; transformation is currently emitting `license: open`.
- **Impact:** Record cannot reach Zenodo until the license maps to a supported vocabulary (`cc-zero`, `cc-by`, etc.).
- **Next step:** Review license normalization rules in the transformation pipeline; either update the mapping or fall back to storing the raw value in `notes` when uncertain.
- **Resolution (2025-10-11T22:14Z):** Folded “open access / no restrictions” phrases into the `cc-zero` mapping; FGDC-2284 now publishes successfully.

### Enhanced metrics regression
- **Observation:** 2025-10-11T22:33Z run of `python3 scripts/enhanced_metrics.py --input output/data/zenodo_json --output output/enhanced_metrics_sandbox.json --log-dir logs` failed for every record with `calculate_comprehensive_metrics() missing 1 required positional argument: 'file_path'`.
- **Impact:** Enhanced metrics JSON reports 0 files processed, so downstream quality dashboards lose coverage.
- **Next step:** Inspect `scripts/enhanced_metrics.py` and the calculator call signatures; reintroduce the `file_path` argument (or adjust the API) and rerun to restore metrics.
- **Resolution (2025-10-11T22:34Z):** Directory helper locates FGDC attachments and passes paths to `calculate_comprehensive_metrics`; sandbox metrics now cover 4,204 records.

### Legacy verification entries
- **Observation (2025-10-11T23:03Z):** `python3 scripts/verify_uploads.py --sandbox --output output --log-dir logs --limit 20` failed for FGDC-1/FGDC-10 because the script still references `transformed/zenodo_json/...` paths removed after the output reorg.
- **Impact:** Verification success rate capped at 90%; legacy depositions linger in registries without accessible source files.
- **Next step:** Backfill or migrate those early records (copy JSON into `output/data/zenodo_json/`) or prune stale entries from `upload_log.json` before future verification runs.
- **Resolution (2025-10-11T23:09Z):** Migrated FGDC-1/10 log paths to `output/data/...` and regenerated FGDC-1 JSON with both creators; verification now passes 100%.
