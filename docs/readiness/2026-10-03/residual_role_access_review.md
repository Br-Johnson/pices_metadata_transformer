# Parallel read-only role and access reviews

Historical read-only review at PR8 `37ea595`: implementation and observed successor
counts are now in [the joint/collection profile](joint_collection_citation_190.md).
The source decisions and original read-only eligibility delta below remain intact.

Three separate reviewers checked Ecotrust37, USDA/DNR31 and Unaami23 while the
single code writer implemented the separate 27-source citation extension. The
reviews made no file edits, provider requests, credential/private-run access or
eligibility changes. Their canonical member digests bind the complete evidence
members with sorted JSON keys, compact separators and UTF-8/ensure_ascii=False.
All memberships, source/payload/metadata hashes and full source constraints are
in [the frozen residual audit](residual_creator_analysis.json), SHA-256
`9f93d22ede3b67bb50de386f299cea3d91762ce5f10844247b660ee899fc5b21`.

| Exact source cohort | Members | Full-member digest | Actual eligibility change |
| --- | ---: | --- | ---: |
| Ecotrust, Pacific GIS, and Conservation International | 37 | `b541425a147cc1d3b0d4d1772b4136b97ce1db1770575510cd8eef60514faa07` | 0 |
| USDA Forest Service, Alaska Department of Natural Resources, Division of Support Services-Land Records Information Section | 31 | `4523d329f84d9aa33c24239b52446314cf02642e5cdd3c3cdff887872ed260b1` | 0 |
| Unaami Arctic Data Collection | 23 | `e073bea8226faa5b6bf56710c90d7cf46fb02e3ef349fb1293a287d8bf007e99` | 0 |

Each review confirmed exact full-corpus membership, every original hash, copied
XML byte equality, prepared payload/whole-metadata equality, plain origins, no
aliases, source metadata dates and unchanged restricted access/blank licenses.
USER_ATTESTED archival authority remains separate from access meaning and a reuse
license. FGDC describes primary citation originators and metadata contacts as
separate roles; metadata access/use fields concern metadata. Copied dataset-like
wording is evidence of context, not an automatic scope decision.
[Citation definitions](https://www.fgdc.gov/metadata/csdgm/08.html),
[metadata-reference definitions](https://www.fgdc.gov/metadata/csdgm/07.html).

## Ecotrust: three literal citation credits

The source supports this dedicated, bounded correction, in original order:

```json
[{"name":"Ecotrust"},{"name":"Pacific GIS"},{"name":"Conservation International"}]
```

Add no types, identifiers, affiliations, people or XML-authorship claim.
[FGDC-706](../../../FGDC/FGDC-706.xml) describes Pacific GIS through Ecotrust and
Conservation International; these credits cannot be called three independent
legal organizations. Preserve the combined raw origin in the original and notes.
The current literal-preservation profile does not install this split: it would
need its own reviewed full after-image, exact 37-member bindings and creator-only
payload delta tests.

Six separate constraint strata remain: 30 transfer-cost/non-sale records;
FGDC-567/637 transfer-cost/tape format; FGDC-638/645 copy-media cost/Unknown;
FGDC-641 contact/Unknown; FGDC-707 GIS agreement/scale instruction; FGDC-619
all-None. The audit enumerates all six strata, including every non-sale member.
FGDC-707's limited permission for basemap inclusion does not supply the missing
agreement terms or a new license. FGDC-619's contextual USFWS credit stays in its
abstract without becoming a new primary creator. **Thirty-six access holds
remain; FGDC-619 is a diagnostic candidate, not a validated promotion.**

## USDA/DNR: two source credits with DNR hierarchy intact

The reviewed role interpretation supports these literal names in source order:

1. USDA Forest Service
2. Alaska Department of Natural Resources, Division of Support Services-Land Records Information Section

Keep the DNR section inside its department. Infer no equal contribution,
modernized names, contact authors, identifiers, affiliations or XML authorship.
An [official 1997 Alaska publication](https://dggs.alaska.gov/pubs/id/1783)
corroborates LRIS's DNR context. All 31 existing combined creator objects include
Organization type; a future split must explicitly review each entire new object
rather than silently copying that type to two entries. No after-image is installed.

All 31 retain access holds: 29 exact GIS Starter Kit agreement/scale-and-order
cases; [FGDC-739](../../../FGDC/FGDC-739.xml) all-Unknown; and
[FGDC-799](../../../FGDC/FGDC-799.xml) modular-kit availability with the same use
instruction. The actual GIS agreement is absent from the reviewed evidence.
Repeated dataset/metadata text does not disclose its metadata-restoration terms.

## Unaami: literal collection attribution, incomplete acknowledgment evidence

The defensible literal citation remains exactly:

```json
[{"name":"Unaami Arctic Data Collection"}]
```

The reviewed DFO Staff precedent supports preserving a collective citation
without adding an Organization type, contact person, expanded identity,
affiliation or XML-authorship claim. All 23 dates remain `20020422` / `2002-04-22`.
All 92 constraint nodes repeat the acknowledgment of both Unaami and the original
data source. [FGDC-545](../../../FGDC/FGDC-545.xml) describes a collection, but no
reviewed lineage/cross-reference identifies the separately requested original
data source. Point/distribution contacts and NOAA liability text cannot fill that
attribution gap. All 23 access/acknowledgment holds remain.

## Meaning decisions that remain queued

Existing exact Contact Source / Check with Contributor or Source attestations
do not answer these different strings. Any scope statement must bind the precise
source IDs/hashes and preserve the wording and blank license:

- Ecotrust: for each of the five non-None strata, do the repeated metadata-field
  costs/non-sale/distribution/contact/agreement instructions govern only the
  underlying GIS layer, or also restoration of the descriptive XML?
- USDA/DNR: what metadata-restoration conditions come from the missing agreement
  for the exact 29-member stratum, FGDC-739's Unknown fields and FGDC-799's modular
  wording?
- Unaami: does acknowledgment apply to metadata restoration, dataset use, or
  both, and what exact original-source acknowledgment satisfies it for these 23?

Source evidence or a separately recorded narrow attestation can answer scope;
no broad license, access synonym expansion or contact-derived creator is assumed.
These questions do not block the independently supported 27-source work.
