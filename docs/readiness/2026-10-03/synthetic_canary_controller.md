# Frozen runnable synthetic canary controller

This controller closes the write-stage gap without changing the frozen packet, the existing read guard, the upload service, PR8 or the separate 70-record cohort. Its base runtime is `d5022b8828ef910749aef32371304f2b2b669674`. The parent reported that runtime's one-request diagnostic passed HTTP 200 with 25 owner-consistent items and every validation milestone. The historical failure cause remains unknown.

Execute only after the parent confirms the dispatched full inventory succeeded and supplies this controller's exact published commit. Check out that exact commit on its separate handoff branch; do not overlay an executor-written wrapper or use an unpinned branch tip. The runtime pins the unchanged packet INVENTORY SHA-256 `428559c7a8e81e84c22627b0add1230797b92013f87152e2ee3024b56af30fd1` and verifies all 17 entries itself.

## Inputs and command

Keep the original private run, staged files, checker output and every prior ledger/intent:

`/workspace/pices-sandbox-run-9379fd8-20261002/synthetic`

Do not create a replacement run directory, reset state, refresh timestamps by hand or copy credentials. The existing `ZENODO_SANDBOX_TOKEN` must be supplied by the designated provider environment. The token loader must return that exact opaque value. An owner file contains only the private positive integer from verified account provenance as JSON; it is input data, never committed or printed.

From the checked-out repository root, run the installed Python interpreter:

```sh
python -m scripts.synthetic_canary_controller --owner-file /path/to/private-owner.json
```

The module is the complete executor entry point. It fixes the run directory, source selection, sandbox origin, response limits and transaction sequence; the executor supplies no transport or upload logic. `--help` does not contact the provider. Exit zero means completed or a matching cached completion; exit one means stop. Shared stdout is one sanitized JSON receipt. Keep ordinary logs, state and account details private.

## Enforced preconditions and bounds

Only `SYNTHETIC-PICES-9379FD8-20261002` can execute. The controller verifies staged payload bytes, original XML SHA-256/size, full prepared metadata and artifact contract against the pinned packet. It requires the genuine, unexpired, sandbox checker authorization for that exact metadata hash and the retained complete inventory IDs. It refuses a preexisting synthetic upload ledger without its matching controller state. Unknown/partial old attempts require owner-led reconciliation; the controller never reconstructs their state.

- **One create POST**, **one metadata PUT**, **one exact XML upload PUT**, and **eight total GET attempts**, including the new bounded constructor check. Limits persist across process restarts. Each attempt is durably consumed before transport.
- **300-second overall deadline**, per-request `(10, 30)` timeout, JSON responses at most 12 MiB, downloaded XML exactly 471 bytes with the pinned SHA-256.
- HTTPS `sandbox.zenodo.org`, port 443, unchanged Bearer value; no URL credentials, query parameters, fragments, redirects or automatic retries. Production and other origins, action endpoints, other IDs/files and unsupported methods stop before transport.
- Only the returned, checked, owner-matching positive deposition ID may be updated. The controller fsyncs that ID before returning the create response to the service; the service separately persists its ledger ID before subsequent mutations.
- The response must be an owner-consistent `unsubmitted` draft with `submitted` exactly false. A canonical same-origin bucket UUID is required. The only supported download is the returned `links.download` matching that bucket and the exact selected filename. Unsupported live schema/link forms stop for code-owner review.

No actual-source candidate, publication, deletion, replacement or production operation is enabled. The one synthetic create consumes its existing slot in the four-total canary run cap; it is not a new allowance.

## Exact sequence and rerun behavior

The module constructs the client under the transport controller, invokes the existing `DraftUploadService` once, independently reads back expected metadata/files/owner/unpublished state/reserved DOI, and downloads the one XML to verify its bytes in memory. It then invokes the same service once unchanged with the original ledger and verifies the final readback. The unchanged service retry must preserve ID and DOI and issue zero additional POST/PUT operations.

Normal first execution uses eight GETs: constructor, initial deposition, bucket discovery, service readback, independent readback, XML download, unchanged service retry, final independent readback. It uses exactly one of each permitted write. Readback must retain the current reserved DOI; a previously observed DOI cannot mask its later disappearance.

After completion, invoking the same module again validates the original local bindings and completed ledger and returns `cached=true, fresh_remote_check=false` with **zero requests**. This reuses the proven outcome and does not pretend to perform a fresh remote check. Any failed/uncertain attempt remains stopped on rerun. No blind retry, automatic repair, alternate namespace or cleanup deletion is available.

The private durable control file is `synthetic/state/sandbox/synthetic-controller.json`; its separate lock covers the complete transaction. Preserve it together with the existing upload ledger. Private state retains ID/DOI/inventory bindings; the shared receipt exposes only counts, fixed phases, completion flags and sanitized allowlisted error classifications.

## Validation and dispatch receipt

Twelve offline controller tests exercise the full mocked flow and process rerun, durable state before writes, uncertain-create consumption, duplicate POST rejection, malformed origins/paths/Bearer values, redirects, owner/ID/publication/metadata/file mismatch, stale inventory, missing prior control state, credential redaction, cleanup failures and current DOI disappearance. Independent functional and security review cleared the controller after the DOI regression was fixed. The full guarded suite passes **269 tests** on this provider-runtime branch. No provider requests or writes were performed by the implementation owner.

After the controller prints its receipt, **pause**. Send that receipt to the parent; retain ID/DOI/account evidence privately. Success does not dispatch FGDC-100, FGDC-1839 or FGDC-3682. Those remain a separate parent-gated stage under the existing narrow historical-duplicate exception.
