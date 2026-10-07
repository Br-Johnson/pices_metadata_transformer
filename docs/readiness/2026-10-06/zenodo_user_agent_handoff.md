# Identify the production client to Zenodo's edge firewall — 2026-10-06

The production 403 reproduced from the Mac on 2026-10-06 has one mechanical
cause, and it is the most likely explanation for both earlier production 403s.
`zenodo.org` answers a request that carries no `User-Agent` header with an HTML
403 ("Access to this resource has been restricted due to unusual traffic from
your network") at its edge, before the request reaches the InvenioRDM
application. The shared Mac transport in `scripts/modern_singleton_executor.py`
sent no `User-Agent`, because Python's `http.client` adds none on its own. The
sandbox does not enforce the rule, which is why every sandbox canary passed.

## Evidence

[zenodo_edge_user_agent_evidence.json](zenodo_edge_user_agent_evidence.json)
retains three credential-free, body-less `GET /api/communities/pices` probes
sent from the Mac on 2026-10-06 between 21:11:18 and 21:12:09 UTC, with
response hashes in the receipt. They were diagnostic reads made under Brett's
chat request of that day, outside the executor's grant system, with no token
and no mutation.

| Probe | Client | Result |
|---|---|---|
| A | curl, default User-Agent | 200, `application/json`, `x-ratelimit-limit: 133` |
| B | Python http.client, the transport's header set minus Authorization, no User-Agent | 403, `text/html`, firewall reference `22f2b043f258bebc32d54ae692b6a2ac` |
| C | Probe B plus `User-Agent: pices-metadata-transformer/1.0` | 200, `application/vnd.inveniordm.v1+json` |

Probe A returned 200 forty-eight seconds before probe B and probe C returned
200 three seconds after it, so the Mac's IP was not blocked at capture time;
the rejection is per request. The same symptom and fix are recorded in
[jspsych/datapipe#271](https://github.com/jspsych/datapipe/pull/271)
(2026-09-21), and Zenodo's
[performance update of 2026-09-15](https://blog.zenodo.org/2026/09/15/2026-09-15-stability-and-performance-updates/)
asks clients that make many requests to respect the published limits and send a
clear, identifiable User-Agent of the form `AppName/1.0 (+url; contact)`.

What the probes do not show: probe C sent the short token
`pices-metadata-transformer/1.0`, not the shipped constant with its
`(+https://…)` comment, and no probe was authenticated or carried a body. The
12:05 UTC FGDC-141 `POST /api/records` was the first request of its run and used
this transport, so it almost certainly received the same edge page and created
nothing; that remains unproven because the PR42 runtime discarded the body. The
client and headers of the 13:18:42 UTC credential-free GET were not recorded, so
it is not attributed either. The [recovery handoff](modern_unknown_create_handoff.md)
route is still the way to close FGDC-141; nothing here adopts an identity or
authorizes a create replay. The parent should update Zenodo support ticket
3327790 with this finding; no unblocking was needed at 21:12 UTC.

Before any one-shot provider action, send one credential-free GET through the
shipped header set and retain it as probe D. This lane could not send it. From
the merged checkout, with no token:

```bash
python3 -c "import http.client, ssl, sys; sys.path.insert(0, '.'); from scripts.modern_singleton_executor import USER_AGENT, MIME; c = http.client.HTTPSConnection('zenodo.org', timeout=20, context=ssl.create_default_context()); c.request('GET', '/api/communities/pices', headers={'Accept': MIME, 'Accept-Encoding': 'identity', 'Connection': 'close', 'User-Agent': USER_AGENT}); r = c.getresponse(); print(r.status, r.getheader('Content-Type'), r.getheader('X-RateLimit-Limit'), len(r.read()))"
```

A 200 with the vendor MIME type and an `X-RateLimit-Limit` value verifies the
exact shipped bytes; an HTML 403 holds everything until the value is reviewed.

Probe D was sent on 2026-10-07 at 00:45:17 UTC with the contact-bearing value and
returned 200, `application/vnd.inveniordm.v1+json`, `x-ratelimit-limit: 133`; it is
retained in the evidence receipt.

## Change

`Transport.request` now sends
`User-Agent: pices-metadata-transformer/1.0 (+https://github.com/Br-Johnson/pices_metadata_transformer; johnson@psc.org)`
alongside the unchanged `Authorization`, `Accept`, `Accept-Encoding: identity`
and `Connection: close` headers, on every request shape. `modern_publication.py`
and `modern_unknown_create.py` reuse this transport, so capture, publication,
readback and the FGDC-141 observation all identify themselves. An import-time
check rejects a non-ASCII, non-printable or whitespace-padded value, so a bad
edit fails before any attempt can be spent. The tests import the constant,
check its form, and pin the header on body-bearing POST and PUT and on
body-less GETs with both Accept values.

The contact element is Brett's address, decided on 2026-10-06 before the first
production create, so the runtime hash changes once. The token is never part of
the string. The three executors also accept `--token-keychain SERVICE`, which
reads the token from the macOS login Keychain item of that service name through
`security find-generic-password` instead of prompting; the value stays in memory
and is never logged, and a missing item or malformed value holds before any
attempt is spent. Both routes still require a Mac terminal, the service name
must start with `pices-`, and the irreversible `publish` action refuses the
Keychain route and keeps its live prompt. `scripts/modern_operator.py` adds the
bounded owner-inventory capture and the create grant and duplicate proof
minting that the runbook uses; minted documents are validated by the executor's
own `authorize` before they are reported. The matcher compares title, file name,
file MD5 against the XML, SHA256 literals, normalized source-id mentions, and
refuses any record whose files cannot be seen unless it is protected, excluded,
recorded in the modern journal or explicitly known; minting re-derives the
summary from the hashed raw receipts, so an edited summary cannot pass. Two
independent review passes were run on this change and their material findings
were resolved before it was committed.

The sandbox canary transport in `scripts/mac_sandbox_canary.py` is unchanged:
sandbox.zenodo.org does not apply the rule and its source hash is pinned. The
legacy `scripts/zenodo_api.py` client and the matching adapters still send the
python-requests default; they are outside the first-record path and are
recorded in [tech-debt](../../tech-debt.md).

Runtime SHA256 of PR #47 as merged (`f77eaa7`):
`19afd44a7dd156df8f3168c9badc96dbe4d74e4320dbffdc3f8c131e1ac13f0c`.
Runtime SHA256 after the contact address, Keychain token source and operator
toolkit were committed to main:
`e23b81aba71ac50d348f25c60d4ac4c1d60bd88e3dc89f356d5599597d3d023c`.
Source/test binding (191 files):
`63614aecbe18582e33489a27d25abeb19bc5fde399a91581da51f4f6280873cb`.
No preparation or grant was made on the merged PR #47 runtime, so no
compatibility constant is needed for it.
No pinned runtime constant changes: the fifteen historical constants (PR34 to
PR46, REVIEWED194 and PROGRAM20) are untouched and the live runtime is always
accepted, so the FGDC-141 original packet (PR42 runtime) still passes the
recovery preflight's runtime check. Main's pre-change runtime `108fe080…` is
in no constant, so nothing prepared or granted on it can bridge; no production
draft was created on it. All 4,206 original XML files are untouched.

## Validation

The guarded harness `ci/run_offline_tests.py` resolves descriptors through
`/proc/self/fd` and is Linux-only; the exact-head run happens in GitHub CI on the
PR. On the Mac, the transport-related and mapping modules below were run with
plain `unittest` on a symlink-free temporary directory under Python 3.12.12
with the pinned requirements, after merging main:

| Module | Tests | Result |
|---|---|---|
| tests.test_modern_singleton_executor | 37 | pass |
| tests.test_modern_operator | 8 | pass |
| tests.test_mac_sandbox_canary | 29 | pass |
| tests.test_production_mutations | 31 | pass |
| tests.test_modern_transport_diagnostics | 9 | pass |
| tests.test_modern_unknown_create | 35 | pass |
| tests.test_modern_response_evidence | 33 | pass |
| tests.test_modern_publication | 56 | pass |
| tests.test_modern_unknown_create_history | 2 | pass |
| tests.test_modern_singleton | 7 | pass |

`ruff check --isolated --select E4,E7,E9,F,I,B` passes on both changed files.
An independent review of the change by separate reviewer agents found no
defect in the code; its documentation findings are resolved in this version.
No provider mutation, token read or production-state write occurred in this
lane.

## Operator consequences

- Dispatch provider actions only from a checkout at or after the merged head of
  this change; a pre-change runtime cannot pass the edge from any network.
- Send and retain probe D first, as above.
- The evidence file above can serve as the reviewed
  `--network-recovery-proof` input of the FGDC-141 observation once the parent
  has verified it; the observation route, its packet requirements and its holds
  are unchanged, and the observation has not yet run.
- The first new production record follows the
  [community-first handoff](modern_pices_community_handoff.md) sequence with
  this merged runtime rather than the frozen PR40 runtime that document pins.
  A PICES-authored singleton from
  [modern_pices_singletons26.json](modern_pices_singletons26.json) is the
  natural first target for the PICES community.
- Application responses carried `x-ratelimit-limit: 133` for unauthenticated
  GETs; the edge 403 carried none. The published authenticated limits are 100
  per minute and 5,000 per hour, returned as 429 with `Retry-After` when
  exceeded. The transport never retries, so pace writes well inside them.
