# Finite modern singleton drafts

Status: implemented for offline validation; live execution requires separate evidence and authority.

PR33 made legacy mutations durable. Its payload, integer IDs, mutation names and
remote QA shape do not implement the modern API. This increment adds a separate
versioned mapper and executor for the 19 members of the pinned
`ncdc_nesdis_noaa_literal_19` creator cohort. It does not widen a fictional canary
policy or change any of the 4,206 original XML files or source-status profiles.

## Source contract

`scripts.modern_singleton.prepare` reruns `assess_source`, the original artifact
contract and the singleton boundary. It verifies the exact current creator
profile, source plan, source hashes and explicit organizational creators. The
publication date remains the approved source metadata date. `resource_type: other`
describes the restored XML; public descriptive metadata and restricted XML files
retain USER_ATTESTED rehosting and no new license grant.

The explicit new policy assigns `publisher: Zenodo` as repository host of this
restored artifact. It makes no claim about the original dataset's publisher or
authorship, or when Zenodo hosted the artifact. All assembled legacy metadata is
preserved in a labeled, escaped additional description. In particular, the old
forced PICES publisher is labeled a legacy mapping value, not a source attestation.
The original complete XML remains the attached file, byte for byte.

The stored modern record schemas are validated offline. Vocabulary `other` is
supported by retained RDM resource types (`d4a4ef21`, file SHA256
`825e8249526f1e88b836cf4a7f214ccebfec38cc43b0911a2d4f43e1a3cd59a9`)
and Zenodo description types (`7111dde7`, file SHA256
`14bdcfa742a8be05c774a23425741720d24fe1409240c7644571c6a9fd2665a5`).
The service sanitizes HTML using deployment configuration. Exact preservation of
the escaped block must therefore pass actual response/readback comparison; this
implementation never normalizes away changed HTML or source content.

## Execution contract

The retained [modern API contract](../readiness/2026-10-03/modern_zenodo_api_contract.json)
and RDM 35.2.0 file-resource tests support this sequence with the full body on create:

| Action | Fixed route | Required HTTP status |
| --- | --- | --- |
| Create metadata-bearing draft | `POST /api/records` | 201 |
| Initialize one original file | `POST /api/records/{id}/draft/files` | 201 |
| Upload original bytes | `PUT /api/records/{id}/draft/files/{key}/content` | 200 |
| Commit uploaded file | `POST /api/records/{id}/draft/files/{key}/commit` | 200 |
| Verify components | GET draft, file list, file descriptor, bytes, draft again | 200 each |

Creation can return 201 with validation errors. Before file initialization the
executor verifies all submitted metadata, access, returned owner/parent/record,
creation time, empty files, unpublished first version, empty PIDs and canonical
links. Only the exact upstream missing-upload warning is allowed at that point.
After commit no validation errors are allowed. The final draft GET must have the
same revision as the first GET, bracketing component checks. An unchanged retry
uses the same five GETs and exact revision, with no mutations.

The fixed cumulative budget is ten GETs and one of each of the four writes. All
requests use modern MIME, fixed constructed routes, verified TLS, bounded bodies
and deadlines. There are no redirects, automatic retries, DOI reservation,
metadata PUT, publication or deletion. The real transport accepts an explicit
in-memory token only on the Mac; import, preparation and preflight never probe a
provider. CLI failures print closed diagnostics. Receipts contain hashes and
bounded identity fields, never provider bodies or echoed credentials.

## Authority and state

Source support alone is insufficient. A reviewed grant binds the complete
source/payload/artifact/runtime/schema evidence, canonical production state root,
sole executor, owner, exact action budget, passed canary receipt and a window of
at most 600 seconds. It also binds a separately reviewed duplicate/history
projection with complete coverage, no matching IDs/DOIs, retained evidence hashes
and an unexpired window. The parent must verify those underlying receipts; JSON
fields are neither a cryptographic signer nor an automatic absence detector.
The retained incomplete production inventory does not satisfy this requirement.
No production grant is supplied by this commit.

The independent `*.modern-v1.json` journal stores per-source bindings, identities,
request counts and consumed attempts. A separate permanent O_EXCL create-intent
file prevents journal loss from replenishing create. The common environment lock
serializes modern and legacy execution. Both paths refuse a source attempted in
the other path; returned protected/excluded IDs and existing legacy identities
are held. A valid numeric candidate returned by a rejected create response is
retained as **untrusted evidence**, never as authority for later requests.

Every attempt is durable before transport. An interrupted execution is never
replayed, even when some later actions were unspent. Read-only recovery can verify
a completed same-ID draft within the original exact grant's 600-second window
and remaining ten-GET budget. A lost create response, pending upload, exhausted
budget or expired grant remains held. There is no reset, grant renewal, automatic
identity adoption or partial-write continuation in this version. Preserve all
state and receipts for a later reviewed recovery increment.

## Validation and remaining work

Run the real-source and executor fault contracts without credentials or network:

```sh
python -B ci/run_offline_tests.py tests.test_modern_singleton tests.test_modern_singleton_executor tests.test_production_mutations
```

The new tests cover all 19 real mappings, the four-write protocol, unchanged
readback and interruption/identity/durability/budget/credential boundaries.
Actual current-head CI runs the complete guarded suite before merge.

For a separately prepared and assessed member, the following entry points are
offline. `--output-dir` must be the canonical production output/state directory
whose complete prior history the parent reviewed, never a fresh directory chosen
to bypass an earlier attempt. Preparation prints the exact evidence/binding; it
does not create a grant or claim that duplicates are absent.

```sh
python -B -m scripts.modern_singleton_executor prepare --json-file /approved/prepared/FGDC-141.json --output-dir /canonical/production-output
python -B -m scripts.modern_singleton_executor preflight --json-file /approved/prepared/FGDC-141.json --output-dir /canonical/production-output --grant /approved/grant.json --duplicate-proof /approved/duplicate-proof.json
```

Only after all separate provider gates are satisfied may the parent dispatch the
same arguments with `execute` to the sole Mac executor. That action prompts for
the token without echo or persistence. `readback` uses the same original grant
and state for the GET-only retry/recovery described above. This coding handoff
does not dispatch either action. Do not use a new grant or output directory to
restart an attempted create.

This is an executable **draft** increment. Mandatory production blockers remain:
the independently verified live canary result, complete scoped duplicate/history
evidence, a real provider grant, actual source-payload readback including HTML,
modern QA/release/publication integration, paired-class execution, and protected
record corrections preserving existing files, IDs and DOIs. The broader 3,933
source-supported targets have not all acquired a modern mapping or live readiness.
Typed personal creators and other mapping cohorts need separate reviewed coverage.
Unspent-step continuation and read-only grant renewal are later recovery features;
they are not required to demonstrate this finite uninterrupted draft protocol.
