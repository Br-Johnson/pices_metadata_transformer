# Catalogue tail publication receipt — 2026-10-24

This receipt continues the [v2 publication receipt](../2026-10-22/v2_publication_receipt.md). It
covers the records published after 2026-10-22: the repaired and held singletons, the 25 non-Exxon
pairs, the creators64 lane and the 36 held sources Brett cleared on 2026-10-23. Every record was
reviewed by an independent AI reviewer against its original XML in v1 and again in v2, and passed
validation, the pinned schema and an emulation of the provider's sanitiser before it was created.

## Result

| | Records | FGDC files |
|---|---|---|
| Published by 2026-10-22 (v2 receipt) | 3,823 | 4,026 |
| bulk-018: seven sanitiser repairs and FGDC-1939 | 8 | 8 |
| bulk-019: FGDC-141 | 1 | 1 |
| pairs-002: the 25 non-Exxon pairs ([ADR 0015](../../adr/0015-nonexxon-pair-policy.md)) | 25 | 50 |
| bulk-020-v2 and -v2b: creators64 round 2, 19 with the box as text | 56 | 56 |
| bulk-021: creators64 round 3, FGDC-3851 | 1 | 1 |
| bulk-022-v2 and -v2b: the 36 held sources ([ADR 0016](../../adr/0016-held37-reviewed-clearing.md)) | 36 | 36 |
| **Bulk journal, final state** | **3,950** `published`, `wire_version` 2, no holds | **4,178** |

**Duplicate check.** The public PICES community listing at 2026-10-25T00:09Z returned 3,956
records: all 3,950 bulk records once each, none missing; the five protected legacy records
17317851, 17317853, 17317855, 17317857 and 17317859; and record 15046283, an unrelated PICES
dataset. Every record id is distinct and no FGDC file is attached to two records (228 two-file
records). With the five legacy records, 4,183 of the 4,206 source files are represented.

## Decisions applied

- Brett's 2026-10-22 creator decisions (Unaami as organisation; credited name as organisation;
  the record's own byline) for creators64; FGDC-3851 as Hermann, Albert J. from its contact element.
- Brett's 2026-10-23 rule for a box that contradicts the record's own text: no map, box as text
  (`map_as_text.json`, 19 sources; `../2026-10-24/map_as_text_r2.json` adds FGDC-4139).
- Brett's 2026-10-23 answers on the held-sources evidence sheet
  ([decisions](../2026-10-23/held_sources_decisions.json)): 22 access, 9 creator and 5 date holds
  cleared and published; the tenth creator record, FGDC-2817, has a second, undecided access text.

## Run record

- Reviewers held two bulk-022 records in v2; both were fixed in `5152eed` after an independent
  review and published from the re-sheet bulk-022-v2b: FGDC-4139 (a point in the wrong hemisphere,
  now box as text) and FGDC-1318 (the company contact "Resource Data, Inc." had been typed as a
  person).
- Six title-twin pairs in bulk-022 were adjudicated distinct (global and regional NEAR-GOOS sets;
  the POST project and its database) and recorded as allowances.
- Zenodo answered 502 three times on 2026-10-24: twice during the GET-only owner inventory, before
  any write (the drafts runner now waits 180 s and reruns such a stop), and once on FGDC-759's
  content upload. That draft listed its file without content, which the reconcile step could not
  read; the gap was fixed and independently reviewed in `22577b2`, FGDC-759 was reconciled by GET,
  its content resent once and the record published.
- Code on main: `58033eb` (creators64 round 3), `0572e70` (held37 lane, ADR 0016), `5152eed`,
  `22577b2`. Each change had local tests and an independent review before it reached a provider run.

## Not published

| Category | Sources | Why |
|---|---|---|
| Excluded duplicates | FGDC-77, 78, 460, 2364, 2421, 2515, 2538 | Duplicates of published sources in the source collection (by design). |
| creators64 holds | FGDC-287, 411, 771, 2229, 2235, 2824, 3786 | Compound, venue or unnamed credits with no owner decision. |
| Undecided access text | FGDC-2817 | "Check with Contributor" with "Refer to webstite URL: http://www.csa.com/"; 13 published records carry the same pair. Its creators are ready. |
| Kept held by Brett | FGDC-909, 3850, 4185, 21, 4077, 4184 | DoD marker; no metadata date; test or multi-document files. |
| Retired | FGDC-3373, 3484 | All NUL bytes; nothing to recover. |
| **Total** | **23** | 4,206 − 4,183 represented. |

## Follow-ups for Brett

- Four published records show a map point in the wrong hemisphere under the same 2026-10-23 rule:
  FGDC-4115 and 4140 (Station Papa at 145E), 4098 (Bowie Seamount at 135.6E) and 4159 (Babine Lake
  at 126E). Fixing them is an in-place update of published records (same DOI, new revision).
- v2 maps only the first `<stdorder>`; 35 DFO OSAP sources have a second ordering block that is
  only in the attached XML.
