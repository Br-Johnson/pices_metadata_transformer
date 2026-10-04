# Captured-only production identity inputs for 228 pairs

The [deterministic input](alias228_production_reconciliation_input.json), SHA256
`a5b34f430a3b0b3a14776987e9828b4a1cf701ce2dc2172bd4cbb472759e37e5`,
contains all 228 pairs and 456 member IDs/hashes from merged PR28. It reads only 11
explicitly pinned public repository evidence files. All228 targets remain
unresolved and upload-ineligible; no exact production candidate is established
for any pair by this captured inventory. That is not evidence of remote absence.

Five historical imports are protected with their existing IDs/DOIs: 1238→17317855,
2043→17317851, 2057→17317859, 2725→17317857 and 2731→17317853. Each retains the complete
captured 2026-10-01 timestamp/provenance, public metadata and public file-list
objects plus a digest. Four captured lists contain `metadata.txt` with literal
MD5 values; 17317855's captured empty list does not prove file absence. These are
historical snapshots and do not establish current ownership, version or files.

The two title-collision pairs 2920/3148 and 3027/3255 stay distinct from 17317851 and
from each other. Title or research DOI similarity cannot transfer provider
identity. Poster 10042430 is excluded; unrelated 15046283 remains preserved.

The initial independent review found a capture-time summary error. The corrected
packet preserves the exact known historical timestamps and fields, with
[13 passing local checks](alias228_production_reconciliation_checks.json) and a
[narrow independent correction review](alias228_production_reconciliation_review.json).
The [initial review](alias228_production_reconciliation_initial_review.json)
remains evidence of the finding and the otherwise complete pair audit.

Reproduce from the repository root, choosing an output file that does not exist:

```bash
python -B docs/readiness/2026-10-04/build_alias228_production_reconciliation_input.py \
  --repo . --output /tmp/pices-alias228-reconciliation-reproduction.json
```

The helper has no provider, environment, credential, subprocess or private registry
access. Its frozen counts remain PR28's 3696/504/6 original-file view and 3900/72/6
target view. Use the separate [creator8 ledger](creator8_integrated_source_status.json)
and [target projection](creator8_record_target_projection.json) for current source
accounting; do not rewrite historical production evidence to match later totals.

The sole provider executor `01a0fed7-bf71-7384-95fd-3434599df03f` needs, after parent
dispatch: a complete authorized owner-scope inventory with endpoint/query/pagination
and completeness evidence; candidate readback checked against both member IDs/filenames and their shared
raw XML hash;
current ownership, record/version/concept/DOI state and complete file evidence;
and explicit review of every conflict while preserving existing records/DOIs.
Community-only public search, missing pages or inaccessible scopes leave gaps.
No candidate is guessed, no canonical member selected, and no provider stage,
action grant, correction, deletion, upload or class execution support is created.
