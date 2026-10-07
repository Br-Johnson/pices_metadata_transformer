# Batch runner contracts for modern drafts

Date: 2026-10-07. Status: accepted for implementation in reviewed increments;
nothing here grants a provider action. Refines [ADR 0011](0011-batched-modern-publication.md)
with what the first 26 production drafts taught and freezes the documents the
batch layer adds. The single-record chain stays the reference semantics; a
batch never weakens a per-record contract, it only lets one grant and one
reviewed inventory cover many records.

## What the 26 drafts showed

| Observation | Consequence for the batch layer |
|---|---|
| A verified draft costs about 12 s and 9 requests (create, init, content, five GETs); minting and preflight are offline | 250 records fit one 50-minute session; pacing at one request per second keeps the chain under 60 per minute without a token bucket, which stays as a guard |
| Two holds came from the provider's text sanitiser (`&quot;` decoding, half-width folding), both after a 201 | Holds are classified by journal state and the last receipt, never by message: a started row with a candidate id, an unbound identity and a single complete 201 create receipt is a *validation hold* (parked for the resume route, batch continues); a started row with a bound identity and a later failed receipt is a *recovery hold* (reported for the separately reviewed recovery route, batch stops; the readback route applies only when the upload had completed); no row, or a create receipt that is not a complete 201, is a *transport or contract hold* (batch stops) |
| The legacy listing shows no files for RDM drafts and the summary grows past 1 MiB near 2,600 records | Journal-pinned ids are skipped at capture and summarised minimally once the bound is near; the journal is the barrier for the chain's own drafts, the inventory the barrier for everything else |
| FGDC-1924 and FGDC-2708 describe one workshop from two sources; no check compared sources with each other | The manifest carries a twin check (identical source bytes hold; equal or contained core titles need a reviewed allowance), decided by Brett on 2026-10-07 for that pair. Measured over all 4,204 prepared titles, the rule flags 330 equal-title groups (477 pairs, the largest group of seven) and 134 containment pairs, so allowances are groups, recorded once in a registry under the state root and consulted by every build; each flagged group is a curation decision (distinct records, or a duplicate in the source collection to exclude) made before its batch |
| One description in the corpus (FGDC-2733) carries a character the sanitiser removes | Manifests carry explicit exclusions with reasons; an offline pre-screen names them before a create is spent |
| A `scripts/` change moves the runtime hash and strands started rows | A batch runs under one runtime; the manifest pins it, validation re-derives it, and code lands only between batches |

## Documents

All documents are canonical JSON under the state root
(`<output>/state/uploads/production`), written exclusively and never replaced,
and validated by the executors with `require`, as every other document of this
chain. Example payloads live in `contracts/examples/`.

### `modern-batch-v1` (manifest) — implemented by `scripts/modern_batch.py`

Built offline from prepared inputs. Path: `batches/<batch_id>.manifest.json`.

| Field | Meaning |
|---|---|
| `batch_id` | `[a-z0-9][a-z0-9-]{2,63}`, operator-chosen, unique under the state root |
| `stage` | `drafts` (v1); capture and publication manifests are later increments |
| `origin`, `owner`, `state_root` | as the executor grant |
| `built_at`, `built_by`, `runtime_sha256` | provenance; the runtime must equal the live one at validation |
| `members[]` | `index`, `source_id`, `policy`, `schema_version`, `source_sha256`, `wire_sha256`, `binding`, `title_key`, `journal_phase` — the binding is the live preparation binding the executor will demand; the title key is case-folded, whitespace-normalised and stripped of the constant artifact suffix |
| `member_count`, `membership_sha256` | count and SHA256 of the ordered `[source_id, binding]` pairs |
| `attempted_count`, `attempted_sha256` | the modern-journal sources outside the batch that the twin check compared against (count and SHA256 of the sorted ids); their titles and digests are read from the immutable prepared input and original XML without `prepare()`; a row without its prepared input holds. Sources known only to the legacy registries are not compared; an exact-title copy of one is still caught by the inventory matcher |
| `twins[]` | every title twin found inside the batch or against attempted sources, each covered by an allowance |
| `allowances[]` | the allowances used: `sources` (sorted group, every pair inside it allowed), `allowed_by`, `note`, `origin` (`cli` or `registry:<file>`); a command-line allowance that matches nothing holds as stale, a registry entry may name sources the batch never meets |
| `exclusions[]` | `source_id`, `reason`; a source deferred from this batch |

Rules: a twin is an identical source (hard), an equal title key, or a title
key of at least 40 characters contained in another's (soft); FGDC-2708's core
title sits inside FGDC-1924's, while series siblings that share boilerplate do
not contain one another. At most 250 members; distinct, well-formed ids; a member may already
have a journal row (the runner skips verified rows, so a rerun on the same
manifest writes nothing); byte-identical sources never share a batch or
follow an attempted twin; `validate` re-derives every member from the live
preparation and refuses any drift, reorder or runtime change; it also
re-derives the attempted set and the twins against the current journal, so a
twin attempted after the build, or an edited `twins`, `allowances` or
`exclusions` list, holds. Every `scripts/` change moves the runtime, so
manifests are rebuilt (offline, seconds) after any code change.

### `modern-twin-allowance-v1` (registry) — implemented

One reviewed decision per file under `batches/allowances/<name>.json`:
`sources` (sorted group), `allowed_by`, `note`, `decided_at`; written
exclusively, never replaced, read by every build. The first entry records
Brett's 2026-10-07 decision for FGDC-1924 and FGDC-2708.

### `modern-batch-grant-v1` — increment 2

Minted by the operator toolkit, reviewed and signed like a create grant.

| Field | Meaning |
|---|---|
| `kind`, `schema_version`, `approved`, `executor`, `origin`, `stage`, `owner`, `state_root`, `token_scope`, `draft_only`, `canary_receipt_sha256`, `reviewed_by` | as the create grant |
| `batch_id`, `manifest_sha256`, `membership_sha256` | the manifest it covers, found at `batches/<batch_id>.manifest.json` |
| `limits` | the per-record limits (unchanged: create 1, init 1, content 1, commit 1, get 10) |
| `started_at`, `expires_at` | one window of at most 8 hours |
| `evidence_policy` | `inventory_max_age_seconds` 2700, `inventory_max_records` 100, `proof_lifetime_seconds` 3600 |

The executor's `authorize` accepts either the per-record grant or a batch
grant whose manifest hash matches the file under the state root and whose
membership contains `(source_id, binding)` for the prepared record. The
per-record duplicate proof stays per record: the runner mints it from the
latest reviewed inventory with that inventory's signer as `reviewed_by`,
and the proof's binding is the record's. Under a batch grant the proof rule
changes from "the proof covers the whole grant window" (impossible for an
eight-hour window and a one-hour proof) to "`checked_at <= now <
expires_at` at every request", re-evaluated by `Runner.current()`, while
`started_at <= now < expires_at` of the grant is checked separately. Intents
and journal rows stay per record and record the batch grant's hash; the
publication bridge accepts a batch grant as the "old grant" of a row by the
same membership check. A row held under a batch grant is resumed only under
a distinct grant (today's per-record resume grant, or a later batch grant),
because `resumable()` refuses the grant that started the row.

### `modern-batch-ledger-v1` — increment 3

Path: `batches/<batch_id>.ledger.json`, written atomically between members;
the executor takes the ledger lock itself for each record, so the runner
never holds it across a record's execution.

| Field | Meaning |
|---|---|
| `batch_id`, `manifest_sha256`, `grant_sha256`, `started_at`, `updated_at`, `status` | `running`, `stopped` or `complete` |
| `inventories[]` | each reviewed inventory used: `sha256`, `captured_at`, `reviewed_by`, `records`, `members_minted` |
| `members{}` | per source: `status` (`pending`, `already-verified`, `verified`, `held-validation`, `held-recovery`, `held-transport`, `skipped`), `record_id` or `candidate_id`, `proof_sha256`, `inventory_sha256`, `attempted_at`, `requests` |
| `counts`, `requests`, `stops[]` | progress keyed by status, request totals per minute and hour, and every stop with its reason and the last durable member |

The example payloads are shown expanded for reading; the chain stores canonical
JSON, and the examples validate only against the checkout and state root they
were built from.

### Inventory at scale — increment 7

`modern-owner-inventory-v2` summarises journal-pinned records as
`{id, owner, known: true}` only, keeps full entries for unknown records, and
raises the page bound to cover 5,000 records; the matcher ignores known
entries except by id. Triggered when a v1 summary passes 768 KiB.

## The runner (increment 3)

`scripts/modern_batch.py run --manifest --grant --inventory --reviewer`:

1. Validate the manifest and the batch grant; load or create the ledger.
2. For each member in index order: skip a verified row (`already-verified`);
   leave a started row for its own route (`skipped`, reason `resumable` or
   `recoverable`), since a resume needs a grant other than the one that
   started the row; otherwise mint the duplicate proof from the inventory
   (refusing when it is older than 45 minutes or has already covered 100
   members), preflight offline, then execute through the existing `Runner`
   under the batch grant.
3. Pace: at least one second between requests, a token bucket of 60 per
   minute and 4,500 per hour, and a pause until `X-RateLimit-Reset` when
   `X-RateLimit-Remaining` drops below 10 (the transport gains header
   exposure in increment 2).
4. Classify a hold by the journal row and its last receipt: a candidate id,
   an unbound identity and a single complete 201 create receipt is
   `held-validation` and the batch continues; a bound identity with a later
   failed receipt is `held-recovery`, reported for the separately reviewed
   recovery route (readback only once the upload had completed), and the
   batch stops; no row, or a create receipt that is
   not a complete 201 (a 429, 5xx, HTML body or edge 403), is
   `held-transport` and the batch stops after the ledger write. No write is
   ever retried.
5. Stop cleanly when the inventory goes stale or the grant window ends; the
   operator captures a fresh inventory, a reviewer agent signs it, and the
   same command resumes from the ledger.

Reviewer agents sign inventories; Brett releases per batch at the
publication stage only, as today. Drafts need no human release.

## Implementation order

1. This ADR, `modern_batch.py` build, validate and allow, the twin check,
   the allowance registry and the first allowance (FGDC-1924 with
   FGDC-2708), example payloads. Done here.
2. Batch grant acceptance in `authorize` and the publication bridge; rate
   limit headers on the transport response; operator `mint-batch`.
3. The runner, the ledger and the hold classes; prove on the 26 (zero
   writes), then on the next 100 after their inputs are classified into the
   production root.
4. Capture under batch grants. 5. Multi-record QA manifest and the
   independent assessor. 6. Publication under batch grants with rolling
   community captures; the first publications are the reviewed 26.
7. Inventory v2 when the bound approaches.

Each increment is one reviewed change on `main` with the full guarded CI,
landed between batches so no started row is stranded by a runtime change.
