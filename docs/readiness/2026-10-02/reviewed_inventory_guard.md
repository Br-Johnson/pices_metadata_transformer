# Reviewed replacement for the provider inventory guard

The full stopped-attempt guard has now been reviewed offline. Its actual failing
branch remains unknown: no response/status or completed validation stage was
retained. No new provider request was made during this review.

## Findings in the supplied guard

- `check_links` applied the sandbox host rule to every HTTP(S) per-record link.
  Only keys named `doi`/`conceptdoi` pointing to two DOI resolver hosts escaped
  that rule. This rejects inert external citation/HTML links and other DOI link
  keys or test resolvers even though the client does not follow them. This is an
  overly broad validation rule, **not a confirmed explanation of the failure**.
- `parsed.port` can raise before `require`, leaving no fixed classification.
- `parse_qs` without `keep_blank_values=True` ignores `token=` and similar blank
  credential query fields. The replacement checks them explicitly.
- Owned-record owner matching remains a necessary guard. Public community hits
  are not restricted to the authenticated owner. The old community fallback
  could accept missing `hits` as an empty array; the replacement requires shape.
- Request count was incremented before transport. No response milestone/status
  was retained until every check and raw-file write succeeded. A failed guard
  therefore erased useful evidence. Raw-body persistence is no longer necessary
  for the one-request diagnostic; receipts contain only bounded safe fields.
- Constructor wrapping erased `StopRun` classifications; the outer handler only
  recognized `StopRun`, so every wrapped failure became generic. Runtime safe
  diagnostics now preserve fixed stages/types/status. Set-up retry changes after
  construction cannot constrain construction; the constructor itself is now
  single-attempt and has redirects disabled.

## Replacement code and bounds

Use `scripts.sandbox_read_guard.SandboxInventoryGuard`, not an executor-edited
copy. Its default transport bound is **one GET**, and it only permits the sandbox
HTTPS origin on port 443 and the two inventory endpoints. Bearer value must stay
unchanged; credential query fields, writes and other paths/origins are rejected
before transport. Redirects are disabled, transport timeouts are bounded, and
streamed response bytes are capped at 12 MiB. Return-link URLs are never followed.
Only root pagination `self`/`next`/`prev` links are validated as actionable links;
per-record DOI/citation/HTML/bucket/action links remain inert. A future file or
write operation must apply its own explicit host/path checks.

The guard records request preparation, transport entry, response receipt, status,
JSON shape, owner checks, pagination checks and final completion independently.
Malformed URLs, transport/HTTP/schema/owner/link/cleanup failures have safe fixed
classification. Cleanup cannot overwrite a primary error or falsely increment
completed pages. No tokens, URLs, headers, response bodies or owner IDs appear
in `receipt()`. A valid empty owned list reports `owned_items=0` and does not
claim owner identity verification.

## Exactly one next observation, only after parent dispatch

Keep all existing private run directories and ledgers intact. Use the exact
reviewed commit supplied with this document. Do not retry the old guard or run
inventory pagination, POST, PUT, publication or deletion in this diagnostic step.
The code owner remains sole implementation writer.

From the provider checkout, use this exact Python sequence, retaining the private
`expected_owner_id` from the already verified provenance (do not publish it):

```python
import json
import os
import signal
import requests
from scripts.sandbox_read_guard import SandboxInventoryGuard
from scripts.zenodo_api import create_zenodo_client, load_zenodo_token, ZenodoAPIError

# expected_owner_id is the private integer already supplied to this executor.
receipt = {'status': 'setup_failed', 'writes_performed': 0}
guard = client = None
previous_handler = signal.getsignal(signal.SIGALRM)
def deadline(*_):
    raise requests.exceptions.Timeout('Bounded read deadline')
try:
    token = load_zenodo_token(sandbox=True)
    if token != os.environ.get('ZENODO_SANDBOX_TOKEN'):
        raise ValueError('Environment credential delivery required')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(300)
    with SandboxInventoryGuard(token, expected_owner_id, max_requests=1) as guard:
        client = create_zenodo_client(sandbox=True)  # exactly the constructor GET
    receipt['status'] = 'probe_passed'
except ZenodoAPIError as error:
    receipt.update(status='probe_stopped', diagnostics=error.diagnostics)
except Exception:
    receipt['status'] = 'setup_or_deadline_stopped_sanitized'
finally:
    signal.alarm(0)
    signal.signal(signal.SIGALRM, previous_handler)
    if guard is not None:
        receipt['guard'] = guard.receipt()
    if client is not None:
        try:
            client.close()
        except Exception:
            receipt['status'] = 'client_cleanup_stopped_sanitized'
print(json.dumps(receipt, sort_keys=True))
```

No raw exception string/traceback is emitted. The receipt distinguishes an
unreached response (`status=null`) from HTTP rejection or validation after an
observed response. HTTP 200 plus a later link/owner failure is not an auth failure.
Send the sanitized receipt to the parent and **pause after this single probe,
even on success**. A successful constructor alone is not a complete inventory or
permission to advance to writes; parent dispatch controls the next phase.

After the diagnostic is resolved, the same reviewed guard may be used with an
explicit parent-approved inventory bound (at most 240). Full inventory still
requires the reviewed client's pagination/total/ID checks. The existing
synthetic-first, source-plan, four-total-create, own-run idempotency and no
production/publication/deletion rules remain intact.
