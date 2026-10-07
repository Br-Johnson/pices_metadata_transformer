# First production record for the PICES community — operator runbook (2026-10-06)

This is the shortest honest path from the merged User-Agent fix to one
validated record published into the PICES community. It consolidates the
existing contracts; it changes none of them and grants nothing by itself.
Only the sole Mac executor runs the token-bearing steps, from a real terminal;
with Brett's 2026-10-06 authorization that executor is the Claude session in the
app's Terminal pane, reading the token from the Keychain.

Target: `FGDC-1319`, the first member of
[modern_pices_singletons26.json](modern_pices_singletons26.json). Its source
origin is literally "North Pacific Marine Science Organization (PICES)", it
prepares cleanly on the merged runtime (policy `modern-xml-pices26-v1`,
schema 5, one organizational creator, publication date 2003-06-16, nine
subjects, 4,992-byte original XML), and it is the natural first record for the
PICES community. Any other member of that list works the same way.

## Paths and identities

| Name | Value |
|---|---|
| Checkout | `/Users/brettjohnson/code/pices_metadata_transformer` at or after the merged head of the [User-Agent change](zenodo_user_agent_handoff.md) |
| Production operations root | `/Users/brettjohnson/Documents/Codex/2026-09-30/task-4/pices-production-operations` |
| `OUTPUT` | `<root>/output` (the `--output-dir` of every production command) |
| State root | `<OUTPUT>/state/uploads/production` (holds `uploads_registry.json*`, journals, intents, snapshots) |
| Zenodo owner (user ID) | `266679`, per [fgdc141_owned_inventory_no_match.json](fgdc141_owned_inventory_no_match.json) |
| PICES community | UUID `92279449-f6e1-422d-8610-40802567c58b`, slug `pices`, parent `null`, visibility public, submission policy open, review policy `members`, observed 2026-10-06 21:12 UTC |
| Sandbox canary receipt | `mac_sandbox_receipt_2026-10-05.zip`, SHA256 `f2141c916b38a53168edca63f0af79b47df3e9913653f3538aba040ca9a20f7c` |
| Token scopes | draft and capture `deposit:write`; publication `deposit:write deposit:actions` |
| Token source | Keychain item `pices-zenodo-production` (`--token-keychain pices-zenodo-production`) |

Run every command from the checkout with the Python 3.12 environment that
has `requirements.txt` installed, for example
`/Users/brettjohnson/.cache/pices-venv312/bin/python`. Never put the token in
an argument, a file, the shell history or captured output. The executors read it
from the macOS login Keychain item `pices-zenodo-production` when given
`--token-keychain pices-zenodo-production`, and prompt for it otherwise.

## 0. Probe D: the shipped User-Agent, no token

```bash
python3 -c "import http.client, ssl, sys; sys.path.insert(0, '.'); from scripts.modern_singleton_executor import USER_AGENT, MIME; c = http.client.HTTPSConnection('zenodo.org', timeout=20, context=ssl.create_default_context()); c.request('GET', '/api/communities/pices', headers={'Accept': MIME, 'Accept-Encoding': 'identity', 'Connection': 'close', 'User-Agent': USER_AGENT}); r = c.getresponse(); print(r.status, r.getheader('Content-Type'), r.getheader('X-RateLimit-Limit'), len(r.read()))"
```

Expected: `200 application/vnd.inveniordm.v1+json 133 <bytes>`. An HTML 403
means stop; the value needs review before any one-shot action.

## 1. Prepared input and preparation packet (offline)

The executor reads `<OUTPUT>/data/zenodo_json/FGDC-1319.json`, which must carry
the current artifact policy (`artifact_policy.creator_interpretation.manifest_sha256`
equal to `15c654dc714849327b827363071a1da3ad7c3fa20c2c95a990d7868e75e96bd2`).
If the file is missing or older, regenerate it exactly as the test fixtures
do, into the production output root:

```bash
SRC=$(mktemp -d) && cp FGDC/FGDC-1319.xml "$SRC/" && python -B scripts/collection_qa.py --source-dir "$SRC" --output-dir "$OUTPUT" --authority-manifest docs/readiness/2026-10-02/rehosting_authority.json --access-interpretation-manifest docs/readiness/2026-10-02/contact_source_interpretation.json --creator-interpretation-manifest docs/readiness/2026-10-02/exxon_citation_interpretation.json --contributor-access-interpretation-manifest docs/readiness/2026-10-02/contributor_source_interpretation.json --collective-creator-interpretation-manifest docs/readiness/2026-10-03/dfo_staff_citation_interpretation.json --institution-creator-interpretation-manifest docs/readiness/2026-10-04/source_citation_credits_426.json --source-link-interpretation-manifest docs/readiness/2026-10-03/historical_dataset_linkage_21.json --source-title-interpretation-manifest docs/readiness/2026-10-04/source_display_titles_42.json --source-scope-attestation-manifest docs/readiness/2026-10-03/source_scope_reconciliation_904.json --dataset-access-interpretation-manifest docs/readiness/2026-10-04/finite_source_resource_access_655.json
```

Then produce the preparation packet (zero provider requests):

```bash
python -B -m scripts.modern_singleton_executor prepare --json-file "$OUTPUT/data/zenodo_json/FGDC-1319.json" --output-dir "$OUTPUT" > "$OUTPUT/../evidence/pices26/FGDC-1319.preparation.json"
```

Keep that packet: the bridge, QA and publication stages all require it. Its
`binding` is the preparation binding used below.

## 2. Fresh owner inventory, duplicate proof and create grant

The create grant and the duplicate proof must be reviewed documents, fresh
within an hour, bound to the preparation binding and the state root. The proof
asserts that the owner's current records contain no copy of this source. The
operator toolkit captures the inventory through the production transport with
the Keychain token, which also verifies that the stored token works, and
writes raw page receipts plus a summary document:

```bash
python -B -m scripts.modern_operator inventory --evidence-dir "$OUTPUT/../evidence/pices26" --captured-by "Claude Fable 5.1 (capture)" --token-keychain pices-zenodo-production
```

It lists `/api/deposit/depositions` fifty records a page until an empty page,
at most one hundred pages, fetches the detail of any record whose listing shows
no files (at most twenty-five), writes raw receipts as `.partial` files until
the capture completes, and prints the inventory path, its SHA256 and the record
count. The legacy listing's coverage of RDM drafts is unproven; drafts created
by this chain are known through the journal, which the executor checks before
every write. An independent reviewer then reads the inventory summary against
the source's title, `FGDC-1319.xml` and any mention of `FGDC-1319`, and signs
the minting with its own name. Minting is offline; it refuses on any match (title, file name, file MD5
against the XML, SHA256 literal, or source-id mention), on any record whose
files cannot be seen unless its ID is protected, excluded, in the modern journal
or passed as `--known-record`, on an inventory older than fifty minutes, on a
mismatched owner, on an existing intent or journal row for the source, and on
any window over ten minutes. It only reports success after the executor's own
`authorize` accepts the two documents, and it removes both files if anything
fails after the first write. A capture that holds names its stage, page and
status in its reason and leaves only `.partial` receipts. Use new output names
for every attempt:

```bash
python -B -m scripts.modern_operator mint-create --json-file "$OUTPUT/data/zenodo_json/FGDC-1319.json" --output-dir "$OUTPUT" --inventory "$OUTPUT/../evidence/pices26/inventory-<STAMP>.json" --owner 266679 --reviewer "<reviewer identity>" --canary-receipt-sha256 f2141c916b38a53168edca63f0af79b47df3e9913653f3538aba040ca9a20f7c --grant-out "$OUTPUT/../evidence/pices26/FGDC-1319.create-grant-<STAMP>.json" --proof-out "$OUTPUT/../evidence/pices26/FGDC-1319.create-duplicate-proof-<STAMP>.json"
```

One inventory can serve several records minted within its fifty-minute life.
Mint immediately before step 3; the grant window is ten minutes.

## 3. Preflight, then the one-shot draft create

```bash
python -B -m scripts.modern_singleton_executor preflight --json-file "$OUTPUT/data/zenodo_json/FGDC-1319.json" --output-dir "$OUTPUT" --grant "$OUTPUT/../evidence/pices26/FGDC-1319.create-grant-<STAMP>.json" --duplicate-proof "$OUTPUT/../evidence/pices26/FGDC-1319.create-duplicate-proof-<STAMP>.json"
```

A `{"binding": ..., "provider_requests": 0}` line means the whole offline
contract holds. Then, inside the same ten-minute window:

```bash
python -B -m scripts.modern_singleton_executor execute --json-file "$OUTPUT/data/zenodo_json/FGDC-1319.json" --output-dir "$OUTPUT" --grant "$OUTPUT/../evidence/pices26/FGDC-1319.create-grant-<STAMP>.json" --duplicate-proof "$OUTPUT/../evidence/pices26/FGDC-1319.create-duplicate-proof-<STAMP>.json" --token-keychain pices-zenodo-production
```

It reads the token from the Keychain, then performs at most four writes (create, file
init, XML upload, commit) and five readback GETs, and prints the verified
identity. The record is a private draft; nothing is published. The journal row
in `<state root>/uploads_registry.json.modern-v1.json` reaches phase
`verified`. A held result after the journal row appears keeps everything spent and
retained; do not rerun. A `"stage":"token"` hold happens before any attempt
and spends nothing; fix the Keychain item or terminal and rerun inside the
window.

This is the real API test with a validated record. If it holds with an HTML
403 on the first request, the User-Agent value is being rejected and the
evidence sidecar beside the journal shows the page.

## 4. From draft to accepted PICES membership

The remaining stages are documented in the
[community-first handoff](modern_pices_community_handoff.md) and use the same
`--json-file`, `--output-dir`, `--preparation`, `--old-grant` and
`--old-duplicate` arguments, pointing at the three files from steps 1 and 2:

1. `capture` with a schema-1 capture grant (`modern-singleton-capture-grant-v1`,
   limits `{"get": 5}`, `documents: {}`, binding = the bridge binding printed
   by `bridge`): five GETs, saved as `<state root>/FGDC-1319.modern-snapshot-v1.json`.
2. Raw duplicate evidence by title against external repositories and the
   independently reviewed production projection
   (`modern-production-duplicate-v1`), plus the reviewed PICES authority
   projection (`modern-pices-authority-v1`) from one community capture and one
   authenticated permissions capture. All three must be reviewed by someone other
   than their capturer, within one hour.
3. `prepare-qa`, then record approval and program review in the QA manifest,
   then `scripts.release_manifest` and the separate human release decision.
4. The v2 publish grant (`modern-singleton-publish-grant-v2`, limits
   `{"get": 22, "review": 1, "submit": 1}`, `exclusive_writer: true`,
   `documents` = the SHA256 of the snapshot, QA, duplicate and release files,
   `community` = the reviewed projection), `preflight`, then `publish`: one
   review PUT, one submit-review POST with `require_review: false`, and the
   accepted-membership readback. `release_complete: true` is the finish line.

Every projection's `reviewed_projection_sha256` is computed with
`scripts.modern_publication_qa.community_projection_hash` or
`production_projection_hash` over the projection without its review fields.
The windows are tight: community and production evidence expire one hour after
capture, grants last ten minutes, and record review must follow all evidence.
Plan steps 2 to 4 of this section as one sitting.

## What is still open

- FGDC-141 keeps its spent create and its separate GET-only observation route;
  this runbook does not touch it.
- Per record, the chain costs up to 14 draft-stage, 5 capture and 24
  publication requests and one human release. A batch path for the 3,839
  prepared targets does not exist yet; the QA validator accepts one record per
  manifest. Design that only after the first record completes end to end.
