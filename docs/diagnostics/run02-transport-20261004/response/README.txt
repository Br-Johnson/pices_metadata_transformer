Offline response capture helper

Interface:
    from response_capture import capture_response
    captured = capture_response(response, explicit_approved_token)
    # Persist captured.artifact only, using the caller's private atomic 0600 writer.
    # Feed captured.data to the controller instead of response.json()/content/text.
    # Check HTTP status and application validation errors independently.
    # Stop/reconcile if artifact.snapshot_available is false.
    # Close the response in the caller's finally block, especially after cutoff.

No network access, environment access, credential lookup, logging or filesystem
write occurs in the helper. Its only dependency is the existing pure module
scripts.modern_canary_errors from the repository checkout on PYTHONPATH.
The original data field is intentionally omitted from CaptureResult repr.

Bounds and meaning:
- At most 65,536 response bytes retained in the capture buffer. One iter_content
  traversal, with early stop on overflow; the caller closes the response.
- Sanitized snapshot compact UTF-8 encoding is also capped at 65,536 bytes.
  The containing diagnostic artifact has additional bounded field overhead.
- Timestamps identify capture start/end, not the request's send time.
- iterator_exhausted records stream exhaustion separately from body_complete.
  content_length_check explicitly says verified, unavailable for absent length
  or decoded content, invalid, mismatch or conflicting framing. Malformed
  Content-Length, unknown Content-Encoding/Transfer-Encoding and simultaneous
  Content-Length/Transfer-Encoding hold the snapshot. Supported content coding
  classes are identity, gzip, deflate, br and zstd. Decoding capability belongs
  to the supplied response iterator. None proves TLS/origin receipt or full
  wire framing; decoded lengths cannot validate compressed wire lengths.
- Hash, when present, describes complete bytes supplied by iter_content,
  normally decompressed by Requests. It is not a wire-body hash.
- Hash is suppressed for credential echoes, credential/header-block redaction,
  and any held snapshot. No partial-body hash is claimed as a complete hash.
- Content-Type, Content-Length, ETag, Date, X-Revision-Id, X-Revision and Revision
  are retained with narrow syntax checks. Existing _safe_trace_headers also
  supplies allowlisted trace identifiers for every status, including 200.
  No custom outbound header is added.
- 200, 400 and 412 responses are captured alike. Success/validation interpretation
  remains the controller's responsibility.

Scope and limits:
Known token literal, percent/HTML encoded and base64 variants are filtered in
decoded strings/keys. Conventional credential keys and textual assignments,
Bearer/Basic values, URL-bearing strings and JSON header blocks are redacted.
This is not universal secret detection. Other personal or private metadata can
remain in the full object. The artifact is private-only and is not approved for
public issue/PR/log output. Split or unknown credential encodings are not a
claimed detection capability. Unsupported JSON, duplicate keys, nonfinite
numbers, oversize/deep structures, ambiguous encodings, key-redaction collisions
and stream errors hold the snapshot and retain fixed diagnostics only. Original
parsed data may still be returned on a post-parse hold; never persist that data.

Run from this directory:
    PYTHONPATH=/workspace/pices_metadata_transformer python -m unittest -v test_response_capture

Tests use fake responses and dummy tokens only; no credentials or real requests.
