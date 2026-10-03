# Access-held source citation cleanup

This checkpoint follows published PR8 `9cdf8b032812fccdd236580f9754641932c617bc`.
Runtime/source/test contracts are frozen at
`0b2132cb3891666993820cc569efea8789b4408a`, on normal handoff branch
`handoff/pr8-access-held-credits-20261003`.

**77 bounded source-credit corrections are complete; all 86 access holds remain.**
There are no source-status promotions: actual full-corpus QA stays
**2,288 supported / 1,912 held / six malformed**. Clearing attribution does not
answer access meaning, grant a license, choose a provider identity or approve release.

## Independently reviewed source changes

The [396-member opt-in creator profile](access_held_source_citations_396.json),
SHA-256 `7b45346be4435fc9fa6bfecfeb3cbc175610abf37a3e59a6b43b9731028e6b8c`,
retains the previous 143 cohort objects covering 319 source bindings verbatim and
adds 77 single-source cohorts, for 220 cohorts and 396 exact source/hash
bindings from the historical [86-member source-review queue](remaining_source_credit_candidates_86.json),
SHA-256 `e81f08548c86a454cf96d4b3d5ca2efd75f87ba518bc793c1f8f7d83194c5843`.
The queue's report/hash evidence records the pre-correction state and remains
unchanged; it must not be mistaken for the current review outcome.
The frozen manifest's interpretation sentence and the audit's
`previous_319_cohort_objects_unchanged` field use 319 as source-membership shorthand;
the executable assertion preserves all 143 actual earlier cohort objects.

| Reviewed selection | Corrected | Retained attribution gaps |
| --- | ---: | ---: |
| Literal institutions/programs | 37 | 0 |
| Plain joint-agency/contractor credits | 7 | 0 |
| Plain person, list and named-role credits | 14 | 4 radio cases |
| Mixed XML credits | 15 | 2 program/institution cases |
| Literal collection and supplemental references | 4 | 3 address/journal cases |
| **Total** | **77** | **9** |

**34 complete creator lists change; 43 existing lists remain unchanged with source
preservation notes.** All 77 full after-images were independently reviewed against
original XML and exact source hashes. The five priority siblings
**FGDC-121/1767/336/533/535** preserve their complete existing untyped creator objects:
Raytheon ITSS, U.S. GLOBEC Northeast Pacific and Alaska Maritime National Wildlife
Refuge. Their source-credit bindings are separate from the exact access terms that
keep them held.

The 37 literal institution/program records preserve entire existing objects and
reviewed existing types. In five radio records—1265/1282/1287/1289/1291—the institution
credit remains catalog primary-citation context; mandatory notes distinguish it
from Doug Schneider's reporting. The NCAR/NOAA primary-citation strings in 28/70
are retained without asserting a corporate hierarchy or affiliation. The SPOT
credit keeps `Ovservation` literal and untyped. NCDS/NASA provider/archive context
adds no author or institutional identity.

The seven plain joint/contractor splits follow explicit primary wording. The
USDA Forest Service / Alaska DNR pair in 565/674 receives consciously reviewed
Organization objects. Exxon/DNR and the literal `USDC Forest Service, Chugach
National Forest` stay untyped. The source's USDC is not repaired to the abstract's
USFS. The DNR/Arctic Geo Resources and DNR/Virgin Creek credits retain explicit
contracting context without asserting equal authorship, affiliation, contractor
ownership or XML rights. FGDC-565's archaeological restrictions remain verbatim.

Named person/list credits preserve source order, inverted names, initials, ranks
and honorifics. FGDC-289 retains the literal `(Ed)` annotation in notes without
assigning author roles; 906 retains `(comp.)` as compilation context. Other
compiler/editor-only notes bind 2197/2302/2413/2524. Primary institutional and
location qualifications stay in the full source origin, without affiliation fields
or added institutional authors. Country-specific data-by credits in 542 remain
scoped to Korean, Polish and Chinese data; they do not claim sole authorship of
the combined database. Committee/institution lines in 2701 remain one untyped
literal collective credit, without four independent legal-author identities.

Same-work abstract references supply literal authors for 2228/2656/2691:
Susanne F. McDermott / Sandra A. Lowe, `Allen, E.W.`, and `Hansen, Paul G.`.
Their primary journal/publication origins remain context. FGDC-2228's cited-work
credit supplies no data-collection or historical-slide ownership claim. FGDC-715
preserves `CIA World Bank II` literally; its abstract's different Data Bank wording
and public-domain statement do not change the creator spelling/type or create an
XML license.

Each new profile preserves the exact plain origin or complete parsed mixed-origin
element, including attributes, text, child order and internal tails. Only the outer
sibling tail is excluded from the element projection; the full source hash still
binds every original byte. Mandatory role/context notes also bind their complete
supporting abstracts. Original XML and full parsed-origin preservation notes stay
intact. The selector adds only a reviewed manifest hash to the existing opt-in path;
no generic parsing heuristic or rights/access policy change is introduced. Existing
agent and both human QA routes enforce full creator objects and required notes.

Independent review corrected three note overstatements before final QA: 1269/1271
now say **literal magazine/source context**, because the radio abstracts establish
reporting but not venue/affiliation; 289 avoids implying that both names are editors.
The final pin rejects the earlier proposal bytes.

## Actual validation and integrity

**Five new focused tests and 306 guarded offline tests pass, independently reproduced.** The new-profile
acceptance regression first failed against the predecessor's unsupported hash.
Contracts cover all 396 source bindings and prior 143 cohort objects, all 86 actual access
holds, the five siblings, full-object/context/abstract forgery, unresolved-role
exclusion, opt-in withdrawal, missing/forged manifests and cache tampering.
Transport/socket connections are disabled and only dummy tokens are used.

The fresh old 319-profile baseline fully reproduces all 4,194 reviewed predecessor
payload bytes. Fresh and completed-resume corrected reports and all 4,194 payloads
are byte-identical. The corrected report SHA-256 is
`dd6a9775ca3124f796a7280189072a446ddbd3256ead34a02ef24013dab87247`;
the fresh baseline is `f790764c69adc7b04e00b1c94a8216baffd250c8cbf5f9a90867eec7383efeaf`.
One audit read encountered an intermediate resume report; final evidence is taken
only after that process completed, and the completed audit/resume proof passes.

The [standalone complete delta audit](audit_access_held_source_credits.py) verifies
**4,206 original hashes / 4,200 XML copy byte sequences / 4,194 payload hashes**, with
no missing/extra artifacts. Exactly 77 prepared metadata objects change only through
creator lists and bounded notes: 34 lists change and 43 lists stay intact. All other
fields, source dates, four constraint fields, contributors, relationships,
restricted access and blank licenses remain unchanged. **4,117 complete prepared
metadata objects remain identical.** Exactly 396 policy references change: 77 new
creator bindings and 319 administrative prior rebindings. **3,798 complete payload
byte sequences remain identical.** Submission artifact fingerprints remain
source/policy-bound; 209 previously supported profiles change assessed fingerprints
through the prior-policy rebinding while their prepared metadata stays identical.

All 77 corrected records retain the primary metadata-access adjudication hold.
Their former creator ambiguity is replaced by the existing unsupported-source-
access diagnostic reached later in assessment. The other nine keep both creator
and access holds. All other hold reasons and source statuses are unchanged.
Technical totals stay 4,131 passing / 63 held / 12 not constructed. All 456 aliases,
90 earlier joint/collection access holds and every prior source/protection binding
remain preserved. Remote verification and publication approval are zero.

[The validation receipt](access_held_source_credits_validation.json) records exact
corrected IDs, report/manifest/source inventories, full after-image digest, source
reviews and final independent runtime/delta reviews. It distinguishes source-credit
correction from source-support promotion. The earlier 21 historical dataset-link
corrections and all earlier citation after-images remain intact.

## Exhausted review scope and queued evidence

The exact 86-member creator review is complete: 77 defensible corrections are
implemented and **nine source-role gaps remain** in
[the exact retained-gap receipt](remaining_access_held_creator_gaps_9.json).
No further complete source-backed creator after-image is available within this queue.

| Retained source | Evidence needed |
| --- | --- |
| FGDC-1257/1258/1262/1273 | Story byline/transcript or explicit role statement distinguishing primary Brad Stevens/Nancy Fresco/William Smoker/Jan Curtis from Doug Schneider's reporting |
| FGDC-4063/4064 | Exact statement establishing independently credited originators versus the Census of Marine Life / Vancouver Aquarium program–institution relationship |
| FGDC-10 | Same-work author/compiler evidence; a postal address, contact and different-subfamily reference are insufficient |
| FGDC-2664/2817 | Same-work byline; journal/place labels and contacts do not establish authorship |

All 86 access holds still need their own source-specific meaning or conditions.
No variants of Contact Source or Contributor-or-Source are silently widened.
The [nine partitions of the 90-member access questions](morning_source_decisions.md) remain
queued under unchanged exact source bindings. More broadly, 1,912 held records still
include 456 aliases, 1,413 access-first cases, eight creator-only gaps, 21 empty
creators, six metadata-date gaps and eight title-only cases. All 42 source-title
failures require separately reviewed display/title evidence; no truncation or
invented date/creator is added. Alias equality chooses no record/DOI or ownership;
[the neutral candidate map](source_alias_candidates.json) remains unchanged.

This source cleanup makes later adjudication more precise. It does not establish
live record readiness. Production credentials and fresh provider identity/record
QA/release evidence remain required.

## Frozen offline reproduction

Checkout this document's containing commit on the normal handoff branch. Its
runtime files are identical to `0b2132cb3891666993820cc569efea8789b4408a`.
Install `requirements.txt` in an isolated environment. The guarded 306-test harness
in the [preceding checkpoint instructions](source_credit_and_linkage.md) is unchanged;
it now discovers the five additional contracts. From the repository root:

```sh
classify_source () {
  python -m scripts.collection_qa --source-dir FGDC \
    --authority-manifest docs/readiness/2026-10-02/rehosting_authority.json \
    --access-interpretation-manifest docs/readiness/2026-10-02/contact_source_interpretation.json \
    --creator-interpretation-manifest docs/readiness/2026-10-02/exxon_citation_interpretation.json \
    --dataset-access-interpretation-manifest docs/readiness/2026-10-02/registration_access_interpretation.json \
    --contributor-access-interpretation-manifest docs/readiness/2026-10-02/contributor_source_interpretation.json \
    --collective-creator-interpretation-manifest docs/readiness/2026-10-03/dfo_staff_citation_interpretation.json \
    --source-link-interpretation-manifest docs/readiness/2026-10-03/historical_dataset_linkage_21.json \
    --reviewed-at 2026-10-03T06:13:33Z "$@"
}
classify_source \
  --institution-creator-interpretation-manifest docs/readiness/2026-10-03/source_credit_citations_319.json \
  --output-dir /workspace/pices-access-held-credit-qa/baseline-final
classify_source \
  --institution-creator-interpretation-manifest docs/readiness/2026-10-03/access_held_source_citations_396.json \
  --output-dir /workspace/pices-access-held-credit-qa/after-final
python docs/readiness/2026-10-03/audit_access_held_source_credits.py \
  --before /workspace/pices-access-held-credit-qa/baseline-final \
  --after /workspace/pices-access-held-credit-qa/after-final \
  --reviewed-baseline /workspace/pices-source-credit-linkage-qa/after
```

The retained predecessor input must match report hash `e075199e...`. On a fresh
machine, reproduce that snapshot from frozen `9cdf8b0` using its documented command
before running the audit. The standalone audit imports no runtime modules and
needs no PYTHONPATH modification. Wait for every classifier process to finish
before reading its report; intermediate checkpoint files intentionally lack a
final summary. Repeat the corrected command with the same timestamp to verify
byte-identical resume. These directories are offline evidence, never upload ledgers.

## Provider and repository limits

The original Sandbox HTTP500 empty POST remains **permanently spent/held**. Frozen
controller `2a2c82fa257832986fdd62309a13462b691febda`, receipts, run ID, ledger,
create budget, clocks and parent-reported cumulative 190 GETs are unchanged.
This task performs zero provider requests/writes/retries/resets. The separate
provider executor remains sole writer; parent dispatch and existing verification
and approval gates still apply. Historical production IDs/DOIs stay protected;
unrelated poster 10042430 remains excluded. No repository merge, production release,
delete, credential provisioning, paid capacity or new bot request occurs.

Existing PR8 stays open and non-draft. GitHub automated review remains usage-limited:
[actual receipt](https://github.com/Br-Johnson/pices_metadata_transformer/pull/8#issuecomment-5961480212).
The last substantive bot review covered `6f792df`; local independent review is
separate evidence.
