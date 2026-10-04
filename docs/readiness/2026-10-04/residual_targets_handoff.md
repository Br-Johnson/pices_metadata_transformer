# Twenty-five finite target corrections — 2026-10-04

Base: merged PR29, `9bac0ace68c83a2082168f022315c05a1192210b`.
This correction supports 24 previously held identical-pair targets and singleton
FGDC-2664. It preserves every original XML and all existing provider guards.

The accepted profiles are [resource655](finite_source_resource_access_655.json),
[creator426](source_citation_credits_426.json) and [title42](source_display_titles_42.json).
All prior 607 resource members, 122 resource contexts, 423 creator members and
36 title members remain exact. Earlier accepted profile pins remain valid.

- Resource655 adds 48 exact originals: 21 ADF&G report-series pairs, one TINRO ice
  pair, one VNIRO observation pair and one Food Habits pair. Literal resource
  conditions remain intact; source review adds no licence or blanket exemption.
- Three pairs receive complete display titles: 2894/3122 (No.110), 2960/3188
  (No.116), and 2872/3100 (No.106, both Volume I and Volume II). Complete original
  citations, dates, bylines and pagination remain in preservation notes.
- Pair2837/3065 retains ordered Pat Livingston and Douglas Smith credits with
  their explicit editor/compiler roles. Institutional hierarchy stays preserved.
- FGDC-2664 receives the literal credit `Sapozhnikov, V. V.` from a later
  publisher bibliography and distinctive subject match. The review does not
  claim an inspected 1993 byline or equivalence of original and translated editions.

The four editorial pairs also had independent access gaps. Their finite access
supplement and separate access-only/editorial-only withdrawal tests cover both
conditions. No generic fallback, author expansion, source-date repair or right is
introduced. Both members of every pair retain their identities and original files.

## Actual measured result

The [guarded receipt](residual_targets_validation.json) records a ten-source smoke
and a 52-source batch: all49 candidate originals plus supported pair2953/3181 and
held control288. Before/after/unchanged retry/complete withdrawal use one output
per batch with saved actual phase snapshots. Six new contracts also exercise
independent interpretation withdrawal, full-root/source/evidence tampering and
the mandatory class-operation guard.

| View | Supported | Held | Malformed | Total |
| --- | ---: | ---: | ---: | ---: |
| Original source files | 3,705 | 495 | 6 | 4,206 |
| Unique record targets | 3,933 | 39 | 6 | 3,978 |
| Paired class targets | 228 | 0 | 0 | 228 |

All228 class targets remain upload-ineligible. The 495 original-file holds include
all456 legacy alias identities plus39 nonalias sources. Source-file and target
counts are separate views, not additive upload counts.

The [source ledger](residual_targets_integrated_source_status.json) changes only
FGDC-2664 from the frozen predecessor. All4205 other status objects remain exact;
all4206 original hashes pass before/after comparison. The [target projection](residual_targets_record_target_projection.json)
freshly assesses/rebuilds only24 classes and updates one singleton. Its204 other
class rows,3750 singleton identities and source-to-target index remain preserved;
3749 singleton rows are unchanged. The projection's `class_assessment_scopes`
distinguishes fresh selected artifacts from the historical204, whose payload pins
resolve through the pinned prior index and original PR28 measurement. Those204
payloads are not copied or rebuilt in this output. Historical provenance remains
explicit rather than being presented as a new universal class assessment.

The [independent output audit](residual_targets_independent_output_review.json)
recomputed saved metadata, submission and artifact hashes and verified770 file
bindings without rerunning classification. The [focused receipt](residual_targets_focused_checks.json)
records24 passing guarded tests with zero unexpected I/O. The [runtime/profile
review](residual_targets_runtime_profile_review.json) and [helper review closure](residual_targets_measurement_review.json)
are clear; the initial helper findings remain preserved in a separate receipt.
The actual current-head GitHub CI and final Codex review remain merge gates.

## Reproduce offline

From the repository root with public requirements installed, choose a fresh output:

```bash
python -B docs/readiness/2026-10-04/validate_residual_target_corrections.py \
  --repo . \
  --output /tmp/pices-residual-targets-reproduction \
  --reviewed-at 2026-10-04T20:31:15Z
```

The helper installs the guard before project imports, clears the environment and
uses dummy values. It records4387 actual repository input hashes including all
4206 originals, separately from CI runtime bindings. Saved receipt paths and
checkout IDs describe the author's actual run; another checkout has its own
bindings. The committed receipt is authoritative for its own inputs and timestamp.
Bulk phase payloads are reproducible output rather than new original-source data.

For focused regression:

```bash
python -B ci/run_offline_tests.py \
  tests.test_residual_target_corrections tests.test_sensitive_resource11 \
  tests.test_residual_title233 tests.test_derived_creator_extension \
  tests.test_content_class_targets
```

## Remaining evidence and provider boundary

The [45-case packet](residual_targets_remaining45.json) and [grouped questions](residual_targets_remaining45.md)
preserve ten creator gaps,19 incorporated-policy gaps, four other resource-scope
gaps, six metadata-date gaps and six malformed originals. Related papers, current
catalogues and repository history narrow the gaps without inventing a missing
creator/date or selecting one component from a malformed original. Further
source-owner or archival evidence may resolve these cases; global research
exhaustion is not claimed. Rehosting and identical-pair authority are already held.

The [parent-relayed production summary](production_owner_inventory_parent_summary.json)
reports a separate authorized reader's completed42-GET current-owner inventory.
This integration lane made no provider requests and has not independently audited
the underlying response ledger. Zero exact candidates among20 owned concepts
provides current-owner coverage, not deleted/tombstone historical absence. Two
title hints remain separate. Five existing source/record/DOI associations and the
poster/programme exclusions remain unchanged. Parent and the sole provider owner
retain the full capture and decide subsequent bounded stages. No class execution,
identity adoption, new action grant or production release is enabled here.

Source proposal/review files are copied byte-for-byte into this directory with
the `residual_pair*`, `residual_creator*`, `residual_gts*`, `residual_policy*` and
`residual_date*` names. Historical `/tmp` paths inside those receipts identify the
reviewer's original artifacts; accepted profiles and the remaining packet pin the
durable repository copies. Earlier failed receipts and evidence remain intact.
