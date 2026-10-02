# Cloud source and pending-batch findings verification

The findings checkpoint `b9d677d0d74937ea57807211b042aaecd5fe457d` descends from public PR8 base `35b01a265b86125459e1047b30297a4cbcea5210`. Its implementation resolves two audited defects without changing original XML or provider policy.

## Resulting behavior

- Source resolution prefers `FGDC/<id>.xml`, then the prepared original-copy directory, then the legacy output-root location. Every present candidate must be a readable regular file with identical bytes. Divergent copies, directories and dangling symlinks fail before provider calls. Missing canonical sources retain the compatible fallback. Identical symlink aliases remain supported.
- The compatibility uploader filters the caller's ordered subset through the service's eligible pending files before applying its limit. Previously completed records no longer consume a batch slot. Statistics, result lists and histograms describe the current invocation; durable environment-scoped registry entries remain intact. The existing zero-limit-as-unlimited behavior remains unchanged.
- The shared service continues to enforce source hashes, payload hashes, uncertain-creation reconciliation, known-draft retry identity and production duplicate inventory. This change grants no license, release authority or historical sandbox reconciliation exemption.

## Cloud validation, 2026-10-02

The dedicated findings worktree used `/workspace/pices_metadata_transformer/venv/bin/python`; the main-branch setup script was not used as the PR validation gate.

- Full `unittest` discovery: **160 tests passed**. Python audit hooks blocked socket connection/DNS operations and disallowed subprocesses. There were zero blocked attempts. The only permitted subprocess was exact `git rev-parse HEAD` for QA provenance (40 calls).
- The suite includes a synthetic limit-ten smoke: seed one completed record, select ten of the remaining eleven records, create exactly ten mock drafts, and preserve eleven durable success entries. Repeating the completed subset creates zero drafts; publish and delete methods are never called.
- An additional actual-source `batch_transform --input FGDC --limit 10` run generated all ten JSON records and ten byte-identical original copies in isolated scratch output. Its legacy validation correctly **exited 1**, reporting missing open-access licenses for all ten raw payloads. No license was invented. This raw transformation is not a supported technical-XML preparation or authorization for live upload.
- All **4,206** source XML SHA-256 values still match the independently recorded startup census. `git diff --check` passes.

Cloud evidence is retained outside tracked operational state at `/workspace/scratch/pices-findings/`: `offline-suite.log`, `limit10-transform.log`, `source-preservation.json`, and the isolated `limit10-output/` and `limit10-logs/` directories. No provider calls, credential reads, uploads, publication or deletions were performed.

## Review and operational limits

Independent final-diff review and the actual GitHub automated review remain integration-owner gates. Existing root-relative source discovery assumes commands run from the repository root. Pending selection intentionally validates the service's complete prepared directory before restricting the caller subset; an unrelated invalid item fails closed. The resolver does not lock local files against concurrent edits, so source writers must remain stopped during a run. These are existing execution constraints, not authority to alter original sources.

Cluster-first curation and its schema, overlap and source-membership controls are a separate lane. This findings checkpoint does not consume the unsafe compiler WIP or approve any correction cohort. Provider compatibility/readback and production release remain separately gated.
