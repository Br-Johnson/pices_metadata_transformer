# Literal citation extension: 27 new source bindings

The source decisions extend the reviewed PR8 checkpoint `a70e56b` and the exact
residual audit `84b0cf7`, without changing original XML or general creator rules.
Runtime: `51af64d17c777222afe49a989d591dad01836bfa`.
[The combined manifest](institution_program_citation_99.json), SHA-256
`04db21a16750930112589d0cb9ab51df4638499831ac8b61760b179734d18323`, contains
the original 72 cohort objects verbatim and 27 newly reviewed source/hash bindings.
The original 72 manifest remains accepted and unchanged. No additional CLI
option, schema, clock or authority is introduced.

## Actual source decisions

| Exact citation group | Sources | Newly supported | Independent access holds |
| --- | ---: | ---: | ---: |
| NOAA / NMFS / AFSC / RACE | 9 | 4 | 5 |
| Northwest Fisheries Science Center / NMFS / NOAA | 4 | 4 | 0 |
| Auke Bay Laboratory / AFSC / NMFS / NOAA | 3 | 0 | 3 |
| Fisheries and Oceans Canada, Ocean Sciences & Productivity Division | 4 | 1 | 3 |
| Scripps Institution of Oceanography (SIO) | 3 | 3 | 0 |
| North-East Asian Regional - Global Ocean Observing System (NEAR-GOOS) | 2 | 2 | 0 |
| National Science Museum, Tokyo, Division of Fishes | 2 | 2 | 0 |
| **Total** | **27** | **16** | **11** |

Independent source review cleared each as one literal primary dataset-citation
attribution. Every source has one plain, attribute-free origin and no aliases.
Full existing creator objects remain intact: existing Organization types only
for the 16 RACE/NWFSC/Auke Bay sources, no added type for the other groups. Agency
hierarchies are not split, contacts are not promoted, and XML authorship remains
explicitly unestablished. Preserve NWFSC's literal "National Oceanographic"
wording and NEAR-GOOS's untyped program attribution.

Recognition is limited to this exact manifest and source ID/hash/plain origin.
The shared agent and both human QA schemas check full creator objects. Rehashing
edited memberships, inferred type/name/affiliation/identifiers, withdrawn evidence
or the same literal name outside membership does not gain trust. Selecting the
old 72 profile or removing/missing the new evidence retains the 27 conservative
holds. No access vocabulary or rights rule is widened.

The eleven held sources are FGDC-220,228,231,232,257,258,259,260,378,500,504.
Their access instructions remain unresolved after creator checks pass. The
sixteen supported sources also retain every dataset/metadata term, including
NEAR-GOOS registration, Scripps's COPEPOD/original-PI credit, FGDC-4042's
copyright/commercial-use restriction and FGDC-3749's source-website instruction.
Source support does not turn these into open-license or unrestricted data records.
All XML remains restricted with blank licenses and separate USER_ATTESTED
rehosting provenance; the exact metadata creation/revision day is unchanged.

## Observed validation and preservation

The new positive tests failed before the hash pin was installed. **30 targeted
tests and 284 complete guarded offline tests pass**; network connection attempts
were blocked during the full suite. The ten-source smoke yields six supported
and four retained access holds. Tests cover all 99 source hashes/full objects,
old-cohort preservation, forgery, both human schemas, agent assessment, payload
tampering, conservative withdrawal/missing evidence and unchanged resume.

Fresh and resumed full-corpus reports are byte-identical, SHA-256
`9dfb6e2e6ab4c3cf12e8d9a7db8bf48d44bd5296dde0f90d5d1b6df8289ead6e`.
Actual counts: **2,137 supported / 2,063 held / six malformed**, exactly
16 held-to-supported changes in the new 27 and no other source-status changes.
The current-runtime old-profile baseline is 2,121 / 2,079 / six. Technical totals
stay 4,131 passing / 63 held / 12 not constructed; aliases stay 228 groups /
456 held identities. Remote verification and publication approvals remain zero.

All **4,206 original hashes**, **4,200 copied XML files** and **4,194 whole
metadata objects** are unchanged. Full metadata was compared against both the
fresh old-profile baseline and the earlier reviewed source preparation. Relative
to the fresh baseline at the same assessment timestamp, exactly **99 payloads**
change solely in `artifact_policy.creator_interpretation`: 27 added references
and 72 administrative rebindings to the combined manifest. Their meanings and
metadata stay identical. The [receipt](institution_program_validation.json)
records exact IDs, residual reasons, hashes, counts and validation scope.

Larger [parallel role/access reviews](residual_role_access_review.md) supply
bounded attribution decisions for Ecotrust37, USDA/DNR31 and Unaami23. No
correction or eligibility change is installed for those 91 members; different
access wording remains a separate evidence question.

## Offline reproduction

```sh
python -m scripts.collection_qa --source-dir FGDC \
  --output-dir /workspace/pices-residual-27-qa/reproduction \
  --authority-manifest docs/readiness/2026-10-02/rehosting_authority.json \
  --access-interpretation-manifest docs/readiness/2026-10-02/contact_source_interpretation.json \
  --creator-interpretation-manifest docs/readiness/2026-10-02/exxon_citation_interpretation.json \
  --dataset-access-interpretation-manifest docs/readiness/2026-10-02/registration_access_interpretation.json \
  --contributor-access-interpretation-manifest docs/readiness/2026-10-02/contributor_source_interpretation.json \
  --collective-creator-interpretation-manifest docs/readiness/2026-10-03/dfo_staff_citation_interpretation.json \
  --institution-creator-interpretation-manifest docs/readiness/2026-10-03/institution_program_citation_99.json \
  --reviewed-at 2026-10-03T04:48:29Z
```

Repeat the exact command/output/timestamp for unchanged resume. Selecting the
original institutional manifest reproduces the 2,121-supported source baseline.
The timestamp is a source-assessment time, not an invented source date. This
classification is not a safe upload list, live-record QA, existing-ID/DOI decision
or production release.

The separately frozen canary still has one consumed uncertain POST. Its
[finite recovery recommendation](uncertain_create_recovery_recommendation.md)
does not reset failed state, promise infinite absence proof or authorize writes.
Source restoration continues independently. Oct 6 can support reproducible
source-review deliverables; all-record production publication is not demonstrated
while live canary, credentials, identity reconciliation and release gates remain.

Independent implementation review cleared the frozen runtime, reproduced all
284 guarded tests, validated every one of the 99 source/hash/full-object bindings,
and independently confirmed the exact 16 promotions, eleven retained access
holds, byte-identical resume and complete preservation/policy-only changes.
No concrete code/data blocker remains; this is source-only review, not live QA.
Final independent documentation review verified the receipt/runtime hashes,
all three role-cohort digests, relative links and finite recovery gates; no
material documentation blocker remains.
