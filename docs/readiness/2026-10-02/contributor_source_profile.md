# Contributor or Source access interpretation

Brett replied **“yes”** at **2026-10-02 23:43 UTC** to: “in the PICES records, does ‘Check with Contributor or Source.’ mean contacting them to obtain the underlying dataset, just like ‘Contact Source.’, rather than restricting reposting the metadata?” The separately recorded USER_ATTESTED provenance is message `Sentinel_2407c97336c88191a6a5ab9160a3e637`, source thread `01a0f2a9-8da9-7252-b293-c326ee80b018`. The supplied timestamp has minute precision; `23:43:00Z` is its normalized minute, not a claim of independently known seconds.

[The manifest](contributor_source_interpretation.json) binds exactly 585 original source IDs and SHA-256 hashes. All four plain fields (`metainfo/metac`, `metainfo/metuc`, `idinfo/accconst`, `idinfo/useconst`) contain the exact phrase **Check with Contributor or Source.**, and no member has metadata security or extension nodes. Its membership independently matches the integration owner's raw-source census. This is a separate attestation; no synonym, punctuation variant, or different contributor wording inherits it.

The optional `--contributor-access-interpretation-manifest` selects this evidence only for its exact access wording, alongside the existing Contact Source, creator and registration profiles. The validator pins the canonical sorted compact source-map SHA-256 (`1c9293ce0936f3e61d16325bc5fd6f2966b7c48de50e4d814c8db4e952c8c988`) and count 585, then rechecks manifest digest, source membership/hash, exact question/reply/provenance, paired field shape and wording, and post-attestation assessment time. Separate USER_ATTESTED rehosting authority remains mandatory. Matching use wording is an audited context constraint, not a license. The XML remains restricted and unlicensed, and original dataset instructions are preserved. Extra metadata restrictions/security, unsupported creators or dates, aliases, stale source evidence, duplicate safeguards and release gates remain unchanged. Both agent and human QA/readback revalidate the evidence.

Before implementation, the positive fixture failed with the existing exact-USER_ATTESTED rejection. Sixteen focused tests then passed, covering the legacy profile plus the new positive case, coherent restriction/security/date/creator mutations, malformed evidence/authority, backdating, rehashed cohort additions/removals/hash rebindings/same-count substitutions, withdrawn collection evidence and stale agent/human readback. A bounded ten-source run yielded seven supported and three held, including the known creator/date residuals. The final pinned-code whole-corpus run and identical resume produced **1,988 supported / 2,212 held / six malformed**, versus **1,406 / 2,794 / six** without this profile. Exactly 582 of the 585 cohort members changed held→supported; no other source status changed. FGDC-1390 retains its ambiguous creator hold, and FGDC-1422/1423 retain exact-day/construction holds. Technical counts remain 4,131 passing / 63 held / 12 not constructed; all 228 exact-copy groups / 456 members remain held. All 4,206 original hashes, 4,200 prepared XML copies and 4,194 complete raw metadata objects were verified unchanged. Both remote-verification and publication-approval totals remain zero. See [validation receipt](contributor_source_validation.json) for the full promoted-ID list, residual reasons, report hashes and final script hashes. The integration owner reported 264 passing full-suite tests, and independent review cleared the canonical pin with 16 focused tests passing.

Reproduce from the repository root, using a new output directory and current timezone-aware timestamp; repeat that timestamp for resume:

```sh
venv/bin/python -m scripts.collection_qa --source-dir FGDC \
  --output-dir /workspace/pices-contributor-policy/reproduction \
  --authority-manifest docs/readiness/2026-10-02/rehosting_authority.json \
  --access-interpretation-manifest docs/readiness/2026-10-02/contact_source_interpretation.json \
  --creator-interpretation-manifest docs/readiness/2026-10-02/exxon_citation_interpretation.json \
  --dataset-access-interpretation-manifest docs/readiness/2026-10-02/registration_access_interpretation.json \
  --contributor-access-interpretation-manifest docs/readiness/2026-10-02/contributor_source_interpretation.json \
  --reviewed-at 2026-10-02T23:48:30Z
```

No provider calls, credential handling or original XML edits are required. Source support is preparation evidence, not publication approval.
