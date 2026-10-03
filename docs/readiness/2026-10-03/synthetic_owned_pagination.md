# Frozen synthetic canary: bounded owned pagination

Historical handoff: the live v2 scan later stopped at page63 on nine legitimate
missing-title drafts. See [the compatibility checkpoint and pending recovery
constraint](synthetic_empty_draft_compatibility.md) before any dispatch. Its failed
state is not resumable and the remaining old budget cannot complete a fresh scan.

This was the runnable handoff at its frozen checkpoint. It supersedes the ten-GET owned gate in
`synthetic_canary_controller.md`. Parent dispatch is required for each provider
stage. Only provider executor `01a0fed7-bf71-7384-95fd-3434599df03f` uses its existing
Sandbox credential and performs provider writes. The code owner made zero provider
requests or writes. Do not run another connectivity probe.

Runtime commit: **b565d24187350da25bf32f10e5e6941018cbc3ed**. Handoff branch:
`handoff/pr8-synthetic-owned-pagination-20261003`. Use the exact final handoff
commit supplied by the parent; its Python runtime must match this runtime commit
and the hashes in `synthetic_owned_pagination_validation.json`. Do not merge it
into PR8. Dependencies are the repository requirements; offline validation used
Python 3.12 and the package versions in the receipt.

## Reconciled checkpoint and scope

Baseline `6b8f6a8829e3c2bd85fc8adb9f2a5c34d14e5fef` stopped after constructor plus
nine 100-item owned pages: ten HTTP-200 reads, 900 listed items, no draft/write.
The parent reports approximately 16,538 owned items. Five earlier reads remain
counted, including the failed slashless public query (HTTP 400, cause unknown).
The complete untested owner patch was transferred and verified with SHA-256
`920211c5773484f5c8da79eb970d8806f7c2c7db8c02cfa0e4a1ab320c1e692b`; it is preserved
locally at `/workspace/pices-transfer/original-owner.patch` as transfer evidence,
not as approved runnable code. No private provider data was transferred.

The revised gate uses only the already observed owned-deposition endpoint,
`/api/deposit/depositions`, with `page=N,size=100`. No query filter, new sort order,
public-community query, redirect or automatic retry is introduced. An exact
server-side run-identity filter has not been verified, so none is assumed.
Historical Sandbox title duplicates are allowed. Exact synthetic title, frozen
source identity embedded in metadata, or any recognized file-name alias matching
the selected XML requires reconciliation. Every page is checked for owner,
positive unique IDs, collision fields and bounded size. Missing/malformed identity
fields and repeated IDs stop safely. These are sequential pagination checks;
there is no claim of a server snapshot or account quiescence.

Production and actual-source duplicate screening retain their original complete
public-plus-owned inventory requirements. Generic upload paths cannot consume
this reduced synthetic-only grant. Production public API compatibility and the
unknown community-query HTTP 400 remain separate tasks.

## Preserve the original private run

Use the existing stage, with its original source, payload and durable ledgers:

`/workspace/pices-sandbox-run-9379fd8-20261002/synthetic`

Do not recreate/restage the directory, substitute a source, choose a new run ID,
remove a state file, edit a timestamp, renew a budget or overwrite prior receipts.
Keep `ZENODO_SANDBOX_TOKEN` in the designated provider environment; never print,
copy or commit it. `--owner-file` points to private JSON containing only the
previously verified positive integer account ID. No `.env` is required.

The module verifies unchanged packet INVENTORY.json SHA-256
`428559c7a8e81e84c22627b0add1230797b92013f87152e2ee3024b56af30fd1`, all 17 packet
entries, and staged source/payload/expected metadata/artifact bindings before
transport. The packet, including its historical EXECUTOR.md, remains unchanged.
Use the commands below for the current synthetic stage; older packet commands do
not supersede this handoff.

The stopped `synthetic-inventory-controller.json` (two reads, HTTP 400) and
`synthetic-owned-inventory-controller.json` (ten-read cap failure) remain untouched
and are hash-bound in the new state. Only those exact read-only failures can be
superseded: same owner/packet, failed and incomplete, and the known cap diagnostic
for the owned attempt. Any other prior failure or an existing write controller /
nonempty upload ledger stops before requests. No uncertain-create state is reset.

New state uses scope `synthetic_owned_namespace_pages_v2`, file
`state/sandbox/synthetic-owned-pages-controller.json`, and private page files in
`state/sandbox/synthetic-owned-pages/`. This is an explicit new schema with
immutable references to v1 evidence; old state is never converted or reused as a
grant. Do not downgrade and execute an older runtime on this run.

## First parent dispatch: inventory only

Run at repository root using the credential-ready provider's approved interpreter:

```sh
python -m scripts.synthetic_canary_controller --inventory-only --owner-file /path/to/private-owner.json
```

Bounds are **225 additional inventory GET attempts**, including every constructor
and resume replay, plus the **15 previously observed reads**, for **240 cumulative
inventory reads maximum**. Each attempt is durably counted/fsynced before
transport. A successful scan may contain up to 200 pages. A full 200th page does
not prove completion and stops. The 16,538-item offline fixture completes with
166 pages plus constructor = **167 new GETs**, **182 cumulative inventory GETs**.
This leaves practical headroom and does not assume the live count is unchanged.

The state has an absolute 30-minute expiry from first start. Resume does not
renew it. The CLI inventory deadline is 1,800 seconds; every request also checks
the original expiry and remaining allowance. Requests have timeout `(10,30)`,
12 MiB response limits, unchanged Bearer authentication, exact HTTPS Sandbox
port/path/query checks and redirects disabled. Raw and decoded JSON credential
echoes are rejected before page persistence.

Pages are privately saved with saved-page and raw-response hashes.
Uncommitted/orphan page files, missing or changed retained pages, malformed IDs,
invalid owner, collision, non-200 status, redirect, expiry, page/budget exhaustion,
cleanup failure or schema failure never yield an executable grant. Private completion state binds owner, packet, scope, exact authorized filename
and hashes of the retained inventory and grant. The sanitized output reports
completion/count fields and the packet hash without those private bindings. Success authorizes only the later
synthetic controller; it is not a production duplicate proof.

Return the module's sanitized receipt, then **pause**. Shared receipts contain
fixed status/count/hash fields and safe diagnostics, not account IDs, titles,
remote IDs/DOIs, URLs, headers, token, response bodies or arbitrary exception text.
Keep page content, owner/IDs and full prior state private; never push them to Git.

## Explicit resume after eligible read-only interruption

No automatic retries occur. The module may return `resume_allowed=true` after a
transport-only ConnectionError/Timeout while the original time/read budget permits
at least constructor, all retained pages and another completion candidate. A
process interruption can also leave a valid incomplete checkpoint. The parent
must inspect the sanitized result and dispatch explicitly:

```sh
python -m scripts.synthetic_canary_controller --inventory-only --resume-inventory --owner-file /path/to/private-owner.json
```

Resume validates every local checkpoint, all previous-failure hashes and the
original lifetime/allowance before sending anything. It **replays from page one**,
checking all retained page content and order again, then continues beyond them.
There is no cursor or partial-snapshot trust. Earlier failure diagnostics are
retained in the failure history; explicit resume records its starting counters.
Changed retained pages, collisions and other semantic failures permanently block
this state. An orphan requires owner reconciliation; never delete it to retry.

Replay costs are charged to the same 225-read allowance. A late interruption can
leave too little budget to replay; it then returns `resume_allowed=false`. Other
stops, expiry and exhausted budgets require code-owner/parent reconciliation,
not another run namespace or an edited receipt. A completed inventory command
cannot be reissued as a refresh. If its grant expires before the write dispatch,
stop for a newly reviewed recovery plan.

## Second parent dispatch: synthetic draft/readback/unchanged retry

Only after successful inventory and final review, dispatch separately:

```sh
python -m scripts.synthetic_canary_controller --owner-file /path/to/private-owner.json
```

Only `SYNTHETIC-PICES-9379FD8-20261002` is executable. Its original durable run ID
and service intent/create allowance remain unchanged. Across process restarts,
the write controller permits **one create POST, one metadata PUT, one XML upload
PUT and eight GET attempts**. These eight are the separately authorized synthetic
stage's reads, not inventory reads. The XML is exactly 471 bytes with SHA-256
`ba23767a19b7d235ffcc8d8cf03380052ae03735e08f5c4ca9c57316bd14ae25`.

The existing service saves intent before create and ID before following updates.
The controller also durably consumes each allowance before transport and requires
the returned ID be absent from the verified pre-run IDs. Owner, unsubmitted state,
submitted=false, exact metadata/files, reserved DOI, same-origin bucket UUID,
selected file path and XML download checksum remain independently verified.
Decoded credential echo is rejected before create-response ID/metadata persistence.
No redirect, automatic retry, publish, delete, production endpoint or action route
is permitted. The synthetic command's deadline remains 300 seconds.

After full readback and download, the unchanged service retry must preserve the
same ID/DOI and issue zero new POST/PUTs. Final readback must pass. An uncertain or
failed create/update/upload consumes its allowance and blocks rerun; do not
create again. Completed module reruns validate local bindings and return
`cached=true,fresh_remote_check=false` with zero requests. They do not establish
fresh remote verification. Exit zero means completed; exit one means stop.

Return the sanitized receipt and **pause immediately**. Actual sources FGDC-100,
FGDC-1839 and FGDC-3682 require a later separate dispatch and their original narrow
historical duplicate exception. The synthetic remains one slot of the original
four-total canary create budget. No production credential/write, source-QA
promotion, publication, deletion, merge or paid-capacity action is authorized by
this handoff.

## Offline evidence and review

**299 guarded offline tests pass**, independently reproduced. Fixtures cover the
reported inventory size; the 200-page and 240 cumulative-read bounds; endpoint and
page/size enforcement; partial pages and late own-run collisions; immutable prior
receipts; resume replay/order/expiry/orphans/insufficient budget; generic-scope and
production protections; durable intent and uncertain create; redirect handling;
exact readback/unchanged retry; and JSON-escaped token echoes. Review findings for
insufficient replay allowance, missing page parameters and escaped credential
echo were reproduced and fixed. All 4,206 original XML files match baseline bytes
and every packet entry remains unchanged. See the paired validation JSON.

No live inventory success, draft success or production readiness is asserted.
Metadata-restoration baselines remain on separate reviewed source-QA branches;
this runtime branch intentionally preserves its prior transformation code.
