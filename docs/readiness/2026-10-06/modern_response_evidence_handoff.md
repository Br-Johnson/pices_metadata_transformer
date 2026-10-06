# Bounded response diagnostics after the first create403

Parent reports the first production `POST /api/records` returned403 at12:05UTC
on October6. The original body and Location were not retained. Its create intent
and request count remain spent, with no verified record identity or publication.
A later credential-free GET returned403 HTML describing unusual network traffic;
this does not establish the earlier POST's cause. Do not change credentials,
bypass the restriction, reset state or retry creation.

## Changed behavior

Both modern draft and community-publication callers preserve minimal status,
captured byte count and a safe full-response hash before checking HTTP status,
MIME, JSON or record semantics. The Mac transport returns an explicit immutable
response containing status, Content-Type, Location and read completeness. It
still uses verified TLS, the fixed production host, a20-second request deadline,
the1MiB response limit, no redirects and no automatic retries. Read interruptions,
premature Content-Length EOF and unfinished chunked EOF remain failures.

Each received response gets an exclusive mode0600, file-and-directory-fsynced
JSON sidecar beside its existing journal. The filename is derived only from the
journal, source ID, grant digest and request index. The receipt binds its exact
bytes by SHA256. Existing files cannot be overwritten. A failure saving a sidecar
leaves the request spent and its minimal response status recorded; no next action
is sent. Historical journals and intents are never rewritten to add diagnostics.

The sidecar retains at most64KiB of a complete safe body, base64-encoded, with a
separate prefix hash and explicit truncation status. Its full-response hash refers
to all received bytes only when the response is complete and credential-free
under the screening contract. Incomplete bodies have no retained body or full
hash; their byte count is a captured-prefix lower bound. Body evidence is outside
the journal, so large diagnostics do not consume its existing1MiB reader limit.

Credential screening examines complete inputs before prefix selection. It checks
literal, UTF16, escaped JSON/hex, nested percent/HTML and standard/URL-safe base64
token forms, plus explicit credential assignments. A credential in either allowed
header also suppresses the body, headers and raw hash. Unresolved normalization
at the depth bound is suppressed. Only Content-Type and Location are read from
the response headers. Location query/fragment are removed; userinfo, malformed,
duplicate or control-bearing values are omitted. Neither Location nor diagnostics
are used to dispatch requests or establish identity. Exception text, cookies and
authorization headers are never persisted.

Existing offline three-value injected transports remain accepted. Exact raw
publication snapshot and completion-marker schemas remain unchanged. Publication
still preserves reject-only DOI observations before later MIME/status rejection.
The explicit PR43 historical-runtime bridge covers only the six prior singleton
policies with exact nonruntime evidence and original journals/intents.

## Validation and execution boundary

Affected guarded tests cover the real mocked Mac transport, error responses,
redirects, malformed bodies and framing, boundary credential encodings, bounded
sidecars, failed persistence, original spent intent/no replay and the shared
publication caller. CI and independent review must cover the final frozen head.

This change cannot reconstruct the missing original403 body, reconcile an unknown
record ID, authorize another provider request or unblock publication by itself.
Keep the old Mac runtime and submitted payload immutable. The separate read-only
unknown-create reconciliation contract and the supported network recovery must
be reviewed before parent dispatches the sole Mac executor. Do not run a new
create merely to exercise diagnostic capture.
