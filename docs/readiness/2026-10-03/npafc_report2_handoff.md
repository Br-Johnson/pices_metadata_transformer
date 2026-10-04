# Exact two NPAFC report descriptions — 2026-10-04

This adds only FGDC-885 and FGDC-887 to the finite source interpretation profile.
Their metadata describe NPAFC reports 499 and 448 and juvenile-salmon survey
methods. The full XML does not supply station/catch records or the complete
reports. The literal access and publication-notification conditions remain in
both resource and metadata fields. They do not expressly exempt XML; the separate
existing restoration authority remains mandatory. No notification fulfilment,
new license, report/data publication right or new user attestation is claimed.

The [source proposal](npafc_report2_source_proposals.json) and
[independent source review](npafc_report2_source_review.json) bind both source
hashes, complete serialized roots, four plain constraints and the five original
statement files. The [additive 558-member profile](finite_source_resource_access_558.json)
preserves all 556 prior member/context objects and earlier review blocks. A
separate two-member review requires an aware assessment time after the independent
review; prior members retain their previous review times and behavior. Both new
records are REVIEWER_RECONCILED, without expanding the exact 821-record direct answer.

## Measured result

A one-record smoke and then the [exact-two comparison](npafc_report2_bounded_delta.json)
measured two held-to-supported changes. Complete raw metadata, original/copied
XML, creators/roles, report references, scientific/geographic text and source-date
semantics remain unchanged. The sole payload change is the added exact reviewed
policy reference. XML stays restricted and unlicensed; all QA routes retain their
authority, integrity, independent hold and publication checks.

The [cached ledger for all 4,206 sources](npafc_report2_integrated_source_status.json) is
**3,640 supported / 560 held / 6 malformed**. This is the frozen baseline plus
independently measured disjoint 22/106/42/2 deltas, not a new full-corpus or provider
audit. The [generator](integrate_npafc_report2_counts.py) reproduces the previous
3,638/562/6 ledger first and preserves every one of its 4,204 unselected status
objects. All 456 aliases and 31 exact exceptions remain held. The remaining 35
deferred resource cases need their own source review, not a blanket interpretation.

## Reproduction and review

From this checkout with existing dependencies and the retained frozen baseline:

```bash
env -i PATH="$PATH" python docs/readiness/2026-10-03/guarded_npafc_report2_qa.py \
  --baseline /workspace/pices-remaining-cohorts-qa/after/classification.json \
  --output /tmp/pices-npafc-report2-review --limit 2 \
  --reviewed-at <current-aware-time-after-source-review>
env -i PATH="$PATH" python docs/readiness/2026-10-03/integrate_npafc_report2_counts.py \
  --baseline /workspace/pices-remaining-cohorts-qa/after/classification.json \
  --output /tmp/pices-npafc-report2-integrated.json
python -B ci/run_offline_tests.py tests.test_npafc_report2_reconciliation tests.test_resource42_reconciliation
```

The focused contracts cover exact context/hash/time/evidence rejection, old
profile compatibility, all unselected cached statuses, deterministic repeat and
withdrawal, authority/rights gates and agent/both human QA routes. The normal PR
must have a substantive current-head Codex review and actual passing CI before
merge under standing authorization. Its GitHub checks/review timeline records
that outcome; local focused results are separate evidence.

No synthetic/provider runtime, spent intent, private stage, existing record/DOI,
credential, production deduplication or release gate changes. PUT3 remains held
pending retained ingress/parser evidence. Local instrumentation remains an
offline prototype, not evidence of live transmission. This source increment
performs no provider requests, publication or outside messaging.
