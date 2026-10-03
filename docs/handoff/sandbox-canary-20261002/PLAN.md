# Bounded sandbox canary candidates

Code: `9379fd8f13255b95ffab7a2c6735525e1d5cf1de`; tree `3079d38a9be151b85e15350404948f2f0e9b908d`.

Planning only: secure provisioning, authenticated account verification, fresh inventory, successful synthetic-first transport test and exact final selection verification remain required. No provider action has occurred.

| Source | Profile | XML bytes | SHA-256 |
|---|---|---:|---|
| FGDC-100 | baseline | 6111 | `fc1921212cfe534217440582eba6811d1ac10b4c2183ea41cfc5e3a77b240352` |
| FGDC-1839 | citation | 6554 | `db588248e233bdb0d309ef3387c1f79ed363b94dbcd44a44131f24d4daeecc35` |
| FGDC-3682 | registration | 4619 | `1400516e035cdb9c68cc0b5590ebdae4429ab3945497d50170fb8e3b823e06c1` |

Maximum three actual-source drafts, serially, after one separately verified synthetic draft. All are selected from the 1,406 supported preparations, technically validated and reassessed offline. Protected historical sources and exact-copy aliases are excluded. Authentic titles and source metadata remain unchanged except for the pinned canary keyword; full payload/metadata hashes are updated. Historical duplicates require the explicit sandbox-only code-pinned exception; all own-run identities stay strict.

## Expected readback

- Returned positive integer draft ID belongs to the authenticated intended account and sandbox host
- Draft is unsubmitted and never done/published; no publish/community-submission action
- Metadata matches expected_metadata_sha256 using existing compare_metadata semantics; source-backed metadata unchanged
- Exactly one original XML attachment, exact basename/size/MD5; downloaded bytes match pinned SHA-256
- Source SHA-256, artifact policy/contract and payload hash match selection before any write
- Reserved DOI, if returned, and draft ID are recorded and preserved across all retries; no production DOI assigned

## Retry and stop rules

- Persist create intent before POST and returned ID before metadata/file operations
- Execute candidates serially under existing environment ledger lock with one writer
- Repeat exact unchanged payloads and same durable ledger: zero new creates, same IDs/DOIs, metadata/files verified
- Unknown POST result stops for read-only reconciliation; never clear ledger or repeat POST
- After partial failure resume known ID; skip already matching XML upload; no DELETE
- Changed payload/source, unexpected files, stale/incomplete inventory, cross-host bucket or identity mismatch stops

The exact metadata objects, source copies, source/payload hashes and artifact contracts are in this directory and `selection.json`. This is not an executable upload allowlist or a release manifest. A blocked candidate must stay blocked; do not silently replace it or manufacture inventory eligibility.
