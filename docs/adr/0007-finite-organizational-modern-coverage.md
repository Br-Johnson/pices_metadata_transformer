# Finite organizational modern coverage

Date: 2026-10-05. This extends the reviewed mapping from 19 to 105 singleton
targets, adding 86 explicitly named source/hash bindings. The complete supported
population remains 3,933 targets; 3,828 are outside this modern path. These are
code and offline evidence counts, not uploads or production release approvals.

## Selection and preserved meaning

The pinned citation426 profile has 106 members whose complete creator objects
already contain exactly `name` and `type: Organization`. Intersecting those
members with the frozen publication plan yields 105 supported singletons and one
hold, FGDC-710. No selected source has a protected or known production identity.
No organizational type is inferred from names, keywords or institutional wording.

The [finite manifest](../readiness/2026-10-05/modern_organizational_extension86.json)
binds exactly 86 additions to the existing citation cohort, original XML digest
and publication-plan digest. The [census](../readiness/2026-10-05/modern_organizational_coverage_census.json)
retains all 106 candidate bindings, raw constraints, primary/supplemental creator
evidence and the held case. The largest added group is USDA/Alaska DNR with 31;
the remainder includes NOAA/NMFS/AFSC/RACE 9, China First Institute 7, Northwest
Fisheries Science Center 4, Auke Bay 3 and 32 individual profiles. The extension
uses 37 existing profiles; the original 19 form the 38th eligible profile.

All 105 reuse the existing one-XML payload contract: literal creator order,
institutional hierarchy and address text, approved source metadata date,
restricted files and no new license. Complete assembled legacy metadata,
including bounded citation notes and supplemental context, remains in the
escaped preservation block. The original XML is uploaded byte for byte.
`publisher: Zenodo` continues to identify the repository hosting the artifact.

The 228 paired targets require a distinct two-file identity/QA/execution contract.
The five protected published imports require correction/version handling that
preserves existing IDs and DOIs. Those dependencies are not supplied by this
finite single-file extension. Untyped creators and new source/licensing decisions
remain outside the selected scope.

## Policy version and compatibility

The original 19 keep precisely `schema_version:1` and
`policy:modern-xml-ncdc19-v1`, without depending on the new manifest. Their wire
bytes and all nonruntime preparation fields are unchanged against retained
beforeimages captured with the actual PR35 runtime before editing.

The additional 86 use `schema_version:2`,
`policy:modern-xml-organizations86-v1`, the exact `mapping_manifest_sha256` and
their `creator_cohort`. Missing/changed manifests, mismatched source hashes or
cohorts, and source-policy substitutions hold. Modern QA resolves the exact
source policy instead of accepting any global policy label. This is an additive
preparation-evidence version; provider payload and journal schemas do not change.

Historical compatibility is finite: the original 19 may bridge verified creation
evidence from PR34 runtime
`0f0a537dde0d6970ce6c64aad1169cf9ebb290cbcf7b527ab3917ace1393fff5`
or PR35 runtime
`30092eff4631d7543f24b8ecabf0a85c294da8fcc4c308ecc97224e38b58b270`.
Every nonruntime field must equal the freshly assessed preparation. New 86
preparations accept only the current runtime; they cannot claim to have executed
under either earlier implementation. Old grants are checked at their original
request times and never revived.

An already-started capture or publication has its original bridge/grant binding
and permanent intent. Changing runtime does not migrate that stage, refresh its
budget, replace its snapshot or authorize another grant. Preserve its frozen
runtime and all evidence; recovery still requires its original unexpired grant
and remaining allowance. There is no reset or state-root relocation mechanism.

## Execution and remaining gates

The [draft interface](0005-finite-modern-singleton-drafts.md) and
[publication interface](0006-finite-modern-singleton-publication.md) are unchanged.
One exact source is processed per invocation. All grant schemas, original state
paths, cross-lane record/parent/DOI collision checks, permanent intents, request
budgets, redaction, redirect refusal and no-replay behavior remain in force.
Publication still needs fresh independently reviewed owner/source/history proof,
saved readback, record QA, independent program review and a separate human release.

For an already prepared and assessed selected source, `prepare` remains offline:

```sh
python -B -m scripts.modern_singleton_executor prepare \
  --json-file /approved/prepared/FGDC-696.json \
  --output-dir /canonical/original-production-output
```

The output/state root must be the original one whose full history was reviewed.
Use the final merged commit from the PR timeline, retain the printed preparation
packet, and follow ADR 0005/0006 for the exact later stages. Only parent may
dispatch provider execution to the sole assigned Mac executor. No grant, token,
provider call or publication is supplied by this increment. The Mac canary is
still unexecuted pending token entry.

## Evidence and reproduction

The [measurement receipt](../readiness/2026-10-05/modern_organizational_coverage_validation.json)
records actual 105 preparations, exact repeats, XML/payload size bounds, complete
metadata preservation, old 19 compatibility and all 4,206 original hashes before
and after. The [guarded helper](../readiness/2026-10-05/measure_modern_organizational_coverage.py)
requires the retained exact pre-edit baseline and only writes to a fresh `/tmp`
directory. It cannot rebuild historical execution by relabeling a current fixture.

The retained local comparison can be reproduced in the same integration checkout
with a new output directory:

```sh
python -B docs/readiness/2026-10-05/measure_modern_organizational_coverage.py \
  --repo /workspace/pices-modern-organizational-coverage-20261005 \
  --output /tmp/pices-modern-105-new-comparison \
  --baseline /tmp/pices-modern-old19-baseline-20261005-v2/baseline.json
```

That baseline SHA-256 is
`7e1d0ccb825c5114df5abc1e9ae0f7a83ddeda501ef2e0abc56ac70ae3e36940`.
Its original prepared files must remain at their recorded paths; the comparison
reads them without migration or writes. The committed receipt retains each of
the 19 original/current bindings and matching wire/nonruntime digests. The
portable tests below independently construct and check all 105 real sources.

```sh
python -B ci/run_offline_tests.py \
  tests.test_modern_organizational_coverage tests.test_modern_singleton \
  tests.test_modern_singleton_executor tests.test_modern_publication \
  tests.test_modern_publication_qa
```

The new representative test performs the exact four draft writes, readback/retry,
capture, QA/release, publish/inclusion and unchanged retry through fake transport.
It also retains uncertain-create effects and rejects historical-runtime forgery.
Other tests preserve the original transport, collision and recovery boundaries.
Actual current-head CI and substantive independent review remain merge evidence;
neither these tests nor source support assert deployed compatibility or live success.

The [focused result](../readiness/2026-10-05/modern_organizational_focused_checks.json)
records 115 passing guarded contracts, zero failures/errors or unexpected I/O,
and unchanged source/test bindings. Full current-head CI and the final review
and merge receipt are retained in the PR timeline.
