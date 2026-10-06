# First production record for the PICES community — operator runbook (2026-10-06)

This is the shortest honest path from the merged User-Agent fix to one
validated record published into the PICES community. It consolidates the
existing contracts; it changes none of them and grants nothing by itself.
Only the sole Mac executor runs the token-bearing steps, from a real terminal.
The code lane that wrote this runbook cannot run them: it holds no token, and
its session is blocked from the production state folder.

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

Run every command from the checkout with the Python 3.12 environment that
has `requirements.txt` installed, for example
`/Users/brettjohnson/.cache/pices-venv312/bin/python`. Never put the token in
an argument, a file, the shell history or captured output; the executors
prompt for it.

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
python -B -m scripts.modern_singleton_executor prepare --json-file "$OUTPUT/data/zenodo_json/FGDC-1319.json" --output-dir "$OUTPUT" > "$OUTPUT/../evidence/FGDC-1319/preparation.json"
```

Keep that packet: the bridge, QA and publication stages all require it. Its
`binding` is the preparation binding used below.

## 2. Fresh owner inventory, duplicate proof and create grant

The create grant and the duplicate proof must be reviewed documents, fresh
within an hour, bound to the preparation binding and the state root. The proof
asserts that the owner's current records contain no copy of this source. Capture
the inventory with the token read into the shell, never typed into a file:

```bash
read -rs -p 'Production token (deposit:write): ' ZT; echo; mkdir -p "$OUTPUT/../evidence/FGDC-1319"; for p in 1 2 3; do curl -sS --fail --max-time 20 --max-redirs 0 -A 'pices-metadata-transformer/1.0 (+https://github.com/Br-Johnson/pices_metadata_transformer)' -H "Authorization: Bearer $ZT" -H 'Accept: application/json' "https://zenodo.org/api/deposit/depositions?page=$p&size=100&sort=mostrecent&all_versions=true" -o "$OUTPUT/../evidence/FGDC-1319/inventory-page-$p.json"; done; unset ZT; python3 -c "import json,glob; rows=[r for f in sorted(glob.glob('$OUTPUT/../evidence/FGDC-1319/inventory-page-*.json')) for r in json.load(open(f))]; print(len(rows), 'owned records; titles containing PICES Scientific Report No. 18:', [r['id'] for r in rows if 'No. 18' in r.get('title','')])"
```

Stop at the first empty page. Review the listing yourself: no owned record may
already carry this source's title, its file `FGDC-1319.xml`, or its XML
SHA256. Then mint the two documents with your name as reviewer. The grant
window is ten minutes, so mint immediately before step 3:

```bash
python -B - <<'EOF'
import hashlib, json, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, '.')
from scripts.modern_singleton import encode
from scripts.modern_singleton_executor import EXECUTOR, LIMITS, ORIGIN
OUTPUT = Path('/Users/brettjohnson/Documents/Codex/2026-09-30/task-4/pices-production-operations/output')
EVID = OUTPUT.parent / 'evidence' / 'FGDC-1319'
REVIEWER = 'Brett Johnson'   # the human who reviewed the inventory listing
OWNER = '266679'
packet = json.loads((EVID / 'preparation.json').read_bytes())
state_root = str((OUTPUT / 'state' / 'uploads' / 'production').resolve())
sha = lambda b: hashlib.sha256(b).hexdigest()
inventory = b''.join(p.read_bytes() for p in sorted(EVID.glob('inventory-page-*.json')))
history = (OUTPUT / 'state' / 'uploads' / 'production' / 'uploads_registry.json.modern-v1.json')
history_bytes = history.read_bytes() if history.exists() else b'{}'
now = datetime.now(timezone.utc).replace(microsecond=0)
proof = {'schema_version': 1, 'origin': ORIGIN, 'owner': OWNER, 'binding': packet['binding'],
         'state_root': state_root, 'complete': True, 'history_reconciled': True,
         'checked_at': now.isoformat(), 'expires_at': (now + timedelta(minutes=55)).isoformat(),
         'matched_record_ids': [], 'matched_dois': [],
         'inventory_sha256': sha(inventory), 'history_sha256': sha(history_bytes), 'reviewed_by': REVIEWER}
proof_path = EVID / 'create-duplicate-proof.json'
proof_path.write_bytes(encode(proof))
grant = {'schema_version': 1, 'approved': True, 'executor': EXECUTOR, 'origin': ORIGIN,
         'binding': packet['binding'], 'state_root': state_root, 'owner': OWNER, 'limits': dict(LIMITS),
         'started_at': now.isoformat(), 'expires_at': (now + timedelta(minutes=10)).isoformat(),
         'duplicate_proof_sha256': sha(proof_path.read_bytes()), 'reviewed_by': REVIEWER,
         'token_scope': 'deposit:write', 'draft_only': True,
         'canary_receipt_sha256': 'f2141c916b38a53168edca63f0af79b47df3e9913653f3538aba040ca9a20f7c'}
(EVID / 'create-grant.json').write_bytes(encode(grant))
print('proof and grant written; window ends', grant['expires_at'])
EOF
```

`matched_record_ids: []` is your statement that the review found no match;
do not mint it before looking.

## 3. Preflight, then the one-shot draft create

```bash
python -B -m scripts.modern_singleton_executor preflight --json-file "$OUTPUT/data/zenodo_json/FGDC-1319.json" --output-dir "$OUTPUT" --grant "$OUTPUT/../evidence/FGDC-1319/create-grant.json" --duplicate-proof "$OUTPUT/../evidence/FGDC-1319/create-duplicate-proof.json"
```

A `{"binding": ..., "provider_requests": 0}` line means the whole offline
contract holds. Then, inside the same ten-minute window:

```bash
python -B -m scripts.modern_singleton_executor execute --json-file "$OUTPUT/data/zenodo_json/FGDC-1319.json" --output-dir "$OUTPUT" --grant "$OUTPUT/../evidence/FGDC-1319/create-grant.json" --duplicate-proof "$OUTPUT/../evidence/FGDC-1319/create-duplicate-proof.json"
```

It prompts for the token, then performs at most four writes (create, file
init, XML upload, commit) and five readback GETs, and prints the verified
identity. The record is a private draft; nothing is published. The journal row
in `<state root>/uploads_registry.json.modern-v1.json` reaches phase
`verified`. A held result keeps everything spent and retained; do not rerun.

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
