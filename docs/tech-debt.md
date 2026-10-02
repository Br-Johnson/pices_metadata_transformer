# Tech Debt Log

## 2025-10-11

### Upload log drift
- **Observation:** `python3 scripts/batch_upload.py --sandbox --output-dir output --batch-size 5 --limit 5 --interactive` left `output/state/uploads/upload_log.json` unchanged (`len(entries)=2`, last timestamp 2025-10-11T02:29Z) despite four successful uploads in Batch 1.
- **Impact:** Monitoring and audit tooling depending on the log will miss sandbox activity, masking partial failures.
- **Next step:** Inspect `scripts/batch_upload.py` logging flow; ensure both registry and upload log stay aligned in interactive mode.
- **Resolution (2025-10-11T22:15Z):** `_append_to_upload_log` now runs for every outcome; `upload_log.json` shows seven entries after sandbox retest.

### License mapping gap
- **Observation:** FGDC-2284 failed with `Invalid license provided: open`; transformation is currently emitting `license: open`.
- **Impact:** Record cannot reach Zenodo until the license maps to a supported vocabulary (`cc-zero`, `cc-by`, etc.).
- **Next step:** Review license normalization rules in the transformation pipeline; either update the mapping or fall back to storing the raw value in `notes` when uncertain.
- **Resolution (2025-10-11T22:14Z):** Folded “open access / no restrictions” phrases into the `cc-zero` mapping; FGDC-2284 now publishes successfully.

### Enhanced metrics regression
- **Observation:** 2025-10-11T22:33Z run of `python3 scripts/enhanced_metrics.py --input output/data/zenodo_json --output output/enhanced_metrics_sandbox.json --log-dir logs` failed for every record with `calculate_comprehensive_metrics() missing 1 required positional argument: 'file_path'`.
- **Impact:** Enhanced metrics JSON reports 0 files processed, so downstream quality dashboards lose coverage.
- **Next step:** Inspect `scripts/enhanced_metrics.py` and the calculator call signatures; reintroduce the `file_path` argument (or adjust the API) and rerun to restore metrics.
- **Resolution (2025-10-11T22:34Z):** Directory helper locates FGDC attachments and passes paths to `calculate_comprehensive_metrics`; sandbox metrics now cover 4,204 records.

### Legacy verification entries
- **Observation (2025-10-11T23:03Z):** `python3 scripts/verify_uploads.py --sandbox --output output --log-dir logs --limit 20` failed for FGDC-1/FGDC-10 because the script still references `transformed/zenodo_json/...` paths removed after the output reorg.
- **Impact:** Verification success rate capped at 90%; legacy depositions linger in registries without accessible source files.
- **Next step:** Backfill or migrate those early records (copy JSON into `output/data/zenodo_json/`) or prune stale entries from `upload_log.json` before future verification runs.
- **Resolution (2025-10-11T23:09Z):** Migrated FGDC-1/10 log paths to `output/data/...` and regenerated FGDC-1 JSON with both creators; verification now passes 100%.

## 2025-10-15

### Split creator tokens
- **Observation:** Zenodo sandbox records show creators split into individual words (e.g., “National Oceanic”; “Office”) instead of the expected organization name for NOAA-sourced metadata.
- **Impact:** Published metadata misrepresents provenance and breaks downstream duplicate detection relying on exact creator strings.
- **Next step:** Revisit the transformation step that tokenizes organization names; ensure legacy FGDC `origin` values map to a single `person_or_org` entry.
- **Resolution (2025-10-15T05:21Z):** Updated creator parsing treats organization strings as atomic; iteration loop sample (`FGDC-1001.json`) now preserves the full NOAA organization label.

### Placeholder text leakage
- **Observation:** Description and purpose fields emit literal placeholders such as “No abstract was givien” and “No purpose was givien,” including a typo from the FGDC source.
- **Impact:** Public records contain low-quality messaging and visible spelling errors; reduces curator trust and usability.
- **Next step:** Normalize placeholder phrases during transformation—either drop them, replace with empty fields, or move the original FGDC notice into Zenodo `notes`.
- **Resolution (2025-10-15T05:21Z):** Transformer now replaces placeholder abstracts/purposes with neutral guidance (`Abstract not provided…`); verification via iteration loop confirmed sanitized output and notes.

### Publisher fallback
- **Observation:** Despite injecting the PICES publisher in the DTO, published sandbox records still list `Publisher: Zenodo`.
- **Impact:** PICES branding is missing in the public metadata; contract requirements to credit the organization are unmet.
- **Next step:** Confirm whether the legacy deposition API allows overriding `metadata.publisher`; if so, update the upload payload. Otherwise, document the limitation and explore post-publish patching options.
- **Status (2025-10-15T05:21Z):** Transformer now forces `metadata.publisher = "North Pacific Marine Science Organization"`; need to run the next sandbox upload batch to verify the UI reflects the change.

### Stale upload verification targets
- **Observation:** Iteration loop verification (2025-10-15T05:21Z, `--limit 10`) reports `record_not_found` for FGDC-3754 through FGDC-3758 despite entries in `upload_log.json`.
- **Impact:** Upload registry may reference depositions that never completed or were purged, inflating verification failures and masking real regressions.
- **Next step:** Audit `upload_log.json` and Zenodo sandbox to reconcile these entries; remove or refresh stale registry records before the next publication pass.
- **Resolution (2025-10-15T05:24Z):** Purged FGDC-3754–FGDC-3758 from `output/state/uploads/upload_log.json` and `uploads_registry.json`. Re-run verification to ensure the iteration loop exits cleanly.

### Missing sandbox credentials during regression sweeps
- **Observation (2025-10-15T06:07Z):** `pre_upload_duplicate_check` and `verify_uploads` abort with `Secrets file not found: .env` when run from a clean environment.
- **Impact:** Regression gate cannot exercise duplicate detection or upload verification without a local `.env`; downstream steps rely on their reports for audit parity.
- **Next step:** Document the requirement to populate `.env` with sandbox tokens before running the gate; consider adding a guard that emits a clearer message or supports read-only dry runs.

## PR 8 independent review follow-up

Durable draft ownership, complete inventory validation and publication locking were consolidated in shared helpers rather than copied into CLI wrappers. Offline evidence ingestion preserves malformed-response provenance. Remaining operational work: reconcile historical unscoped ledgers, adjudicate ambiguous source rights/dates, validate live API normalization, and resolve AquaDocs availability before treating external coverage as checked. No CI workflow is configured; the 65-test network-blocked suite is locally reproducible, but a future CI setup should enforce these critical paths.

### 2026-10-02: Source audit and live canary blockers

The 20-source audit is deliberately stratified and uses strict raw parsing; it does not exercise XML recovery or prove live compatibility. Technical schema passes can still have ambiguous date semantics or unestablished artifact rights. The 4,206 files contain 228 exact byte-copy pairs; preserve source aliases and reconcile identities rather than assume one deposit per filename. The current empty-file contract needs an explicit meaningful-artifact policy and tested adaptation before Zenodo live writes. No authenticated sandbox access is exposed in this execution environment. See `readiness/2026-10-02/source_audit.md`. Documented editable `inprogress` drafts are now accepted only with `submitted:false`.

### 2026-10-02: Explicit original XML artifacts implemented offline

The version-1 opt-in contract now supports reviewed original XML bytes without silently attaching files to or reclassifying legacy records. Exact file/policy/source bindings are shared by upload, readback, reconciliation, verifier and QA/publication. An uncertain file response resumes the same draft and uses remote checksums to avoid repeat transfer. Canonical UUID/host/deposition-ID bucket validation and disabled redirects protect environment-scoped transfer. Independent review closed bucket identity/traversal and final metadata-readback gaps with mock regressions. Remaining gates are source-specific object/rights/date/creator decisions and authenticated sandbox service validation. The current legacy empty-file path remains for compatibility, not an assertion that Zenodo accepts new fileless deposits.

### 2026-10-02: Delegated record QA and separate release

Human-per-record review is superseded by delegated agent record QA. Schema2 binds exact source/payload/artifact/draft/savedresponse/duplicate evidence and honest reviewer/run/revision provenance. Deterministic supported profiles may pass; ambiguous or unsupported profiles remain explicit holds. Independent process review and risk-stratified samples bind the approved population. A separate human release manifest binds exact QA content and bounded record selection; QA alone never publishes. Historical schema1 human approvals are supported as record QA without silently granting new release authority. Actual full production QA and authenticated sandbox transport remain unexecuted.

### 2026-10-02: Collection classification and cache integrity

Source-only classification now covers all 4,206 files without inventing remote evidence. Resume binds every Python rule dependency and validates prepared payload/original-copy integrity before reusing constructed results. Independent tests reproduce output deletion/tampering and rule invalidation. All 4,200 parseable sources remain held under the narrow explicit XML-rights profile; six malformed sources require reversible recovery with original bytes preserved. See `readiness/2026-10-02/collection_audit.md` for counts, ten independent semantic samples and the precise sandbox authentication boundary. Technical passes do not grant record QA or release.

### 2026-10-02: Evidence-backed routine hold reduction

Exact source titles now remain unchanged when only an artifact suffix would exceed limits; escaped exact source abstracts preserve scientific comparison signs and placeholders. Technical passes rise from4,089 to4,131, while all publication holds remain. Official PICES exporter code copies dataset constraints into metadata constraint fields;4,073 sources exhibit matching template evidence. Rights scope and creator roles require a shared provenance decision rather than4,200 inferred licenses or contact-to-author substitutions. See `readiness/2026-10-02/hold_reduction_plan.md`.

### 2026-10-02: User-attested restoration authority

Brett confirmed permission/instruction to rehost the lost GeoNetwork metadata. Exact-source-bound attestation replaces the blanket absent-authority hold, without assigning a CC license or claiming independent verification. Restricted-file preparation supports687sources;3,513 remain held and6 malformed. Public notes preserve rawXML and remain subject to platform metadata reuse terms; file download restriction does not conceal them. Live record QA, sensitive/source exceptions, alias reconciliation, sandbox auth and production release remain separate.

### 2026-10-02: Revalidate evidence during classification and approval

Isolated review reproduced two lifecycle gaps: editable cached verdicts could falsely promote held sources, and historical schema-1/schema-2 human approvals did not recheck changed external restoration-authority manifests. Classification now reconstructs each row from original XML and reruns source assessment while reusing verified transformation bytes. All artifact approval paths revalidate any restoration-authority digest, exact source membership and restricted blank-license conditions. Human semantic adjudication remains supported; agent QA, independent program review and separate release requirements remain unchanged. Failing-first regressions and complete offline collection verification accompany the recovery. The original checkout and shared branch are not part of this isolated repair; publication requires a reconciled single writer.

### 2026-10-02: Bounded citation-origin hold reduction

The exact 31-source Washington Sea Grant Program cohort supports one verbatim institutional citation origin, without supplying XML authorship or a new license. Recognition is confined to source citation classification/QA. A ten-record payload comparison exposed unwanted contact/distributor changes from altering the shared organization detector; the final helper leaves that detector unchanged. A known institution with appended identities stays ambiguous. Ten then 31 source-only preparations pass, with only creator type and its explicit decision note changing; 46 focused/surrounding tests and four final contact regressions pass. Existing full-suite evidence is reused. See `readiness/2026-10-02/sea_grant_cohort.md` for source bindings, unresolved access/creator/date/identity questions and the arithmetic cohort delta. This local batch is not pushed and has no remote verification or release approval.

### 2026-10-02: Exact source-bound access wording adjudication

Brett's 18:26:45 UTC statement interprets Contact Source access as underlying dataset acquisition. The additive optional policy reference binds the exact 1,004-source cohort and user provenance, alongside existing restricted-file restoration authority. Matching raw use text is a context guard, never a new license. Separate metadata restrictions, creator/date/relation/alias holds and stale approval evidence remain fail-closed. The assessment uses its actual post-attestation time rather than backdating to the old controlled baseline; this deliberately updates all constructed policy/inventory timestamps and derived hashes while all 4,194 raw metadata objects remain unchanged. Failing-first and lifecycle controls, 147 offline tests and fresh/resume verification yield 196 newly supported preparations, not publication approvals. Semantic resume reassessment remains intentional (29.512 seconds fresh, 27.214 resume). Final independent review, live compatibility and release evidence remain separate. See `readiness/2026-10-02/contact_source_cohort.md`.


### 2026-10-02: Cloud checkpoint integration and grouped corrections

The cloud checkout was moved from the PR7 merge to exact PR8 base `35b01a2`
before validation. The saved main-branch onboarding checks are not evidence for
this branch. The two transferred code trees and 41 inventory-listed artifact
hashes were verified; source census independently matches all 4,206 originals.
The original-source and upload-limit fixes passed 160 guarded offline tests and
an independent bounded diff review before local integration.

Source lookup remains relative to repository-root `FGDC/`; callers must run
from that root, and concurrent source writers must remain stopped. Conflicting
prepared copies fail closed rather than being silently repaired. Pending
selection validates the full prepared directory before limiting the caller
subset. These constraints are documented; they are not implicit permissions to
rewrite source bytes or remove records.

The compiler and source-only QA serve distinct purposes: exact membership and
field precedence make corrections reproducible, while a narrow reviewed source
interpretation is still needed for a mixed creator citation. Raw schema success
is not semantic approval. Historical sandbox duplicates may be acceptable for a
future labeled cohort, but its explicit routing is not implemented; current
inventory, new-run retry and production DOI safeguards remain in force. No
provider operation or credential transfer is part of this repair.


### 2026-10-02: Explicit database-registration interpretation (local only)

The exact 122-member source context describes obtaining/downloading data via
underlying research databases. A pinned SOURCE_BACKED interpretation preserves
all raw constraints and complete metadata, while separate USER_ATTESTED XML
rehosting authority remains mandatory. It does not generalize the Contact Source
attestation, assign a license, infer creators, or register with any database.
The 78 access-only cases become supported; 23 ambiguous and 21 empty creators
remain held. Original abstract markup is bound by parsed-subtree hash plus text
rather than falsely assumed to be a plain leaf. Each full source hash is pinned.

New production-goal authority does not supply operational evidence. Connectivity
and credential provisioning are absent; current client reads cwd .env only.
Before live creation, enforce protected historical source-to-record identities;
before publication, explicitly verify immutable record/DOI identity. Published
metadata editing and richer external duplicate adjudication require separately
tested routes. Never use draft recovery for published IDs or replace unknown
state with a new record. See the local production critical path and planning
manifest; the published PR8 code remains frozen while GitHub review quota blocks
a substantive final-head automated verdict.
## 2026-10-02 successor token compatibility

- Environment tokens now precede the legacy cwd `.env` fallback; explicit client tokens retain highest priority. Values stay opaque so NetworkSecret placeholders reach existing Bearer headers unchanged. No new token parser or resolver is introduced.
- Validation: 189 tests pass using the existing venv with inherited socket/DNS blocking; only local Git revision reads and the existing curation CLI test subprocesses are permitted. Six new tests cover precedence, mode isolation, legacy fallback, error non-disclosure, and mocked session/bucket headers. All 4,206 original hashes remain unchanged. Initial harness attempts blocked required local subprocesses; the final inherited guard permits these specific commands.
- Archive transfer remains blocked: Library resolved version 0 of `pices-successor-68b1443.tar.gz`, but the current supported helper returned `library file transfer failed: download failed`. No archive imported, no reviewed batch reimplemented. Retry supported materialization after transfer access is restored.
- Credential provisioning and the exact bounded canary plan remain separately gated. No credentials configured, provider writes, production changes, PR pushes or merges. The 585-record Contributor/Source interpretation remains pending; do not extend the Contact Source interpretation automatically.
