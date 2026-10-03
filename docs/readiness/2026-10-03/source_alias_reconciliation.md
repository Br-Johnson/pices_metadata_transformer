# Exact-copy alias reconciliation: review candidates only

This analysis starts from PR8 `0188b1f93c459d2427c10d9f1964966289f8576c`
and the frozen source-only report
`f6b68ea0bbc328bd44f6bba06a9b504c8b438c232fc10dcc868d628e2867ec91`.
Actual counts stay **2,138 supported / 2,062 held / six malformed**.
No source, payload, runtime rule, alias hold, provider state or record identity
is changed. All 90 reviewed joint/collection access holds remain intact.

## What the complete independent reconciliation found

All **228 exact-copy groups / 456 identities** are pairs. Original and copied
XML bytes, entire prepared metadata objects and artifact policies are identical
within each pair. No pair has meaningfully different prepared metadata.
Every pair's numeric FGDC IDs differ by 228; that pattern is an observation,
not evidence of a historically primary catalogue entry.

Complete payloads differ solely at `/content_classification/files/0/name`.
Existing artifact preparation binds each source ID and filename: contracts
differ at `source_id`, `files[0].name`, `classification_sha256` and contract
`sha256`. File SHA-256, MD5, size and policy digest are equal. Locally derived
submission metadata then differs only in `notes`, through the artifact-contract
digest. **Identical prepared metadata does not make submitted identities or
fingerprints interchangeable.** The map preserves every member's original
filename, raw/payload/metadata hashes and derived contract/submission hashes.

| Current diagnostics | Groups | Source identities |
| --- | ---: | ---: |
| Alias identity adjudication only | 204 | 408 |
| Alias plus access/contradictory-access holds | 20 | 40 |
| Alias plus creator/access holds | 1 | 2 |
| Alias plus title-length/access holds | 3 | 6 |
| **Total, all still held** | **228** | **456** |

Without alias gating the source diagnostics are 408 supported / 48 held; these
are not released records. Technical totals are 450 passing / six held.
The creator/access pair is FGDC-2837/3065. Title/access pairs are
FGDC-2894/3122 (276 characters), FGDC-2960/3188 (252), and FGDC-2872/3100 (358).
Identity reconciliation cannot silently clear those other failures.

## Recommended candidate identity

Use `fgdc-xml-sha256:<shared-original-SHA-256>` as a neutral, durable **byte-group
review identity**. Keep both original source IDs and files. The smallest numeric
FGDC ID is an optional deterministic review representative only; no source
provenance establishes that it is historically primary or owner-preferred.

[The machine-readable candidate map](source_alias_candidates.json), SHA-256
`d1b5aae5446e230d86fd4a91b6385548b8d6c4fa93a3b98a0ccc26fc731f22d5`, has
456 `source_alias_to_candidate_canonical` entries and 228 complete group records.
Every canonical provider record ID/DOI is explicitly unset. No source/provider
records are deleted, collapsed, rekeyed or selected for upload. The analysis
supplies zero eligibility or publication approvals.

Before selecting any provider canonical record, obtain a verified source-to-record
crosswalk, ownership and current remote state. Preserve each existing record/DOI;
a content hash or a title cannot establish those facts. The map is not consumed
by the upload pipeline and grants no bypass of production duplicate protection.

## Retained production associations and distinct title matches

None of the 456 aliases has a direct source/hash association with the five
retained production records. The five protected IDs/DOIs and their original
confidence are preserved, including FGDC-2725's weaker title/date candidate.
The earlier unavailable 17317855 entry and later strengthened FGDC-1238 proposal
remain in evidence history. Earlier public record 15046283 has no source binding;
do not attach it to a group or invent its DOI. Unrelated poster 10042430 stays
excluded. These are historical public facts, not current ownership or absence.

Two groups share the title of retained record 17317851,
DOI `10.5281/zenodo.17317851`, but have different hashes and abstracts:

| Source identity | ProCite | Distinct description |
| --- | ---: | --- |
| Retained FGDC-2043 | 104 | Chiniak Bay bird species composition |
| FGDC-2920/3148 | 438 | Nearshore bird diet/population/production/species composition |
| FGDC-3027/3255 | 604 | Fish diet at Sitkalidak Strait |

The alias pairs must not inherit FGDC-2043's record ID or DOI. Their group map
contains explicit title-only protection warnings; authoritative provider IDs
remain null.

Independent member proof:
`2c82c3420d0146fc42c93ed288cafcf938acae9a892d32403a344bf780b9f339`.
Independent artifact/submission proof:
`f3f11b77e4f767adb390babb1f2901292909bbea7596d3bb933535e52fa37791`.
The owner generator independently matches both proofs, the complete alias-group
digest `798863f69fbcc965f17e21c53e807c8961dfd86c9aeb5139fba07f0160ae7f33`
and historical protection digest
`d6c4aabc801945ccf6edc0221ca87b026777a479db98ed63837252d6829680ed`.
Member, submission and protection proof digests serialize source-ID-sorted rows
as canonical JSON with sorted keys, compact separators, UTF-8 and
`ensure_ascii=False`. The alias-group digest orders groups by source hash.

## Parallel source work and morning decisions

[The read-only next-source evidence](residual_source_candidates.json) freezes
164 non-alias cases outside the reviewed 190 and current access/relation/title
holds. All 164 originals/copies and 158 extant payloads were independently checked;
the 158 complete metadata objects equal the fresh old-profile baseline. The receipt
SHA-256 is `5a53f924e7fcd762509a57a938461aa59638f56e614d42ba2f910e39f5026855`.

The recommended next batches are **15 plain institutional citations preserving
existing full Organization objects**, then **24 untyped institution/program
credits**. Preserve exact historical spelling, raw whitespace/newlines and full
existing creator objects. Five same-origin access-held siblings stay outside the
24-member scope. These 39 are candidate diagnostics, not new support approvals.
Smaller two-credit/person-list cases need dedicated complete after-image review.
Thirty-five mixed BASIS cases need role/order review, including source
"Nancy Navis" versus abstract "N. Davis". Twenty-one empty origins and six blank
or literal `2080207` metadata dates need authoritative evidence; no contact,
hosting context or invented date can fill the gaps.

The [morning meaning bundle](morning_source_decisions.md) gives exact representative
terms and the unchanged source/hash bindings for all 90 access holds, with the
missing creator/date evidence and canonical-identity limits separately stated.
No user answer is assumed by this analysis.

## Reproduce without provider access

```sh
PYTHONDONTWRITEBYTECODE=1 python docs/readiness/2026-10-03/source_alias_reconciliation.py \
  --prepared /workspace/pices-joint-citation-91-qa/after > /tmp/source-alias-candidates.json

PYTHONDONTWRITEBYTECODE=1 python docs/readiness/2026-10-03/residual_source_candidates.py \
  --prepared /workspace/pices-joint-citation-91-qa/after \
  --comparison /workspace/pices-joint-citation-91-qa/baseline \
  > /tmp/residual-source-candidates.json
```

Both maps were regenerated with byte-identical results. The generators
check actual original/copy/payload bindings and report hashes; they do not call a
provider or create an upload ledger. Their SHA-256 pins are:

- Alias generator: `3736e325843c0e6bdd73bb66d955d32116a33aa311e324090730d7d745e6299b`.
- Next-source generator: `50dfc0a6cfc81e0379bde78ceea96f0e4ce1648fac77ce1989e048cb579bc4e3`.

Independent artifact review reconstructed both alias proof digests from the map,
verified every retained historical protection and both title-only warnings, and
cleared all 456 rows / 228 groups. Separate source-artifact review verified all
eight cohort digests, 112 displayed evidence records / 106 existing full creator
objects, and the morning bundle's nine partitions / 90 distinct source-hash
bindings. It corrected the `metrd` evidence label to metadata review date; no
source dates, memberships or support counts changed. Both generators pass Ruff
F checks, and all 16 local links in the two handoff documents resolve.

Runtime tests are unchanged from the reviewed
289-test source checkpoint; no new live QA or repeated runtime test result is
claimed for this read-only analysis. The uncertain Sandbox POST remains spent
and held; no provider request, retry, state reset, new canary machinery, merge or
production release is performed.
