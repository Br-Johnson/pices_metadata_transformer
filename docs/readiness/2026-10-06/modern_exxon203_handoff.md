# Frozen offline Exxon203 paired preparation

The separate class API prepares **203 supported targets containing 406 original
XML files**. Existing singleton wire coverage remains **3,262**. Combined modern
wire preparation therefore covers **3,465 targets /3,668 originals**; it does not
establish paired execution readiness. **468 supported targets remain outside the
modern mapping:443 singletons and25 pairs.**

Source support stays 3,933 targets (3,705 singletons and228 pairs); the 39 held targets
and 6 malformed sources are unchanged. All 4,206 original XML files remain intact.
No provider requests, credential access, grants, attempt resets, production writes,
identity reassignment, publication or deletion occurred in this coding increment.

## Contract and evidence

- [Finite203 mapping](modern_exxon_pairs203.json), SHA256
  `19686d6204a2d42e42dbef735313693e2a47553ec135f674c6e7c235a82ffa58`.
- [Independent source assessment](modern_exxon203_source_review.json), SHA256
  `51c7266a2da2d270fc52ba70e712faa27a3ffd59cd2ba7b44ff4f7dbdd3bf48d`.
- [Measured preservation](modern_exxon203_validation.json) and
  [31 affected guarded contracts](modern_exxon203_focused_checks.json).
- [Architecture and limits](../../adr/0010-finite-modern-content-class-preparation.md).

The finite set is rederived from the approved 228-pair representation and 821-member
Exxon creator profile, then checked against the supported source plan. The prior 412
singleton manifest supplies the exact reviewed three-creator projection only. Both
original names/bytes, member payloads, policies, v1 artifacts and the whole v2 class
contract remain bound. Complete assembled class metadata is retained in an escaped
wire block, including the two-file provenance notes and unchanged source access
conditions/blank license. No primary or canonical member is selected.

The API freshly rebuilds both source assessments at a caller-supplied, fixed,
timezone-aware nonfuture time. `PreparedClass` exposes `record_target_id`, two
`source_ids`, wire `body`, two `(filename, bytes)` `originals`, complete
`legacy_target`, `evidence` and its `binding`. It has no singleton `source_id` or
`xml` alias. `validate_prepared` rebuilds everything; self-rehashed edits cannot
validate. All upload, remote verification and publication flags remain false.

## Frozen code and actual validation

Measured local code/test commit:
`bdedf7a7447603f71827c1895a5749823321d53f`.
Runtime SHA256:
`31dd71eb8bfe8c87f50d7ff3c4cbc22f045d926c099f81c21db2dc6df70614a2`.
The 179-file source/test/contract/CI binding is
`8daa38ea93d3ba93bc862e783f788a921454ec5567072ab78015d059f68c551d`.
Subsequent documentation receipts do not change either binding. The final PR head
requires substantive independent Codex review and actual full current-head CI before
merge; the PR carries the resulting remote commit, CI and review links.

All 203 new targets were prepared twice. Every one of the 3,262 existing singletons
was prepared once at its exact retained paths and compared for identical wire and
nonruntime evidence. All 25,421 retained public files, 18 referenced public profiles
and 4,206 original XML hashes were verified before and after. All four guarded
measurement processes passed with no unexpected network, private-read, process or
write events. The individual 406 alias-file holds remain intact; both-member class
assessment is supported for 203. These are different ledgers and must not be conflated.

Actual roots: `/tmp/pices-exxon203-shard0-v1` through
`/tmp/pices-exxon203-shard3-v1`. Receipt SHA256 values in that order:

```text
17d96e87e53fcf09cb8d96a31caab73c97e56d52a25d69fe4c80ec3c60b775b2
3387a510af09526b4cc279e2575d9415c2f7c04f136fc9b143cc73624634fe0d
1a0b3d3c7d9400de571d6cd28782091679ab9135a3248312d7de74f8bb166f8b
96d498d51f8ad0ead9eba55ec0e921548e8b494d5ed2321f8ba8ba346a2ef97e
```

The original XML aggregate remains
`3430315763379ef81c393cca00eb776952df3ad3f66856ef4b15edd48e396013`;
the Git FGDC tree remains `6c509a3e62252888a6709d1df94bcf109b83241b`.
Preserve these actual roots, every earlier comparison root and all historical
canary/production receipts. Missing state is never permission to recreate anything.

## Runnable offline verification

From the frozen checkout, use the guarded harness:

```sh
/tmp/pices-code-venv/bin/python -B ci/run_offline_tests.py \
  tests.test_modern_content_class tests.test_content_class_targets \
  tests.test_content_class_guards
```

The [measurement helper](measure_modern_exxon203_coverage.py), SHA256
`8d4be3e8b484f0abc6e94074bf2cfea6e64f2d88dcb4c27ccabddd6b05ddd830`,
requires all exact retained public baseline roots and profile paths from the prior
handoffs. It intentionally cannot substitute a new classification for missing
historical inputs. To repeat shard 0 choose a fresh `/tmp` output, then repeat for
indices 1–3 and independently aggregate all four actual receipts:

```sh
/tmp/pices-code-venv/bin/python -B \
  docs/readiness/2026-10-06/measure_modern_exxon203_coverage.py \
  --repo "$PWD" --output /tmp/pices-exxon203-shard0-independent \
  --shard-index 0
```

Each process clears environment credentials, installs the offline guard, permits
only exact public baselines for reads and writes only to its fresh output. The API
it exercises is `scripts.modern_content_class.prepare(record_target_id, paths,
reviewed_at=...)`; output is a proposal, never a provider command.

## Compatibility and remaining work

Adding this module changes the all-script runtime hash. The explicit bridge admits
PR42 runtime `d09495acd462e7a51c3c1344265758ed8482256e9d901c05b64711734316ef2d`
only for its six existing singleton policies. Exact nonruntime evidence, original
journals, spent budgets and durable create intent remain mandatory. Started capture
and publication states do not migrate or receive new grants. No class policy enters
this bridge; all existing singleton and legacy release guards remain closed to pairs.

The 443 residual singletons comprise 289 creator426 cases, 70 DFO Staff collective
credits, 79 direct-credit interpretation cases (69 typed holds and 10 name-only), and 5
protected existing records. The 25 residual pairs comprise 24 organizational and 1
personal dependency. This is the frozen mapping partition, not a declaration that
all residual source interpretations are permanently blocked. Subsequent coherent
source-supported increments require their own review, tests and merge.

Class-aware durable multi-file execution, owner reconciliation, source-specific QA,
release, exact remote readback and destination permissions remain separate gates.
Existing records/DOIs and excluded unrelated records remain protected. Parent owns
production destination clarification and any live dispatch to the sole Mac executor.
The October 4 committed inventory comparison and parent's reported byte-identical
October 6 repeat remain separately dated; this lane did not repeat provider reads.
