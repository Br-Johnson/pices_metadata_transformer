# Frozen sandbox execution handoff

**Current execution pause:** the supplied guard has been reviewed and replaced,
but the historical failure remains unclassified. Follow the exact one-GET
diagnostic in `docs/readiness/2026-10-02/reviewed_inventory_guard.md` only after
parent dispatch; then pause even on success. No write or full inventory is part
of that observation. The duplicate exception does not clear this gate.

The integration owner remains the sole code writer. The provider executor runs
this frozen plan and reports evidence; it must not change code, source metadata,
selection, inventory rules or failure handling. This branch adds the independently reviewed narrow sandbox duplicate exception
and public frozen planning artifacts to prior reviewed runtime commit
`9379fd8f13255b95ffab7a2c6735525e1d5cf1de`, tree
`3079d38a9be151b85e15350404948f2f0e9b908d`. Do not merge the handoff branch into PR8.

The parent has approved this bounded sandbox draft canary and separately reports
successful NetworkSecret substitution in the designated provider environment.
Do not copy credentials or placeholders between environments. The expected owner
ID is supplied privately in the provider task; it is intentionally absent here.
Initial page-one authentication is not a complete inventory or ownership audit.
No account inventory, owner ID, draft ID, token or private provider response may
be pushed to Git or included in this public packet.

## Exact scope and order

Maximum **four new sandbox drafts total for this run**, including the synthetic:

1. `SYNTHETIC-PICES-9379FD8-20261002` — one fictional XML file, 471 bytes,
   SHA-256 `ba23767a19b7d235ffcc8d8cf03380052ae03735e08f5c4ca9c57316bd14ae25`.
   Exact readback plus unchanged retry must succeed before any actual-source create.
2. `FGDC-100` — supported baseline.
3. `FGDC-1839` — supported citation interpretation.
4. `FGDC-3682` — supported registration interpretation.

No substitute candidates, fifth create, publication, action endpoint, deletion,
production requests or community-submission action. Authentic title, source, creators, dates and rights stay unchanged. The exact
`pices-sandbox-canary:pices-successor-9379fd8-sandbox-20261002` keyword is added to
the three actual-source payloads and included in the initial create POST so
lost-response drafts can be discovered. All resulting payload/metadata hashes
are rebound in this packet; no other metadata change is allowed. Existing metadata community suggestions are not approval to submit.
All protected production source identities and unrelated poster 10042430 are
excluded. No `.env` file is needed or permitted for this execution.

`selection.json` binds each source SHA-256/MD5/size, prepared payload file hash,
canonical submitted metadata hash and artifact contract. `INVENTORY.json` binds
all packet files. Expected submitted metadata is supplied in separate JSON files.
The source/metadata-only interpretation does not establish production readiness.

## Checkout and offline verification

Fetch the updated `handoff/pr8-reviewed-read-guard-20261002`; use the exact final commit and inventory
hash delivered by the integration owner. Check out that commit in the provider's
clean checkout. Use the exact newly reviewed runtime commit supplied in the handoff. The `FGDC`
tree must match `9379fd8:FGDC`; scripts/tests now include the bounded exception.
Do not execute the new plan using the older runtime.
Verify every inventory entry's byte count and SHA-256 before preparing a run.
Do not print or enumerate environment values. Use the existing approved Python
interpreter with repository requirements installed; all commands run at repo root.

Create one new private local run directory, never overwrite a previous run:

```python
from pathlib import Path
import shutil
packet = Path('docs/handoff/sandbox-canary-20261002')
run = Path('/workspace/pices-sandbox-run-9379fd8-20261002')
run.mkdir(mode=0o700, exist_ok=False)
shutil.copytree(packet / 'synthetic/data', run / 'synthetic/data')
shutil.copytree(packet / 'actual-data', run / 'actual/data')
```

A stopped run must resume this same directory and durable state. If it already
exists, inspect/reconcile it; do not choose another run label or erase state.
Before network activity, for each of the four staged JSON files use
`OutputPaths(stage, 'sandbox')`, `prepare_metadata`, `metadata_hash` and
`prepare_artifact` to match `selection.json` and the full expected metadata JSON.
Match copied XML to the canonical originals for the three authentic sources;
`assess_source` must still pass those three. Synthetic is a technically validated
fixture, not an authentic source QA pass. Stop on any mismatch.

## Authenticated read and genuine inventory gate

Only in the designated credential-ready provider environment, use the environment
placeholder through `create_zenodo_client(sandbox=True)`; its constructor performs
a read. Verify the expected account privately against the parent-provided identity
and owned-deposition owner fields. Missing/ambiguous owner fields require a stop
and clarification, not assumed ownership. Fetch the complete owned deposition
inventory and complete public PICES community inventory with the reviewed paginated
methods `get_all_my_depositions()` and
`get_records_by_query(q='communities:pices', size=200)`. Reject repeated/malformed
pages, incomplete totals, unexpected host links, or any API failure. Preserve raw
responses/hashes and timestamps privately; report only sanitized counts/status.
Record the pre-run IDs privately for the four-new-draft bound and duplicate check.

Run the existing duplicate checker separately for each staged directory, immediately
before that stage, with replacements disabled:

```python
from scripts.pre_upload_duplicate_check import PreUploadDuplicateChecker
canary_plan = str(packet / 'legacy-duplicate-exception.json') if stage.name == 'actual' else None
checker = PreUploadDuplicateChecker(sandbox=True, output_dir=str(stage), allow_replacements=False,
                                    canary_plan=canary_plan)
try:
    summary = checker.check_all_files()
    # Require zero check_errors, zero duplicate_files, and the exact stage filenames.
    # Require the independently checked complete owner/community inventory above.
    assert not summary['check_errors'] and not summary['duplicate_files']
    assert set(summary['safe_to_upload_files']) == set(expected_stage_filenames)
    checker.generate_upload_list()
finally:
    checker.client.close()
```

This creates the real environment-scoped fingerprint-bound inventory from actual
responses. Do not handwrite/edit safe-to-upload files, renew a stale timestamp,
remove duplicates or invoke replacements. The explicit actual-source plan permits only exact listed source/payload hashes
and historical title matches created strictly before 2026-10-02T00:00:00Z.
The code pins the full exception manifest SHA-256. Every match is checked, not
just the first. Missing/invalid creation time, identifier collision, recent match,
in-batch match, another canary namespace or own-run remote draft without its exact
original ledger stays blocked. No ordinary or production path receives this
exception. The checker records tolerated historical IDs privately. If any candidate
is still blocked, stop the entire actual stage and report it; never skip or replace.
Authentic-source stage starts only after synthetic success.

## Serial draft operations and exact readback

Use one writer and the existing service, never generic pipeline/publish commands:

```python
from scripts.path_config import OutputPaths
from scripts.upload_service import DraftUploadService
# stage and source_id are the exact staged directory and next fixed ID above.
paths = OutputPaths(str(stage), 'sandbox')
canary_plan = str(packet / 'legacy-duplicate-exception.json') if stage.name == 'actual' else None
service = DraftUploadService(paths, 'sandbox', canary_plan=canary_plan)
json_file = str(Path(paths.zenodo_json_dir) / (source_id + '.json'))
entry = service.upload(json_file, client)  # client is the verified sandbox client
assert entry.get('success') and entry.get('publish_status') == 'draft'
```

For each source, record positive integer deposition ID, owner, state and reserved
DOI privately. Confirm owner equals the expected authenticated account; ID was not
in pre-run inventory and is not another selected source's ID. Require an unpublished,
unsubmitted draft (`submitted` exactly false, state not `done`). The only permitted
writes are one create POST per new source (actual-source POST already carries its exact
run-marked metadata), metadata PUT to that returned ID, and
one upload PUT for its exact missing XML. Reviewed code persists uncertain-create
intent before POST and the returned ID before subsequent operations.

After service success, GET the same deposition and require:

- Existing `compare_metadata` finds no divergence from full expected metadata.
- `validate_files` confirms exactly one selected original XML filename, exact
  byte count and MD5/SHA-256 from the contract; no unexpected file.
- Download that file read-only using its returned same-host HTTPS:443 URL with
  redirects disabled and the existing Bearer session; validate the host strictly
  before sending. Stop if there is no supported same-host download link. Stream
  bytes to private storage and compare SHA-256 and byte count with the plan.
- Owner, returned ID, unpublished state and reserved DOI remain consistent.

Then invoke `service.upload(json_file, client)` again unchanged with the same
ledger. Require zero new POSTs, zero new file uploads, identical ID/DOI and exact
metadata/file readback. Record method/path counts only, never headers or tokens.
After synthetic passes all checks, refresh/check authentic-stage inventory and
execute the three candidates serially in listed order. Stop on the first failure.

## Retry limits and stop conditions

The total create bound is four across restarts, not four per process. Retain the
private pre-run ID set, exact selection and durable stage ledgers. Track each
create intent even if its response is lost. Never repeat a create with uncertain
outcome; use GET-only reconciliation through the code owner. No speculative
cleanup or DELETE. No changed payload/ledger to manufacture a successful retry.

Stop for changed source/payload/contract, missing secure placeholder, auth/owner
mismatch, incomplete/stale inventory, non-exempt candidate duplicate, count/identity mismatch,
non-sandbox or redirected URL, unexpected files, metadata mismatch, publication,
ambiguous create/update/upload, failed checksum or any retry that creates/uploads
again. Generic exception output must remain sanitized: no headers, token values,
request objects, raw tracebacks or private response dumps in shared reports.
Do not alter runtime code to resolve a provider schema incompatibility; report it
and return control to the sole code owner.

Return a private sanitized receipt with code/plan hashes, auth/owner check status,
inventory completeness/counts/timestamps, per-source actual ID/reserved DOI and
source/metadata/file hashes, first-run versus retry operation counts and final
unpublished state. No publication/production readiness is inferred. Send private
record/account data only to the parent, never the Git branch.

## Updated actual-source exception activation

The original synthetic fixture is unchanged. If it has already passed in the
designated provider environment, preserve its original ledger and use its verified
private receipt; **do not create a second synthetic**. Only the actual-source
packet/expected hashes are superseded with the pinned namespace keyword. Before
any actual-source write, stage these new exact files into the as-yet-unused actual
stage directory. If an actual-stage ledger already contains any create intent or
ID under older payload hashes, stop and reconcile with the code owner; do not
overwrite, clear or migrate it automatically. Existing checker output is not an
upload ledger; refresh it from real complete inventories with the explicit plan.

The publisher rejects canary-marked ledgers even if supplied approval material.
Production constructors reject the exception before a client is created. New
creates remain at most three listed actual sources; the prior one-synthetic
budget remains counted toward the four-total cap across both runtime versions.

The checker initializes a plan-bound ledger when granting the actual-stage
inventory. The service consumes each source create permission before saving
intent and issuing POST. Missing initialized ledger, lost source entries with
consumed grants and uncertain intent all fail closed. The unchanged retry also
requires submitted=false and an unpublished state; a published remote canary
cannot be reported as a successful draft. Do not reconstruct these state files
manually. A stop after grant consumption but before POST requires owner-led
read-only reconciliation and a genuinely refreshed check, not another create.
