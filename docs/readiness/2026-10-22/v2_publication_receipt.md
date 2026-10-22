# v2 publication receipt — 2026-10-22

Brett's goal (2026-10-20) was to publish every appropriate record to production Zenodo, where
appropriate means reviewed by an AI for accuracy and passing validation. On 2026-10-21 he chose
the v2 mapping, [ADR 0014](../../adr/0014-v2-wire-and-in-place-update.md), and approved the full
run after the FGDC-985 canary.

## Result

All 3,823 approved records are published in the PICES community in the v2 form. They are 3,620
singletons and 203 two-file pairs, covering 4,026 FGDC sources.

| | Records |
|---|---|
| Created and published directly in v2: bulk-012 to 017 and pairs-001 | 1,307 |
| Published in v1 earlier, then updated in place to v2 (same DOI, new revision) | 2,516 |
| Bulk journal, final state | 3,823 `published`, `wire_version` 2, no holds |
| Distinct Zenodo record ids / DOIs | 3,823 / 3,823 |

Every record was reviewed in v2 by an independent reviewer agent against its original XML:
19 recorded `-v2` reviews in `bulk-v1/reviews/`, all members approved.

**Duplicate check.** The public PICES community listing at 2026-10-22T20:50Z returned 3,829
records:

- all 3,823 bulk records, each once, with none missing;
- the 5 protected legacy records 17317851, 17317853, 17317855, 17317857 and 17317859;
- record 15046283, an unrelated PICES dataset.

No duplicate was created. Two pairs, FGDC-3027 and FGDC-2920, were held by the inventory barrier.
Their title matched legacy record 17317851 (FGDC-2043) once the artifact suffix was dropped. The
three are distinct Exxon Valdez metadatabase entries with different abstracts and XML, so the holds
were released with `--allow-inventory-record 17317851`, the evidence recorded, and both published.

## Run record

The pipeline `bin/pices-pipeline-v2.sh` was the single provider writer, from 2026-10-22T12:00Z to
20:46Z. Eight transient failures were reconciled by GET and resumed automatically: lost answers,
and Zenodo 500s on reads. One 500 stopped the run once, at FGDC-2667 in bulk-012, before 5xx
recovery was added to the runners; it was reconciled and the run resumed. The ledgers are in
`bulk-v1/runs/` and the console in `logs/bulk/pipeline-v2.txt`.

## Not published, by design

- **Fail validation.** Seven records the provider's sanitiser would alter: FGDC-2570, 2583, 2588,
  2589, 2591, 2733 and 2768. Their source text needs repair first.
- **Held by the v1 accuracy review.** FGDC-1939, for a cut keyword. It has an existing v1 draft;
  publishing it needs the corrected wire reviewed and a draft-update step.
- **Awaiting its own decision.** FGDC-141, an unknown create from the single-record chain.
- **Already published, protected.** The five legacy records FGDC-1238, 2043, 2057, 2725 and 2731.
- **Excluded duplicates.** Seven duplicate sources, and sources outside the reviewed policies.
