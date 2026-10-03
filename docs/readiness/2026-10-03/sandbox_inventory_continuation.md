# Sandbox continuation: inventory, then one synthetic draft only

Independently reviewed inventory-only continuation; execute only after parent dispatch. Synthetic writes remain blocked pending the exact write-stage controller described below. Continue the existing private run and ledger. The parent reports runtime `d5022b8` passed its one-request diagnostic: HTTP 200, 25 owned items, all validation milestones. This does not establish complete inventory. No actual FGDC source, publication, deletion, replacement, production request, credential copying or new run namespace is authorized here.

## Preserve and verify offline

Use frozen runtime `d5022b8828ef910749aef32371304f2b2b669674`, not an unpinned branch tip. Packet INVENTORY.json SHA-256 is `428559c7a8e81e84c22627b0add1230797b92013f87152e2ee3024b56af30fd1`; all 17 entries must verify. Verify the existing packet inventory and staged files. Preserve `/workspace/pices-sandbox-run-9379fd8-20261002`, including every original ledger, create intent and ID. Do not recreate the directory, restage over existing files, or reset safe-upload/ledger state by hand. Inspect existing synthetic ledger before any network operation: an uncertain create or partial previous write requires parent-led read-only reconciliation, not another create. A previously successful synthetic must not be created again.

Only source: `SYNTHETIC-PICES-9379FD8-20261002`. Stage root: existing run directory `/synthetic`; `OutputPaths` adds its `data` directory; payload basename adds `.json`, source basename adds `.xml`. From packet `selection.json`, require source size 471, SHA-256 `ba23767a19b7d235ffcc8d8cf03380052ae03735e08f5c4ca9c57316bd14ae25`, MD5 `820b1d0e33ac04feb42248698cd3dcaa`; staged payload SHA-256 `987f2259092f42024331f90e694fb001e32e6b14cc0e05d98b8b78addb5998b8`; canonical prepared metadata SHA-256 `2d3a4697cbec05b1cc219e39048b9ecb611ea811d076091edf5906b8cc4776ea`; contract SHA-256 `e7f9203dd867d9af0dac949c3c2886fb2c494096fdd55a52029d5ac1d4251c90`. Recompute with existing `prepare_metadata`, `metadata_hash`, and `prepare_artifact`, and compare full expected metadata JSON. No canary exception plan is passed for the synthetic.

## One complete inventory through the existing checker

The overall diagnostic-plus-inventory transport budget is 240 GET attempts, including the already reported one and the checker constructor. Thus the new guard below permits at most 239 attempts, fewer if any additional inventory requests have occurred. Exhaustion is a stop, never a reason to start a fresh guard. Keep a 300-second overall deadline using the reviewed diagnostic's sanitized timeout pattern. Every response remains subject to the guard's 12 MiB bound.

Run the following inside the reviewed sanitized error/deadline/cleanup envelope; do not emit raw exceptions or checker output to shared logs. Redirect checker stdout into private local output because it can include titles. All imports and token delivery use the reviewed environment loader, without printing environment values.

```python
from pathlib import Path
from scripts.sandbox_read_guard import SandboxInventoryGuard
from scripts.pre_upload_duplicate_check import PreUploadDuplicateChecker
from scripts.zenodo_api import load_zenodo_token
from scripts.upload_service import read_json

stage = Path('/workspace/pices-sandbox-run-9379fd8-20261002/synthetic')
expected_name = 'SYNTHETIC-PICES-9379FD8-20261002.json'
checker = None
with SandboxInventoryGuard(load_zenodo_token(True), expected_owner_id,
                           max_requests=239) as inventory_guard:
    checker = PreUploadDuplicateChecker(sandbox=True, output_dir=str(stage),
                                        allow_replacements=False, canary_plan=None)
    checker.client.max_retries = 0
    summary = checker.check_all_files()
    assert not summary['check_errors'] and not summary['duplicate_files']
    assert summary['safe_to_upload_files'] == [expected_name]
    retained = read_json(checker.paths.already_uploaded_path)
    assert retained['environment'] == 'sandbox' and retained['community'] == 'pices'
    assert retained['total_records'] == len(retained['records'])
    assert all(type(r['id']) is int and r['id'] > 0 for r in retained['records'])
    pre_run_ids = {r['id'] for r in retained['records']}
    checker.generate_upload_list()
client = checker.client
# Capture the safe inventory receipt, close client in the sanitized cleanup
# envelope, and pause. Do not execute the conditional synthetic stage.
```

The checker constructor performs one bounded GET. `check_all_files()` calls the existing exact-total/repeated-ID-checked community pagination and owned-deposition pagination itself; do not call these methods separately beforehand. `already_uploaded_path` retains their merged record IDs and metadata, permitting the pre-run union above without another fetch. It does not retain owner fields; owner verification comes from the guard's per-owned-page checks and previously verified private account identity. Do not interpret community hits as belonging to this owner. Retain the generated inventory/check artifacts privately and the sanitized guard receipt. Any checker/guard/schema/identity/total/inventory-age failure stops before writes; close the client safely.

## Required transport capability before the synthetic operation

**Current runtime gap:** `SandboxInventoryGuard` deliberately rejects all deposition-ID GETs, POSTs, PUTs and file downloads. It cannot guard the following stage. The client has no single reviewed write-stage request-budget/origin/owner enforcement wrapper, and ordinary `_make_request` calls still default to following redirects outside this inventory guard. Setting `client.max_retries=0` alone does not disable those redirects. Do not remove the guard and assume its protections continue; do not invent an executor patch. Parent/code owner must supply or explicitly verify an existing frozen write-stage transport controller before executing this section. The constraints below specify what that controller must enforce. This continuation dispatches inventory only: finish inventory, emit the sanitized receipt, close the client safely and pause. The conditional synthetic section requires a separate parent dispatch after that capability is confirmed; a new process/client would need its constructor GET counted in the next explicit budget.

## Conditional synthetic plan; NOT dispatched by this inventory continuation

Use only the client selected by the subsequent exact dispatch, retain `max_retries=0`, disable redirects on every request, and retain the original ledger. Every request must be HTTPS sandbox port 443 with unchanged environment Bearer value and no URL credentials. Permit only this synthetic create, its returned positive deposition ID, and its validated canonical same-origin file bucket/download. Reject action/publication/deletion routes, other IDs and unrecognized links before transport. Require matching private owner, unpublished state and `submitted is False` before any post-create mutation; this needs transport response validation because the service itself does not check owner.

Across this continuation and any resume: **at most one new create POST**, **one metadata PUT**, **one file-upload PUT**, and **eight post-inventory GET attempts** (including readbacks, bucket discovery and download). Automatic retries are zero. Any prior synthetic create/intent consumes the create allowance; a lost response consumes the attempted allowance and stops. If the subsequent dispatch creates a new client after this inventory-only pause, its constructor must run under the read guard and counts as the eighth GET; the normal synthetic sequence uses seven. Never rerun failed upload calls; only the explicitly required unchanged retry after complete success is permitted.

Use existing `OutputPaths(str(stage), 'sandbox')`, `DraftUploadService(paths, 'sandbox', canary_plan=None)`, and `service.upload(str(Path(paths.zenodo_json_dir) / expected_name), client)`. Require `success is True` and `publish_status == 'draft'`; otherwise stop with the original ledger intact. For a newly created source, returned ID must be absent from `pre_run_ids`; existing successful-ledger reconciliation uses its original ID and never creates. Record ID/owner/DOI only privately.

After service success, GET that same ID; require exact ID, expected owner, `submitted is False`, state not `done`, unchanged reserved DOI, zero `compare_metadata(expected_metadata, remote['metadata'])` differences, and `validate_files(remote['files'], artifact)` success. Download the sole expected file through a validated same-origin HTTPS:443 link with redirects disabled, stream at most 472 bytes and require exactly 471 bytes plus the expected SHA-256 and MD5. Stop if no supported same-host download link exists. Do not guess a link, use signed cross-host links, or bypass link checks.

Only after all those checks pass, call the same `service.upload` once more with unchanged payload and ledger. Require the identical deposition ID/DOI and zero additional POSTs, metadata PUTs or file PUTs. Perform a final same-ID GET and repeat exact metadata/files/owner/unpublished-state checks. The service's internal retry readback alone does not enforce owner or `submitted is False` for this synthetic path, so these explicit checks are mandatory. No second download is needed unless the code owner dispatches it separately. The normal first upload uses three GETs (initial deposition, bucket discovery, final service readback); explicit first readback, download, unchanged retry and final explicit readback add four, for seven total. The eight-GET ceiling is a hard bound, not authorization for an extra diagnostic or retry.

Immediately pause after synthetic verification. Do not progress to FGDC-100, FGDC-1839 or FGDC-3682 under this continuation.

## Receipts and mandatory stops

Return only frozen code/packet hashes, successful gate booleans, inventory counts/time/hash, method/stage attempt counts, expected-vs-observed checksum equality, and success/failure classifications in shared receipts. Send any required actual deposition ID/DOI/owner privately to the parent; never Git. Do not share raw response bodies, headers, exception strings, URLs, source-account titles or tracebacks. Persist original ledgers, counters and safe receipts locally, without replacing previous evidence.

Stop on any unsupported transport capability, changed binding, incomplete or stale inventory, duplicate, wrong owner/ID, unexpected state/file/link, redirect, non-200 read, ambiguous POST/PUT outcome, failed checksum/readback, exhausted budget/deadline, or retry mutation. No cleanup deletion, alternate namespace, replacement record, blind retry or lost-intent recreation.
