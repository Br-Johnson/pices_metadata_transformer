# Reviewed correction batches

The standalone compiler converts reviewed source cohorts into ordinary keyed
curator decisions accepted by `scripts.batch_transform --decisions`. It performs
no provider calls and confers no publication or rehosting authority. Original
FGDC XML remains immutable. Use common FGDC mappings first, then coherent
source-supported batches, narrower groups and explicit residual source IDs.
Sandbox records are not metadata truth.

```sh
python -m scripts.curation_batches --sources FGDC \
  --manifest reviewed-batches.json --decisions-out decisions.json --audit-out audit.json
```

Both output paths must be new, distinct files outside the source directory and
must not overwrite a manifest. Validation of every affected transformation and
artifact contract completes before output creation. A filesystem failure during
writing can leave a partial output pair; discard those outputs and retry with new
paths. Never consume outputs from a failed invocation.

## Version 1 contract

Root: exactly `schema_version: 1` and nonempty `batches: [...]`. Batch:

- `batch_id`, `version: 1`, nonempty `reviewer`, timezone-aware `reviewed_at`,
  `rationale`, and nonempty `evidence`. Evidence entries are text or inert JSON
  objects with a nonempty `kind`; structured source receipts are retained intact.
  Evidence contents remain subject to human review, not automatic factual proof.
- `selector`: `normalization: strip_xml_text` and exactly one of
  `fgdc_paths_equal` or `source_ids`. Path selection matches the ordered lists of
  all element text, trimming only surrounding whitespace. Supported paths are
  primary citation `origin`, `title`, `pubdate`; `idinfo/accconst`,
  `idinfo/useconst`; and `metainfo/metd`, `metrd`, `metac`, `metuc`.
  Explicit `source_ids` enables narrower residual cohorts. Missing or malformed
  explicitly selected sources fail. XML parse failures otherwise appear in audit
  exclusions. Source symlinks fail.
- `members`: every matching source's exact `source_id` and lowercase raw-byte
  `source_sha256`, including held sources and aliases. Membership must be complete
  and exact, with no duplicates. No alias or hold is cleared by selection.
- `correction`: nonempty subset of `metadata`, `artifact_policy`, and
  `content_classification`. Metadata permits only `creators`, ISO
  `publication_date`, and `license`; creator fields are `name`, optional `type`,
  `affiliation`, `orcid`, `gnd`. Empty or unknown structures fail. Factual and
  rights changes require source-backed review; no license is inferred.
- Optional `supersedes`: unique IDs of earlier batches in manifest/command order.

Duplicate JSON keys (at any level), duplicate batch IDs across manifests, unknown
contract keys/versions and unsupported selector semantics fail closed. The API
`load_manifest(path)` enforces duplicate-key handling; `compile_batches` accepts
already parsed manifests and returns decisions/audit without writing outputs.

## Overlap and precedence

Corrections compose by metadata field; artifact policy and content declaration
are each atomic fields. Equal values coalesce and disjoint fields compose.
Conflicting values require explicit `supersedes` naming **every currently active
prior batch** contributing that field for that source. Equal-value contributors
remain active until superseded. Unknown or forward supersession references fail.
Manifest order alone never permits a conflicting overwrite. All batch reviews,
evidence, fingerprints and supersession declarations remain in each compiled
decision. The audit lists each equal/conflicting field overlap and resolution,
exact membership hashes, inventory hash and decisions hash.

## Original XML artifact binding

Artifact declarations use the existing artifact contract's strict schema and
explicit rights/date evidence. In a batch, `artifact_policy.source_sha256` must
be exactly `$source_sha256`; the single content file name must be exactly
`$source_filename`. The compiler replaces only these two fields with the member
hash and original `<source_id>.xml`. It performs no general string interpolation.
Artifact and content declarations must be supplied together; only complete,
reviewed descriptive-metadata inventories of the original XML are supported.
Optional artifact policy references `source_access_interpretation`,
`rehosting_authority`, and `creator_interpretation` contain exactly nonempty
`manifest_path` and lowercase 64-hex `manifest_sha256`. The compiler preserves
these references and validates their syntax only; downstream pinned-profile
validation decides their meaning and authority.
Existing XML-specific `rights_scope`, `rights_source_xpath`, and policy `license`
are preserved. An explicit empty metadata license remains empty: rehosting
authority is not a license grant. These syntax checks do not clear QA holds.
No research-data availability is inferred. The existing artifact validator
checks every resulting binding.

## Migrating the transferred candidate

The 821-member transfer candidate is a precursor, not a v1 compiler manifest.
After independent source/evidence review, move its `schema_version` to a new
root, add `version: 1` to the batch and `normalization: strip_xml_text` to its
selector, and wrap it in root `batches`. Preserve all members, hashes, correction
values and structured evidence. This document does not approve or apply that
candidate, decide rights, or clear its residual access/alias holds.

Implementation rationale: field-level active contributors prevent silent
last-writer-wins loss of review, while atomic artifact declarations prevent
partial policy merges. This compiler is additive and does not change the
existing decisions interface. Shared checklist/technical-debt updates belong to
the integration owner. See `docs/readiness/curation-compiler-cloud.md` for checks.
