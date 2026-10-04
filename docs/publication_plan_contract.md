# Offline publication plan, version 1

`python -B -m scripts.publication_plan --repo . --output /tmp/pices-publication-plan.json`
creates a new JSON file of kind `nonexecutable_publication_plan`. It performs no
provider operations and is not an upload, QA, identity-adoption, execution-state
or release manifest. It never constructs a client or discovers a registry.
An existing output is not overwritten.

The current implementation accepts the finite PR30 source baseline only. Eleven
exact evidence/profile pins and all4,206 original XML hashes must match. Each of
3,978 targets occurs once:3,750 singletons and228 pairs, with both original pair
identities/filenames retained. All45 held/malformed targets remain in the manifest
and are excluded from prospective batches. Source-supported planning therefore
contains3,933 targets and4,161 original files. `--batch-size` accepts1–10 whole
targets; it never cuts a pair into individual uploads.

Every row has `executable`, `publication_approved`, `upload_eligible` and
`remote_verified` set to false, an empty `provider_actions` list and a null grant.
Both global `shared_execution_holds` and each row's `execution_holds` apply.
The batch list describes prospective review/preparation work, including protected
existing targets that may require a correction review. It is not a create list.

`expected_original_files` contains literal filenames, paths, sizes, SHA-256 and
MD5 values computed from the original files. These are not policy or payload
contracts. Singletons need separately validated prepared metadata/artifact policy.
Pairs retain saved v2 artifact references and the explicit24-fresh/204-historical
resolver. Those artifacts are not rebuilt or newly validated by this planner.
All files are descriptive metadata; underlying datasets are not included.
Original XML, source conditions, restricted artifact access and no inferred
licence remain requirements. The legacy production transport is not validated by
the separate modern synthetic controller.

Identity decisions preserve the five existing record IDs, DOIs and historical
beforeimages. The parent reports those associations unchanged in the fresh owner
inventory; the complete raw capture is not available to this code lane. Each pair
therefore carries a reported-zero-exact-current-owner-candidates decision with
raw-capture review pending. Current-owner coverage does not establish deleted or
tombstone historical absence. Two title hints remain nonidentity evidence.
Other singleton identities remain unassessed; the228-pair comparison is not an
inventory comparison of all singleton sources. Poster10042430 and programme15046283
remain excluded from FGDC restoration.

## Optional sanitized restart export

`--restart-snapshot PATH` reads only the explicitly supplied JSON file. It must
contain exactly these top-level fields:

| Field | Required value |
| --- | --- |
| `schema_version` | Integer1 |
| `kind` | `sanitized_offline_publication_restart_snapshot` |
| `environment` | `production` |
| `publication_inputs_sha256` | Exact value from the current plan, binding its evidence and original-file inventory |
| `entries` | List of unique target entries; omitted targets retain missing-state holds |

Each entry has exactly `record_target_id`, `source_sha256`, `environment`,
`deposition_id`, `doi`, `needs_reconciliation`, `upload_status`, `publish_status`,
`metadata_sha256` and `artifact_contract_sha256`. Target/hash/environment must
match. The provider ID is a positive integer or null; DOI is a literal DOI string
or null; `needs_reconciliation` is boolean. Upload status is pending, failed,
success or unknown. Publication status is draft, published or unknown. Payload
and artifact hashes are lowercase64-digit SHA-256 or null. The export is a
sanitized report of prior state, not a current provider verification receipt.

Malformed, unknown, duplicate-target or stale exports are rejected. Shared provider
IDs, a conflicting protected ID/DOI or an excluded identity produce explicit holds.
Missing state never replenishes a consumed create allowance. Uncertain creates or
writes require reconciliation, and unknown state remains held. A reported partial
or completed draft is only a same-identity readback hint. A reported published
identity is preserved; no replacement or new create is proposed. All hints retain
`safe_to_retry: false`. Neither supplied flags nor a self-rehashed snapshot can
make the plan executable. Actual durable recovery and bounded grants remain with
the separately reviewed executor.

`publication_inputs_sha256` is the canonical JSON SHA-256 of evidence bindings and
original-file descriptors. `plan_sha256` is the canonical JSON SHA-256 of the plan
without that field, using sorted keys, UTF-8, unescaped Unicode and compact
separators. There is no generated timestamp or environment-dependent path in the
new identity, so an unchanged planning retry is exact. A changed snapshot yields
a distinct plan and cannot modify any prior state or evidence.
