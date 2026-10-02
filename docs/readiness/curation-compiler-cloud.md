# Cloud curation compiler validation

Parent-authorized implementation completes the unsafe local checkpoint imported
as `9811a2878f276f798585a16a43db2fdaa894d69e` (public PR8 base `35b01a2`).
Only compiler, its tests, and compiler documentation changed in this lane.

The original six tests, previously 18 negative failures plus a missing-loader
error, now pass. Added coverage verifies all active equal-value owners must be
superseded, exact residual selectors, source-bound artifact tokens, real fixture
artifact validation, source changes between compilation/validation, CLI source
output/hardlink protection, preserved structured evidence, deterministic audits,
malformed exclusions and symlink rejection.

Guarded focused command uses the cloud shared venv and transferred socket/
subprocess guard adapted solely to this worktree path:

```
PYTHONPATH=/tmp/pices-curation-cloud-guard:/workspace/pices-curation \
/workspace/pices_metadata_transformer/venv/bin/python -m unittest \
 tests.test_curation_batches tests.test_artifact_contract tests.test_content_classification -q
```

Result: 34 tests passed; log `/tmp/pices-curation-cloud-tests.log`.
No guard events were recorded. Tests operate only on temporary XML fixtures.
No real correction cohort was applied, and no provider operation occurred.
Independent frozen-diff review and combined integration suite remain the
integration owner's gates. The transferred candidate requires explicit schema
migration and independent census/evidence review; it is not automatically approved.

Residual limitation: outputs are not a transactional pair across two filesystem
paths. Every transformation validates before writes, and existing files are
never overwritten. Consumers must require a successful CLI exit plus both files.
