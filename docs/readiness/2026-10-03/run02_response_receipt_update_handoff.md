# Run02 response receipt update — 2026-10-04

This updates the current execution guidance for the
[complete-schema repair](run02_complete_schema_repair_handoff.md). Its original
handoff, validation receipts, failed stages and spent counters remain historical
evidence. This change adds response facts; the 517-byte PUT, four pinned schemas,
same-draft routes, warning acceptance and PUT1/GET1 ceiling are unchanged.

## What the actual evidence establishes

Parent corrected PUT2's receipt interpretation: nonempty errors stopped the
controller before identity comparisons. The `identity_validation` phase names a
code location, not a failed identity comparison. Its response has
`observed_bytes: 3282`; an earlier lookup of `body_bytes` returned null because it
used the wrong key. GET197 predates PUT2 and establishes no later persistence.
Publisher omission explains the verified publisher error. The discarded second
field remains unknown, and the source-backed `files.enabled` warning is only a
candidate explanation. Publisher/file-error methods do not themselves explain
all six missing metadata fields or the access mismatch. The current
`application/json` request format remains unchanged.

The pinned [publisher validator](https://github.com/inveniosoftware/invenio-rdm-records/blob/d4a4ef21ef5cd99b6d1350b537c82581799296a3/invenio_rdm_records/services/pids/providers/datacite.py#L272-L306)
and [empty-file component](https://github.com/inveniosoftware/invenio-drafts-resources/blob/v11.0.3/invenio_drafts_resources/services/records/components/base.py#L121-L154)
append their errors without themselves clearing metadata/access. The
[draft update](https://github.com/inveniosoftware/invenio-drafts-resources/blob/v11.0.3/invenio_drafts_resources/services/records/service.py#L275-L317)
uses valid parsed data, commits the draft and returns accumulated errors, while
the [request parser](https://github.com/inveniosoftware/invenio-rdm-records/blob/d4a4ef21ef5cd99b6d1350b537c82581799296a3/invenio_rdm_records/resources/config.py#L275-L280)
explicitly accepts `application/json`. These are source-method observations, not
proof of the live deployment or PUT2 persistence.

## Facts recorded before validation stops

Each response entry retains its own method/action, status, `observed_bytes`,
`body_sha256` and `body_complete`. The exact vendor MIME
`application/vnd.inveniordm.v1+json` is recognized without retaining arbitrary
header text. Complete decoded credential-clean bodies record fixed root and
metadata/access/files/errors/pids/parent container presence and types. Missing,
null and wrong-shaped containers remain distinguishable.

The selected repair adds all seven expected metadata-field comparisons, access
comparisons and bounded safe error paths before status or record checks. Its
`exact_missing_upload_warning_present` recognizes an exact warning even alongside
another error; `only_exact_missing_upload_warning` distinguishes the sole exact
error. Recognition grants no allowance. `record_contract_validated` and
`exact_missing_upload_warning_accepted` become true only after the existing full
metadata/access/identity/files/DOI contract passes for that response.

Held output includes the sanitized separate response entries. Partial/capped or
malformed bodies cannot claim complete container/contract observations. A
credential echo, including supported encoded forms, suppresses those projections
and the body fingerprint. Beginning GET clears the legacy flat latest diagnostic;
an interrupted GET cannot inherit the successful PUT's flags. A complete HTTP200
body or a phase label alone still proves neither persistence nor canary completion.

## Refresh the runtime-bound private preflight

Parent reports the previous actual private preflight passed at `cd4f5e2`, with
380 historical files / 381 bound entries and zero requests. This update changes
three provider runtime hashes. That prior runtime binding cannot authorize this
code, although the corrected prepared body remains exactly 517 bytes, SHA256
`71830ca80356953b8654dd0e589eeff15b1b46c08c313b98372936c85c09da7a`.

After current-head CI and Codex review, the sole executor uses the existing
staging/preflight commands from the original handoff at a fresh parent path with
the same required namespace basename. Preserve the prior pristine preflight
stage, every failed stage, grant, receipt and expected-hash inventory. Reuse the
sealed historical hash evidence, declare complete selected evidence coverage,
and compute the actual new inventory count/hash; never replace old state or
derive a new baseline from unchecked current files. The 357 dummy count is a
sanity floor/example, not the actual topology's required count.

Return the new actual preflight runtime hashes, binding and inventory count/hash
to parent. Only parent binds a fresh matching grant of at most 600 seconds and
dispatches executor `01a0fed7-bf71-7384-95fd-3434599df03f`. The same-draft PUT3
and subsequent validated GET198 remain the only permitted actions. An unknown
error or missing field holds with this response evidence; no guessed payload,
repeated PUT, new create or automatic canonical GET follows a failed PUT.

## Minimal remaining route after successful repair

The repair verifies metadata only. A separately reviewed continuation must bind
its successful PUT/GET receipt and current canonical draft, preserve all seven
metadata fields, and allocate a DOI once if absent, initialize the exact file,
upload its bytes and commit it. Draft/list/content readback followed by the same
three unchanged GETs then tests persistence and idempotency. With a DOI allocation,
this adds three POSTs, one content PUT and six GETs, reaching cumulative GET204;
it is outside the current repair grant. Do not reuse the older owned-continuation
CLI, which is bound to older evidence and includes another metadata PUT, or use
the repair's absent-DOI validator after allocation.

Production needs a source-aware modern mapping, actual-source Sandbox trials,
current inventory and duplicate reconciliation, exact existing ID/DOI/file
preservation, draft QA and bounded release with remote verification. Existing
publication-goal authority and accepted rehosting/access interpretations remain
settled. Research the 37 deferred source cases and alias crosswalks; raise only
irreducible source evidence, exact terms or canonical identity decisions. Preserve
all 4,206 original XML, 3,638 supported / 562 held / 6 malformed accounting and
the exclusion of unrelated poster10042430. Root performs no provider operations.
