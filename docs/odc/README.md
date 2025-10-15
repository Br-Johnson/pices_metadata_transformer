# Plan B JSON-LD Catalogue

This directory holds the machine-actionable JSON-LD representations of the
Zenodo records that PICES publishes.  The catalogue is generated with
`scripts/generate_jsonld_catalogue.py`, which also produces a sitemap at
`docs/odc/sitemap.xml` for ODIS harvesters.

## Publishing Workflow

1. Run `python scripts/generate_jsonld_catalogue.py` after bibliographic
   enrichment and curator review have been applied to the DTOs.
2. Commit the updated files under `docs/odc/records/` and the sitemap.
3. GitHub Pages serves the directory so harvesters can dereference the
   JSON-LD documents directly.  For stability a `w3id` redirect can point to
   the same base URL used when generating the sitemap (default
   `https://pices-data.github.io/pices-metadata-transformer/odc/records`).
4. The generator emits `output/reports/odc/harvest_status.json`, which is used
   by CI to block merges when JSON-LD validation fails.

## File Naming

Each JSON-LD file is written as `<zenodo_id>.jsonld`.  When the DOI is known,
the suffix of the DOI is used; otherwise the FGDC identifier is retained until
an upload assigns a DOI or deposition identifier.

