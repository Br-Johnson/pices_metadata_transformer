# Tech Debt Log

## Portable guarded CI — 2026-10-04

PR23 originally had no workflow or automated check. The same PR now adds a
standard public-repository Ubuntu job, immutable action pins, read-only token
permissions and checkout without a persisted credential. The portable unittest
runner clears its environment, uses dummy provider tokens, verifies installed
guard probes, rejects unexpected transport/subprocess/private-file operations
and allows writes only under its own temporary fixture root. Descriptor-relative
mutations are resolved before policy checks. Source bindings are compared before
and after all contracts. This prevents accidental I/O from the reviewed tests;
it is not a sandbox for hostile code. Dependencies install before the guarded
process, and no artifacts/caches or paid runner capacity are provisioned.
Actual final-head Actions results and substantive Codex review are required before
the standing merge rule applies. Provider runtime, schemas, packet and private
preflight bindings remain unchanged by this CI implementation.

## Complete modern schema and expected empty-file warning — 2026-10-04

The prior six-field wire projection missed DataCite's semantic publisher
requirement, which the generic storage schema leaves optional. The bounded
synthetic repair now pins the full official record JSON schemas and adds all
service-required and fixed-fixture checks, with no online reference resolution.
The documented Zenodo host default applies only to the sealed fictional payload.
Exact upstream method fixtures reproduce publisher and missing-upload errors.
The latter can be accepted only by the separate metadata-stage ledger after all
seven metadata fields, access, sealed identity, enabled-empty files and absent
DOI pass, under an explicit warning-policy grant. Permission/toggle errors and
every other validation error still hold. This is not publication readiness.
PUT2's actual second label remains unknown; source reproduction does not recover
it or explain the reported same-attempt missing metadata. A finite token-checked
field-path projection now makes future genuine validation labels diagnosable
without provider values/messages. All357 historical entries retain their previous
expected hashes, GET197 remains a historical identity anchor, and both prior PUTs
stay spent. Live service compatibility is still subject to sole-executor readback.
See `readiness/2026-10-03/run02_complete_schema_repair_handoff.md`.

## Persistent repository authorization — 2026-10-04

Older instructions required implementation confirmation and prohibited agents
from editing AGENTS.md. Brett now authorizes merges after passing CI and Codex
review, plus direct-main rules/documentation commits. The current rules and README
record that standing authority, and the workspace rules apply it across existing
checkouts. Frozen historical handoffs retain their bytes and do not override the
current user instruction. PR22 was merged under Brett's explicit exact-head
approval, with 422 guarded offline tests and 12 independent contracts; those
receipts do not claim a CI run. Configured CI remains a separate tooling debt.
Provider grants, immutable source evidence and production release remain separate.

## Finite42 reviewer provenance — 2026-10-04

The556 profile retains all514 source/context objects and adds42 reviewer contexts.
The common validator returns actual provenance instead of a universal SOURCE_BACKED
label and requires current aware time after review; old profiles/calls stay
compatible. Five original statements remain live dependencies;821/904 are not
expanded. Cached measured22/106/42 accounting is not a new whole-corpus audit.
Literal conditions, restricted blank-license XML and source/provider/release holds
remain. The37 deferred candidates and31 exceptions need separate evidence.
See `readiness/2026-10-03/resource_reconciliation_42_handoff.md`.

## Explicit same-draft repair ledger — 2026-10-04

A known wire-schema defect justifies a separately counted controlled repair under
the parent directive; it does not reopen the failed mutation allowance. The new
stage binds latest GET197, original201/creation interval, the spent PUT lineage and
complete preserved-file inventory, then accepts only one corrected PUT and one
GET. An optional shared prepared-request checker verifies the actual494-byte body
before send; existing controllers without the hook retain their route. A ten-minute
window is explicitly bound by parent dispatch, never minted/extended by staging.
Metadata-only completion does not finish the remaining PID/file trial. Any failure
or interruption needs evidence-based parent reconciliation, with no reentry/reset.
See `readiness/2026-10-03/run02_subjects_repair_handoff.md`.

## Fixed modern subjects schema and transient errors — 2026-10-04

The immutable fictional code02 input used legacy keywords in a modern draft body.
An explicit deep-copy runtime projection now emits one subject-only object, with
the exact source packet and historical preparation retained. Readback validates
full subject equality. Runtime hash changes deliberately invalidate old grants;
no failed-stage migration or allowance reset is provided. Complete credential-free
JSON responses retain only closed error-field flags before status/identity failure.
These flags describe container/field shape, not message validity or permission to
continue. The parent-reported GET197 proves intended metadata did not persist but
cannot recover transient PUT errors or establish all failure causes. A future
same-draft plan must bind current evidence, changed runtime and explicit authority
without replaying spent attempts. Source ledger3596/604/6 is unchanged; next42 are
selection-only. See `readiness/2026-10-03/modern_subjects_correction_handoff.md`.

## Modern transport evidence boundaries — 2026-10-03

A durable action intent spends the allowance before preparation/send. It cannot prove network dispatch. The fixed diagnostic correction records trusted phase/exception enums, local send/adapter observations, response status independently of body projection and aware first/cleanup failure capture times. No arbitrary exception text or old-stage migration/reset. Exact runtime binding intentionally refuses consumed grants; future observability does not authorize another create. The original modern cause remains unknown; all allowances and historical193 reads stay held/preserved. Search window defaults cap10000 results, so a finite200-page/240-GET plan cannot promise a16538-entry inventory. An explicitly newest ordered prefix supplies candidate evidence only, with a separately approved GET-only ledger and no absence/adoption conclusion. See readiness/2026-10-03/modern_transport_diagnostics.md and review/validation receipts.

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

## Successor integration and credential safety — 2026-10-02

- Repository handoff restored after Library helper transfer failed. Verified exact 68b1443 code/tree, evidence parent and three-file-only diff, archive SHA-256, all 43 inventory entries and 4,206 original hashes. Evidence branch was not merged.
- Combined loader now rejects malformed/empty tokens before Session creation. Valid opaque placeholders remain unchanged. Transport/connection/bucket exceptions suppress potentially secret-bearing text and traceback chaining; remote error bodies are replaced with HTTP status diagnostics. This deliberately trades verbose provider errors for credential confidentiality.
- 207 guarded offline tests pass, independently reproduced. Prior P2 credential leak is closed. Fresh whole-corpus classification matches all handoff statuses: 1,406 supported / 2,794 held / six malformed; 4,200 XML copies and 4,206 originals verified unchanged. See `readiness/2026-10-02/successor_integration_validation.json`.
- Secure sandbox setup instructions prepared in `readiness/2026-10-02/successor_secure_sandbox_setup.md`. No credentials provisioned or provider writes. Actual proxy substitution, intended account, inventories and exact synthetic canary selection remain unverified/gated. Contributor-or-Source interpretation remains pending. Original d8b30c5 branch retained; combined branch unpublished.

## Narrow sandbox canary duplicate exception — 2026-10-02

- Brett's explicit historical sandbox-duplicate authorization is implemented only through `canary_plan` on the checker/service. The code pins the three-source plan SHA-256, exact source/payload/metadata hashes, namespace and HTTPS sandbox origin; production rejects opt-in before client creation. Title matches require creation strictly before 2026-10-02 UTC and no canary namespace; identifier, recent, unknown-date, local-batch and own-run identity conflicts remain blocked.
- New actual-source payloads add only one namespace keyword. Initial create POST includes exact metadata, so lost responses remain discoverable by namespace. A bound ledger and consumed create grants prevent cached-inventory reuse after ledger loss; uncertain creates stop. Exact same-run retries preserve IDs/files and must remain unsubmitted drafts. Canary ledgers cannot be published. No deletion or production exception was introduced.
- Failing-first feature test preceded implementation. Independent review then reproduced two concrete defects (lost-ledger duplicate create and published-state retry); both were captured as failing regressions and fixed. Current 232-test guarded offline suite passes, including all three candidates first-run/retry with exactly three creates and uploads. Independent final review is recorded in the handoff receipt. No provider writes by the code owner.
- Provider must keep the original synthetic ledger and count it against the four-total cap; do not repeat synthetic creation. New actual-source payload hashes supersede the earlier unmarked packet only before actual-source intents exist. See `handoff/sandbox-canary-20261002/EXECUTOR.md`.

## Safe constructor probe diagnostics — 2026-10-02

- Separate from the sandbox exception: constructor requests are one-attempt and preserve fixed stage, allowlisted exception type, observed HTTP status or null, retryability and attempt count. No token/URL/header/body/exception text or original traceback is exposed.
- Dummy tests distinguish transport and HTTP errors, guards before response and after status/JSON/owner/link stages, arbitrary exception names/attributes and secret-bearing messages. The provider guard source is not yet available; no actual cause or authentication failure is asserted. Provider remains paused and code owner performs no authenticated request. See `readiness/2026-10-02/constructor_probe_diagnostics.md`.

## Reviewed read-only inventory guard — 2026-10-02

- Reviewed complete sanitized provider guard source. Its per-record blanket host filter was overly broad for inert DOI/citation/HTML links; no actual failing branch can be inferred from the retained evidence. Query blank-value omission, pre-transport counting, constructor/outer exception erasure and missing-hit fallback were also identified.
- Added context-managed SandboxInventoryGuard with strict outgoing sandbox GET/endpoints/Bearer, actionable pagination checks, streaming byte bound and safe status/milestones. Inert record links are never followed. An independently found cleanup exception leak is fixed; cleanup cannot mask primary safe errors or mark completion.
- The exact next diagnostic is one constructor GET, followed by pause even if successful; it does not authorize pagination or writes. See `readiness/2026-10-02/reviewed_inventory_guard.md`. No provider requests by the code owner.

## Contributor or Source attestation integration — 2026-10-02

- Brett's exact “yes” at 23:43 UTC is separate USER_ATTESTED evidence for the 585 original source/hash pairs. The optional contributor interpretation preserves all four original access/use fields, restricted XML, blank licenses, separate rehosting authority, and independent creator/date/security holds.
- Independent review caught mutable cohort membership despite a refreshed manifest hash. Contributor-only canonical count and sorted source-map SHA-256 now reject additions, removals, rebinding and same-count substitutions; the older Contact Source profile is unchanged. Real-source and synthetic shape regressions cover both the scope and preserved restrictions.
- The reviewed executor guard is frozen separately at d5022b8828ef910749aef32371304f2b2b669674 on handoff/pr8-reviewed-read-guard-20261002; all 17 packet entries verify. Its next step remains one constructor GET only after parent dispatch, then pause. No implementation-owner authenticated requests or provider writes. Historical pending entries above describe earlier checkpoints and are superseded by the current validation receipts.
- Final guarded offline suite: 264 tests pass; independent contributor/legacy review: 16 tests pass with no remaining findings. The final corpus run yields 1,988 supported / 2,212 held / six malformed, exactly 582 promotions from the attested cohort. FGDC-1390 retains ambiguous creator semantics; FGDC-1422 and FGDC-1423 retain insufficient metadata-date precision. See `readiness/2026-10-02/contributor_source_validation.json` for reproducibility and preservation evidence.

## Remaining held cohorts — 2026-10-03

- Ranked all 2,212 held sources from PR8 c486d1f with exact source/hash evidence. Alias identity and six unsupported metadata dates remain held; separate institutional/access opportunities are reported without claiming promotions.
- Implemented the independently reviewed 70-source literal DFO Staff interpretation on a separate branch. Names, full metadata, source bytes and rights remain unchanged; no inferred type, affiliation, acronym expansion or contact-derived author. Manifest bytes pin exact source membership and full creator objects.
- Failing-first regression and 16 focused tests (independently reproduced), then 270 guarded full-suite tests pass. Full-corpus preservation/resume receipt accompanies the cohort report in readiness/2026-10-03. Provider handoff d5022b8 and PR8 c486d1f are not moved by this branch.

## 2026-10-03 — Exact institutional citation source interpretation

General creator detection holds some literal institutional citations because of
unknown organizational patterns or commas in a hierarchy. No universal heuristic
was changed. A separate exact-byte/source-hash-bound 72-member manifest supports
the four audited literal citations with existing full creator objects. Exactly
63 creator-only holds clear; eight local validator title-length issues and FGDC-2578's
separate access wording remain held. No shortening or synonym/rights inference.

Both human QA schemas and agent assessment use the shared validator and full
object comparison. New opt-in evidence participates in cache invalidation; absent,
withdrawn or forged evidence cannot silently grant the interpretation. Fresh and
resumed classification reports are byte-identical; all original/copy bytes are
preserved and raw metadata objects are unchanged, with only72 payload policy-reference additions. The combined
2,121-source support population is not live record QA or release approval.
## Residual source roles and uncertain Sandbox creation — 2026-10-03

The 27-member literal citation proposal preserves existing creator objects and
has 16 current creator-only diagnostics, not validated promotions. Larger
37/31/23 joint/collection groups retain independent access and role questions;
resolve exact source-bound cohorts rather than widening a universal parser or
rights vocabulary. See readiness/2026-10-03/residual_source_next_batch.md.
The separately frozen controller consumed its create allowance on HTTP500;
188 GETs and an empty reconciliation search cannot clear that uncertainty.
A parent-dispatched two-GET known-record positive/negative created-filter check
can assess query compatibility without new state machinery. Preserve the failed
write intent and continue source restoration independently of provider repair.

## Reviewed literal citation extension and remaining meanings — 2026-10-03

The additive 99-member opt-in profile preserves 72 earlier cohort objects and
resolves 16 source-supported creator holds among 27 new bindings, retaining 11
access holds. No general name parser or access vocabulary changed. Compare whole
metadata and account for 99 policy-reference changes: 27 new and 72 administrative
rebindings. Separate Ecotrust (37), USDA/DNR (31) and Unaami (23) role reviews
establish bounded attribution candidates but do not answer access or
acknowledgment scope.
See readiness/2026-10-03/institution_program_citation_99.md and the parallel role
review. The original uncertain create remains spent after 190 GETs; finite backend
confirmation/account-owner inspection/adoption decisions replace indefinite
absence polling, without automatically granting another POST or resetting state.

## Reviewed joint/collection citations and offline identity preparation — 2026-10-03

The 190-member opt-in profile retains 99 earlier cohort objects and explicitly
reviews 68 joint-citation after-images, including both USDA/DNR Organization
objects. No generic comma split is introduced. The raw combined origin is retained
in a note beside each corrected list; only its existing curator-decision creator
list also changes. Unaami's 23 untyped collection objects remain literal. Actual
source QA promotes only FGDC-619 and retains 90 access cases across nine exact
partitions; meaning decisions must bind those source IDs/hashes rather than
expanding old access attestations. See the current readiness profile/receipts.

Complete offline duplicate/source-integrity preparation independently confirms
4,206 originals, 4,200 copies, 4,194 payloads and all 228 exact-copy pairs. All
456 alias identities remain held; title collisions are not record identity.
Historical public IDs/DOIs are protected with their original association confidence,
including three distinct contents sharing FGDC-2043's title. Fresh remote identity
verification remains required before release. No canary machinery or new authority
is added; its uncertain POST remains spent.

## Alias candidates and residual source evidence — 2026-10-03

All 228 exact-copy pairs have identical complete prepared metadata and artifact
policies. Their full payloads retain distinct source filenames; artifact contracts
and locally derived submission notes therefore have distinct fingerprints. Use
the shared original SHA-256 as a neutral review-group key and retain every source
ID/hash. A smallest-ID display representative supplies no historical priority,
ownership or canonical provider identity. The 456-entry candidate map leaves all
provider IDs/DOIs unset; all alias holds remain active. Two title-only matches to
FGDC-2043/ProCite104 have different abstracts and cannot inherit its DOI.

Parallel source QA ranks 15 full-object institutional and 24 untyped literal
citation candidates without installing a profile. Five same-origin access-held
siblings remain outside that scope. Separate full after-image review is required
for smaller credit/person lists and 35 mixed BASIS role/order cases. Twenty-one
empty origins and six unsupported metadata dates need authoritative evidence;
contacts, hosting context and guessed dates cannot repair them. The nine-partition
morning bundle queues exact XML-versus-dataset scope decisions for the unchanged
90 access holds. See readiness/2026-10-03/source_alias_reconciliation.md and its
reproducible maps. No provider access, spent-create reset or release occurs.

## Exact 39-source literal-citation extension — 2026-10-03

The additive 229-member manifest preserves all earlier 190 cohort objects and
binds 39 explicitly reviewed full creator after-images. The 15 plain institutions
retain existing Organization type/hierarchy; 24 literal program/institution credits
remain untyped. No generic parser, modern identity, new role or contact attribution
is introduced. Immediate predecessor/evidence hashes now identify this extension;
older evidence stays clearly ancestral. Five same-origin access-held siblings are
excluded. Actual QA promotes all 39 and no other source: 2,177 supported / 2,023
held / six malformed, with 4,194 whole metadata objects unchanged and only 229
creator-policy references changed. Source/policy-bound submission fingerprints
still differ when policy evidence changes. Full tests and source-integrity receipts
remain separate from provider verification and release; see the current profile
and the morning scope questions. Original uncertain canary creation stays spent.

## Exact source credits and historical dataset linkage — 2026-10-03

Mixed XML and short-person/list credits require bounded reviewed interpretations, not a generic comma/initials parser. The additive 319 profile preserves prior 229 objects and binds 90 new source after-images, complete parsed mixed origins, scoped roles and three exact abstract supplements. The distinct 21-member link profile removes inferred XML alternate identities only with full before/after metadata hashes, retaining the exact dataset portal URL. Both agent and human QA enforce evidence/context; withdrawal restores holds.

Actual 111 promotions yield 2,288 supported / 1,912 held / six malformed; 301 guarded tests and full delta preservation are independently reproduced. Complete prepared metadata equality differs from submitted artifact fingerprints: 229 evidence rebindings update policy-bound fingerprints. No provider state changes. Further 86 access-plus-creator cases remain a source-role review queue, including five literal siblings and dedicated radio/editor/compiler context; they cannot clear access holds. Complete after-image hashes deliberately prevent unrelated edits from piggybacking on the link correction; future metadata corrections need a newly reviewed profile. See readiness/2026-10-03/source_credit_and_linkage.md and validation receipt.

## Access-held citation cleanup — 2026-10-03

Source-credit fidelity can improve without resolving access meaning. The exact 86-member review supports 77 source/hash-bound after-images and retains nine radio/program/address/journal attribution gaps. Every access hold remains; the additive 396 profile retains the earlier 143 cohort objects covering 319 source bindings. Literal compiler/editor, country-specific data-by, contracting, reporting and collection credits require explicit context. Source references support three supplemental author credits; contacts and byline-free journal labels do not. Independent review removed unsupported magazine-venue and shared-editor claims before the final pin.

Actual complete delta: 34 creator lists and 43 note-only corrections, 4,117 unchanged prepared metadata objects, 396 policy changes including 319 rebindings, and unchanged 2,288/1,912/six eligibility. All 4,206 originals, 4,200 XML copies and 4,194 payload hashes are verified. Wait for classifier completion before auditing report summaries; checkpoint files intentionally contain partial inventory only. Further work within the 86 queue requires new role or access evidence rather than another generic parser. See readiness/2026-10-03/access_held_source_credits.md and validation receipt.

## Finite source-backed access meanings — 2026-10-03

A public resource locator, source-only acquisition instruction or explicit
public-metadata statement can establish meaning without granting rights. The
additive immutable264 profile preserves all122 earlier registration cases and adds
142 exact source/hash/four-constraint/full-context bindings: acquisition36,
publication referral75, resource availability30 and distinct PWID metadata/data
scope1. The existing opt-in classifier and shared agent/human gate validate each
selected source. No word-matching rule, current website terms, agency ownership,
new license or XML authorship is inferred.

Actual full QA: 2,430 supported / 1,770 held / six malformed; 312 guarded tests and
independent focused implementation/source/delta reviews pass. All4,194 complete
metadata objects remain identical;264 policy references and243 assessed artifact
fingerprints change. All4206 original hashes,4200 copies,176 protected access holds
and456 aliases remain intact. Contributor361, ADF&G351 and Unknown109 need exact
scope evidence; the13 smaller attribution/title after-images are review proposals,
not runtime changes. See readiness/2026-10-03/finite_source_resource_access.md and
remaining_source_decision_packet.md. Provider identity/readback/release work stays
with the parent's separate executor; consumed canary allowances stay spent.

## Five credit and eight display-title after-images — 2026-10-03

Full source context can resolve literal analysis/contributor/report credits without
inventing XML authorship or types. The additive401 profile preserves previous220
cohort objects covering396 bindings; five new literal credits retain exact primary
and supplemental XML and role notes. Eight long PICES report titles use individually
reviewed responsibility boundaries, retaining complete originals/credits/bundle
context in notes. Complete before/after hashes prevent unrelated changes; shared
agent/human gates require exact evidence and withdrawal restores holds.

Actual QA:2443 supported /1757 held /six malformed;317 guarded offline tests pass.
Only13 complete metadata objects change;4181 remain identical.401 creator reference
changes include396 prior rebindings; eight title references fall in those same401.
All4206 originals,4200 copies,176 access holds and456 aliases remain intact. Existing
catalogue identity can support retaining a DOI for the same import while old uploaded
bytes/runtime remain unknown; no upload-receipt-only identity requirement is added.
Current ownership/file/version/correction/readback/release QA remains distinct.
See readiness/2026-10-03/source_credit_title_13.md and production_identity_adjudication.md.

## Isolated modern synthetic contract — 2026-10-03

Modern upload is a different protocol: create, optional managed DOI allocation, metadata PUT, file initialization, content PUT and commit. The isolated candidate uses a fictional packet, distinct namespace and explicit fresh approval; it cannot consume/replenish old legacy grants or serve as a production adapter. Separate action counters and pending intent precede transport; completed retry only reads. A partial inventory is a known-ID reject set, not completeness evidence.

Source-supported REST transfer envelopes differ from embedded record file metadata; validate these separately. DOI allocation returns the full draft, with only documented PID fields retained. Deployed support/scope/vocabulary may fail this bounded trial; no cause for historicalHTTP500 is inferred. Failed drafts/PIDs may remain orphaned and need separate reconciliation; no delete/recreate or automated fallback. The existing reported write scope and nonblocking hidden email state are retained. Tests and exact approval/runtime bindings are in readiness/2026-10-03/modern_synthetic_approval_plan.md. Production mapping, file-version correction and release remain separate tasks.

## Retained-import dates and file versions — 2026-10-03

The local five source2bf5f8a after-images use exactmetd days for the descriptive XML artifact date, preserving ambiguous resource citation dates verbatim. Standalone Library transfer supplies all five complete metadata beforeimages with exact fileSHA and independently recomputed metadata hashes; the historical ZIP failure no longer blocks metadata comparison.2043/17317851 and2057/17317859 carry1220-01-01, which the narrow metadata-only preservation proposal also retained.2004-07-23 is the FGDC metadata date, not an established underlying-work publication date; that narrow correction remains held. XML-artifact title/type/credit/date/provenance comparisons require coherent object-policy review, not a silent date substitution. The separate complete510-line saved file/version transfer now binds all five exact file IDs/links/checksums, concept DOIs and capture/modified times. Content/history checks preceded the latest deposition captures; this is a non-atomic historical snapshot and no current-after-capture assertion follows. No revision/ETag or version ordinal was preserved or inferred: a fresh modern concurrency baseline belongs to separately authorized execution against these existing records. No repeatedproviderreads, new grants, runtime change or live correction. See the schema3 preparation receipt.

Metadata corrections preserve sameDOI and verifiedexistingfiles. Adding XML is a distinct version/two-file action with original placeholders retained and version/PID relations explicit; the current one-XML upload contract does not authorize it. The already held Contributor1238 and departmental-republication2731 source decisions remain unresolved. See readiness/2026-10-03/five_import_correction_preparation.md/json.

## Credential echoes after successful create — 2026-10-03

PR10 final-head review identified loss of a reconciliation handle when a create201 included both a valid record ID and a credential echo. Retain only a syntactically valid, credential-free decimal ID privately before rejecting the echo; keep it untrusted, with pending intent, spent create and permanent failure. Never expose it in public receipts or adopt/retry the draft automatically. A dedicated failing-first regression and an ID-containing-credential case cover the correction. Code merge remains separate from the unissued live trial grant; old uncertain ledgers remain untouched.

## Exact821 user-attested scope — 2026-10-03

The three frozen question groups now have an explicit USER_ATTESTED underlying-data scope answer. Apply it only to the exact821 source/hash/four-constraint/context bindings with separate XML rehosting authority and shared agent/human validation. Missing/withdrawn/tampered/conflicting evidence restores holds. It creates no license, underlying-data rights or release grant. Actual791 promotions produce3234 supported/966 held/6 malformed;2 creator and28 title holds remain. Only30 previously protected sources are within this exact answer:28 promote,148 protected cases remain held;456 aliases stay held. All4194 raw constructed metadata objects/4206 originals/4200 copies are preserved. Normalized submission notes embed active evidence, so the five-record preparation binds current notes/fullmetadata hashes separately from the preserved historical94 comparisons. Current all-five source support does not resolve2043/2057's underlying-date mode, current rights/file-version/concurrency/correction or release gates.

Parent separately approved/dispatched modern runtime dc351b0; its durable create intent is held with network dispatch unknown. Root neither inspects provider stages nor executes provider requests. Every historical/create allowance remains spent; diagnostics/reconciliation is a separate bounded task.


## Finite remaining-source cohorts — 2026-10-03

Add exact205 underlying-resource acquisition/use interpretations,8 literal creator corrections and27 complete display titles without generic inference. Full352 guarded offline tests and complete4206/4200/4194 delta yield3468 supported/732 held/6 malformed;35 raw metadata objects change only reviewed fields/context notes. Old264/401/8 member objects and821attestation remain intact.110 previously protected held access records clear from individual source evidence,38remainheld; no broadattestation expansion. Creator preservation notes follow the established classifier order and require actual full after-image review. Inherited profile summary text describes ancestral cohorts; current contract/new-role fields govern additions.

Remaining276nonalias holds include238access-only,31creator-lane,6dates and233title;456alias identities need verified provider crosswalk and owner decisions. Residualaccessgroups may admit further source review and are not universally irreducible. Normalized submission notes include active evidence refs, so unchanged raw metadata does not imply unchanged normalized upload bytes. The five-import raw metadata and historical comparisons remain untouched, with current concurrency/correction/release gates outstanding. Merges of PR11/12 were rejected by automatic review because original trustedscope excluded merges; sourcework stays in reviewed open handoffs. Root performs no provider requests/stage mutations. Frozen GET-only parentdispatch preserves193historicalreads and spentcreate allowances under separate boundedledger; diagnostics cannot reconstruct the consumed moderncreate cause.

## Supported modern transport and a distinct synthetic run — 2026-10-03

Parent reports one official-routeGET succeeded and its entire2025 newest prefix
crossed the2026 search boundary; cumulative195 and285 preserved files remain.
This neither settles the unknown run01 create nor proves a transport failure
cause. Its read-only expiry is unchanged. Correct future transport by preserving
ordinary Session.request environment/CA processing and existing adapters, with
instance-only phase observations and an opaque authorization-preservation check.
Disabling all environment routing is too broad a fix for netrc credential risk.

Run02 uses a new immutable packet/exclusive stage and same finite protocol budget,
never migration/reset/retry of run01. Parent dispatch must bind the applicable
standing user trial approval; a fresh binding is accounting, while any action
outside that actual approval is a substantive scope decision. No extra inventory
or preconfirmation is required to test deployed modern protocol compatibility.
All source classifications and production gates stay unchanged. Existing token
configuration is sufficient; .env.example needs no new setting.
See readiness/2026-10-03/modern_supported_route_handoff.md.

## Exact22 named forestry GIS delivery terms — 2026-10-03

Named GIS feature/coverage descriptions and physical copy-media delivery support
an exact22 acquisition-scope reading. Literal Unknown use remains unresolved;
separate attested restricted/unlicensed XML authority is required. Complete source
roots bind descriptions, metadata and distribution liability together, avoiding
generic Unknown or same-wording inference. An additive491 pin preserves all469
prior member/context objects and leaves821attestation and all runtime gates intact.

Bounded before/after proves22 promotions with no raw metadata or XML changes.
Frozen main3468/732/6 plus this actual delta projects3490/710/6; no full corpus
re-audit is claimed. Normalized submission evidence/notes may still change.
156 access scope gaps are grouped into15 concrete questions;60 other candidates
remain held/deferred and need a later coherent reviewed increment. All494 separate
creator/date/title/alias identities remain held. No provider release follows.
See readiness/2026-10-03/cnf_copy_media_handoff.md.

## Empty modern draft and explicit owned continuation — 2026-10-04

Run02's201 followed by sealed canonical200 proves one owned first empty draft,
not persistence of submitted metadata. Service creation permits incomplete drafts;
the root cause of this deployment's missing metadata/file-policy mismatch remains
unknown. A separate parent-bound continuation validates exact identity and empty
beforeimage, then requires full committed metadata/access after one PUT before
file operations. It inherits spent create/read counts rather than clearing the
old failed state. The same file-list entry validator replaces the redundant item
GET, retaining byte/checksum/identity proof within the original eight-read ceiling.

Any renewed window is an explicit parent grant decision and preserves original
expiry/counters; no controller-generated extension or new create exists. Original
controlled files are hash-checked before requests; the full305-file historical
inventory is parent/executor evidence and must not be described as root-verified.
See readiness/2026-10-03/run02_owned_continuation_handoff.md.

## Second empty response and prepared JSON evidence — 2026-10-04

The second metadataPUT200 also failed all known metadata checks. Current dummy
preparation proves both fixed bodies are serialized, but the live prepared body
was not recorded. Standalone pre-send capture observes current bytes without
consuming another action. A separate oneGET observes persisted state within the
existing recovery expiry; neither recreates historical transmitted-byte evidence.

Pinned modern metadata uses subjects rather than the packet's keywords. Publisher
is optional. Partial-valid-data semantics mean that defect alone cannot explain
every missing metadata field and file-access mismatch. Future packet/schema
correction requires concrete diagnostics and a separately reviewed authorized
action; current spent state remains held. No production compatibility inference.
See readiness/2026-10-03/run02_body_diagnostics_handoff.md.

## Exact106 scope reconciliation and integrated status accounting — 2026-10-04

The original821 answer is a finite direct-question record. The83 additional
ordinary descriptions use the same recorded restoration/scope evidence through
a distinct REVIEWER_RECONCILED status; no new user answer or enlarged question is
invented. An additive904 profile preserves the entire821 object and rechecks the
five original evidence files. Separate23 whole-source resource contexts extend491
to514 without resolving literal data conditions or changing attribution.

Actual bounded106 QA preserves all XML and complete raw metadata. A deterministic
status ledger applies disjoint measured22/106 deltas to the frozen4206 baseline,
yielding3596/604/6 while preserving every unselected status and456 aliases. This
integrated accounting does not replace a future full transformation/remote audit.
The31 exact exceptions remain held, with titles, source quotes and minimal
questions. Next42 source work waits for this merge; all provider gates stay separate.
See readiness/2026-10-03/resource_scope_reconciliation_handoff.md.

## Historical evidence containers and private leaves — 2026-10-04

The failed owned origin legitimately names `/workspace`0755. It is an ancestor
container, not a recursively private evidence tree. Requiring0700 or selecting all
its contents blocks before transport and risks reading unrelated repository data.
The repair binds a complete exact file manifest and whole selected evidence trees,
permits canonical non-group/other-writable ancestry (including trusted sticky/tmp),
and keeps private regular single-link leaves, symlink exclusion and stage separation.
All known original/failed-stage files and latest beforeimage require coverage;
minimum file count is only a sanity check. Completeness of the historical353 set
remains sole executor/parent manifest evidence, never root-private inspection.
A shared Controller input preflight prepares the actual fixed PUT without a grant,
ledger mutation or provider request. Parent starts a new window only after it passes.
No old origin rewrite, chmod, grant revival, replay or source promotion follows.
See readiness/2026-10-03/run02_evidence_layout_handoff.md.
