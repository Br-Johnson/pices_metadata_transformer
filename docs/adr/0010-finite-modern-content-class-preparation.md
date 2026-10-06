# ADR 0010: Finite modern preparation for exact XML content classes

Status: accepted for offline implementation; provider execution remains unimplemented.

## Context

The approved pair representation retains two original source identities and filenames
under one local content-hash target. The first coherent modern cohort comprises 203
Exxon pairs (406 original files). Their existing reviewed citation credits and modern
creator projection are already bound; choosing one source as primary would lose the
approved identity and inventory contract. Modern singleton execution, QA and release
intentionally reject every paired identity, including renamed copies of paired bytes.

## Decision

Use `scripts.modern_content_class.prepare(record_target_id, paths, reviewed_at=...)`
and a distinct `PreparedClass`. Rebuild through the existing class assembler at an
explicit fixed assessment time. Require both member assessments supported and bind
both payloads, policies, original files and v1 artifacts to the complete v2 class
contract. Preserve the complete assembled class metadata in the wire preservation
block, including its two-filename notes. Keep the original metadata, XML, source
profiles, alias holds and existing singleton wire payloads unchanged.

A pinned finite 203 manifest is independently checked against the pinned pair
representation, Exxon821 profile, source plan and prior creator projection. The
projection manifest supplies only the reviewed creator representation; its singleton
membership is not reused as authority for pairs. Missing or changed evidence holds
the entire class. `validate_prepared` freshly rebuilds and compares every field;
self-rehashed edits are insufficient.

`PreparedClass` exposes both originals and has neither the singleton `source_id` nor
`xml` attributes. No transport, grant, provider command or publication entry point is
added. Canonical source/provider identities remain null, reconciliation pending,
execution unimplemented, and upload/remote-verification/publication flags false.
Existing singleton and release guards remain effective. This is a separate API and
evidence schema, not a migration of saved singleton or class execution journals.

Adding the module changes the all-script runtime binding. The explicit PR42 bridge
therefore recognizes that runtime only for the six singleton policies existing in
PR42, with exact nonruntime evidence and immutable original attempt history. It
neither admits this class policy nor migrates started captures/publications.

## Consequences and verification

Coverage counts must distinguish wire-prepared targets from executable singleton
coverage. Full guarded measurement prepares all 203 pairs twice, compares all 3,262
existing singleton payloads at their retained original paths, and verifies all 4,206
original hashes and retained evidence. Finite mutation tests cover member changes,
withdrawn authority, forged manifests/targets, metadata/rights preservation and
closed singleton/release paths. Applicable current-head CI and independent review
precede merge.

Class-aware durable multi-file execution, owner inventory reconciliation, QA,
release, destination permission and exact remote readback remain separate required
contracts. Preparation grants no provider action and establishes no duplicate absence.
