# Registration cohort: whole-corpus verification (unpushed)

Frozen implementation `74daa5ad530715c94e301935b9dc5f68b9aee7bf` passed
196 offline tests (13 new regressions), with zero network attempts. Independent
source/code review found no remaining blocker after auditing all 122 exact
source/abstract/constraint bindings, human and agent approval rechecks, conflict
handling, restrictive rehosting conditions and unchanged metadata. This is local
review, not a GitHub automated verdict or live release approval.

Failing-first evidence includes a missing-feature test and the actual existing
122-held baseline; FGDC-3682 was held solely for source access. Bounded ten-source
assessment produces three supported/seven held. Full cohort assessment produces
78 supported and 44 held: 23 ambiguous creators and 21 empty creators. No creator,
date, rights or source bytes are changed to obtain those results.

The integration owner classified all 4,206 originals using the existing
restoration/Contact Source/Exxon evidence plus the optional exact registration
profile. Fresh and resumed reports are byte-identical:

| Source result | Frozen PR8 | Local registration branch |
|---|---:|---:|
| Supported preparations | 1,328 | 1,406 |
| Held | 2,872 | 2,794 |
| Malformed | 6 | 6 |

Only 78 audited cohort IDs change status, from held to supported. Every other
source status is unchanged. Technical totals remain 4,131 passing / 63 held / 12 not
constructed; all 228 exact-copy groups / 456 members remain held. All 4,206 original
hashes and 4,200 prepared XML copies are unchanged. Complete raw metadata objects
for all 4,194 constructed payloads are identical to the frozen baseline, including
creators, dates, attribution, access, licenses and source constraints. Only the
explicit policy/evidence interpretation changes for the selected cohort.

[Machine receipt](registration_whole_corpus_validation.json) records the exact
assessment time, report hashes, changed source IDs and all script hashes.
Documentation commits after the frozen implementation do not alter tested code.
Source support remains distinct from authenticated readback, duplicate evidence,
record QA and exact release selection. Remote verification and publication
approvals remain zero. No new batch was pushed and no provider write occurred.

Independent receipt/output review subsequently rechecked all 45 script hashes,
all original and copy hashes, and every complete metadata object. It confirmed
the exact 78 changed IDs and unchanged remaining statuses with zero mismatches.
