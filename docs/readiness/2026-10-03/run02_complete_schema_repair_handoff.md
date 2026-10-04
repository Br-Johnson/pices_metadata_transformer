# Controlled run02 complete-schema repair

Parent reports PUT2 returned HTTP200 with two validation errors: publisher and
one unknown field. Its per-attempt metadata diagnostics report all six intended
fields absent and file access mismatched. The exact prior494-byte body passed its
prepared-send check. No GET followed; cumulative GET197, run02 PUT2 and create1
remain spent, and all357 historical evidence entries are preserved. No raw
response was retained, so the second field cannot be reconstructed. GET197 is an
earlier identity anchor, not a current canonical read after PUT2.

The new controller validates all submitted fields against the pinned official
modern record JSON schemas and all service-required/fixed synthetic predicates.
See [schema provenance and limits](../../../contracts/schemas/zenodo-modern/README.md)
and [independent source research](modern_complete_schema_independent_research.json).
It adds only `publisher: "Zenodo"` to the previously corrected fictional wire
body. This documented repository-host default fits an unpublished protocol
fixture, and assigns no publisher to any PICES source record.

The exact corrected PUT body is517 bytes with SHA256
`71830ca80356953b8654dd0e589eeff15b1b46c08c313b98372936c85c09da7a`.
The historical fictional packet, all source inputs and prior schemas/grants remain
unchanged. The new namespace is
`pices-modern-synthetic-20261003-code-02-schema-repair`.

Upstream draft updates can report `files.enabled` when enabled files are still
empty. That is a source-backed candidate explanation, not identification of the
discarded live label. The separate new ledger accepts only one error on that
field with exactly one of these upstream messages:

- `Missing uploaded files. To disable files for this record please mark it as metadata-only.`
- `Missing uploaded files.`

The response must first pass all seven metadata fields including publisher,
public record/restricted file access, the same sealed owner/id/parent/created
first draft, enabled files with zero entries/count/bytes, and absent DOI. The
same field with permission/toggle errors, any other error/message, changed
identity/access/files/DOI or incomplete metadata holds before GET. The warning
message is compared in memory and never copied into state or receipts. Generic
controllers retain their original error policy. Completion is metadata-only and
does not establish publication readiness or complete the remaining file/PID trial.

The sole executor remains `01a0fed7-bf71-7384-95fd-3434599df03f`. Root and reviewers
perform no authenticated/provider requests, and read no real private evidence or
credential/settings files. The public [contract](../../../contracts/examples/run02_schema_repair.json)
is `approved:false`; code, staging and preflight never issue an action grant.

## Sole-executor offline staging before any new window

1. Use the frozen reviewed checkout and install its requirements, including
   `jsonschema>=4.23,<5`. Preserve every old stage, grant, journal and counter.
2. Create a new0600 manifest at a fresh canonical absolute path. Convert the
   previous sealed expected path/hash inventory for **all357** retained evidence
   entries to the schema below. Do not adopt the current filesystem as a new hash
   baseline or overwrite an old manifest. Every selected historical evidence file
   must be declared; the new manifest itself is the only permitted extra leaf.
3. Select the complete actual evidence subtrees or exact manifest leaves. Retain
   the old `/workspace`0755 origin literally as ancestry; do not recursively scan
   it or change its mode. Canonical non-writable shared ancestors are accepted;
   all evidence leaves must be private regular single-link files with no symlinks
   or overlapping/inside-stage roots. The old failed subjects-repair stage must
   be included completely, alongside the original/owned stages, GET196/197 and
   all earlier receipts.
4. Stage at a fresh path with the exact new namespace basename. Staging validates
   the permanently spent subject-repair runtime,494-byte proof, HTTP200/two-error
   flags and its same-attempt metadata/access diagnostics. It also validates all
   legacy lineage, complete historical manifest coverage and the corrected local
   schema before creating the new stage.

```json
{"schema_version":1,"files_sha256":{"/canonical/absolute/evidence/file":"<previous-expected-sha256>"}}
```

```sh
python -m scripts.modern_run02_schema_repair stage \
  --stage /absolute/new-parent/pices-modern-synthetic-20261003-code-02-schema-repair \
  --previous-repair /absolute/retained-parent/pices-modern-synthetic-20261003-code-02-subjects-repair \
  --preserved-manifest /absolute/new-private-parent/preserved357.json \
  --preserved-root /absolute/complete-evidence-subtree

python -m scripts.modern_run02_schema_repair preflight \
  --stage /absolute/new-parent/pices-modern-synthetic-20261003-code-02-schema-repair
```

Repeat `--preserved-root` for nonoverlapping complete subtrees, or omit it for a
manifest-only forest. Preflight executes the same complete controller input,
lineage, credential-echo, local schema and prepared-request checks, with no action
grant read/mint, ledger write, lock, intent or transport. Return only its closed
flags, exact six-runtime/schema hashes, binding hash and inventory count/hash to
parent. In the357-entry dummy topology the new manifest yields358 inventoried
leaves. Bind the actual computed count/hash; never force an expected count.

## Parent grant and sole execution

Only after the actual private offline preflight succeeds, parent may begin one
fresh window of at most600 seconds. Bind the exact new stage/runtime/schema/input
inventory and explicit `controlled_full_schema_repair:true` and
`allow_exact_missing_upload_warning:true` predicates. The grant also requires
`existing_candidate_only:true`, `no_create_or_reset:true`, the unchanged original
owner/known-id set, historical GET197, and limits `{"metadata":1,"get":1}`.
Copy the public contract's allowance and warning policy exactly; it grants no
create, PID, file, publication, deletion, replay or reset route.

The sole executor calls `execute` once. It may perform one additional metadata
PUT at the same sealed canonical `/api/records/{id}/draft`, then one GET only
after the PUT is fully validated and durably acknowledged. Each request remains
bounded to20 seconds/65536 response bytes with TLS, no redirects and zero retry.
At most cumulative GET198 and run02 PUT3 are permitted; create stays1. Any failed,
uncertain or interrupted intent stays spent permanently and cannot reenter.

The new error projection retains at most16 unique field paths, each at most128
ASCII characters, with bounded lower-case identifier and numeric-index syntax.
It rejects controls, URL/path punctuation, opaque strings and credential variants
before bounds; labels are never truncated into different fields. Suppression and
count-limit flags remain visible. Messages and values are not retained. Full-body
credential echoes suppress the projection; malformed, partial and oversize bodies
retain the original hold behavior. Names alone never waive validation.

No live success is claimed by the local schemas, source-method or mocked execution
fixtures. Provider dispatch and subsequent evidence reconciliation remain with
parent and the sole executor. Source accounting remains3638 supported/562 held/
six malformed, with all XML/raw metadata, aliases, DOIs and existing files intact.
