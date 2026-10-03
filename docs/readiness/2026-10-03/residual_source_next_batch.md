# Residual source review and Oct 6 readiness

This source-only analysis starts from PR8/source checkpoint
`a70e56bd67bd85c0ee38c29aa387d03207461738`. It installs no interpretation,
changes no runtime rule or prepared payload, and adds no source-support approval.
The separately frozen canary remains at `2a2c82fa257832986fdd62309a13462b691febda`.

## Actual source evidence

The existing classification SHA-256 is
`7151a1fcf26db347a0a3e8fed392c82c8059d02c7cf0b7525e13cf3694d8d0a7`.
It still reports **2,121 supported / 2,079 held / six malformed**, with
**zero remote verifications and zero publication approvals**. The 279 passing
offline tests belong to the previously reviewed a70e56b evidence; they were not
rerun or counted as live verification by this analysis.

[The deterministic audit](residual_creator_analysis.py) rechecked every original
hash, all 4,200 copied XML files and all 4,194 prepared payload hashes. The entire
metadata object in each of those 4,194 payloads equals the earlier reviewed
2,058-supported checkpoint, including creator objects, dates and rights.
[The new evidence](residual_creator_analysis.json) has SHA-256
`9f93d22ede3b67bb50de386f299cea3d91762ce5f10844247b660ee899fc5b21`.
Every selected member carries its source/payload/metadata hash, full creator
object, exact metadata date, four source constraint fields and unchanged rights.

The largest disjoint current reason partitions include 1,198 access-only,
408 alias-only, 187 access-plus-creator and 154 creator-only. Other partitions
remain in the evidence. Checks can stop at creator ambiguity, so these are
current diagnostics rather than proof that no later check will fail.

## Next bounded interpretation batch

| Exact source citation group | Members | Current creator-only diagnostics | Other current access holds |
| --- | ---: | ---: | ---: |
| NOAA / NMFS / AFSC / RACE | 9 | 4 | 5 |
| Northwest Fisheries Science Center / NMFS / NOAA | 4 | 4 | 0 |
| Auke Bay Laboratory / AFSC / NMFS / NOAA | 3 | 0 | 3 |
| Fisheries and Oceans Canada, Ocean Sciences & Productivity Division | 4 | 1 | 3 |
| Scripps Institution of Oceanography (SIO) | 3 | 3 | 0 |
| North-East Asian Regional - Global Ocean Observing System (NEAR-GOOS) | 2 | 2 | 0 |
| National Science Museum, Tokyo, Division of Fishes | 2 | 2 | 0 |
| **Total** | **27** | **16** | **11** |

All 27 have exactly one plain, attribute-free primary citation origin, no
exact-copy aliases, and one existing creator whose name equals that literal
origin. Preserve the whole existing creator object, including existing
Organization types only where already present. In particular, do not silently
correct the NWFSC source's literal "National Oceanographic" wording or add a
legal-institution type to the NEAR-GOOS program. Names and contacts do not establish
XML authorship; the existing dataset-citation attribution caveat remains.

The proposed implementation follows the already reviewed opt-in institutional
profile: exact source ID/hash/name/full-object bindings, unchanged conservative
default, agent and human schema checks, tamper/withdrawal coverage, then fresh and
resumed full-corpus comparison. Its reviewed membership must be frozen before
implementation. No new profile is installed here. **Sixteen is a candidate
diagnostic count, not an observed or guaranteed eligibility delta.** If exactly
16 later pass all checks, the conditional result would be 2,137 supported /
2,063 held / six malformed; the actual count remains 2,121 / 2,079 / six.

The eleven separate access holds preserve "Upon request", "Contact custodian",
distribution-format wording and "Unknown". Existing restrictions, blank
licenses, USER_ATTESTED rehosting provenance, exact metadata creation/revision
days and all underlying dataset terms stay unchanged. No access synonym is
approved by a creator interpretation. Eight of these eleven are in the RACE/Auke
Bay groups and three in DFO Ocean Sciences.

## Larger cohorts that still need separate evidence

| Largest current creator-diagnostic cluster | Exact members | Creator-only subset | Remaining work |
| --- | ---: | ---: | --- |
| Ecotrust, Pacific GIS, and Conservation International | 37 | 1 (FGDC-619) | Audit the three explicit institutional credits as a separate, source-bound joint-attribution correction; 36 independent access holds remain. |
| USDA Forest Service, Alaska DNR, Division of Support Services-Land Records Information Section | 31 | 0 | Separate the USDA credit from DNR's subordinate-unit hierarchy; all 31 have independent access holds. |
| Unaami Arctic Data Collection | 23 | 0 | Preserve the literal collection attribution; do not invent a legal institution or promote a metadata contact. All 23 retain an acknowledgment/access hold. |

The 37/31/23 groups are disjoint from the proposed 27 and have no aliases. Their
exact memberships and all constraint partitions are bound in the evidence.
Ecotrust includes 30 records saying "Data may not be sold" plus transfer costs,
two tape-format cases, two copy-media-cost/Unknown cases, one contact/Unknown
case, one GIS agreement case, and the one all-None case. USDA includes 29 exact
GIS Starter Kit agreement cases, one all-Unknown case and one modular-kit case.
Unaami's 23 records repeat the same acknowledgment of both collection and
original data source in all four constraint fields. These copied fields provide
context, not new authority or a license. Existing Contact Source / Check with
Contributor or Source attestations do not automatically cover these different
wordings. Queue any required scope question with its exact membership; do not
ask for a blanket archive license or release these groups through a heuristic.

The nine-record BASIS/Japan group with six named people and a trailing NPAFC
credit is not folded into the literal-institution batch: its origin contains
mixed XML and combines individual/institutional roles. The five-record related
BASIS group has additional people, institutions and locations. Their original
citations stay intact pending a dedicated role/order audit.

## Actual canary blocker and smallest optional filter verification

Parent reports the reconciliation GET returned HTTP200 with zero hits after the
normal Requests environment merge fixed SSL without trust changes. Cumulative
GET attempts are **188**, with one uncertain POST and zero metadata/file PUTs.
There is no candidate ID or ledger binding. Latest receipt SHA-256:
`2edf461d42ce6f1149b2c0c9e53f446dd28bc0d9932ceb24659ccd7a6e2e8792`.
This receipt was reported by the parent, not read from private provider storage
by the code owner. The initial POST returned HTTP500 despite matching the
[official empty-create contract](https://developers.zenodo.org/#quickstart-upload)
and [official compatibility test](https://github.com/zenodo/zenodo-rdm/blob/7111dde7d1ebf6f64bc695edf7ad8cce5bfa1ac7/site/tests/legacy/test_quickstart.py#L31).
The server cause and remote commit outcome remain unknown. Search may lag;
zero results do not authorize recreation. The create allowance stays consumed.

If the parent chooses one additional read-only compatibility check, the sole
provider executor can use the already retained owned control ID, denoted
`CONTROL_ID`, and its already retained, timezone-aware creation timestamp T.
The fixed actual ID stays in private executor evidence and is never published.
If T is unavailable or
not trustworthy, stop offline rather than adding another request. The
[official legacy mapping](https://github.com/zenodo/zenodo-rdm/blob/7111dde7d1ebf6f64bc695edf7ad8cce5bfa1ac7/site/zenodo_rdm/queryparser.py#L82)
supports created and recid; that static source is not evidence of deployed
Sandbox behavior. Use exactly two GETs to the hardcoded, slashless Sandbox
owned-deposition endpoint with page=1, size=2, all_versions=1:

1. `q=recid:CONTROL_ID AND created:["T_MINUS_1_SECOND_UTC" TO "T_PLUS_1_SECOND_UTC"]`
   must return exactly that verified-owner ID with the retained created value.
2. Only after the positive control passes,
   `q=recid:CONTROL_ID AND created:["T_MINUS_120_SECONDS_UTC" TO "T_MINUS_60_SECONDS_UTC"]`
   must return an empty array. The disjoint window tests that created is honored
   rather than merely accepting the parameter.

Maximum **two transport GET attempts / 190 cumulative**, including failures;
no constructor GET, automatic retry, redirect, scan, recid sweep or new write
grant. Use normal verified SSL, Bearer only in the header, the existing bounded
response discipline, (10,30) timeouts and a separate five-minute diagnostic
window. Validate locally and retain a separate redacted/hash-bound receipt;
leave every prior state, clock, ID set, ledger and receipt untouched. Query
errors, unexpected IDs/owner/timestamps or redirects stop the check. A successful
positive/negative pair supports only filter compatibility for the known record:
it does not prove uncertain-draft absence, causal identity, or permission for any
PUT. No new controller/state machinery is needed for this diagnostic plan.

## Truthful Oct 6 readiness

As of Oct 3, the source archive and reproducible source-support evidence can be
prepared for review, and residual correction work can continue independently of
the provider fault. There is no evidence supporting a promise that all defensible
records will be published by Oct 6. Current source support covers 2,121 files;
2,079 remain held and six original files are malformed. The proposed 27-member
batch supplies reviewable next work, not completed corrections or remote QA.

Live synthetic draft/readback/unchanged-retry has not passed. Parent reports no
production credential is configured; production existing-ID/DOI reconciliation,
provider compatibility, action approval and remote verification still precede
release. Historical duplicate authorization applies only to Sandbox trial scope.
Preserve existing production identities and DOIs, exclude unrelated poster
10042430, and do not delete, recreate uncertain drafts, merge the repository or
purchase capacity as part of this source analysis.

## Reproduce this evidence without provider access

```sh
python docs/readiness/2026-10-03/residual_creator_analysis.py \
  --classification /workspace/pices-institution-qa/after/classification.json \
  --prepared-dir /workspace/pices-institution-qa/after \
  --comparison-dir /workspace/pices-institution-qa/baseline \
  --output /tmp/pices-residual-creator-recheck.json
```

The output must have SHA-256
`9f93d22ede3b67bb50de386f299cea3d91762ce5f10844247b660ee899fc5b21`.
Use a new output filename on repeat; the script refuses to overwrite evidence.
No provider call, credential, recovery of malformed source, or upload list is used.
Independent review reproduced the exact evidence hash and crosschecked all 118
audited members (27 next-batch and 91 larger-cohort members). Source shapes,
hashes, full creator objects/types, metadata dates, all four constraint fields,
unchanged restricted/blank-license rights and the 16/11 partition cleared. The
review also checked the two-GET query encoding/disjoint control windows and
identified the private control-ID exposure in the draft prose; the published
plan now uses an executor-only placeholder. No runtime suite was repeated and
no provider/private-file access was used for this review.
