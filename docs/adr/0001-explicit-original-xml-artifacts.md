# Explicit original XML artifacts

Status: implemented offline; live activation awaits human source-policy decisions and authenticated sandbox validation.

Zenodo requires a file. The historical empty-file contract and tiny generic metadata stubs do not establish a faithful archival object. Attach the untouched original XML only when a source-hash-bound human decision explicitly identifies it as a descriptive metadata artifact with reviewed object type, date meaning and rights evidence. Keep legacy deposits unchanged by default.

Use one additive version-1 artifact contract for filename/size/checksum/policy/role bindings across the environment ledger, duplicate payload fingerprint, QA manifest, upload/resume, reconciliation and readback. Avoid separate attachment flows with different safety rules. Preserve source bytes and source aliases. Do not imply underlying research data are present or reuse a cited work DOI for the XML.

This deliberately limits the first implementation to one original XML artifact with resource type other. Broader multi-file data deposits require their own reviewed role/rights/identity contract. A schema pass or a filled evidence field is not independent legal clearance. Live rollout remains bounded draft-only canaries, readback and unchanged rerun before expansion; production publication remains explicitly human-QA gated.
