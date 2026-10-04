# Same-draft controlled subjects repair — 2026-10-04

Ready for parent dispatch to sole provider executor
`01a0fed7-bf71-7384-95fd-3434599df03f`: one corrected metadata PUT followed by one
canonical draft GET, on the existing owner-verified empty run02 draft. Root and
reviewers issue zero provider requests and read no real credential/private stage.
There is no create, DOI allocation, file initialization/upload, publication, delete,
new version, search, inventory GET, redirect, automatic retry or old-state reset.
Completion means this metadata repair only; later file/PID trial work is not run.

## Authority and material change

This is a specifically directed correction within Brett's approved newer-API
fictional Sandbox trial, following the demonstrated legacy-keyword schema defect.
Parent's current instruction explicitly asks for the controlled same-draft repair.
The material allowance change is **one additional metadata PUT** and **one GET**
under a fresh, parent-bound window of at most ten minutes. The prior metadata PUT
stays spent; its expired grant is preserved as provenance, not extended or reused.
No additional create allowance or production capability follows. The parent can
dispatch this exact plan using that existing instruction; no generic new user
permission loop is needed. Staging does not mint the executable grant.

## Sealed inputs and preflight

Parent's fresh GET197 reported the exact retained ID/parent/created/owner,
first-draft state, canonical links and empty files matching; all intended metadata
remained absent, record access matched, file access mismatched and no GET errors
container existed. Its complete private beforeimage SHA256 is
`866775b60653bd5b25b1a59d9965fb070e07213a9310948f152df5d300fcee1b`.
The earlier PUT's intended changes did not persist; its transient validation
errors remain unknown. Root does not infer the complete cause or inspect that body.

The executor must use that retained beforeimage and the exact failed owned
continuation stage. `verify_origin` rechecks the original201 receipt, original
create interval and original failed ledger through the existing sealed verifier.
It additionally verifies the spent metadata-PUT state's prior binding, old runtime
hashes, grant, journal, one PUT200 receipt, failed/pending metadata intent and exact
same ID/parent/created/DOI-absent identity. Creation time stays tied to the original
create interval, not the new repair window. The latest beforeimage may contain
only known empty/default metadata; record access is public and unrepaired file
access is public or absent. Its exact sealed hash, ownership and empty-file
contract are required regardless of those permitted default shapes.

Retain the immutable original `preserved_root=/workspace` exactly as ancestry
provenance. Its mode0755 is legitimate; never chmod it, edit the old origin or
recursively select the entire workspace. Select the actual preserved evidence:
whole original failed stage, failed owned continuation, complete GET197 diagnostic
tree and all other historical evidence trees/leaves. The sole executor seals a
private0600 manifest `{"schema_version":1,"files_sha256":{"/absolute/file":"sha256"}}`
from the existing retained evidence, covering every353 previously reported file.
No inferred replacement count or reconstructed history is acceptable.

Use `--preserved-manifest` plus nonoverlapping `--preserved-root` evidence subtrees;
manifest-only selection also supports exact loose leaves under shared directories.
Every declared hash must match, and every actual original/failed stage file and the
latest beforeimage must be covered. The manifest source is itself inventoried and
its copied contents join the sealed static inputs. The actual inventory count may
therefore exceed353; it is computed and must be bound exactly by parent dispatch.
The338 floor is a sanity check, not proof of completeness. Files remain private
regular leaves without hardlinks. Canonical0755 directories are permitted only
without group/other writes. All symlink ancestors/descendants and stage overlap
are refused; the trusted sticky `/tmp` ancestor is permitted for existing stages.
No public sibling is read merely because it shares `/workspace`.
The complete inventory, copied ledgers, sealed source/beforeimage and runtime are
reverified at initialization, before each request and before completion. Missing
or changed history holds without another provider call. No old file is edited.

Create a distinct0700 directory ending exactly
`pices-modern-synthetic-20261003-code-02-subjects-repair`, outside every preserved
root, with0600 files. Sole executor's offline staging command is:

```bash
python -m scripts.modern_run02_subjects_repair stage \
  --stage <absolute-new-repair-stage> \
  --prior-continuation <absolute-existing-failed-owned-stage> \
  --beforeimage197 <absolute-retained-canonical-GET197-body> \
  --preserved-manifest <absolute-sealed-complete-history-manifest> \
  --preserved-root <actual-original-failed-stage-or-evidence-tree> \
  --preserved-root <failed-owned-stage> \
  --preserved-root <GET197-diagnostic-tree>
```

Use the existing private Sandbox environment token/configuration only. Do not print
environment, authorization/proxy/netrc/CA values or raw private identities/bodies.
If broader roots already include a named stage, supply the containing root once;
do not add overlapping roots. Additional disjoint preserved trees must also be
included. Failed or partially created staging remains held; do not erase/recreate.
Choose a fresh destination when an earlier staging directory exists. The reported
blocked dispatch consumed zero PUT/GET and historical reads remain197.

Before a parent execution window begins, run:

```bash
python -m scripts.modern_run02_subjects_repair preflight --stage <absolute-new-repair-stage>
```

This uses the same complete local input validation as the real Controller:
lineage, all file hashes and permissions, binding/state/journal, same empty identity,
metadata/access beforeimage, token-echo exclusion and actual Session-prepared494-byte
PUT. It never sends, writes a ledger, mints/loads a new grant or consumes an intent.
Return only its closed hashes/counts to parent. Missing/changed inputs hold before
another live window. A preflight object cannot run or request without authorization.
Parent binds the complete new runtime/input/inventory receipt only after this passes.

## Exact bound executable grant

Parent dispatch supplies a fresh explicit approval reference identifying Brett's
standing trial and this controlled-repair instruction. The sole executor writes
`approval.json` atomically0600, after successful read-only preflight, with **exactly** these fields:

- `schema_version:1`, `approved:true`, that `approval_reference`, and the exact
  executor ID above.
- `binding`: the complete unchanged new `binding.json` object; this binds current
  four runtime hashes, historical packet, every copied input, GET197 and the exact
  prepared PUT hash. Do not substitute an old binding or amend private ledgers.
- `limits:{"metadata":1,"get":1}`; `owner` and `known_ids` copied exactly from the
  sealed original create approval.
- Aware `started_at` at dispatch and `valid_until` no later than start+600seconds.
  There is no implicit extension or revival of an old expiry.
- `existing_candidate_only:true`, `no_create_or_reset:true`,
  `controlled_schema_repair:true`, `historical_get_intents:197`.
- `preserved_file_inventory`: the exact computed `{count,sha256}` returned by
  staging and independently bound by parent dispatch.

The public [contract/example](../../../contracts/examples/run02_subjects_repair.json)
has `approved:false`; it is not a usable grant. No extra keys or broader limits
are accepted. Runtime/source/grant drift rejects before transport.

## Two requests, with permanent intent accounting

Execute exactly once, only after the explicit grant is bound:

```bash
python -m scripts.modern_run02_subjects_repair execute --stage <absolute-new-repair-stage>
```

An exclusive stage lock precedes execution. The repaired body is the unchanged
historical code02 metadata-PUT source, explicitly projected to the modern subjects
schema. Requests must prepare **494 bytes**, SHA256
`4e47c3b2340483500d99ec9807fd9c90201532713b8b48e4adfe2e539fc0fb74`,
with JSON content type/length and intended opaque bearer. The current ordinary
Session.request environment/CA route is preserved. The shared preparation hook
checks exact method, canonical URL, authorization, Accept, content type, length
and body hash before send. No pids are sent. Existing source-backed DOI-absent
state is required on both responses; no PID request is introduced.

1. Before transport fsync `metadata:1` and the pending exact PUT intent. Hardcode
   only `https://sandbox.zenodo.org/api/records/{sealedID}/draft`. Require HTTP200,
   complete bounded credential-free JSON, no errors, the exact same identity/owner/
   first-draft/created/canonical links, empty files, all six corrected metadata
   values including exact full subjects, public record access and restricted file
   access. Publisher may use the previously supported optional default only. Safe
   validation-error flags are retained before status/identity/metadata rejection,
   including400 and200; never messages, unknown paths or private values.
2. Only after the PUT response passes every contract and validation is durably
   acknowledged, fsync `get:1` and pending canonical GET intent. GET the exact same
   draft URL with no query/body or link following. Require HTTP200 and the same
   complete metadata/access/identity/empty-file/DOI-absent contracts. Verify all
   preserved history again, then seal completed metadata-repair evidence.

Both requests have TLS verification, zero adapter retries, `allow_redirects=False`,
streamed65536-byte response ceiling, timeout20 and a total wall alarm bounded by
20seconds or remaining repair expiry. Expiry is rechecked after intent fsync,
preparation, before send/adapter and throughout response streaming. The optional
prepared hook is absent for every other controller; their behavior remains.

New counts are at most `{metadata:1,get:1}`. Historical reads197 become at most198;
run02 metadata-PUT intents1 become at most2; run02 create intent remains1. Other
historical counts stay in their immutable original ledgers and inventory. Attempt
counts describe durable intent, not proof that bytes reached the provider.

Any uncertain/failed/redirected/expired/credential-bearing/truncated response,
contract failure or interruption permanently holds the new stage and its spent
intent. Failed PUT has no readback. Readback failure does not repeat PUT or GET.
Reentry after either attempt, completed execution and any retry request are refused.
Return only closed receipts/flags/hashes to parent, preserving all raw private
evidence and prior inventory. Success supplies evidence for the next separately
reviewed same-draft phase; it does not publish or complete the whole file trial.

The [evidence-layout repair handoff](run02_evidence_layout_handoff.md) supersedes
the earlier runtime pin and preservation-root recipe. Prior receipts stay intact.
The earlier [validation](run02_subjects_repair_validation.json) records411 guarded tests and
seven independently repeated repair contracts. The
[final independent review](run02_subjects_repair_independent_review.json) binds the
frozen runtime/contract/handoff checkpoint. Source restoration remains a separate
coherent42-member integration and changes none of these provider instructions.
