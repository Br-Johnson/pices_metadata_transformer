# Remaining source cohorts after PR8 c486d1f

The exact baseline has **2,212 held records** and is bound in [the census](remaining_held_census.json). Every held source hash was checked against its original XML. Counts below overlap unless explicitly described as disjoint. The [reproduction script](remaining_held_census.py) takes the baseline classification JSON via `--baseline`.

| Opportunity | Exact source group | Defensible action / remaining evidence |
|---|---:|---|
| Exact-copy identity | 228 pairs / 456 files; 204 pairs have no other hold | Preserve both IDs, eventually represent one artifact per pair. Existing remote identity must be resolved before canonical selection; never count 408 alias-only files as 408 publications. |
| Literal collective citation | 70 `DFO Staff` records, all creator-only | Implemented in a separate pinned source-backed profile, preserving exactly `[{"name":"DFO Staff"}]`. No acronym expansion, institutional type, affiliation or person is inferred. |
| Exact institutional citation | 72 records / four exact strings | Next clear candidate: full literal PICES (26), NCDC/NESDIS/NOAA (19), China SOA (20), China First Institute (7), each as one organizational creator. Predicted 63 promotions; nine independent residuals. Not implemented or claimed as a validated delta. |
| Alternative access wording | 376 `Check with Contributor` records | Separate wording from Brett's existing attestations; 361 share the narrow all-four-fields context. No automatic synonym expansion. |
| Missing/malformed metadata dates | Six records | No exact metadata creation/revision day is recoverable from these XML alone. Keep held. |

Other larger origin groups are mostly held for unrelated reasons: 407 Exxon-origin records, 396 ADF&G-origin records and 381 NOAA/OAR/PMEL-origin records are not automatically creator correction cohorts. Complete reason partitions and exact memberships are included in the census. Its largest disjoint reason sets are 1,197 access-only pairs of diagnostics, 408 alias-only, 287 creator-only, and 188 access-plus-creator. Diagnostic short-circuiting can mask additional holds, so membership must come from original source patterns, not only the first diagnostic.

## Implemented literal collective profile

All 70 members have exactly one plain primary-citation `<origin>DFO Staff</origin>`, with no child nodes or attributes and no exact-copy aliases. Representative [FGDC-4078](../../../FGDC/FGDC-4078.xml) describes experimental ADCP turbulence observations. Its metadata contact is a separate person within Fisheries and Oceans Canada; that contact is not promoted into the creator field. The source supports the literal collective citation, not a claim that the collective is a named legal institution or independently established XML author.

[The manifest](dfo_staff_citation_interpretation.json) pins every source ID/hash and the entire literal creator object. The validator pins the manifest bytes. Opt in with `--collective-creator-interpretation-manifest`, alongside all previous authority/access/creator manifests. Full-object QA rejects an added type, affiliation, inferred name or changed reference. XML, full generated metadata, restricted access, blank license, and the existing authorship caveat stay unchanged. The implementation changes only the source-bound interpretation and resulting eligibility, not attribution text.

Two independent source reviews cleared this narrowly literal interpretation. The positive test failed before implementation; 16 focused DFO/legacy citation tests pass, independently reproduced. The full guarded offline suite passes **270 tests**. Fresh and resumed full-corpus results match: **2,058 supported / 2,142 held / six malformed**, exactly **70 promotions** and no other status changes. All 4,206 originals, 4,200 prepared copies and 4,194 complete metadata objects remain unchanged. Full-corpus fresh/resume and preservation evidence is recorded in [the validation receipt](dfo_staff_validation.json); do not infer remote verification or publication from source support.

## Decisions still needed

- **Aliases:** “May each byte-identical pair represent one metadata artifact, preserving both source IDs and any existing remote identity?” Options: approve one-artifact representation with remote canonical reconciliation; or keep pairs held pending identity review. Example FGDC-2838/3066 has identical source SHA-256 `3545d2a03e23dd16f246ba2e836dc33f76dbe1394aa645e0debf85c5f55a3d96`, title “Carbonate Chemistry of the Bering Sea.” No alias is released by this work.
- **Dates:** FGDC-4139, 4161 and 4181 contain literal `2080207`; do not insert a digit to make `20080207`. FGDC-1422, 1423 and 3850 have empty metadata dates. “What verified metadata creation/revision day, with its source, applies to each?” The alternative is to keep these six held. Resource publication dates, survey dates and filesystem timestamps are not substitutes.
- **Access:** “For the exact 361-record all-four-fields `Check with Contributor` cohort, does that wording mean contacting the contributor to obtain the underlying resource rather than restricting reposting the descriptive metadata?” Options: confirm that narrow interpretation with provenance; or retain the access hold. [Exact question membership](check_with_contributor_question_members.json) is evidence only, not authority. This question is not answered by Brett's differently worded previous attestations, and no expansion is implemented here.

No provider request, production release, alias canonicalization, invented date or new license is part of this work. The frozen provider handoff at d5022b8 remains unchanged.
