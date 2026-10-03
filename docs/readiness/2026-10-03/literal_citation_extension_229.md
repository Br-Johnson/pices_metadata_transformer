# Exact literal-citation extension: 39 supported sources

This source restoration checkpoint extends PR8 `d1efbe0ebc18422cabbed1ecfce090b5efcb3311`.
Runtime is frozen at `48af136fe6a52d6a3cfc1e7a6eaf5fda8d131ba1`.
The [229-member opt-in manifest](literal_citation_extension_229.json), SHA-256
`d2ba819c774a43f8cb5d90c28f2e4b3d41283747ddea9f282c0241468ab2c749`, preserves
all 190 previous cohort objects verbatim and adds 39 exact source/hash bindings.
It uses the existing institution interpretation option; default behavior and all
earlier profile hashes remain unchanged.

## Reviewed creator objects and actual source outcomes

| Exact source selection | Added bindings | Complete creator objects changed | Newly source-supported |
| --- | ---: | ---: | ---: |
| Plain institutional citations, existing Organization objects | 15 | 0 | 15 |
| Literal institution/program citations, existing untyped objects | 24 | 0 | 24 |
| **Total** | **39** | **0** | **39** |

Independent source-role review explicitly checked every full after-image against
its primary citation, raw XML hash and existing object. The 15 institutional
objects retain their complete cited hierarchy and existing Organization type;
the 24 untyped credits retain their entire literal objects. Types are consciously
reviewed for these exact source credits, never inferred from a comma or copied
into other records. All 39 have one exact plain primary origin. This is primary
dataset-citation attribution; XML authorship is not independently established.

Historical wording stays literal: `National Climate`, `NOA`, `National Academy of
Science`, cited institutional hierarchies and existing RACE/NMML whitespace
normalization are preserved. The manifest pins exact raw double spaces and the
embedded NMML newline separately from complete normalized creator objects.
Abstract references, original COPEPOD PIs, contacts and hosting organizations do
not replace or expand primary attribution. No split, modernized name, new type,
identifier, affiliation, creator role or source date is invented.

The exact selections and complete source evidence remain in
[the reviewed candidate receipt](residual_source_candidates.json), SHA-256
`5a53f924e7fcd762509a57a938461aa59638f56e614d42ba2f910e39f5026855`.
Their membership digests are `b68bf3a16b7df992e81edf11e0a9dd09c84f743ee8a068dd4914c91db55c4c48`
and `6d64251642fcb74f993352fb830843f62042759998a9aa7d7f1c620b9dfdca0d`.
The new manifest binds immediate predecessor 190 and this evidence receipt;
older predecessor, decision and role evidence remain explicitly ancestral.

Five same-origin access-held siblings—FGDC-121,1767,336,533,535—remain outside
the extension. All 90 joint/collection access holds and 456 exact-copy alias
identities stay held. All 21 empty origins, six unsupported metadata dates and
35 mixed BASIS role/order cases retain their source evidence gaps. Smaller credit
and person-list proposals are not implemented by this profile.

## Actual offline validation and preservation

**34 focused and 294 guarded offline tests pass.** The acceptance regression first
failed on the new manifest's unsupported hash. Tests verify all 229 bindings,
prior cohort/full-object preservation, rehashed forgery, same-origin exclusion,
opt-in/withdrawal, cache repair, actual 39-source decisions, complete metadata and
rights preservation, agent QA and both human QA schemas. Independent runtime
review reproduced all 294 tests with Requests transport and socket connections
disabled; no runtime blocker remains.

Fresh full-corpus QA yields **2,177 supported / 2,023 held / six malformed**,
exactly 39 promotions and no other source-status change. Technical totals remain
4,131 passing / 63 held / 12 not constructed. The same-timestamp fresh 190-profile
baseline is 2,138 / 2,062 / six; all its 4,194 complete metadata objects equal the
previous reviewed source preparation. Assessment time never replaces source dates.

[The complete audit](audit_literal_citation_extension.py) verifies all 4,206 raw
hashes, 4,200 before/after copied XML bytes and 4,194 before/after payload hashes,
with no missing or extra artifacts. **All 4,194 complete metadata objects remain
identical**, including creators, notes, dates, constraints, restricted XML, blank
licenses and acknowledgment wording. Exactly 229 payloads change only through
creator-policy references: 39 new references and 190 administrative rebindings;
3,965 complete payload byte sequences remain identical. Submission fingerprints
remain source/policy-bound and are not interchangeable merely because prepared
metadata is equal.

The [validation receipt](literal_citation_extension_validation.json) retains
exact promoted IDs, before/after report and inventory hashes, unchanged alias
proofs, held siblings and access decisions. Historical production ID/DOI and
title-collision protections remain unchanged. Provider verification and actual
publication approvals remain zero.

## Reproduce offline

```sh
python -m scripts.collection_qa --source-dir FGDC \
  --output-dir /workspace/pices-literal-citation-39-qa/reproduction \
  --authority-manifest docs/readiness/2026-10-02/rehosting_authority.json \
  --access-interpretation-manifest docs/readiness/2026-10-02/contact_source_interpretation.json \
  --creator-interpretation-manifest docs/readiness/2026-10-02/exxon_citation_interpretation.json \
  --dataset-access-interpretation-manifest docs/readiness/2026-10-02/registration_access_interpretation.json \
  --contributor-access-interpretation-manifest docs/readiness/2026-10-02/contributor_source_interpretation.json \
  --collective-creator-interpretation-manifest docs/readiness/2026-10-03/dfo_staff_citation_interpretation.json \
  --institution-creator-interpretation-manifest docs/readiness/2026-10-03/literal_citation_extension_229.json \
  --reviewed-at 2026-10-03T06:13:33Z

python docs/readiness/2026-10-03/audit_literal_citation_extension.py \
  --before /workspace/pices-literal-citation-39-qa/baseline-final \
  --after /workspace/pices-literal-citation-39-qa/after-final \
  --reviewed-baseline /workspace/pices-joint-citation-91-qa/after
```

For a fresh comparison, run the same classifier/time with the original 190
manifest in a separate baseline directory. Repeat the exact current profile,
timestamp and output directory for unchanged resume. The optional reviewed
baseline is an offline hash-pinned source snapshot, never a remote inventory.

The [morning questions](morning_source_decisions.md) retain all nine exact access
partitions. No new access interpretation or license is supplied. The original
Sandbox HTTP500 POST stays spent and held, with receipts, budgets, clocks and
190 cumulative GETs unchanged. No provider request/write, retry, reset, new canary,
repository merge or production release occurs.

Final independent corpus/document review matched exact counts and promoted IDs,
all raw/copy/payload hash proofs, complete metadata equality, 229 policy-only
changes / 3,965 identical payload bytes, all 39 source/full-object after-images,
the 90 four-field access bindings, 456 alias holds and five protected historical
record IDs/DOIs. All missing creator/date/mixed-role and excluded-sibling holds,
inventory digests, provenance and 19 local links match. No offline implementation,
source-integrity or documentation blocker remains. Fresh/resumed reports are
byte-identical at SHA-256
`64a9c6fca4527c3f3901ca14e014690a18cc0ee4a455fa902bf7c35483c3c0e7`.
