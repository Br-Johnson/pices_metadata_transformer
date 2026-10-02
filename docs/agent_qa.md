# Delegated record QA and separate publication release

Brett authorizes agents to perform record-level QA; he is not expected to inspect 4,000 records individually. This supersedes the earlier human-per-record policy. Production release remains separately authorized. Neither a QA run, independent code review nor this PR authorizes bulk publication.

## Every-record evidence and holds

`python -m scripts.agent_qa --help` assesses each successful environment-ledger record using original XML, prepared metadata, reviewed artifact contract and saved read-only remote/duplicate evidence. Schema2 records honest reviewer type, reviewer identity, run ID, revision, time, checks and evidence. Approval is tied to source bytes, metadata, file/role/policy hashes and the exact deposition ID. Current evidence is reassessed at publication; changed input or saved response invalidates approval.

The currently supported automatic profile requires strict parseable original XML, preserved title/abstract, unambiguous primary institution or surname/given-name creators, exact calendar dates, explicit supported rights, reviewed metadata-only file inventory where applicable, and no outgoing relations needing separate adjudication. XML-specific rights come from explicit metadata-use constraints with matching scope/XPath/policy; a license on the described research object does not silently relicense the XML. Unknown rights remain held even if restricted access passes metadata validation. Contradictory source access restrictions, unsupported date precision/creator mixtures, malformed or stale remote/file inventories, incomplete duplicate evidence and unresolved identities remain explicit holds.

Duplicate proof is scoped evidence, not a claim of worldwide absence. The automatic profile accepts fresh complete saved responses from supported repository formats for a canonical positive title search; exclusion queries, HTML shells, missing pages and caller-renewed old evidence cannot prove no match. DOI/source-ID matching, alternate versions, derived subsets, exact source aliases, real candidates and unavailable services require further evidence-based agent adjudication outside this narrow automatic profile. Never delete or merge automatically.

These limits deliberately avoid blanket approval. A broader supported profile can be added only with evidence and regression coverage. No actual production record population has been approved. The original 20-case audit and source-field census are bounded evidence, not a full live-record QA result.

## Independent review and spot checks

Schema2 program review has two explicit components: independent process review and risk-stratified source spot checks. Both bind the exact approved-population digest and record assessor identity, time, scope and evidence. The independent assessor must differ from the record assessor. Spot checks identify actual sampled record IDs and risk strata; they never imply every record was independently checked. Suggested strata include date precision/semantics, institutional versus personal creators, rights/access, original XML artifacts, duplicate aliases/versions and corrected historical records. Changed population invalidates the review binding.

The checks are separate from record assessment so supported rows can be assessed before program review is complete. Publication requires the completed program review. Review of fixture/code behavior alone must not be recorded as a source spot check on real approved records.

## Release is separate

`python -m scripts.release_manifest --help` prepares an **unapproved** release for exact QA-approved source IDs. It binds the complete QA manifest hash and selected draft/source/metadata/file identities. A human release authority explicitly supplies release approval, authority identity, time and rationale for that bounded selection. This is one release decision, not human QA of every record.

The production publisher requires both `--qa-manifest` and `--release-manifest`. It selects released QA-approved rows before `--limit`, then validates every selected row, independent program evidence, release binding and live metadata/files before the publish operation. Saved snapshot state can differ after publication; actual metadata/file identity must still agree. Final readback is checked before verified success, and retry uses remote state rather than another publish POST.

Historical schema1 manifests remain human record-QA evidence, with prior exact source/payload/file bindings. They cannot be relabeled as agent approval without schema2 evidence and still need separate release authority under the current policy. Schema2 is additive; no old approvals, ledgers or source files are silently migrated.

## Current operational checkpoint

Three authentic source-backed technical drafts and a clearly labeled synthetic XML fixture are prepared offline, with no assigned license or publication approval. See the [canary packet](readiness/2026-10-02/candidate_decisions.md). Authenticated sandbox access and fresh environment-scoped inventory are unavailable here, so no draft creation has occurred. Nonpublishing transport tests do not require final production QA; actual-source publication does.
