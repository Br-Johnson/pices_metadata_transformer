# Residual source32 handoff — 2026-10-04

From main `b5291c3d9cc7e6fd8fef455120329d00a46a6156`, the bounded offline
measurement promotes exactly 32 sources: **3,677 supported / 523 held / 6
malformed**. These are source-readiness counts, not remote verification or
publication. They become main accounting only when this reviewed increment is
merged. The PR timeline records the final current-head CI, Codex review and merge.

## Exact change and evidence

Resource profile [592](finite_source_resource_access_592.json) preserves all 563
previous member/context objects and all three earlier review blocks. It adds:

- Four previously reviewed physical-copy cases, 740/815/851/879, with
  `SOURCE_BACKED` provenance. Historical prices, media and supply terms remain
  literal; no present availability or dataset permission is inferred.
- Twenty-five independently reviewed catalogue resource contexts: 669, 753, 779,
  784, 817, 832, 834, 836, 845, 853, 855, 860, 861, 880, 882, 883, 1341, 1710,
  1767, 1903, 2603, 2698, 2702, 3541 and 4037. Their separate
  `REVIEWER_RECONCILED` block binds the exact source, full XML context, original
  constraints, review time and five earlier user-statement snapshots. Source
  conditions remain unresolved and separate restoration authority remains required.

Creator profile [412](source_citation_credits_412.json) preserves all 233 previous
cohort objects and 409 source bindings. It adds exact FGDC-10 article attribution
and FGDC-3957/3961 institutional product-analysis credit. All creator objects are
name-only; original address/empty origins and explicit role notes are preserved.
This does not establish XML authorship. The [proposal](residual_creator3_proposals.json),
[locator erratum](residual_creator3_evidence_erratum.json) and
[independent review](residual_creator3_source_review.json) are live byte-pinned
dependencies for only these three cohorts. Missing or altered evidence holds them.
The snapshots contain reviewer-transcribed extracts; no retained remote HTML/PDF
bytes or inspected article byline image is claimed. NOAA independently supports
the exact ordered Part II credit; BHL is corroborating worker transcription and
could not be retrieved independently. The separate erratum corrects only the
WNPSST catalogue locator to `yyyy_nn.wnpsst`.

No provider runtime, endpoints, action budgets, credentials, production dedup or
release requirements change. No provider request was made. All prior failed
receipts and bounded execution ledgers remain untouched.

## Measured preservation and checks

The [validation receipt](residual_source32_validation.json) measures a ten-source
smoke, then resource29, creator3 and seven held controls, each before/after/repeat/
withdrawal. Resource29 uses creator409; creator3 uses resource563, isolating the
two changes and avoiding administrative rebinding of previous creator references.
Complete raw metadata is unchanged for all 29 resource cases. Only complete
creator objects and appended preservation notes change for the three attribution
cases; every other metadata field and original note is compared in full, including
the embedded Curator decision object. Dates, restricted access and blank licenses
remain exact. Repeat is identical and withdrawal restores the original holds and
payload bytes. Controls 288/762/849/859/1770/2244/4063 remain held.

All 4,206 original SHA-256 values match the frozen baseline both before and after.
The [integrated ledger](residual_source32_integrated_source_status.json) changes
exactly 32 rows; all 4,174 unselected objects, 456 alias identities and 31 exception
holds are preserved. This is a frozen all-source ledger plus a measured finite
delta, not a fresh full-corpus classification or upload.

[Focused guarded checks](residual_source32_focused_checks.json) record five new
resource contracts and four new creator contracts passing, with zero unexpected
network/private-file/process/write calls. They cover exact membership, full-root
and constraint tampering, review times, live evidence, source and payload
preservation, repeat/withdrawal, and agent plus both human QA schemas. Four prior
combined-source contracts also passed. The first control-report test failure is
retained: its assertion incorrectly required an unchanged selected-profile
fingerprint and was corrected without weakening source/metadata comparisons.
Actual full current-head CI is a separate final PR gate.

Reproduce the bounded measurement from a clean checkout with project dependencies:

```bash
python -B docs/readiness/2026-10-04/validate_residual_source32.py \
  --repo "$PWD" --output /tmp/pices-residual-source32-fresh
python -B ci/run_offline_tests.py
```

The measurement requires a new output directory, clears its environment, uses a
dummy credential and blocks provider transport, sockets and DNS. The CI runner
adds filesystem/process guards. These commands perform offline work only.

| Artifact | SHA-256 |
| --- | --- |
| Resource592 | `7dc625fe5fac625d1fe36f3fdf481c0ba63bd40acb0acc2c9b148079a6f9d550` |
| Creator412 | `c6aa4f9c2e4c80ea565b3a92d66d0e066b12f77534bd23feb92807bd18894ee3` |
| Validation receipt | `653315c87d46b8ef27ca0a73a6a335b44fb7a7974fe24c1461a2d055e044f54f` |
| Integrated ledger | `8d70adb44b599f7b0707f3565d43b2356ee7973054ca66c5592f3826a2c555f2` |
| Canonical status rows | `1bb3ad118096373f69688f438f6f765584e62b46dd2d1d8151ee79060a9d8013` |

## Remaining work and grouped evidence decisions

The 523 held partition is 456 aliases, 22 creator cases, six dates, one title,
one password-target case, 31 existing exceptions and six resource cases. The six
malformed files are additional. Detailed source-bound evidence is retained in
[the baseline reconciliation](held555_reconciliation.json),
[alias/malformed findings](residual_alias_malformed_handoff.json),
[creator questions](residual_creator22_questions.md) and
[six-resource review](residual_resource6_source_review.json).

- **Identity and damaged exports:** the source says, “The ProCite database record
  number corresponds to the Excel Procite Number.” Obtain the original catalogue/
  export-to-ProCite/Excel mapping and existing-record/DOI associations before
  choosing among 456 aliases. Supply intact provenance-bound exports for all-NUL
  3373/3484. For 21/4077/4184/4185, identify which of nine complete XML document
  spans belongs to each catalogue row and how the others are retained; 4185 starts
  with an exact copy of FGDC-6 followed by two “tester 2” entries. No first-document
  parser bypass or canonical identity guess is justified.
- **Creator evidence:** the remaining 16 NEAR-GOOS products have empty origins;
  “collected via Global Telecommunication System (GTS)” does not identify their
  complete credited producers. Four article cases have venue origins such as
  “Journal of Cytology” and “Okeanologiya. Moscow”; they need exact-work ordered
  credits. Two atlas/chart cases say “USSR” and “Published by direction of the
  Chief of Naval Operations.”; they need the edition's credited responsibility.
  Full IDs, titles and consequences are in the linked creator questions.
- **Metadata dates and display title:** 1422/1423/3850 have empty `metd` and
  4139/4161/4181 contain literal `2080207`; authoritative metadata-history evidence
  is required, with no inferred day. FGDC-233 needs a source-supported complete
  shorter display title or a source-specific editorial choice that preserves its
  full source title. No automatic truncation or invented abbreviation is applied.
- **Unretrieved policy scope:** 288 cites “SEBSCC Data Policy (see
  www.pmel.noaa.gov/bering)” and 1770 cites
  `http://daac.gsfc.nasa.gov/data/dataset/SEAWIFS/ds_top_help.html#RESTRICTION`.
  Obtain the applicable terms or an informed source-specific statement of whether
  they separately constrain restricted, unlicensed restoration of these XML
  descriptions. This is not a repeated rehosting-authority or license question.

Four additional source proposals, 762/849/859/2244, are queued for a separate
finite integration and remain held here. FGDC-4063 still says “May require
password access”; its target cannot be resolved by analogy to other records.
The 31 earlier exceptions retain their source-specific questions and evidence;
this increment makes no blanket ruling on them. Parent dispatch of the sole
provider executor and live readback/retry remain separate from source readiness.
