# Cloud integration verification

The integration owner resumed exact public PR8 base `35b01a2`, verified both
checkpoint trees, and independently checked all 41 transferred file hashes.
The archive SHA-256 was
`93b46e86fce926893de3da599420fd94f600f5781b24f2b06096f5fcd06816dc`
(639,383 bytes, 43 safe members). No original XML or credential was transferred
as new source authority; all 4,206 originals already matched the public base.

## Changes and independent review

- Original source precedence rejects divergent copies before client operations;
  upload selection filters pending files before limit and resets invocation
  counters. Independent bounded review cleared `99a769d`.
- Correction compiler rejects invalid schema, duplicate/missing/stale members
  and unreviewed overlapping field values. Explicit supersession preserves all
  contributing reviews. Independent compiler review cleared final `94a779d`.
- Independent census enumerated all source hashes and 213 creator-hold patterns,
  confirmed the exact 821-member citation cohort and its disjoint residuals.
- Pinned opt-in citation interpretation checks exact source membership/wording
  and complete creator objects. Independent review identified and verified the
  repair of a missing human-QA reference recheck; final `724a939` was cleared.
  Old human/agent approvals cannot substitute stale interpretation bytes.
- The explicit migrated compiler batch produces the same 821 source hashes and
  full creator objects as every actual prepared cohort payload. Compilation is
  not a claim that raw legacy outputs pass license validation or that a record
  is publication-approved.

## Combined validation

The integrated code at `b1cbbca` passes **183 tests**, zero failures/errors. A
process-inherited socket/subprocess guard permits only local Git revision reads
and the guarded compiler CLI needed by its temporary-fixture tests. Zero network
or disallowed subprocess events occurred. The first harness attempt incorrectly
blocked those compiler subprocess tests; correcting only the harness produced
the passing run. No implementation change was hidden in that rerun.

Fresh and resumed source-only classification at
`2026-10-02T21:00:34.514318+00:00` are byte-identical:

| Result | Count |
|---|---:|
| Supported preparations | 1,328 |
| Held sources | 2,872 |
| Malformed originals | 6 |
| Technically passing payloads | 4,131 |
| Technical holds | 63 |
| Not constructed | 12 |
| Exact-copy groups / members | 228 / 456 |
| Remote verification / publication approvals | 0 / 0 |

All 4,206 original SHA-256 values and 4,200 prepared XML copies were checked
unchanged. The 821-member cohort retains 406 alias holds and FGDC-1994's access
hold, while 414 creator-only cases become supported. Restricted attachments,
blank licenses, source citation attribution and XML-authorship caveats remain.

[Machine receipt](cloud_integration_validation.json) pins every Python script
hash, counts, timestamp and final classification digest. Subsequent documentation
updates do not change the tested scripts or source data. Tests are discoverable
with `python -m unittest discover -s tests -v`; full classification uses the
runbook's explicit authority, access and creator interpretation manifests and
the same assessment timestamp for a resumed run.

Local independent reviews establish bounded code/source checks, not an automated
GitHub verdict. The actual final-head Codex review is tracked in PR8's timeline.
No merge, Zenodo/AquaDocs write, credential creation, community submission or
production release is included. Remaining narrower source groups, alias identity
adjudication, FGDC-1994 access scope and eventual authenticated compatibility
remain separate work.
