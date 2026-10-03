# Modern canary transport diagnostics and read-only reconciliation handoff

The actual modern trial cause remains **unresolved**. Parent reports a durable
create intent at`2026-10-03T20:33:02.504304Z`, no HTTP status/body/ID/exception trace,
and terminal audit completion at`2026-10-03T20:34:22.359350Z`. The terminal time is
an observation, not a response or known failure time. Frozen runtime was
`dc351b071df53c6d44f01491694916c1d44bd9f2`, namespace
`pices-modern-synthetic-20261003-code-01`, packet SHA256
`95d125ba6e47cb87cd89fcc981c8a179ee37127e0fe9ccab5711f9984b79787e`.
One modern POST intent is spent, with0 PUT/0 GET; historical GET ledger is193.
No reviewer denial was reported. These are sanitized parent-reported facts;
root has not inspected credentials, provider stages or terminal audits.

Offline reproduction establishes ambiguity: invalid local header preparation,
deadline setup/alarm, mocked adapter ConnectionError and response-projection failure
after mockedHTTP500 previously collapsed to the same held state. It does not
establish which occurred in the actual trial. No fixed-packet preparation defect,
transmission or provider processing is proved. See [static review](modern_transport_static_review.json).

## Frozen future diagnostic correction

Runtime commit`a43f4a12056371b5b11af6b791d1ae8ad3c3cb2c` retains fixed safe phase
and exception codes in the private state/journal and the held CLI projection.
Request preparation is explicit before Session.send; an instrumented HTTPAdapter
records local entry. `send_call_started` records the checkpoint before that call;
`adapter_entered` records entry to the local adapter. **Neither proves that bytes
reached Zenodo.** Header-return evidence and validated status are durable before
body/projection processing. A dedicated wall-deadline code and aware failure-capture
time survive generic wrapping. Cleanup retains the first failure plus a fixed
secondary category. A failure outside a pending attempt is recorded separately as
`controller_failure`; it cannot relabel the preceding acknowledged successful
attempt. Arbitrary exception text/class names/arguments/stack traces,
headers, raw URLs and bodies are never copied into these new diagnostics.

The historical receipt field`provider_requests` remains the count of durable action
intents, explicitly labelled`durable_action_intents_not_confirmed_transmissions`.
No limit/route/redirect/retry/publication/deletion permission changes. HTTPS/TLS,
20second wall deadline,64KiB body ceiling,30minute grant,4 POST/2 PUT/8 GET bounds
and completed-only unchanged read retry remain. The explicit send uses no proxies
and zero adapter retries, preserving the existing environment policy.

All349 guarded offline tests pass. Independent review ran25 initial focused
contracts and8 updated diagnostic contracts, closing deadline/time findings.
Automatic review then identified incorrect attribution of next-action pre-intent
expiry to an acknowledged prior action. The new regression fails against the
previous runtime and passes the correction; the final independent review runs all9
diagnostic contracts and clears this delta. See the
[pre-intent review](modern_preintent_independent_review.json).
Changed runtime/test files pass Ruff. See [validation](modern_transport_validation.json)
and [independent review](modern_transport_independent_review.json).

This runtime binding differs from the consumed grant. **Never rewrite/migrate/reset
the old state or approval, run execute/retry against it, create another draft,
adopt a discovered ID or replenish any allowance.** The correction improves
future evidence only; it cannot recover missing evidence retrospectively or supply
a new approval. Root issued zero provider requests.

Offline reproduction from this frozen checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m unittest \
  tests.test_modern_transport_diagnostics tests.test_modern_synthetic_canary
ruff check scripts/modern_synthetic_canary.py tests/test_modern_transport_diagnostics.py
```

Every new diagnostic contract uses dummy temporary stages/tokens and exact mocked
transport boundaries. The full validation also blocks unmocked Requests sends and
socket connections. No provider stage or real credential is needed.

## Parent-dispatched read-only reconciliation plan

This plan issues no grant. The parent must dispatch the sole provider executor,
`01a0fed7-bf71-7384-95fd-3434599df03f`, under a separate bounded **GET-only** grant
if read-only reconciliation is approved. Preserve the original journal/receipts,
all spent allowances and historical193 reads. Keep a separate private0700/0600
reconciliation ledger; each additional read increments cumulative accounting
before dispatch. No POST/PUT/DELETE, redirects, automatic retry or link following.

1. First retain any already-saved sanitized evidence that identifies interpreter
   main-thread status, whitelisted exception category, last local phase, response
   status or proxy dependency. Do not print exceptions, credentials, environment
   values or raw private stages. Missing evidence stays unknown; no diagnostic
   replay is allowed.
2. If no trustworthy candidate ID was already retained, a source-supported
   candidate route is`GET https://sandbox.zenodo.org/api/user/records` with the
   modern Accept header and explicit`sort=newest,size=100,page=1`. Framework source
   supports this route/order; deployed support remains unverified. Do not substitute
   public/community search, guessed title/namespace/created filters, cursors or an
   old-runtime mutable-state restart. A rejected route/schema/order stops held.
3. Validate each inventory hit's schema, canonical unique ID and aware created time,
   plus descending created ordering across the page and page boundary. Valid
   unrelated historical records remain non-candidates. For a possible canary,
   separately match full current draft identity, exact namespace/title/initial
   metadata, known owner, unpublished/unsubmitted first draft and empty files.
   Incomplete/malformed inventory remains held; do not treat it as a non-match.
   Treat intent-minus5seconds through terminal-observation-plus5seconds as search
   context only, with any clock tolerance explicit. A newest prefix may stop once
   it crosses that lower boundary; index lag/mutable pages make it candidate
   evidence only. It cannot establish global absence or authorize adoption.
4. The separate reconciliation grant permits at most240 **additional** GET intents
   including details: historical193 plus at most240 means a cumulative ceiling433.
   No read counter is reset. Bounds are200 list pages,size100,30minutes,
   <=20seconds per response. Inventory pages need a separate bounded32MiB response
   ceiling; the canary's64KiB single-record cap is not an adequate100-record page
   bound. Exhausting either byte/time/read limit stops incomplete without automatic
   page-size changes or repeated reads. Persist fixed query/page/body-hash/item-ID
   checkpoints and elapsed/count accounting before advancing. Resume only with a
   separately approved remaining read budget and demonstrated compatible ordering;
   ordinary offset pages are not a snapshot/cursor and cannot prove completeness.
   Do not blindly resume a changed page or clear a failed ledger.
5. The pinned inherited search default is**10000 results**; parent reports the old
   account scan failed at page101. Thus the numerical200-page ceiling cannot
   promise16538-entry completeness. Any HTTP400/redirect/partial body/schema or
   order failure, duplicate/missing page, full final page or exhausted budget leaves
   the result incomplete. Do not claim zero matches means no created draft.
6. For a candidate canonical ID, hardconstruct a bounded
   `GET /api/records/{id}/draft` within the same grant/budget; never follow response
   links. Preserve candidate IDs privately as untrusted reconciliation handles.
   Zero/one/multiple matches all remain evidence only. A match does not bind the
   old ledger, reset create, authorize DOI allocation, PUT, upload or publication.

Source pins and exact local primary-source line references are retained in the
static review. Search defaults are framework evidence, not an assertion about
deployed configuration. Production compatibility/deduplication remains separate;
all existing IDs/DOIs/files and unrelated-record exclusions remain intact.
