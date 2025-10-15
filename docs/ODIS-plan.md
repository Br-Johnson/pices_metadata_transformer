# ODIS Metadata Publishing Options

The following alternatives outline different ways to expose PICES Zenodo records so they can be harvested and associated with the Ocean Data and Information System (ODIS) and the Ocean InfoHub (OIH).

## Plan A — Static HTML Landing Pages with Embedded JSON-LD
1. **Harvest Zenodo metadata:** Use the Zenodo REST API to pull the latest JSON for targeted records, capturing identifiers for PICES materials and any ODIS-relevant facets (geography, organizations, themes).
2. **Transform to schema.org JSON-LD:** Map Zenodo fields to schema.org/Dataset (and related types) in JSON-LD, preserving authoritative identifiers and linking to the North Pacific Marine Science Organization (PICES) as `creator`/`publisher` where appropriate.【F:docs/ODIS-Book.md†L367-L401】
3. **Render lightweight HTML landing pages:** For each record, generate a static HTML page that embeds the JSON-LD snippet in a `<script type="application/ld+json">` block inside the page head so Gleaner and similar harvesters can extract the markup.【F:docs/ODIS-Book.md†L380-L419】
4. **Publish with sitemap support:** Host the pages on a stable domain (e.g., GitHub Pages, institutional web server) and expose `robots.txt` plus `sitemap.xml` that enumerate each landing page with `lastmod` metadata for crawler discovery.【F:docs/ODIS-Book.md†L389-L393】【F:docs/ODIS-Book.md†L54-L113】
5. **Enable automated refresh:** Schedule the pipeline (GitHub Actions, cron job) to detect Zenodo changes, regenerate affected pages, and republish the sitemap so ODIS harvesters stay in sync.

**Pros:** Full control over schema markup, can add cross-links to regional/thematic hubs, aligns with ODIS guidance for HTML + structured data. **Cons:** Requires hosting and build automation outside Zenodo.

## Plan B — JSON-LD Record Directory Served via Stable URLs
1. **Generate standalone JSON-LD files:** Transform Zenodo records into schema.org-aligned JSON-LD documents stored as individual files in a version-controlled directory.【F:docs/ODIS-Book.md†L367-L401】
2. **Host the files on a persistent web endpoint:** Publish the directory through GitHub Pages or similar static hosting, optionally fronted by a persistent redirect (e.g., w3id) so ODIS sees durable URLs while PICES retains control.
3. **Expose a sitemap for harvesting:** Produce an XML sitemap that lists each JSON-LD file URL and update the `lastmod` timestamps whenever records change, following the ODIS web architecture guidance.【F:docs/ODIS-Book.md†L389-L393】
4. **Offer content negotiation for JSON-LD:** Configure hosting (or use simple HTTP headers) to advertise `application/ld+json` so tools like Gleaner can request the JSON-LD serialization directly.【F:docs/ODIS-Book.md†L470-L472】
5. **Automate validation and publication:** Use CI to run JSON-LD validation before pushing updates and regenerate the sitemap so the directory stays aligned with Zenodo releases.

**Pros:** Lightweight to host, mirrors the reference pattern shared by ODIS nodes, and keeps JSON-LD under direct PICES governance. **Cons:** Requires maintaining a public web endpoint and redirect strategy in addition to Zenodo.

## Plan C — Enhanced Zenodo Landing Pages with Supplemental Discovery Aids
1. **Author JSON-LD payloads per record:** Create schema.org JSON-LD snippets that reference the Zenodo DOI landing page and encode PICES affiliations and thematic details.【F:docs/ODIS-Book.md†L367-L401】
2. **Embed or attach markup within Zenodo:** Where Zenodo allows HTML, inject the JSON-LD snippet into the record description using the `<script type="application/ld+json">` pattern, or upload it as a clearly labelled supplemental file for harvesters to fetch.【F:docs/ODIS-Book.md†L380-L419】
3. **Publish an external sitemap of DOIs:** Maintain a minimal static sitemap (outside Zenodo if necessary) that lists each DOI landing URL so ODIS harvesters know which pages to crawl.【F:docs/ODIS-Book.md†L389-L393】
4. **Coordinate with ODIS on crawling constraints:** Share the sitemap location and confirm that Gleaner or alternate harvesters can fetch the Zenodo pages and detect the embedded JSON-LD; adjust formatting if Zenodo sanitizes tags.
5. **Monitor validation and fallbacks:** Periodically verify that the embedded JSON-LD remains accessible and valid; if Zenodo stripping occurs, fall back to attaching JSON-LD files plus pointing to them from the sitemap.

**Pros:** Keeps the DOI landing page as the authoritative HTML surface, minimizes external infrastructure. **Cons:** Dependent on Zenodo’s support for embedded script tags or discoverable attachments; still needs an auxiliary sitemap for reliable harvesting.

---

**Recommendation for review:** Start with Plan A or B for quickest alignment with the ODIS publishing guidance, then evaluate whether Plan C is warranted for long-term federation or advanced thematic linking.

## Selected Approach — Plan B Execution Blueprint

- **Objective:** Deliver a machine-actionable JSON-LD catalogue for all Zenodo deposits so ODIS/OIH harvesters have durable URIs, consistent schema.org coverage, and fresh metadata within 24 hours of a record change.
- **Success signals:** 100% of Zenodo sandbox records appear in the published sitemap, JSON-LD validates against schema.org Dataset, and every enriched record preserves bibliographic cross-links surfaced via the duplicate detection workflow.【F:docs/bibliographic_linkage_plan.md†L74-L84】
- **Governance:** Host the JSON-LD directory in the public repository (e.g., `docs/odc/records/`), publish via GitHub Pages, and optionally register a `w3id.org` redirect for long-term URL stability.

## Phase Sequencing

1. **Stabilise base pipeline (Week 0):**
   - Re-run the post-merge regression suite (`batch_transform`, `pre_upload_duplicate_check`, `verify_uploads`) to confirm the metadata publishing adjustments in `br-johnson/adjust-zenodo-metadata-publishing-process` did not introduce regressions.【F:docs/todo_list.md†L32-L85】
   - Capture diffs in `output/validation_report.json` and `logs/errors.json`; flag anomalies in `docs/tech-debt.md` if new edge cases surface.
2. **Schema & generator hardening (Week 1):**
   - Lock the JSON-LD field mapping (FGDC/Zenodo → schema.org Dataset) and document invariants directly inside the generator module header.
   - Produce 10-sample payloads (covering datasets, reports, multi-file deposits) and store under `contracts/examples/odc/` for regression tests.
3. **Hosting + sitemap automation (Week 1-2):**
   - Implement GitHub Pages publishing job that pushes `docs/odc/records/<zenodo_id>.jsonld` plus `docs/odc/sitemap.xml`.
   - Add cache-busting by writing `lastmod` from the latest Zenodo `metadata.modified` timestamp, ensuring harvesters track deltas.
4. **Bibliographic linkage integration (Week 2):**
   - Invoke the duplicate detection adapters before JSON-LD emission so confirmed `related_identifiers` and provenance notes flow into both Zenodo payloads and the external catalogue.【F:docs/bibliographic_linkage_plan.md†L32-L72】
   - Persist curator decisions alongside generated JSON-LD for traceability (`output/reports/duplicates/`).
5. **Validation & monitoring (Week 2-3):**
   - Add CI checks (JSON Schema + schema.org ShEx validation + link checker) to guard against malformed records.
   - Emit a nightly summary (`output/reports/odc/harvest_status.json`) tracking record counts, validation failures, and bibliographic linkage coverage.

## Integration Touchpoints

- **Transformation pipeline:** Extend the existing Zenodo JSON builder to emit a canonical record DTO consumed by both the uploader and the Plan B generator, keeping one source of truth for schema mappings.
- **Bibliographic workflow:** Feed confirmed matches (DataCite, Crossref, etc.) into the DTO before serialization so the JSON-LD mirrors the `related_identifiers` shipped to Zenodo and captures `isAlternativeIdentifierOf` relationships for harvesters.【F:docs/bibliographic_linkage_plan.md†L52-L84】
- **Testing harness:** Reuse the orchestrator dry-run (`scripts/orchestrate_pipeline.py --limit 10 --sandbox`) as a smoke test by appending a JSON-LD generation step and diffing against stored fixtures.
- **Documentation:** Update `docs/todo_list.md` and `docs/tech-debt.md` whenever new hosting constraints, API limitations, or outstanding linkage anomalies are discovered.

## Testing & Verification Post-Merge

- **Regression sweep:** Execute limited runs of `scripts/batch_transform.py`, `scripts/pre_upload_duplicate_check.py`, `scripts/verify_uploads.py`, and `scripts/metrics_analysis.py` against the sandbox environment to verify the merged branch preserved metadata completeness.
- **Plan B coverage tests:** Add unit tests for the JSON-LD generator (field presence, vocabulary normalization) and CLI-driven contract tests that compare emitted JSON-LD against expected fixtures.
- **Harvest simulation:** Run Gleaner or a local RDF crawler against the GitHub Pages staging URL to confirm sitemap discovery and JSON-LD parsing, capturing logs for reproducibility.
- **Monitoring drills:** Validate that the CI pipeline blocks publishing if JSON-LD validation or bibliographic linkage checks fail, ensuring issues surface before harvesters encounter them.

## Risks & Mitigations

- **Hosting reliability:** GitHub Pages deploy delays could create stale records—mitigate with scheduled CI retries and timestamped `sitemap.xml` entries.
- **Schema drift:** Zenodo field changes or new FGDC edge cases may break the JSON-LD mapping; mitigate with contract fixtures, type checking, and explicit TODO entries when new patterns appear.
- **Linkage false positives:** Bibliographic adapters might surface erroneous matches; mitigate with curator thresholds, decision audit trails, and the ability to blacklist identifiers within the generator.
- **Operational load:** Additional CI stages increase runtime; scope Plan B jobs to incremental diffs (e.g., only regenerate JSON-LD for records updated in the last batch) to keep pipelines under 10 minutes.

## Comprehensive QC Workflow (Bibliographic + JSON-LD + LLM Review)

1. **Baseline Regression Gate**
   - Triggered after each mapper or transformation change and before Plan B artefacts are regenerated.
   - Commands: `batch_transform`, `pre_upload_duplicate_check`, `verify_uploads`, `metrics_analysis` with `--limit 10` for smoke testing and full runs nightly.
   - Output diffs feed `docs/todo_list.md` and `docs/tech-debt.md` when anomalies arise.
2. **Bibliographic Linkage Enrichment**
   - Run DataCite and Crossref adapters over the entire record set (default) with optional `--limit` for spot checks; persist candidate matches to `output/reports/duplicates/`.
   - Curator decisions update the canonical record DTO prior to both Zenodo uploads and JSON-LD generation, ensuring `related_identifiers` stay in sync.【F:docs/bibliographic_linkage_plan.md†L32-L84】
3. **JSON-LD Catalogue Generation**
   - Consume the enriched DTO to emit `docs/odc/records/<zenodo_id>.jsonld` and regenerate `docs/odc/sitemap.xml`.
   - CI validates schema, link integrity, and diff coverage; failures block publishing and raise TODO items.
4. **LLM-Assisted Human QA**
   - `scripts/extract_review_set.py` assembles paired FGDC XML summaries and DTO excerpts, prioritising creator/contributor anomalies detected during transformation metrics.
   - Review CLI streams each bundle through the structured prompt, capturing observations in `output/reports/review/creator_anomalies_<timestamp>.json`; runs support both targeted (`--limit 25`) and full-corpus modes.
   - Curator reviews findings, applies deterministic mapper fixes, and re-runs affected pipeline stages. Because the DTO is the single source of truth, corrected records automatically propagate to Zenodo, JSON-LD, and bibliographic outputs without re-running the LLM audit unless new warnings surface.
5. **Final Verification & Publishing**
   - Execute the orchestrator with the JSON-LD and review stages enabled; confirm `output/reports/odc/harvest_status.json` and review logs are green before scheduling production uploads.
   - Archive QC artefacts alongside upload audits for traceability and future spot checks.

This sequencing keeps automated checks fast, reserves LLM involvement for human-quality assessments, and prevents redundant manual reviews when upstream metadata or linkage logic shifts.
