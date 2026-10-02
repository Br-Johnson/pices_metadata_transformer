# Constructor probe diagnosis: safe evidence, no blind retries

The provider is paused with zero writes. A prior urllib GET with `page=1&size=5`
returned HTTP 200; the later Requests constructor GET omitted those parameters
and passed through a provider-owned Session.send guard. The guard counted one
invocation before transport, but retained no completed stage or HTTP response.
This does not establish transport completion, authentication failure or a schema
failure. The guard source has not reached the code owner and is not reviewed.

Differences identified offline: query shape/default page size; urllib versus
Requests transport/proxy behavior; Requests session headers, pooling and redirect
handling; the external guard; and prior application GET retries. None is proven
to be the cause. The runtime URL/query behavior is deliberately unchanged.

## Reviewed diagnostic interface

`ZenodoAPIError.diagnostics` contains only these bounded fields:

- `stage`: constructor_probe, api_request, bucket_upload, request_prepare,
  transport, response_status, response_json, response_owner or response_links.
- `exception_type`: a fixed allowlist (HTTPStatus, ProxyError, SSLError,
  ConnectTimeout, ReadTimeout, Timeout, ConnectionError, InvalidHeader,
  JSONDecodeError, RequestException, ValueError, AssertionError or unknown).
- `status`: observed integer HTTP status 100–599, otherwise null.
- `retryable`: transient-classification hint only, never permission to rerun.
- `attempt`: bounded attempt number.

Constructor probes issue at most one request attempt with redirects disabled. Invalid headers, guard/
schema failures, TLS/proxy configuration failures and unknown exceptions are not
retried. Ordinary non-POST transport retries remain limited and class-specific.
The exception text, URL, headers, body and original chained traceback are not
retained in diagnostics. Arbitrary exception class names/attributes are ignored.
Existing generic error-string interfaces remain compatible when no diagnostic
fields were explicitly set. Bucket error handling uses the same sanitizer.

A guard that has observed HTTP 200 and then rejects owner shape can communicate
that safely using a fixed message and stage, never a token or raw response:

```python
raise ZenodoAPIError('Response guard rejected owner shape',
                     stage='response_owner', exception_type='ValueError',
                     status=200, retryable=False)
```

Do not label an exception as a response failure unless a response was actually
received. For an unstructured guard ValueError the constructor can report only
its safe category and a null status; it cannot infer the guard's internal stage.

## Minimum next handoff, before another provider request

The parent/provider should supply **the guard implementation source only**, with
credential values, request/response examples and private account data omitted.
The code owner needs the guard's Session.send delegation, status/JSON checks,
owner schema check and link validation logic. No network operation is needed to
supply this. Review it against dummy response fixtures before changing the guard.

After that review and explicit parent dispatch, at most one instrumented,
read-only constructor probe may be considered. Capture bounded milestones
`request_prepared`, `transport_entered`, `response_received`, followed by each
validation stage; false/unreached is distinct from failed. Emit only the bounded
`diagnostics` object, stage-completion booleans, request count and HTTP status
when observed. Never serialize exception vars, prepared requests, response
objects, URLs, headers, body, owner IDs, secret placeholders or raw tracebacks.
No POST/PUT, no retry loop and no authentication conclusion from a null status.

No such diagnostic probe has been run by the code owner. Synthetic and actual
source execution remain paused until the constructor/guard issue is resolved.
The sandbox duplicate exception is a separate commit and cannot override this
transport/response gate.
