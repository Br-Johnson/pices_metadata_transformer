# Finite institutional91 modern mapping

Measured coverage is **3,262 supported singleton targets**, leaving **671**
supported targets outside the mapper: 443 singletons and 228 pairs. The
[aggregate receipt](modern_institution91_validation.json), SHA256
`c170ee5d9d7da6190ca2a2b97062bb1d87cad565e694959922f520d6367cf730`,
verifies all 91 additions twice and all 3,171 retained wire/nonruntime comparisons
once. All 21,779 retained public files, 14 exact public profile paths and 4,206
original XML hashes match. Every measurement guard reports zero unexpected I/O.
The measured checkout is `/workspace/pices-modern-next-citations-20261006` at
`95b93dd69aee0127536530d22537e2453448e291`; later changes only strengthen/fix tests
and retain these results. Actual roots are `/tmp/pices-institution91-shard{0..3}-v1`.
The aggregation script remains `/tmp/pices-institution91-aggregate.py`, with its
exact digest recorded in the aggregate. It only verifies saved artifacts.

The finite manifest selects **91 exact sources across nine institutional citation
groups** for modern organizational representation. Legacy creators remain
name-only, with their complete literal names unchanged. The selection consists
of 60 Fisheries/Oceans Canada institutional-unit credits, 29 Japan Coast Guard,
one Meteorologiske Institut and one CSIRO credit. It adds no authorship,
collectors, affiliations, identifiers, dates, rights or licences.

The [source assessment](modern_institution91_source_review.json),
[all-source bindings](modern_institution91_source_bindings.json) and
[independent semantic review](modern_institution91_independent_review.json)
cover exact membership, original XML, retained payloads, full creator objects and
citation context. The [mapping](modern_institution_singletons91.json) additionally
binds parsed origin elements, including attributes and children, rather than only
display strings. Their initial representation mismatch was caught in review and
corrected before the coverage run; the interrupted focused run remains at
`/tmp/pices-institution91-focused-v1.log` (exit 130). A later test-only QA clock
mismatch is retained in `/tmp/pices-institution91-focused-v3.log`: its positive control rejected a future-dated
snapshot. The corrected test uses the publication fixture time. The measurement
checkout remains frozen, so these later test-only changes do not alter its
runtime or payloads.

The 79 direct interpretation holds remain: 69 typed compounds, seven Data Analyst
role credits, one ambiguous Frontier research-system/program and two personal
compounds. All 289 creator426 residuals, DFO Staff70, five protected identities
and 228 paired targets remain outside this increment. Source support remains
3,933 targets, with 39 held and six malformed. The original 4,206 XML files and
historical metadata profiles are immutable.

| Input | SHA256 |
| --- | --- |
| 91-member mapping | `19dd282e701bb115e256c90cac0ebaba0cfa1b49baf748dc4bf55106cc22dfd1` |
| Source assessment | `8cc6bd3a75de1e63b28b18f325a04d17333a356647804221d256a25d91f5b662` |
| All-source binding review | `0cdf17201243f9bdaeaca90c4ae1f46b573d0be9429359942a8b7eb89a73d633` |
| Independent semantic review | `5904019eb6edf096bf6a27798c9f001d154604fcf2a18fa62d75cbe4e1602a44` |
| Guarded measurement helper | `4c9163229ade333a2dc9a3bff1ba5725c033a302c0c343cb170459393d40b010` |

New preparation evidence uses schema 6 and policy
`modern-xml-institutions91-v1`; its creator authority is the pinned finite
mapping. No citation426 interpretation is grafted onto these direct credits.
Runtime SHA256 is
`d09495acd462e7a51c3c1344265758ed8482256e9d901c05b64711734316ef2d`.
The previous five policies return before loading this manifest. Verified PR41
preparations may bridge only for those policies, including validated completed
content uploads, when every nonruntime field and original attempt still matches.
New institutional preparations cannot claim the PR41 runtime. Started captures,
publication operations, canonical paths and spent budgets never migrate.

## Offline reproduction

Run each index 0 through 3 once, using a distinct fresh output directory:

```sh
python -B docs/readiness/2026-10-06/measure_modern_institution91_coverage.py \
  --repo /workspace/pices-modern-next-citations-20261006 \
  --output /tmp/pices-institution91-reproduce-shard0 --shard-index 0
```

The helper verifies the retained PR41 receipts under
`/tmp/pices-pices26-shard{0..3}-v1` and their earlier baseline chain. Preserve every
recorded input, profile, preparation and wire path with its exact digest. Missing
baselines require evidence recovery. Each shard classifies only its 23 or 22 new
sources, prepares each twice, then prepares 793 or 792 old inputs once at their
original paths. All four successful receipts are required to claim coverage.
Complete raw input metadata and normalized legacy preservation blocks are bound
separately. The guard clears the environment, supplies dummy credentials and
allows writes only to fresh temporary output. Retain each coverage, artifact
manifest and referenced file. No provider request or executable grant is created.

```sh
python -B ci/run_offline_tests.py tests.test_modern_institution_coverage \
  tests.test_modern_pices_coverage tests.test_modern_publication \
  tests.test_modern_publication_qa
```

## Focused validation and staged bindings

The [focused receipt](modern_institution91_focused_checks.json), SHA256
`0d5855973941ef5a57feb7ad5ab71584d9cb09e709b07ed73b3235f9a1336384`, preserves every run.
The corrected runtime passes **106 focused contracts** in 582.789 seconds.
After strengthening direct-mapper refusal assertions and adding consistently
rebound QA substitutions, **10 affected contracts pass** in 67.296 seconds on the
final test tree. Its positive control passes before altered policy, schema,
cohort, manifest and creator-authority evidence are rejected.

The 106-test source binding is
`6f9998d0da71cebde30990c445ec7f89287e4226bde1bcf5133c6a665c038d7a`.
The measurement/source-test binding at frozen local `95b93dd` is
`b53a1ef7279b377e994f5f78526799c623c0c13da9aff3adf6d39f3be755c2ef`.
The final source-test binding at local `8d6e00b` is
`6ae0735b354c59139a237f63e408e4fe6cad5c6376e4efdd6375f7e73bc96494`.
The later change is test-only; all three use the identical runtime. No failed
run is reported as passing. Actual current-head CI, independent Codex review
and merge receipts belong to the PR timeline; local receipts do not claim a
run of the later published commit.

## Separate provider authority and inventory dates

Parent reports that the October 6 production inventory independently repeated
the October 4 evidence byte-for-byte. The [retained raw comparison](fgdc141_owned_inventory_no_match.json)
remains explicitly an October 4 capture; this handoff records the separately
dated parent report without fabricating an October 6 capture timestamp or
manifest. No further inventory request follows from this code work.

The sole Mac executor retains provider actions. Production destination
confirmation, exact source/identity/history reconciliation, bounded draft grant,
canary compatibility, readback, record QA, independent review, human release and
accepted PICES inclusion remain separate. Repository merge authority supplies
none of these provider grants. Existing records/DOIs, unrelated exclusions,
original intents and journals remain protected.
