# Five retained-import correction preparation

The five complete current metadata beforeimages from the reader's saved
2026-10-03 17:26:37–44UTC captures are now independently received through a
standalone Library text transfer. All303lines are present, with has_more=false.
The16494-byte file matches the supplied SHA-256
`3f8b6da19071af5a0e454497794f8eb3dbc8b509a28f15097c78d4aa2391f923`;
all five complete metadata hashes are independently recomputed. Existing record
IDs, version DOIs, captured owner and exact creator/contributor values match the
supplied evidence. Root made no provider request. The earlier ZIP download
failure remains historical evidence and no longer blocks metadata comparison.

The standalone transfer contains metadata, not current file lists or file bytes.
Those exact file/version bindings remain with the reader and must be transferred
from existing evidence before a live correction is frozen. Do not repeat GETs,
substitute October1 public file lists for the latest captures, or reopen the
already supported same-import identity adjudication.

The paired preparation JSON independently binds all five local source bytes,
prepared payloads and metadata after-images to source2bf5f8a and completed report
`6213c25a1f3d71cdb08ae19a1ca91762fdad5b3f11524ed7ed137f1b7edb044e`.
Three assessed supported metadata hashes match; two held after-images are locally
reproduced proposals, not assessed eligibility. No source/creator/date/rights
status or original XML changes here.

| Source | Retained record /DOI suffix | Exact current date | Exact metd | XML-artifact date candidate | Source status |
|---|---|---|---|---|---|
| FGDC-1238 SeaMARC |17317855|1990-01-01|20010308|2001-03-08|Contributor access held|
| FGDC-2043|17317851|1220-01-01|20040723|2004-07-23|Source-supported|
| FGDC-2057|17317859|1220-01-01|20040723|2004-07-23|Source-supported|
| FGDC-2725|17317857|1981-01-01|19980203|1998-02-03|Source-supported|
| FGDC-2731|17317853|1988-01-01|19980713|1998-07-13|Departmental republication scope held|

All five version DOIs retain prefix`10.5281/zenodo.` plus the listed record ID.
**The two confirmed date blockers are2043/17317851 and2057/17317859, each carrying
1220-01-01.** The narrow metadata-only preservation proposal also carried1220;
that is not an acceptable date correction. Their replacement underlying-work
publication date remains unestablished. The exact current metadata hashes and
creator/contributor beforevalues are now bound in the paired schema2 receipt.

No invented date is needed for the already reviewed XML-artifact date role: these
five exact days are metadata creation/last-update dates, not underlying dataset
publication or a new2026 repository date. In particular,2004-07-23 is not an
established publication date for either underlying work. A coherent XML-artifact
candidate uses that date together with the source-backed artifact title/type,
creator/distributor roles and provenance; it is not a silent date-only substitute
on a narrow existing-resource correction. Preserve literal citation pubdates:
1238=`1990`,2043/2057=`122003`,2725=`19810101`,2731=`1988 - Present`.
Do not silently interpret122003 as December2003, borrow a coverage date, or reduce
an interval to a day. If a candidate intends the **underlying resource's**
publication date instead, that is a different after-image needing source-specific
date meaning/precision evidence; keep2043/2057 held for that mode. Showing the
other three current dates for preservation comparison does not newly establish
January1 or precise publication dates. Neither comparison is an executable patch.

All five current objects have license=`cc-zero` and lack access_conditions;
1238 is restricted and the other four are open. The paired receipt retains
exact current and prepared creator/contributor arrays and hashes every differing
metadata field. These are comparisons between current metadata and the separately
prepared XML-artifact candidate. They do not authorize removing current fields
that are absent from the source-prepared object, changing DOI/PID/version bindings,
or changing rights or attribution without the complete actual after-image review.
Field-value hashes use the same canonical UTF-8 JSON serialization as the full
metadata hashes; they are not raw-string hashes.

SeaMARC's reported missing access_conditions can be prepared from the existing
frozen after-image exactly:

> Descriptive metadata are publicly readable. Original XML files remain restricted while reuse rights are unresolved. Permission to rehost is USER_ATTESTED; no new license grant is asserted.

Retain access_right=`restricted`, blank license and all four literal “Check with
Contributor” constraints. This missing-field proposal records uncertainty and
rehosting scope; it does not clear1238.2731 likewise retains its “Requests for
one or two pages…” and conditional departmental republication access hold. The
[821 questions](remaining_source_scope_questions_821.md) cover these distinct
Contributor and ADF&G decisions. No creator/contact role is inferred from the
remote beforevalues; source-backed candidate roles stay attached to the
XML-artifact mode rather than being inferred as authorship of the underlying work.

## Exact file-preserving action choices

**Metadata edit:** retain the same record/DOI and every verified original file,
including placeholders. Freeze only reviewed field deltas against the exact
current metadata hash, keeping immutable identity/PID/version/file bindings.
No file upload/removal belongs in this action. Zenodo documents metadata editing
of published records and says that publishing those changes retains the DOI.
This describes the available approach; no production edit or release is approved
here. [Official metadata-edit guidance](https://help.zenodo.org/docs/deposit/manage-records/).

**Adding original XML:** prepare a separately reviewed new-version and two-file
contract that retains/imports the original placeholder/file as one role and binds
the untouched XML as the other, with per-file basename/size/checksum/source/rights
evidence and exact readback. The new version has its own persistent identifier;
preserve the original five version records/DOIs and document version relations.
Do not delete the old records or relabel an old DOI as a new distinct artifact.
Zenodo documents new versions for changed files and import of prior files; the
API returns the original resource with a latest_draft link, which needs exact
identity/origin/version validation. No such write is authorized or implemented
by this preparation. [Official version guidance](https://help.zenodo.org/docs/deposit/manage-versions/),
[API action contract](https://developers.zenodo.org/#new-version).

The current one-XML upload contract does not cover the two-file/version action.
Existing source approval, account credentials or publication authority supplies
no permission to delete originals. Keep1238/2731 access-held, exclude poster10042430
and unrelated15046283, and preserve all current beforevalues until exact reviewed
corrections and the separate provider/release gates are satisfied.

[Exact source/after-image preparation receipt](five_import_correction_preparation.json).
The [previous independent review](five_import_correction_preparation_review.json)
continues to bind the earlier checkpoint; the schema2 evidence update receives a
separate bounded review. PR10 code is merged at
`e3fde4b4fa9e30435b6b1322536aca276eebc22b`, with reviewed runtime
`dc351b071df53c6d44f01491694916c1d44bd9f2`. Modern live execution remains
unapproved; both prior uncertain create allowances remain permanently spent.
