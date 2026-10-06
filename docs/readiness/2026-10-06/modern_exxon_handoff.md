# Finite Exxon singleton preparation handoff

This increment selects **412 supported, unprotected singleton targets** from the
existing Exxon primary-citation interpretation. Measured modern coverage is
**3,145**: the preserved PR37 population of 2,733 plus these 412. All four guarded
measurement shards passed, as did **148 focused tests**, with unchanged source
bindings and zero unexpected guard events. The [aggregate receipt](modern_exxon_validation.json)
and [focused result](modern_exxon_focused_checks.json) retain the actual evidence.
No provider request or production release is authorized by this handoff.

The measured runtime is
`1ac72000a7697bedef5b6e76ca0a28252a85f36bb0529a7e521c68aa4177d9e2`;
the source/test binding is
`0c2926be37acfaffe2aea3bbe2521e8149586e5894f34ab8afddd802e98bc278`.
Actual current-head CI, independent review and merge evidence are retained in the
PR timeline. Local receipts identify the base checkout plus measured changes;
they do not claim to be a CI run of the later published commit.

## Exact scope and evidence

The ordered credits remain the Exxon Valdez Oil Spill Trustee Council,
`Bodkin, James` with `U.S. Geological Survey, Anchorage, Alaska`, and
`Dean, Thomas A.` with `Coastal Resources Associates, Inc., Carlsbad, California`.
The finite projection uses one organizational creator and two personal creators
with the already reviewed family/given fields and one literal affiliation each.
It does not infer XML authorship or authorship of the separately cited research
articles, introduce identifiers, or split the affiliation/location strings.

| Binding | Exact SHA256 |
| --- | --- |
| [412-member mapping](modern_exxon_singletons412.json) | `5dbfeb098ee8b3bbad0e06d020c1c14c88e32363d45fab4e69a5cc961482a94f` |
| [Existing creator profile](../2026-10-02/exxon_citation_interpretation.json) | `ee49147aec99d83cf54cb7fa4e59f7e50229967af0f08f5408e97144367e99e5` |
| [Independent source review](modern_exxon_source_review.json) | `ad17c1efcb4014edcfc3e4fb8c08fb884ee4ea4928805fb7929277f1a6d155f3` |
| [Pinned service creator contract](modern_exxon_creator_contract.json) | `e320207b7feda481d7466eaa28e021d64ce24ce7e25f442e0f33e164fe9d88ab` |
| [Frozen publication plan](../2026-10-04/publication_plan.json) | `39d2894d518fa5a10d87cc784ce40064e6757529f23219eea153f25805f506ad` |

Preparation evidence uses `schema_version: 4` and policy
`modern-xml-exxon412-v1`. The actual legacy artifact policy must retain its
separate Exxon creator reference; citation426 remains unchanged. Preparation
reruns source assessment and checks the exact singleton plan, source bytes,
complete creator objects, original artifact contract, source metadata date and
restricted XML with blank license. All assembled legacy metadata remains in the
escaped preservation block; `publisher: Zenodo` still identifies the artifact
host. The pinned service contract supports the personal/affiliation request
shape, not deployed provider behavior. Readback may add only the exact derived
personal display name; other name, order, affiliation, role or identifier changes
remain held.

FGDC-2043 and FGDC-2057 remain protected existing-record corrections preserving
IDs/DOIs; FGDC-1994 remains source held. The **203 paired targets / 406 source
members with the same mixed Exxon creator dependency** remain outside the
singleton mapper. This creator contract is a dependency for a future separately
reviewed two-file identity/QA/execution contract, not admission of those pairs.

The original [remaining-target census](/tmp/pices-pr37-remaining-census.json), SHA256
`64a19fe425a9e998fdce0afa8f47b6d38ff4cf58bb6f326573ea8dd2b1bb5043`,
retains the exact IDs and partitions. The aggregate receipt carries the exact
remaining membership and source hashes. The remaining 788 supported targets comprise:

| Remaining mapping/dependency class | Targets |
| --- | ---: |
| Other creator426 singletons | 315 |
| DFO Staff singletons | 70 |
| Direct name-only singletons | 101 |
| Typed direct mapping holds | 69 |
| Protected existing records | 5 |
| Paired targets | 228 |

These are mapping boundaries, not new source-status decisions. The frozen 39
source-held targets and six malformed inputs remain unchanged. Paired targets
include the 203 Exxon dependencies, one creator426 dependency and 24 other
primary-credit dependencies.

## Offline reproduction and retained receipts

Run from the frozen reviewed checkout with its dependencies installed. The
[measurement helper](measure_modern_exxon_coverage.py), SHA256
`4376cf168a0410ac17e324d0c7434d94d4525f901eaa01fe833fe9fa4f70b7c7`,
clears the environment, supplies dummy credentials only, and installs the exact
offline guard before classification/preparation. It blocks network, private
reads, unexpected subprocesses and writes outside a fresh output root.

Reproduction requires the unchanged public PR37 aggregate
[receipt](modern_direct_primary_validation.json), SHA256
`dee8b89dfb8f452b1d88b5e23face7ba81417ca0b23ba1b4d198b158bf900464`,
and its recorded inputs at `/tmp/pices-direct-primary-shard{0..3}-v1`.
The retained old105 baseline must remain at
`/tmp/pices-modern-old105-baseline-20261006/baseline.json`, SHA256
`87599287eadabf8a75f26667a39705b64c1c5cba888f67a5a664ae5ec8b183e0`.
Its prepared root and every retained path stay exact. Eight referenced public
profile files under
`/workspace/pices-modern-primary-organizations-20261006/docs/readiness`
are also required at their original paths and digests; the helper derives the
exact file allowlist from the pinned inputs and grants no broad directory or
write exception. Missing retained inputs require evidence recovery, not a newly
classified substitute baseline.

Run indices 0 through 3, each with a distinct fresh output directory:

```sh
python -B docs/readiness/2026-10-06/measure_modern_exxon_coverage.py \
  --repo /workspace/pices-modern-remaining-citations-20261006 \
  --output /tmp/pices-exxon-rerun-shard0 \
  --shard-index 0 --shard-count 4
```

Each shard freshly classifies only its 103 assigned new IDs and prepares each
twice. The 2,733 old preparations are compared once each across the shards at
their retained input paths, without reclassification: request wire must be
byte-identical and every nonruntime evidence field equal. Each shard verifies
all retained input/wire/evidence hashes, all 4,206 original hashes and source
bindings before/after, limits, complete legacy metadata, creator/date/rights
fidelity and zero unexpected guard events. Retain `coverage.json`,
`wire_artifact_manifest.json`, `retained_file_manifest.json` and their referenced
artifacts. Aggregate only after checking the four disjoint new/retained ID sets,
matching frozen runtime/policy/source bindings, complete 412/2,733 coverage and
all saved hashes. A single shard does not establish the aggregate result.

The focused offline command is:

```sh
python -B ci/run_offline_tests.py \
  tests.test_modern_exxon_coverage tests.test_modern_primary_organizations \
  tests.test_modern_organizational_coverage tests.test_modern_singleton \
  tests.test_modern_singleton_executor tests.test_modern_publication \
  tests.test_modern_publication_qa
```

Record actual results separately from these reproduction instructions. Actual
current-head CI and substantive Codex review remain required for repository
integration; local measurements do not substitute for them.

## Preparation and separately gated execution

The interfaces remain those in [ADR 0005](../../adr/0005-finite-modern-singleton-drafts.md),
[ADR 0006](../../adr/0006-finite-modern-singleton-publication.md) and the prior
[coverage handoff](../../adr/0008-finite-direct-primary-organizations.md).
For a separately prepared selected input, these entrypoints make no requests:

```sh
python -B -m scripts.modern_singleton_executor prepare \
  --json-file /approved/prepared/FGDC-1839.json \
  --output-dir /canonical/production-output

python -B -m scripts.modern_singleton_executor preflight \
  --json-file /approved/prepared/FGDC-1839.json \
  --output-dir /canonical/production-output \
  --grant /approved/grant.json --duplicate-proof /approved/duplicate-proof.json
```

The paths above denote actual parent-reviewed inputs; they are not supplied
grants. Keep the canonical original production state/history root. A fresh
measurement directory is not a replacement execution root or a way to bypass a
spent attempt. The historical-runtime bridge admits PR37 only for its prior
policies; new Exxon preparations require the current runtime. Every nonruntime
field and original grant/request time still has to validate, with no grant
renewal, budget replenishment or migration of an already-started operation.

After the merged reviewed compatible client, verified live canary, complete fresh scoped
duplicate/history evidence and bounded provider grant are established, parent
alone may dispatch the sole assigned Mac executor using `execute`. Its token is
entered through the hidden terminal prompt and kept in memory. `readback` retains
the original grant/state and GET-only recovery boundaries; uncertain effects and
consumed attempts remain held without mutation retry or reset. This handoff
dispatches neither action.

Publication remains a separate `scripts.modern_publication` sequence:
`bridge`, saved `capture`, `prepare-qa`, `preflight`, then separately authorized
`publish`/`readback`. The CLI requires `--json-file`, `--output-dir`,
`--preparation`, `--old-grant` and `--old-duplicate`; additional grant/snapshot/QA/
duplicate/release inputs must satisfy the action contract in ADR 0006.
Source support and this creator projection supply no live absence proof, new
license, publication grant or human release. Full metadata/XML readback,
record QA, independent program review, human release, PICES community authority
and existing-record/DOI protections remain effective.

Parent reports the bounded Mac Sandbox canary completed on October 6: draft
612988 at revision13 remained unpublished without a PID; the 439-byte XML upload,
both exact downloads, repeat reads and final fence passed. The retained Mac
closure `task4/mac-xml-canary-closure-20261006.json` has SHA256
`e109ae135006ba5829ff44e8e0da289e6cc985f7c506d7a57e9f89bf565df948`.
Reported cumulative counts are 220 GET / 9 PUT / 1 create / 1 UI / 1 file-init /
0 commits. This code lane has not independently read that Mac-local receipt.

The report identifies a separate production-client dependency before batching:
content PUT may already return `completed` and need no commit, and downloaded
Content-Type may repeat the identical binary value. The current executor and
publication transcript validators still require the pending/commit path and a
single binary media value. Preserve actual consumed actions and all historical
receipts; resolve these contracts in a separate reviewed repair using retained
credential-clean response evidence. The observed metadata PUT revision jump
affects the frozen Mac path, not the production creator path. This bounded
existing-draft canary does not establish production bulk restart behavior.
