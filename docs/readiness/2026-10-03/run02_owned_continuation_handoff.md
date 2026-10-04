# Run02 owned empty-draft continuation

Parent's canonical GET returned200. The retained candidate ID, string owner,
unpublished first draft/version1, aware creation window, canonical Sandbox links
and enabled empty-file aggregates matched. Required metadata fields were absent;
the file access string differed from the submitted restricted policy. The GET
proved an owned empty candidate, not persisted metadata or a completed trial.

The modern service permits incomplete draft creation with201. Its source passes
parsed JSON to the create service; neither source nor the GET establishes why
this deployment returned empty metadata. Do not claim that the endpoint ignores
the request body or silently change content type. Recovery applies only to this
sealed candidate, never another create or a generic missing-metadata exception.

Parent-reported create response SHA256:
`20e8f71aad83b1f045c5657288f38896ab6a5931e4b1424e22310be25729dabf`.
Canonical beforeimage SHA256:
`316073505991baeca08490de43bc3dc5f0334917c0bcee4a60abc77e2a03f662`.
Fixed-field diagnostic SHA256:
`3ea2e9ad7da503b7ad62277258b1b0f8936f03d3712025197f68c80e672cdbf6`.
Original02 packet0f54838bf45ebecccaf575db4145c5a51cdd01507f0aaa6e9b418aadd786db13,
runtime8b96b63ca66ec4e27546ce3980abb98cb8f5f7b696eb2c7d3f590ac7a61e9b24,
error helper2f1f68bf7fee4e39099b5969e2013e1bc01f30b9edef6a2cb7f44a275fbb5bf3.
Parent reports305 prior files preserved, one original createPOST and one separate
diagnosticGET, cumulative GET196. Root/reviewers have read none of those private
files, inspected no actual credentials/environment and made no provider request.

## Separate ledger and exact parent grant

Only executor01a0fed7-bf71-7384-95fd-3434599df03f may stage/execute. The original
failed state, pending create, response and grants remain immutable. A fresh private
0700 destination must be outside the original stage and the entire parent-named
preserved private root. It has basename
`pices-modern-synthetic-20261003-code-02-owned-continuation`. Static copies and
ledger files are0600; symlinks/hardlinks/unexpected files are rejected. The code
checks original seven controlled files against the copied origin hashes before
each request, plus the pinned readback/diagnostic hashes. Parent/executor must
verify their complete305-file before/after inventory separately; the controller's
origin check is not a fresh audit of all historical private files.

Staging creates no usable approval and issues no request. The retained create
receipt must be exactly201, complete credential-free JSON with the pinned digest;
the sole create attempt must have reached identity validation with201 and the
observed approved send/adapter path. A500/uncertain/different prior create cannot
be rebound. The candidate ID must equal the original private uncertain ID.

```bash
python -m scripts.modern_owned_continuation stage \
  --stage /NEW/PRIVATE/pices-modern-synthetic-20261003-code-02-owned-continuation \
  --original-stage /OLD/PRIVATE/pices-modern-synthetic-20261003-code-02 \
  --preserved-root /OLD/PRIVATE \
  --beforeimage /OLD/PRIVATE/CANONICAL_BEFOREIMAGE.json \
  --diagnostics /OLD/PRIVATE/FIXED_FIELD_DIAGNOSTICS.json
```

Use only the already-configured private `ZENODO_SANDBOX_TOKEN` and ordinary
approved Session.request routing/CA/adapters. No credential, proxy, CA or scope
change is needed. Credential checks cover raw/decoded JSON before copying it.
All actual paths/IDs/owners/bodies stay private; the commands are placeholders.

Parent then writes approval.json using the exact keys in
[the fictional grant contract](../../../contracts/examples/run02_owned_continuation.json).
Its binding must equal this final runtime's `binding(stage)`, including every
static input hash and the original source path/hashes. Use the existing private
owner and identical original known-ID reject set. Set approved/executor/standing
approval reference, existing_candidate_only/no_create_or_reset, additional_get_limit6,
original_valid_until, and the exact305-file inventory digest. `limits` is the
original lifetime ceiling; create1/get1 are already spent in the new ledger.
The fixed controller has **no CREATE route** and no extra diagnostic GET.

For `window_mode=original_window`, valid_until is clipped to the original02 expiry
and at most30minutes after started_at. An expired original grant cannot dispatch.
If parent explicitly authorizes a separately reviewed continuation window under
the applicable standing authority, it must issue this new exact bound grant with
`window_mode=specifically_authorized_continuation_window`, fresh aware started_at
and valid_until at most30minutes later. The original expiry remains in provenance;
staging/controller code never extends it, reuses the expired grant, generates an
approval or replenishes an action. If that scope is not authorized, stop held.

## Bounded sequence and retained predicates

Constructor performs only local proof checks. It validates the sealed beforeimage
against the unchanged canonical ID/owner/parent/time/first-draft/file predicates,
requires empty/default metadata, public record access, public or restricted file
access, and absent DOI. It records no assertion that submitted metadata persisted.
The parent-issued continuation is the explicit adoption authority for this exact
owned candidate; there is no automatic adoption from a failed create.

Sequence: one metadataPUT to the exact candidate draft with the committed02
metadata-put.json and restricted file policy. Immediately require all exact
metadata/access/identity/empty-file predicates; failure permanently spends PUT
and stops before any file initialization. Only if DOI is wholly absent after PUT,
allocate it once and validate the updated record and managed Sandbox DOI again.
Then one file-initPOST, one contentPUT and one commitPOST use the existing file
key and bytes. No publish/delete/newversion or real PICES source upload exists.

Each completed readback uses three GETs: draft record, file listing, exact content
bytes. The listing must contain exactly one entry that passes the unchanged file
validator (key/status/local transfer/size/checksum and canonical self/content/commit
links). It serializes the same schema as an item read; the formerly duplicated
item GET is omitted. Missing fields stop; there is no detail-read fallback.
Only after the first pass completes may one unchanged three-GET retry run.

```bash
python -m scripts.modern_owned_continuation execute --stage /NEW/PRIVATE/pices-modern-synthetic-20261003-code-02-owned-continuation
python -m scripts.modern_owned_continuation retry --stage /NEW/PRIVATE/pices-modern-synthetic-20261003-code-02-owned-continuation
```

Lifetime accounting: prior create1+diagnosticGET1, at most3 remainingPOSTs
(DOI/init/commit), twoPUTs and six additionalGETs. GET total7of8, cumulative
historical GET202 maximum; one original read remains unused and is not exposed
by this sequence. All intents persist before transport. TLS, no redirects/retries,
20-second request/body wall deadlines clipped to the grant,64KiB response maximum,
strict token-echo checks, exact response validation and held interruption/reentry
semantics remain. An uncertain PUT or upload is never automatically replayed.

Fixed metadata/access diagnostic field names return presence/type/match labels
and booleans; no actual values, unknown response keys, credential/environment
values or exception text/repr/trace. Strict owner and full post-PUT source/payload
checks are retained. No production credentials, writes, identities or deduplication
rules change. The separately reviewed23+83 source profiles are not in this PR.

Primary-source conclusions and pinned references are preserved in
run02_owned_continuation_source_contract_independent_review.json. Concrete code,
tests and final-head handoff review must clear before parent dispatch.
