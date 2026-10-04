# Approved identical-pair record targets

This increment follows merged source15 PR27 at
`dc10c9955e0e28ac1069d8b50ad729e40a255697`. The finite
[recorded user approval](alias_pair_approach_authority.json) permits one restored
record per identical pair, retaining both source IDs, original files and
provenance. It supplies neither a historical canonical filename nor production
record/DOI reconciliation. All provider operations remain separately assigned.

## Measured result

| View | Supported source semantics | Held | Malformed | Total |
|---|---:|---:|---:|---:|
| Preserved legacy source-file ledger | 3,696 | 504 | 6 | 4,206 |
| Unchanged singleton target projection | 3,696 | 48 | 6 | 3,750 |
| New pair targets (456 original files) | 204 | 24 | 0 | 228 |
| Combined unique record targets | 3,900 | 72 | 6 | 3,978 |

The legacy ledger still holds all 456 paired source rows. Fresh semantic assessment
of both members finds 408 supported member assessments and 48 held; those are
files, not 456 independent upload targets. All 228 class targets remain
`upload_eligible=false`, including the 204 with supported source semantics.
The 24 additional-held content IDs are unchanged from the prior source15 analysis.

The [measurement receipt](alias228_target_measurement.json) records a fresh
ten-source/five-pair smoke, exact repeated preparation, then fresh classification
of all 456 sources and assembly of all 228 targets. It checks both actual originals
and policies, complete common metadata, exact non-notes metadata, and display
notes changed only by pair provenance and the class artifact digest. The
[target index](alias228_record_targets.json) separately projects every singleton
from the unchanged byte-pinned source ledger.

All selected 456 originals were read and hash-checked again. All 4,206 source-ID
and hash bindings are retained from the pinned ledger; this measurement does not
reread the 3,750 unselected originals. Their preservation is separately supported
by source15's complete inventory and the unchanged `FGDC` Git tree
`6c509a3e62252888a6709d1df94bcf109b83241b`. No original XML path changes in this diff.

## Contract and migration boundary

The [version-2 example](../../../contracts/examples/original_xml_content_class_v2.json)
is the actual FGDC-2953/3181 target, not a template granting authority to other
sources. Both files have their own identity/policy bindings and exact transfer
size/checksums. Canonical historical catalogue/provider IDs and DOI remain null.
The [ADR](../../adr/0003-finite-identical-xml-record-targets.md) describes the additive
migration; version-1 singleton contracts and historical ledgers remain intact.

Class payloads belong in a separate output directory, never legacy `zenodo_json`.
Missing, changed or disagreeing members yield held diagnostics without a complete
artifact. `validate_class_target` rebuilds against current evidence and both files.
Shared source-backed operation, verification, adoption and approval paths refuse
member IDs, known raw hashes, renamed originals, class-shaped bindings and
protected selected registry evidence. No environment, flag or legacy approval can
enable them. Upload batches, the compatibility upload CLI and limited pre-upload
checks apply selection before client construction. Verifier construction checks
the full successful registry before its later verification limit. Generic account
audits and raw transport helpers are outside this selected-source guard.

The dormant replacement helpers now refuse explicitly when enabled; their DELETE
bodies are removed. Source-only metadata preparation and assessment remain usable.
No class create/resume, two-file provider transfer/readback, production reconciliation,
QA/release or publication implementation is included. Future reviewed execution
must preserve existing provider records/DOIs and both original files.

## Reproduce offline

From this checkout with the public Python requirements installed, choose a fresh
output directory and an actual, timezone-aware assessment time:

```bash
python -B docs/readiness/2026-10-04/measure_alias228_targets.py \
  --repo "$PWD" \
  --output /tmp/pices-alias228-reproduction \
  --reviewed-at "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

The helper installs the portable offline guard before importing repository runtime,
clears the environment and uses dummy credentials. It pins current profiles and
captures/rechecks every public input actually read. The successful measurement
used `2026-10-04T19:13:20Z`; an assessment at a different time intentionally has new
time-bound payload/contract hashes. Its inputs and outputs remain in
`/tmp/pices-alias228-targets-measured-v2` for local review. The committed index paths
are relative to that generated `record_target_view` directory. The helper recreates
all class payloads and both original copies; only the example is committed here.

The first smoke failure is [retained](alias228_first_measurement_failure.json):
class display notes initially retained CRLF while the singleton loader normalized
display newlines. The shared loader now supplies note text, while raw original
bytes and hashes remain unchanged. The measurement helper was not weakened.

[134 focused guarded tests](alias228_focused_tests.json) passed after that correction,
covering normal singleton selection plus identity/caller/registry/QA conflicts,
missing/changed inputs, repeat preparation and v1 preservation. There were zero
unexpected guard events in tests or measurement. The focused receipt predates
packaging the measured example and is local evidence; the PR's actual CI and
independent current-head Codex review determine merge eligibility.

## Frozen evidence

| File | SHA-256 |
|---|---|
| `approved_alias_representation_228.json` | `9e45fc869b0fe03220b44734cf429129f78dc93eb9fd20bf9b802398b684dda6` |
| `alias228_target_measurement.json` | `c39a9d22b5a1bd6709ac0003c0c2bb3c42f7af86a4fc649ed22ac6c1ad266c32` |
| `alias228_record_targets.json` | `fd9bcba857c5d9816f44bbca0ac4c826c10527f64a7e6330468ee2fe814981d4` |
| `measure_alias228_targets.py` | `125726c82c3b9a773f834718a63d93fef782de2c6e282911498bb9483c2e4bf9` |
| `original_xml_content_class_v2.json` | `327bad635c93494cc316fbf48a15856c3f5d97ca4bd852130a3c2e9f737bdff2` |
| Preserved source15 ledger | `4a4ef82f9da793c0a83cd58f6388991dd38f7a5f92947b2d089855b259af4e4a` |
