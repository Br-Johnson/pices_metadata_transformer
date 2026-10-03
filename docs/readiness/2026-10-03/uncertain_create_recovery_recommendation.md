# Finite recovery decision for the uncertain empty POST

The actual remaining blocker is the server-side result of the sole empty-create
POST: HTTP500, no retained ID, one consumed create allowance and no metadata/file
PUTs. Parent reports the creation-time query returned HTTP200 with zero hits,
then both known-record controls passed (positive: exact owner/ID/schema/created;
negative: empty). **190 cumulative GET attempts** are recorded. Latest control
receipt SHA-256:
`5551ba3187c1add6fc77f86b408ebdb34a6a6cce9468ca62bd78bc1bae9fdee9`.
The prior empty-reconciliation receipt is
`2edf461d42ce6f1149b2c0c9e53f446dd28bc0d9932ceb24659ccd7a6e2e8792`.
These are parent-reported results; the code owner has not opened private provider
evidence or made provider calls. The control establishes query compatibility for
the known record, not empty-draft indexing or proof of transaction rollback.

The frozen controller remains `2a2c82fa257832986fdd62309a13462b691febda`.
Its original POST stays spent. All failed receipts, intent/ledger, old clocks and
cumulative counts remain evidence; do not reset them or start another run.
The title was never PUT, so a title/keyword lookup cannot identify this empty
draft. Repeating empty searches cannot remove that ambiguity conclusively.

## Recommended next evidence

Prefer one provider/backend confirmation of the original request's outcome.
The account owner or sole executor can supply the original UTC attempt interval,
private account identity, slashless endpoint, POST method, empty JSON body and
HTTP500 status to Zenodo support. Include an already retained correlation ID only
if one exists; the controller did not retain the 500 body/headers, so do not
invent one or send a token. Ask for the existing draft ID/transaction outcome
and server fault cause. The request shape is already supported by the official
API; another POST is not a diagnostic. No support message is sent by this task.

Alternatively, the account owner can inspect the authenticated uploads UI for
drafts around the saved attempt interval and record an explicit outcome. A UI
inspection is a finite decision input, not a mathematical absence proof. If
there is no identifiable draft, the choice remains either pause creation pending
backend confirmation or explicitly accept that residual uncertainty and authorize
one bounded replacement attempt. A replacement requires new explicit POST
authority and a consistent cumulative canary budget; the original attempt still
counts. Neither an empty UI view nor the existing trial grant silently supplies
that additional allowance. No new run, marker, budget or POST is created here.

## If a draft is eventually identified

Backend linkage to the original attempt, or an explicit account-owner decision
identifying that exact draft with adequate causal/account-activity evidence, can
support adoption. Timestamp, owner and absence from the partial old ID set alone
are only candidate evidence. Obtain exact-ID readback and verify owner, creation
time, unsubmitted state, empty files and empty user metadata (permitting only the
already-reviewed `prereserve_doi` reservation object), and checked Sandbox
bucket/DOI identity before proposing a binding. Keep the actual ID and account
details in private executor evidence.

The next concrete action would be a reviewed ID-only recovery path with POST
permanently disabled, preserving the original failed attempt/history and consumed
create counter. Bind only that identified ID/source/run/payload and the unused
one-metadata-PUT/one-file-PUT ceilings, with a fresh parent dispatch after any
expired timing grant. Then validate readback and unchanged retry. This document
does not bind a ledger, renew a clock or authorize those writes. Published or
nonempty/ambiguous drafts need separate review; do not erase them to manufacture
a clean candidate.

There is no requirement to poll indefinitely. The actual needed decision is
causal identity evidence for adoption, or explicit additional POST authority
that acknowledges the unresolved earlier attempt. Source QA continues while
that decision is pending. No publication, deletion, production credentials,
production write, merge or paid capacity is involved.
