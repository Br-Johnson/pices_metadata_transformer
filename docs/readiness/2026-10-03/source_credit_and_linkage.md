# Reviewed source credits and historical dataset links

This checkpoint extends reviewed PR8 `dfeff4ce59a46cf4068255ef1e025c84d2e21edb`.
Runtime/source/test contracts are frozen at
`15a8aecf796d880c539343f28d6d33fce2bc5cce`, on normal handoff branch
`handoff/pr8-source-credit-and-links-20261003`. Actual offline QA yields
**2,288 supported / 1,912 held / six malformed**, exactly **111 promotions**.
These source verdicts supply no remote identity, duplicate absence or release approval.

## Exact reviewed changes

The [319-member creator profile](source_credit_citations_319.json), SHA-256
`7526abc74cdc62644fe682b17ebb23213b90ccb80f6f00c61ee149174ae7c257`, retains all
229 earlier cohort objects verbatim and adds **90 exact source/hash bindings**.

| Added selection | Sources | Source interpretation |
| --- | ---: | --- |
| Smaller explicit plain credits | 10 | Literal person lists and the reviewed two-Organization USFWS/DNR objects |
| Other plain credits | 21 | Literal spelling/order and existing objects; translator role retained |
| BASIS mixed XML | 34 | Explicit ordered citation credits, preserving primary spelling and affiliation context |
| Other mixed XML | 22 | Explicit source credits, retaining funding/support and source context |
| Exact supplemental abstract citations | 3 | Two matching work-author references and one scoped chart-production credit |
| **Total** | **90** | **90 newly source-supported records** |

All full after-images were independently reviewed. **82 complete creator lists
change; eight existing lists remain unchanged with reviewed context bindings.**
The 56 mixed primary origins bind every parsed element tag, attribute, text,
child order and internal tail. The outer origin tail belongs to its surrounding
citation and is excluded from this element projection; immutable full-source
hashes still bind every original byte. The complete primary origin XML, explicitly
labeled a parsed representation, is added to notes without mutating the tree.
Existing plain profiles retain their plain, attribute-free single-origin guard.
No generic name parser, contact attribution, inferred type, affiliation or identity
is added. Source spelling such as `Nancy Navis`, `Akihisa Uran`, `Syuiti Abe`,
`USFWG` and the source's `Drogman` remains literal.

FGDC-2645's required note identifies Gerald A. Sanger as translator of the Shuntov
excerpt, without assigning him original authorship. FGDC-3592–3595 preserve
Office of Naval Research's explicit citation credit and funding/support context;
they do not assert personal authorship or equal contribution.

Three supplements bind the complete original abstract element as well as the
primary citation and source hash:

- [FGDC-2243](../../../FGDC/FGDC-2243.xml) has an explicit nine-author abstract
  reference matching its primary Continental Shelf Research 8(12), pages 1299–1319.
  The profile uses those exact names, without contact-derived expansion.
- [FGDC-2683](../../../FGDC/FGDC-2683.xml) explicitly credits Juan Munoz in the
  reference for the same title and 1954 magazine article. Its original magazine
  origin remains publication-venue context.
- [FGDC-152](../../../FGDC/FGDC-152.xml) explicitly credits R.H. Wyman with producing
  the resource's charts. The required note limits this credit to chart production;
  book sole-authorship and XML authorship remain unestablished. No Navy affiliation
  or institutional type is inferred.

The separate [21-member historical-link profile](historical_dataset_linkage_21.json),
SHA-256 `53b8f4cf4b2c84755653328916d0abfb8439984bd31906e0359f7588e5bd6168`, binds
FGDC-4186–4206. Each has exactly one plain primary online linkage to
`http://near-goos.coi.gov.cn/`, no cross reference, and no alias. The same root is
cited by distinct station and data-series resources. [FGDC §8.10](https://www.fgdc.gov/metadata/csdgm/08.html)
defines Online Linkage as a dataset resource pointer. This evidence supports
preserving the historical pointer without asserting alternate identity of the
restored XML artifact; present website behavior is not part of the evidence.

The correction removes only the generated `isAlternateIdentifier` relationship
and appends the exact URL to notes. The original URL/XML, entire creator objects,
dates, description, references, access terms and blank licenses stay intact.
No replacement relationship, modernized URL, DOI or provider identity is chosen.
Complete before/after prepared metadata hashes bind all 21 after-images. Their
independently reproduced inventory/proof/complete-after hashes are in the receipt.

Both opt-ins are exact manifest-byte/source bindings. Agent QA and both human QA
schemas require the full reviewed objects, source evidence and preservation notes.
Withdrawal or missing/forged evidence restores holds; it cannot silently retain
an eligible correction. Profile changes invalidate construction caches. Coordinated
cache-payload/hash/verdict tampering is also rejected or repaired. Existing source
rights/date/access, alias, remote evidence and release protections remain independent.

## Actual validation and preservation

**Seven new focused tests and 301 guarded offline tests pass.** The initial new-profile
regression failed on the unsupported manifest hash before implementation.
Independent runtime review reproduces all 301 and the seven focused tests, including
mixed-element/supplemental evidence mutation, full-object/context forgery, defaults,
withdrawal, cache tampering, all 21 full-link after-images, agent QA and both human
schemas. Requests transport and socket connections are disabled; only dummy tokens
are used by the test harness.

The old 229-profile fresh baseline is **2,177 / 2,023 / six** and fully reproduces
all 4,194 reviewed predecessor payload byte sequences. Corrected fresh and resumed
reports and all 4,194 payloads are byte-identical. The corrected report SHA-256 is
`e075199e01caef6a1018160be2a74c73f76b3d42190eac72511a14d0f9a0eb26`;
the fresh baseline is `6bc08894bfef3feb85a71fe048255f07b5fe5bb08b9bb73170db97341cb6908b`.

The [complete delta audit](audit_source_credit_and_linkage.py) and independent
standalone comparison verify **4,206 original hashes / 4,200 copied XML byte sequences
/ 4,194 prepared payload hashes**, with no missing or extra artifacts. The exact
prepared metadata deltas are 82 creator lists and notes, eight notes-only and 21
notes and related identifiers; **4,083 complete prepared metadata objects remain
identical**. All other fields are unchanged. Exactly 340 policy references change:
90 new creator bindings, 21 new linkage bindings and 229 prior administrative creator
rebindings. **3,854 complete payload byte sequences remain identical.**

Prepared metadata equality is distinct from submitted fingerprint equality.
Submission adds a source/policy-bound artifact-contract fingerprint to notes.
Consequently 119 previously supported profiles get changed assessed fingerprints
through the prior-policy rebinding; the 111 newly supported records gain assessed
hashes. This does not change their source dates, rights or scientific metadata.
Technical totals stay 4,131 passing / 63 held / 12 not constructed.

The [validation receipt](source_credit_and_linkage_validation.json) records exact
promoted IDs, source/report/manifest/inventory hashes and independent reviews.
All 456 exact-copy alias holds, 90 joint/collection access holds, other hold reasons,
source constraints, restricted XML and blank licenses remain preserved. Remote
verification and publication approval are both zero.

## Remaining work and queued decisions

The 1,912 held records split into disjoint priority scopes:

| Scope | Held |
| --- | ---: |
| Exact-copy identity | 456 |
| Access meaning, excluding aliases | 1,413 |
| Creator attribution only | 8 |
| Empty primary creator | 21 |
| Unsupported metadata date | 6 |
| Source title itself exceeds 250 characters, without other holds | 8 |

The eight creator-only gaps are FGDC-1206/1314 (journal venue only), 2552 (country
credit), 2586 (publication direction), 2587 (collection-editor/lecture-author roles),
3779 (explicit Contributor credit and original-PI role), 3788 (unresolved program/
NOAA relationship), and 3815 (malformed initial/name delimitation). They need actual
source or role evidence; contacts and invented names cannot resolve them. The
BASIS 34 literal citation credits are now resolved without silently replacing
`Nancy Navis`; the older broad BASIS review question is superseded by this exact
implementation. FGDC-3815 remains held.

The 21 empty origins and six source-date gaps remain unchanged. FGDC-1422/1423/3850
lack `metd`; 4139/4161/4181 have literal `2080207`. Verified metadata creation or
last-update days are needed, without guessing. All 42 title failures across the
collection concern titles already exceeding 250 characters; the existing artifact-
suffix fallback cannot repair them. The eight title-only IDs are 1917, 1922, 1923, 1924,
1925, 1930, 1933, 1935. Preserve original titles and queue a bounded display-title
proposal with source-title provenance rather than truncating without review.

Further source-only citation cleanup is **not exhausted**. The separately
[ranked 86-member access-plus-creator queue](remaining_source_credit_candidates_86.json)
is disjoint from all 319 members and has exact member inventory SHA-256
`50b589b0938d49a62077f564324c7501c89b23af0249f3aa871692bac638354b`. It contains 37
plain institution/program credits, eight person credits, ten lists/named-role
contexts, seven joint/contractor credits,17 mixed XML credits and seven nonperson
primary credits. These are review queues, not approved after-images or promotions.
Five literal siblings 121/1767/336/533/535 are a small next source-role candidate;
their independent access holds remain intact. Some abstracts contain matching
work-author references, while radio/editor/compiler roles require dedicated review.

The [nine-partition 90-member access questions](morning_source_decisions.md) and
[unchanged exact scope bindings](joint_collection_source_decisions.json) remain
queued. Existing rehosting/Contact Source/Contributor-or-Source attestations are
not widened. The [456-entry neutral alias map](source_alias_candidates.json)
selects no provider record/DOI; numeric representatives remain provisional.
Existing production IDs/DOIs and weaker historical evidence stay protected;
unrelated poster10042430 remains excluded.

For Oct 6 readiness, source preparation is advanced and reproducible. Delivery
remains gated by the unresolved canary and fresh remote identity/record/release
verification; production credentials are not configured. No upload list or
publication claim follows from source support.

## Frozen offline reproduction

Checkout the handoff branch at this document's containing commit; the tested
runtime files are identical to `15a8aecf796d880c539343f28d6d33fce2bc5cce`. Install
`requirements.txt` in an isolated environment. From the repository root:

```sh
python - <<'PY'
import os, unittest
from unittest.mock import patch
os.environ['ZENODO_SANDBOX_TOKEN'] = 'offline-fixture-token'
os.environ['ZENODO_PRODUCTION_TOKEN'] = 'offline-fixture-token'
def forbidden(*args, **kwargs):
    raise AssertionError('Network transport is forbidden in the offline suite')
with patch('requests.sessions.Session.send', forbidden), \
     patch('socket.create_connection', forbidden), \
     patch('socket.socket.connect', forbidden):
    suite = unittest.defaultTestLoader.discover('tests')
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
PY

classify_source () {
  python -m scripts.collection_qa --source-dir FGDC \
    --authority-manifest docs/readiness/2026-10-02/rehosting_authority.json \
    --access-interpretation-manifest docs/readiness/2026-10-02/contact_source_interpretation.json \
    --creator-interpretation-manifest docs/readiness/2026-10-02/exxon_citation_interpretation.json \
    --dataset-access-interpretation-manifest docs/readiness/2026-10-02/registration_access_interpretation.json \
    --contributor-access-interpretation-manifest docs/readiness/2026-10-02/contributor_source_interpretation.json \
    --collective-creator-interpretation-manifest docs/readiness/2026-10-03/dfo_staff_citation_interpretation.json \
    --reviewed-at 2026-10-03T06:13:33Z "$@"
}
classify_source \
  --institution-creator-interpretation-manifest docs/readiness/2026-10-03/literal_citation_extension_229.json \
  --output-dir /workspace/pices-source-credit-linkage-qa/baseline
classify_source \
  --institution-creator-interpretation-manifest docs/readiness/2026-10-03/source_credit_citations_319.json \
  --source-link-interpretation-manifest docs/readiness/2026-10-03/historical_dataset_linkage_21.json \
  --output-dir /workspace/pices-source-credit-linkage-qa/after

PYTHONPATH=. python docs/readiness/2026-10-03/audit_source_credit_and_linkage.py \
  --before /workspace/pices-source-credit-linkage-qa/baseline \
  --after /workspace/pices-source-credit-linkage-qa/after \
  --reviewed-baseline /workspace/pices-literal-citation-39-qa/after-final
```

The audit's reviewed predecessor input is the retained, exact-hash source snapshot.
For a fresh machine, reproduce that snapshot from frozen predecessor `dfeff4ce`
using its documented 229-profile command before running the final audit. Output
directories are local evidence, never upload ledgers or provider state. Repeat the
corrected command with the same timestamp to verify unchanged resume.

## Provider and repository handoff

The original Sandbox HTTP500 empty POST remains **permanently spent/held**. Its
run ID, failed receipts, ledger/intent history, create allowance, clocks and
parent-reported cumulative 190 GETs are unchanged. This task makes zero provider
requests or writes, and introduces no retry/reset/new canary action. The separate
provider executor remains sole writer; parent dispatch and existing review/live
verification gates apply. The frozen canary controller at
`2a2c82fa257832986fdd62309a13462b691febda` is untouched.

Publication is only to the existing open, non-draft PR8 and normal handoff branch.
No merge, production release, deletion, credential provisioning, paid capacity or
new bot review request occurs. GitHub automated review remains usage-limited:
[actual receipt](https://github.com/Br-Johnson/pices_metadata_transformer/pull/8#issuecomment-5961480212).
The last substantive bot review covered `6f792df`; independent local review is
separate evidence.
