# User-attested historical metadata restoration authority

On 2026-10-02 Brett replied to the collection rehosting-authority question:

> I have permission and instruction to rehost this metadata which was originally published on a geonetwork catalogue that we lost access to.

This closes the absence-of-rehosting-authority question. It is **USER_ATTESTED**, not an independently verified agreement, a new Creative Commons license, authority over underlying research data, or production release. `rehosting_authority.json` binds the statement to 4,206 original source IDs and SHA-256 values. Matching sources no longer require an exact CC label merely to establish rehosting authority. Six malformed originals remain unassessed; a hash listing does not make them valid preparations.

## Supported source-only preparations

The authority-aware profile preserves original XML, constraints, citation attribution, metadata-date semantics and explicit object identity. It prepares `other` metadata artifacts with blank license and restricted attachment downloads. This existing Zenodo representation avoids assigning CC0/CC-BY to files; it is not a decision that the lost catalogue was confidential. Creators preserve dataset citation attribution; XML authorship is not independently established. Contacts are never automatically promoted to authors.

Source access terms outside the supported vocabulary, ambiguous creators, unresolved relations, invalid dates and exact-copy aliases remain holds. Exporter evidence organizes exceptions, without overriding them. Changed manifest/source/policy hashes, sources outside scope, open attachments, new licenses or mismatched access conditions fail closed.

| Source-only result | Before | After |
| --- | ---: | ---: |
| Supported preparations | 0 | 687 |
| Held parseable sources | 4,200 | 3,513 |
| Strict parse failures | 6 | 6 |
| Technical payload passes | 4,131 | 4,131 |
| Technical holds / not constructed | 63 / 12 | 63 / 12 |
| Exact-copy groups / involved files | 228 / 456 | 228 / 456 |
| Remote verification / publication approvals | 0 / 0 | 0 / 0 |

All 4,200 parseable sources match the attested hash population. Before alias checks, 689 pass source-only assessment; two are held by the alias gate. Remaining reasons overlap: 3,172 sources have access terms requiring scope adjudication; 1,329 encounter creator ambiguity; 21 have empty creator names; 42 raw titles exceed limits; 21 newly reached records need relation adjudication; six lack a supported metadata date. Short-circuit counts are not disjoint totals.

The 127 sources outside the common exporter signature are included in Brett's collection attestation, while their record decisions remain separate: all lack metadata-use/access fields; 106 have organization-primary metadata contacts and 21 person-primary contacts. No license is inferred from missing terms.

## Public metadata and attachment access

The pipeline preserves complete raw XML in record notes. Restricting attachment downloads **does not hide XML contents already represented in public metadata**. Sources with unresolved sensitive access terms remain held. [Zenodo policies](https://about.zenodo.org/policies/) require licenses for public files and specify CC0 metadata reuse, except email addresses; its [terms](https://about.zenodo.org/terms/) describe that default. This platform condition is distinct from the blank attachment license and Brett's attestation. Production release must account for the submitted public metadata and applicable terms. No release, live upload, publication or credential action occurred.

## Reproduce

From repository root, run `python -m scripts.collection_qa --source-dir FGDC --output-dir NEW_DERIVED_WORKSPACE --reviewed-at 2026-10-02T12:20:58Z --authority-manifest docs/readiness/2026-10-02/rehosting_authority.json`. Originals remain untouched. Authority-aware exports are `authority_collection_summary.json`, `authority_collection_classification.csv` and `authority_collection_hold_codes.json`; earlier `collection_*` files retain the baseline.

Classification is offline: it does not invent uploaded ledgers, snapshots or external duplicate clearance. Record QA still requires fresh remote/file/duplicate evidence and independent process review; production requires separate release authority. Sandbox authentication remains an external execution blocker.
