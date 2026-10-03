# Separately authorized fresh synthetic Sandbox run

Use the exact final commit supplied by the parent on
`handoff/pr8-synthetic-fresh-canary-20261003`. Its runtime is frozen at
`e93ce2af002c5c36a9e589bebc4e72c4d0089b57`.
The [validation receipt](synthetic_fresh_canary_validation.json) binds code and
the [new fictional packet](../../handoff/sandbox-fresh-canary-20261003-01/selection.json).
The packet inventory SHA256 is
`29ca42f8abcf04e27308ccefab2c92a0364f9a511ab247f5520fa57b39bf8a32`.

Brett explicitly approved a separately tracked Sandbox test after being told it
could leave one extra empty draft. His exact reported question/reply is retained
in [the authorization](../../handoff/sandbox-fresh-canary-20261003-01/authorization.json).
This authorizes a new test, while the original HTTP500 uncertain create remains
**permanently spent and held**. No original state, allowance, ledger, receipt or
clock is copied, renewed, reset or reconciled. Parent-reported 190 prior GETs stay
recorded as historical context. No original private folder is assumed present in
the code environment or opened here.

The sole provider executor remains `01a0fed7-bf71-7384-95fd-3434599df03f`.
The code owner made zero provider requests or writes. Parent dispatch remains
required; these instructions are transferable to the executor's separate environment.

## Fixed identity and transport bounds

- Source: `SYNTHETIC-PICES-FRESH-20261003-01`.
- Exact title: `SYNTHETIC TEST ONLY PICES FRESH 20261003 01`.
- At most **eight GET attempts, one empty create POST, one metadata PUT and one XML PUT**.
- A separate **30-minute clock** starts only during provider execution. Rerun never renews it.
- No automatic request retry, redirect, inventory scan, public/community query,
  publication, deletion, production path or authentic-source upload is permitted.

The initial owned-control GET verifies the intended account and rejects every
observed exact new-run title/source/file collision, malformed metadata/files and
file identity aliases. An empty owned response cannot prove account ownership.
This is explicitly **not a complete historical/own-run inventory claim**. The
separate authorization accepts the bounded new synthetic create; it does not
reconcile the original unknown POST outcome or relax production deduplication.

Creation requires HTTP201, a positive ID outside the observed reject set, correct
owner, an empty/unsubmitted draft and safe bucket links. The timezone-aware
creation timestamp must be within the current persisted POST interval, allowing
60 seconds of clock skew, and stay unchanged on readback. The returned ID and
any returned DOI are persisted before subsequent PUTs. A nonempty matching DOI is
required at final readback/retry. Exact metadata, file inventory,
checksums, downloaded XML and current DOI are verified. An unchanged service retry
must reuse that ID/DOI and consume no additional POST/PUT.

Every attempt is fsynced before transport in both controller state and an
independent attempt journal. A failed/uncertain create stays spent. Lost state or
ledger cannot reconstruct controls while the independent journal/evidence remains.
Any failed/incomplete process stops for parent review; there is no resume option.
A matching completed process rerun uses zero requests and reports
`cached=true, fresh_remote_check=false`.

## Exact provider execution

Use an isolated checkout of the parent's exact final commit and the executor's
working Python environment with `requirements.txt` installed. Keep the original
checkout/run intact. Choose **one new private stage outside the entire original
run root**, with the exact fresh source ID as its basename. The executor knows its
private paths; the placeholders below are not code-environment paths.

Before dispatch, verify code hashes from the receipt and all packet entries:

```sh
python - <<'PY'
import hashlib, json
from pathlib import Path
receipt = json.loads(Path('docs/readiness/2026-10-03/synthetic_fresh_canary_validation.json').read_bytes())
for path, expected in receipt['code_sha256'].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == expected, path
from scripts.synthetic_fresh_canary import packet_plan
packet_plan()
print('Frozen code and fictional packet verified; no provider request.')
PY
```

Stage once, offline. An existing stage is refused and never replaced:

```sh
PICES_FRESH_STAGE='/PRIVATE/NEW/RUN/SYNTHETIC-PICES-FRESH-20261003-01'
python -m scripts.synthetic_fresh_canary --stage-only --stage "$PICES_FRESH_STAGE"
```

`staged=true` proves only local preparation. It is not a completed live canary.
After parent dispatch, `ZENODO_SANDBOX_TOKEN` must already be set to the working
Sandbox token in the executor's private environment. Do not print its value.
Use the existing privately verified positive account-ID JSON:

```sh
(
  set -C
  python -m scripts.synthetic_fresh_canary \
    --stage "$PICES_FRESH_STAGE" --owner-file '/PRIVATE/VERIFIED-OWNER.json' \
    > '/PRIVATE/NEW/RUN/fresh-canary-sanitized-receipt.json'
)
```

The receipt path above must be new; `set -C` prevents overwriting an existing
receipt before execution begins. Preserve it on failure. Do not echo tokens,
share environment dumps or create substitute ownership evidence. Exit zero from
this second command requires completion or matching cached completion. A fresh
success must report `completed=true`, `exact_readback=true`,
`unchanged_retry=true`, `cached=false` and counts `{get:8,create:1,metadata:1,file:1}`.
The historical-plus-new maximum is 198 GETs, retaining the parent's reported 190.
Return the sanitized JSON to the parent and pause. Do not launch actual-source
records or another namespace/stage, and do not retry any failed result.

Inside this separate stage, `state/sandbox/` retains:

- `synthetic-fresh-grant.json`: fixed packet/source/owner/clock/limits.
- `synthetic-fresh-controller.json` and `synthetic-fresh-attempt-journal.json`:
  durable counters, binding and private returned ID/DOI.
- `synthetic-fresh-upload-ledger.json`: only this source's private draft state.
- `synthetic-fresh-response-evidence.json`: sanitized response projections.
- Separate controller and ledger locks.

All data/control parents and files must resolve inside the fresh stage. Symlinks,
nonregular files and hard-linked controlled files are rejected before use.
The entire old run root is excluded. These local files are execution evidence,
never upload inventories or release approvals; do not delete or manually edit them.

## Sanitized failure evidence and review

Response evidence retains HTTP status, enumerated MIME/format, bounded body size
and SHA256, completeness, known error-field names, fixed error categories and
attempt counts. Failed bodies are bounded to 64 KiB; accepted bodies to 12 MiB.
Raw body text, arbitrary headers/keys/values/links/account IDs and exception text
are omitted. Transport failure diagnostics preserve safe stage/type/status and
spent counters. This supports diagnosing repeated HTTP500/HTML/JSON failures
without disclosing private responses or allowing another create.

Independent review found and closed three gaps before final handoff: descendant
staging beneath the old root, missing observed identity fields, and control-path
symlinks. The receipt distinguishes full-suite and subsequent focused review
checkpoints. All original packet/FGDC source files remain unchanged.

PR8's reviewed metadata code is now merged, separately from this canary branch;
see [the merge verdict](pr8_merge_readiness_0db412d.json). Parent now reports verified
production access in a separate read-only executor; fresh remote identity/file/DOI
QA and release approval still gate production publication. Code merge does not
authorize publication. [Exact latest source/artifact inputs](production_readonly_source_inputs_4b13126.json)
bind merged main `4b131266cee68798fffed1c309e447a48a420185` for that executor.
Use that source commit for metadata work; this fresh-canary branch has separate
ancestry and must not substitute for the latest 396-source profile/runtime.
