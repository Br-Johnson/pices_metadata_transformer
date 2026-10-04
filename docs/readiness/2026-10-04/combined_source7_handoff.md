# Combined existing-source corrections — 2026-10-04

This single integration combines the reviewed FGDC-885/887 pair from
`52e2cac91690c7f21fc62d0223be862a9f971121` with five disjoint corrections from
`4b0a387807ef8ce30aac21a7cac1f7cfc1686d00`, based on main
`ecfba4ed3496c0a8d400eb2ace46800f0c166708`. Earlier pair/five receipts remain
immutable evidence of their own scopes and intermediate counts. This handoff
supersedes their separate preparation choices.

| Exact sources | Interpretation and preserved condition |
| --- | --- |
| FGDC-885, FGDC-887 | NPAFC report descriptions; summarized-data access and publication notification remain literal. No notification fulfilment or explicit XML exemption is claimed. |
| FGDC-1257, FGDC-1258, FGDC-1262, FGDC-1273 | Radio publications; data-source publication acknowledgment remains required. No satisfaction of that condition is claimed. |
| FGDC-4064 | The abstract explicitly applies password access to the most recent data. No password entitlement is claimed. |
| FGDC-4063 — held control | The password target remains unresolved. FGDC-4064's evidence does not answer this separate record. |

All seven interpretations are REVIEWER_RECONCILED. Separate USER_ATTESTED
restoration authority remains mandatory, without independent agreement verification,
new underlying-data rights, license or release permission. Original constraints,
dates, credits, notes and original XML remain intact. No creator correction is
added by this integration; the earlier source-supported credits remain unchanged.

## Profile and measured result

Select [profile 563](finite_source_resource_access_563.json) through the existing
`--dataset-access-interpretation-manifest` option. Its SHA-256 is
`7e9f66fc19968c3f2784ff0ea5ab6d1169c1bd165035e5612c78332567636224`.
Keep the other current source manifests, including source-scope profile 904.
The 556-member base, both additions, all full contexts and the three exact review
blocks remain unchanged. Runtime review selection uses exact ID/hash membership
and each review's original aware timestamp. A failed check cannot fall back to
another review. Old 558/561 profiles remain accepted for reproducibility.

The [combined validation](combined_source7_validation.json) measures eight sources
before, after, repeated and withdrawn. Exactly seven move held to supported;
FGDC-4063 remains held with its entire payload unchanged. Only each selected
record's exact policy reference is added. Complete raw metadata and all copied
XML remain identical. All 4,206 originals match the frozen ledger before and
after measurement. Restricted access and blank licenses remain mandatory.

The [combined ledger](combined_source7_integrated_source_status.json) recounts
**3,645 supported / 555 held / 6 malformed** from the frozen 3,638/562/6 ledger
and this measured seven-record delta. All 4,199 unselected status objects remain
identical. All 456 exact-copy alias identities and 31 exceptions remain held.
This is bounded fresh classification plus cached corpus accounting, not a fresh
full-corpus classification or remote audit. The original inventory digest is
`66dbe250d3a91f0b377cdfc0a5054423516666d798273f1e30858a36f8f758a5`;
the combined status-row digest is
`648074d12fb246a63cf3beb7febefdf3c009dd3fcbb92bf6aa9ee5e589ee1e76`.

## Reproduction and repository gates

With existing dependencies, from the repository root:

```sh
env -i PATH="$PATH" python -B docs/readiness/2026-10-04/validate_combined_source7.py \
  --output /tmp/pices-source7-new-verification
python -B ci/run_offline_tests.py tests.test_combined_source7
python -B ci/run_offline_tests.py
```

Use a new output directory. The eight-source run is below the ten-record smoke
limit and rejects sockets, DNS and provider transport. It verifies the complete
original XML inventory and writes measured validation plus the combined ledger.
Current assessment time and checkout paths affect prepared-payload hashes;
original source, profile, complete metadata and status-row hashes are bound.
The guarded suite clears credentials and enforces network/private-file/process
boundaries. Combined contracts also compare every previous interpretation and
exercise agent and both human QA routes under profile 563.

One non-draft PR contains both batches. Merge requires actual passing CI and a
substantive Codex review covering the current head with material findings resolved,
under the standing repository authorization. The GitHub checks and review timeline
record those final outcomes; historical offline receipts are separate evidence.

No source XML, provider runtime, spent-action ledger, existing provider ID/DOI,
production deduplication or release gate changes. No provider request or outside
message is performed. Provider transport investigation remains a separate lane;
this integration does not establish transmission, readback or publication.
