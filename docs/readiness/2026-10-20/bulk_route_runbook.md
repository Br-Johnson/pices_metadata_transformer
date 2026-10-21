# Bulk route runbook — 2026-10-20

Operator sequence for [ADR 0013](../../adr/0013-bulk-draft-and-publication-route.md).
Every command runs from the checkout with
`/Users/brettjohnson/.cache/pices-venv312/bin/python -B -m scripts.modern_bulk`
and `--output-dir "$OUTPUT"`, where `OUTPUT` is
`/Users/brettjohnson/Documents/Codex/2026-09-30/task-4/pices-production-operations/output`.
Offline commands may run anywhere; token-bearing commands need the Mac terminal
(the app's Terminal pane), because the token prompt and the Keychain read both
require a TTY. Owner `266679`, PICES community `92279449-f6e1-422d-8610-40802567c58b`.

## Operator wrapper

`pices-production-operations/bin/pices-bulk.sh` wraps the commands below:
`drafts BATCH...` (stops at the first run that does not complete),
`release NAME BATCH...`, `publish NAME` (prompts for the token) and `status`.
Results go to `pices-production-operations/logs/bulk/`. On 2026-10-20 the
app's auto-mode classifier refused provider-touching runs from the Claude
session, so these run in Brett's own terminal unless he allows them.

## Once: inputs and registry

1. Prepared inputs for every source are classified into `$OUTPUT/data`
   (done 2026-10-20 with the runbook manifest set and `--reviewed-at
   2026-10-20T00:00:00+00:00`; the 27 earlier inputs were kept). Never
   reclassify a reviewed source: the wire carries the classification time.
2. Title-twin decisions go to the registry: distinct groups with
   `python -B -m scripts.modern_batch allow --output-dir "$OUTPUT" --name twins-fgdc-N --sources ... --allowed-by ... --note ...`,
   duplicates with `modern_bulk exclude --source FGDC-N --reason ... --decided-by ...`.

## Per batch (at most 250 members)

```bash
python -B -m scripts.modern_bulk plan --output-dir "$OUTPUT" --batch-id bulk-NNN --owner 266679 --built-by "<builder>" --members-file members.json
```

Offline. Builds the `modern-batch-v1` manifest (twin check against every
journal) and `bulk-v1/sheets/bulk-NNN.sheet.json`: per member the source
fields, the wire fields, automatic flags and a membership-seeded sample.

A reviewer agent (not the builder) reads every flagged and sampled row against
`FGDC/<id>.xml`, writes `{"decisions": {...}, "examined": [...], "summary": "..."}`
and records it:

```bash
python -B -m scripts.modern_bulk review --output-dir "$OUTPUT" --batch-id bulk-NNN --decisions decisions.json --reviewer "<reviewer>"
```

Drafts (Keychain token, 6 requests per record, about 5 seconds each):

```bash
python -B -m scripts.modern_bulk drafts --output-dir "$OUTPUT" --review "$OUTPUT/state/uploads/production/bulk-v1/reviews/bulk-NNN.review.json" --owner 266679 --captured-by "<operator>" --token-keychain pices-zenodo-production
```

The run rebuilds the manifest for the pending approved members (fresh twin
check), captures the owner inventory and refreshes it every 45 minutes,
adopts verified modern-v1 drafts without a request, and stops on any
transport failure, 429, 5xx, HTML or edge 403, or three record holds in a row.

## Pairs (two byte-identical originals, one record)

```bash
python -B -m scripts.modern_bulk plan-pairs --output-dir "$OUTPUT" --batch-id pairs-001 --built-by "<builder>" --targets-file targets.json --reviewed-at 2026-10-20T12:00:00+00:00
```

`targets.json` lists `record_target_id`s from
`docs/readiness/2026-10-06/modern_exxon_pairs203.json`. The assessment time is
fixed for the batch because the pair wire depends on it. Review, drafts,
release and publish then run exactly as for singletons; the record holds both
files and is journaled under its first source id.

## Release and publication

```bash
python -B -m scripts.modern_bulk release --output-dir "$OUTPUT" --name release-NNN --review <review>... --authority "Brett Johnson" --instruction "<the goal as Brett gave it>" --instructed-at 2026-10-20 --prepared-by "<operator>"
python -B -m scripts.modern_bulk publish --output-dir "$OUTPUT" --release "$OUTPUT/state/uploads/production/bulk-v1/releases/release-NNN.json" --owner 266679
```

`publish` prompts for the token: Brett types it once per run. It first reads
the PICES community with that token and stops unless the identity, public
visibility and `can_include_directly` hold. Per record: GET draft, review PUT,
GET draft, submit-review POST (`require_review: false`), GET record, GET files.
A submission the community leaves pending stops the run.

## Holds

`status` lists holds. A record held before any provider request (an
inventory match, an exclusion) is released with `unhold` after review;
`--allow-inventory-record ID` records a reviewed false match for that source. A record
held after a request is observed with
`reconcile --source FGDC-N --owner 266679 --token-keychain pices-zenodo-production`
(GET only), which moves it to the phase the provider shows and allows a write
whose effect is absent to be sent once more by the next run. A lost create is
bound from the inventory when its draft appears; otherwise reconcile must see
absence twice, ten minutes apart, before the next run may re-send it.

## Second wire (v2) and in-place updates — ADR 0014

[ADR 0014](../../adr/0014-v2-wire-and-in-place-update.md) carries Brett's 2026-10-20 mapping
decisions: FGDC content in real Zenodo fields, a public XML file without a license, a
Dataset or Report type from the pinned classification, and no title suffix.

The review sheet for a batch, offline. It holds the approved members of the v1 review with
their v2 wires:

```bash
python -B -m scripts.modern_bulk plan-v2 --output-dir "$OUTPUT" --base-review "$OUTPUT/state/uploads/production/bulk-v1/reviews/bulk-NNN.review.json" --built-by "<builder>"
```

A reviewer agent other than the builder checks the new fields of every flagged and sampled
row against `FGDC/<id>.xml`. Those fields are the type, publication date, dates, map,
contributors, rights, notes, links and references. The agent records the decisions with
`review --batch-id bulk-NNN-v2`.

**Members not yet drafted.** Run `drafts`, `release` and `publish` with the `bulk-NNN-v2`
review exactly as above. The records are created and published in the v2 form.

**Records already published with v1.** Build an update release from the same review, then
run the update:

```bash
python -B -m scripts.modern_bulk release --output-dir "$OUTPUT" --action update --name update-NNN --review <v2 review>... [--only FGDC-N] --authority "Brett Johnson" --instruction "<Brett's question 8 answer>" --instructed-at 2026-10-20 --prepared-by "<operator>"
python -B -m scripts.modern_bulk update --output-dir "$OUTPUT" --release "$OUTPUT/state/uploads/production/bulk-v1/releases/update-NNN.json" --owner 266679 --token-keychain pices-zenodo-production
```

Each update sends these requests:

1. Edit POST. The edit draft must equal the published v1 record.
2. Draft PUT with the v2 wire, the record's own DOI pids and its custom fields.
3. Publish POST.
4. GET of the record.
5. GET of its files.

The DOI stays the same and the record gets a new revision. A record somebody changed by
hand holds before anything is saved. `reconcile` observes a held update by GET only.

The wrapper has matching commands: `pices-bulk.sh plan-v2 BATCH...`,
`release-update NAME [--only FGDC-N]... BATCH-v2...` and `update NAME`. Update one record
as a canary, and show it to Brett before any scaled run.
