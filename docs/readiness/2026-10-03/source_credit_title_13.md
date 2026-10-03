# Five source credits and eight preserved display titles

Runtime/source contracts are frozen at `427a2197d339dab4b1a00a6767928cb0cb5b8389`
on normal branch `handoff/pr8-source-credit-title-13-20261003`. This branch includes
the preceding reviewed finite142 source access batch and preserves its manifests.

**13 more sources are supported: 2,443 supported / 1,757 held / six malformed.**
The five credits and eight individually selected report titles improve fidelity;
all source dates, rights/access, relationships, XML bytes, original credits and
complete original titles remain preserved. Source support is separate from remote
verification and publication approval, both still zero.

The additive [401-member credit profile](source_citation_credits_401.json), SHA256
`217a11a96ffbc1f55d6e065cfcc5fac34efd4a10057b399e4a6e25faa076887a`, preserves
all 220 prior cohort objects covering 396 source bindings verbatim. It adds exactly
FGDC-3779/3815/3958/3959/3965 from the reviewed proposal packet. Jury Rudjakov remains
explicit contributor credit rather than an inferred original PI. The same-report
reference supplies seven literal names for 3815, retaining the separate NPAFC credit,
malformed primary delimiter and TINRO context. Japan Meteorological Agency is the
explicit analysis credit for 3958/3959; 3965 has explicit FERHRI data/institution
context. All five are untyped. No contacts, hosts, XML authors or person identities
are invented. Original parsed origins, supporting elements and scoped notes are
mandatory in agent and both human QA schemas.

The [eight-title profile](source_display_titles_8.json), SHA256
`fa08a25108bbd90a03fe0c107d5b4398403deabd76df2b839830fde05eb46780`, covers
FGDC-1917/1922/1923/1924/1925/1930/1933/1935. Each display title is selected before
its exact reviewed responsibility clause. The complete original title and parsed
title XML, including all editorial/sponsor/committee credits, remain in notes and
the unchanged original artifact. Report 7 retains its full BASS/REX bundle context.
The existing artifact suffix rule applies only when the selected title fits 250
characters. This is a finite eight-source profile, not a truncation heuristic.

The optional `--source-title-interpretation-manifest` adds source/hash/complete
parsed element and whole before/after metadata checks. Agent and both human QA
paths require the same exact after-image. Removing, changing, rehashing or replacing
evidence fails closed; title/date/creator/license/relations/notes cannot piggyback
on a title correction. Source selection supplies no right, alias or provider ID.
The old creator profile remains accepted and both new interpretations are opt-in.

Five new guarded focused contracts and **317 guarded offline tests** pass. Actual
full QA verifies all 4,206 originals, 4,200 copied XML byte sequences and 4,194 payload
hashes. Exactly 13 complete metadata objects change through five creator lists and
eight titles with bounded preservation notes; 4,181 remain identical. Exactly 401
creator-policy references change (five additions +396 rebindings), with eight
additional title references within that same membership; 3,793 payload byte sequences
remain identical. All 176 protected access sources and 456 aliases remain held;
all other source statuses and hold reasons are unchanged. Technical totals become
4,142 passing / 52 held / 12 not constructed. The [validation receipt](source_credit_title_13_validation.json)
records actual inventories, tests and independent reviews.

The [identity adjudication](production_identity_adjudication.md) supports retaining
17317855/17317857/17317853 for the same existing imports, without using unknown
historical byte provenance as a catalogue-identity blocker. It grants no publication
or live correction. Contributor 361 / ADF&G 351 / Unknown 109 remain genuine scope
questions covering 821 distinct held sources. The six missing/malformed exact-day
dates, attribution gaps and 456 aliases remain held. No more receipt search or
source-scope extrapolation is performed by this batch.

## Offline reproduction

Checkout this document's final containing commit and install `requirements.txt`
in an isolated environment. Use the committed transport-blocked wrapper and full
command in [the finite142 checkpoint](finite_source_resource_access.md), replacing
only the creator option, adding the title option and choosing a fresh output:

```sh
--institution-creator-interpretation-manifest docs/readiness/2026-10-03/source_citation_credits_401.json
--source-title-interpretation-manifest docs/readiness/2026-10-03/source_display_titles_8.json
--output-dir /PRIVATE/NEW-SOURCE13-OUTPUT
```

Keep `--reviewed-at 2026-10-03T06:13:33Z` for exact report reproduction. In a
**separate checkout of frozen
`7a46be5b53d378643c15e67494575e8fa9ef33b5`**, run that checkpoint's finite142 command
to reproduce and retain predecessor report `f89ea065...6a0`. Then return to this
document's final containing commit for source13. Predecessor options run against
the newer runtime cannot reproduce the old report, because its profile binds every
script hash. Audit completed outputs only:

```sh
python docs/readiness/2026-10-03/audit_source_credit_title_13.py \
  --before /PRIVATE/REPRODUCED-FINITE142-OUTPUT \
  --after /PRIVATE/NEW-SOURCE13-OUTPUT
```

The completed guarded resume reproduces the exact report and all 4,194 prepared
payload hashes. Rerun with unchanged code, inputs, arguments and timestamp to
verify cache/resume equality. These commands use no provider operation. The
parent dispatches any separately approved provider/identity/file/readback/release
stage; neither original nor fresh failed canary may be rerun. The retained imports
FGDC-2057/2043/2725 are source-supported; FGDC-1238/2731 retain access scope holds.
Their exact current source/hash/ID/DOI state is included in the validation receipt.
