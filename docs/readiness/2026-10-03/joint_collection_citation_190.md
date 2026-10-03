# Reviewed joint and collection citation decisions

Source checkpoint: `37ea59528123a243490e60079be72a48ec55a389`.
Frozen runtime: `ca57547e9e393943fdd7763942a1072be0ad5ec0`.
The [combined 190-member manifest](joint_collection_citation_190.json), SHA-256
`43ab11d7da41c6d1b6f8ff7a9582240192505818167725f81a353d4a1ae9e68d`, retains
the earlier 99 cohort objects verbatim and adds exactly 91 source/hash bindings.
The old profiles remain accepted and unchanged. The existing institution CLI
option selects this profile; absent, missing or withdrawn evidence restores the
conservative original creator objects. No generic comma parser or access rule
is changed.

## Actual source-backed decisions

| Exact source cohort | Sources | Creator-list corrections | Newly supported | Access holds retained |
| --- | ---: | ---: | ---: | ---: |
| Ecotrust, Pacific GIS, and Conservation International | 37 | 37 | 1 | 36 |
| USDA Forest Service / Alaska DNR with its cited hierarchy | 31 | 31 | 0 | 31 |
| Unaami Arctic Data Collection | 23 | 0 | 0 | 23 |
| **Total** | **91** | **68** | **1** | **90** |

Ecotrust becomes three literal, untyped credits, in source order. Pacific GIS is
described through Ecotrust and Conservation International in FGDC-706; the list
does not assert three independent legal organizations. USDA/DNR becomes two
complete Organization objects: USDA Forest Service, then Alaska Department of
Natural Resources, Division of Support Services-Land Records Information Section.
The DNR hierarchy stays intact. Both type choices were independently reviewed
from these institutional primary credits and the previously reviewed official
DNR/LRIS context; they are not automatically copied from the combined object.
The exact full USDA/DNR after-image SHA-256 is
`59f6c740ca52f9a8a23dba8d01935926d5cdbbbabdc17c9f73b7a3b3bdf05f81`.
Unaami remains one untyped literal collection credit, following the reviewed
collective-citation precedent. No contact, person, affiliation, identifier,
modernized name or XML-authorship claim is introduced.

The [source-decision receipt](joint_collection_source_decisions.json) binds all
three before/after images and the frozen full-member digests. Recognition requires
the exact manifest bytes, source ID/hash and one exact plain primary origin.
Agent QA and both human schemas check complete creator objects. Rehashed
memberships, changed object fields/order or names outside membership gain no
trust. Rights, dates, aliases and release checks remain independent.

Only **FGDC-619** becomes source-supported after actual validation. Its four
constraint fields are `None`; its abstract's contextual USFWS credit stays
unchanged without becoming a primary creator. All other 90 access cases remain
held. Original/copied XML, metadata dates, all constraint wording, USER_ATTESTED
rehosting evidence, restricted access, blank licenses and the explicit
XML-authorship caveat remain intact. No new attestation or license is supplied.

## Verified changes and duplicate preparation

**35 focused and 289 guarded offline tests pass**, including failing-first
positive cases, complete source/full-object validation, evidence forgery,
withdrawal, unchanged resume, payload mutations and both human schemas. Independent
runtime review reproduced all 289 tests and checked every one of the 190 bindings.
The ten-source smoke yields one supported and nine held sources.

Fresh and resumed full-corpus reports are byte-identical, SHA-256
`f6b68ea0bbc328bd44f6bba06a9b504c8b438c232fc10dcc868d628e2867ec91`:
**2,138 supported / 2,062 held / six malformed**. The fresh old-profile baseline
is 2,137 / 2,063 / six, with all 4,194 complete baseline metadata objects equal
to the reviewed PR8 preparation. Only FGDC-619 changes status.

All **4,206 original hashes**, **4,200 copied XML byte sequences** and **4,194
prepared payload hashes** are verified. Exactly 68 metadata objects change only
in their creator lists and bounded citation notes: the existing curator-decision
creator list is updated and one exact raw-primary-origin note is added. All
other existing notes and metadata fields remain unchanged; **4,126 whole metadata
objects are identical**. At the same assessment timestamp, exactly **190
payloads** change solely through those 68 corrections and creator-policy
references: 91 new references plus 99 administrative rebindings.

Independent complete-source preparation verified **228 exact-copy pairs / 456
held alias identities / 3,978 unique raw contents**, with no missing/extra copies
or payloads. None of the new 91 members has an alias. The original inventory
digest is `27999ceb97fd8f2905513b28a22ac7e09966dab717ab7fad14bb8f9e8507bf8c`;
the duplicate-group digest is
`798863f69fbcc965f17e21c53e807c8961dfd86c9aeb5139fba07f0160ae7f33`.
The reproducible audit matches those independent digests and the protected
historical-public association digest.

Exact titles collide in 329 groups / 712 files; 104 groups / 262 files have
different raw contents. Whitespace/case-normalized titles collide in 329 groups /
713 files; 104 groups / 263 files have different contents. Titles are diagnostics,
not identity decisions. The five committed public associations retain their
existing record IDs and DOIs, including FGDC-2725's weaker candidate confidence.
FGDC-2043's shared title covers three distinct contents; FGDC-2731's report89-04
stays separate from report88-02. Unrelated poster10042430 remains excluded.
This is preparation from historical public evidence, not current remote state,
authenticated ownership or complete production duplicate absence.

The [validation receipt](joint_collection_validation.json) records counts, exact
deltas, hashes, every copy-alias pair and protected public associations. Remote
verification and publication approvals remain zero. Technical totals remain
4,131 passing / 63 held / 12 not constructed. Source support is not an upload
list or production release.

## Remaining exact meaning decisions

The nine partitions and every affected source/hash are enumerated in the source
receipt. Existing Contact Source / Contributor-or-Source attestations do not
answer these other strings. A source statement or a separately recorded narrow
scope attestation could answer them while preserving all wording and blank
licenses:

| Held members | Representative evidence | Exact remaining decision |
| --- | --- | --- |
| Ecotrust30 | [FGDC-568](../../../FGDC/FGDC-568.xml) | Do staff/media transfer costs and `Data may not be sold.` govern underlying GIS data only, or descriptive XML restoration too? |
| Ecotrust2 | [FGDC-567](../../../FGDC/FGDC-567.xml) | What XML-specific scope remains for staff/media cost and UNIX-tar/8mm distribution instructions? |
| Ecotrust2 | [FGDC-638](../../../FGDC/FGDC-638.xml) | What XML-specific conditions remain for copy-media cost and `Unknown` use? |
| Ecotrust1 | [FGDC-641](../../../FGDC/FGDC-641.xml) | Does `Contact Chugach National Forest` concern dataset acquisition only, and what does `Unknown` mean for XML restoration? |
| Ecotrust1 | [FGDC-707](../../../FGDC/FGDC-707.xml) | What metadata-restoration conditions come from the missing GIS Starter Kit agreement and scale/order wording? Its double-space `Starter  Kit` text remains a separate exact binding. |
| USDA/DNR29 | [FGDC-696](../../../FGDC/FGDC-696.xml) | What XML conditions come from the missing GIS agreement and scale/order wording? |
| USDA/DNR1 | [FGDC-739](../../../FGDC/FGDC-739.xml) | What XML-specific scope or condition is established by the four `Unknown` fields? |
| USDA/DNR1 | [FGDC-799](../../../FGDC/FGDC-799.xml) | What XML-specific conditions remain for modular-kit availability and scale/order instructions? |
| Unaami23 | [FGDC-545](../../../FGDC/FGDC-545.xml) | Does collection/original-source acknowledgment apply to XML restoration, dataset use or both, and what exact original-source credit satisfies it? |

Copied dataset-like text in metadata fields is context, not an automatic scope
decision. Acknowledgment cannot be satisfied by inferring a data-source author
from contacts. These holds do not undo the independently supported citation
corrections or FGDC-619's observed promotion.

## Offline reproduction

```sh
python -m scripts.collection_qa --source-dir FGDC \
  --output-dir /workspace/pices-joint-citation-91-qa/reproduction \
  --authority-manifest docs/readiness/2026-10-02/rehosting_authority.json \
  --access-interpretation-manifest docs/readiness/2026-10-02/contact_source_interpretation.json \
  --creator-interpretation-manifest docs/readiness/2026-10-02/exxon_citation_interpretation.json \
  --dataset-access-interpretation-manifest docs/readiness/2026-10-02/registration_access_interpretation.json \
  --contributor-access-interpretation-manifest docs/readiness/2026-10-02/contributor_source_interpretation.json \
  --collective-creator-interpretation-manifest docs/readiness/2026-10-03/dfo_staff_citation_interpretation.json \
  --institution-creator-interpretation-manifest docs/readiness/2026-10-03/joint_collection_citation_190.json \
  --reviewed-at 2026-10-03T06:13:33Z

python docs/readiness/2026-10-03/audit_joint_citation_preparation.py \
  --before /workspace/pices-joint-citation-91-qa/baseline \
  --after /workspace/pices-joint-citation-91-qa/after \
  --reviewed-baseline /workspace/pices-residual-27-qa/after
```

Repeat the classifier's exact timestamp/output for unchanged resume. For a fresh
comparison, run the same classifier with the original 99 profile into a different
baseline directory at that timestamp, then point the audit at those actual
before/after directories. The optional reviewed baseline additionally verifies
complete metadata equality to the preserved PR8 report `9dfb6e2e…`; it is never
a remote snapshot. Assessment timestamps do not replace source metadata dates.

The uncertain Sandbox create remains held under the separate frozen controller.
Its spent POST, failed receipts and budgets are untouched; the earlier
[finite recovery recommendation](uncertain_create_recovery_recommendation.md)
is unchanged. No provider call/write, POST retry, new canary machinery, production
release, repository merge or paid-capacity change is part of this checkpoint.

Final independent corpus/document review matched every audit field, complete
source/copy/payload preservation, the exact 68 corrections/190 references/one
promotion, all nine residual partitions, full USDA after-image pin, alias and
historical-public identity protections, and documentation links. No material
implementation or documentation blocker remains; access meanings and live
QA/release evidence remain separate holds.
