# Eight finite citation credits — 2026-10-04

Base: merged PR28, `173a4b0613e915b2915ae815b01f9f8823f2ced8`.
The accepted citation profile is now [423](source_citation_credits_423.json),
SHA256 `c720de8c0775adf3b432fc4bc5e28bdfbb36c67ceb91b73b719d0179cf8f8bf6`.
It preserves every prior 415-member cohort object and adds exactly eight credits.
Resource607, title36 and all complementary profiles remain unchanged.

Seven source-bound JMA derived products (3951/3952/3953/3966/3967/3968/3969)
receive the institutional creator “Japan Meteorological Agency”. The evidence
supports responsibility for these decoded or analysed products; it does not name
the institution as creator of every input observation or the preserved XML.
Product names, codes and global/regional descriptions support the match; numeric
coordinate equivalence is not claimed. Literal versions, dates and the 3969
longitude values remain unchanged. The WIND2 example filename is not date evidence.

FGDC-1314 receives the four ordered initials credited in a publisher-hosted
bibliographic citation to the matching 1997 work: Evdokimov, V.V.; Rodin, V.E.;
Viktorovskaya, G.I.; Pavlyuchkov, V.A. The retained [source review](creator1314_independent_source_review.json)
distinguishes that later citation from an inspected original byline and preserves
the literal title, journal, date, geography and other source fields.

## Measured result

The [guarded measurement](creator8_validation.json) passes a ten-source smoke and
an eight-candidate plus held-control batch. Each batch uses one prepared output
for before/after/unchanged retry/withdrawal, saving each actual phase. Only the
eight creator fields and their preservation notes change. Existing creator
references for controls 3954 and 909 upgrade415→423 with identical validated
credits and raw metadata, so their derived payload/contract hashes change.
Control3975's complete payload remains unchanged and held;909 remains held.

| View | Supported | Held | Malformed | Total |
| --- | ---: | ---: | ---: | ---: |
| Original source files | 3,704 | 496 | 6 | 4,206 |
| Unique record targets | 3,908 | 64 | 6 | 3,978 |

All 4,206 original hashes pass before/after comparison; all 4,198 unselected
ledger objects remain exact. Source constraints, restricted file access, blank
licenses and separate USER_ATTESTED restoration authority remain intact. The
[source ledger](creator8_integrated_source_status.json) is a measured finite delta
on the frozen prior ledger, not a fresh universal reclassification.

The [target projection](creator8_record_target_projection.json) changes only eight
singleton statuses. Its 228 class rows, source index and class payload/contract
pins are preserved from PR28:204 supported/24 held, all228 upload-ineligible.
No fresh class assessment or artifact rebuild is implied.

The [remaining inventory](creator8_remaining_holds.json) gives exact source IDs,
hashes, existing holds and missing evidence:40 held nonalias sources, six malformed
sources, and24 historical held classes. The40 nonalias holds comprise11 creator
gaps,19 incorporated-policy cases, two metadata-product scope cases, one sensitive
model scope case, one password referent and six metadata-date gaps. Intact bytes
or authoritative component mapping remain necessary for malformed originals.

## Reproduce offline

From the repository root with public requirements installed, use a new output path:

```bash
python -B docs/readiness/2026-10-04/validate_creator8_current.py \
  --repo . \
  --creator-manifest docs/readiness/2026-10-04/source_citation_credits_423.json \
  --output /tmp/pices-creator8-reproduction \
  --reviewed-at 2026-10-04T19:13:20Z
```

The helper installs the offline guard before project imports, uses dummy values,
and hashes original XML independently of CI runtime bindings. Saved receipts
retain the actual author's checkout and paths; a new checkout/review time will
have different receipt bindings. The committed measurement is authoritative for
its own inputs and timestamp. [Focused checks](creator8_focused_checks.json)
record37 passing guarded tests; four new contracts cover exact finite membership,
current metadata/retry/withdrawal, missing/tampered evidence and separate authority.
The PR's actual current-head CI and independent Codex review are the merge gates.

## Parallel evidence preparation

The [pair reconciliation handoff](alias228_production_reconciliation_handoff.md)
preserves captured identities and specifies fresh read-only evidence gaps for the
sole provider executor. Its frozen semantic counts describe PR28, separately from
the creator8 counts above. The [transport recommendation](run02_existing_evidence_transport_recommendation.md)
identifies a same-attempt ingress/parser evidence comparison before another trial.
Neither artifact grants provider actions. This increment makes zero provider
requests, remote verification claims or publication approvals.
