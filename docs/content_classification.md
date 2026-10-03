# Searchable deposited-content classification

The project keyword `pices-metadata-only` identifies records whose reviewed deposited content is descriptive metadata rather than the underlying research data. A meaningful downloadable FGDC XML artifact can still be metadata-only. File count, extension, a dataset link, or restricted file access alone cannot establish classification. External data availability remains separate.

The user approved this keyword/filter approach. No live records were edited or uploaded. The deposited-object, rights and date policy still needs PICES agreement; the current fileless uploader is not thereby made compatible with Zenodo's file requirement.

## Internal contract

`scripts/content_classification.py` is the canonical classifier/exporter. A source-hashed curator decision passed through the existing `batch_transform.py --decisions FILE` contains an optional `content_classification` object:

```json
{
  "inventory_complete": true,
  "reviewer": "Reviewer identity",
  "reviewed_at": "Review timestamp",
  "rationale": "Evidence supporting deposited object scope",
  "files": [
    {
      "name": "FGDC-EXAMPLE.xml",
      "role": "descriptive_metadata",
      "evidence": "Reviewed as descriptive FGDC metadata, not underlying observations"
    }
  ],
  "external_availability": {
    "status": "unknown",
    "url": "https://example.org/described-object"
  }
}
```

The enclosing decision still requires the exact original `source_sha256`, reviewer, rationale and reviewed_at. Do not treat this example as approval for any real source. File roles are descriptive_metadata, research_data, other or unknown. Classification requires a complete inventory, review provenance, named files and role evidence. Data roles also require `data_coverage` of complete or partial for the described scope. Missing evidence/coverage is unknown; an explicit claimed status inconsistent with the evidence is rejected.

| Internal content_status | Reviewed deposited content | Exact exported keyword |
| --- | --- | --- |
| metadata_only | Only descriptive metadata files | pices-metadata-only |
| data_included | Research data for complete described scope, with or without metadata files | pices-data-included |
| mixed | Research data for only part of described scope | pices-content-mixed |
| unknown | Incomplete/unreviewed/ambiguous evidence | pices-content-unknown |

Classification and file-role evidence stay in the transformed result's top-level `content_classification` and canonical DTO `extra_metadata`; they are not invented Zenodo API fields. Only one project tag and a short human-readable description note are exported in `metadata.keywords`/`metadata.description`. Existing scientific keywords remain. Regeneration replaces stale project tags and description notes idempotently. Resource type, DOI and rights are independent and unchanged by this exporter.

A declaration describes an intended, reviewed deposit. It does not prove that the named files were uploaded or that their hashes match live files. Before publication, reconcile planned roles with the actual live inventory under the agreed artifact policy and reapprove changed metadata. Adding a tag changes the payload hash and invalidates old approval. Do not use this feature to bypass the existing publication/duplicate gates.

## Search queries

Zenodo supports [custom keywords](https://help.zenodo.org/docs/deposit/describe-records/keywords-and-subjects/), exposes the legacy [keywords metadata representation](https://developers.zenodo.org/#representation), and supports [advanced field and NOT searches](https://zenodo.org/help/search). The parent researcher independently verified the exact advanced keyword field against public searches; this implementation did not upload records or repeat that live test.

Include metadata-only records:

```text
metadata.subjects.subject.keyword:"pices-metadata-only"
```

Exclude that tag, combined with the desired collection/query:

```text
NOT metadata.subjects.subject.keyword:"pices-metadata-only"
```

Exclusion also leaves unknown, mixed and unclassified records; it is **not proof that the remaining records contain data**. To specifically select reviewed data-bearing records, include `pices-data-included`; add `pices-content-mixed` only when partial coverage is wanted. A metadata-only tag describes deposited content, not whether an external dataset can be obtained.

## Offline validation and readiness evidence

Regression tests cover reviewed XML-only roles, data plus metadata, partial data scope, external links, ambiguous files, missing evidence, stale status replacement, repeated export, scientific-tag preservation, API-schema compatibility, original-source fidelity and internal-only evidence retention. The suite has 73 tests. It does not establish live search indexing or file/API compatibility.

The [curator matrix](readiness/2026-10-01/curator_decision_matrix.md), [readiness plan](readiness/2026-10-01/production_readiness_plan.md), cohort summary and public source associations preserve the bounded production preparation. Counts refer to the identified audited revision, not completed production work.
