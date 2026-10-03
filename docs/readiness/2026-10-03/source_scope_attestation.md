# Exact 821-source scope attestation

Brett answered the three frozen questions on 2026-10-03 at20:20UTC:
“they reply to the underlying data. all these metadata records were public before”.
The evidence reference is `Sentinel_e28f30cd7f308191b3ea2f19487dd34a`, replying to
`Sentinel_d7aa47e9454c81918b46da87263b4cae`. This is **USER_ATTESTED** scope
clarification, with separate existing XML rehosting authority; it grants no new
license, underlying-data rights, provider action or publication release.

The [original questions](remaining_source_scope_questions_821.json), SHA256
`ceb72f230679aa2f9d36aabd9e62abebd14c3382c74d59ff40bae74c0cb278ca`,
bind the census membership. The [opt-in manifest](source_scope_attestation_821.json),
SHA256 `3e2bc71f6cd409769a8ccb34912ec2c1a7a3802f3444c2446038e347dbc5a657`,
pins that question, transcript and exactly821 source hashes, four raw constraints
and title/abstract/purpose element hashes. Original question/census bytes are retained.

| Exact group | Selected | Promoted | Independent holds retained |
|---|---:|---:|---:|
| Check with Contributor, all four fields |361|359|2|
| ADF&G Request/Republication paired variants |351|323|28|
| Unknown, all four fields |109|109|0|
| Total |821|791|30|

The completed rebuild yields **3234 supported /966 held /6 malformed**, from
2443/1757/6. FGDC-10 andFGDC-2664 retain creator ambiguity;28 ADF&G sources retain
long-title holds. The exact821 overlap30 older protected cases:28 now promote
under this explicit answer,2 retain creator holds. The other146 protected sources
remain unchanged, leaving148 protected holds. All456 alias identities remain held.

All4206 original XML hashes,4200 exact copies and4194 complete raw constructed metadata objects
are unchanged against both the frozen previous report and a same-timestamp current
baseline. Only821 payload policy references are added;3373 payload files outside
that membership are byte-identical before/after. Literal constraints, attribution,
restricted XML and blank licenses remain intact. No dates or creators are invented.
No remote_verified or publication_approved flag is true.

Normalized submission preparation embeds active policy evidence in notes. The
[five-record preparation](five_import_correction_preparation.md) therefore retains
its historical94 comparisons and separately binds current normalized metadata/
notes hashes. Those notes changes are provenance changes; every other normalized
field remains unchanged in that bounded five-record comparison.

The optional classifier flag participates in the cache profile. The shared agent
and both human QA routes validate the same pinned evidence, exact source/context,
separate rehosting authority and restricted/blank-license policy. Missing, tampered,
withdrawn, conflicting, nonmember or future-dated evidence fails closed. Removing
the opt-in evidence restores access holds while preserving independent decisions.

Runtime commit: `503f72b15b0b5cf949096e6e7d4d2c3200001ac5`.
**347 guarded offline tests pass**, plus7 independently reproduced focused contracts.
See [validation](source_scope_attestation_validation.json),
[complete delta](source_scope_attestation_complete_delta.json),
[source evidence review](source_scope_attestation_evidence_review.json) and
[implementation review](source_scope_attestation_implementation_review.json).
The old report SHA is `6213c25a1f3d71cdb08ae19a1ca91762fdad5b3f11524ed7ed137f1b7edb044e`;
baseline `52b8fb6dc66643a0113275dff2e2f19db2be21db75dc18404b92e663c1ec057a`;
after `759b7c924dc1452be1850635d4bee41230007883f7b94a4691160b067fa127dc`.

## Reproduce the source-only rebuild

From the frozen handoff checkout, with Requests/socket/DNS blocked as in the
guarded validation harness, run the following. A new output directory is required;
omit only the final scope flag for the same-runtime baseline.

```bash
python -m scripts.collection_qa --source-dir FGDC --output-dir /tmp/pices-scope821-after \
  --reviewed-at 2026-10-03T20:30:00Z \
  --authority-manifest docs/readiness/2026-10-02/rehosting_authority.json \
  --access-interpretation-manifest docs/readiness/2026-10-02/contact_source_interpretation.json \
  --contributor-access-interpretation-manifest docs/readiness/2026-10-02/contributor_source_interpretation.json \
  --creator-interpretation-manifest docs/readiness/2026-10-02/exxon_citation_interpretation.json \
  --dataset-access-interpretation-manifest docs/readiness/2026-10-03/finite_source_resource_access_264.json \
  --collective-creator-interpretation-manifest docs/readiness/2026-10-03/dfo_staff_citation_interpretation.json \
  --institution-creator-interpretation-manifest docs/readiness/2026-10-03/source_citation_credits_401.json \
  --source-link-interpretation-manifest docs/readiness/2026-10-03/historical_dataset_linkage_21.json \
  --source-title-interpretation-manifest docs/readiness/2026-10-03/source_display_titles_8.json \
  --source-scope-attestation-manifest docs/readiness/2026-10-03/source_scope_attestation_821.json
```

The independent modern trial is separate: parent reports exact approval and one
durable POST intent, with no retained response/ID/exception trace and no established
network dispatch. All create allowances remain spent/held; no reset or new grant
follows from this source work. Root issued zero provider requests.
