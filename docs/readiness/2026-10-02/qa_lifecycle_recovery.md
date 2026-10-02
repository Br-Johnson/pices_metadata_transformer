# Offline QA lifecycle recovery

This repair is based on local checkpoint `2d4b4298ca44c2bedc1fe77cc6513ec67794b342`. Review reproduced two defects in temporary fixtures: changing cached verdict fields promoted a held source during resume, and schema-1/schema-2 human approvals accepted a changed external restoration-authority manifest.

Classification now recreates every row from raw XML and reruns technical and source assessment. Verified prepared payloads still avoid retransformation when their artifact policy and content inventory match the current collection policy. A cached payload cannot substitute dataset rights for XML rights or remove requested restoration authority. Cached verdicts, provenance and approval/readback flags cannot replace current evidence. All artifact approval paths recheck any restoration-authority digest, exact source membership and restricted blank-license conditions. Human semantic adjudication remains available; program review and separate release gates still apply.

Both defects have failing-first regressions. The complete suite passes 136 tests with socket access blocked, including malformed cached sources, cache-policy route changes, unchanged transformation reuse, alias removal, stale human authority approvals, remote readback, invalid file/license conditions and legitimate human creator adjudication. The baseline suite passed 128 tests before these regressions were added.

Fresh and resumed classification each cover 4,206 originals. Every record and summary matches the pre-repair run: 687 supported, 3,513 held, six strict parse failures; technical counts remain 4,131 pass, 63 held and 12 not constructed. The 228 exact-copy groups involving 456 files remain adjudication holds. All source hashes match the attested manifest, and all approval/readback flags remain false.

The unchanged resume is byte-identical to the fresh report. The updated rule profile is `0ae46acc9fd2b493855ddcb254d912583f13af1f7eaf579bf6bbc5abfe160c77`; report SHA-256 is `e48aeea2101650292b7d6af5acf90cb276d5f5826c894e7a871800d28071a75a`. Only the rule profile changes the report relative to the baseline. Existing classification CSV and hold-code exports remain valid because all record decisions are unchanged.

On the recovery Mac, fresh classification took 26.97 seconds and resume took 23.93 seconds. The earlier cache-only resume took 2.63 seconds; rechecking semantics intentionally adds work while retaining construction reuse. These timings describe this local run.

Reproduce with `python -m unittest discover -s tests -v`, then the collection command in [rehosting_attestation.md](rehosting_attestation.md) using a new derived workspace. Run the same collection command again to check unchanged resume. The recovery used Python 3.14.7 with an external audit-hook socket guard, a successful block-control check, a minimal credential-free environment and bytecode writes disabled; no socket attempts were made by the successful suite or classifier.

The original checkout and running task were left untouched. This isolated repair does not establish remote record QA, authenticated sandbox compatibility or production release. Reconcile the original writer before a single writer publishes the tested recovery.
