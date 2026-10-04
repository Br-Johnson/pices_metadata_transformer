# Five residual resource-condition corrections — proposed integration

This isolated batch measured five held→supported source records against fetched
main `ecfba4ed3496c0a8d400eb2ace46800f0c166708`. Recounting the committed 4,206-row
source ledger gives **3,638 supported / 562 held / 6 malformed**. Applying only
the measured five-row delta gives **3,643 supported / 557 held / 6 malformed**,
**proposed until the sole integration owner integrates it**. This is bounded
fresh validation plus frozen-ledger accounting, not a fresh full-corpus audit or
provider verification.

| Exact source | Original XML SHA-256 | Evidence and preserved condition |
| --- | --- | --- |
| FGDC-1257 | `343d0e1b6c7d96a3899dfe5173b84ce12f8a5174d77b7fbdf65a897a00416b42` | Radio publication; acknowledgment of data-source publication remains required. |
| FGDC-1258 | `fb72564a17bf0535a1cfeaab04dd92d674dcb164ce4d608cdd17c19a5b1bfac9` | Radio publication; same explicit acknowledgment condition. |
| FGDC-1262 | `3b9761159b7036598d96e2fcee9651c8f1c32428840106c4edb5cf53483d93cc` | Radio publication; same explicit acknowledgment condition. |
| FGDC-1273 | `02957d0e04f214f4f02b72487d71923b613c01d81133967b17c2381626b1309a` | Radio publication; same explicit acknowledgment condition. |
| FGDC-4064 | `1b3891fe9136b5a95182c3e0b5a06929a7524870ba09479fd59c5148da26806c` | Abstract explicitly says password access is required for the most recent data. |

The original eight-source creator-repair batch already supplies the corrected
credits. This batch changes no creator. The new finite policy reference interprets
the five exact resource conditions using complete XML context; its status is
**REVIEWER_RECONCILED**. Rehosting authority remains separately required and
**USER_ATTESTED**, without independent agreement verification. No acknowledgment
satisfaction, password entitlement, license, underlying-data right, XML authorship
or new human answer is asserted.

FGDC-4063, SHA-256
`d4316e685146a6232b5491273da2132f18f4c7397770634eb4d11fd00dc8a076`,
stays held. Its project description does not name the object of “May require
password access.” Needed evidence: identify whether that instruction and Contact
Source cover project data, descriptive metadata, or another resource in this exact
record. FGDC-4064's explicit recent-data statement cannot answer for FGDC-4063.

## Evidence, implementation and measured limits

- [Independent source review](residual_source5_independent_source_review.json):
  `ce1b8de4fb27178fd56df51a6bce9cd5bc4b970d85693fb11dd31c904cc6976c`.
  Exact five-member digest:
  `3466770764a8718a870a7e127361be5f564569a7d4d08dd584297be826d581d5`.
- [Additive 561-member profile](residual_source_access_561.json):
  `b0a0f90f8d61b1908ea1a291284a04d8047186e63b2dc9427181a39af6a292f7`.
  All 556 earlier member and context objects and the earlier42 review are retained
  verbatim. A separate five-member review preserves their own assessment time.
- [Measured validation](residual_source5_validation.json) records six-source
  before/after, identical resume and withdrawal. All five complete raw metadata
  objects and all six original/copied XML byte sequences are unchanged. Only the
  five exact artifact-policy references are added. FGDC-4063's entire payload is
  unchanged. Restricted XML, blank licenses, all dates/credits/notes and literal
  constraints stay exact.
- The source ledger remains immutable at SHA-256
  `e9f248c1730aa59f4d89f9ddf66aedf05dd172c73dab190709ea3e8c6683b061`.
  Every unselected status object stays exact. Proposed status-row digest:
  `a156af48d7efcf918b17de8d072f32193fa7e3232b2bb37a8235ec8f2c87ba63`.
  All 456 aliases, 31 exact exceptions, six date holds, one title hold, 25
  unresolved creators and 37 deferred resource cases remain held. The prior six
  creator-repaired/access-held cases become five supported and one held.
- Validation and contract runs block provider transport and use dummy credentials.
  Independent review verifies all 4,206 original hashes against the frozen ledger;
  the guarded suite verifies unchanged runtime/test/contract bindings during testing.
  [All 461 guarded tests pass](residual_source5_tests.json) in 222.497 seconds,
  with unchanged bindings and zero test guard violations. This includes 11 new
  contracts covering repeat/withdrawal, complete-source and cached-metadata
  tampering, original evidence, authority, time, and agent/both human QA routes.
  [Independent implementation review](residual_source5_implementation_review.json)
  reproduced the bounded delta, cleared all original hashes and passed 30 tests
  across separate 29+1 runs. Ruff and whitespace checks pass. The first broad run
  was invalidated by concurrent test-file edits and is explicitly superseded by
  the frozen 461-test run; no source XML changed.

## Reconciliation and integration instructions

`AGENTS.md`, the active checklist, current runtime manifests, resource42 handoff,
alias review, remaining732 questions and physical-copy4 proposal were reconciled.
The mounted `/workspace/.agents` directory was empty; no local skill files were
present. Older frozen authorization text is retained; this delegation's explicit
no-main-push/no-merge/no-duplicate-PR limit governs this lane.

This batch excludes **FGDC740/815/851/879** (existing physical-copy proposals) and
**FGDC885/887** (the active sole integration owner's work). No source XML or earlier
manifest/receipt is rewritten. No provider request, publication, identity/DOI
change, credential access, new service or schedule occurred. Known non-PICES and
unrelated poster exclusions stay in the unchanged pipeline.

The owner can apply the isolated handoff-branch commit/patch to their integration checkout, then
select `docs/readiness/2026-10-04/residual_source_access_561.json` through the
existing `--dataset-access-interpretation-manifest` option. Other latest manifests
remain as in the runner below. Conservative defaults and old profiles remain
accepted. This patch does not activate the new profile globally.

If the owner's parallel batch extends the same resource profile, combine both
disjoint memberships and complete contexts in a newly pinned profile, preserve
both review blocks and original attestations, and measure the combined delta.
Do not replace an owner's newer manifest with this 561-member snapshot or add
their unmeasured promotions to these proposed counts. Runtime pin/review dispatch
and appended checklist text may need a small integration conflict resolution.

Reproduce from this checkout with installed requirements, using a new output path:

```sh
python -B docs/readiness/2026-10-04/validate_residual_source5.py \
  --output /tmp/pices-source5-new-verification
python -B ci/run_offline_tests.py tests.test_residual_source_access
python -B ci/run_offline_tests.py
```

The runner transforms six sources (a smoke smaller than the requested ten-record
maximum), then repeats and withdraws the profile. It derives the current/proposed
counts from actual ledger rows and measured statuses. Current aware time is used
unless `--reviewed-at` is supplied; payload/report hashes therefore depend on that
time and checkout paths. Source, profile, metadata and proposed status-row hashes
are explicit. No executor-local historical baseline directory is required.

## Useful remaining source work

The [independent25-creator audit](unresolved_creator25_review.json), SHA-256
`fad807ca69b5e7c4588d3fc89b5065fb8da5250e02b034d8caee390c34b8ced4`,
verified all 25 exact originals and found no defensible new attribution: one
address-only origin (10), four journal/venue origins (1206/1314/2664/2817), a
country-only atlas (2552), publication-direction chart text (2586), and 18 empty
NEAR-GOOS origins. Same-work bylines or explicit product-producer/XML-author
credits are needed; contacts and access hosts cannot supply them.

The existing 228-pair alias audit remains sufficient: XML equality provides no
verified provider crosswalk or owner-selected canonical identity. Keep all 456
source identities and existing IDs/DOIs until those facts are supplied.

The source review also records 12 preliminary, unimplemented resource candidates:
753, 779, 784, 832, 834, 836, 845, 853, 855, 861, 880 and 882. They require their
own complete source review and runtime validation; this batch gives them no
eligibility change. Sensitive, metadata-product and incomplete exceptions remain
held, as do the previously proposed physical-copy4 and owner-reserved pair.
