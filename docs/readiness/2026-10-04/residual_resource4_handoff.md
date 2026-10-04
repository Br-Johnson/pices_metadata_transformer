# Four resource contexts and complete content-alias mapping — 2026-10-04

The measured increment from main `e998e9c97945da60cf9c15fb39ab5fc2a5b11d47`
promotes exactly **FGDC-762, 849, 859 and 2244**, producing **3,681 supported /
519 held / 6 malformed**. This is offline source readiness, not remote verification
or publication. These counts become main accounting on merge; the PR timeline
records actual current-head CI, independent Codex review and merge verification.

## Four exact interpretations

[Profile596](finite_source_resource_access_596.json) retains all 592 earlier
members, complete source contexts, review blocks and assessment times. A separate
four-member review binds each original hash, complete XML root, four literal
constraints, review time and the five unchanged original statement snapshots.
The [independent source review](residual_resource4_source_review.json) reads the
whole sources, including a separate challenge of the museum and SPOT cases.

| Source | Literal condition retained | Bounded source reading |
| --- | --- | --- |
| FGDC-762 | “The permission of the Village Council is necessary to copy maps pertaining to the village of Tatitlek.” | The catalogue describes blueline maps; it contains no map image, geometry or community harvest-location list. Council consent and unknown use remain unresolved. |
| FGDC-849 | “User must review and sign a Data Use Policy stating data use provisions.” | The source specifies a mammal-data request/signature/notification workflow. The complete policy is unavailable; signature, notification and specimen-examination conditions are not claimed satisfied. |
| FGDC-859 | “Licensee agrees to limits to internal use and copy restrictions.” | The description and fee inquiry identify the SPOT imagery product. The XML contains no imagery pixels; no SPOT licence, payment or copying permission is inferred. |
| FGDC-2244 | “Copyright protected by ESA and CSA. Give credit to ESA and CSA.” | The source describes ERS/RADARSAT images and their PI/NASA approval, copyright and credit conditions. No imagery or approval is supplied by restoring the catalogue XML. |

All four use `REVIEWER_RECONCILED` provenance and the existing separate restoration
authority. No express XML exemption, expanded original attestation membership,
fulfilled condition, new licence or underlying-data right is asserted. All
original constraints remain present in the complete metadata and XML.

## Measurement and verification

The [measurement](residual_resource4_validation.json) uses seven sources, below
the ten-source smoke limit: four candidates and held controls 288/1770/4063.
Creator412 and every other interpretation input remain constant. Before and
withdrawal produce seven holds; after and repeat produce exactly four supported
and three held. Every complete raw metadata object and XML copy is unchanged;
the only candidate payload change is the exact dataset-access policy reference.
Control rows and payloads remain identical. Repeat is asserted in memory while
reusing the after directory; separate first-after and repeat snapshots are not
claimed.

All 4,206 original hashes match the frozen ledger before and after. The
[integrated ledger](residual_resource4_integrated_source_status.json) changes
exactly four rows and preserves all 4,202 unselected objects, including all 456
alias identities and 31 prior exceptions. This is the frozen all-source ledger
plus a measured finite delta, not a fresh full-corpus semantic classification.

[Four focused guarded contracts](residual_resource4_focused_checks.json) pass
with unchanged source bindings and zero unexpected network/private-file/process/
write calls. They exercise exact membership, old-profile compatibility, full-root
and constraint tampering, live evidence, review times, metadata/XML preservation,
repeat/withdrawal, and authority/rights checks through agent and both human QA
schemas. Full actual current-head CI and independent implementation review remain
the final PR merge gates.

## What the 456 aliases mean

**They are 228 pairs of byte-identical source files, with both members held.**
There are 228 extra copies. None has an exact-content counterpart among the
already-supported records. Consequently “456 aliases” does not mean 456 distinct
scientific resources, or 456 redundant copies of records already counted as
supported. Byte identity alone also cannot establish the total number of distinct
scientific resources represented by different descriptions.

The complete [JSON](alias456_source_to_content.json) and
[CSV](alias456_source_to_content.csv) map every one of the 456 filenames to its
`sha256:<raw XML hash>` canonical content class and both group members. All 228
groups were checked by direct raw-byte equality, and all 4,206 original hashes
were checked against the baseline ledger. The corpus contains 3,978 unique file
contents. Canonical source, catalogue, provider-record and DOI fields remain null:
the mapping proves content equivalence and does not select a filename or existing
record identity. It makes no promotion, collapse, deletion, rekey or upload choice.

The mapping is explicitly bound to baseline e998e9c, whose counts were
3,677/523/6. This four-source increment changes none of its 456 alias status
objects. Older component diagnostics found 204 pairs supported apart from alias
gating and 24 pairs with additional holds; those historical results are not
current semantic QA. See the [plain-language explanation](alias456_explanation.md)
and [identity-evidence review](alias456_canonical_evidence_review.json).

The additional tracked source-archive lead was checked. Its 4,204 XML entries are
all exact copies of current originals, with no export manifest, non-XML entries
or comments. It omits the two all-NUL originals 3373/3484. The
[archive receipt](source_archive_provenance_check.json) therefore supplies no new
canonical identity or intact replacement. Archive order is not identity evidence.

## Remaining evidence and reproducibility

The 519 held rows consist of 456 aliases and 63 nonalias sources: 22 creator
cases, six metadata dates, one display title, 31 prior exceptions and the three
policy/password controls. Six malformed files are counted separately. The
[remaining-decision reconciliation](post4_remaining_decisions.md) separates
missing provenance/history that requires outside evidence from further agent
research and review. The source-specific FGDC-233 title option is queued for
independent editorial review; it is not an automatic truncation or a promotion
in this increment. Settled restoration and Contact Source/Contributor meanings
are not asked again.

From a clean checkout with project dependencies, use fresh output directories:

```bash
python -B docs/readiness/2026-10-04/validate_residual_resource4.py \
  --repo "$PWD" --output /tmp/pices-resource4-fresh
python -B docs/readiness/2026-10-04/build_alias_content_manifest.py \
  --repo "$PWD" --output-dir /tmp/pices-alias456-fresh
python -B ci/run_offline_tests.py
```

The bounded measurement clears its environment, uses a dummy credential and
blocks provider transport, sockets and DNS. The standard-library alias builder
reads pinned evidence and original source bytes, performs no semantic
classification or network operation, and writes analysis artifacts outside the
checkout. Its complete output was reproduced; every mapping/evidence object and
CSV byte matched the worker artifact, with only the final generator-file hash
updated after import formatting and an explicit strict-length assertion.

| Artifact | SHA-256 |
| --- | --- |
| Resource596 | `4719b46cfe46a2b950b3abc695fd8778ffc7bd3041e5bb0bae253c613c55ec2c` |
| Source review | `2a7d9f1ab402d4d9aef71ae0e553a1b80d07152107b2d3e500fe66a10115aea3` |
| Measurement | `fae52ca3cb0189095e64e8817604a81545dfe4db1bf2e8464799dc956f1bf038` |
| Integrated ledger | `4e24fbe4859644d7fe1ddfbd87bf207df8dd6f4f8a9ea288713a1fb9a15aed7b` |
| Complete alias JSON | `9c110638bd161483727aed1b42e516fdc7a3c9d8134c97a9a70abff690750bbb` |
| Complete alias CSV | `f92334c5d3212f78ccdfd02063f6a09596015a50c9a579fa67e98703ce0bcf1f` |

No provider requests, transport changes or action-budget changes were made.
Original IDs, existing records/DOIs, production deduplication and unrelated poster
10042430 protections remain intact. Sole-executor live work remains separate.
