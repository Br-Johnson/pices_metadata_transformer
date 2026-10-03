# Bounded modern synthetic Sandbox approval packet

This is ready for offline review and a concrete parent decision. **No live grant
has been issued and root made zero provider requests.** Source PR9 is merged at
`d0f13930baa5fbcd6684038d03954aad2baba5a5`; its tree exactly matches reviewed2bf5f8a.
The independent source-supported modern protocol research and narrow DOI-envelope
review are linked below. Deployment behavior remains something this bounded trial
would test, not a prerequisite that forces account changes or an open-ended audit.

The requested decision is: **approve one separate synthetic modern Sandbox trial
for namespace `pices-modern-synthetic-20261003-code-01`, solely by provider executor
`01a0fed7-bf71-7384-95fd-3434599df03f`, with the fixed packet, frozen runtime and
ceilings below?** Approval would let the parent materialize a private exact grant
and dispatch that executor. Until approval, only offline stage/tests are authorized.

The fixed title is `SYNTHETIC TEST ONLY PICES MODERN 20261003 CODE 01` and the one
filename is `pices-modern-synthetic-20261003-code-01.xml`. Its fictional organizational
creator, dataset type, date2026-10-03 and metadata PUT marker are test values. They
supply no production mapping or inference. PacketSHA:
`95d125ba6e47cb87cd89fcc981c8a179ee37127e0fe9ccab5711f9984b79787e`.

| Step | Exact method/path | Successful status | Maximum |
|---|---|---|---|
| Create fixed complete draft | POST `/api/records` |201|1|
| Allocate managed DOI, only if DOI key wholly absent | POST `/api/records/{id}/draft/pids/doi` |201|1|
| Fixed metadata after-image, preserving returned DOI | PUT `/api/records/{id}/draft` |200|1|
| Initialize fixed key | POST `/api/records/{id}/draft/files` |201|1|
| Upload fixed XML bytes | PUT `/api/records/{id}/draft/files/{key}/content` |200|1|
| Commit that file | POST `/api/records/{id}/draft/files/{key}/commit` |200|1|
| Exact readback | GET draft, files list, file entry, file content |200|4|
| Explicit unchanged completed retry | Same four GETs, same bound ID |200|4|

The absolute ceiling is **4POST+2PUT+8GET**, fourteen transport attempts lifetime.
If create supplies a valid managed DOI, its allocation allowance stays unused:
3POST+2PUT+8GET. There is no constructor, inventory, account, query, connectivity
or reconciliation GET, and no additional mutation allowance. All responses use
`Accept: application/vnd.inveniordm.v1+json`; metadata/init use application/json,
file content uses application/octet-stream. Exact HTTPS origin is
`https://sandbox.zenodo.org`. TLS verification stays enabled; environment proxies,
automatic redirects and retries are disabled. Each request/body has an absolute
20-second wall deadline plus20-second socket timeout and64KiB response cap; the
one grant window is30minutes including the explicit read-only retry. Fixed XML
fits the cap. No deadline or allowance is extended on restart.

Use the same known Sandbox owner and current token, whose deposit:write scope is
USER_REPORTED present. The pinned modern route verifies authenticated ownership;
its deployed scope sufficiency is still unverified and may be tested by this
trial. No publish scope or email-visibility condition is added; email visibility
is not_visible and nonblocking. The approved fixture requires managed datacite
DOI with Sandbox prefix10.5072, grounded in the earlier reviewed Sandbox fixture;
returned DOI is never fabricated, and allocation does not claim external DOI
registration. A different or malformed supplied DOI stops before allocation.

**Why a separate execution approval is required:** token permission is capability;
the existing original and separate-fresh grants each authorize a particular
namespace/create and both create allowances are consumed by uncertainHTTP500.
This candidate adds a distinct namespace, one new create and modern init/commit
(and conditional DOI) POSTs outside those exact spent grants. The user has already
authorized engineering, offline tests, publication of code and source PR9 merge.
This is the remaining bounded provider action decision, not a blanket API migration
or production-credential gate. Neither failed ledger is read, reset or replenished.

Reversibility and duplicate risk: staging/code changes are reversible. A attempted
POST may leave one unpublished orphan draft or allocated PID even if the response
is lost; no success count or HTTP500 proves absence. There is **no automatic
create retry, adoption of an uncertain returned ID, cleanup/delete, publish,
community submission or new version**. Any failed/interrupted stage remains held
with durable attempt and redacted diagnostics for separate reconciliation. The
parent confirms this exact namespace is unused and grants it exclusively; known
previously observed IDs are only a reject set, never a complete-inventory claim.
Returned identity/creation time/parent/owner/marker must match this fresh run before
another mutation. Create-start and bounded-response times are durable; the aware
server creation time must be within five seconds before start through five seconds
after response capture, with at most20seconds between the two client times. It is
bound once and must remain identical in every later envelope. This finite skew
permits small client/server clock differences. Full production dedup remains untouched.

## Separate runtime bindings and dispatch

Run from the reviewed checkout, not the legacy/fresh controller branches. Parent
must pin the final reviewed runtime commit and both module SHA values in the
validation receipt before granting. The packet inventory, full fixed metadata and
XML hashes, namespace, absolute private stage path, owner, executor and action
limits bind the approval independently of the source QA merge. No production
credential fallback or old provider-stage file is accessed.

Offline stage only (no token needed):

```bash
python -m scripts.modern_synthetic_canary stage --stage /ABS/PRIVATE/pices-modern-synthetic-20261003-code-01
```

The stage is exclusive and mode0700, controlled files0600, symlinks/hardlinks/extra
files rejected. It includes binding/state/journal from creation. Existing stages
are never replaced. The parent may create `approval.json` **only after explicit
approval**, matching the JSON shape below; fill private values from existing
verified provenance, not guesses/new probes. `binding` must exactly equal the
stage's `binding.json`, itself pinned to the reviewed modules and packet. Required
keys are strict. This is an illustrative shape, deliberately not a usable grant:

```json
{
  "schema_version": 1,
  "approved": false,
  "approval_reference": "EXPLICIT PARENT DECISION REQUIRED",
  "executor": "01a0fed7-bf71-7384-95fd-3434599df03f",
  "binding": "EXACT binding.json OBJECT",
  "limits": {"create":1,"doi":1,"metadata":1,"init":1,"content":1,"commit":1,"get":8},
  "started_at": "AWARE UTC START AFTER APPROVAL",
  "valid_until": "EXACTLY START PLUS 30 MINUTES",
  "owner": "PRIVATE KNOWN POSITIVE INTEGER",
  "known_ids": ["PREVIOUSLY OBSERVED POSITIVE DECIMAL STRING IDS"],
  "exclusive_namespace_confirmed": false,
  "deposit_write_user_reported": true,
  "prior_create_allowances_permanently_spent": true
}
```

Write grant mode0600 without printing private owner/stage/token. The actual approved
grant sets approved/exclusive true and exact typed values. The CLI never issues a
grant. Only the provider executor then uses its existing Sandbox token in environment:

```bash
python -m scripts.modern_synthetic_canary execute --stage /ABS/PRIVATE/pices-modern-synthetic-20261003-code-01
python -m scripts.modern_synthetic_canary retry --stage /ABS/PRIVATE/pices-modern-synthetic-20261003-code-01
```

The second command is valid only after full first-pass readback, within the same
window, and makes fourGETs with zeroPOST/PUT. A second retry or default execute
on an attempted/completed stage stops with no requests. Flock excludes concurrent
CLI execution. Before every transport the exact action count and pending intent
are fsynced to state and a hash-bound journal. Missing/mismatched/pending/failed
state blocks restart; no blind failed-state reset. Raw bodies, private owner and
URLs never enter the public receipt. A syntactically valid create201 ID is retained
privately as an untrusted reconciliation candidate before rejecting a credential
echo elsewhere in the response. An ID containing the credential is never retained.
The echo still permanently holds the attempt; neither that candidate nor a code
merge authorizes adoption, another create or live execution. Same-ID exact metadata/DOI/count/size/checksum
and byte readback is required. Modern embedded record file metadata is validated
separately from the REST file transfer envelope; unrelated descriptive links are
inert and only exact constructed action paths are used.

Tests and evidence: [validation receipt](modern_synthetic_validation.json),
[source-supported plan review](modern_synthetic_plan_review.json),
[modern primary-source research](modern_zenodo_api_research.md),
[contract/evidence](modern_zenodo_api_contract.json),
[PR9 merge receipt](source_pr9_merge_receipt.json),
[exact821 questions](remaining_source_scope_questions_821.md).
