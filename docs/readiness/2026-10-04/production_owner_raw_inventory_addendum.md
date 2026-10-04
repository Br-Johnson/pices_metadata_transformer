# Current-owner raw inventory evidence — 2026-10-04

Later evidence: the [two-detail closure](production_owner_file_coverage_closure.md)
resolves the two file gaps using retained 22:17 UTC responses. This addendum and
its review receipts retain the earlier 21:53 capture's scope and findings.

This documentation-only addendum advances the evidence review after merged PR31
(`4bc59af3ff4432e297e64d3c70b6c57ecdaf0390`). The frozen publication plan, source
classifications, runtime code and all execution holds remain unchanged.

The original 20:27–20:29 UTC capture retained 42 request receipts and sanitized
projections, but **no original provider response bodies**. Those observations
remain useful historical evidence. They are not raw captures, and later matching
hashes do not change their original retention status. The transfer manifest is
Library `libfile_cbc754ee59108191bc2d78e9bb0133ce`, SHA-256
`d4ae05a5fe18eec6cfbb4330fbbdec73669429f266a8ca92205fe7e0c0c197dc`.

The separate authorized reader then retained exactly three fresh response bodies
at **21:53:04–21:53:10 UTC**. The integration owner independently checked the
transferred bytes, source descriptors, metadata hashes and candidate comparisons
offline. No provider requests were made by this review.

| Raw response | Bytes | SHA-256 |
| --- | ---: | --- |
| First page 1 | 80,271 | `77b4792e26b4f1144b23da197e539e05611a887d0c965a4fe908b7d567c8cc50` |
| Terminal page 2 | 2 | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| Repeated page 1 | 80,271 | `77b4792e26b4f1144b23da197e539e05611a887d0c965a4fe908b7d567c8cc50` |

The [review receipt](production_owner_raw_inventory_review.json) binds the three
transferred file IDs, credential-free request ledger, exact hashes and all 228
pair decisions. The raw bodies remain in the authorized Library transfer; they
are not copied into this public repository. The raw capture manifest is Library
`libfile_110c56cf9bcc8191a88e36b739984908`, SHA-256
`4223e1d78297889755abb659621fb504a97f5fa566b5c743d1ce94d95ebf57e7`.

## Verified scope and remaining discrepancy

The three bodies contain 20, zero and 20 objects; the two page-1 bodies are byte
identical. All 20 objects belong to owner 266679, with 19 published depositions
and one unsubmitted draft. The reader used the documented owner listing with
`all_versions=true`, page size 100, no state/community filter and no redirects.
The endpoint documents an array of deposition resources and the all-versions
option: [Zenodo API documentation](https://developers.zenodo.org/#list).

All 20 complete metadata objects reproduce the earlier retained metadata hashes.
The five protected record IDs and literal DOIs match the frozen associations;
the source associations are preserved, not newly inferred from provider fields.
All 20 returned file descriptors match the earlier descriptor values. However:

| Record | Fresh list files | Earlier detail files | Consequence |
| --- | ---: | ---: | --- |
| `17317855` (protected FGDC-1238) | 0 | 1 | Current file preservation and candidate coverage unresolved |
| `10783360` (unsubmitted draft) | 0 | 3 | Current file candidate coverage unresolved |

An empty listing array does not establish current file absence or deletion. The
four earlier descriptors retain their earlier observation times and are not
inserted into the fresh raw arrays.

All 4,206 original source SHA-256, MD5 and size descriptors were reverified
offline. Comparison of literal source IDs, literal source SHA-256 values, exact
source filenames and declared MD5/size against the returned fields finds no
direct source candidates, including none for any of the 228 pairs. This is a
candidate search result with incomplete file coverage, not source identity
adoption or proof of absence. The title hints for pairs 2920/3148 and 3027/3255
remain separate from the protected FGDC-2043 association with record 17317851.
Poster 10042430 and programme 15046283 remain excluded from restoration.

## Minimum next reader action

Exactly two fresh detail responses are justified:

```text
GET https://zenodo.org/api/deposit/depositions/17317855
GET https://zenodo.org/api/deposit/depositions/10783360
```

The parent dispatches these to the authorized reader. Retain original body bytes
before parsing, with timestamps, status, byte count and SHA-256, excluding
credentials and request authentication headers. No automatic redirects or
retries. Check returned owner/ID/concept/DOI/metadata against the retained listing;
compare complete file names, IDs, checksums and sizes against both the original
source inventory and the explicitly historical descriptors. Any discrepancy
remains held; do not refill a create budget or infer deletion.

These two detail responses need their own offline review. They may resolve the
two file-coverage gaps; their mere collection does not close the gate. No repeat
inventory, other deposition details, version histories or file-content downloads
are requested. If either response introduces a specific unresolved issue, return
that issue for a scoped follow-up rather than widening the read set automatically.

The raw owner-listing capture review is complete. The current-owner file-candidate
gate remains open. Global or deleted/tombstone absence, exact remote file bytes,
newly verified version histories, identity adoption, transport/recovery, QA/release
and provider action grants are not established. The frozen plan remains entirely
nonexecutable; this addendum is not an input or permission override for it.
