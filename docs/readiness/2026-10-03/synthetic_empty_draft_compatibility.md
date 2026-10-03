# Frozen empty-draft compatibility checkpoint; recovery blocked

Runtime: **ff84b66241ff5642c58ae6686072492bcd2db0cd**. Branch:
`handoff/pr8-synthetic-empty-draft-compatibility-20261003`, based on frozen handoff
`a8cfeef632c6764cfc7e4211fddd2e0e61385dd4`. The older published branch remains
unchanged. This is a reviewed compatibility patch, not a new inventory allowance
or executable recovery grant. The parent must dispatch each provider stage;
executor `01a0fed7-bf71-7384-95fd-3434599df03f` remains the sole credential user and
provider writer. The code owner made zero provider requests or writes.

## Reconciled provider evidence

The parent reports that the v2 controller consumed 64 new GET attempts, retaining
62 verified pages / 6,200 entries, then stopped on page63 with a semantic
`response_json` failure. The guard had accepted HTTP200, JSON, ownership and links.
No draft or write occurred. The separately dispatched one-GET page63 diagnostic
returned the same response SHA as the failed response and confirmed 100 records:
all metadata objects and files arrays, 91 nonempty string titles, nine absent title
fields, and 100 empty files arrays. No private response body or account ID was
transferred into this checkout.

The cumulative count is **15 earlier reads + 64 v2 attempts + one diagnostic =
80 observed inventory GETs**. The original v2 state, all 62 saved pages, response
hashes, failed receipts and any prior ledger remain private and untouched. They
must not be deleted, edited or reclassified as a completed inventory.

## Minimal compatibility rule

Historical drafts can have incomplete metadata. Missing, empty or whitespace-only
titles are accepted when metadata is an object and files is an array. A supplied
non-string title remains a schema failure. Every supplied title is compared with
the frozen synthetic title, all metadata keys/values are searched for the exact
source identity, and every recognized filename/name/key alias is checked for the
selected XML name. Owner, positive integer ID, uniqueness, page size, actual file
shape, outgoing endpoint/query, redirect rejection and credential redaction stay
unchanged. Unrelated historical title duplicates remain allowed.

Production/actual-source duplicate screening and generic upload grant rules are
unchanged. The original run ID, source/payload/packet bindings, durable create
intent and one synthetic create/metadata PUT/upload PUT allowance remain intact.
No publish, delete or production action is added.

## Explicit recovery constraint

This patch intentionally cannot reset or resume the reported semantic failure.
Neither the ordinary inventory entrypoint nor `--resume-inventory` can use that
failed state. The write entrypoint cannot consume its incomplete grant. Do not
run any of those commands against the private failed run at this checkpoint.

The current 240 cumulative-read ceiling leaves **160** attempts after the 80
observed reads. A fresh scan of the reported 16,538 entries requires 166 pages plus
constructor, approximately **167** GETs, for **247 cumulative reads minimum**.
The live count may change. Reusing unverified offset pages would claim a snapshot
the API has not established. The old absolute 30-minute expiry cannot be silently
renewed. An exact server-side run-identity filter is still unverified.

The parent decision pending is whether to authorize one separately reviewed
recovery scan with up to **225 additional GETs**, at most **200 pages**, and an
explicit new **30-minute lifetime**. This would retain all 80 prior reads and
report a **305 cumulative ceiling**. That proposal is not authorization and is
not implemented or executable in this runtime. Keeping the 240 ceiling means the
live scan remains blocked; no guaranteed-failure scan is dispatched.

If authorized, a follow-on recovery implementation must use a distinct state and
scope, validate and hash-bind the exact failed v2 checkpoint, all saved pages and
diagnostic evidence, include the 80 prior reads in its durable accounting, and
start a complete cold scan from page1. Old pages remain evidence, not completion
credit. Eligible transport resumes must replay all retained recovery pages under
the same new budget/expiry. Existing write/uncertain-create ledgers must continue
to block new inventory/create attempts. Only completion of that reviewed recovery
may create a new controller-bound synthetic grant. Parent dispatch and provider
execution remain separate from coding.

## Offline validation

**303 guarded offline tests pass** with networking blocked. The prior 302-test
suite was independently reproduced; the added checkpoint regression was also
independently reviewed and run. The exact page63 fixture completes a full
16,538-entry scan offline with 167 GETs. Missing-title records still detect source
markers in metadata keys/values and every file alias. Non-string titles, invalid
owner/IDs/schema and repeated IDs remain rejected.

A regression recreates the original title requirement's page63 semantic failure:
64 attempts, 62 saved pages, no complete grant. After applying the compatibility
checker, ordinary inventory, explicit resume and write execution all stop with
zero additional requests and byte-identical failed state/pages. Existing budget,
expiry, partial-inventory, uncertain-create, redirects, token-echo, readback and
unchanged-retry regressions remain passing. F lint and diff checks pass. All 4,206
original XML files and 17 packet entries are unchanged. See the paired
[validation receipt](synthetic_empty_draft_compatibility_validation.json).

The source-QA integration is separate: PR8 at
`a70e56bd67bd85c0ee38c29aa387d03207461738` has 279 independently reproduced tests,
2,121 supported / 2,079 held / six malformed and 133 source-support promotions
against c486d1f. It remains unmerged and does not grant provider or release access.
