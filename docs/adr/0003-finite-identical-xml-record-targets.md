# 0003: One local record target per approved identical XML pair

Status: implemented for offline preparation; provider execution remains blocked.

The fixed inventory contains 456 source identities in 228 byte-identical pairs.
Brett approved one restored record per pair, retaining both original IDs, files
and provenance. The approval does not select a historical canonical filename,
resolve existing production identities or grant publication authority.

Each finite pair receives the content-addressed target ID `sha256:<raw-XML-hash>`.
The version-2 class artifact contract contains both actual filenames, sizes,
SHA-256 and MD5 values, and both independently checked v1 policy/artifact bindings. The
version-1 singleton contract and immutable source-status ledger are preserved.
Class preparation requires both complete metadata objects to agree, evaluates
both source semantics and retains additional policy/creator/date holds. Missing
or changed input produces a held diagnostic without a fabricated artifact.

Targets live outside legacy upload inputs. They preserve full common metadata,
source XML and class provenance without naming a primary source. All class
targets carry `upload_eligible=false`, pending production reconciliation and
reviewed class execution support. Revalidation rebuilds the entire object from
live pinned evidence; recalculating a digest cannot authorize altered input.

Legacy source-backed upload, resume, adoption, record review, verification, QA and
release paths refuse these identities before selected provider operations. The
guard combines supplied and current selected registry evidence, member IDs,
known raw hashes, renamed original bytes, class-shaped contracts and remote-ID
associations. Upload batches, the compatibility upload CLI and limited pre-upload
checks apply selection before client construction, so excluded aliases do not
block a selected ordinary singleton. Verifier construction preflights the full
successful registry before its later verification limit. Dormant replacement helpers
are retired; they cannot delete records if their old switches are enabled.

The boundary is intentionally finite. Generic account audits and raw transport
helpers are not a universal zero-network contract. No flag, environment variable,
legacy approval or invented reconciliation receipt enables class operations.

The migration is additive: prepare the separate target view and keep source files
and historical ledgers intact. Future execution needs a separately reviewed
production record/DOI reconciliation and class-aware durable create/resume,
two-file transfer/readback, QA and release contracts. Existing records and DOIs
must be preserved; choosing either member as a legacy singleton is not migration.

See the [artifact contract](../artifact_contract.md) and
[measured handoff](../readiness/2026-10-04/alias228_target_handoff.md).
