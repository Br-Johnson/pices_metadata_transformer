# Modern upload compatibility repair

This production-client repair handles a validated file upload that is already
completed when the content PUT returns, and identical duplicate binary
`Content-Type` values on XML download. Source selection, metadata request wire,
original XML, rights, production identity, grant budgets and release gates stay
unchanged. **135 focused guarded tests passed**, including 19 new compatibility
regressions. The [actual result](modern_upload_compatibility_focused_checks.json)
records zero failures/errors, zero unexpected guard events and unchanged source
bindings. All 4,206 original XML hashes still match the PR38 baseline. Actual
current-head CI, final independent review and merge evidence belong to the PR
timeline; the local receipt identifies its base checkout plus measured changes.
No provider action is authorized by this handoff.

Frozen repaired runtime SHA256:
`7c3e7184f490cc4e43743f12fa831d58e6b79d8e36f93bd7e9c92a2a637f57be`.
The 174-file source/test binding is
`10041eb4f43e5edb2e3fa193a696fd4625af1d2ec7b7535a6e61362d40bc446c`.

## Evidence checkpoint

Parent reports the sole Mac executor closed the bounded Sandbox draft612988
canary at revision13: exact 439-byte XML download, unchanged retry and final fence
passed; draft unpublished with no PID. The Mac-local closure is
`task4/mac-xml-canary-closure-20261006.json`, parent-reported SHA256
`e109ae135006ba5829ff44e8e0da289e6cc985f7c506d7a57e9f89bf565df948`.
Reported cumulative counts are 220 GET / 9 PUT / 1 create / 1 UI / 1 file-init /
0 commits. Parent also reports four offline Mac reproductions of completed-on-PUT
and identical duplicate binary media headers. No fixed-plus-one production
revision defect was reproduced.

The Mac-local `task4/production-preparation-20261006/compatibility-review.md`
and exact sanitized response fixtures are unavailable in this checkout; the clean
responses have been requested and remain pending. These are parent-reported
observations, not an independently inspected raw-response receipt in this code
lane. Do not probe a provider or access raw/private Mac fixtures to fill the gap.

Parent's proposed first production source is FGDC-141, XML SHA256
`3f53f9d0d1d49631ccb6c2885312d3282870c32bd392abe57bd035f8cc139b27`,
with parent-reported wire SHA256
`16d25f25b0e5e606de85f5b4327a6872a8f7f90c03f26cc70908dc5eb914ea33`.
These observations do not establish current preparation binding, duplicate
absence or dispatch authority; the assigned Mac must reconcile its actual
prepared input and repaired runtime before any separately granted request.

PR38's finite Exxon increment has measured coverage of 3,145 supported singleton
targets, preserving all 2,733 prior mappings; 788 supported targets remain outside
the mapper. Its 148 focused tests and measurement receipts are retained in the
[Exxon handoff](modern_exxon_handoff.md). PR38 merged at
`4a3703df949a952bb7b9b00544a3132cea771bfc` after exact-head independent Codex
approval and 748 passing actual guarded CI tests. Its tree is
`5e7b76364059c4cf1c4bda9d176df54d3b8e7aae`; main, parents and original FGDC
tree were verified. This repair preserves that frozen checkout and evidence.

## Bounded behavior

The unchanged draft grant limit is
`{"get":10,"create":1,"init":1,"content":1,"commit":1}`. It is a maximum,
not an instruction to send a commit after successful completion.

| Validated content PUT result | Writes actually used | Subsequent verification |
| --- | --- | --- |
| `completed` with exact key, routes, transfer type, size and checksum | Create POST, file-init POST, content PUT; **commit 0** | Five GETs, then eligible unchanged GET-only retry |
| `pending` with exact key, routes and transfer type | The same three writes plus one commit POST | Five GETs, then eligible unchanged GET-only retry |

An invalid or uncertain response holds the spent attempt. The completed branch
persists optional `upload_completion` only after the full file-response
validation: exact schema 1 / `content-completed-v1`, request index 2 and the
validated content-response hash. Journal validation checks the bound three-write
transcript; `commit:0` alone never establishes completion. Once this marker is
present, the draft runner permits only GETs. Full readback still verifies record
identity, metadata, restricted files, exact XML bytes and a stable revision.
The retry uses the same original grant, state root and remaining ten-GET budget.
No reset, new state directory, revived grant, mutation retry or budget increase
is introduced.

Historical PR34–PR38 preparations remain marker-free four-write transcripts.
The publication bridge accepts PR38 runtime
`1ac72000a7697bedef5b6e76ca0a28252a85f36bb0529a7e521c68aa4177d9e2`
for policies/schema versions 1–4, with the existing older-runtime allowlists
retained. All nonruntime preparation evidence, original request bodies, grant
times, intents and identities must match. A completed-on-PUT marker can cross
only a current-runtime preparation; it cannot be attached to historical evidence
to manufacture a three-write success. Both current branches still need saved
readback, QA and the separate publication/release contract.

The shared response-media parser accepts duplicate values only for binary reads:
every comma-separated member must be the same bare allowed media type
(`application/octet-stream`, `application/xml` or `text/xml`) after case/space
normalization. Duplicate parameterized values, JSON duplicates, mixed types and
empty members remain held. Draft and publication XML downloads use the same
rule; no metadata comparison or request-body normalization is added.
Credential-clean observed DOI claims keep their existing reject-only collision
barrier even when strict media validation then rejects the response. Such a
retained claim never authorizes adoption, publication or a following mutation.

## Offline preparation and verification

Use the frozen reviewed code and actual parent-reviewed paths. The following
entrypoints make no provider requests; `prepare` prints its new exact binding.
The canonical production output/state root must retain all existing history.

```sh
python -B -m scripts.modern_singleton_executor prepare \
  --json-file /approved/prepared/FGDC-141.json \
  --output-dir /canonical/production-output

python -B -m scripts.modern_singleton_executor preflight \
  --json-file /approved/prepared/FGDC-141.json \
  --output-dir /canonical/production-output \
  --grant /approved/grant.json --duplicate-proof /approved/duplicate-proof.json
```

The named grant/proof paths are placeholders for real reviewed artifacts, not
grants supplied by this document. Repaired runtime binding requires current
preparation and an appropriately bound parent grant; it does not reopen an
already consumed attempt. Do not move historical production state or reuse
measurement directories as execution roots.

Run the affected contracts under the repository's cleared-environment offline
guard; retain the actual result and binding before claiming success:

```sh
python -B ci/run_offline_tests.py \
  tests.test_modern_upload_compatibility \
  tests.test_modern_singleton_executor tests.test_modern_publication \
  tests.test_modern_publication_qa tests.test_modern_exxon_coverage
```

Current-head CI and substantive independent Codex review remain the merge gates.
Parent alone dispatches the sole assigned Mac executor after the verified live
canary, complete fresh scoped production duplicate/history evidence, owner/
identity checks and a bounded grant are reconciled. Only that separate dispatch
may use `execute`; `readback` retains GET-only recovery and spent-attempt rules.
Hidden terminal token entry, in-memory credentials and Mac-only transport remain
unchanged. Cloud integration performs no provider calls or credential reads.

Publication interfaces and fixed budgets remain in
[ADR 0006](../../adr/0006-finite-modern-singleton-publication.md): `bridge`,
`capture`, `prepare-qa`, `preflight`, separately authorized `publish` and
`readback`. Complete saved readback, record QA, independent program review,
human release, PICES community authority and existing ID/DOI protections remain
mandatory. Neither the canary report nor this compatibility repair releases the
paired targets, protected records or source-held/malformed inputs.
