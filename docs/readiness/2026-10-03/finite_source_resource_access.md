# Finite source-backed resource access meanings

From merged `4b131266cee68798fffed1c309e447a48a420185`, runtime/source contracts are
frozen at `4cb1f80b70d9052e248b413e205c287ba49573f1` on normal branch
`handoff/pr8-source-access-exceptions-20261003`.

**142 exact sources are newly source-supported: 2,430 supported / 1,770 held /
six malformed.** All 4,194 complete prepared metadata objects remain unchanged.
The correction changes source-bound interpretation evidence only, with separate
restricted, unlicensed restoration authority mandatory. It supplies no data
permission, new license, remote verification or publication approval.

| Exact added meaning | Count | Evidence |
| --- | ---: | --- |
| Underlying-data acquisition | 36 | Access explicitly says how to obtain data; all four literal fields and complete title/abstract/purpose are pinned. FGDC-2579 retains operational-use, permission and password restrictions. Four Source-use variants remain exact cases. |
| Publication referral | 75 | Plain repeated PMEL publication-locator URL in all four fields; full source contexts describe publications. The `metuc` pointer remains unresolved reuse-rights evidence. No current URL terms or agency ownership is inferred. |
| Resource availability/distribution | 30 | Exact data/resource distribution, media or technical-access statements with paired literal `None` use. Complete contextual evidence remains pinned, without a generic availability rule. |
| Public metadata / restricted data | 1 | FGDC-1910 explicitly states metadata is available for public use while data owners must permit access to datasets. Its distinct meaning is retained; no dataset permission or XML license is granted. |

The [264-member profile](finite_source_resource_access_264.json), SHA256
`5c141ea3e0fae8e9b6673a2dc3f5aadba0d16c949767f80b5892ac589e6a0dbf`, retains
all prior 122 registration member objects and source contexts verbatim. Use it with
the existing `--dataset-access-interpretation-manifest` option. The old immutable
registration profile remains accepted. Every added ID/hash is finite and excludes
all 176 protected 86/90 access sources and 456 aliases. Per-source meanings, exact
plain four-field constraints, complete title/abstract/purpose elements and security/
extension absence are rechecked; no lexical heuristic can add membership.

The classifier selects added IDs once from validated immutable evidence, then
revalidates each selected record. Agent and both human approval schemas use the
same policy gate. Separate restoration authority, restricted access, blank policy/
metadata licenses and XML-specific date/rights scope stay mandatory. Missing,
changed, rehashed or withdrawn evidence restores conservative holds.

Six new focused contracts and **312 guarded offline tests** pass. Independent
implementation review reproduced the six focused contracts and every exact profile
binding. Independent complete delta review is recorded in the [validation receipt](finite_source_resource_access_validation.json).
All 4,206 originals, 4,200 XML copies and 4,194 payload hashes are checked. Exactly 264
dataset-policy references change (142 additions +122 earlier evidence rebindings),
3,930 payload byte sequences remain identical, and all 4,194 whole metadata objects
remain identical. Assessed submission/artifact fingerprints change for 243 records;
source support is distinct from a live provider metadata match. Every other status
and hold reason remains unchanged, including all 86/90 access holds and 456 aliases.

The [grouped decision packet](remaining_source_decision_packet.md) separates source
scope questions from actual metadata corrections and original data restrictions.
ADF&G 351, Unknown 109 and Contributor 361 receive no automatic interpretation here.
Thirteen smaller source-credit/title proposals are queued without an implemented
promotion. No provider request or uncertain-create retry was performed.

## Reproduction

Checkout this document's final containing commit. Use an isolated requirements
environment and the guarded harness from [the prior source checkpoint](access_held_source_credits.md).
From the repository root, the committed [offline wrapper](guarded_offline_classify.py)
sets dummy tokens and blocks Requests, socket and DNS transport:

```sh
python docs/readiness/2026-10-03/guarded_offline_classify.py --source-dir FGDC \
  --authority-manifest docs/readiness/2026-10-02/rehosting_authority.json \
  --access-interpretation-manifest docs/readiness/2026-10-02/contact_source_interpretation.json \
  --creator-interpretation-manifest docs/readiness/2026-10-02/exxon_citation_interpretation.json \
  --dataset-access-interpretation-manifest docs/readiness/2026-10-03/finite_source_resource_access_264.json \
  --contributor-access-interpretation-manifest docs/readiness/2026-10-02/contributor_source_interpretation.json \
  --collective-creator-interpretation-manifest docs/readiness/2026-10-03/dfo_staff_citation_interpretation.json \
  --institution-creator-interpretation-manifest docs/readiness/2026-10-03/access_held_source_citations_396.json \
  --source-link-interpretation-manifest docs/readiness/2026-10-03/historical_dataset_linkage_21.json \
  --reviewed-at 2026-10-03T06:13:33Z \
  --output-dir /PRIVATE/NEW-FINITE-ACCESS-OUTPUT
```

Choose a new output directory. The fixed review timestamp reproduces the reviewed
report bytes. Preserve the reviewed predecessor output/report
`dd6a9775...87247`. Audit the completed outputs only:

```sh
python docs/readiness/2026-10-03/audit_finite_source_access.py \
  --before /PRIVATE/REPRODUCED-MERGED-BASELINE \
  --after /PRIVATE/NEW-FINITE-ACCESS-OUTPUT
python docs/readiness/2026-10-03/remaining_access_decisions.py \
  --baseline /PRIVATE/REPRODUCED-MERGED-BASELINE/classification.json \
  --census-output /PRIVATE/NEW-CENSUS.json \
  --manifest-output /PRIVATE/NEW-FINITE-PROFILE.json
```

The census/profile generator verifies the frozen report and all original hashes;
it creates evidence only. Its outputs reproduce the committed bytes. Re-run the
classifier against a completed output for the cache/resume check without changing
code, inputs or timestamps. Partial classifier checkpoints have no final summary.
The completed guarded resume reproduces the exact report and all 4,194 payload
hashes. These instructions perform no remote operation; provider dispatch/release remains
the parent's separate responsibility.
