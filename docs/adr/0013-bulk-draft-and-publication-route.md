# Bulk draft and publication route for reviewed records

Date: 2026-10-20. Status: accepted. Supersedes the per-record publication
sequence of [ADR 0009](0009-community-first-modern-publication.md) and the
remaining increments of [ADR 0011](0011-batched-modern-publication.md) and
[ADR 0012](0012-batch-runner-contracts.md) for the bulk of the collection. The
single-record executors, their journals and the 26 verified PICES drafts stay
as they are; this route adopts those drafts, it does not rewrite their history.

## Context

On 2026-10-20 Brett set the goal: publish every appropriate record to
production Zenodo, where *appropriate* means reviewed by an AI for accuracy and
passing validation, and noted that most records have already been reviewed.

The finite source policies are that review at source level: 3,636 singletons
sit in one of ten reviewed creator policies and pass `agent_qa.assess_source`
(the 69 remaining singletons, the 39 held, the 6 failed and the 5 protected
sources do not). The existing chain cannot carry them to publication:

| Limit | Where | Effect at 3,636 records |
|---|---|---|
| One journal document, read with a 1 MiB bound; about 6.4 KB per verified row | `modern_singleton_executor.read_document`, `uploads_registry.json.modern-v1.json` | The journal refuses to load after about 160 drafts |
| Every scripts/ change moves the runtime inside every row binding | `runtime_binding`, `RESUME_RUNTIMES`, the `PR*_RUNTIME` bridge constants | One new constant per code change between create and publish |
| Publication needs eight hand-built documents per record inside one hour: capture grant, snapshot, production projection, raw external title searches with zero hits, community projection, single-record QA manifest, release, v2 grant | `modern_publication`, `modern_publication_qa`, `release_manifest` | Thousands of hand-built documents; an external hit for a report that also exists elsewhere blocks it |
| The publish token is typed at a terminal for every record | `production_token(action='publish')` | One human token entry per record |

## Decision

Add `scripts/modern_bulk.py`, a batch route with one journal file per record,
that reuses the existing preparation, provider transport, response screening,
metadata comparison, inventory capture, duplicate matcher and batch manifest
with its twin check. Nothing in the single-record chain changes behaviour.

### Membership and review

1. **Batch manifest.** Members come from `modern_batch` manifests
   (`modern-batch-v1`, at most 250 singletons, live preparation bindings,
   identical sources held, equal or contained core titles allowed only by a
   reviewed allowance). The attempted set now also includes this route's
   journal, so twins are caught across batches.
2. **Accuracy review sheet.** `modern_bulk sheet` writes, offline, one row per
   member: the source XML's citation title, origins, publication date,
   abstract opening, keyword count and time period beside the wire's title,
   creators, publication date, description opening and subjects, plus
   automatic flags (empty or short description, date that disagrees with the
   source, creator names that look like placeholders, replacement characters
   or mojibake, very long titles, sanitiser-sensitive characters).
3. **AI review.** A reviewer agent reads every flagged row and a random sample
   of at least 10 percent of the others (never fewer than 20) against the
   original XML and writes `modern-bulk-review-v1`: the manifest SHA256, the
   sheet SHA256, the reviewer, the time, the sampled ids, and a decision for
   every member (`approved`, or `held` with a reason). The draft stage refuses
   a member the review does not approve.

### Duplicate barrier

Before any create, for every member: no record of this route, no modern-v1
row or intent (except a verified row, which is adopted), no legacy registry or
mutation entry, not protected or excluded, and no match in a fresh owner
inventory. The inventory is captured at the start of every run and again every
45 minutes; it is matched on full title, core title (artifact suffix removed),
file name, file MD5, SHA256 literal and source-id mention, and any unknown
record whose files cannot be seen holds. Records this route created are known
by its journal. External repositories (AquaDocs and others) are not consulted:
Brett deferred that linkage until after initial publication on 2026-10-06.

### Stages and requests

| Stage | Requests | Token |
|---|---|---|
| `drafts` | create POST, file-init POST, content PUT, commit POST only when the PUT did not complete the upload, then GET draft and GET file listing | Keychain or prompt |
| `publish` | once per run, GET the PICES community with the token (identity, public visibility, parent, `can_submit_record` and `can_include_directly` must hold); per record GET draft, review PUT (`community-submission` to the PICES UUID), GET draft again (the PUT has no compare-and-swap), submit-review POST with `{"require_review": false}`, then GET published record and GET file listing | Keychain item `pices-zenodo-production`, allowed by Brett in chat on 2026-10-20 so publication runs unattended; without `--token-keychain` it prompts |

The draft readback requires the exact wire metadata (with the provider
sanitiser tolerances of `same_text`), public record access, restricted files,
one file per original with the original size and MD5, and the owner. The
publish readback requires `is_published`, the same identity and metadata, the
DOI pids, PICES (and its parent, when the verified community has one) as the
communities with PICES the default, and the original file.
A record is complete only when that readback passes.

### Journal, holds and pacing

- One canonical JSON file per record under `<state_root>/bulk-v1/records/`,
  written atomically after every receipt. An exclusive intent file under
  `bulk-v1/intents/` precedes the create, so a source can never be created
  twice by this route; the existing modern and legacy barriers also see it.
- Every request is recorded as `uncertain` before dispatch and completed after
  the response; each response is credential-screened and retained beside the
  record (`bulk-v1/evidence/<id>/`).
- No write is retried automatically. A hold on one record parks it with its
  reason. A transport hold (timeout, interrupted body, 429, 5xx, HTML or edge
  403) stops the run. Three consecutive record holds stop the run.
- `reconcile` reads only. With a known identity it moves the record to the
  phase the provider shows and allows a write whose effect is absent to be sent
  once more by the next run. A create whose answer failed validation is bound
  from its retained 201 body when that body now validates. A create whose
  answer was lost is bound when one unknown owner record carries its title;
  it counts as absent only when two inventories at least ten minutes apart,
  both captured two minutes or more after the create, show no unknown record
  that could carry it, and the next run checks the whole barrier again on a
  fresh inventory before re-sending. Every allowance is reported.
- A barrier hold on a record that never reached the provider is released with
  `unhold`, which can name owner records a reviewer found to be false inventory
  matches for that source; reviewed duplicates are excluded with `exclude`.
- An inventory that lists another owner's records, or fails, stops the run
  without holding the record in hand.
- Pacing: at least 0.8 seconds between requests (at most 75 per minute and
  4,500 per hour, under Zenodo's authenticated 100 per minute and 5,000 per
  hour). The transport keeps its contract of reading only `Content-Type` and
  `Location`, so the rate-limit headers are not consulted; a 429 stops the run.
- Records are bound by source and wire SHA256, not by the runtime, so a code
  change between stages strands nothing.

### Release

Brett's 2026-10-20 goal instruction is the release decision for every member
that is in a reviewed source policy, passes validation and is approved by its
batch review. Each publish run writes a `modern-bulk-release-v1` document that
quotes that instruction, names the batch reviews it relies on and lists the
records it covers. Brett can stop the route at any time; nothing here deletes
or edits a published record.

## Consequences

- About 13 requests per record across both stages (six for drafts, six for
  publication, plus the inventory pages): roughly 47,000 requests and 11 hours
  of paced API time for the 3,636 singletons, run in batches.
- The 26 verified PICES drafts are published by the `publish` stage after
  their own batch review; FGDC-141's unknown create stays held for its
  separate route.
- The 203 reviewed pairs (two byte-identical originals under two source ids,
  prepared by `modern_content_class`) use the same route as one record with
  both files: `plan-pairs` builds their sheet with a fixed assessment time
  (their wire depends on it) and the twin check against every journal source
  except each pair's own two ids; the record is journaled under the first id
  and intents claim both; uploads and commits are spent per file, and
  `reconcile` reads a pair interrupted between its uploads and allows only the
  missing file again. The 69 unreviewed singletons stay outside.
- One token per publish run replaces one per record. On 2026-10-20 Brett
  allowed the bulk publish stage to read the Keychain item (action
  `bulk-publish`); the single-record publisher keeps its live prompt.
