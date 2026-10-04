# Run02 evidence-layout repair — 2026-10-04

This supersedes the ebd42d preservation-root recipe after its local precondition
failure: parent reports zero PUT, zero GET, historical197 reads and353 unchanged
evidence files. The old branch, grants, failed receipts and origins remain intact.
Only the sole executor stages/preflights actual private evidence. Root and reviewer
have made no provider request and have read no real credential/private evidence.

## Inputs and offline dispatch order

1. Use this PR's exact frozen code and the updated
   [controlled repair instructions](run02_subjects_repair_handoff.md). Retain literal
   `/workspace`0755 as historical ancestry; never change its mode or old origin.
   Select actual evidence subtrees/leaves, not the entire workspace. A complete
   manifest is mandatory; count alone never supplies historical completeness.
2. Seal a0600 `schema_version:1,files_sha256` manifest containing every previously
   retained353 historical evidence file with canonical absolute paths and the
   expected SHA256 values from the previous sealed inventory. Convert that existing
   inventory without adopting current bytes as a new baseline or changing old files. Include original/failed stages and the complete GET197 diagnostic
   evidence. Feed it through `--preserved-manifest`, alongside nonoverlapping whole
   `--preserved-root` evidence trees. Loose leaves can be manifest-selected.
3. Stage into a fresh0700 destination with the same namespace basename, outside
   every evidence root/leaf. Never erase/reuse any earlier partially staged state.
   The new copied manifest is a required static input. Older stage bindings lack
   it and intentionally cannot execute this input revision; no migration/reset of
   old private stages occurs. All original static/dynamic stage files and the
   latest beforeimage must be included, regardless of the338 sanity floor.
4. Run `python -m scripts.modern_run02_subjects_repair preflight --stage <new-stage>`
   before parent starts a live window. It applies the real Controller's complete
   local checks and prepares the exact494-byte PUT using the ordinary Session.
   It does not load/mint an action grant, write any ledger or send/consume an action.
   Return only closed preflight hashes/counts to parent, keeping paths/bodies private.
5. Only after that successful receipt, parent binds the fresh at-most600-second
   grant to the actual new binding/runtime and inventory hash/count. The source
   manifest itself is inventoried, so a declared353-file set gives354 preserved
   inventory entries in the fixture. Bind the actual count; never force353/338.
6. Execute once under that exact grant. Same sealed draft, one metadata PUT then
   one canonical GET; unchanged identity/ownership/empty-file/DOI-absence, prepared
   body, status/error/privacy and no-redirect/retry rules still apply. No CREATE,
   PID, file operation, publication, delete or production capability is added.

Evidence roots/directories may be0755 without group/other write bits; private
regular files remain0600 (or stricter) with one link. Every ancestor/descendant is
canonical and symlink-free. Trusted sticky/tmp supports existing temporary stages;
other shared writable ancestors reject. Broad-origin public siblings are not read.
All declared hashes and whole-tree inventories are rechecked before each request
and completion. Manifest completeness of the historical353 is parent/executor
proof; root has verified only the synthetic topology and public code.

## Verification and runtime

The synthetic353-file fixture has a0755workspace, private original stage beneath
it, failed owned continuation outside it, GET196/GET197 evidence, historical leaves
and a public unrelated sibling. It retains the original provenance literally and
passes stage, no-grant read-only preflight, full real Controller and shared Session
prepare/send route with two mocked responses. The adapter/socket/DNS remain blocked.
Old file bytes/modes and workspace mode are unchanged. Sparse manifest selection
also passes; no unrelated sibling is inventoried. Invalid/missing manifest entries,
public leaves, writable directories, symlink ancestors/leaves, hardlinks, overlap
and subtree additions reject. Manifest-only destinations nested within original
or failed stages also reject before any mkdir/copy. Noncanonical destination
spellings containing `..` reject before creation, rather than being normalized. Existing repair tests preserve uncertain/redirect/
credential/error and permanently spent-intent behavior.

[Validation](run02_evidence_layout_validation.json) and
[independent review](run02_evidence_layout_independent_review.json) bind the tested
code. Current runtime pins are recorded in the approved-false
[contract](../../../contracts/examples/run02_subjects_repair.json).

## Parallel source review

The independent [four-source receipt](physical_copy4_independent_source_review.json)
clears physical acquisition scope for740/815/851/879 while preserving literal
Unknown use, historical prices/lead times,851's incomplete regional blueprint and
879's actual index description. It proposes no license/current availability or
promotion. This PR changes no source profile, classifier or source eligibility;
main remains3638 supported/562 held/6 malformed before any later bounded delta.
