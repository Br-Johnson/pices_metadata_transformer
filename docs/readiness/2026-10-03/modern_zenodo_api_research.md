# Modern API source research and offline contract

The pinned Zenodo source supports a modern draft route, but this review does not establish deployed Sandbox write support or explain the legacy HTTP500. No live provider request, write, credential/private-run read or repository edit occurred. This is research for an offline adapter contract, not an execution grant.

The checkout is Zenodo v26.6.1 at `7111dde7d1ebf6f64bc695edf7ad8cce5bfa1ac7`, with lock SHA `aa05d6aef7de46bae73d9eb342c53180b0143c331d51a5a92dde1341d933d84f`. It pins RDM Records35.2.0 at `d4a4ef21ef5cd99b6d1350b537c82581799296a3`, Records Resources11.1.1 at `12ca933194d9f5c4ea15eacc72ec220ee2cec197`, Drafts Resources11.0.3 and OAuth2Server6.1.0. The two registry distributions were checked against the exact lock SHA values; all inspected source files and line anchors are bound in the paired JSON.

`POST /api/records` is the slashless modern create route. RDMRecordResource inherits draft-aware RecordResource creation, which calls RDMRecordService. LegacyRecordService also inherits that service, so changing routes could bypass legacy conversion while retaining the same failing backend. The source supports the route and includes a [localhost demo](https://github.com/zenodo/zenodo-rdm/blob/7111dde7d1ebf6f64bc695edf7ad8cce5bfa1ac7/scripts/new_api_flow.py); neither proves current deployment behavior.

The [official Zenodo documentation](https://developers.zenodo.org/) documents legacy deposit creation and published-record search/read. It does not provide a modern POST contract. Its “new Files API” describes legacy bucket uploads. It documents deposit:write for nonpublishing writes. Examined modern source requires authenticated identity and owner/review permissions, but declares no route-specific scope; the locked OAuth REST loader verifies with an empty required-scope list. Modern deployed scope requirements and sufficiency of the existing write scope therefore remain unverified. Keep current scope gates.

Use explicit `Accept: application/vnd.inveniordm.v1+json`. Zenodo replaces application/json record serialization with legacy-shaped JSON. Modern responses use string ID, `parent.access.owned_by.user`, `is_published`, first-draft status, `pids`, and a files object. UI display fields must not substitute for canonical metadata. The complete minimum metadata schema requires title, resource_type.id, publication_date, and one or more creators[].person_or_org. Personal creators require family_name; organizational creators require name. Publisher, description and rights are optional schema fields. Empty/incomplete drafts may still receive 201 and returned validation errors, so201 alone does not prove metadata correctness. No creator type, date or rights inference is approved for PICES production records.

The source-backed upload phases are:

| Action | Route | Status |
|---|---|---|
| Create | POST /api/records |201|
| Metadata update | PUT /api/records/{id}/draft |200|
| File initialization | POST /api/records/{id}/draft/files |201|
| Content upload | PUT /api/records/{id}/draft/files/{key}/content |200|
| File commit | POST /api/records/{id}/draft/files/{key}/commit |200|

The [pinned Zenodo REST tests](https://github.com/zenodo/zenodo-rdm/blob/7111dde7d1ebf6f64bc695edf7ad8cce5bfa1ac7/site/tests/resources/test_record_file_permissions.py) confirm these statuses in a local application. The demo incorrectly asserts content 201, disables TLS verification and publishes/edits; those parts must not be copied. Local transfer is pending before commit and completed afterward. Draft record readback has files.entries keyed by file key; the file-list endpoint returns an entries array. The file endpoint exposes key/status/size/checksum and self/content/commit links. All links need the same-host, same-ID, exact-key checks; redirects stop.

A canary testing metadata PUT plus one file requires **3 POST + 2 PUT**, with independently spent intent/counters for initialization, content and commit. It cannot reuse the legacy one-create/one-metadata-PUT/one-file-PUT ceiling. Modern DOI reservation, if needed, adds `POST /api/records/{id}/draft/pids/doi` (201): **4 POST + 2 PUT**. Legacy prereserve_doi is synthesized by its serializer; do not manufacture modern pids.doi from that pattern or silently remove a DOI criterion.

The paired JSON defines an offline request/state/test contract, not runnable provider code. Its illustrative metadata is the public source fixture, not unique identity or authorization. Any eventual test needs a separately reviewed synthetic packet and grant, finite counts/lifetime, initial title marker, durable returned ID/PID before further writes, exact metadata/file readback, and an unchanged retry with no writes. All earlier uncertain legacy creations, receipts and consumed budgets remain held. There is no runtime fallback, POST reset, publish/delete/newversion, production adapter or gate waiver here.

Source inspection and static AST checks confirm init 201/content 200/commit 200/read 200; no Zenodo/Invenio integration suite was executed. Checkout remains clean. The remaining questions are deployed modern support/scopes/schema/vocabulary, the revised mutation budget and DOI contract, and explicit provider dispatch authorization after an independently tested adapter.

Paired [contract/evidence packet](modern_zenodo_api_contract.json). Original local paths record research provenance; pinned source URLs, versions and hashes provide portable evidence.

Independent review is recorded in [the review receipt](modern_zenodo_api_review.json).
SHA256: `484b2580ff84e3313d4576446d2bbb6af4bd90870f34f5e7d1da10cc08c39b9d`


The parent reported that the Sandbox token has write access and no email-verification
option appears. Email visibility is nonblocking here. This research neither
attributes HTTP500 to account setup nor requires an account change. The separate
provider executor owns the already authorized creation-window reconciliation;
root performs no authenticated request, write, retry or private-run read.

The research does not change runtime commit `9fdb393af11b38fea29dde64bd9569cee9ce3746`
or its independently passing 21 focused diagnostic contracts. All existing receipts,
failed-create state, durable identities, budgets and production protections remain
unchanged. No grant, namespace, marker or runnable adapter is introduced by this
document.
