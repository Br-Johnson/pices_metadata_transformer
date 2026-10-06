# AGENTS.md — Operational Ruleset for Agentic Coding Assistants

## Global Principles

- Plan before coding. Execute in atomic, reversible increments.
- Explain decisions and continue work within the user's authorized scope. Ask only for missing information or authority needed to proceed.
- Maintain reproducibility, determinism, and traceability.
- Avoid technical debt and unbounded complexity.
- Prefer simplicity, composability, and transparency over cleverness.
- Keep this ruleset current when the user changes repository workflow rules; authorized implementation continues directly on `main` after branch reconciliation; rules and documentation updates may also be committed there.

## Standing Repository Authorization — updated 2026-10-06

Brett explicitly authorized this repository workflow. It supersedes older
instructions requiring separate merge approval, prohibiting rules edits, or
requiring a feature branch or PR as a routine preference, including instructions
retained in historical checkouts, plans and handoffs.

- Reconcile every current relevant branch, PR and interrupted checkpoint. Integrate ready work with its required tests and independent Codex review; distinguish already integrated, genuinely incomplete, obsolete and unrelated work instead of merging blindly.
- Merge existing pull requests without another approval when CI passes and Codex review covers the current head. Resolve material review findings before merging.
- After consolidation, continue authorized implementation directly on `main`. Run appropriate local checks and obtain independent review before publishing changes, then verify the resulting main head and required checks. Do not create another feature branch or PR merely to follow an older workflow preference.
- If a real protected-main or repository prerequisite requires a different integration route, report the exact gate and honor it without bypassing it.
- Commit rules changes and other documentation updates directly to `main` without another approval, with appropriate documentation checks.
- Keep one code integration writer and coordinate with the sole Mac provider executor. Repository changes do not grant provider actions.
- Preserve unfinished branches, frozen historical checkouts, journals and receipts. No branch deletion is authorized by the consolidation request.
- Carry this authorization across tasks; do not ask the user to approve the same workflow again.

The provider executor, bounded action grants, immutable original XML, source
evidence, identity/DOI preservation and production release requirements remain in
force. The spent unknown-create hold and supported-network-recovery requirement
remain unchanged. AquaDocs linkage is deferred until after initial publication;
it is not completed or passed and is not an initial publication blocker.

## Agent Protocol

1. **Plan:** Outline the system shape, data models, endpoints, dependencies, and risks.
2. **Resolve:** Investigate design assumptions and ask only about unresolved decisions that materially affect the work; existing user authorization remains effective.
3. **Code:** Implement minimal, self-contained diffs with meaningful commit messages.
4. **Test:** Run smoke + contract tests; verify invariants and side effects.
5. **Doc:** Update README, `.env.example`, and contracts as needed.
6. **Teach:** Summarize what was learned — theoretical insight, design trade-off, or best practice — in a concise note or comment.
7. **Reflect:** Log design rationale and unresolved questions to `/docs/tech-debt.md`.

## System Integrity

- **Contracts-first:** Freeze endpoint definitions and example payloads before implementation.
- **Schema versioning:** Every schema or model change includes forward/backward migrations.
- **12-Factor Config:** No secrets in code; `.env.example` must remain accurate.
- **Versioning discipline:** Never break a public API without `/v2` and a documented migration path.
- **Definition of Done:** All tests pass; docs and examples updated; no untracked or orphaned files.

## Reliability & Safety

- Validate all inputs and sanitize all outputs.
- Use context-appropriate authentication (CSRF for browsers, JWT/Bearer for services).
- Log structured events or metrics relevant to the project context (e.g., latency, error rates, resource usage, accuracy).
- Never log secrets or PII; enforce least privilege for credentials, databases, and APIs.
- Treat timeouts, retries, and failures as first-class design concerns; include graceful degradation or fallbacks when applicable.

## Tooling

- Enforce type safety and linting before commit (`mypy`, `ruff`, `black`, `ESLint`, `Prettier`, etc.).
- CI must test critical paths, migrations, and contract validations.
- Maintain sample payloads and schemas in `contracts/examples/`.
- Use automated dependency updates (e.g., Dependabot/Renovate) when available.
- Use context7 when you need to get access to the most recent documentation for any given ccoding framework or tech

## Documentation

- Each module begins with a short header: purpose, invariants, and assumptions.
- Major design or architecture changes require an ADR (`/docs/adr/XXXX-title.md`).
- Keep a running `docs/tech-debt.md` ledger with rationale, impact, and remediation notes.
- Update or regenerate reference documentation when interfaces or schemas change.

## Notes for Agents

- Investigate uncertainty using available evidence; ask for clarification when a necessary decision cannot be resolved from that evidence or existing user instructions.
- When confident, act deterministically and document reasoning.
- Prefer small, composable contributions that others (human or agent) can review easily.
- Maintain internal consistency — code, docs, and tests must always reflect the same truth.

# Project Specific Rules

## Core Principles

- **Never modify original FGDC XML files** - they are the source of truth
- **Always validate transformations** before uploading to Zenodo
- **Preserve all metadata** - if uncertain about a field, include it in Zenodo `notes` field rather than exclude it
- **Work in small batches** - test with `--limit 10` before processing large sets
- **Check for duplicates** - verify no duplicate records are uploaded to Zenodo after each batch

## Critical Files (Never Delete)

- `FGDC/` - Original source files (4,206 XML files)
- `secrets.txt` - API tokens (keep secure) and never commit
- `logs/progress.csv` - Cumulative progress tracking
- `output/` - All generated content

## Workflow Guidelines

### Before Making Changes

- **Read existing logs** to understand current issues
- **Test with small samples** using `--limit 10`
- **Review transformation results** in `output/zenodo_json/`
- **Check validation reports** in `output/validation_report.json`
- **Consult the active checklist** in `docs/todo_list.md` and update it before and after each significant action
- **Decide publishing mode** – hold production drafts for record QA, independent review and a separate human release. The reviewed [community-first handoff](docs/readiness/2026-10-06/modern_pices_community_handoff.md) supersedes the legacy `--publish-on-upload` instruction: bind actual PICES identity/permission evidence before the separately granted draft-review and submit-review route. Repository merge authority does not grant provider actions; retain the sole executor, original journals and spent budgets.

## Code Modification Rules

- **Test changes incrementally** - use `--limit 10` to test modifications
- **Preserve existing mappings** - only modify if you have a clear improvement
- **Add new validation rules** when you discover new issues
- **Comment complex transformations** with reasoning
