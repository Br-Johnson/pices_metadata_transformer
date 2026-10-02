# Reproducible metadata-only migration: draft, review, publish

Production records remain drafts until documented human QA. This policy supersedes the older auto-publish suggestion in AGENTS.md. Running a pipeline is not evidence of publication or successful remote verification. No production migration was performed while implementing these changes.

## Canonical paths and responsibilities

`fgdc_to_zenodo.py` transforms original XML without modifying it; `validate_zenodo.py` supplies the shared metadata contract. `upload_service.py` owns both uploader entry points' durable draft lifecycle. Environment-scoped `OutputPaths` separates sandbox and production ledgers, duplicate inventories, verification and publication reports. Legacy unscoped ledgers are deliberately not imported: reconcile them with endpoint and source evidence first. Transformation output is shared, so changing it invalidates approval hashes.

`publish_records.py` is the explicit publication entry point. Production requires `--qa-manifest`. Inline production publication is disabled. Automatic duplicate replacement is retired; deletion is never a recovery strategy. `verify_uploads.py` compares submitted metadata and the explicit reviewed file contract; legacy records without an artifact policy retain the empty-file contract. Audit summaries count unique ledger records and explicitly describe local ledger evidence; they do not substitute for remote verification.

## Repeatable sequence

1. Preserve and identify the original FGDC source collection and Git revision. Transform and validate offline. Ambiguous dates, unknown rights, and oversized notes must be resolved before upload. Dates are calendar validated within 1600–2100; this fixed policy is not a guess about historical records.
2. If human correction is necessary, pass `batch_transform.py --decisions FILE`. Decisions are keyed by FGDC ID and include the original raw `source_sha256`, reviewer, rationale and reviewed_at, plus supported metadata overrides (`publication_date`, `creators`, `license`). A changed source invalidates the decision. Never repair the source XML silently.
3. Perform the explicit pre-upload inventory for the selected environment. Missing, failed, expired or wrong-environment inventory blocks creation. Inventory includes owned drafts as well as published records. Treat search limitations as limitations, not proof of absence.
4. Upload metadata-only drafts through either existing uploader CLI. The shared service writes creation intent before POST and persists the returned draft ID before metadata update. Known IDs resume; successful identical submissions skip. Changed metadata blocks reuse. An ambiguous creation response stops for reconciliation rather than replaying POST.
5. For uncertain creation, an operator must identify the draft using authenticated read-only evidence in the correct environment. Save the GET response with endpoint, retrieval time, status and explicit confirmed source ID/source hash/metadata hash. Use `python -m scripts.reconcile_draft --help` for offline reconciliation. Empty drafts require affirmative human source correlation; title similarity alone is insufficient.
6. Verify remote drafts and generate a new manifest with `python -m scripts.qa_manifest --output OUTPUT --production --manifest FILE`. Review source fidelity, dates, creators, rights, relations and metadata-only status. Fill reviewer, time, rationale, all checks, and duplicate adjudication for each record. Approvals bind to source bytes, prepared metadata and draft ID. Publication also compares the live remote metadata. Never copy approval to changed content.
7. Publish only the specifically approved manifest through `publish_records.py --production --qa-manifest FILE` with the intended output directory. Confirm remote state; unconfirmed publication remains explicit in the ledger. Re-run verification and retain reports, source hashes, manifest and software revision.

## External repository duplicate evidence

`python -m scripts.matching.evidence --help` ingests saved read-only search snapshots; it does not contact repositories. Its envelope records repository, endpoint, retrieved_at, scope/query, HTTP status, format, body and declared scope completeness. Supported response structures are checked. HTTP 200 HTML, HTTP failures, malformed responses, Identify-only OAI responses and incomplete pagination cannot mean checked-no-match. Candidate matches remain deferred for human review.

Use DOI/persistent IDs and source IDs first, then metadata similarity as evidence. Classify same work, alternate version, derived subset or different dataset. Record the evidence and publication rationale; same-work publication requires an explicit metadata-reference decision. No automatic merge or deletion is implemented. An unavailable service requires an explicit human waiver with evidence and rationale, never a fabricated no-match finding.

Independent review observations found AquaDocs' candidate OAI route returned an Angular HTML shell and candidate server API routes returned HTTP 503. These observations do not prove endpoint deployment, coverage or absence of duplicate PICES records. No live AquaDocs integration or confirmed cross-repository duplicate is claimed. DOI/handle examples from ODIS are identifier examples only.

## Validation and remaining limits

Regression tests use temporary fixtures and mock clients, covering rights fidelity, calendar and creator handling, scoped state, uncertain POST, restart recovery, QA hash invalidation, verification, JSON-LD and external-response validation. They establish offline behavior, not compatibility with every live Zenodo normalization or repository deployment. Review the existing source exceptions and actual live drafts before authorizing a migration. Existing unrelated operational/metrics scripts have not been comprehensively redesigned.

The independent follow-up review is recorded in [swarm review](reviews/2026-09-30/swarm_review.md). Inventory pagination must have structurally valid, unique positive integer record IDs. Publication and recovery require an explicit matching deposition ID, recognized state and files list; absence of a field is not proof of a metadata-only draft. One deposition ID belongs to one source in each environment ledger. Publication holds the shared ledger lock throughout fresh approval validation and the remote operation. Catalogue filenames use a digest of the entire DOI to avoid suffix collisions.

## Searchable deposited-content status

Follow the approved [content classification contract](content_classification.md) when creating source-hashed curator decisions. Exported project keywords distinguish metadata-only, data-included, mixed and unknown; file-role evidence remains internal. Do not infer data availability from an FGDC XML attachment or external link. Keyword exclusion does not prove the remaining records contain data. These classifications do not resolve the separate deposited-artifact/DOI/rights/date policy or authorize publication.

## Staged rollout gate (2026-10-02)

See the [20-source offline audit](readiness/2026-10-02/source_audit.md) and its reproducible evidence. Technical validation is not source-specific rights or publication approval. No sample is cleared for live creation yet. The [opt-in original XML artifact contract](artifact_contract.md) is now implemented and offline tested. Activation requires reviewed per-record object, rights and date evidence; live sandbox compatibility is still pending. Do not substitute dummy files. Zenodo’s documented editable draft state `inprogress` is accepted only when `submitted` is explicitly false; `unsubmitted` remains supported for compatibility. Sandbox and production are separate, and existing production IDs/DOIs must be reconciled before creating anything new.
