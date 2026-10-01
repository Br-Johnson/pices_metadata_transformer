# Five curator decisions for October 6

These are proposed decisions, not approved corrections. Counts describe the **current transformation contract**, not inherently unpublishable sources. A metadata-only source can itself be a meaningful deposited metadata artifact. Original source XML remains unchanged. Audit revision: `6f792dfc2ff2d3021d7a38cba9f8ab3152d2d58e`.

## 1. Define the deposited object and its rights

Decide whether each Zenodo record deposits the original FGDC metadata artifact describing an external object, or mirrors the same research object already published elsewhere. Original FGDC XML is a candidate meaningful file under the former policy; neither missing underlying datasets nor a lack of downloadable source data automatically excludes a metadata record. PICES should approve that policy before a sandbox upload test. Do not add dummy files.

This decision controls DOI identity, date, credited creators and license scope. A separate metadata artifact should not inherit the described dataset's DOI, publication date or license as if it were that dataset. A same-object mirror must preserve its existing DOI where applicable and be distinguished from a version/subset. Attribution should distinguish metadata creators/curators from referenced research authors, with evidence and roles. A license for metadata/XML does not silently relicense the underlying research object.

Across all **4,200 parseable sources**, zero use-constraint values are recognized as an explicit license grant by the current conservative parser. There are **179 exact wordings**, so cohort review is tractable. This result includes the 2,876 records stopped earlier by date validation; the previous 1,321 license-validation count was only the date-pass subset. No missing use-constraint strings were found in this extraction. No license should be inferred simply from `None`, public access or an institutional affiliation.

| Exact source wording | Count | Representative evidence | Decision needed |
| --- | ---: | --- | --- |
| Contact Source. | 993 | [FGDC-122 use constraints](https://github.com/Br-Johnson/pices_metadata_transformer/blob/6f792dfc2ff2d3021d7a38cba9f8ab3152d2d58e/FGDC/FGDC-122.xml#L96) | Authority/contact evidence; distinguish metadata rights from dataset restrictions. |
| None | 852 | [FGDC-100](https://github.com/Br-Johnson/pices_metadata_transformer/blob/6f792dfc2ff2d3021d7a38cba9f8ab3152d2d58e/FGDC/FGDC-100.xml#L75) | No stated constraint is not an explicit CC0 grant. |
| Check with Contributor or Source. | 585 | [FGDC-1209](https://github.com/Br-Johnson/pices_metadata_transformer/blob/6f792dfc2ff2d3021d7a38cba9f8ab3152d2d58e/FGDC/FGDC-1209.xml#L48) | Resolve permission scope through contributor or an authoritative collection agreement. |
| Republications of materials in this report series may be authorized by the department | 391 | [FGDC-1007](https://github.com/Br-Johnson/pices_metadata_transformer/blob/6f792dfc2ff2d3021d7a38cba9f8ab3152d2d58e/FGDC/FGDC-1007.xml#L53) | Conditional authorization requires evidence; it is not an already granted license. |
| Check with Contributor | 362 | [FGDC-10](https://github.com/Br-Johnson/pices_metadata_transformer/blob/6f792dfc2ff2d3021d7a38cba9f8ab3152d2d58e/FGDC/FGDC-10.xml#L58) | Same authority review. |
| Unknown | 175 | FGDC-1890, FGDC-1891 | Explicit uncertainty; no grant. |
| Check with Source. | 165 | FGDC-1041, FGDC-1310 | Source/referral terms; retain verbatim. |

These seven exact values cover **3,523 sources (83.9%)**; 172 remaining wordings cover 677. Treat cohort similarity as a way to organize evidence, not blanket authorization. Group labels in the evidence JSON are triage heuristics, not legal interpretations.

## 2. Decide the publication-date meaning for missing/unknown/status values

**1,580 date-held sources** contain status/unknown values under the triage grouping: Unknown 1,373; Planned 87; Unpublished material/Material 107; Varies 13. Examples: FGDC-120, FGDC-335, FGDC-4083, FGDC-1094, FGDC-2561. Another **116 sources lack a primary publication date** and currently use a documented fallback rather than fail the date check; that fallback still needs semantic QA.

Confirm whether the Zenodo publication date means first availability of the deposited metadata artifact or the described research object. For a new metadata artifact, an evidence-backed artifact publication date may differ from the research date, which belongs in the description/coverage/citation. Do not automatically replace every unknown value with today's date. Keep unpublished/planned research status explicit. Record approved date derivation, precision and provenance.

## 3. Resolve the repeated `122003` value from provenance

**819 sources** share this exact ambiguous six-digit value (FGDC-1839, FGDC-1840, FGDC-1841, FGDC-1843; sea-otter FGDC-2057 is another). Current parser holds it instead of treating it as year1220. Do not silently guess December2003 or substitute a cited article's year.

Use catalogue-export history and metadata creation/maintenance provenance to determine whether this is a systematically encoded metadata date, and what that means for the approved object/date policy. Approve a cohort rule only if the provenance actually supports it, then create hash-bound per-source decisions. Unknown plus122003 account for **2,192 of2,876 date holds (76.2%)**, but resolving dates alone does not resolve rights.

## 4. Separate coverage/ranges and date precision from publication date

**435 held sources** have clear range/ongoing forms under the triage grouping, including `72-88  thru  87-98` (259), `1988 - Present` (110), `1960 - Present` (27) and `19970101-20021231` (5). Examples: FGDC-1007, FGDC-101, FGDC-2303, FGDC-338. Preserve the range as coverage; do not choose the first observation year as a publication date without evidence. An additional **50 exact YYYY-YYYY values are currently accepted by taking the first year**; those require semantic review too despite passing the parser.

**24 held sources** have otherwise unambiguous month precision: September2001 (23; FGDC-1773 onward) and October2001 (1; FGDC-1752). A month-aware normalization can be automated only after PICES agrees how Zenodo's date field represents precision. Retain the original month precision and avoid presenting an invented first day as known. No parser changes were made in this preparation.

The remaining **18 held sources** span16 exact values—mixed ranges, multiple years, abbreviated quarter/month ranges and status text. Some are recurring/status rather than invalid dates; they need individual triage rather than one guessed correction. Examples: FGDC-626 (`1978-1980, 1989-1994`), FGDC-633 (`199207-099301`), FGDC-1310 (`Jul. - Sep. 2002`), FGDC-345 (`in process`). Evidence JSON retains every exact pattern and representative IDs.

## 5. Reconcile source integrity and existing record identities

Six source files fail XML parsing. FGDC-3373 and FGDC-3484 fail at byte0 and are the only source IDs absent from the4,204-file original archive. FGDC-21, FGDC-4077, FGDC-4184 and FGDC-4185 report trailing content after the document element. Recover approved corrected *working copies* with raw-original hashes and provenance or explicitly exclude pending investigation; do not edit original FGDC sources. The archive difference is now explained by source IDs, not evidence that all4,204 archive entries are valid.

### Bounded public-record source association

Public landing-page evidence was compared with source title/citation/description. No authenticated record identity, old upload provenance or exact payload equivalence is claimed.

| Existing production ID | Supported source association | Remaining uncertainty / action |
| --- | --- | --- |
| [17317859](https://zenodo.org/records/17317859) | FGDC-2057: unique matching title, sea-otter/Kenai description, ProCite133 | Strong descriptive association. Raw date122003 and Contact Source remain unresolved. Retain existing DOI; do not mint a duplicate. Citation1994 is evidence about cited research, not automatically metadata-artifact publication. |
| [17317851](https://zenodo.org/records/17317851) | FGDC-2043: matching title, ProCite104, Chiniak Bay species-composition description | Strong descriptive association. Other identical-title sources have different ProCite IDs/scopes, so do not merge them by title. Raw date122003/rights unresolved. |
| [17317857](https://zenodo.org/records/17317857) | FGDC-2725: unique matching full title; source date19810101 agrees with displayed1981-01-01 | Candidate association supported by title/date, not authenticated provenance. Institution creator fidelity and source rightsNone need QA. |
| [17317853](https://zenodo.org/records/17317853) | FGDC-2731: exact report-number/title match89-04 | Candidate association. Similar FGDC-2563 is report88-02 and must remain separate. Source1988-Present is not automatically report publication date. Later page fetch was rate-limited; no additional description match claimed. |
| [17317855](https://zenodo.org/records/17317855) | Unresolved here: public landing/API fetch unavailable | Preserve DOI; wait for owner inventory/metadata export. Parent previously saw restricted files; do not interpret inaccessible files as absent. |
| [15046283](https://zenodo.org/records/15046283) | No matching source title found for wellbeing record in this collection | Different apparent scope; no duplication/exclusion conclusion from title absence. Preserve existing record. |

## What is already safe to automate

Source hashing; exact-pattern grouping; deterministic normalization of supported calendar forms with raw values retained; preserving institutional names and author order; typed accepted links; full-identifier catalogue filenames; response/pagination validation; separate environment ledgers; existing-ID crosswalk preparation; and stale-approval checks are already covered by offline tests. Passing a parser is not proof of correct object semantics or rights.

After the five decisions, generate explicit source-hashed decisions, a small representative sandbox test batch under the agreed artifact policy, and a production correction manifest that preserves existing record IDs/DOIs. Human QA must precede any community draft-review submission because acceptance can publish. No uploads, community submissions, deletions, publication, merging or source/code changes occurred during this preparation.

## Approved searchable content classification

The approved project tags and reviewed file-role contract are documented in [content classification](../../content_classification.md). Internal states are metadata_only, data_included, mixed and unknown. Original descriptive FGDC XML alone remains metadata_only only with an explicit reviewed role declaration; unsupported evidence defaults to unknown. The feature is implemented and tested offline. It does not approve a deposited-object/rights/date policy or authorize uploads or publication.
