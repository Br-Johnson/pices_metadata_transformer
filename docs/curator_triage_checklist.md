# Curator Triage Checklist

Use this checklist after each LLM-assisted review cycle to ensure metadata
corrections flow deterministically back into the pipeline.

1. **Map anomalies to transformer rules**
   - [ ] Record missing creators/contributors in `docs/tech-debt.md` with FGDC IDs.
   - [ ] Update `scripts/fgdc_to_zenodo.py` or supporting mappers to address
         systemic issues (e.g., placeholder abstracts, organisation parsing).
2. **Update bibliographic blacklists/overrides**
   - [ ] Add false-positive identifiers to a local suppression list within the
         bibliographic linkage workflow.
   - [ ] Capture rationale in the curator observations file.
3. **Regenerate DTOs and JSON-LD**
   - [ ] Re-run `scripts/batch_transform.py` with `--limit 10` to confirm fixes
         before scaling up.
   - [ ] Re-run `scripts/generate_jsonld_catalogue.py` and confirm
         `output/reports/odc/harvest_status.json` reports `status: pass`.
4. **Archive artefacts**
   - [ ] Store the latest review observation file alongside the bibliographic
         decision log in `output/reports/review/`.
   - [ ] Update `docs/todo_list.md` with outcomes and outstanding follow-ups.

