Reviewed offline transport diagnostics: repository handoff

This directory transfers reviewed diagnostic code. It is not integration ownership,
a runnable live canary, a live grant, a counter reset or a provider-stage update.
The two runtime files and all copied tests/runner are unchanged from their reviewed
versions. No private responses, live credentials, private thread identifiers or
provider state are included. Credential-looking test strings are fictional data.
The existing synthetic draft reference in write_observer.py is intentional.

Exact runtime SHA256
write_observer.py
  c039510536ab1e5f07ea7baad3ee0b2a2b95c89e095030668e5a01a0476baadc
response/response_capture.py
  b3e40ba97d2b6f382a714ea9a4da0ec3e6303ed716e0e32218d94708d5a51913

Minimal publication and complete execution layout
The manifest's repository_handoff_files lists files newly published here.
The manifest's files inventory instead binds the COMPLETE materialized execution
layout, excluding the manifest itself. Three support files are intentionally not
duplicated here: they already exist in repository commit
ecfba4ed3496c0a8d400eb2ace46800f0c166708. support_git_objects identifies their
source paths and destination paths. Copy them from those immutable git objects
outside the repository, then run the unchanged verifier. Missing support before
materialization is expected; running directly in this directory fails closed.

Materialization after the sole consumer has fetched the exact handoff commit
Use an isolated local object checkout containing that commit. The commands below
perform only local git-object reads and write a new temporary directory. Fill in
source_repo and handoff_commit from the transfer receipt; do not use a moving
branch name. No checkout, credential lookup, network request or install is needed.

    set -euo pipefail
    source_repo=/absolute/path/to/isolated/object-checkout
    handoff_commit=IMMUTABLE_COMMIT_FROM_TRANSFER_RECEIPT
    support_commit=ecfba4ed3496c0a8d400eb2ace46800f0c166708
    diagnostic_dir=$(mktemp -d /tmp/pices-run02-diagnostic-XXXXXX)
    chmod 700 "$diagnostic_dir"
    git -C "$source_repo" archive "$handoff_commit:docs/diagnostics/run02-transport-20261004" | tar -x -C "$diagnostic_dir"
    mkdir -p "$diagnostic_dir/support/scripts" "$diagnostic_dir/support/docs/handoff/modern-synthetic-canary-20261003-code-02"
    git -C "$source_repo" show "$support_commit:scripts/modern_synthetic_canary.py" > "$diagnostic_dir/support/scripts/modern_synthetic_canary.py"
    git -C "$source_repo" show "$support_commit:scripts/modern_canary_errors.py" > "$diagnostic_dir/support/scripts/modern_canary_errors.py"
    git -C "$source_repo" show "$support_commit:docs/handoff/modern-synthetic-canary-20261003-code-02/metadata-put.json" > "$diagnostic_dir/support/docs/handoff/modern-synthetic-canary-20261003-code-02/metadata-put.json"
    cd "$diagnostic_dir"
    sha256sum TRANSFER_MANIFEST.json
    # Compare with the independent transfer receipt before executing any file.
    # Use an existing interpreter with requirements-transport.txt already present:
    /absolute/path/to/python -B verify_and_test.py

The exact runner verifies every file's size/hash and membership before tests.
It pins support imports inside this materialized directory, clears the test-process
environment, blocks real sockets/DNS/processes/private-file reads and confines test
writes to temporary fixtures. Its audit hook protects these fixed reviewed tests;
it is not a general sandbox for arbitrary code. Existing absolute workspace paths
in copied tests are neutralized by the runner. response/README.txt's old standalone
unittest command is historical; the root command above is authoritative here.

Expected result: 40 methods (15 observer/composition,7 adversarial,18 response)
plus the three-case simulated demo. The optional --parser-check/--parser-deps flags
remain in the unchanged runner but are NOT supported by this minimal handoff; the
separate parser reproduction and dependencies are intentionally omitted. Use the
default command only. No dependencies are downloaded or installed by this packet.

Runtime and routing limits
Requires Linux/POSIX, including /proc/self/fd, fcntl and SIGALRM. It does not run
unmodified on native macOS. Pinned tested Python3.12.14, Requests2.34.2 and
urllib32.8.0. Tests cover a simulated HTTPS-origin-over-HTTP-proxy CONNECT case.
Existing stdlib
TLS, environment CA, verification enabled and zero adapter retry must remain
unchanged in any separately reviewed wiring. Fake-socket coverage does not prove
a live TLS handshake, proxy behavior, credential injection policy or origin receipt.

Observer use requires an exclusively owned existing Session and the exact fixed
body/target/conditional header. It delegates the original adapter/pool/connection,
captures local write entry/return/error, and preserves surfaced exceptions. A
successful local write is NOT proof that Zenodo received the body; a failed write
may have transmitted a prefix. Selected write failures can be swallowed by urllib3
before a200 response, which the offline tests reproduce without attributing any
historical live failure. Hooks begin after CONNECT/TLS setup and do not inspect
proxy credentials or actual cloud hops. Unknown/custom paths hold.

capture_response reads the response once. Persist only CaptureResult.artifact via
the caller's atomic private0600 writer; keep data only in private memory for
validation and close the response. Sanitization is limited, not a guarantee that
the artifact is safe for public logs. Hold unavailable/truncated/ambiguous captures.
Hashes describe decoded iterator bytes, not TLS or compressed wire bytes.

No live requests, receiver probes or counter changes are authorized here. Existing
provider ownership, bounded grants and spent attempts remain unchanged. This
handoff does not modify original FGDC, rubric, rights, DOIs or application runtime.
