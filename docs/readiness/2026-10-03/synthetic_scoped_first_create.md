# Sealed synthetic first-create checkpoint

This is the localized controller for the parent's explicitly adopted synthetic
first-create scope. **Not runnable yet:** the two actual diagnostic receipt
hashes in `scripts/synthetic_first_create.py` remain `PENDING`. This is a local
stop before any provider request. Do not dispatch the command until the exact
retained receipt files are pinned and the final reviewed runtime is supplied.

The code environment was verified available by shell commands at
2026-10-03 03:31 UTC. The separate provider executor's connection was not
verified here. The code owner made no provider request, write, or credential
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

Before final dispatch, retain exact existing JSON receipt bytes at these private
evidence paths below `state/sandbox/` (copy locally, never rerun a diagnostic):

- `synthetic-owned-recovery-failure-receipt.json`: original pinned v3 failure.
- `synthetic-owned-page-101-diagnostic-receipt.json`: the separately authorized
  single page101 HTTP400 diagnostic; its exact SHA is still required.
- `synthetic-scoped-diagnostic-receipt.json`: the actual capture of the two
  successful scoped GETs; its exact SHA is still required. If captured separately,
  supply both actual filenames/hashes for the small final pin adjustment rather
  than fabricate a combined response or guard observation.

Only unused first-create evidence is accepted. A prior write-controller state
cannot be reconstructed around a nonempty/lost ledger. Every uncertain create
consumes its durable one-POST allowance and stops permanently for reconciliation;
neither negative search nor a new clock allows recreation.

## Runtime after final receipt binding and review

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
