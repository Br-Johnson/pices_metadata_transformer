# AGENTS.md — Operational Ruleset for Agentic Coding Assistants

## Global Principles

- Plan before coding. Execute in atomic, reversible increments.
- Explain reasoning and request confirmation before implementation.
- Maintain reproducibility, determinism, and traceability.
- Avoid technical debt and unbounded complexity.
- Prefer simplicity, composability, and transparency over cleverness.
- Never edit this AGENTS.md file yourself

## Agent Protocol

1. **Plan:** Outline the system shape, data models, endpoints, dependencies, and risks.
2. **Ask:** Confirm design assumptions or key uncertainties before writing code.
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

- When uncertain, ask for clarification rather than guessing.
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
- **Decide publishing mode** – production uploads should pass `--publish-on-upload` to `scripts/batch_upload.py` so Zenodo drafts are auto-submitted to the PICES community. Use `scripts/publish_records.py` only for remediation or backfill.

## Code Modification Rules

- **Test changes incrementally** - use `--limit 10` to test modifications
- **Preserve existing mappings** - only modify if you have a clear improvement
- **Add new validation rules** when you discover new issues
- **Comment complex transformations** with reasoning
