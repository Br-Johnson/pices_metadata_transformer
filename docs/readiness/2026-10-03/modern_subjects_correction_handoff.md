# Fixed synthetic subjects correction — 2026-10-04

This handoff corrects the modern synthetic request schema and captures closed
validation-error flags before a failed response contract stops execution. It is
offline engineering, not a repaired PUT plan, grant, controller restart or provider
dispatch. The existing run02 draft and every spent/uncertain allowance remain held.
Root and reviewers made zero provider requests and read no real credential or
private stage. Only executor `01a0fed7-bf71-7384-95fd-3434599df03f` may perform any
subsequently authorized provider action; parent must dispatch it separately.

## Reconciled live evidence, supplied by parent

Parent reports one fresh, separately authorized canonical GET completed, with
cumulative GET197 and `canonical_projection_complete`, pending false. The exact
retained draft identity, owner, first-draft state, canonical links and empty files
match. All six expected metadata fields remain absent; record access matches and
file access mismatches. The GET contains no errors container. Its private complete
beforeimage SHA256 is
`866775b60653bd5b25b1a59d9965fb070e07213a9310948f152df5d300fcee1b`.
Root has not read that beforeimage. The prior PUT did not persist the intended
changes. Absence of GET errors cannot establish what transient PUT validation
errors were returned. Historical prepared-body evidence does not reconstruct the
bytes of that actual PUT, whose prepared wire was not retained.

The earlier mutation window is expired. All prior receipts, ledgers, cumulative
reads and parent-reported private inventory remain preserved. This PR supplies no
new read window and no additional live action. No private transfer is needed for
the fixed schema correction.

## Supported wire schema and immutable input

The pinned [RDM metadata schema](https://github.com/inveniosoftware/invenio-rdm-records/blob/d4a4ef21ef5cd99b6d1350b537c82581799296a3/invenio_rdm_records/services/schemas/metadata.py)
declares `metadata.subjects`; it does not declare `metadata.keywords`. The locked
vocabularies14.4.0 [subject relation schema](https://github.com/inveniosoftware/invenio-vocabularies/blob/25815eecf1c962bbbb89db5f79d5cddcd4ea58f5/invenio_vocabularies/contrib/subjects/schema.py)
uses `subject` as free text, and its [base relation schema](https://github.com/inveniosoftware/invenio-vocabularies/blob/25815eecf1c962bbbb89db5f79d5cddcd4ea58f5/invenio_vocabularies/services/schema.py)
permits a nonempty free-text relation without an ID. Zenodo's pinned
[legacy deserializer](https://github.com/zenodo/zenodo-rdm/blob/7111dde7d1ebf6f64bc695edf7ad8cce5bfa1ac7/site/zenodo_rdm/legacy/deserializers/metadata.py#L345-L353)
maps each legacy keyword to a subject object. These primary sources support the
wire correction; they do not prove the live deployment's exact revision or explain
independently why all other metadata and file access failed to persist. See the
unchanged [schema review receipt](modern_subjects_schema_independent_review.json).

`modern_wire_payload` deep-copies only the fixed fictional source body. It requires
the exact one-element namespace keyword list, refuses preexisting subjects, removes
`keywords`, and inserts exactly
`subjects: [{"subject": "pices-modern-synthetic-20261003-code-02"}]`.
Nothing else changes. Both regular and owned controllers use this projection;
readback requires exact complete subject-object equality and rejects legacy
keywords, extra IDs/schemes and namespace changes. Publisher remains optional and
is not invented for this fixture. Production mappings are unchanged.

The historical code02 packet SHA256 remains
`0f54838bf45ebecccaf575db4145c5a51cdd01507f0aaa6e9b418aadd786db13`.
Historical source files, earlier contracts/captures and sealed beforeimage
constants stay byte-identical. [The new wire example](../../../contracts/examples/modern_subjects_wire.json)
separately binds immutable source hashes and canonical encoded projected bodies;
`approved` is false. Canonical encoded bodies and Requests-prepared wire bodies
have different encodings and hashes. The [fixture capture](modern_subjects_fixture_wire_capture.json)
records the prepared body: POST471 bytes SHA256
`85c6d0f0b2a72fadfcc8632d68cbacdb58cc500cc1b462e2cc4ae3d443d67c2f`,
PUT494 bytes SHA256
`4e47c3b2340483500d99ec9807fd9c90201532713b8b48e4adfe2e539fc0fb74`.
Historical preparation remains POST458 /PUT481 bytes and is separately selectable.

Changed controller/error-helper hashes invalidate old runtime-bound approvals
before transport. There is no migration, failed-state reset, replacement stage,
new create, adoption or repeated PUT. Existing hardcoded same-draft ownership,
PID/file checks, action ceilings, durable attempt counters, deadlines, ordinary
environment routing, TLS and no-redirect/no-retry rules remain in force.

## Closed transient error evidence

For a complete bounded nonbinary JSON object, shared transport first checks raw
and decoded credential echoes. Only a credential-free object can add the fixed
validation-error projection to the existing response receipt before status or
identity rejection. Thus HTTP400 and HTTP200/201 bodies can retain safe error
field evidence when the action subsequently fails. No response message, unknown
field path, arbitrary key, value, URL, header or parsed body is retained by this
projection. Known exact metadata/access/files field names become booleans;
container/type/count/field-shape flags and an unknown-field-present boolean are
the only other outputs. Nested unknown paths stay unknown. Container/field shape
does not validate error-message contents and grants no action authority.

Credential echo, malformed/truncated/binary bodies, redirects, uncertainty and
contract failure continue to stop without followup. Durable attempts remain spent.
Canonical readback diagnostics now compare subjects while retaining closed legacy
keyword presence/type/match flags for forensic comparison; that pure helper issues
no GET. A future same-draft recovery design must preserve failed ledgers and bind
the new runtime, retained identity/current beforeimage, actual body, safe response
diagnostics and explicit remaining authority. This document does not supply it.

## Runnable offline verification

From a checkout of the frozen PR head with the existing dependencies installed,
these commands use fictional inputs only. `env -i` clears environment credentials;
the guard installs dummy tokens and blocks Requests/socket/DNS transport while
running the full test suite:

```bash
env -i PATH="$PATH" python docs/readiness/2026-10-03/guarded_remaining_source_qa.py test
python -m scripts.modern_request_body_diagnostics
python -m scripts.modern_request_body_diagnostics --historical-source-body
```

The capture replaces `Session.send` locally and proves zero adapter calls; its
default clears the environment and netrc route. Do not add the private-token flag,
execute either controller, prepare/reset a private stage or request a live read
under this handoff. [Validation](modern_subjects_correction_validation.json)
records404 guarded tests,44 focused tests, seven independently repeated new
contracts and Ruff. The actual shared controller preparation path is tested for
both regular POST and owned PUT, with no adapter or provider dispatch.
The [final independent review](modern_subjects_correction_independent_review.json)
binds the frozen implementation/handoff checkpoint; its receipt-only addition
changes no runtime, payload, action bound or instruction.

## Next defensible source cohort, selection only

Current integrated counts remain **3596 supported /604 held /six malformed**.
The [next-cohort selection](remaining604_next_cohort_selection.json) binds the
largest currently independently source-cleared coherent set:41 resource-condition
records plus FGDC-4060's in-document disclaimer,42 total. Every selected source
is still held with a matching hash in the integrated ledger. This PR does not
integrate a profile or promote any source. The existing proposal/review hashes and
exact membership are retained in that selection receipt.

The42 require a subsequent bounded implementation, actual delta, preservation
contracts and review after this PR integrates. Literal conditions remain unresolved,
restricted access and blank licenses remain, and no expanded attestation or release
is inferred. The31 exact exceptions and456 alias identities remain held. A future
passing42 delta would yield3638/562/6; those are conditional counts only.
