# Frozen authorized synthetic inventory recovery

Runtime commit: **0acf265ba9f0dcc99d0d8e530ad1f3aa4e8909fc**. Handoff branch:
`handoff/pr8-synthetic-authorized-recovery-20261003`. Use the exact final handoff
commit supplied by the parent and the Python file hashes in the paired validation
receipt. This branch is separate from PR8 and the frozen earlier canary branches.

The parent explicitly authorized one recovery allowance of **225 additional
inventory GET attempts**, counting all **80 previously observed reads**, for a
**305 cumulative inventory ceiling**, at most **200 pages**, and a distinct
**30-minute recovery lifetime**. Parent dispatch is still required for each
provider stage. Executor `01a0fed7-bf71-7384-95fd-3434599df03f` is the sole provider
credential user/writer. The code owner made no provider requests or writes. No
token, credential provisioning, configuration or production change is needed.

## Exact retained evidence and private preparation

Keep the original stage, synthetic source/payload and durable ledgers:

`/workspace/pices-sandbox-run-9379fd8-20261002/synthetic`

Keep all original failed receipts and the following private files byte-identical:

- `state/sandbox/synthetic-inventory-controller.json`, if present: two-read HTTP400.
- `state/sandbox/synthetic-owned-inventory-controller.json`, if present: ten-read
  cap failure, five earlier reads included.
- `state/sandbox/synthetic-owned-pages-controller.json`: failed v2 state with 64
  attempts, 62 saved pages / 6,200 IDs, next page 63, no resumes and the known
  nonretryable `response_json`/ValueError semantic failure.
- Every file in `state/sandbox/synthetic-owned-pages/`: exactly pages001–062.

Before the first recovery dispatch, retain the **original v2 module failure JSON
output** at the new evidence path
`state/sandbox/synthetic-owned-pages-failure-receipt.json`. Copy the already
retained module JSON object locally; if captured inside a tool result, extract
that exact object without changing its fields. Do not rerun the old controller,
make a new diagnostic request, synthesize guard observations from pages, or
overwrite any original receipt. If the target already exists, preserve its bytes.
Missing/mismatched evidence stops locally before transport; it is not a reason to
recreate the private run or reset state.

If the original one-GET page 63 diagnostic JSON is locally retained, preserve a
copy at `state/sandbox/synthetic-owned-page-63-diagnostic-receipt.json` before
starting recovery. Its JSON must include the failed response SHA as a string
value. The complete diagnostic file bytes are then hash-bound. Retain its original
capture as well. Do not create a diagnostic by sending another request. Absence
of this optional local copy never subtracts its observed read: the diagnostic is
always included in the 80-read total. Adding/removing/changing either evidence
copy after recovery starts blocks reuse, so prepare available evidence first.

The runtime requires the failure receipt's 64 completed owned HTTP200 guard
observations with JSON/owner/link validation, no writes or community reads, and
the exact failure/count fields matching the private state. Every retained page's
raw-response SHA must match its corresponding receipt observation (constructor
index 0; page N index N). Saved file hashes, 100-item page counts, owner, unique
positive IDs and collision fields are rechecked locally. The unsaved failed
page 63 response hash is retained in the new binding. Older receipt hashes must
still match the v2 state. Private response bodies/owner/record IDs stay private.

The binding includes the exact reviewed compatibility commit
`58bbf0d501cda9244804734d52a1d425d47bd0c3`, its pinned validation receipt SHA
`65efffe3c461e620323b01f2f7ee34cadd31b61f13e92f72d2a63a3c04616f3c`, and hashes of the
failed state, original failure receipt, all 62 pages and any retained diagnostic.
No old failed grant is usable. The original v2 clock is validated and preserved,
even if expired; it is never renewed.

## First parent dispatch: recovery inventory only

Use the provider's approved interpreter/dependencies at this frozen checkout.
Keep its existing Sandbox credential in its designated environment. `--owner-file`
is the existing private JSON positive integer owner ID; never print or commit it.

```sh
python -m scripts.synthetic_canary_controller --inventory-only --recover-inventory --owner-file /path/to/private-owner.json
```

This creates only the distinct schema3 state
`state/sandbox/synthetic-owned-recovery-controller.json`, scope
`synthetic_owned_namespace_recovery_v3`, and new page folder
`state/sandbox/synthetic-owned-recovery-pages/`. The start/expiry are first set
when that recovery state is created after local evidence validation. Expiry is
exactly start + 30 minutes. The old state/pages are neither converted nor overwritten.

The scan starts with the guarded constructor GET and **page 1**, using only
`/api/deposit/depositions?page=N&size=100`. Old pages provide no completion credit
and are not assumed to be a server snapshot. No public/community query, new
filter/sort, redirect, automatic retry or account-quiescence claim is introduced.
Historical duplicate titles and empty drafts are allowed; exact frozen run title,
source identity anywhere in metadata, or selected XML name in any recognized
filename/name/key alias still block. Metadata must be an object and files an
array; supplied titles must be strings; owner/ID/page/file validation stays strict.

Every attempted constructor/page/replay GET consumes the same durable 225-read
allowance before transport, with file and directory fsync. Every send checks the
remaining budget and absolute new expiry. The guard has unchanged Bearer value,
exact HTTPS Sandbox path/query validation, timeout `(10,30)`, 12 MiB response cap,
raw/decoded credential echo rejection and redirects disabled. The CLI deadline
is 1,800 seconds. A full 200th page does not prove completion and stops.

The reported 16,538-item fixture completes with 166 pages+constructor = **167 new
GETs**, for **247 cumulative inventory GETs**. Live counts/order may change; this
is adequate finite headroom, not a claimed live inventory result. Completion
rechecks the old evidence binding and binds the owner/packet/scope, exact selected
filename, retained inventory and safe grant hashes. Generic upload paths and
production cannot consume this synthetic scope.

Return the sanitized module receipt and **pause**. It reports all 80 prior reads,
new attempts, cumulative total, ceiling 305, compatibility commit and original
failure-receipt SHA, with fixed diagnostics and guard observations. It omits
private owner/remote IDs, URLs, bodies, headers, credentials and exception text.
Exit 0 means completion; exit 1 means stop. No draft/write occurs in this command.

## Explicit recovery resume only

A transport-only ConnectionError/Timeout may permit explicit parent-dispatched
resume while the original recovery clock/counts still allow constructor, every
retained recovery page and another completion candidate:

```sh
python -m scripts.synthetic_canary_controller --inventory-only --recover-inventory --resume-inventory --owner-file /path/to/private-owner.json
```

Resume first rechecks all original failure/evidence hashes and retained recovery
page hashes/content. It replays from page 1, requiring identical content/order for
all saved recovery pages, then continues. Replay is charged to the same allowance;
earlier recovery failure diagnostics remain in its history. No clock renewal or
attempt reset occurs. Changed pages, schema/owner/collision failures, redirects,
orphan files, expiry and insufficient replay allowance block; do not delete/edit
state to retry. A completed recovery cannot refresh or downgrade to the old mode.

## Separate second parent dispatch: original synthetic write/readback/retry

Only after the inventory receipt confirms completion and parent review, dispatch
while the recovery grant is fresh:

```sh
python -m scripts.synthetic_canary_controller --owner-file /path/to/private-owner.json
```

The original synthetic namespace/run and all 17 packet/source/payload/metadata/
artifact bindings are unchanged. The recovery grant is matched to its schema3
completion state and current original-evidence binding. That binding is hashed
into the durable write controller, including local cached reruns.

Across restarts, the unchanged write ceilings are **one create POST, one metadata
PUT, one XML upload PUT and eight GET attempts**. The eight reads are the
separately authorized synthetic stage, beyond the inventory ceiling. Service
intent persists before create and returned ID before updates. Owner, absent
pre-run ID, unsubmitted draft state, exact metadata/files, reserved DOI, checked
bucket UUID/origin/path, XML download hash and unchanged retry remain required.
No automatic retry, publish, delete or production endpoint/action is allowed.
The write-stage deadline remains 300 seconds.

An uncertain/failed create/update/upload consumes its allowance and blocks
recreation. An existing write controller/nonempty upload ledger blocks another
inventory run. Completed write reruns revalidate local bindings and return
`cached=true,fresh_remote_check=false` with zero requests. They do not establish
fresh remote verification. Return the receipt and **pause immediately**. The
synthetic remains one slot of the original four-total-create canary budget;
actual-source stages require a later separate parent dispatch.

## Offline review and source-QA membership

**322 guarded offline tests pass**, independently reproduced. The 19 new recovery
tests reproduce the exact old 64-attempt/62-page failure and verify cold completion,
80+167=247 cumulative reads, the 225/305 bound, original evidence preservation,
separate expiry, replay/history, drift/tampering/orphans, own-run collisions,
redirects, decoded token echoes, generic/production isolation, CLI dispatch and
uncertain-create stops. Independent temporary-fixture probes also confirm that
old-scope substitution and evidence changes after completion block execution or
cached reruns with zero requests. F lint and diff checks pass. All 4,206 original
XML files and 17 packet entries are unchanged. See
[the validation receipt](synthetic_authorized_recovery_validation.json).

No live recovery, draft success, fresh remote verification or production readiness
is asserted by this offline evidence.

The separate PR8 source-QA head remains
`a70e56bd67bd85c0ee38c29aa387d03207461738`, unmerged. The exact
[133-promotion membership](source_qa_133_promotion_membership.json) distinguishes
the prior 70 DFO sources (reviewed 8bc36dc; 270 tests+16 independent focused) from the
new 63 institutional promotions (runtime 196cdb0; 279 independently reproduced
tests): 18 PICES, 18 NOAA hierarchy, 20 SOA and 7 First Institute. It includes every
source ID/hash, pinned original manifests/review receipt URLs+SHAs, and the nine
residuals from the 72-member institutional audit. The cohorts are disjoint. Full
corpus remains 2,121 supported/2,079 held/six malformed, with zero remote/publication
approvals and all 4,206 originals/4,200 XML copies/4,194 full raw metadata objects
unchanged. Source support does not authorize these records for provider upload.
