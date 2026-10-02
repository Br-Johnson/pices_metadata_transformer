# Original FGDC XML artifact contract

This is an explicit per-record option, not a migration of legacy records. The deposited object is the original XML metadata artifact, resource type `other`, with no underlying research data included. Its DOI identifies that artifact. Referenced work identifiers belong in reviewed relations; do not assign another work's DOI to the XML object.

## Activation and evidence

Provide `artifact_policy` alongside `metadata` in a transformed JSON, or inside the existing source-hash-bound curator decision supplied to the transformer. The transformer carries it to the top-level result and applies its explicitly chosen resource type. The upload preparer validates the contract before any create. No new API fields are submitted.

A [synthetic contract example](../contracts/examples/original_xml_artifact.json) documents the shape; its rights/date evidence applies to no real source.

Required policy fields:

| Field | Required value or meaning |
|---|---|
| `schema_version` | `1` |
| `object_kind` | `original_fgdc_xml` |
| `resource_type` | `other`; must agree with submitted metadata |
| `source_sha256` | SHA-256 of the untouched original file bytes |
| `date_semantics` | `source_metadata_date` or `metadata_artifact_publication`, explicitly reviewed |
| `date_evidence` | Evidence supporting the exact submitted date and its meaning |
| `rights_evidence` | Permission/license/access evidence applicable to the XML artifact |
| `reviewer`, `reviewed_at`, `rationale` | Honest human or authorized agent preparer provenance |

Also provide the existing `content_classification`: complete reviewed inventory with exactly one file, its actual original basename, role `descriptive_metadata`, evidence, reviewer, review date and rationale. This yields `metadata_only`. The preparer exports `pices-metadata-only` and an explicit description/notes statement identifying the XML object. Scientific tags and underlying source content remain preserved.

The option does not infer a license or select a date. Existing metadata validation and production evidence-bound record-QA and separate release checks still apply. A textual evidence field is documentation supplied by the reviewer, not independently verified permission. Do not fill it with a placeholder to authorize a real upload. Policy/source mismatches, an unsupported resource type, or a conflicting file inventory block preparation.

## Identity, transfer and recovery

The version-1 `artifact_contract` records source identity, policy and classification hashes, original filename, byte size, SHA-256, MD5 for remote checksum comparison, and descriptive role. Its digest is included in submitted metadata notes, so the duplicate-inventory metadata fingerprint also changes when the artifact policy or file changes. The contract is persisted in the environment-scoped ledger before remote operations and copied into the QA manifest. These are additive optional fields; absent policy retains the previous empty-file behavior without reclassifying legacy deposits.

Upload persists a returned draft ID before metadata/file operations. It reads the exact draft and checks any existing files before writing. Missing XML is uploaded from an immutable temporary copy of the original bytes. A matching file on retry is left in place; unexpected files or checksum conflicts block rather than overwrite or delete. The final GET must confirm draft state, submitted metadata and exact file inventory/checksum/size before upload is marked successful. Lost attachment responses therefore resume the same draft without another create or file upload if readback already confirms the file.

Bucket transfer requires HTTPS, the selected environment host, matching deposition ID and a canonical UUID bucket path. Credentials are sent in a header; redirects are disabled and transfer timeouts bounded. No credential values are logged or read by the offline tests.

Verification and production QA/publication use the same exact file contract. Changed source bytes, policy or file roles invalidate the old ledger/approval binding. Remote checksum/size changes or extra/missing files block verification and publication. Production also rechecks approved metadata and files after publication before reporting verified success. If the service has published but the final readback differs, the operation reports failure requiring human reconciliation; it does not repeat the publish POST.

## Operational boundary

No real records have been attached, published or deleted while implementing this feature. Live compatibility is pending a secure authenticated sandbox session and fresh scoped inventory. Authentic publication policy is separate from already authorized nonpublishing technical tests. Use the [three-candidate decision packet](readiness/2026-10-02/candidate_decisions.md), at most three approved draft canaries, readback and an unchanged rerun before expansion. Do not submit those drafts to a community: acceptance can publish them. Production remains draft until supported record QA and separate explicit release.

Offline coverage is in `tests/test_artifact_contract.py`: attachments and exact readback, idempotent rerun, lost responses, missing/corrupt/foreign files, source/policy changes, QA binding, mocked production final drift, reconciliation, and bucket identity/environment/redirect checks. Original sources are never edited.

## Optional source access interpretation

Version-1 XML policies may additionally reference `source_access_interpretation` as `{manifest_path, manifest_sha256}` for the exact [Contact Source cohort](readiness/2026-10-02/contact_source_cohort.md). This additive field does not change legacy records or grant rehosting, a license, dataset access or release authority. Separate source-bound rehosting authority, restricted attachments and a blank license remain required. Source QA and all human/agent approval paths recheck the manifest digest, exact source and paired source constraints, attestation provenance and post-attestation assessment time. The existing policy fingerprint binds this reference, so changed evidence requires renewed artifact/QA bindings. The classifier's optional `--access-interpretation-manifest` flag leaves the conservative access profile intact when absent.
