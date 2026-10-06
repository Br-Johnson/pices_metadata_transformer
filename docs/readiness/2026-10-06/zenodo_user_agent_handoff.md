# Identify the production client to Zenodo's edge firewall — 2026-10-06

The two production 403s of 2026-10-06 have one mechanical cause. `zenodo.org`
answers any request that carries no `User-Agent` header with an HTML 403
("Access to this resource has been restricted due to unusual traffic from your
network") at its edge, before the request reaches the InvenioRDM application.
The shared Mac transport in `scripts/modern_singleton_executor.py` sent no
`User-Agent`, because Python's `http.client` adds none on its own. The sandbox
does not enforce the rule, which is why every sandbox canary passed.

## Evidence

[zenodo_edge_user_agent_evidence.json](zenodo_edge_user_agent_evidence.json)
retains three credential-free `GET /api/communities/pices` probes sent from the
Mac on 2026-10-06 between 21:11:11 and 21:12:09 UTC, with response hashes:

| Probe | Client | Result |
|---|---|---|
| A | curl, default User-Agent | 200, `application/json`, `x-ratelimit-limit: 133` |
| B | Python http.client, the transport's exact headers, no User-Agent | 403, `text/html`, firewall reference `22f2b043f258bebc32d54ae692b6a2ac` |
| C | Probe B plus `User-Agent: pices-metadata-transformer/1.0` | 200, `application/vnd.inveniordm.v1+json` |

Probes A and C bracket probe B by three seconds, so the Mac's IP was not
blocked; the rejection is per request. The same symptom and fix are recorded in
[jspsych/datapipe#271](https://github.com/jspsych/datapipe/pull/271)
(2026-09-21), and Zenodo's 2026-09-15 performance post asks clients to send a
clear, identifiable User-Agent of the form `AppName/1.0 (+url; contact)`.

The 12:05 UTC FGDC-141 `POST /api/records` was the first request of its run and
used this transport, so it almost certainly received the same edge page and
created nothing. That remains unproven because the PR42 runtime discarded the
body. The [recovery handoff](modern_unknown_create_handoff.md) route is still the
way to close it; nothing here adopts an identity or authorizes a create replay.
Zenodo support ticket 3327790 was filed as an IP block and should be corrected
by the parent; no unblocking is needed.

## Change

`Transport.request` now sends
`User-Agent: pices-metadata-transformer/1.0 (+https://github.com/Br-Johnson/pices_metadata_transformer)`
alongside the unchanged `Authorization`, `Accept`, `Accept-Encoding: identity`
and `Connection: close` headers. `modern_publication.py` and
`modern_unknown_create.py` reuse this transport, so capture, publication,
readback and the FGDC-141 observation all identify themselves. The pinned header
expectation in `tests/test_modern_singleton_executor.py` carries the new header.
A contact address may be appended to the string later; the token is never part
of it.

The sandbox canary transport in `scripts/mac_sandbox_canary.py` is unchanged:
sandbox.zenodo.org does not apply the rule and its receipts are pinned.

Runtime SHA256 after the change, on the branch merged with main at
`14c4109` (reviewed citations31):
`9aa2667e8fc29a2159bf2781034fe7fe7cfbac3c928b77c5d8967f19fed32d08`.
Source/test binding (189 files):
`74938028f7e6d5df7072b9a119e61fdb5b556f2aa4208c91b57f0c7101853280`.
Historical preparation packets keep their recorded runtime hashes. The bridge
and recovery compatibility constants PR34 to PR44 are untouched, and the live
runtime is always accepted, so the FGDC-141 original packet (PR42 runtime) still
passes the recovery preflight's runtime check. All 4,206 original XML files are
untouched.

## Validation

The guarded harness `ci/run_offline_tests.py` resolves descriptors through
`/proc/self/fd` and is Linux-only; the exact-head run happens in GitHub CI on the
PR. On the Mac, the transport-related and mapping modules below were run with
plain `unittest` on a symlink-free temporary directory under Python 3.12.12
with the pinned requirements, after merging main:

| Module | Tests | Result |
|---|---|---|
| tests.test_modern_singleton_executor | 31 | pass |
| tests.test_modern_transport_diagnostics | 9 | pass |
| tests.test_modern_unknown_create | 35 | pass |
| tests.test_modern_response_evidence | 33 | pass |
| tests.test_modern_publication | 56 | pass |
| tests.test_modern_unknown_create_history | 2 | pass |
| tests.test_modern_singleton | 7 | pass |

`ruff check --isolated --select E4,E7,E9,F,I,B` passes on both changed files.
No provider mutation, token read or production-state write occurred in this
lane; the three probes above were unauthenticated reads.

## Operator consequences

- Dispatch provider actions only from a checkout at or after the merged head of
  this change; the pre-change runtime cannot reach the API from any network.
- The evidence file above can serve as the reviewed
  `--network-recovery-proof` input of the FGDC-141 observation once the parent
  has verified it; the observation route and its packet requirements are
  unchanged.
- The first new production record should follow the
  [community-first handoff](modern_pices_community_handoff.md) sequence
  unchanged: create, capture, prepare-qa, record and program review, release,
  preflight, publish, readback. A PICES-authored singleton from
  [modern_pices_singletons26.json](modern_pices_singletons26.json) is the
  natural first target for the PICES community.
- Expect ordinary rate-limit headers on every response. The published limits are
  100 requests per minute and 5,000 per hour for authenticated clients, with
  429 and `Retry-After` beyond them.
