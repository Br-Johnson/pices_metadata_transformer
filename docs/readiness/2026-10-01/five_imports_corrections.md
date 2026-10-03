# Correction proposal for five existing production imports

**Review only. Preserve the existing record IDs and DOIs.** Five bounded, unauthenticated public API GETs succeeded on October1,2026. Original source fields were compared at repository revision `1693d7f1bbc6bb3e21dec0953f084f7b719fccf8`. This establishes descriptive association, not authenticated upload provenance or approval to edit. No live change, new record, deletion, community submission or publication was performed. The [structured proposal](five_imports_correction_proposal.json) includes exact source fields/hashes, current public fields, retrieval provenance and candidate values.

| Existing record | Source association | Supported correction candidate | Unresolved decisions |
| --- | --- | --- | --- |
| [17317859](https://zenodo.org/records/17317859), DOI10.5281/zenodo.17317859 | **FGDC-2057 / ProCite133**: matching full title and normalized abstract, matching ProCite number | Current year1220 is unsuitable; flag for correction, but replacement value is not established. Existing description is source-faithful. | Raw122003 meaning; object/date policy; source Contact Source vs currentCC0; mixed institutional/personal creator attribution. Cited1994 is not automatically the metadata publication date. |
| [17317857](https://zenodo.org/records/17317857), DOI10.5281/zenodo.17317857 | **FGDC-2725**: unique full-title match and date19810101; description missing prevents an abstract match | Restore the substantive source abstract. Replace split person-like institution fragments with source-faithful organization credit, pending reviewer confirmation of the deposited object's creator role. | CurrentCC0 not established by sourceNone. Source date matches current1981-01-01; no unsupported date change proposed. |
| [17317855](https://zenodo.org/records/17317855), DOI10.5281/zenodo.17317855 | **FGDC-1238**: matching full title and normalized abstract | Same NOAA organization-credit correction candidate. Existing description matches source. | Source1990 is yearprecision, not evidence of a known January1. Check with Contributor is not a CC0 grant. Restricted public API file listing is not proof of absent files. |
| [17317853](https://zenodo.org/records/17317853), DOI10.5281/zenodo.17317853 | **FGDC-2731**: matching report89-04 title and normalized abstract | Replace split Alaska department/division fragments with source-faithful organization credit, subject to role review. | Source1988-Present resembles coverage/series information; public1988-01-01 is not verified report publication date. TitleMarch1989 is a verification lead. Conditional departmental authorization does not establish currentCC0. |
| [17317851](https://zenodo.org/records/17317851), DOI10.5281/zenodo.17317851 | **FGDC-2043 / ProCite104**: matching title, normalized abstract and ProCite number | Flag year1220 without guessing a replacement. Existing description is source-faithful. | Same122003/rights/object-role issues as sea-otter record. Cited1977 is research citation evidence, not automatically metadata date. |

## Concrete field proposals

### Restore description on17317857

[FGDC-2725](https://github.com/Br-Johnson/pices_metadata_transformer/blob/1693d7f1bbc6bb3e21dec0953f084f7b719fccf8/FGDC/FGDC-2725.xml) contains a substantive abstract about measured dissolved hydrocarbons, seasonal patterns and circulation in Bristol Bay. Public `metadata.description` is null. The exact full abstract is retained in the structured proposal as the candidate replacement. Preserve source wording; any scientific typo correction is a separate decision. The source purpose currently retained in public notes is not a substitute for its abstract.

### Preserve institutional identity on17317857 and17317855

Source primary origin for both:

> National Oceanic and Atmospheric Administration (NOAA), Office of Oceanic and Atmospheric Research (OAR), Pacific Marine Environmental Laboratory (PMEL)

Current public creators instead contain `Oceanic, National`, `Atmospheric Administration, Office of Oceanic` and `Atmospheric Research, Pacific Marine Environmental Laboratory`, with fragmented affiliations. Propose an organization-classified source-faithful hierarchy, not those fabricated person-like names. Final metadata-creator versus cited-author credit depends on object policy; this is not an executable API patch.

### Preserve institutional identity on17317853

Source primary origin:

> Alaska Department of Fish and Game (ADF&G), Division of Commercial Fisheries, Management and Development Division

Current public roster fragments it into `Fish, Alaska Department of`, `Game, Division of Commercial Fisheries, Management` and `Division, Development`. Propose source-faithful organization credit after role review.

### Do not automatically rewrite creators on17317859/17317851

Their shared source origin combines the Exxon Valdez Oil Spill Trustee Council, James Bodkin/USGS and Thomas Dean/Coastal Resources Associates. The cited research publications have different author rosters. Determine whether the record credits metadata curators, dataset creators, or cited research authors; preserve the original origin in provenance. No automatic author replacement is proposed.

## What122003 does—and does not—prove

The repository's FGDC standard specifies calendar formsYYYY,YYYYMM,YYYYMMDD ([date convention](https://github.com/Br-Johnson/pices_metadata_transformer/blob/1693d7f1bbc6bb3e21dec0953f084f7b719fccf8/docs/FDGC-STD-001-1998v2.txt#L274)) and defines pubdate as publication/release date of the dataset ([definition](https://github.com/Br-Johnson/pices_metadata_transformer/blob/1693d7f1bbc6bb3e21dec0953f084f7b719fccf8/docs/FDGC-STD-001-1998v2.txt#L2620)). ApplyingYYYYMM mechanically reads122003 as year1220/month03. That is not an acceptable marine-catalogue interpretation; the current parser deliberately holds it.

Across all819 sources with that exact pubdate, metainfo/metd is20040723. Their cited research dates vary. This supports a shared source/export pattern, not an approved publication-date correction. Interpreting it as MMYYYY/December2003 remains a hypothesis until export provenance or authoritative catalogue documentation confirms it. Do not substitute1994,1977,2004-07-23 or today's date automatically.

The public records show1220-01-01, whereas the previously audited code could produce1220-03-01. Do not claim these records were generated by that exact code revision without upload provenance. Correct the known unsuitable year only after a reviewer approves the replacement and precision under the agreed object identity policy.

## Shared remaining gates

- All five public records report CC0/Dataset. Source use constraints are Contact Source, None, Check with Contributor or conditional departmental authorization. They do not themselves establish CC0 for the deposited object. Confirm metadata-artifact rights separately from underlying research rights; no replacement license is guessed.
- Four public listings expose102-byte metadata.txt files. Restricted17317855 exposes no public file entries. Neither filenames/file count nor restricted visibility establishes research-data content. Review actual contents and assign the approved metadata_only/data_included/mixed/unknown roles before adding searchable tags. No file replacement or version creation is proposed here.
- All five public metadata responses include PICES community membership. Parent's authenticated owner inventory independently reports the same membership and no second owned copy of these five titles. This does not exclude external duplicates or versions.
- Keep existing record IDs/DOIs; correct metadata in place only after exact-field approval. No new duplicate draft is proposed. Any file/content change, record version or community action needs its own reviewed plan under Zenodo's rules.
- Poster10042430 is explicitly outside this task and must remain excluded.

The earlier readiness association table had unavailable public reads for17317855 and a title-only association for17317853. These successful API reads now strengthen those associations; they do not authorize production edits.
