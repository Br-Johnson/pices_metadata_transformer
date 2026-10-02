# Correction batches — local implementation checkpoint

This is an unfinished, local-only implementation checkpoint. Do not use the
compiler for real corrections or publication yet. The current happy-path CLI
works, but strict schema validation, duplicate detection and reviewed overlap
handling are deliberately exposed by failing tests and remain to implement.
In particular, the current prototype overwrites overlapping decisions; that is
not the approved final behavior.

The intended workflow is the shared FGDC transformer for common mappings,
followed by the largest coherent source-supported correction batches, then
narrower cohorts, with individual decisions as a residual fallback. Existing
Zenodo sandbox records are API/reconciliation evidence, not metadata truth.
Original FGDC XML remains the provenance baseline and must stay byte-identical.

## Proposed schema and compatibility

The standalone command compiles one or more manifests into ordinary keyed
curator decisions accepted by `scripts.batch_transform --decisions`. No change
to the existing decision interface or priority source/uploader modules is made.
Run from the repository root:

```sh
python -m scripts.curation_batches --sources FGDC \
  --manifest reviewed-batches.json --decisions-out decisions.json --audit-out audit.json
```

Root contract: `schema_version: 1`, `batches: [...]`. Each batch declares:

- `batch_id`, `version`, `reviewer`, timezone-aware `reviewed_at`, `rationale`
  and a nonempty `evidence` list.
- `selector`: declared normalization `strip_xml_text`, plus `fgdc_paths_equal`
  mapping supported exact FGDC paths to ordered lists of source element text.
  This strips surrounding element whitespace and preserves interior text.
- `members`: exact `source_id` and lowercase raw `source_sha256` for every source
  matching that selector, including held records and aliases.
- `correction`: existing `metadata` whitelist (`creators`, `publication_date`,
  `license`), and optionally existing `artifact_policy` and
  `content_classification` declarations. No license correction is currently
  planned. All factual corrections need source-backed evidence.
- Optional `supersedes`: prior batch IDs explicitly reviewed for conflicting
  overlapping fields. The intended rule is that equal values coalesce, disjoint
  fields compose, and conflicting values fail unless reviewed supersession
  explicitly names every prior active batch affecting that field. All review
  provenance must remain in the compiled decision and audit.

The current module checks exact cohort membership and member hashes, compiles
decisions with provenance, and validates actual affected transformations with
the existing Zenodo validator and artifact contract. It also records malformed
source exclusions and a source-inventory digest. The pending schema/overlap
cycle must reject unknown keys/versions, invalid override structures, duplicate
JSON/member/batch IDs and unsupported selector semantics before this is ready.
Fixed source-binding tokens for artifact/content declarations are proposed but
not implemented. A residual explicit source-ID selector is likewise proposed.

No creator or license is guessed. No provider calls, credentials, GitHub edits,
uploads, source XML edits, publications or merge operations are part of this
compiler. Full affected-output validation must pass before outputs are written.

## Checkpoint evidence and next work

Base: public PR8 head `35b01a265b86125459e1047b30297a4cbcea5210`, tree
`0050ae4359183354ed8095475dd0d18ad307f97e`. Worktree:
`/tmp/pices-curation-layer-35b01a2`, branch `fix/pr8-curation-batches`.

The repository `AGENTS.md`, TDD and testing skills were read. The user's direct
authorization for parallel implementation and reasonable design discretion
supplies the requested design confirmation. The integration owner retains
shared runbook/checklist/technical-debt edits; this lane owns only the new module,
tests and this document.

Python runtime: `/Users/brettjohnson/Documents/Codex/2026-09-30/task-4/review-venv/bin/python`.
Offline guard: `/tmp/pices-curation-guard/sitecustomize.py`, copied from the
priority lane with the exact allowed local git-revision cwd changed to this
worktree. It blocks socket access and non-Python subprocesses except that exact
local revision read. System Python lacks dateutil; an older guard was initially
incompatible with this cwd. Both harness issues were corrected before RED.

- Baseline: existing metadata/artifact/content suites, 48 tests passed.
  `/tmp/pices-curation-baseline.log`.
- First RED: the end-to-end CLI compilation test failed because the compiler
  module did not yet exist. `/tmp/pices-curation-red1.log`.
- First GREEN: the same offline CLI fixture passed and originals stayed equal.
  `/tmp/pices-curation-green1.log`.
- Second RED: six tests ran with 18 expected negative/overlap failures plus one
  missing `load_manifest` interface error. `/tmp/pices-curation-red2.log`.
  Production implementation of this cycle is not yet complete.

The source census lane has identified 821 exact primary-citation origin matches
for a three-entry creator correction. Its exact source manifest and evidence
will be handed off separately. No real correction cohort has been compiled or
applied here. Integrate only after the schema/overlap cycle is GREEN, a focused
surrounding check passes and an independent review covers the frozen diff. The
integration owner will run the combined full socket-blocked suite once after
integrating finalized lanes; this checkpoint must not be reported as ready.

The pause was requested because Brett's Mac ran out of application memory. No
background test, full-corpus or provider process remains running in this lane.
The patch and Git bundle preserve tracked work for a supported cloud workspace;
the bundle needs the public base commit as its prerequisite. Offline logs and
guard are separate local evidence and must be copied if migration needs them.
