# Run02 prepared-body evidence and one canonical readback

The second failed stage stays held. Parent/executor reports the existing candidate's
metadata PUT returned HTTP200, with all six expected metadata fields missing,
record access matching and file access mismatching. No file operation, DOI request,
or further GET occurred. Historical GET intents remain196; all312 prior private
files are reported preserved. Root has neither read that private evidence nor
issued provider requests. Preserve the original201 create, failed original stage,
failed continuation, spent create1/metadata1/diagnosticGET1, journals and receipts.

The committed PUT input is620 bytes, SHA256
`0197c230248e4192866b8662fa60a4cca4b05ed0d060fc67f6a9102bb6180128`.
Parent confirms a nonempty dictionary was passed through Requests `json=`, and
configured Content-Type was`application/json`; actual historical prepared headers
and serialized bytes were not retained. The3282-byte value was the response size.

## Evidence and limits

The independent dummy-token test exercised the actual committed shared execute
path, stopping before the adapter. Its POST prepared458 bytes, SHA256
`6699d88705dfc3daa76b8a41ac0cbb41e4fec3fc55c05fa25cb855c2e7d56978`;
PUT prepared481 bytes, SHA256
`1842cd59ad04211ce2368dd1410aa1fdaafa5d760edea5362c784fd02933c788`.
Both Content-Length values match, Content-Type is`application/json`, and decoded
JSON equals the entire frozen input, including all six supplied metadata fields
and restricted file access. See [exact-route source/body review](run02_body_serialization_independent_review.json).

The new standalone helper reproduces that ordinary Session.request preparation
without opening a failed stage or instantiating a controller. It replaces this
Session's send with capture plus a trusted local stop, blocks all HTTP adapters
and socket/DNS boundaries, restores the instance in finally, and has no original
send fallback. It emits fixed labels/booleans, numeric body/Content-Length and
SHA256 only; raw/decoded/encoded credential echoes suppress hashes and bodies.
An explicit executor-only mode prepares using its already configured opaque token
and ordinary environment/CA route, without printing or inspecting routing values.
This proves local preparation now, **not historical wire bytes, delivery or server
processing**. It creates no grant or ledger and spends zero provider allowances.

The [official modern REST reference](https://raw.githubusercontent.com/inveniosoftware/docs-invenio-rdm/production/docs/reference/rest_api_drafts_records.md)
specifies top-level metadata/access/files JSON for POST and PUT. The
[pinned metadata schema](https://github.com/inveniosoftware/invenio-rdm-records/blob/d4a4ef21ef5cd99b6d1350b537c82581799296a3/invenio_rdm_records/services/schemas/metadata.py)
declares subjects and leaves publisher optional. Both frozen payloads instead
contain undeclared metadata.keywords. Nested validation can return partial valid
data on an incomplete draft; this defect alone does not explain loss of every
metadata field and access.files. A current public source pin is not a claim about
the deployed Sandbox version. Do not add a publisher or change Content-Type on
this evidence. No payload edit, repeated PUT or new create is authorized here.

## Frozen runnable offline capture

Run from this reviewed checkout. Root/reviewers use only the first command:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m scripts.modern_request_body_diagnostics
PYTHONDONTWRITEBYTECODE=1 python -m unittest tests.test_modern_request_body_diagnostics
```

The default CLI clears environment lookup for the capture and disables netrc,
using a synthetic token. Only parent-dispatched sole executor
`01a0fed7-bf71-7384-95fd-3434599df03f` may run:

```bash
PYTHONDONTWRITEBYTECODE=1 python -m scripts.modern_request_body_diagnostics \
  --use-existing-private-sandbox-token
```

Do not print the environment, authorization header, proxies, CA or netrc values.
Keep the existing private token/configuration; do not create an alternate token
route. Return the closed projection only. If capture fails or a predicate differs,
hold with the fixed diagnostic; no live retry or fallback. A dry capture result
cannot recreate evidence for either spent live mutation.

## Parent dispatch: exactly one canonical GET, if the current window is active

This is a separate read-only diagnostic under the **already authorized current
recovery grant**. It is not a controller execute/retry/adoption, fresh approval,
grant reset or extended window. Parent must dispatch the sole executor. Root must
not execute it. If that original current expiry has elapsed, stop before intent;
do not guess the expiry or create a replacement window.

1. Use the exact already verified private run02 candidate/owner/parent/created
   identity from retained trusted receipts. Bind current packet SHA and unchanged
   runtimes: modern synthetic SHA256
   `4865590399aa47d5a24ce52605500b5c2fcf12a4479d49cda1ec18d40566e435`,
   continuation SHA256
   `5fb1b8275db0aa72f8175ad971bf8ceb1345cf240c4737e584229a603dc4c9c2`.
   Privately bind the original201 receipt, sealed canonical beforeimage, consumed
   continuation grant, failed state/journal and PUT200 response hashes, plus the
   unchanged312-file inventory. Never derive a candidate from a new search.
2. Create a distinct private0700 directory/0600 diagnostic ledger outside both
   failed stages and the preserved312-file tree. Set expiry to the earlier of
   now+120seconds and the **existing recovery grant expiry**. Bind historical196
   and exactly one additional GET with ceiling197. Acquire an exclusive lock;
   before transport fsync a permanently spent GET intent and197 cumulative count.
   Reentry/pending/failure may inspect evidence only, never repeat the read.
3. Hardconstruct only `https://sandbox.zenodo.org/api/records/{validatedID}/draft`;
   ID must match the retained positive numeric run02 ID. No query or request body.
   Use the reviewed ordinary Requests Session route and intended opaque bearer,
   Accept`application/vnd.inveniordm.v1+json`, TLS verification, zero adapter
   retries, `allow_redirects=False`, streamed response and timeout20. Preserve the
   existing environment/CA route. Verify prepared method/URL/auth match using
   booleans only; no account probe, constructor GET, inventory scan, link following
   or fallback route. Check expiry again after durable intent and immediately
   before send. A total wall alarm is min20seconds/remaining diagnostic window.
4. Record response-status and complete-body flags with fixed labels. Cap the
   complete response at65536bytes under the same wall deadline. A redirect,
   non200, truncation, JSON/type failure or deadline leaves that one intent spent;
   close the response/session and restore alarm, with no second request. Do not
   retain raw error or partial bodies.
5. For a complete200 JSON object call the pure
   `canonical_readback_projection(raw, token, expected_identity, owner)` from
   `scripts.modern_request_body_diagnostics`, where expected_identity contains
   only the privately retained id/parent_id/created. It checks credential echoes
   before hashing or allowing private retention. If safe, exclusively write/fsync
   a0600 raw canonical beforeimage **in the new diagnostic directory only**.
   Return only fixed identity/owner/first-draft/canonical-link/empty-file flags,
   six known metadata presence/type/match flags, record/file access flags, and
   errors-container presence/type/count/shape plus known error-field booleans and
   unknown-field-present flag. Never return raw messages, private values, unknown
   keys, URLs, exception strings, headers or credentials. Malformed errors do not
   authorize any action. This helper does not validate HTTP status or transmit.
6. Seal diagnostic receipt/state hashes and cumulative197; verify all312 prior
   files and both failed ledgers byte-identical. Return sanitized results and
   provenance to parent. Missing GET errors cannot prove absence of transient PUT
   validation errors. Even fully matching persistence is evidence only; no PUT,
   create, DOI/file operation, publish, delete, new version or controller restart.

The example [contract](../../../contracts/examples/run02_body_diagnostics.json)
is deliberately not an approval. GET evidence and actual prepared-body evidence
may narrow the cause; all mutation allowances and production gates remain held.

[Validation](run02_body_diagnostics_validation.json) records391 guarded tests and
nine focused contracts, including ten simulated readbacks. The
[independent helper/handoff review](run02_body_helper_independent_review.json)
repeated all nine focused tests and cleared the frozen implementation. Its code
and primary handoff pin is834f531; this final receipt/link-only addition changes
no runtime, packet, action bound or reviewed execution instruction.
