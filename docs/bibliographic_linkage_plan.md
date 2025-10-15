# Plan for External Bibliographic Duplicate Detection and Linking

This document outlines a proposed approach for identifying and linking PICES FGDC records to
pre-existing bibliographic entries (e.g., DataCite, Crossref, OAI-PMH catalogues) before they
are published to Zenodo. The plan is intentionally high level so that it can be implemented and
delivered iteratively after review.

## Objectives

1. **Prevent global duplicates** by checking authoritative registries for matching titles and
   abstracts before publishing to Zenodo.
2. **Surface existing persistent identifiers (DOIs)** when a match is detected and link the
   Zenodo record to the original resource via the `related_identifiers` block.
3. **Provide transparent review tooling** so curators can confirm or override proposed matches
   prior to publication.

## Discovery Targets

The following systems provide structured metadata that can be queried programmatically:

- **DataCite REST API** – rich JSON metadata with title, description, creators, subjects, and
  DOI assignment status.
- **Crossref REST API** – complementary coverage for journal articles and reports that may not
  appear in DataCite.
- **Global OAI-PMH endpoints** – configurable for institutional or thematic repositories that
  PICES members rely on (e.g., NOAA, Fisheries and Oceans Canada).
- **Zenodo public search** – final guardrail to catch records that might have been uploaded by
  other communities outside the private sandbox.

## Matching Strategy

1. **Normalise candidate metadata**
   - Lowercase titles, remove punctuation, collapse whitespace.
   - Extract the first 500 characters of the abstract/description for fuzzy comparison.
2. **Query external services**
   - Issue keyword searches that combine the normalised title and one or two discriminating
     keywords (e.g., organisation acronym, geographic region).
   - Paginate through small result sets (≤ 50 records) to stay within API rate limits.
3. **Rank potential matches**
   - Apply a weighted score that mixes:
     - Title similarity (Jaro–Winkler or token set ratio).
     - Abstract similarity (cosine similarity on sentence embeddings or TF–IDF vectors).
     - Creator overlap (exact match on family names or ORCID identifiers when present).
   - Flag matches above a configurable threshold (e.g., score ≥ 0.82) for curator review.
4. **Curator confirmation workflow**
   - Produce a review report (CSV/JSON) listing candidate matches with confidence scores,
     source system, DOI (if present), and landing-page URL.
   - Allow curators to accept, reject, or defer each match; accepted matches feed a
     `related_identifiers` payload that references the external DOI using the relationship
     `isAlternativeIdentifierOf`.

## Linking Strategy for Confirmed Matches

When a curator accepts a match:

1. **Record linkage metadata**
   - Capture the external DOI, source system, matched title, and match confidence.
2. **Augment Zenodo metadata**
   - Update the transformed JSON prior to upload to include:
     ```json
     "related_identifiers": [
       {
         "relation": "isAlternativeIdentifierOf",
         "identifier": "https://doi.org/10.xxxx/abc123",
         "resource_type": "dataset"
       }
     ]
     ```
   - Append a note that references the discovered DOI and system for human context.
3. **Persist audit trail**
   - Store matches in `output/reports/duplicates/` alongside the replacement plan so the
     provenance of each linkage decision is preserved for future audits. Record the curator
     decisions inside the canonical DTO audit trail so downstream stages (JSON-LD, upload
     verification) can surface linkage context without re-reading the review artefacts.

## Implementation Milestones

1. **Prototype search adapters** for DataCite and Crossref (shared interface for querying and
   normalising responses).
2. **Add fuzzy matching utilities** (string metrics and embeddings) inside a new
   `scripts/matching/` module.
3. **Build a review CLI** that produces match candidates and ingests curator decisions.
4. **Integrate with transformation pipeline** so accepted matches enrich the Zenodo JSON before
   upload.
5. **Extend automated reports** to summarise how many records were linked to existing DOIs and
   flag any unmatched high-confidence candidates for manual follow-up.

This plan can be executed incrementally, starting with DataCite (highest value, most structured)
and expanding to other registries as required.

## Quality-Control Integration Points

- **Entry Criteria:** Run the bibliographic linkage pass immediately after the baseline regression sweep and before JSON-LD generation so the canonical DTO already contains vetted `related_identifiers`. This prevents duplicate manual review once the LLM audit stage begins.【F:docs/ODIS-plan.md†L42-L58】
- **Review Feedback Loop:** Store curator decisions and rationale alongside the generated review artefacts (`output/reports/review/`). When the LLM QA uncovers creator/organisation anomalies tied to external identifiers, feed those back into the adapter blacklist or matching thresholds before the next full run.
- **Reporting:** Append linkage metrics (match counts, acceptance rate, false positive overrides) to the nightly QC summary consumed by the JSON-LD validation pipeline, ensuring harvest readiness reflects both deduplication and metadata accuracy.
