# Frozen sealed synthetic first-create handoff

This is the reviewed localized controller for the parent's explicitly adopted
synthetic first-create scope. Use the exact final commit supplied by the parent
on `handoff/pr8-synthetic-scoped-first-create-20261003` and verify the Python
hashes in the paired validation receipt before dispatch. Both actual diagnostic
receipts are now bound to the exact original paths and hashes supplied by the
parent; no diagnostic is rerun or reconstructed.

The code environment was verified available by shell commands. The parent has
confirmed the separate provider executor is available. The code owner made no
provider request, write, or credential
inspection. Executor `01a0fed7-bf71-7384-95fd-3434599df03f` remains sole provider
credential user/writer; parent dispatch remains required.

## Evidence and scope

The parent reported both scoped diagnostics passed at 03:16:38 UTC: the owned
positive control returned HTTP200/six unique owned candidates including retained
record373311 with its exact title; the fixed synthetic title query returned
HTTP200/zero candidates. These two GETs bring the observed total to **185**.
There were no grants/writes. Indexed title results are additional candidate
evidence, not complete own-run absence or reconciliation of an uncertain POST.

Keep the original stage and all files/receipts byte-identical:
`/workspace/pices-sandbox-run-9379fd8-20261002/synthetic`.

The gate locally validates the old v2 recovery binding and all retained v2/v3
pages. Frozen v3 failed-state SHA256 is
`158b34452cb43d102457bd6f700e3bd8bc0aabb7dd0412ba7d65a6e71116f23f`;
its original failure receipt SHA256 is
`b0d5826cc12866dde84ae92428ac9a82341dc0925b6969bee6892f7743a50d1b`.
The expired 03:18:03 clock is preserved. No old state is reset or resumed.

The original v3 failure receipt must be retained below `state/sandbox/` at
`synthetic-owned-recovery-failure-receipt.json`, with its pinned SHA above. If a
local copy is needed, copy the already retained exact bytes; never overwrite an
existing file or rerun the failed controller.

The two actual diagnostic receipts remain at their existing original paths:

| Original private file | SHA256 |
| --- | --- |
| `/workspace/pices-sandbox-run-9379fd8-20261002/diagnostic-page101-limit-receipt.json` | `8134aa13052e97ebd11a3a50380fe597b00cf4d028d364f0232758ed0a129227` |
| `/workspace/pices-sandbox-run-9379fd8-20261002/diagnostic-scoped-title-search-receipt.json` | `cbdb5267fa65be3ca0073d39045bb1d26611b6f7b40bf580702fd1eff31ba230` |

The final binding review checks exact filenames/hash constants without opening
private provider content in the code environment. Provider execution rechecks
the exact retained bytes locally and hashes them into the durable grant.

Only unused first-create evidence is accepted. A prior write-controller state
cannot be reconstructed around a nonempty/lost ledger. Every uncertain create
consumes its durable one-POST allowance and stops permanently for reconciliation;
neither negative search nor a new clock allows recreation.

## Parent-dispatched provider runtime

```sh
python -m scripts.synthetic_canary_controller --scoped-first-create --owner-file /path/to/private-owner.json
```

The new **30-minute clock starts only in this provider execution**, after local
evidence checks; restart never renews it. Separate files
`synthetic-first-create-grant.json` and `synthetic-first-create-known-ids.json`
preserve the old inventory caches too. Both explicitly set
`inventory_complete=false`: the 10,000 retained IDs form a **partial reject set**,
validated on every controller load.

At most eight new GETs (including the existing client constructor), one empty
POST, one exact metadata PUT and one original-XML PUT are allowed. A completed
transaction reports **193 cumulative GETs**, below the authorized305 ceiling;
it does not spend the remaining120 on another inventory. No redirects, automatic
request retries, public/community query, publish/delete or production path.

Creation requires HTTP201/new resource, an ID outside the partial reject set,
correct owner, empty/unsubmitted draft and safe links/DOI. The timezone-aware
creation timestamp is bounded by the durable current POST interval with at most
60seconds of clock skew, then must remain unchanged on every readback. The
returned ID is durable before any PUT. Exact metadata/XML/DOI readback and an
unchanged retry remain mandatory; completed process rerun makes zero requests.

Production and actual-source complete-inventory requirements remain in place.
The shared service accepts this scope only through the exact active synthetic
controller capability bound to the original packet, source, metadata and grant.

Validation: owner and independent reviewer each passed all334 guarded offline
tests at the reviewed checkpoint. After binding the exact actual receipt pins
and original paths, both passed all12 focused tests and the narrow consistency
review. The paired `synthetic_scoped_first_create_validation.json` contains the
final Python hashes and validation evidence. No provider request was made here.
Return the sanitized runtime receipt to the parent and pause after the canary.
