# Production readiness — October 1, 2026


Current source-identity adjudication is recorded in
[the reviewed three-record decision](../2026-10-03/production_identity_adjudication.md).
It supports 1238→17317855,2725→17317857 and2731→17317853 for correcting the same
existing imports; historical uploaded-byte/runtime provenance remains unknown.
Earlier initial observations below are historical. Source-identity, current
ownership/files/version, metadata corrections and publication QA remain separate;
no old-upload receipt is required to establish catalogue identity.

## Verified repository and offline state

GitHub PR 8 is open, ready for review, and unmerged at `6f792dfc2ff2d3021d7a38cba9f8ab3152d2d58e`. Main remains `4592f142b9c5be225254a0ad059c5cab7c6448ce`. The local implementation tree matches the published PR tree. Rechecked unit suite: 65 pass. Earlier network-blocked full suite passed. No live upload/publication validation is claimed.

A fresh network-prohibited census examined all 4,206 source XML files, without source changes or curator overrides:

- Six XML parse holds: FGDC-21, FGDC-3373, FGDC-3484, FGDC-4077, FGDC-4184, FGDC-4185.
- 2,876 transformation holds on publication date. Raw primary-date examples: Unknown 1,373; 122003 819; 72-88 thru 87-98 259; 1988 - Present 110; Planned 87; unpublished-material variants 107; September 2001 23. Some have plausible partial dates but the current contract does not normalize those without decisions. Observation ranges are not automatically publication dates.
- 1,321 further records fail the open/embargoed license requirement.
- Three pass the current offline contract: FGDC-767, FGDC-832, FGDC-854. This does not establish human approval, duplicate absence, or live compatibility.
- Among the 1,324 successfully constructed metadata payloads, license recognition is unresolved for all; three pass because their access rights do not require an open license. Rights were not evaluated for the 2,876 date-held transformations, so this is not a complete rights census.

The legacy upload log contains 4,086 rows, all with sandbox URLs and no explicit environment field. Archived transformed JSON and original XML ZIPs each contain 4,204 files. The expanded transformation directory has zero JSON files; no local QA manifest or scoped production upload ledger exists. None of these counts is a production-completion claim. Reconcile source/archive differences and old ledger IDs before importing state.

## Policy decisions that block production

1. Zenodo's current FAQ explicitly rejects fileless metadata-only records. Current upload_service disables files, and verifier/publisher expect an empty files list. Agree with PICES/Zenodo on the deposited object and a meaningful artifact policy. Original FGDC XML may be a suitable metadata artifact only if that policy is approved; generic placeholders are not a solution. That agreement will require a scoped implementation/verification update.
2. Determine whether each deposit is the SAME existing research object or a distinct metadata artifact describing it. Zenodo directs same-object uploads to use the existing DOI; a DOI for a different described object belongs in a typed relation. Do not mint duplicate identities or reuse a dataset DOI for a separate metadata artifact. Document this adjudication.
3. Community draft-review acceptance automatically publishes the record. Human QA must precede submission, not just precede the standalone publisher. Current CLI gates do not control manual UI submissions. Published-record community submission grants curators metadata view/edit access and does not transfer ownership or create a new record.
4. Establish authorized curator decisions for dates, rights and author identity/order. Bind corrections to original source hashes, reviewer and rationale; preserve source XML.

## Existing public records: retain identities and match before changing

The following public inventory was supplied by the parent reviewer and is not a fresh authenticated owner-dashboard capture. PICES production has six public records; sandbox public search had 4,198 results. Personal-account records outside the community remain unknown.

| Production ID | Proposed disposition pending exact source match/QA |
| --- | --- |
| 17317859 | Retain existing DOI; inspect/repair metadata after source match. Possible sea-otter/ProCite133 counterpart is sandbox375625/sourceFGDC-2057, but differing dates mean no verified duplicate claim. |
| 17317857 | Retain existing DOI; source match, file/rights/date/name QA pending. |
| 17317855 | Retain existing DOI; source match and QA pending. Files are restricted, not proven absent. |
| 17317853 | Retain existing DOI; source match, file/rights/date/name QA pending. |
| 17317851 | Retain existing DOI; source match, file/rights/date/name QA pending. |
| 15046283 | Retain existing DOI; March2025 spreadsheet record has a different apparent scope. Do not treat it as an accidental catalogue test without source evidence. |

The five October2025 records were reported as CC0/Dataset, with four identical 102-byte metadata.txt placeholders. These observations flag QA, not proof that every record is erroneous or safely replaceable. Brett's latest direction is correction and duplicate prevention, not deletion. No deletion is planned.

## Next sequence and approvals

1. Export a read-only owner inventory including personal-account published records, unpublished drafts, exact IDs/DOIs and community membership/pending submissions. This environment exposes no supported authenticated browser/Zenodo connector, so account enumeration is blocked here; do not access cookies, tokens or secret files as a substitute. Arrange a supported signed-in browser handoff or a dashboard export.
2. Build a source-to-existing-record crosswalk using FGDC/source IDs, full DOI/handle and source evidence. Include same-work/version/subset adjudication; titles alone are insufficient. Capture each intended correction and preserve the existing DOI.
3. Resolve artifact/DOI/community workflow policy with PICES before bulk preparation. Identify the authorized reviewer and allowed license/date decisions. No blanket CC0 or guessed date correction.
4. Produce a small approved representative batch, with raw-source hashes, exact existing IDs or explicitly justified new IDs, normalized metadata, artifact hashes once policy agreed, QA, duplicate evidence and proposed action. Reconcile legacy state into environment-scoped ledgers only from verified evidence.
5. Obtain exact-scope approval for corrections/community submissions and, separately, new draft creation/publication if needed. For community inclusion, disclose the record list and curator edit access; community acceptance is a separate state to verify.
6. Verify live results and preserve audit evidence. Only after actual completion prepare the WG52 activity report. October6 review can assess readiness and policy decisions; no unverified promise that all records will be finalized by then.

Official references:
- https://support.zenodo.org/help/en-gb/1-upload-deposit/36-do-you-support-metadata-only-records
- https://help.zenodo.org/docs/deposit/create-new-upload/
- https://help.zenodo.org/docs/share/submit-for-review/
- https://help.zenodo.org/docs/share/submit-to-community/

No original source changes, token reads, account access, merge, upload, publication, deletion or community submission were performed in this readiness check.

## Added user requirement: searchable metadata-only flag

The production curation manifest must distinguish metadata-only, data-bearing and unknown deposited content using reviewed file evidence. Original FGDC XML alone is descriptive metadata and must remain metadata-only for this purpose. External underlying-dataset location/availability is a separate attribute. The approved keyword/query contract is now implemented offline; see [content classification](../../content_classification.md). Reviewed declarations are required and default to unknown. No invented field or production edit is authorized by this planning entry.
