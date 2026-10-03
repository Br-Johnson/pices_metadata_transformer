# Exact literal institutional citation profile

PR8 was reconciled at `c486d1fe138a1b515a3075840a113a3cdd5a8644` before this work.
The separately reviewed 70-source DFO checkpoint `8bc36dc634c80225d12ac82f91b6fd0abc91e7b5`
reproduced its 270 guarded tests and full-corpus baseline of 2,058 supported /
2,142 held / six malformed. This disjoint source-QA branch includes that reviewed
cohort and the new profile; no repository merge or provider operation occurs.
The separate canary runtime branch remains frozen and provider dispatch remains
with the parent.

Runtime commit: **196cdb029cce3c5dadb632c24bf43c83ca525ee3**. Exact manifest:
[institution_citation_interpretation.json](institution_citation_interpretation.json),
SHA-256 `5099ec64f8b12df939f0c4a5816bd04cf44c2554be9768865c8db9aee18325aa`.
The validator pins those complete bytes and selects exactly one matching source
ID/hash cohort. It rechecks a single plain, attribute-free primary citation origin.
Rehashed membership/type/name/affiliation changes do not become trusted evidence.

## Audited source scope

| Exact primary citation name | Sources | Creator-only candidates | Independent holds |
|---|---:|---:|---:|
| North Pacific Marine Science Organization (PICES) | 26 | 18 | Eight original titles exceed the local validator's title-length limit |
| National Climatic Data Center (NCDC), National Environmental Satellite, Data and Information Service (NESDIS), National Oceanic and Atmospheric Administration (NOAA) | 19 | 18 | FGDC-2578 has separate access wording |
| People's Republic of China, State Oceanic Administration (SOA) | 20 | 20 | None in this cohort |
| China State Oceanic Administration, First Institute of Oceanography | 7 | 7 | None in this cohort |

Each complete literal institutional citation is one attribution. Comma-separated
hierarchical clauses are retained within that name; they are not promoted into
separate creators, people or inferred affiliations. Existing full creator objects
are preserved, including existing Organization types only for the NOAA and First
Institute groups. No type is added to PICES or SOA. All 72 original source/hash
bindings, contexts and full prepared creator objects were independently audited;
none belongs to an exact-copy alias group.

PICES titles sometimes identify editors/compilers. Those titles and original notes
remain verbatim; title/contact names do not become XML creators. Primary citation
attribution does not independently establish XML authorship. The existing explicit
caveat remains in every payload. Dates remain the exact metadata creation/revision
day in metainfo/metd; source resource dates/Unknown/ranges are not replacements.

This is an opt-in source interpretation, not a general transformer rule. Missing,
changed or withdrawn profile evidence retains the conservative default hold.
Both agent source QA and human schema1/schema2 readback revalidate the shared
manifest reference and full creator objects. Existing date, rights, source/title,
relation, alias, remote/duplicate and publication checks remain active. Rehosting
USER_ATTESTED provenance remains separate; restricted access, blank license and
all underlying dataset constraints are unchanged.

## Actual full-corpus result and preservation

**279 guarded offline tests pass**, independently reproduced. The new positive
fixtures failed before implementation. Tests cover all 72 members, cohort/source
forgery, full-object changes, original XML shape, opt-in withdrawal/missing evidence,
agent checks, both human schemas and unchanged reclassification.

Fresh and resumed complete reports are byte-identical: **2,121 supported /
2,079 held / six malformed**. Exactly **63 held→supported** changes occur versus
8bc36dc, all in the audited creator-only subset. Combined with the previously
reviewed DFO70 cohort, this is **133 source-support promotions versus PR8 c486d1f**.
No other source status changes. Technical totals stay 4,131 passing / 63 held /
12 not constructed; exact-copy totals stay 228 groups / 456 held identities.
Remote verification and publication approvals remain zero.

All **4,206 original hashes**, **4,200 copied XML files** and **4,194 entire raw
metadata objects** remain unchanged. Exactly 72 complete prepared payloads change,
each solely by adding artifact_policy.creator_interpretation pointing to this
pinned manifest. Full metadata—not a projection—was compared. See the
[validation receipt](institution_citation_validation.json) for exact promoted IDs,
residual reasons, report/profile/file hashes and preservation counts.

The nine residuals remain held: FGDC-1917,1922,1923,1924,1925,1930,1933,1935 retain
title-length holds; FGDC-2578's “Check with Source about how to obtain data.” /
“Check with Source” wording remains outside the separately attested exact access
profiles. No title truncation, access synonym expansion or new rights claim is
implemented. Independent source/code review is not live record QA or release-
program approval.

## Reproduction

From this source-QA checkout, use repository requirements and a new output folder.
For unchanged resume, repeat the same output folder and assessed timestamp:

```sh
python -m scripts.collection_qa --source-dir FGDC \
  --output-dir /workspace/pices-institution-qa/reproduction \
  --authority-manifest docs/readiness/2026-10-02/rehosting_authority.json \
  --access-interpretation-manifest docs/readiness/2026-10-02/contact_source_interpretation.json \
  --creator-interpretation-manifest docs/readiness/2026-10-02/exxon_citation_interpretation.json \
  --dataset-access-interpretation-manifest docs/readiness/2026-10-02/registration_access_interpretation.json \
  --contributor-access-interpretation-manifest docs/readiness/2026-10-02/contributor_source_interpretation.json \
  --collective-creator-interpretation-manifest docs/readiness/2026-10-03/dfo_staff_citation_interpretation.json \
  --institution-creator-interpretation-manifest docs/readiness/2026-10-03/institution_citation_interpretation.json \
  --reviewed-at 2026-10-03T01:40:00Z
```

Omit only the institutional option to reproduce the reviewed 2,058-source baseline.
All six existing evidence options remain necessary for the combined population.
The timestamp is the recorded source-only assessment time, after the existing
attestations; it is not an invented source date or future provider evidence.
Never interpret this classification as a safe upload list, remote match decision,
preservation of an existing production identity/DOI, or release authorization.
No credentials, live requests, provider writes or publication are required.
