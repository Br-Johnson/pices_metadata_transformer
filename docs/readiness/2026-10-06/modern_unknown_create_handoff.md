# FGDC-141 unknown-create recovery handoff — not dispatch authority

The original production `POST /api/records` returned HTTP 403 and remains an **unknown create outcome**. Preserve its submitted bytes, original journal and spent create intent. This handoff authorizes neither a request nor a retry.

> 2026-10-06 update: the runtime pinned below predates the [User-Agent change](zenodo_user_agent_handoff.md),
> which the edge firewall requires. Dispatch only from a checkout at or after its merged head; the preflight
> binding records the runtime actually used. The "no client changes" sentence under *Current external hold*
> is superseded by that handoff, and `observe` accepts `--token-keychain pices-zenodo-production` in place of
> the prompt. Everything else here, including the holds, is unchanged.

## Pins and release prerequisites

| Evidence | Pin / state |
| --- | --- |
| Recovery CLI | `scripts/modern_unknown_create.py`, SHA256 `e31ac7cb256aaaaafa68e2f8e7ae0169f7281fa00756240b839d3d157db039a1` |
| Independent contract draft | `/tmp/pices-review-b-unknown-create-contract.md`, SHA256 `3f2c47a8d647d2b28bedf7480685960b837df31edb20ec9c761595a0928bf09f` |
| AquaDocs deferral | `aquadocs_deferred_followup.json`, SHA256 `e9ec8fb7337d141a3093da2dbfcc3c08050f22f344586b91564bf0ebaafd0a37` |
| Parent recovery packet | Expected SHA256 `e52e6cb05a2ec01cc0bd4abc0e658bde8dfa61fb2a231164c0346f3c740795e2`; **bytes unavailable in this drafting lane** |
| PR44 diagnostics repair | Reported remote head `1d7e0041bc12f523df4c3b2c33abf7f06a033330`, tree `d444a51705242e4c2344caf0142d203fd2e2851f`; merged at `ff6f56a65e6adafdb5957652dae925ce7142b0a7` after 863 passing guarded tests and exact-head Codex review |
| Frozen source/test binding | `2c84405b1360fa3d0e4d1d12b1a3993afdab830a1c34fec7a735401663e20079` (184 files) |
| Runtime SHA256 | `d1055bf636fe04299be2b670af1b3aeefcae6c64149996b85cea469b672ea4f2` |
| Final branch / review / exact-head CI | `handoff/modern-unknown-create-20261006`; final PR records the reviewed commit/tree and test results. Verify all gates before dispatch. |

Do not dispatch until the final frozen PR is independently reviewed and its full current-head CI passes. First verify the actual parent packet and original documents, reviewed owner proof, network-recovery proof, final implementation/review/CI and a fresh explicit grant to the sole Mac executor. Opaque proof JSON being nonempty is not authenticity verification. No new preparation may substitute for the exact originally submitted wire. Current preflight preparation must match those historical bytes exactly.

## Exact CLI inputs and offline preflight

The approved executor uses the **original output/state root**, not a copied state tree. Bound input documents must be at most 1 MiB, with absolute regular-file paths and no symlink substitution. Populate these placeholders only from verified retained evidence. The CLI derives original journal/intent/registry paths from `--output`; there is no alternate-state override.

```bash
set -euo pipefail
set -o noclobber

recovery_repo='/absolute/path/to/final-reviewed-checkout'
recovery_output='/absolute/path/to/original-output-root'
recovery_input='/absolute/path/to/FGDC-141.json'
recovery_preparation='/absolute/path/to/original-preparation-packet.json'
recovery_wire='/absolute/path/to/exact-original-submitted-wire.json'
recovery_original_grant='/absolute/path/to/original-create-grant.json'
recovery_original_proof='/absolute/path/to/original-duplicate-proof.json'
recovery_parent_packet='/absolute/path/to/verified-parent-recovery-packet.json'
recovery_owner_proof='/absolute/path/to/reviewed-owner-proof.json'
recovery_network_proof='/absolute/path/to/reviewed-network-recovery-proof.json'
recovery_preflight='/absolute/path/to/new-FGDC-141-recovery-preflight.json'
recovery_grant='/absolute/path/to/fresh-reviewed-GET-only-grant.json'

recovery_args=(
  --output "$recovery_output"
  --json-file "$recovery_input"
  --preparation "$recovery_preparation"
  --submitted-wire "$recovery_wire"
  --original-grant "$recovery_original_grant"
  --original-proof "$recovery_original_proof"
  --parent-packet "$recovery_parent_packet"
  --owner-proof "$recovery_owner_proof"
  --network-recovery-proof "$recovery_network_proof"
)

cd "$recovery_repo"
python3 -m scripts.modern_unknown_create preflight \
  "${recovery_args[@]}" > "$recovery_preflight"
```

`preflight` requires no `--grant`, makes zero provider requests and emits `binding`, `binding_sha256`, `limits`, `approved:false`, `replay_authorized:false` and `modern_create_outcome:"unresolved"`. A successful preflight is evidence for review, not a grant. Independently confirm the actual parent-packet hash, owner, attempt chronology and canonical state root. Review every input hash in `binding.files`, including the whole original failed journal and permanent create intent.

Required original state is the single uncertain 403 create: phase `started`, no verified or untrusted candidate identity, exactly one request and counts `get:0/create:1/init:0/content:0/commit:0`. Incompatible or missing evidence holds. The expired original grant is checked at the historical attempt time; it grants no fresh GET authority.

## Fresh reviewed grant schema

The grant accepts **exactly** these keys. Replace `binding` with the complete preflight `binding` object, not its digest. The approving parent supplies real UTC timestamps and review identity after verifying the packet, owner and network evidence; do not manufacture any field or approval. The existing executor ID is shown below and must still equal the final reviewed runtime constant.

```json
{
  "schema_version": 1,
  "kind": "modern-unknown-create-read-grant-v1",
  "approved": true,
  "executor": "01a0f3ae-ee1c-7046-9b04-36d35803903c",
  "origin": "https://zenodo.org",
  "binding": "REPLACE_WITH_COMPLETE_VERIFIED_PREFLIGHT_BINDING_OBJECT",
  "limits": {"get": 240, "pages": 200},
  "started_at": "REPLACE_WITH_APPROVED_UTC_START",
  "expires_at": "REPLACE_WITH_APPROVED_UTC_EXPIRY",
  "reviewed_by": "REPLACE_WITH_ACTUAL_APPROVING_REVIEWER",
  "clock_skew_seconds": 0,
  "candidate_scope": "all_returned_owned_ids_including_protected_read_only",
  "read_only": true,
  "no_create_replay": true,
  "token_scope": "deposit:write"
}
```

This displayed placeholder is intentionally invalid until completed and approved. Grant duration must be positive and at most 600 seconds, start no earlier than the original attempt, and current time must be inside the interval. Clock skew must be an explicitly reviewed integer from 0 through 60 seconds. Do not add a recovery-ID field or broaden the candidate scope. Token scope does not grant mutations: this operation is GET-only.

## Observe once, after all prerequisites pass

Run from a real terminal on the authorized Mac (`Darwin`). The command prompts securely for the production token; do not put it in arguments, a file, shell history or captured output.

```bash
python3 -m scripts.modern_unknown_create observe \
  "${recovery_args[@]}" --grant "$recovery_grant"
```

Only these routes are permitted, on `https://zenodo.org` with verified TLS:

- `GET /api/deposit/depositions?page=N&size=100&sort=mostrecent&all_versions=true`
- `GET /api/records/ID/draft` for each returned owned positive decimal item ID, including protected IDs for observation only.

Maximum **240 total GET attempts**, **200 sequential listing pages including the empty terminal page**, and **600 seconds elapsed**, also bounded by grant expiry. Reserve one GET for the final page-1 repeat. Each request timeout is at most 20 seconds or remaining grant/global time, whichever is smaller. Ceilings are maxima, not a requirement to use the budget. No redirects, response-provided URLs, authentication probes, HEAD, search fallback, file downloads, POST, PUT, PATCH or DELETE.

Every request count and uncertain receipt is durably recorded before dispatch. List through an explicit empty page, even after a short nonempty page. Observe every returned owned ID within budget: absent files, old dates or unlike titles do not remove candidates. Validate the final page-1 body hash against the initial page. Overflow, changed pages, malformed identity/owner, interruption, failed persistence, status/MIME failures or unreadable evidence hold. A modern draft 404 remains an unresolved observation; a 403 supplies no permission diagnosis or retry authority.

## Immutable state and evidence limits

Original preparation, submitted wire, grant, proof, source, failed 403 journal, create intent, legacy registry/mutations and supplied proof packets remain byte-for-byte unchanged, rechecked before each GET and at completion. Preserve the original missing-response-body fact; do not reconstruct it from a later response.

New evidence uses the canonical original state root:

- `FGDC-141.modern-unknown-create-v1.intent.json` — exclusive durable recovery barrier.
- `FGDC-141.modern-unknown-create-v1.json` — separate bounded recovery journal.
- Grant/request-index-specific diagnostic and successful raw-response sidecars.

A new grant, deleted/lost journal, renamed file or new recovery ID cannot reset this barrier. Interruption leaves all attempts spent. **No continuation or automatic rerun is implemented**; a future continuation requires its own reviewed contract with cumulative accounting. Do not remove either original or recovery intent.

Keep the journal within 1 MiB and response bodies within the reviewed 1 MiB per-response transport bound. Diagnostic previews are bounded at 64 KiB and cannot replace complete comparison bytes. Safe successful response bodies are retained in exclusive durable mode-0600 raw sidecars with exact hashes; known credential encodings are screened before retention. Suppression, truncation or failed persistence makes the observation incomplete. Aggregate **received body bytes** are capped at `240 × 1 MiB`; base64 sidecars require up to 4/3 of those bytes plus bounded JSON/diagnostic overhead. Do not describe that as a 240 MiB on-disk cap. Never persist the token or exception text.

## Read the result without adopting an identity

Retain counts, raw evidence references, exact-body candidates, unobserved/unresolved IDs, multiple-match status and final repeat checks. Exit status 2 means held: stop and preserve evidence, never rerun automatically. Even phase `captured`, one exact-body candidate, or zero observed matches leaves `modern_create_outcome:"unresolved"`.

The legacy owner listing is not proof of modern draft coverage or absence. The October 4 legacy inventory predates the failed create; listing file omissions are not proof of empty records. Matching a later body to the original submitted wire supports an observed candidate only, not causality or ownership adoption. Preserve `original_create_spent:true`, `replay_authorized:false`, `identity_adoption_authorized:false`, `modern_inventory_coverage_proven:false` and `provider_mutation_authorized:false`. Do not adopt an ID, initialize files, upload, publish, delete or repeat create. Return the bounded evidence to the parent for a separate decision.

## AquaDocs and unchanged publication gates

The user explicitly deferred AquaDocs comparison and related-identifier integration **until after initial production publication**. Its state is **not completed, not passed, and nonblocking for that initial publication**. No AquaDocs links or exclusions were added. Do not relabel the incomplete cache/comparison as a successful deduplication check or launch another transfer/request from this handoff.

Preserve internal and production identity deduplication, source QA, the unknown-create hold and spent intent, accepted PICES membership and remote readback, sole-executor/fresh-grant controls, and the separate publication release gate. AquaDocs deferral relaxes none of those requirements.

## Current external hold

At 13:18:42 UTC on October 6, the parent reports that the approved Mac route
returned HTTP 403 with explicit unusual-network-traffic HTML for a credential-free
GET. DNS resolution was separately restored. Assessment SHA256:
`3a51888432ea533025a384cfd04cd093ceceb46687f3a46e139872548ae3328c`.
Those response bytes are not in this code lane. This establishes the current
route restriction, not the cause of the original create failure. Parent handles
support and network recovery; no further polling, client changes or workaround
is part of this handoff. The actual failed-create packet is still required.

## Offline validation

The initial frozen runtime passed all 56 guarded affected tests (35 recovery plus
21 upload compatibility), with unchanged per-run source bindings and zero
unexpected I/O. Review requested two additional historical-evidence contracts:
a fully consistent synthetic PR42 403 and a fully rehashed nonruntime mismatch.
They preserve the old minimal receipt shape and distinguish test-fixture
generation from prohibited production-state rewriting. Their final guarded
result and the full exact-head CI are recorded in the PR before merge. No provider
requests or real credential access occurred in these tests.
