# First-record PICES community-first release — 2026-10-06

Hold the first production draft until the actual PICES authority evidence, record
QA, independent program review, human release and separate provider grant all
bind the same record and runtime. The community-first v2
implementation has passed the staged focused checks below. Final current-head
review and actual CI are recorded on its PR before merge. It grants no provider action.
The [community-first decision](../../adr/0009-community-first-modern-publication.md)
supersedes the earlier publish-then-inclusion sequence retained in the
[publication ADR](../../adr/0006-finite-modern-singleton-publication.md); historical
receipts and spent attempts remain intact.

> 2026-10-06 update: use the merged runtime recorded in the [User-Agent handoff](zenodo_user_agent_handoff.md)
> rather than the frozen PR40 runtime pinned below; the sequence, limits and gates are unchanged.

PR38 merged at `4a3703df949a952bb7b9b00544a3132cea771bfc` after 748 passing actual
CI tests. Its measured modern coverage is 3,145 supported targets, with 788
outside that finite path. PR39 merged at
`8c0f77210b24859c89dcb5ecae2aba3331f34c29` after 767 passing actual CI tests.
Its [upload compatibility repair](modern_upload_compatibility_handoff.md)
supports validated completed-on-PUT uploads and identical duplicate bare binary
Content-Type values. Those results do not establish production release readiness.
The source scope, original XML, full legacy metadata, restricted access and blank
license remain unchanged.

## Evidence required before the first write

The Mac executor must retain actual PICES community and authenticated permission
captures. An independent reviewer binds their references and SHA256s to the
`modern-pices-authority-v1` projection, including the actual community UUID, slug
`pices`, explicit hierarchy, public visibility, submission/review policies,
record ID and owner. Missing hierarchy or permission information cannot become
guessed null/false defaults. Effective `manage`, `read_draft` and `submit_record`
permissions must be true; `include_directly` records its actual observed value.
Parent reports a Mac GET at 03:59:20 UTC observed UUID
`92279449-f6e1-422d-8610-40802567c58b`, slug `pices`, title
`PICES - North Pacific Marine Science Organization`, open submission policy,
`members` review policy and true `can_submit_record`, `can_include_directly` and
`can_update` flags. That capture was held by the Mac validator and is not yet
validated evidence. Its description says it is for testing/demonstration;
Brett's destination clarification remains pending. Do not dispatch publication
from this reported response or infer a named community role.

The locked `invenio-communities 29.3.0` archive, SHA256
`6cb102f4d2aabf4d784790cadcc299bec917ed8e500aae3c6789fbda6ca80ccb`,
confirms review policies `open`, `closed`, `members` and the effective permission
fields `ui.permissions.can_submit_record`, `can_include_directly`, `can_update`
in its `application/vnd.inveniordm.v1+json` community serializer. Submission policy
remains limited to `open`/`closed`. Community `can_update` is not target-draft
management evidence; record-specific management/read permission remains required.
The projected policy/permission fields are reviewed interpretations of captures,
not a claim that ordinary JSON exposes every effective permission.

The projection carries capture/review actors, observation/review/expiry times,
exact `community` and `permissions` evidence references, and the canonical
`reviewed_projection_sha256`. Review must follow capture, actors must differ,
and the evidence window is at most one hour. It must cover the entire execution
grant. A recomputed digest records the projection; the parent must establish
that the referenced captures and independent review actually occurred.

Saved-response QA and the separate human release must bind this same authority
projection, current source/preparation/bridge, duplicate/history proof and draft
snapshot before the draft-review PUT. Existing record checks, independent program
review, risk-based spot checks, protected IDs/DOIs and complete production
duplicate/history coverage remain required. Standalone source support and
repository merge authorization do not satisfy these release gates.

## Exact community-first sequence

The separate `modern-singleton-publish-grant-v2` has schema version 2 and limits
`{"get":22,"review":1,"submit":1}` over a window no longer than 600 seconds.
It binds the original state root, bridge, owner, exclusive writer, sole executor,
four exact saved input documents (`snapshot`, `qa`, `duplicate`, `release`) and
reviewed PICES projection. Its token scope is `deposit:write deposit:actions`.

The locked `invenio-requests 15.2.1` source archive was verified against SHA256
`9183df4663fd99e3d745b85414efcc04fd9768f0cb61cfc565b599e37a16a2a5`.
It confirms the `(status,is_open,is_closed)` triples `(created,false,false)`,
`(submitted,true,false)` and `(accepted,false,true)`. Request identities are
retained from the successful review response; raw token-clean bytes and their
receipt hash bind the known identity before any recovery GET. The live request
route uses UUIDs; the controller's safe opaque-string subset also accepts those
UUIDs without accepting paths, query strings or arbitrary origins.

| Stage | Fixed operation | Required outcome |
|---|---|---|
| Initial fence | Five GETs: draft, file listing, file descriptor, XML content, draft again | Same identity, metadata/access, original XML and stable draft revision; no existing record or parent review |
| Attach review | One PUT `/api/records/{id}/draft/review` | Exact `community-submission` request to the reviewed PICES UUID; retain its safe request identity |
| Review fence | The same five draft/file GETs | Exact record/file content and known PICES review; stable observed revision no lower than the initial revision |
| Submit review | One POST `/api/records/{id}/draft/actions/submit-review`, body `{"require_review":false}` | Validate the known community submission; this operation may publish immediately |
| Request status | One GET `/api/requests/{request_id}` | Exact topic, receiver, owner and status for that known request |
| Accepted readback | Five GETs: published record, file listing, file descriptor, XML content, record again | Same record/parent/file identities, exact XML/metadata, stable observed published state, actual PICES UUID membership and PICES default |

The post-review record must report the source-defined `draft_with_review` status.
The publication-specific validator checks this exact state and both review
locations before reusing ordinary draft metadata/file invariants; upload and
initial capture still require `draft`. All raw response receipts remain intact.

The review PUT body is exactly
`{"type":"community-submission","receiver":{"community":"<reviewed PICES UUID>"}}`.
Published membership must also match the explicitly captured parent community
when the reviewed hierarchy has one. Never derive a DOI from a numeric record ID;
retain observed record/concept DOIs and keep DOI registration verification separate.
The initial no-review check prevents the PUT from replacing another review.
The post-PUT fence observes a nondecreasing revision and requires both draft GETs
to agree; it assumes neither a fixed increment nor server-side compare-and-swap.
Record/file JSON uses `application/vnd.inveniordm.v1+json`; review and request
resources use `application/json`. Fixed production origin, verified TLS, no
redirects, bounded responses and no transport retry remain enforced.

A submitted/pending request is incomplete. Require `release_complete:true`, which
needs accepted status plus all five published checks. A later GET-only readback may consume one
known-request GET and five published GETs from the original 22-GET allowance and
unexpired grant. No fallback direct-publish route, acceptance action, delete,
request search, automatic resubmission or fresh budget is added.
Pending beyond the original window stays held. An expired grant cannot authorize
readback; later observation requires a separately reviewed read-only continuation
preserving the original attempt and consumed counts, with no new writes. That
continuation is outside this v2 grant and is not automatically enabled.

## Durable state and existing-record evidence

Publication retains `<uploads_registry_path>.modern-publication-v1.json` and
`<original_state_root>/<source_id>.modern-publish-v1.intent.json`. The journal
container and intent remain schema 1; new publication rows identify protocol
`community-first-v2`. This preserves canonical paths instead of creating a second
attempt allowance. An existing own-source v1 publication row/intent cannot be
migrated, reopened or replaced. Every dispatch intent/count is durable first;
uncertain errors keep spent writes and partial evidence held.

The explicit PR39 runtime bridge preserves the original verified draft journal,
create intent, preparation, upload grant, duplicate/history proof and their
historical request times. It changes the current runtime binding without reviving
an old grant or altering original receipts. Use the same production output/state
root throughout preparation, capture, QA and release.

A standalone remote capture provides evidence only. A positive exact XML match
must preserve the existing record ID/DOI and be reconciled with retained history;
unknown upload history does not prove remote absence or authorize another create.
Do not fabricate local creation journals or intents to make an existing record
pass the bridge. If its real history does not satisfy the bridge, keep the record
held for a separately reviewed finite adoption route.

## Offline preparation and executor handoff

Use the reviewed checkout and original paths. The existing offline bridge command
requires all five arguments:

```sh
python -B -m scripts.modern_publication bridge \
  --json-file PREPARED_JSON --output-dir ORIGINAL_OUTPUT \
  --preparation ORIGINAL_PREPARE_PACKET --old-grant ORIGINAL_UPLOAD_GRANT \
  --old-duplicate ORIGINAL_HISTORY_PROOF
```

The same five arguments are required for the other publication stages. A separate
capture grant permits five draft/file GETs and preserves the exact saved snapshot;
`capture` is a provider stage, not an offline preparation command. Prepare a new,
unapproved QA manifest from that snapshot, complete raw duplicate evidence and
the independently reviewed community projection:

```sh
python -B -m scripts.modern_publication prepare-qa \
  --json-file PREPARED_JSON --output-dir ORIGINAL_OUTPUT \
  --preparation ORIGINAL_PREPARE_PACKET --old-grant ORIGINAL_UPLOAD_GRANT \
  --old-duplicate ORIGINAL_HISTORY_PROOF \
  --snapshot SAVED_DRAFT_SNAPSHOT --duplicate RAW_DUPLICATE_PROOF \
  --community REVIEWED_PICES_AUTHORITY --manifest NEW_QA_PATH \
  --source-revision REVIEWED_COMMIT
```

After actual record/program review, `python -B -m scripts.release_manifest
--qa-manifest APPROVED_QA_PATH --release-manifest NEW_RELEASE_PATH` prepares an
unapproved release. Record the separate actual human decision, then bind exact
snapshot/QA/duplicate/release file hashes and the same community projection into
the v2 grant. Use the frozen runtime and staged test receipts below.

`preflight` with the original bridge arguments plus `--grant`, `--snapshot`,
`--qa`, `--duplicate` and `--release` validates the complete contract offline;
it constructs no provider transport:

```sh
python -B -m scripts.modern_publication preflight \
  --json-file PREPARED_JSON --output-dir ORIGINAL_OUTPUT \
  --preparation ORIGINAL_PREPARE_PACKET --old-grant ORIGINAL_UPLOAD_GRANT \
  --old-duplicate ORIGINAL_HISTORY_PROOF \
  --grant APPROVED_V2_GRANT --snapshot SAVED_DRAFT_SNAPSHOT \
  --qa APPROVED_QA_PATH --duplicate RAW_DUPLICATE_PROOF \
  --release APPROVED_RELEASE_PATH
```

Parent dispatches `publish` or the remaining
GET-only `readback` only after actual approvals and preflight. Only the assigned
Mac executor enters the production token through its terminal prompt; this code
lane performs no provider requests or credential reads.

## Frozen implementation and local validation

Final runtime SHA256: `999c23a83d9fbcb800f612c150708c474069f9baf0e9ef192e39107cd3633ec9`. Final 175-file source/test binding:
`ca632f061a554e43a7d7f3f77015145612b6f47c7cc689ca8de985fc2c5fd6f3`.

The [staged local receipt](modern_pices_community_focused_checks.json) retains the
159 passing core contracts (874.493 seconds) at their actual earlier binding, followed
by eight passing authority contracts at the final binding. The only final delta is
the source-verified `members` review-policy allowance, coherent synthetic policy
fixture and narrow regression; final-tree GitHub CI remains the full merge gate.
Both runs used cleared environments/dummy credentials, unchanged source bindings,
zero unexpected I/O and no provider calls. Scoped Ruff and documentation checks
pass. The rejected method-selector attempt ran no tests; the earlier interrupted
run remains retained and is not counted as a pass. Independent review found and
resolved the reviewed-draft status and top-level review guards.

All 4,206 original XML hashes match PR39; canonical aggregate SHA256
`3430315763379ef81c393cca00eb776952df3ad3f66856ef4b15edd48e396013`. Source mappings, source coverage and previous receipt bytes
remain unchanged. Final PR/head/tree, independent review and actual CI evidence
are recorded in the PR handoff; do not infer production clearance from these checks.
