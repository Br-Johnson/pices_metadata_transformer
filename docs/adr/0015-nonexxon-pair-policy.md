# Second pinned pair policy: the 25 non-Exxon pairs

Date: 2026-10-22. Status: accepted for offline preparation; the v2 planning of these
pairs waits for Brett to merge their resource types. Extends
[ADR 0010](0010-finite-modern-content-class-preparation.md), whose preparation contract
applies unchanged, and feeds [ADR 0013](0013-bulk-draft-and-publication-route.md) and
[ADR 0014](0014-v2-wire-and-in-place-update.md), whose review, draft, release, publish
and journal rules apply unchanged.

## Context

The collection has 228 two-file pairs: two FGDC sources with byte-identical XML, published
as one record with both files. The 203 Exxon pairs were prepared under the one pinned pair
policy, `modern-xml-exxon-pairs203-v1`, and published through the bulk route (pairs-001).
The other 25 pairs, 50 sources, were reviewed on 2026-10-06 but never admitted to runtime:

| Review, archived under `docs/readiness/2026-10-06/next_source_review/` | What it settles |
|---|---|
| `pices-nonexxon25-pair-source-review.json` (SHA256 `455b5e01…`) | 24 pairs approved with one organizational creator each, in four groups: ADF&G Division of Commercial Fisheries (21 pairs, the Technical Data Report series), National Sun Yat-sen University (1), VNIRO (1), Far Eastern Hydrometeorlogical Institute / TINRO-Center (1). The Food Habits pair (FGDC-2837, FGDC-3065) is held for its personal name parts. |
| `pices-foodhabits-pair-literal-parts-supplement.json` (`ee723d4a…`) | Approves the exact two-person vector Pat Livingston, then Douglas Smith, and supersedes only that hold. It keeps the name-only legacy credits, the editor and compiler limits and the NMFS/NOAA context, and asserts no external person identity. |
| `pices-foodhabits-pair-current-source-bindings.json` (`b353004c…`) | Binds both originals, the current creator426 cohort and the plan target of that pair. |
| `pices-organizational-pairs24-manifest-design.json` | A design draft, marked `DRAFT_DESIGN_ONLY_NOT_RUNTIME_ADMISSION`. It is not a loader input. |

Brett approved the work on 2026-10-22: "take on the 25 non-Exxon pairs".

## Decision

### A second pinned manifest, derived from the reviews

`docs/readiness/2026-10-22/modern_nonexxon_pairs25.json` (kind
`modern-nonexxon-content-classes-v1`, policy `modern-xml-nonexxon-pairs25-v1`) lists the 25
targets as their representation rows and five groups, each with the exact legacy creator
array the prepared inputs must carry, the exact modern creators the wire sends, the review
that approved them and how the inputs bound the creators. Its SHA256 is pinned in
`scripts/modern_content_class.py` with the review, the supplement and the bindings receipt.

`reviewed_groups()` re-derives the groups and targets from the pinned review and supplement
on every call, through the pinned pair representation, and `nonexxon_source_policy` refuses
the whole policy when the manifest differs from that derivation in any header, group or
target, or when a target also appears in the Exxon manifest. The derivation requires:

- every pair's members to match its representation row by source id and SHA256, both files
  byte-identical and both legacy creator arrays equal, as the review recorded;
- an organizational pair to carry the approving verdict, no blocker and a proposed modern
  creator;
- the one held pair to be the supplement's target, with the supplement's verdict, its approval
  flag set, its boundary hold cleared, its members and source rows equal to the pair's, and the
  supplement and bindings receipt pinning each other and the publication plan.

Each pair also binds its publication-plan target as before: supported, two expected original
files, no production identity.

### Preparation

`modern_content_class.prepare` now selects the one pinned policy that admits a target
(`pair_rule`) and prepares it under ADR 0010's contract: both members assessed live, both
payloads, policies, originals and the v2 class contract bound, the complete legacy metadata
preserved, the wire validated. Two checks differ by policy:

| Group | Legacy creators in the prepared inputs | `creator_interpretation` in the input policy | Wire creators |
|---|---|---|---|
| Exxon203 | the Exxon821 profile array | the Exxon profile digest | the reviewed three-creator projection |
| 24 organizational | one `{"name": …, "type": "Organization"}` object, the literal primary origin | absent | one `organizational` person_or_org with the same name |
| Food Habits | `[{"name": "Pat Livingston"}, {"name": "Douglas Smith"}]` from the creator426 cohort | the creator426 profile digest | two `personal` creators: Pat Livingston, Douglas Smith |

For the 25 pairs the primary origin elements of each original must also equal the elements
the review read (`ordered_primary_origin_elements`), so the review's reading and the live
XML are the same document.

The Exxon policy, its manifest and its wire are unchanged; a test pins the v1 wire SHA256 of
one published Exxon pair at the fixture time.

### Resource types

The bulk route's v2 wire needs a Dataset or Report type for the first source id of each
record. The pinned manifest, `docs/readiness/2026-10-22/resource_types_r3.json` (SHA256
`fdcc8d98…`) as this record is written, has none for these pairs.
`modern_bulk.resource_type_of` now holds a record with the reason "no reviewed resource
type" instead of failing with a KeyError.

`docs/readiness/2026-10-22/resource_types_pairs25_proposal.json` proposes a type per pair
from the first source's XML, under the pinned manifest's rule: the 21 ADF&G report-series
entries are `publication-report` (the pinned manifest types all 217 singleton entries of that
series the same way); the Sun Yat-sen carbonate-chemistry measurements, the VNIRO
hydrochemical data, the Food Habits Database and the TINRO ice-boundary database are
`dataset`. One call is medium confidence: FGDC-2838 (Carbonate Chemistry of the Bering Sea)
could describe a 1985 publication of the measurements. No runtime reads the proposal. The
reviewed types go into `resource_types_r4.json`, built from r3, pinned by a new
`RESOURCE_TYPES_SHA`, as ADR 0014 requires: one manifest per decision, never edited in place.

### Sequence

1. Brett reviews the proposal; r4 is built from r3 with the 25 types and pinned.
2. Classify the 50 sources into the production prepared root (`$OUTPUT/data`) with
   `scripts.collection_qa`, the runbook manifest set and a fixed `--reviewed-at`, without
   reclassifying any source that already has a reviewed input (see "Once: inputs and
   registry" in the [runbook](../readiness/2026-10-20/bulk_route_runbook.md)). The pair
   inputs are not there yet: `plan-pairs` reads `data/zenodo_json/<id>.json` and
   `data/original_fgdc/<id>.xml` for both members of every pair and raises
   FileNotFoundError without them. The classification time enters each input's policy
   digest, the class artifact contract and so the wire, which is why it must stay fixed.
3. `modern_bulk plan-pairs --targets-file docs/readiness/2026-10-22/pairs25_targets.json
   --reviewed-at <fixed past time>` builds the v1 sheet with the twin check against every
   journal. An offline scan of all 4,206 citation titles found no title twin for any of the
   25 pairs.
4. An independent reviewer records the v1 review; `plan-v2` and a second review follow, then
   `drafts`, `release` and `publish`, as in ADR 0013 and ADR 0014.

## Consequences

- 25 records with 50 files: about 13 paced requests each, under ten minutes of API time.
- Admission is finite. Any inconsistency between the manifest, the review, the supplement,
  the bindings receipt, the representation or the plan holds all 25 pairs, not one.
- Changing `scripts/` changes `runtime_binding()` for every preparation. Records are bound by
  source and wire SHA256 (ADR 0013), so published records and reviews are unaffected.
- The Food Habits creators are typed personal on the strength of the 2026-10-06 supplement,
  which reversed an earlier hold on a contextual reading of "Douglas Smith". Brett can still
  hold that pair at review time; the other 24 do not depend on it in the review, but the
  finite manifest does, so leaving it out is a code change.
