# Evidence-backed hold reduction

Update: Brett subsequently attested authority to rehost this lost GeoNetwork collection. The archival-authority question below is closed by that user attestation, without a new license or independently verified agreement. See [the source-bound authority profile and 687 supported preparation results](rehosting_attestation.md). The table below remains the pre-attestation baseline.

The narrow automatic license profile's zero approvals does not mean no rights exist. Hold counts overlap and checks short-circuit: removing an early presentation hold may expose later creator/access/rights holds. Publication and remote verification remain zero.

## Completed reversible routine corrections

The classifier now uses the exact source title without an added suffix when the suffix alone would exceed 250 characters. It never truncates a source title. This resolves 42 technical title holds; 42 source titles themselves exceed the limit and remain held. Original XML, full titles, source hashes, artifact contracts and object classification remain preserved.

It also displays the exact source abstract, or source title if absent, using HTML escaping. The assessment decodes HTML entities after removing actual markup. Scientific comparisons such as `x < 3` and literal source placeholder strings survive display preparation instead of being mistaken for HTML or substituted prose. All 74 title/description-fidelity holds resolve in this collection; no release approval follows.

| Measure | Before | After |
| --- | ---: | ---: |
| Technical payload passes | 4,089 | 4,131 |
| Technical payload holds | 105 | 63 |
| Not constructed | 12 | 12 |
| Title length holds | 84 | 42 |
| Title/description fidelity holds | 74 | 0 |
| Parseable records held | 4,200 | 4,200 |
| Strict parse failures | 6 | 6 |
| Publication approvals / remote verification | 0 / 0 | 0 / 0 |

## Shared provenance and rights scope

[PICES Technical Report 1 (2007), exporter appendix](https://www.pmel.noaa.gov/foci/publications/2007/megr0624.pdf#page=155) writes the same access/use constraint variables into dataset and metadata sections and supplies a fixed metadata contact. Independently checked: 4,073 of 4,200 parseable files contain both compared field pairs with exactly identical parsed text; the same 4,073 have the matching contact. This is a strong template signature, not proof that the exact published exporter/version generated every source. The remaining 127 parseable files require separate provenance assessment.

The [FGDC standard, sections 7 and 8](https://www.fgdc.gov/standards/projects/metadata/base-metadata/v2_0698.pdf) distinguishes dataset originators, metadata contacts and metadata-use constraints. A contact is not necessarily an author. A copied constraint cannot independently prove that a permission applies specifically to the XML artifact. `metd` means metadata creation or last update, not necessarily first publication. Preserve these distinctions in source-bound decisions.

[PICES' 2024 data policy](https://meetings.pices.int/about/PICES-Policy) encourages open metadata sharing, recognizes provider ownership/restrictions and permits reformatting while protecting original records. Its public-availability statement covers PICES-produced outputs, which cannot automatically be extended to every third-party catalog entry. It does not specify one blanket Creative Commons license for these XML files. [The archived catalogue references page](https://sites.google.com/view/pices-metadata/references) connects the catalogue to the North Pacific Ecosystem Metadatabase and historical portal; its website copyright notice is not an explicit archived-XML license. The repository RFQ establishes migration intent, not a particular reuse license.

## Ranked next decisions

1. **Shared archival authority and attribution:** establish the applicable PICES/NOAA archive provenance, permission and attribution policy for the 4,073-record template group. A documented group decision can bind an enumerated source-hash manifest and explicit object/rights/creator roles; retain exceptional restrictions. Do not impose dataset licenses on XML or map “None” to CC0. A permission decision need not be expressed as a CC license, but its exact terms and Zenodo representation need review.
2. **Creator roles:** preserve dataset citation origins and metadata contacts separately. 1,329 current first-failure creator ambiguity holds and 21 empty names cannot be resolved by guessing person splits or promoting contacts. All 4,200 parseable files contain metadata contacts, but that fact alone does not establish XML authorship. A shared creator/curator policy with proven authority could address a large population; an address in an origin remains an exception. Creator holds were 1,322 before earlier fidelity checks were removed; the increase reflects newly reached checks.
3. **Remaining presentation issues:** 42 genuinely overlong source titles can use reviewed derived display titles with the full original preserved and an exact source binding. Implement only after agreeing the shortening rule; do not silently truncate originals. Remaining technical failures include 21 empty creator names.
4. **Dates:** 4,194 syntactically exact-day metadata dates can be preserved as creation/last-update evidence. Six unsupported values remain: three missing and three `2080207`; do not infer `20080207`. Dataset dates such as `122003` or ranges remain descriptive evidence, not inferred artifact publication dates.
5. **Identity and recovery exceptions:** preserve 228 exact-copy groups and six malformed originals. Resolve aliases with explicit source-to-existing-record decisions; recover parsing into derived files only with documented byte changes and strict validation. Existing older production imports are to be corrected/reused, not deleted or recreated.

Access holds include 3,172 records with terms outside the automatic open-access vocabulary; they require scope adjudication, particularly where dataset terms were copied by the exporter. This is an evidence classification, not a claim every such XML must be restricted. Authentication and remote duplicate/readback checks remain separate unexecuted gates; no production changes or publication are authorized by this plan.
