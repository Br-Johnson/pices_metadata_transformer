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

## 2025-10-15

### Split creator tokens
- **Observation:** Zenodo sandbox records show creators split into individual words (e.g., “National Oceanic”; “Office”) instead of the expected organization name for NOAA-sourced metadata.
- **Impact:** Published metadata misrepresents provenance and breaks downstream duplicate detection relying on exact creator strings.
- **Next step:** Revisit the transformation step that tokenizes organization names; ensure legacy FGDC `origin` values map to a single `person_or_org` entry.
- **Resolution (2025-10-15T05:21Z):** Updated creator parsing treats organization strings as atomic; iteration loop sample (`FGDC-1001.json`) now preserves the full NOAA organization label.

### Placeholder text leakage
- **Observation:** Description and purpose fields emit literal placeholders such as “No abstract was givien” and “No purpose was givien,” including a typo from the FGDC source.
- **Impact:** Public records contain low-quality messaging and visible spelling errors; reduces curator trust and usability.
- **Next step:** Normalize placeholder phrases during transformation—either drop them, replace with empty fields, or move the original FGDC notice into Zenodo `notes`.
- **Resolution (2025-10-15T05:21Z):** Transformer now replaces placeholder abstracts/purposes with neutral guidance (`Abstract not provided…`); verification via iteration loop confirmed sanitized output and notes.

### Publisher fallback
- **Observation:** Despite injecting the PICES publisher in the DTO, published sandbox records still list `Publisher: Zenodo`.
- **Impact:** PICES branding is missing in the public metadata; contract requirements to credit the organization are unmet.
- **Next step:** Confirm whether the legacy deposition API allows overriding `metadata.publisher`; if so, update the upload payload. Otherwise, document the limitation and explore post-publish patching options.
- **Status (2025-10-15T05:21Z):** Transformer now forces `metadata.publisher = "North Pacific Marine Science Organization"`; need to run the next sandbox upload batch to verify the UI reflects the change.

### Stale upload verification targets
- **Observation:** Iteration loop verification (2025-10-15T05:21Z, `--limit 10`) reports `record_not_found` for FGDC-3754 through FGDC-3758 despite entries in `upload_log.json`.
- **Impact:** Upload registry may reference depositions that never completed or were purged, inflating verification failures and masking real regressions.
- **Next step:** Audit `upload_log.json` and Zenodo sandbox to reconcile these entries; remove or refresh stale registry records before the next publication pass.
- **Resolution (2025-10-15T05:24Z):** Purged FGDC-3754–FGDC-3758 from `output/state/uploads/upload_log.json` and `uploads_registry.json`. Re-run verification to ensure the iteration loop exits cleanly.
