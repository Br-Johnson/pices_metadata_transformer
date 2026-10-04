# Fifteen finite source corrections and current alias QA — 2026-10-04

From main `05d699e93572345c0591ca932a03089a9dd9ba9c`, the measured increment
supports fifteen additional source files: eleven exact resource interpretations,
three institutional citation credits and one editorial title. The resulting
source-file ledger is **3,696 supported / 504 held / 6 malformed**. These counts
become main accounting on merge. They describe offline readiness; no provider
verification or publication was performed.

## Exact changes

- **FGDC-233:** [title36](source_display_titles_36.json) retains every work-title
  word in a 250-character display title. The report identifier `91-08` and terminal
  period leave the display only; the complete original citation, responsibility
  and date remain in notes and unchanged XML. The [independent review](fgdc233_independent_source_review.json)
  verifies current before metadata against the original proposal. Every earlier
  title member remains exact; this supplies no general shortening rule.
- **FGDC-2552, 3954, 3956:** [creator415](source_citation_credits_415.json) appends
  three exact institutional credits while preserving all 412 earlier members and
  cohort objects. An AAG bibliography attributes the matching three-volume atlas
  to `U.S.S.R. VOENNO-MORSKOE MINISTERSTVO`, corroborated by a library main-author
  entry. JODC documentation assigns development of the two matching monthly
  subsurface-temperature products to the Japan Meteorological Agency. Collection,
  database operation, contacts and method-paper authors are not promoted to
  creator roles. [Short primary excerpts](creator415_primary_excerpts.json),
  [reviewed proposals](creator415_proposals.json) and the
  [independent source review](creator415_independent_source_review.json) are live
  pinned evidence. They are parsed-web excerpts, not retained remote PDF bytes or
  inspected original atlas title pages. Original origins, including empty origins
  and `USSR`, remain preserved. The corrected wording explicitly acknowledges the
  selected creator replacement; the [original proposal](creator415_proposals_original.json)
  remains frozen.
- **FGDC-53, 563, 564, 565, 627, 754, 755, 757, 760, 2086, 2234:**
  [resource607](finite_source_resource_access_607.json) appends eleven separately
  reviewed inventory, cultural/site-layer, observation-database and inspection-
  database contexts. Full roots, all spatial fields and all four constraint
  elements were individually reviewed. Each source positively describes a
  separately held resource or workflow; the specific protected records are absent
  from its catalogue XML. This does not establish a generic metadata exemption,
  safe publication of site data, legal exemption, declassification, FOIA ruling,
  completed redaction/delivery, or satisfaction of any condition. Existing separate
  restoration authority remains required. All 596 prior members, contexts, review
  blocks and assessment times remain exact. See the
  [candidate evidence](sensitive11_source_candidates.json),
  [independent review](sensitive11_independent_source_review.json) and
  [single word-count erratum](sensitive11_source_review_erratum.json); the
  [original reviewed packet](sensitive11_source_candidates_before_wordcount_fix.json)
  is preserved.

## Actual bounded measurement

The [helper](validate_residual_evidence15.py) installs the full offline guard before
project imports, clears the environment and uses dummy credentials. It performs a
ten-source smoke, then fifteen candidates plus seven controls, through before,
after, unchanged retry and withdrawal. The first after directory is copied to
`after_snapshot` before retry into `after`, so both retained snapshots can be
compared byte-for-byte. Their embedded paths still describe the original after
destination; no semantic path normalization is used.

The [measurement receipt](residual_evidence15_validation.json) confirms fifteen
promotions, repeat equality and complete withdrawal restoration. Resource metadata
objects are unchanged. Creator cases change only the selected creator objects and
precisely accounted source-preservation notes, including the corresponding creator
stanza in `Curator decision`. Their actual complete after hashes are measured;
historical projected after hashes are not represented as actual outputs. FGDC-233
changes only the exact title and appended note. All other metadata fields and
every original/prepared XML remain exact.

Held controls 288/909/1318/1770/1994/4063 remain held; supported title control 621
remains supported with identical raw metadata. A prior-member policy reference
can move to an additive profile only after both validators return identical member
interpretations. This changes its derived artifact/submission hash; the helper
recomputes and checks that hash rather than claiming identical submission bytes.

All 4,206 original hashes match before and after, and the
[integrated ledger](residual_evidence15_integrated_source_status.json) preserves
all 4,191 unselected row objects. The old 31-exception membership is retained as
historical evidence; eleven are now measured supported and twenty remain held.
The [twelve focused guarded contracts](residual_evidence15_focused_checks.json)
pass with zero failures, errors or unexpected guard events. Actual final-head CI
and independent exact-head Codex review are recorded on the PR before merge.

## Source files, content classes and restoration targets

Fresh alias QA at immutable baseline `05d699e` measured both original filenames
in every pair with the existing alias gate active. The
[complete receipt](alias228_current_semantics.json),
[228-class CSV](alias228_current_classes.csv) and
[456-source CSV](alias456_current_sources.csv) establish **204 otherwise-supported
classes / 408 files**, and **24 classes / 48 files with additional holds**: twenty
access pairs, one creator/access pair and three title/access pairs. All 456 final
statuses remain held. Both members agree in component semantics and full prepared
metadata in every class. All 528 measured repository inputs match committed
baseline bytes. The [independent output review](alias228_independent_output_review.json)
checks actual saved payloads, both CSV projections and all those input bindings.

The first run used the active checkout's uncommitted title-rule file. Its result
and log remain preserved separately; the [correction receipt](alias228_first_runtime_binding_correction.json)
identifies that mismatch. The authoritative rerun used an untouched detached
baseline, confirmed by the [committed-input proof](alias228_current_input_bindings.json).
The counts above are current measured diagnostics, not merely the older 204/24
historical assessment, and not an alias promotion.

Brett subsequently [approved one restored record per identical pair](alias_pair_approach_authority.json),
with both original IDs/files/provenance retained and existing production records
and DOIs reconciled before any upload. That approach is the next separate code
increment after this one merges. Neither filename is declared historically
canonical. This increment still has **3,696 supported singleton source files**
and **zero newly admitted alias-class restoration targets**. The 204 otherwise-
supported classes are a distinct diagnostic count, pending that implementation
and its reconciliation requirements; 456 files never means 456 distinct targets.

## Remaining evidence

The [54-case nonalias queue](post15_remaining_evidence.json) contains 48 held and
six malformed sources: nineteen creator cases, six metadata dates, twenty prior
exceptions, three controls and six malformed originals. The
[nineteen incorporated-policy investigations](incorporated_policy19_research.json)
and [three further source investigations](pending3_source_research.json) retain
their holds. Adjacent ADF&G/FAR documents, later IOC rules, current site-policy
counterparts and differing model versions do not establish the missing historical
terms or exact sensitive-content scope.

Further product/article credit candidates are separate research proposals. Missing
backup/component/history and password-target facts remain unresolved; their
archive leads have not all been exhausted. No broad hold-approval request or
renewed rehosting/licence question was sent. Original dates, raw constraints,
existing records/DOIs, production deduplication and poster 10042430 protections
remain intact. No provider or transport action is part of this increment.

## Reproduce

From a checkout containing this increment and project dependencies:

```bash
python -B ci/run_offline_tests.py \
  tests.test_residual_title233 tests.test_sensitive_resource11 \
  tests.test_creator415_institution3
python -B docs/readiness/2026-10-04/validate_residual_evidence15.py \
  --repo "$PWD" --output /tmp/pices-evidence15-fresh
```

The [frozen alias helper](measure_alias228_current_semantics.py) must be invoked
with `--repo` pointing to an untouched checkout at `05d699e`, a fresh `/tmp`
`--output`, and an explicit timezone-aware `--reviewed-at`. It deliberately
requires that baseline. Use the helper from this increment as a separate script;
it was not present in the historical baseline tree.

| Artifact | SHA-256 |
| --- | --- |
| Resource607 | `83bdb0b1ab689e5fbf844467975ad9d279b6bba759cb3db3a18a11704715679c` |
| Creator415 | `ae4404c40238542c517822fe4424d14a0cbe93efef542bf42d359717fd4ba2e3` |
| Title36 | `c776b324f43a3e7560ef016f12b7a345bbb2f21cc016b74bd5298b8ed1e10781` |
| Measurement | `a9f096fea9d5a4c466f26c606bdf2134714b90f5492b07e1184a00b16ec5ae43` |
| Integrated ledger | `4a4ef82f9da793c0a83cd58f6388991dd38f7a5f92947b2d089855b259af4e4a` |
| Current alias QA | `10536d3193b4aa915bbc614d66d4172456e4e2f0b66dd2005b1ea791d9d2f3f0` |
