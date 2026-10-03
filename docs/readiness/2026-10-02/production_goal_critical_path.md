# PICES production goal: critical path and access handoff

## Authority and frozen code

Brett's parent-transmitted live voice instruction of 2026-10-02 21:09 UTC
authorizes publication of every defensible PICES metadata record. This is
release authority at goal scope, not evidence that every preparation is ready.
Do not ask again for already authorized publication; bind that authority to
exact QA-approved selections after real record identities/evidence exist.
Credential or access grants still require action-time approval. No deletion,
billing change, unrelated-record modification or arbitrary merge is authorized.

PR8 remains ready and frozen at commit
`d39cc2158a84d830ac0055f796bf3dd9d612cac4`, tree
`7f6db4b6ad24c078eb217490ac10373ab0d3e333`. Its 183 offline tests, original
source preservation, 821-member citation evidence and bounded independent
findings/compiler/source/profile/integration reviews are complete. The ready
event reached Codex but hit usage limits; no substantive final-head GitHub
review ran. The old substantive GitHub review covered `6f792df`, not this head.
No reroll, explicit duplicate request, billing change or new PR push is planned.

## Immediate blocker and smallest user-only access step

The current runtime has no Zenodo connector, relevant environment tokens,
`.env`, `secrets.txt`, or `.env.local`. Only presence was inspected; no credential
value was read. Five unauthenticated public-record probes and one approved
retry failed with ProxyError before receiving any HTTP response. This is a
runtime connectivity failure, not proof that the records are unavailable.

The next user-only step is approval and secure provisioning of sandbox and
production Zenodo API access into a runtime that can reach the two API hosts.
The parent must establish a supported secret delivery route and working
outbound connectivity; do not paste token values into chat or store them in
source/Library artifacts. The current client reads only the appropriate
ZENODO_SANDBOX_TOKEN / ZENODO_PRODUCTION_TOKEN from cwd .env, not environment
variables, so merely adding an environment variable will not enable it. A
reviewed loader adaptation may be preferable once the supported secret route
is known. No account/token/permission creation is attempted here.

Official API reference: https://developers.zenodo.org/

## Bounded technical sequence

1. Restore runtime connectivity and approved credential access. Begin with
   harmless authenticated reads in sandbox and production; confirm account,
   ownership and actual API response compatibility. Never invoke generic
   helpers that create test records as an authentication probe.
2. Capture complete fresh production community + owned-deposition inventories
   with sanitized endpoints/query/pagination, timestamps and response hashes.
   Reconcile all source IDs/hashes and persistent identifiers. Quarantine five
   historical source associations before any new create, preserve their exact
   IDs/DOIs, and exclude unrelated poster 10042430 from every write selection.
   Community membership alone is not proof of ownership.
3. Run one uniquely labeled synthetic sandbox transport draft with exact file
   checksums, readback and unchanged retry. Then run at most three supported
   actual-source sandbox drafts if fresh inventory permits, again proving
   exact content and zero duplicate creates on retry. Do not substitute a
   production write for a blocked sandbox canary. Historical sandbox
   duplicates are authorized, but the current runtime has no explicit
   scoped exception; implement/test that mechanism if needed, never edit
   allowlists or erase state to manufacture eligibility.
4. Before production creation, enforce protected source-to-existing-record
   bindings and explicit expected DOI identity checks. Current title/DOI
   duplicate matching and planning sidecars alone do not enforce a
   source-hash index. Keep five existing published records in a preserve/
   reconcile lane; published editing is not implemented by draft recovery.
5. Select exact defensible IDs/hashes into isolated production outputs.
   Require fresh complete environment-scoped inventory and durable create
   intent. Create at most three production drafts, read back exact source,
   metadata, XML checksum/size and draft identity; unchanged reruns must reuse
   IDs. Ambiguous creates/publications stop for GET reconciliation.
6. Gather real fresh external duplicate evidence, with truthful candidates,
   unavailable-service states and exact source/payload bindings. The current
   automatic no-match QA path does not accept the Zenodo inventory alone.
   Implement/test richer adjudication where defensible cases require it; do
   not relabel unavailable evidence or candidates as no-match.
7. Complete record QA, independent program review and risk-stratified source
   checks against the exact population digest. Materialize an exact release
   manifest using Brett's existing authority, with genuine draft/QA hashes.
8. Publish only the released bounded selection; verify final state, metadata,
   files, record ID, reserved/final DOI and concept DOI against expected
   immutable identity. Record actual community state. Expand in bounded
   batches only after canary/retry success and fresh evidence.

## Deliverables already prepared

The complete `source-record-doi-planning-manifest.json` covers all 4,206 source
IDs/raw hashes/bytes and remaining holds. Its five historical identity fields
are explicitly unverified; every current remote binding remains null.
The frozen source-only baseline is 1,328 supported / 2,872 held / six malformed:
1,325 are nonhistorical supported preparations awaiting remote QA; five
historical identities (including two source-held cases) require reconciliation.
No record is claimed publish-ready. This manifest is not executable upload
state or a substitute for runtime protections.

Source QA continues on unpushed branch `cloud/registration-access-batch`: 122
exact source-backed database-registration records, 78 verified access-only
promotions; 23 ambiguous and 21 empty creators remain held. Larger vague access
cohorts and unknown rights remain separate consequential questions. Next
independently source-supported literal organization groups total 45 members
(PICES 26 and NCDC hierarchy 19), with 36 potential promotions and 9 retained
holds; they are not implemented in this branch.

Only real remote responses can populate final source→record/DOI bindings.
Final delivery must reconcile all 4,206 dispositions, preserve aliases and
malformed sources, list every remaining hold, and distinguish publication
from verified community placement. The parent owns durable continuation;
no invented goal-mode feature or duplicate automation is created here.
