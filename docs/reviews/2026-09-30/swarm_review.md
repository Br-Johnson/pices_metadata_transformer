# Independent review of PR 8 fixes

Four agents independently reviewed lifecycle/inventory, QA/publication, metadata fidelity, and CLI/external-evidence integration. Reviews used source inspection and offline fixtures/mock clients; no original XML changes, credential reads, or Zenodo/AquaDocs writes occurred. Each reviewer rechecked the fixes and reported no remaining blocker within the assigned scope.

Confirmed findings addressed:

- P1: malformed owned-draft collections and repeated paginated record IDs could falsely establish complete inventories. Collections and positive, unique IDs are now mandatory.
- P1: incomplete draft responses could permit publication or certify metadata-only status. Publication, verification and reconciliation require matching ID, recognized state, metadata object and an explicit files list.
- P1: two source identities could claim one draft, including through a malformed creation response. Shared ownership checks block reconciliation/resume and validate a newly returned ID before PUT; uncertain creation remains unresolved on failure.
- P1: concurrent ledger changes could invalidate approval during publication. Publication now holds the environment ledger lock throughout fresh ledger binding, QA, remote reads, POST and persistence.
- P1: explicit license denials could become grants. Negation requires adjudication; license family/version boundaries reject unsupported prefixes and versions.
- P2: lineage citation dates could become the current work's publication date. Publication date selection is scoped to the primary citation before documented fallbacks.
- P2: DOI suffix collisions could overwrite JSON-LD catalogue records. Filenames derive from the entire DOI.
- P2: malformed nested external responses and field types could crash evidence ingestion or claim completeness without pagination evidence. Invalid input produces unavailable provenance; API completeness requires explicit pagination proof.

Validation: 65 unit tests pass, including the full suite with socket connections prohibited. Static syntax/undefined-name checks, compilation and diff checks pass. Targeted rereviews cover each reported boundary. This is bounded offline validation, not evidence of live repository coverage or production completion. No GitHub CI workflow is currently configured.

Human source QA, historical ledger reconciliation, live API compatibility and unavailable AquaDocs duplicate evidence remain documented operational decisions in the runbook.
