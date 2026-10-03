# Fresh canary error diagnostic correction

Runtime correction is frozen at `9fdb393af11b38fea29dde64bd9569cee9ce3746` on normal branch
`handoff/pr8-fresh-canary-error-diagnostics-20261003`, descending from frozen
`f3eff050155fd713917e2287d5eade4f72fff5be`. This is a **no-write correction**,
not another canary dispatch. Both parent-reported HTTP500 creates stay consumed.
No provider request, private run-file read, retry, reset or new allowance occurred.

The previous projection discarded actual error messages and all response headers.
The correction retains a top-level JSON `message` string or HTML `title`/`h1`,
capped at 512 characters after redaction, and an integer body HTTP `status`.
It redacts current credentials in literal/recursive-percent/HTML/base64 forms, private
key/value fields, URLs, emails, paths, opaque values and numbers. Appended
structured payloads and tracebacks are omitted. Other body fields, nested error
objects, successful-response messages and raw plaintext bodies are not persisted.
Decoding is bounded to eight rounds and unresolved encoding is suppressed.
URL-safe/unpadded base64, UNC paths and active script/style content are covered.

Only `X-Request-ID`, `X-Correlation-ID`, `X-Trace-ID`, `traceparent`, `sentry-trace`,
`X-Amzn-Trace-Id` and `CF-Ray` can contribute identifiers. Values must fit bounded
UUID/hex or recognized trace syntax and cannot contain the configured credential.
Cookies, authorization, locations, unknown headers and malformed values are
omitted. Identifiers stay inert. Body fingerprints/status/completeness and durable
attempt counters are preserved for complete and partial failures.

Seven new contracts and fourteen existing fresh-canary contracts pass with global
Requests/socket blocks and dummy credentials. Failing-first retention demonstrates
the predecessor's omission. Fixtures cover durable failure evidence, failed rerun
with zero requests, encoded credentials, private fields, HTML/JSON/nested/plain/
large bodies, trace-header syntax and incomplete responses. Ruff F and diff checks
pass. Independent review is recorded in the [validation receipt](fresh_canary_error_diagnostics_validation.json).

The fictional packet and all request/state/identity/upload budgets are unchanged.
**Omitted past evidence cannot be recovered by this patch.** Never replay a failed
request or rewrite its receipt to imply a newly observed message. Future separately
authorized requests can use the corrected projection. A genuinely retained original
error response may be projected locally by its provider owner without replacing
failure receipts; this coding task reads no private response.

The [account-readiness plan](sandbox_account_readiness_plan.md) is prepared only.
It records Brett's reported write scope and absent email-verification control,
without turning unknown email state into a guessed cause or blocker.
