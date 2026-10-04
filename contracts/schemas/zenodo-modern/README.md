# Pinned modern draft payload validation

These four unchanged MIT-licensed schemas validate every submitted field in the
fixed fictional run02 body, with references resolved from a local registry.
No schema is retrieved over the network at validation time.

Zenodo source at [7111dde7](https://github.com/zenodo/zenodo-rdm/tree/7111dde7d1ebf6f64bc695edf7ad8cce5bfa1ac7)
uses `ZenodoRecordSchema`, inheriting the RDM schema. Its `uv.lock` pins RDM35.2.0
at [d4a4ef21](https://github.com/inveniosoftware/invenio-rdm-records/tree/d4a4ef21ef5cd99b6d1350b537c82581799296a3),
records-resources at [12ca9331](https://github.com/inveniosoftware/invenio-records-resources/tree/12ca933194d9f5c4ea15eacc72ec220ee2cec197)
and drafts-resources11.0.3. `sources.json` records the exact schema hashes and URIs.
The original record and record-definition filenames differ only for the local
record-definition copy, to distinguish it from the base definitions.

The storage schemas intentionally support incomplete drafts and omit metadata
required lists. `modern_draft_schema.validate_payload` therefore also applies the
service-required `resource_type`, `creators`, `title` and `publication_date`
requirements, nested creator type/name rules, the DataCite publisher requirement,
and every fixed fictional description/subject/access/file predicate. This is
complete local validation of this exact writable canary body; it does not emulate
database vocabulary resolution, account permissions, every optional modern field
or the deployed server. The body excludes unrelated branches, including review,
so references for those unused branches are never traversed. Missing local
references cannot trigger a network lookup.

Zenodo's [publisher guidance](https://help.zenodo.org/docs/deposit/describe-records/publisher/)
defines publisher as required and documents the host default, `Zenodo`. The
synthetic fixture was not previously published and contains no source record.
Only its sealed fictional projection receives that value; original source
metadata and all production publisher decisions remain unchanged.

`tests/fixtures/zenodo-modern/components.py` contains exact MIT source-method
excerpts from DataCite PID validation and the draft files update component.
The tests compile those methods with dummy bases/services and reproduce the
publisher and enabled-empty-files errors without framework imports or network.
This supplies an independent semantic oracle alongside the full JSON schemas;
it is not a live service integration result. The [independent source receipt](../../../docs/readiness/2026-10-03/modern_complete_schema_independent_research.json)
binds the complete original files, versions and reproduction evidence.

The documented `files.enabled` missing-upload warning can occur on an otherwise
valid empty draft. Only the separate controlled schema-repair ledger may accept
exactly one such error with one of the two exact upstream missing-upload messages,
after every metadata, access, sealed identity, empty-file and absent-DOI predicate
passes. Permission/toggle errors on the same field, additional errors, missing
metadata, unexpected messages or changed identity/access/files/DOI still hold.
Generic canary, production and release error policies are unchanged. The second
historical live error label was discarded and remains unknown; reproducing this
warning does not establish that it was the live field.
