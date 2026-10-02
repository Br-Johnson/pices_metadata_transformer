# Next-cohort census at stable PR8 d39cc21

Read-only audit at `d39cc2158a84d830ac0055f796bf3dd9d612cac4`. Repository clean; no branch movement, implementations, remote requests, or provider calls. All 4,206 original source hashes independently match the current classification. Baseline: 1,328 supported, 2,872 held, six malformed. This report ranks potential corrections; no new promotion is demonstrated.

## Recommendation

The strongest next source-backed access cohort is **122 registration records**, with exact access text `First time users must register to gain database access.` in both metadata and dataset access fields. Both use fields are literal `None`. All four fields are single plain leaves; none has separate metadata security or extension elements. Every source abstract independently describes the named research database/data and user registration: 88 explicitly reference obtaining data with an account, 32 mention downloading data, and two describe the underlying data database and registration directly. Thus this is supported by the XML itself, rather than an extension of Brett's differently worded Contact Source attestation.

Keep any new decision a separate pinned SOURCE_BACKED dataset-access interpretation, bound to these exact source IDs/hashes, four-field context and inspected abstracts. Require the existing separate USER_ATTESTED rehosting authority; preserve restricted/unlicensed XML, raw source constraints, attribution, and other QA gates. Do not infer present-day access availability or register/log in to any external database. Historical source wording suffices for interpreting scope.

**Potential:** 78 have only access holds, 23 still have ambiguous creators (the Unaami group), and 21 have empty creators. Those 44 must remain held. Every member and residual membership is inspectable in `registration-source-context.json`. Canonical membership digest: `04387b47d838171bf0eb733e043b26982bf33fb0d3e4fc6fec3cefd49b96a206`.

## Largest access groups and narrower contexts

| Exact metadata-access wording | Broad count | Narrow four-field context | No other current holds in narrow context |
|---|---:|---:|---:|
| Check with Contributor or Source. | 585 | 585; all four equal | 582 |
| Check with Contributor | 376 | 361; all four equal | 347 |
| Request for one or two pages of data and/or short reports can usually be accommodated. | 298 | 295; paired uses require possible republication authorization | 227 |
| First time users must register to gain database access. | 122 | 122; paired uses None | 78 |
| Unknown | 111 | 109; all four Unknown | 90 |
| Requests for one or two pages of data and/or short reports can usually be accommodated. | 95 | 95; paired uses require possible republication authorization | 93 |
| Check with this URLs : http://www.pmel.noaa.gov/pubs/publications.shtml | 75 | 75; paired uses refer to publications URL | 75 |
| Acknowledgement of data source publication required. | 43 | 43; paired uses require attribution | 30 |
| Data transfer costs will be based on staff time and media costs. | 40 | 38; paired uses prohibit selling data | 8 |
| Check with Contributor about how to obtain data. | 36 | 34; all four equal | 30 |
| Requestor must complete GIS Starter Kit Data Agreement stating Terms and Conditions for use of Starter Kit Data. | 32 | 32; paired uses also give scale/module instructions | 1 |
| Contact Contributor | 30 | 25; all four equal | 25 |

The **585** group is the largest coherent potential, digest `ba0c0d12801971b5e97b0f7ee3a233811b14c93a927fc1867e6e0d9f3104fa0c`. It has 582 access-only records, FGDC-1390 with creator ambiguity, and FGDC-1422/1423 with missing exact metadata-day/construction holds. Representative abstracts describe survey/catch data, but the generic wording alone is not a source-wide proof that every metadata-use instruction solely concerns underlying data. It should not inherit USER_ATTESTED status from the exact `Contact Source.` statement. A consequential scoped question is whether Brett confirms that **this exact alternative historical wording**, in these exact paired access/use fields and absence of additional constraints, also means contacting the provider to obtain the described dataset. That attestation, if obtained, should be separately recorded with its own provenance. Do not broaden by synonym lists or arbitrary text normalization.

The 36 explicit `about how to obtain data` records are another credible small source-backed candidate. There are two use-context groups: 34 all-four-equal (30 access-only, four creator holds) and two whose paired uses instead say `Check with Contact about how to obtain data.` (both access-only). Keep these as explicit disjoint subgroups. Five `Check with Source about how to obtain data.` records have weaker paired use wording (`Check with Source` for four; `Check with Source.` for one) and deserve separate review.

The no-period `Contact Source` cohort is **15**, not just FGDC-1994. Thirteen have all four fields equal (11 access-only, two creators); one has paired `Check with Source` uses; one has paired `See disclaimer` uses. Do not erase the disclaimer residual by punctuation normalization. The current pinned validator and manifest cover only exact period-terminated `Contact Source.` with their existing context guards; none of these is currently in that automatic scope.

Do not convert `Unknown` into permission. Do not discard republication, registration, cost, attribution, contract or disclaimer language. The 298+95 report-request wording groups could describe underlying report access, but their explicit republication text is consequential and must remain separately reviewed/preserved. A URL is a pointer, not a grant.

## Remaining creator groups

There are 477 actual creator holds across 212 normalized ordered primary-origin patterns. Largest: DFO Staff 70 (70 creator-only), Ecotrust/Pacific GIS/Conservation International 37 (one creator-only), USDA Forest Service/Alaska DNR 31 (zero), Unaami Arctic Data Collection 23 (zero), China SOA 20 (zero), NCDC/NESDIS/NOAA 19 (18), and PICES 18 (18). Exact membership and residuals are in `creator-groups.json`.

`DFO Staff` is a collective literal; no contact-derived expansion is established. Organizational hierarchy strings must not be split into coequal creators automatically. The separate semantics lane subsequently found that the exact PICES origin has 26 held sources, not just the 18 with an explicit creator diagnostic: eight additional title-length failures mask that creator diagnostic. Its report at `/workspace/scratch/pices-next-semantics/REPORT.md` recommends literal full institutional origin strings for PICES and NCDC, with no hierarchy splitting (potential 36 promotions; nine residuals). This distinction matters: ranking explicit creator holds alone is not a complete source-pattern membership selector. This census makes no creator correction or date assumption.

## Overlap and residual controls

Among 2,872 held records, 2,168 carry access holds, 477 creator ambiguity, and 456 exact-copy alias holds. These are overlapping dimensions, not additive totals. Intersections: access/creator 214, access/alias 48, creator/alias two; both creator/alias cases also have access holds.

Disjoint dimension strata are: access alone 1,908; access+creator 212; access+alias 46; access+creator+alias two; creator alone 263; alias alone 408; none of these three dimensions 33. “Alone” describes these three dimensions only; individual records may still have technical/date/relation issues. `disjoint-hold-dimensions.json` contains exact memberships; `residual-groups.json` partitions all held records by their complete reason set (44 patterns).

Single metadata-access wording groups partition access-held sources (179 patterns); adding all four constraint values, plain shape and security/extension flags yields 198 narrower contexts. Creator/access cohorts may overlap (e.g. all 23 Unaami records are in the 122-registration cohort). Any future batch compiler must report those overlaps and field ownership/precedence rather than add expected promotions.

## Evidence files

- `audit.py`: deterministic read-only source enumeration.
- `summary.json`: current classification hash, all-source hash checks, ranked patterns/digests.
- `access-groups.json`, `access_context-groups.json`: exact members, canonical digests, full residual memberships.
- `creator-groups.json`: all 212 origin groups and residuals.
- `held-source-evidence.json`: per-source exact normalized constraint/origin evidence and current holds.
- `registration-source-context.json`: all 122 original titles/abstracts/purposes, member hashes, and residuals.
- `residual-groups.json`, `disjoint-hold-dimensions.json`: independently inspectable partitions.

No guessed creator, date, license, rehosting authority, or live-access claim was introduced. PR8 remains unchanged.
