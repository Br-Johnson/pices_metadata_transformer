# Mac-only full-metadata/XML/readback/retry continuation

This handoff prepares a new bounded continuation of the **existing Sandbox draft
612988**, using the original code02 fictional fixture. It authorizes no request by
itself. Parent dispatch assigns the Mac executor
`01a0f3ae-ee1c-7046-9b04-36d35803903c` after the transfer below is verified. This is
a new scoped assignment; the old cloud executor's grants do not transfer.
The cloud integration owner performs no provider calls.

Brett selected the Mac as the sole execution route for the next canary and eventual
production uploads. Keep cloud failures as historical evidence and stop cloud
transport diagnosis. The Mac marker's success does not isolate the cloud failure's
cause, and such diagnosis is no longer a prerequisite.

## Reconciled checkpoint and evidence limits

Parent reports the corrected Mac run at **2026-10-05 02:47:55 UTC** performed exactly
GET → one PUT → GET, all HTTP200. Draft612988 started at revision10 with empty
metadata, used bare `If-Match: 10` and the same319-byte marker payload, and ended at
revision11 with title and publisher persisted, unpublished and with empty file
inventories. The preceding cloud marker changed revision9→10 while retaining empty
metadata; do not interpret either observation as a proven transport root cause.

| Existing artifact | SHA256 |
| --- | --- |
| Mac `mac_sandbox_corrected_result.json` | `f3c68007ac6a84007c1938235f7e7c78bc0741292f11c8ddb74e4d8c55161d39` |
| Mac `mac_sandbox_receipt_2026-10-05.zip` | `f2141c916b38a53168edca63f0af79b47df3e9913653f3538aba040ca9a20f7c` |
| Corrected319-byte marker payload | `7eeb89d71da59de6953b0a27675e666962ea22c98d3c843a9aee257613d51a93` |
| Full517-byte metadata PUT body | `71830ca80356953b8654dd0e589eeff15b1b46c08c313b98372936c85c09da7a` |
| Original439-byte fictional XML | `7cf966d4c1396a3dc54cfad0b049394f70da59a8e02e9ec294dab00c3a8d4c1b` |

The first two files are on the Mac under
`/Users/brettjohnson/Documents/Codex/2026-09-30/task-4/`.
The cloud integrator has parent-provided hashes, **not those file bytes**. The ZIP
contains the successful receipts, guards, payload, scripts, tests and runtime
manifest. Parent reports Python3.14.7, Requests2.34.2, urllib3 2.8.0 and Darwinarm64;
network settings were captured afterward, with no wire trace. None of this proves
the new runner's live behavior.

The runner is a separately reviewed standard-library HTTPS client, with default
certificate/hostname verification and no token, proxy, netrc or credential
file lookup. Default TLS trust can honor OpenSSL certificate configuration; the
runner does not inspect or change those settings. It does not claim to reuse the marker's Requests implementation.
The first *counted* canonical GET verifies this client's route/authentication and
exact transferred identity before the sole metadata PUT. If that GET fails, stop;
there is no connectivity probe or alternate transport fallback.

## Exact scope and completion criteria

The [action manifest](mac_canary_action_manifest.json) lists every allowed call:
**ten GETs, one metadata PUT, one file initialization POST, one content PUT and one
file commit POST**; at most14 calls and four mutations. No create, DOI reservation,
publish, delete, community action, reset, redirect or automatic transport retry.
The same immutable grant covers both phases for at most600 seconds. Every request
has a POSIX wall-time alarm of at most20 seconds, clipped to the remaining window,
and at most65536 response bytes.

1. GET the canonical draft and verify revision11, exact sealed owner/parent/created,
   first unpublished draft, no PID, exact transferred metadata/access, enabled
   empty file inventory and canonical links.
2. PUT the exact517-byte reviewed full metadata with bare `If-Match: 11`. Require
   revision12 and all seven metadata fields, public record/restricted files and
   empty enabled inventory. Only the already reviewed exact missing-files warning
   is permitted before upload. GET and verify persistence before file initiation.
3. Initialize exactly the existing code02 filename, upload exactly the439-byte
   original fictional XML and commit it once. Verify the canonical file links,
   local transfer, completed status, size and MD5.
4. Read the draft, file list, file detail and actual file bytes. Require one file,
   all intended metadata, unchanged identity and no PID/publication.
5. Reconstruct the runner from the durable successful receipts and repeat those
   four GETs with **zero writes**. Require the same completed draft revision and
   byte-identical XML. This is the unchanged retry, not a repeated write.

The XML key is `pices-modern-synthetic-20261003-code-02.xml`; its MD5 is
`a34b1bdba8624abcb496bfc91fd98f8d`. The original packet, fixture namespace and source
hashes are unchanged. The seven intended fields are resource type, creator,
title, publication date, publisher, description and subject. Known harmless empty
serializer defaults are accepted; additional user content or missing values hold.

Completion proves this narrow synthetic metadata/XML/readback/retry contract only.
The original **nonempty managed DOI criterion remains HELD and unrehearsed**.
Neither full original canary completion nor production readiness is claimed.
If the transferred or live baseline has a PID or differs from the sealed revision11
empty-file state, stop for a revised reviewed contract; do not strip/adopt/reset it.

## Mac offline transfer and staging, before token entry

Use the frozen reviewed source and source-manifest hashes, not a moving branch.
The standalone runner needs Python3.10+ and no new third-party dependencies.
Keep all existing Mac files, cloud stages, failed receipts, grants and cumulative
counters intact. No old stage is rewritten or re-baselined by this runner.

1. Locally hash the two existing Mac artifacts against the values above. Inspect
   the ZIP's sanitized evidence without running any provider command. Verify the
   exact successful script/result/baseline and absence of later provider actions.
   Do not substitute a newly collected snapshot for the historical receipt.
2. Fill a separate0600 copy of
   [the checkpoint example](../../../contracts/examples/mac_canary_checkpoint.json)
   using those retained receipts. `baseline` must contain the exact string
   owner/parent/id/created values, integer revision11, complete canonical metadata
   and the record/files access values. Never guess missing values. Parent and Mac
   executor verify the projection against the preserved evidence before dispatch.
3. `history_manifest_sha256` binds the existing sealed historical checkpoint or
   transfer manifest. `prior_intents` carries its cumulative counters unchanged,
   including the corrected Mac twoGET/onePUT increment. Do not reconstruct totals
   from old GET197 or present the new allowance as a counter reset. Remote cloud
   evidence can remain preserved in its original location; this is a hash-bound
   checkpoint reference, not a claim the Mac independently rehashed every remote
   private file. Record that attribution in the retained transfer evidence.
4. Use a fresh canonical absolute stage path under the Mac task directory.
   Inputs and stage leaves must be current-user-owned0600 regular single-link
   files, stage0700, with no symlink components. Keep the grant outside the stage.
   A copy of the existing ZIP may be made0600 for staging; do not overwrite the
   original receipt. `prepare` copies the hash-bound files and exercises durable
   exclusive file creation and file/directory fsync before any provider intent.
5. Run these commands with the actual locally verified absolute paths:

```sh
python3 -B scripts/mac_sandbox_canary.py prepare \
  --stage /absolute/mac-task/mac-full-canary-20261005 \
  --checkpoint /absolute/mac-task/mac-checkpoint-transfer.json \
  --mac-result /absolute/mac-task/mac_sandbox_corrected_result.json \
  --receipt-bundle /absolute/mac-task/mac_sandbox_receipt_2026-10-05.zip

python3 -B scripts/mac_sandbox_canary.py preflight \
  --stage /absolute/mac-task/mac-full-canary-20261005
```

These commands do not inspect credentials, instantiate transport, read an approval
or make requests. Return their exact binding plus the verified transfer, source
hash and local runtime/private-file/fsync results to parent. If the retained
receipt does not contain a required baseline field, return that precise gap; do
not invent it or make an extra GET to manufacture an authoritative checkpoint.

## Parent dispatch and one-time token entry

After independent code review/tests and actual Mac transfer/preflight succeed,
parent binds a fresh0600 grant from
[the nonapproved example](../../../contracts/examples/mac_canary_grant.json): exact
preflight binding, fixed limits, explicit Mac executor assignment, verified
checkpoint/runtime flags and UTC start/expiry no more than600 seconds apart.
The example is deliberately invalid for execution. Repository merge authority
and code preparation do not mint this provider-action grant.

The earlier one-time token was not saved. Brett must enter a Sandbox credential
with `deposit:write` through the runner's hidden terminal prompt. Do not put it in
chat, arguments, environment files, a shell command, a receipt or the grant. No
production token or publish scope is needed. Prior success does not verify the
newly entered credential; the counted baseline GET checks access to the sealed
owner's draft and a denied write stops without any automatic retry.

```sh
python3 -B scripts/mac_sandbox_canary.py execute \
  --stage /absolute/mac-task/mac-full-canary-20261005 \
  --grant /absolute/mac-task/mac-full-canary-grant.json
```

`execute` prompts once, retains the token only in process memory, completes the
write/readback phase, reconstructs from successful durable evidence and runs the
unchanged read-only retry. It emits closed count/hash results only. Mac Darwin
and a TTY are required; an insecure getpass fallback is rejected.

A permanent exclusive phase intent is created before any request. Every action
gets another fsynced intent before transport, and each response records only
status/size/hash and credential-suppression flags. Raw provider content, headers,
messages, URLs or tokens are never persisted. Unknown HTTP outcomes, invalid
responses, validation failures, disk failures and interruptions remain spent.
**Do not remove an intent, reset a ledger, start a substitute stage/grant, rerun a
write or follow a redirect.** Return the existing closed evidence to parent.

Only if the execute phase has a complete durable success result and interruption
occurred *before* any retry intent exists may the same still-valid grant run the
explicit `retry` command, with another hidden token entry. This permits only the
four reserved GETs; it cannot resume an incomplete write phase. A spent retry
cannot reenter. Grant changes/withdrawal and expiry are rechecked before every
intent and again immediately before transport.

## Preserved source and production gates

All4206 original XML files, raw metadata/source hashes, source decisions and
protected record IDs/DOIs remain unchanged. The frozen publication plan still has
3933 supported targets,39 held and six malformed; its394 prospective batches are
nonexecutable. Original Sandbox failed receipts and spent create/write/read
budgets are preserved, not reset or reinterpreted by the new incremental counters.
Existing production associations remain protected and unrelated poster10042430
and programme15046283 remain excluded. Production identity adoption, real artifact
validation, managed DOI, durable recovery, QA, release and action-grant gates
remain separate. No production mutation is authorized by this handoff.
