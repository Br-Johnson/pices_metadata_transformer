# Finite PICES26 modern mapping

Measured coverage is **3,171** supported singleton targets, with **762** supported
targets outside the mapper (534 singletons + 228 pairs). The
[aggregate receipt](modern_pices26_validation.json), SHA256
`effab194b3621fc867542ab366b57d7f1091400b4ba6ebfabf6f0270955bc208`,
verifies all 26 new mappings twice, all 3,145 prior wires and nonruntime evidence,
18,488 retained evidence files, 11 referenced public profiles and all 4,206 XML
originals. Source/test binding is
`866f2324c3280b5d512a186bd763c792a6e15dd0440f09c605fd46239d8bb632`.
All four guards report zero unexpected events.

The exact 26 `pices_literal_26` singletons receive a separately reviewed modern
organizational representation of their existing primary citation,
`North Pacific Marine Science Organization (PICES)`. Complete legacy creator
objects remain name-only. Original XML, editors/compilers in titles, dates, notes,
access conditions and blank license remain intact. This finite source decision
establishes neither XML authorship nor community identity or release authority.
DFO Staff70, SOA, other untyped credits, protected records and paired targets gain
no new mapping. Source support and all 39 held/six malformed targets are unchanged.

The prior citation profile preserved name-only objects and did not approve a
modern representation. The new [source review](modern_pices26_source_review.json)
and independent review retain that distinction; no historical profile is rewritten.

| Input | SHA256 |
| --- | --- |
| [26-member mapping](modern_pices_singletons26.json) | `15d5f40fe829919a0ff9d9b81bcfc6205b2cd4042a3891e4dc9e4b3595204670` |
| [Source review](modern_pices26_source_review.json) | `7e4b0ea88d239855852383878f9bfcdcb4c4ba232c451ddfcae6910e7682a711` |
| Unchanged citation426 | `15c654dc714849327b827363071a1da3ad7c3fa20c2c95a990d7868e75e96bd2` |
| Unchanged source plan | `39d2894d518fa5a10d87cc784ce40064e6757529f23219eea153f25805f506ad` |
| [Measurement helper](measure_modern_pices26_coverage.py) | `2ff6859c7b024f0eb7bcf2b10d6239dfe54a0795b337ba50a9af87fcb9211ec4` |

New evidence uses schema5 and policy `modern-xml-pices26-v1`. Runtime SHA256 is
`a23fa32cd7312616100a0d34e9b328234a98cd3cd173821d55d494f326ac85d4`.
The old four policies return before reading the new manifest. Verified PR40 draft
history remains compatible only for those four policies, including validated
completed-on-content transcripts. Every nonruntime field must still match;
new PICES26 records cannot backdate their runtime. Started capture/publication
operations retain original bindings and spent budgets.

## Offline reproduction

Run indices 0 through 3 once, each with a distinct fresh temporary output:

```sh
python -B docs/readiness/2026-10-06/measure_modern_pices26_coverage.py \
  --repo /workspace/pices-modern-residual-20261006 \
  --output /tmp/pices-pices26-reproduce-shard0 --shard-index 0
```

The helper reuses the pinned Exxon helper and retained PR37 inputs, then verifies
PR38 receipts under `/tmp/pices-exxon-shard{0..3}-v1`. Preserve every recorded
baseline/profile path and digest. Missing inputs require evidence recovery, not
new classification as a substitute baseline. Each shard classifies seven or six
new sources and prepares them twice, then prepares 787 or 786 old inputs once at
their original paths. All four receipts are required for aggregate coverage.

Checks bind all 4,206 originals, complete raw and normalized legacy metadata
separately, exact prior wire/nonruntime evidence, retained files, runtime and
source/test bindings before/after. The environment is cleared, credentials are
dummy-only and the offline guard permits writes only to fresh temporary output.
Retain each `coverage.json`, `wire_artifact_manifest.json`,
`retained_file_manifest.json` and its referenced artifacts.

```sh
python -B ci/run_offline_tests.py tests.test_modern_pices_coverage \
  tests.test_modern_singleton tests.test_modern_publication \
  tests.test_modern_publication_qa
```

The first aggregate receipt retained a stale hash for the now-289-member
creator426 residual list. Independent review caught it; the corrected aggregate
recomputes every residual membership hash. The first receipt is preserved at
`/tmp/pices-pices26-aggregate-v1-stale-membership.json`, SHA256
`f5fc0125f6379a1407ad1384cae77e0fa6f3e2e69fbc2067238121b85d9222ca`.
No mapper or measurement was rerun for that receipt-only correction.

**104 affected guarded tests pass** in 627.188 seconds, with unchanged source
bindings and zero unexpected guard events. The [focused receipt](modern_pices26_focused_checks.json)
retains the actual result and earlier interrupted/failed attempts. Current-head
GitHub CI, independent Codex review and the merge result are recorded in the PR
timeline; local receipts identify the base checkout plus measured changes and
do not claim to be a CI run of the later published commit.

## Separate execution requirements

The existing offline entrypoint remains:

```sh
python -B -m scripts.modern_singleton_executor prepare \
  --json-file /approved/prepared/FGDC-1319.json \
  --output-dir /canonical/production-output
```

These denote real parent-reviewed inputs, not supplied grants or permission to
replace a state root. The sole Mac executor retains provider actions. Production
identity/history reconciliation, bounded draft grant, canary compatibility,
remote readback, QA, human release and accepted PICES inclusion remain separate.
Brett's destination answer is pending. Repository merge grants no provider action.

The parallel [FGDC-141 assessment](fgdc141_no_match_route.md) finds no supported
candidate within the retained 20-record/24-file owner capture. It preserves the
October 4 scope, protected mappings and unknown history, and invents neither an
existing draft nor an old journal. It does not issue a create allowance.
