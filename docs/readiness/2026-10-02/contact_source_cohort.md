# Local Contact Source access interpretation

Brett answered at **2026-10-02 18:26:45 UTC**: “It means contact someone (source) to obtain the underlying dataset”. The direct reply was to the question about `Contact Source.` access wording. This is recorded as **USER_ATTESTED source-wording interpretation**, separate from the existing USER_ATTESTED historical GeoNetwork restoration authority. It supplies no new license, independently verified agreement, dataset access permission, or publication approval.

The [interpretation manifest](contact_source_interpretation.json) retains the exact statement, timestamp, source thread/turn/user-item/delivery/reply identifiers and 1,004 original source-ID/SHA-256 pairs. Its SHA-256 is `f34e75dfe0430580815c79658cc054d8b8921c2cdf7e327980a4618e89a2852a`. The canonical ordered ID/hash census digest is `47ec5c2c4f55171fcf22873498242dd93f00d80a0c79d332cf316f8d05098b70`. Retrieval by the parent task is attested; independent permission verification is not asserted.

## Source scope and preserved restrictions

Every member has one plain metadata-access field `./metainfo/metac` and one dataset-access field `./idinfo/accconst`, each exactly `Contact Source.`. Metadata-use and dataset-use fields also match verbatim. A read-only audit inspected all 1,004 raw XML files, including all leaf text, metadata security/extensions, contacts, creators, dates and aliases. It found no separate metadata-disclosure restriction. All metadata dates have valid day precision; citation names are present but 808 sources still have ambiguous creator semantics. Of those, 406 files form 203 whole exact-copy pairs and retain alias holds.

FGDC-122 explicitly says “Access is restricted to IMS researchers.” Its abstract also describes an underlying Exxon Oil Spill database as “litigation sensitive”, with access for CHIA researchers. These underlying-resource restrictions are preserved verbatim in the XML and metadata; interpreting the access field does not grant access to that database.

| Preserved metadata-use wording | Sources | Newly supported | Still creator-held |
| --- | ---: | ---: | ---: |
| `Contact Source.` | 876 | 71 | 805 |
| `Check with Source.` | 127 | 124 | 3 |
| `None` | 1 | 1 | 0 |
| Total | 1,004 | 196 | 808 |

The `Check with Source.` entries above are **use** fields paired with identical dataset-use wording inside the exact `Contact Source.` **access** cohort. They remain raw source text, covered by the existing rehosting-only authority and restricted blank-license conditions. They are not converted into a use license or treated as synonyms by the new access rule. Separately worded `Check with Source.` access cohorts receive no exception.

The validator requires the exact attestation/provenance and digest, original source membership, plain paired access/use fields, and an assessment timestamp after the reply. Extra or mismatched metadata-use/access clauses and metadata-security/extension nodes stay held. The optional version-1 `artifact_policy.source_access_interpretation` stores the manifest path/SHA-256 only for valid cohort members. Existing restoration authority remains mandatory; files stay `restricted`, the license stays blank, and explicit unresolved-rights conditions remain. Both agent source QA and historical schema-1/schema-2 human approval/readback revalidate interpretation evidence. Changed or withdrawn evidence invalidates prior approval. Existing creator/date/relation/identity and separate release gates remain.

## Offline validation and reproduction

The positive regression first failed on the existing unsupported-access error. After implementation, 54 focused/surrounding tests pass, including coherent source/manifest changes with extra metadata restrictions, missing/stale/out-of-scope evidence, authority absence, backdated assessment, existing creator/date/relation holds, alias preservation, unchanged construction reuse and stale agent/human approval/readback.

Ten actual sources were prepared first: all ten technical passes, six supported preparations and four creator holds, two also alias-held. They cover all three use-wording groups and FGDC-122's underlying restrictions. The full socket-blocked suite then passes **147 tests**. Fresh/resumed whole-collection classification is byte-identical at assessment time `2026-10-02T18:57:10.240664+00:00`, report SHA-256 `0836cc003d4151019c1102ade8d385d8f3fd897d05e583b306f41b8aa39b1550`:

- 914 supported preparations, 3,286 held sources and six strict parse failures: exactly 196 newly supported from the prior 718 baseline.
- Technical counts remain 4,131 pass, 63 held and 12 not constructed. Exact-copy counts remain 228 groups/456 files, with 3,978 unique raw contents.
- All 4,206 original hashes and 4,200 actual prepared original copies match: 8,406 checks. The six malformed sources remain preserved and have no prepared copies.
- All 4,194 constructed raw metadata objects, including original XML notes, source dates, attribution, dataset constraints, access conditions and license fields, are unchanged against the baseline. Only 1,004 policies gain the interpretation reference. All constructed policies/inventories use the current assessment time, so payload and derived contract/assessed-metadata hashes change accordingly. No decision is backdated to the baseline run.
- There are zero unexpected socket/disallowed-subprocess events, zero remote-verification flags and zero publication approvals. The original owner's checkout and previous isolated workspace remain clean and untouched.

Run from the repository root into a new derived directory:

```sh
python -m scripts.collection_qa --source-dir FGDC --output-dir /tmp/pices-contact-source-qa \
  --authority-manifest docs/readiness/2026-10-02/rehosting_authority.json \
  --access-interpretation-manifest docs/readiness/2026-10-02/contact_source_interpretation.json \
  --reviewed-at 2026-10-02T18:57:10.240664+00:00
```

Use a current timezone-aware assessment time for a new adjudication and repeat exactly that value for resume. Omit the new option to retain the prior conservative access behavior. Resume still reuses verified transformation bytes while fully reassessing source semantics; measured fresh/resume times are 29.512/27.214 seconds. Manifest/policy changes invalidate the construction cache and saved approvals.

Detailed logs, command receipts, full report and exhaustive payload/hash comparison are retained in the coordinating task as `pices-contact-source-*`; the full verification receipt is `pices-contact-source-full-verification-receipt.json`. This batch is local and prepared for independent final review. No push, merge, provider write, credential operation, sandbox canary or production release occurred. Source support counts are preparation evidence, not release approval.
