> Superseded runnable instructions: use [bounded owned pagination](synthetic_owned_pagination.md) and its exact frozen commit. The ten-GET gate below is historical and stopped read-only; do not dispatch it again.

# Frozen synthetic-only owned-inventory canary

Public PICES community inventory is **not necessary for this disposable, sandbox-only synthetic namespace**. The exact synthetic source, original run directory, durable creation intent/ID, complete owned-deposition scan and guarded readback establish its relevant identity and idempotency boundaries. This narrowed authorization is usable only by the active frozen synthetic controller; ordinary upload paths reject it. Production and actual-source duplicate checkers still require their original public-plus-owned inventories.

The stopped public request was `GET /api/records` with `q=communities:pices`, `size=200`, `page=1`, returning HTTP 400. Its body was not retained; the cause is unknown. No size, query, credential or redirect cause is inferred or repaired here. An exact-query regression preserves safe HTTP-status classification. Public API compatibility remains a separate later task, not a prerequisite for this synthetic trial.

## Inputs and two separately dispatched commands

Use the exact commit supplied by the parent on `handoff/pr8-synthetic-owned-gate-20261003`. Keep the existing private run:

`/workspace/pices-sandbox-run-9379fd8-20261002/synthetic`

Keep all existing staged files, ledgers, controller state and failed inventory evidence. Do not create another namespace, delete a state file, reset counters or edit timestamps. The module verifies the unchanged packet inventory SHA-256 `428559c7a8e81e84c22627b0add1230797b92013f87152e2ee3024b56af30fd1`, every one of its 17 entries, and exact synthetic source/payload/metadata/artifact bindings.

The existing `ZENODO_SANDBOX_TOKEN` must come from the designated provider environment; no copying or printing credentials. The owner file is private JSON containing only the positive integer from previously verified account provenance.

**First parent dispatch — owned namespace check only:**

```sh
python -m scripts.synthetic_canary_controller --inventory-only --owner-file /path/to/private-owner.json
```

Only the owned-deposition list endpoint is permitted. The module verifies the account, obtains the complete owned inventory through the existing paginated client, and checks for the exact synthetic title, frozen source ID in metadata, or selected XML filename. A matching owned record, whether draft or published, requires reconciliation. Every full-scan item must expose metadata with a nonempty title and an explicit files list; each file must have a recognized name. Unknown identity fields, repeated IDs, incomplete pagination or owner mismatch stop safely.

This phase permits **10 new GET attempts maximum**, including constructor verification, with five previously observed requests recorded separately—well below the original 240 inventory-read ceiling. Each attempt is durably counted before transport. Responses are capped at 12 MiB; timeout is `(10, 30)` and the command has a 300-second deadline. No redirects, automatic retries or public-community queries occur. No draft is created.

The new scope receipt is `synthetic/state/sandbox/synthetic-owned-inventory-controller.json`. If the earlier `synthetic-inventory-controller.json` exists, it must match the reported stopped read-only attempt: failed, incomplete, two GETs, HTTP 400, same owner and packet. Its bytes are preserved and hashed into the new receipt. An existing synthetic upload ledger or write-controller state blocks this new gate. A repeated owned-gate command stops without requests; never reset its state.

Success binds the owned-only scope, owner, packet, and SHA-256 of retained owned records and the exact synthetic authorization. Return the sanitized receipt and **pause**.

**Second parent dispatch — only after the owned gate succeeds:**

```sh
python -m scripts.synthetic_canary_controller --owner-file /path/to/private-owner.json
```

The module is the complete executor entry point: no handwritten transport, inventory or upload wrapper. Generic pending/upload paths reject this reduced-scope saved grant; only the exact active `SyntheticTransport`, in sandbox with the pinned payload and matching grant bytes, can consume it. Unscoped production and actual-source behavior is unchanged.

## Synthetic operation and bounds

Only `SYNTHETIC-PICES-9379FD8-20261002` is allowed. Across restarts: **one create POST, one metadata PUT, one XML upload PUT and eight GET attempts maximum**. Every attempt consumes its durable allowance before transport. The returned positive ID is checked against the pre-run IDs and fsynced before updates; the existing service independently persists its intent and ID. Failed or uncertain outcomes stop on rerun rather than creating again.

All requests require HTTPS sandbox port 443, exact allowed paths/methods, unchanged Bearer value, and no query credentials, fragments, redirects or retries. Owner must match; state must be `unsubmitted` with `submitted` exactly false. Updates and reads address only the bound deposition. Bucket UUID and selected file path are checked. The command retains its 300-second deadline, 12 MiB JSON cap and exact 471-byte XML download bound.

The existing service creates the draft, updates metadata and uploads the one XML. The controller independently verifies metadata/files/owner/current reserved DOI and downloads the XML to match the pinned SHA-256. It calls the service once more with unchanged payload and ledger, requires the same ID/DOI and zero additional POST/PUTs, and verifies final readback. The eight GETs include constructor, service reads, independent readbacks, download and unchanged retry. A disappeared DOI cannot be replaced by a cached earlier value.

A completed module rerun validates its local bindings and ledger and returns `cached=true, fresh_remote_check=false` with **zero requests**. It does not claim new remote verification. Preserve `synthetic-controller.json` and the original upload ledger. Shared output includes only fixed completion/phase flags, counts and sanitized diagnostics; ID/DOI/account data remain private. Exit zero means completed or matching cached completion; exit one means stop.

Immediately pause after success. FGDC-100, FGDC-1839 and FGDC-3682 remain a separately dispatched stage under the existing narrow historical-duplicate exception. No publication, deletion, production request or actual-source upload is enabled. The synthetic still consumes its original slot within the four-total canary create cap.

## Validation

**284 guarded offline tests pass**, independently reproduced: 23 controller tests and four endpoint fixtures cover the narrowed gate, exact-query HTTP 400 classification, no public calls, same-run collisions, preserved old receipt, malformed collision fields, durable attempt caps, generic grant-consumption rejection, unchanged production/public inventory requirements, full synthetic readback/retry, uncertain creates and credential redaction. Review found and closed the missing-field and scope-consumption gaps. No provider request or write was performed by the implementation owner. Live owned inventory and synthetic execution remain for the separately dispatched provider task.
