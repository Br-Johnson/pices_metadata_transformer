# Publication batch readiness — 2026-10-04

Post-merge evidence update: the [raw inventory addendum](production_owner_raw_inventory_addendum.md)
verifies the new three-response owner listing and narrows the remaining capture
gap to two specific file-detail responses. The frozen PR31 plan and the historical
capture-limit statements below retain their original measurement scope; all
execution holds remain. PR31 merged as `4bc59af3ff4432e297e64d3c70b6c57ecdaf0390`
after 540 actual guarded CI tests and independent Codex review.

Base: merged PR30, `6825c2cda6b8932e2c053af9a76582452524dca3`.
The [offline planner](../../../scripts/publication_plan.py) adds the missing
whole-target publication planning view without changing the uploader, class
guard, identity adoption, QA, release or provider transport.

The [version-1 contract](../../publication_plan_contract.md) defines a distinct
`nonexecutable_publication_plan`, its exact evidence inputs and optional sanitized
restart export. It is deliberately not consumable as `safe_to_upload` or a grant.

| Planning view | Count |
| --- | ---: |
| Original source files, all hashes verified | 4,206 |
| Unique record targets | 3,978 |
| Source-supported singleton targets | 3,705 |
| Source-supported paired targets | 228 |
| Original files represented by supported targets | 4,161 |
| Held targets / malformed originals | 39 / 6 |
| Prospective batches, at most ten whole targets | 394 |
| Executable targets / provider actions | 0 / 0 |

The [saved publication plan](publication_plan.json) retains every target and all
original filenames, byte sizes and SHA-256/MD5 values. Those descriptors are
expected source-file evidence, not validated metadata/artifact policy contracts.
Singleton payload binding remains pending; paired targets retain their exact
saved v2 references and the24-fresh/204-historical artifact resolver. No source
classification or class artifact rebuild was needed.

## Identity decisions and capture limit

All228 pair decisions now carry the [completed reader's parent-relayed summary](production_owner_inventory_parent_summary.json):
42 successful GETs,20 owned concepts/depositions,19 published plus one draft,
24 file descriptors, terminal page20+0 and unchanged page1 consistency, all19
published histories with one version, and zero exact pair candidates by source
ID/XML hash/exact filename/provider MD5 plus size. The code lane has not received
the underlying response ledger. The decisions therefore state **reported zero
exact current-owner candidates; raw-capture review pending**. They do not claim
global or deleted/tombstone historical absence, or authorize creation.

The five existing singleton associations retain their IDs, DOIs and complete
historical public beforeimages. The parent reports them unchanged in the fresh
inventory. They remain protected correction candidates, not new creates. Other
singletons remain identity-unassessed because the228-pair comparison does not
establish their absence. Title hints for2920/3148 and3027/3255 remain distinct
from record17317851 and from each other. Poster10042430 and programme15046283
remain excluded from FGDC restoration.

The integration owner attempted the available internal agent-message tool for
reader `01a10232-63b4-71e5-b20c-65784d3de039`; it returned “agent not found”. No
outgoing cloud-thread coordination tool was exposed. Parent can relay the reader's
credential-free durable capture path/artifact reference and hashes. Preserve the
completed request ledger; no inventory re-fetch is requested from this code lane.
Exact current metadata/files/version/DOI evidence must be independently checked
before these planning decisions become provider identity or execution evidence.

## Guarded validation and reproduction

From the repository root, with public requirements installed:

```bash
python -B docs/readiness/2026-10-04/validate_publication_plan.py \
  --repo . --output /tmp/pices-publication-plan-reproduction
```

Choose a fresh output directory. The helper clears the environment, installs the
existing offline guard before importing the planner, verifies all4,206 originals
before/after, and compares complete unchanged-repeat plans. It writes
`publication_plan.json` and `validation.json`. The [saved validation receipt](publication_plan_validation.json)
records the actual checkout, helper/runtime bindings and output hash. Repository
paths and capture dates inside retained historical evidence describe their
original measurements; they are not new capture claims.

The [focused test receipt](publication_plan_focused_checks.json) records25 passing
guarded tests. Eight new contracts cover exact target/file/batch accounting,
preserved IDs/DOIs and both pair members, summary-only evidence limits, original
and evidence tampering, deterministic repeat, stale/foreign restart exports,
uncertain creates/writes, missing states, partial drafts, published records,
duplicate provider IDs/DOIs, protected DOI conflicts, excluded identities and forged approval fields. Final
current-head CI and independent Codex review remain the repository merge gates.

The [initial independent review](publication_plan_initial_independent_review.json)
identified a DOI-only restart conflict gap. The correction holds foreign protected
DOIs and repeated DOIs even when numeric record IDs differ, and compares the
protected target's own DOI consistently without changing literal reported values.
The final focused contracts and guarded dry run pass; the no-snapshot manifest is
byte-identical across this correction. Earlier v1/v2 measurements remain retained
in the author's evidence workspace and the initial PR revision preserves v1.

Ordinary manifest generation is also available without a provider client:

```bash
python -B -m scripts.publication_plan \
  --repo . --batch-size 10 --output /tmp/pices-publication-plan.json
```

The optional `--restart-snapshot` accepts only an explicit sanitized export bound
to `publication_inputs_sha256`. It reports legacy facts conservatively and never
updates a registry. Missing state does not replenish a create allowance. Known
drafts require same-identity/file readback; uncertainty stays held. Existing
published identities are preserved without replacement. Every restart hint has
`safe_to_retry: false` and every target remains nonexecutable.

## Remaining consequential work

The [staged source briefing](remaining45_staged_questions.md) reduces45 targets to
two initial artifact-location requests: surviving catalogue/history/export
evidence (14 targets), then historical policy/reference material or custodians
(21 targets). A third exact-work/product responsibility request covers the final
ten if source-specific agent work does not resolve them. The [routing JSON](remaining45_staged_questions.json)
keeps all45 assignments and the existing21-group exact questions. No questions
were sent to Brett or external source owners by this increment.

The static [execution audit](publication_batch_readiness_design.md) identifies
reusable singleton recovery and the actual remaining live gaps: source-aware
production transport compatibility; class-aware durable two-file execution and
readback; reviewed production identity/concept/version/DOI reconciliation;
independent QA/release and a bounded grant. Existing guards remain intact. The
separate Mac diagnostic's first quoted-revision request received400 with no
reported state change; the corrected bare-revision request was awaiting Brett's
token entry when parent reported it. This lane neither repeats nor interprets
that pending provider action as success.
