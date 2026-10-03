# Reviewed remaining-source handoff

Frozen integration runtime **d611e1ca02d06306b26649661e60ae4b64a37927** on `handoff/remaining-source-cohorts-20261003`, based on PR11 head08f561ebf117ea31c2c5bf824b44830c1e0f1261. Later reproducibility fixes correct guarded test discovery, format the new test/audit helpers and require a frozen baseline. The new test AST is identical; source validator/profile bytes remain unchanged. PR12 integration retains its separately reviewed modern runtime. This began as a normal stacked handoff and now targets main after dependency merges. The initial handoff recorded a merge rejection under the original trusted scope. After Brett’s exact direct instruction Sentinel_4dc5d70d7dac8191a8a5b60dff23ed9b was supplied, the single PR11 retry succeeded at b3d87f204697a1ba77a2c9d6ece00d99c4e1440d; PR12 then merged at8818c195cc9a1f24ef76eac274ecce65a0561d3d. PR13 now targets main; no bypass/new writer was used.

Actual result **3468 supported /732 held /6 malformed**, **234 additional supported sources**:205 source-bound resource acquisition/use interpretations,27 complete display titles and2 creator promotions. Eight creators are repaired; six retain independent access holds.352 guarded offline tests pass, plus five focused independent runtime contracts. Source semantics and complete actual after-images were independently reviewed in disjoint lanes. No generic date/creator/title/rights heuristic or provider behavior changes.

Evidence:

| Artifact | SHA256 |
| --- | --- |
| Full after classification |0ec37de02ea67af81d3b433a65e523c6c05f30220c667324e2fc3b6a367c8708|
|469 access profile|76a5ca8a8cdadbe0c1b0157d559068c98b16e18619a8561ff66a203a5008730a|
|409 creator profile|f58ae360f225e6c6a1b2c717e389c766d67883c3d6fbb598acd19caa13d5ca24|
|35 title profile|db24d027d65b9e4392ede772172b04ada1fca4d14e576df70998d759303fe5c5|
|Independent runtime review|f70def95822161bd0c0f60a6222c5a025d471bd71797b13b51581b1708d46020|
|Independent205 access review|d6b4462ef9a7e03c41908ed89c5c93a64cf38f6996f7ee6ff70c6d6657b56c19|
|Independent actual delta/GET-only clarification|b8863a693f45c8e819636b70f0b5ebd0104163b2d76d29803edfef747448a779|
|Complete root delta with actual creator hashes/protected subset|6ccf6d621e67e371a916165892417b1dbec7ba385007a9ec6c97de1c1acb35cf|

All4206 original XML hashes and4200 source copies match.4194 complete raw metadata objects checked:4159 unchanged,8 only creators/preservation notes and27 only display title/appended preservation notes. Old264/401/8 member/cohort/context objects remain verbatim; all456 alias identities and date6 retain holds. Exact821 attestation is unchanged.110 of the prior148 protected held sources clear through individually bound source context,38 remain held. The established classifier's eight creator preservation notes precede its final generic attribution note; this exact sequence differs from proposal notes order only and has independent full-object approval. Inherited profile descriptions are historical; the contract/current role fields describe additions.

Current payload evidence references rebind409 creator/469 access/35 title members. All3430 same-time payloads without such rebinding remain byte-identical. Raw metadata preservation is distinct from normalized submission notes, which embed active evidence refs. The five existing imports' raw metadata and preserved historical94 comparisons remain unchanged; no new live correction, concurrency baseline, DOI/file change or release is authorized here.

[Residual questions](remaining_source_questions_732.md) bind276 nonalias holds (238 access-only,31 creator-lane,6 date,1 title) and456 alias identities. FGDC10/2664/233 are the only remaining independent gaps inside the821 answer. More source review may resolve some access residuals; this handoff does not label every residual irreducible. No invented day, contact-as-author, new license or canonical alias selection.

Reproduce offline from this checkout with installed project requirements:

```bash
PYTHONDONTWRITEBYTECODE=1 python docs/readiness/2026-10-03/guarded_remaining_source_qa.py test
ruff check --isolated --select E4,E7,E9,F,I,B scripts/citation_creator_interpretation.py scripts/dataset_access_interpretation.py scripts/source_title_interpretation.py tests/test_remaining_source_cohorts.py docs/readiness/2026-10-03/guarded_remaining_source_qa.py docs/readiness/2026-10-03/audit_remaining_source_cohorts.py
PYTHONDONTWRITEBYTECODE=1 python docs/readiness/2026-10-03/guarded_remaining_source_qa.py classify --output /tmp/pices-remaining-before --reviewed-at 2026-10-03T21:52:00Z --old-profiles
PYTHONDONTWRITEBYTECODE=1 python docs/readiness/2026-10-03/guarded_remaining_source_qa.py classify --output /tmp/pices-remaining-after --reviewed-at 2026-10-03T21:52:00Z
PYTHONDONTWRITEBYTECODE=1 python docs/readiness/2026-10-03/audit_remaining_source_cohorts.py --before /tmp/pices-remaining-before --after /tmp/pices-remaining-after --frozen-baseline /tmp/pices-frozen821-output --output /tmp/pices-remaining-delta.json
```

Use fresh local output directories. First reconstruct the frozen baseline with the commands below, or use the already-saved `/workspace/pices-source-scope821-qa/after` directory after verifying its pinned report hash. The audit requires `--frozen-baseline`; it verifies the pinned759b7c9 report and complete raw before objects. Root's same-time corpus lives in `/workspace/pices-remaining-cohorts-qa/{before,after}`. Both reproducibility helpers pass Ruff; the classifier helper's ten-source fixture returns7 supported/3held and the audit reproduces the complete cc6c05af delta. [Validation](remaining_source_cohorts_validation.json) binds test/log/file hashes and limitations. Provider calls and credential/private-stage reads are unnecessary.

Parent's separate provider executor may now follow the [exact GET-only reconciliation dispatch](modern_readonly_reconciliation_dispatch.md): fixed owned modern inventory route plus canonical draft readback, maximum240 additional GET intents/200pages/30minutes,193historicalreads preserved/cumulative433,20seconds/request,32MiB inventory/64KiB details, no redirects/retries/link following. The modern create intent remains held with dispatch/cause unknown. Candidate evidence does not adopt/reset/replay/write. No root provider requests or stage changes occurred.

PR11: https://github.com/Br-Johnson/pices_metadata_transformer/pull/11, final head08f561e, runtime503f72b,347 guarded tests plus seven independent contracts; exact821 and five-import preparation. PR12: https://github.com/Br-Johnson/pices_metadata_transformer/pull/12, final headdf2ee5b, runtimea43f4a1,349 guarded tests plus nine final independent diagnostic contracts; automatic pre-intent-attribution finding resolved. Both are merged under the supplied direct grant. The combined candidate’s documented suite is verified in the reproducibility correction receipt; exact merged main verification is recorded separately. [Merge gate receipt](pr11_pr12_merge_gate_receipt.json) retains final-head/check evidence and the actual rejection.

## Required frozen821 baseline reconstruction

Before the audit command above, reproduce the pinned759b7c9 report at its original code/timestamp. The current old-profile run intentionally uses the newer source runtime and21:52 timestamp; it is a same-time comparison baseline and cannot replace this frozen20:30 checkpoint. From the current checkout:

```bash
git worktree add --detach /tmp/pices-frozen821-source 08f561ebf117ea31c2c5bf824b44830c1e0f1261
(cd /tmp/pices-frozen821-source && PYTHONDONTWRITEBYTECODE=1 python docs/readiness/2026-10-03/guarded_offline_classify.py \
  --source-dir FGDC --output-dir /tmp/pices-frozen821-output --reviewed-at 2026-10-03T20:30:00Z \
  --authority-manifest docs/readiness/2026-10-02/rehosting_authority.json \
  --access-interpretation-manifest docs/readiness/2026-10-02/contact_source_interpretation.json \
  --contributor-access-interpretation-manifest docs/readiness/2026-10-02/contributor_source_interpretation.json \
  --creator-interpretation-manifest docs/readiness/2026-10-02/exxon_citation_interpretation.json \
  --dataset-access-interpretation-manifest docs/readiness/2026-10-03/finite_source_resource_access_264.json \
  --collective-creator-interpretation-manifest docs/readiness/2026-10-03/dfo_staff_citation_interpretation.json \
  --institution-creator-interpretation-manifest docs/readiness/2026-10-03/source_citation_credits_401.json \
  --source-link-interpretation-manifest docs/readiness/2026-10-03/historical_dataset_linkage_21.json \
  --source-title-interpretation-manifest docs/readiness/2026-10-03/source_display_titles_8.json \
  --source-scope-attestation-manifest docs/readiness/2026-10-03/source_scope_attestation_821.json)
python -c "import hashlib; from pathlib import Path; assert hashlib.sha256(Path('/tmp/pices-frozen821-output/classification.json').read_bytes()).hexdigest() == '759b7c924dc1452be1850635d4bee41230007883f7b94a4691160b067fa127dc'"
```

The historical early receipts record352 source-branch tests and original file hashes. The reproducibility correction receipt binds current helper/test bytes, explicit isolated lint selection (including E701/E702), failure-first discovery and corrected combined-suite evidence. No receipt is rewritten to claim earlier tests covered these later corrections.
