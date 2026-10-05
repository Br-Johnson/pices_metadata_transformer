# ADR 0004: Durable production mutation attempts

Status: accepted for guarded offline integration, 2026-10-05.

## Problem and decision

Legacy singleton upload recovery persisted a draft ID but could repeat a metadata
or artifact PUT after an uncertain response. Publication had no durable attempt
marker. A lost upload registry could reuse a refreshed duplicate inventory.

Use a production-only schema-1 journal next to the upload registry:
`<uploads_registry_path>.mutations.json`. The existing environment ledger lock
covers every journal/registry read, intent write, provider action and result write.
The journal survives inventory refresh and independent registry reconciliation.
Its per-source SHA-256 binding covers environment, source ID, complete original
source hash, actual assembled metadata hash and full artifact contract. It also
retains resolved record ID, known DOI and fixed action keys `create`, `metadata`,
`artifact`, `publish`. The singleton guard still rejects all paired classes.

Before a write, persist an uncertain receipt with the original request record ID
(null for create) and attempt time. Flush/fsync the file, atomically replace it,
then fsync the directory. A failure at any durability boundary prevents dispatch.
A returned create ID is verified against retained associations and saved in the
journal before the upload registry or any subsequent write. Legacy transport
performs at most one attempt for mutations and refuses all automatic redirects.

## Recovery contract

- Never repeat a consumed action, including an action whose effect is absent.
- A complete same-ID metadata GET can confirm a spent metadata write and permit
  a first, unspent artifact write. A complete file/checksum/size and metadata
  readback confirms the artifact action. Changed source, payload, artifact,
  identity or supplied DOI holds the target.
- Successful publication requires a separate same-ID GET with published state,
  approved metadata/files and a known DOI. A publish response alone is not
  enough. Missing DOI fields preserve a previously known literal; a never-known
  DOI remains unverified. DOI equality/collisions are case-insensitive.
- Lost registry plus retained journal cannot create a replacement. Use explicit
  offline identity reconciliation with reviewed source/payload correlation.
  Reconciliation preserves all prior action keys and bindings.
- Incomplete legacy state without a journal is held even if it contains an old
  reconciliation note. Explicit reconciliation seeds all actions as consumed and
  uncertain when historical attempt evidence is missing. Such state can only
  recover already-complete effects by readback; it cannot acquire new writes.
- Preserve the journal and registry together. Loss of both cannot be detected
  from fresh local state; deleting or resetting them is not a recovery procedure.
  There is no journal-reset/regrant CLI or automatic migration that grants writes.

The five retained production source/hash/record/DOI associations are enforced in
both directions. Records 10042430 and 15046283 are excluded. These associations
preserve identity, not ownership or release authority. Existing published files
are retained; their correction path is not implemented by draft reconciliation.

## Executable validation and remaining publication path

Run the existing guarded suite, using dummy credentials and blocked transport:

```sh
python -B ci/run_offline_tests.py tests.test_production_mutations tests.test_artifact_contract tests.test_pipeline_safety tests.test_zenodo_diagnostics
python -B ci/run_offline_tests.py
```

This integrates recovery into the legacy singleton upload/publish services; it
is not a reviewed modern production executor. Modern source-aware creator and
publisher mapping, paired-class execution with QA/release, protected published
record corrections and one real bounded end-to-end rehearsal remain separate.
The parent resolves the Mac account/access issue and dispatches provider stages.
No canary pass, current provider access, production release or publication ETA is
inferred from these offline tests. Source QA remains 3,933 supported targets,
39 held and six malformed; no original XML or source interpretation is changed.
