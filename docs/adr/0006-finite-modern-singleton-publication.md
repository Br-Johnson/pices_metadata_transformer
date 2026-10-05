# Finite modern singleton publication

Date: 2026-10-05. Scope: the same 19 reviewed NCDC/NESDIS/NOAA XML artifacts
as [ADR 0005](0005-finite-modern-singleton-drafts.md), one singleton per invocation.
This is executable integration code with offline fault tests, not live release
approval or a claim of coverage for all 3,933 source-supported targets.

## Contract and retained implementation evidence

The [retained API contract](../readiness/2026-10-03/modern_zenodo_api_contract.json)
pins Zenodo `7111dde7`, RDM `d4a4ef21` and their locked resources dependencies.
Independent review verified its 35 retained file hashes. The examined publish
resource consumes no body and returns a published record with HTTP 202. Its PID
component reserves missing required record DOI/OAI and parent DOI; registration
is asynchronous. The publish service has no examined revision or `If-Match`
precondition. Exclusive-writer authority and immediate readback are required;
other writers outside the shared local lock can still cause a race.

| Operation | Fixed path | Response / maximum attempts |
|---|---|---|
| Read draft and XML | `/api/records/{id}/draft`, `/files`, `/files/{key}`, `/files/{key}/content`, then draft again | Five GETs per bracket; exact revision, metadata, access and original bytes |
| Publish | `/api/records/{id}/draft/actions/publish` | POST without body, 202; once |
| Read published record and XML | Same five routes without `/draft` | Same identity/owner, original bytes, observed PIDs and stable published revision |
| Submit PICES inclusion | `/api/records/{id}/communities` | POST, 200; once |
| Read known inclusion request | `/api/requests/{request_id}` | GET, 200; exact request identity/topic/receiver/creator/status |

The inclusion body is exactly
`{"communities":[{"id":"<parent-verified PICES UUID>","require_review":true}]}`.
Its handler returns standard JSON without the record serializer. Inclusion POST
and request GET use `Accept: application/json`; record/file JSON uses
`application/vnd.inveniordm.v1+json`. Raw XML accepts XML or octet-stream media.
Every request uses the fixed production origin, verified TLS, no redirects,
no transport retries, at most 20 seconds and at most 1 MiB response bytes.
No response link becomes a dispatch destination.

Relevant pinned implementation anchors are RDM
`resources/resources.py::RecordCommunitiesResource.add`,
`services/communities/service.py::RecordCommunitiesService.add`,
`tests/resources/test_resources_communities.py` (forced-review test), and
`tests/resources/test_resources_review.py` (request identity fields). The complete
`invenio-requests` dependency is absent from the retained cache; only the
corroborated identity/status subset is enforced, not an invented full schema.
Request IDs are opaque safe path segments, not assumed UUIDs.

Publication moves the same file bucket and preserves object versions. Standalone
file resources bind `file_id`, `version_id` and `bucket_id`; embedded `id` is not
assumed to alias any of them. Published records have independently observed
`created`/`revision_id` values and lack draft commit links. Original draft identity
and timestamps remain in history. Observed record/concept DOIs are never derived
from the numeric record ID. Submitted inclusion is distinct from accepted PICES
membership. A returned DOI is distinct from externally verified DOI registration.

## Compatibility and immutable history

`scripts.modern_publication bridge` requires the original preparation packet,
upload grant, duplicate/history proof, verified draft journal and permanent
create intent in the original production state root. It validates each recorded
request against the original grant at that request's historical time. This does
not revive the grant or replenish a create/upload budget.

Only the current runtime or the reviewed PR34 runtime
`0f0a537dde0d6970ce6c64aad1169cf9ebb290cbcf7b527ab3917ace1393fff5`
may cross this versioned bridge. All other preparation evidence must match exactly:
source bytes, prepared input, full legacy metadata, modern body, artifact policy,
profiles, source plan and schemas. The current runtime and original row/intent
hashes become the new bridge binding. There is no generic ignore-runtime switch.
A future runtime needs another reviewed explicit bridge or execution on the
frozen runtime. Old receipts are not rewritten to obtain compatibility.

## Saved evidence, QA and release

A separate fresh capture grant spends exactly five GETs and saves the actual
bracketed response bytes (base64), media types, endpoints and hashes. Its snapshot
is created exclusively and never overwritten. Credential echoes are suppressed
before any response body is retained. Partial or interrupted capture cannot be
used for QA and does not get a fresh automatic budget.

The modern QA adapter uses fresh source preparation, this validated snapshot and
fresh complete raw scoped duplicate evidence. It never fabricates legacy
`/api/deposit/depositions` snapshots. The draft creation projection containing
only reviewed inventory/history digests is insufficient for this QA step.
A pending schema-2 manifest binds all evidence and remains unapproved. Explicit
record checks, reviewer provenance, checked-no-match adjudication, independent
program review and risk-stratified sampling remain required. Existing release
preparation then binds the entire exact QA manifest to a separate human release.
A grant or a JSON approval field is a recorded decision, not cryptographic proof
of the named signer's identity; the parent must establish actual authority.

## Fixed budgets and recovery

Capture and publication have separate permanent exclusive-create intents and
journals under the shared environment ledger lock. A publication grant binds the
bridge, owner, original state root, all four saved QA/release input files, a
parent-reviewed PICES identity/policy/permission projection, exclusive writer,
executor, and a time window no longer than 600 seconds.

The publication budget is 22 GETs, one publish POST and one inclusion POST:

1. Five immediate draft/file GETs and one publication POST.
2. Five published/file GETs, one inclusion POST and one request GET.
3. Five published/file GETs to verify unchanged content/PIDs after inclusion.
4. An unchanged read-only retry: one known-request GET and five published/file GETs.

Each attempt and request-body hash is durable before dispatch. Timeouts, HTTP
errors, redirects and invalid responses keep the attempt spent. Recovery uses the
same grant and remaining budget, performs GETs only and never sends an unspent
inclusion automatically. Lost publication response can be checked on the known
record ID. Lost inclusion response without a known request ID remains partially
complete and requires explicit reconciliation; no blind resubmission or request
search occurs. DOI observations survive failed semantic confirmation as untrusted
collision evidence. Confirmation requires independent record/file GET readback.
Cross-lane guards reject protected IDs/DOIs, excluded records, other modern
record/parent/candidate claims, and legacy identities/DOIs.

## Frozen execution interface

Only the assigned Mac executor may enter the token through its terminal prompt.
No environment or credential-file lookup is added. The code integration lane
runs offline tests and never invokes these provider stages. Parent dispatch and
the real canary/access/release gates remain necessary.

Use the frozen merged code with the original production output/state root:

```sh
python -B -m scripts.modern_publication bridge \
  --json-file PREPARED_JSON --output-dir ORIGINAL_OUTPUT \
  --preparation ORIGINAL_PREPARE_PACKET --old-grant ORIGINAL_UPLOAD_GRANT \
  --old-duplicate ORIGINAL_HISTORY_PROOF
```

Those five arguments remain required for every stage. Parent prepares an exact
new capture grant using the returned bridge binding and the schema enforced by
`authorize()`; `documents` is empty and limits are `{"get":5}`. Run `capture`
with `--grant CAPTURE_GRANT`. Preserve its fixed snapshot path and receipt.

Run `prepare-qa` with `--snapshot SNAPSHOT --duplicate RAW_DUPLICATE_PROOF
--manifest NEW_QA_PATH --source-revision FROZEN_COMMIT`. It creates an unapproved
manifest. After record/program review, use `scripts.release_manifest` to prepare
a separate unapproved release and record the actual human release decision.

For `preflight`, `publish` and `readback`, provide `--grant PUBLICATION_GRANT
--snapshot SNAPSHOT --qa REVIEWED_QA --duplicate RAW_DUPLICATE_PROOF
--release EXACT_RELEASE`. The publication grant's `documents` maps those four
names to SHA-256 hashes of the exact input file bytes. `preflight` is offline;
`publish` is the two-mutation bounded stage; `readback` is GET-only recovery or
unchanged retry. A new grant must never be used to bypass a retained intent.

Grant files have exact keys. Both stages require `schema_version:1`,
`kind:"modern-singleton-capture-grant-v1"` or
`"modern-singleton-publish-grant-v1"`, `approved:true` only after actual dispatch
approval, `executor:"01a0f3ae-ee1c-7046-9b04-36d35803903c"`,
`origin:"https://zenodo.org"`, `binding` from the bridge, the original absolute
`state_root`, decimal-string `owner`, exact `limits`, UTC `started_at` and
`expires_at`, nonempty `reviewed_by`, `token_scope:"deposit:write"`, and
`documents`. Capture has `documents:{}`. Publication adds
`exclusive_writer:true` and a `community` object with exactly `id`, `slug:"pices"`,
`evidence_sha256`, `reviewed_by`, `open_submissions:true`, and
`owner_authorized:true`. The parent must verify the underlying community evidence
and permission; placeholders or a stale inventory do not establish those facts.
Capture and publication grants use token scope `deposit:write`; this field does
not configure or expand actual provider token permissions.

## Remaining coverage and gates

The finite 19-source mapping remains the entire modern executable population.
The other singletons, all 228 paired targets, protected published-record repair,
external DOI-resolution evidence and community acceptance need their own
validated paths/evidence. The full Mac canary has not yet passed; at the parent's
latest checkpoint it had not run, revision 11 and cumulative 207 GET / 7 PUT /
1 create / 1 UI counts were unchanged. Offline success creates no live authority.
