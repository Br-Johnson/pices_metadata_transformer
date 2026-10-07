# Batched modern publication to the PICES community

Date: 2026-10-06. Status: proposed; nothing here grants a provider action.
Scope: moving the 3,636 wire-prepared singletons (and later the 203 pairs)
from prepared inputs to accepted PICES membership with the same evidence
guarantees the single-record chain gives today. Supersedes nothing yet; the
single-record chain in [ADR 0009](0009-community-first-modern-publication.md)
stays the reference semantics and the first 26 PICES-authored records run
through it unchanged, as drafts, before any batch mode is enabled.

## Why the single-record chain cannot simply be looped

| Constraint today | Where | Effect at 3,636 records |
|---|---|---|
| One grant per record per stage, window at most 600 s | `modern_singleton_executor.authorize`, `modern_publication.authorize` | 3 grants per record, 10,908 minted documents and 10,908 ten-minute windows |
| Duplicate proof and production projection expire 1 h after capture; community projection 1 h after capture | `modern_publication_qa.validate_production`, `validate_community` | Inventory and community captures repeated at least hourly |
| One record per modern QA manifest | `modern_publication_qa.validate` | 3,636 manifests, each with its own program review |
| Up to 14 + 5 + 24 provider requests per record, no retries, no pacing | executor, capture, publish runners | About 150,000 requests; at 60 per minute that is 42 hours of API time |
| Release manifest already selects many approved IDs | `release_manifest.prepare_release` | Usable per batch as is |

## Decision

Introduce a batch layer on top of the existing per-record journals, intents
and validators, rather than a second pipeline. Per-record truth stays exactly
where it is; the batch adds a manifest, a grant shape, pacing, resumption and
batch-level review.

1. **Batch manifest** (`modern-batch-v1`): an ordered list of source IDs from
   the finite policy lists, with the policy, the prepared-input hash and the
   preparation binding of each member, and a membership SHA256. Produced
   offline; a changed member invalidates the manifest. Batches are sized so
   one stage fits one working session: 250 records for drafts, 500 for
   capture, 150 for publication.
2. **Batch grants** (`modern-batch-grant-v1`, one per batch and stage): bind
   the manifest hash, state root, owner, runtime, stage limits per record
   (unchanged: 14, 5, 24) and a batch window of at most 8 hours. The executors
   accept either the current per-record grant or a batch grant whose manifest
   contains the record; everything else in `authorize` stays. Per-record
   intents and journal rows remain the durable barrier before every request.
3. **Rolling evidence**: the batch runner refreshes the owner inventory every
   45 minutes or every 100 records, whichever is first, and the community and
   permissions captures every 45 minutes during publication. Proofs and
   projections keep their one-hour lifetimes; the runner mints them from the
   latest capture for each record, signed by the reviewer agent that checked
   that capture. The matcher stays per source (title, file name, source-id
   mention, and the file MD5 the legacy listing exposes).
4. **Pacing and stops**: a token bucket of 60 requests per minute and 4,500
   per hour across all stages; `X-RateLimit-Remaining` below 10 pauses the
   batch until the reset time; any 429, 5xx, HTML body or edge 403 stops the
   batch after the current record's durable receipt, with no write retried.
   Reads may resume after `Retry-After`; writes resume only by a new batch run
   that skips records whose journal rows are already past that stage.
5. **QA at scale**: a multi-record modern QA manifest (schema 3) carries one
   `assess()` evidence block per record, produced by a QA agent from the saved
   capture snapshot and duplicate evidence; an independent assessor agent
   performs the program review and a risk-stratified spot check of at least 5
   percent per stratum (date semantics, creator type, rights, file identity,
   alias and version candidates); the existing `validate_program_review`
   rules apply unchanged. Brett releases per batch with one release manifest.
6. **Publication**: the v2 sequence per record (review PUT, submit POST with
   `require_review: false`, request GET, published readback) under the batch
   grant; `release_complete` is per record; a pending or held record is
   reported and left for the single-record route.
7. **Batch ledger** (`batches/<batch-id>.json` in the state root): progress,
   counts, holds and the receipts of each stage; resume reads the ledger and
   the per-record journals and never repeats a spent write.
8. **Pairs** stay excluded until a two-file executor exists; that is a
   separate decision.
9. **Inventory shape at scale**: the owner inventory summary must stay under
   the 1 MiB document bound (about 250 bytes per record, so roughly 4,000
   records); beyond that the summary becomes a manifest over per-page files.
   The legacy listing's coverage of RDM drafts is unproven; the journal is the
   authoritative barrier for drafts this chain creates.

## Consequences

- Draft creation for 3,636 singletons costs about 33,000 requests, roughly
  nine hours of API time at 60 per minute, spread over sessions; capture adds
  three hours and publication about twenty-four. Zenodo's published limits
  are never approached.
- Drafts first, then QA, then release and publication, batch by batch, so a
  problem in rendering or metadata is found on drafts, not DOIs.
- Grants per stage drop from 10,908 to about 50; evidence captures drop to
  about one per 45 minutes of running.
- The executors gain a second accepted grant shape and the QA validator a
  multi-record schema; both are additive and keep the current contracts valid.

## Implementation order

1. Run the 26 PICES-authored drafts through the single-record chain with the
   operator toolkit; fix whatever that exposes.
2. Batch manifest and batch grant shape in the draft executor, with tests, and
   a batch runner that paces, refreshes the inventory, writes the ledger and
   resumes; prove it idempotently on the same 26 (zero new writes) and then
   on the next 100.
3. Capture under batch grants.
4. Multi-record QA manifest, QA agent runner and the independent assessor.
5. Publication under batch grants with rolling community captures; first real
   publications are the reviewed 26.
6. Scale in batches; report per batch.

Each step is one reviewed change on `main` with the full guarded CI, and each
is exercised on production drafts before the next starts.
