"""Measure current component semantics for both members of all 228 alias pairs.

Uses the unchanged collection classifier and its active alias gate. All writes
are confined to a fresh offline fixture directory; no canonical ID is chosen.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import Mock


BASE = "05d699e93572345c0591ca932a03089a9dd9ba9c"
ALIAS_REASON = "Exact-copy aliases require identity adjudication"
MANIFEST = "docs/readiness/2026-10-04/alias456_source_to_content.json"
LEDGER = "docs/readiness/2026-10-04/residual_resource4_integrated_source_status.json"
PINS = {
    "ci/run_offline_tests.py": "1b1f9823488dda1d66dc6bd12bd8e841f84c3e2add727ac254961b3a9e322d05",
    "scripts/collection_qa.py": "cfd88e6c869d6814d1d76ae376835992eec95c728faca0f085894e0b7e9d0938",
    MANIFEST: "9c110638bd161483727aed1b42e516fdc7a3c9d8134c97a9a70abff690750bbb",
    LEDGER: "4e24fbe4859644d7fe1ddfbd87bf207df8dd6f4f8a9ea288713a1fb9a15aed7b",
    "docs/readiness/2026-10-04/finite_source_resource_access_596.json": "4719b46cfe46a2b950b3abc695fd8778ffc7bd3041e5bb0bae253c613c55ec2c",
    "docs/readiness/2026-10-04/source_citation_credits_412.json": "c6aa4f9c2e4c80ea565b3a92d66d0e066b12f77534bd23feb92807bd18894ee3",
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def number(sid):
    return int(sid.removeprefix("FGDC-"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviewed-at", required=True)
    args = parser.parse_args()
    os.environ.clear()
    sys.dont_write_bytecode = True
    repo, output = args.repo.resolve(), args.output.resolve()
    require(datetime.fromisoformat(args.reviewed_at).utcoffset() is not None,
            "Assessment timestamp must be timezone aware")
    require(output.is_relative_to(Path("/tmp")) and not output.is_relative_to(repo),
            "Use a fresh /tmp output directory outside the source checkout")
    require(not output.exists(), "Output directory must be new; no resume cache is used")
    require(digest((repo / "ci/run_offline_tests.py").read_bytes()) ==
            PINS["ci/run_offline_tests.py"], "Offline guard changed")
    helper_sha = digest(Path(__file__).read_bytes())
    sys.path.insert(0, str(repo))
    from ci.run_offline_tests import OfflineGuard, checkout_revision, clean_environment

    require(checkout_revision(repo) == BASE, "Use the exact reviewed base checkout")
    output.mkdir(parents=True)
    os.chdir(repo)
    os.environ.update(clean_environment(output))
    tempfile.tempdir = str(output)

    class ReadBoundGuard(OfflineGuard):
        """Retain hashes of the public repository files actually read by QA."""

        def __init__(self):
            super().__init__(repo, output, BASE)
            self.input_hashes = {}
            self.hashing = False

        def check_read(self, target):
            super().check_read(target)
            if (not self.hashing and target.is_relative_to(repo)
                    and target.is_file() and str(target.relative_to(repo)) not in self.input_hashes):
                self.hashing = True
                try:
                    self.input_hashes[str(target.relative_to(repo))] = digest(target.read_bytes())
                finally:
                    self.hashing = False

    guard = ReadBoundGuard()
    # The helper is public task code, not an additional directory read grant.
    guard.library_files.add(Path(__file__).resolve())
    guard.install()
    guard.self_check()
    for relative, expected in PINS.items():
        require(digest((repo / relative).read_bytes()) == expected, "Pinned input changed")
    import scripts.logger
    scripts.logger.get_logger = lambda *a, **kw: Mock()
    from scripts.collection_qa import classify_collection
    from scripts.path_config import OutputPaths

    manifest = json.loads((repo / MANIFEST).read_bytes())
    ledger = json.loads((repo / LEDGER).read_bytes())
    baseline = {row["source_id"]: row for row in ledger["records"]}
    aliases = {row["source_id"]: row for row in manifest["source_to_content"]}
    groups = manifest["groups"]
    require(len(aliases) == 456 and len(groups) == 228, "Alias scope changed")
    require(all(len(group["equivalence_group_members"]) == 2 for group in groups),
            "A content class is not a complete pair")
    require({sid for group in groups for sid in group["equivalence_group_members"]} == set(aliases),
            "Class and source coverage differ")
    require(all(baseline[sid]["source_status"] == "held" and
                baseline[sid]["source_sha256"] == row["source_sha256"]
                and row["canonical_source_id"] is None for sid, row in aliases.items()),
            "Alias identity or current-ledger hold changed")
    baseline_alias_rows = [baseline[sid] for sid in sorted(aliases, key=number)]
    baseline_alias_digest = digest(canonical(baseline_alias_rows))
    old = repo / "docs/readiness/2026-10-02"
    docs = repo / "docs/readiness/2026-10-03"
    today = repo / "docs/readiness/2026-10-04"
    options = {
        "authority_manifest": old / "rehosting_authority.json",
        "access_interpretation_manifest": old / "contact_source_interpretation.json",
        "creator_interpretation_manifest": old / "exxon_citation_interpretation.json",
        "contributor_access_interpretation_manifest": old / "contributor_source_interpretation.json",
        "collective_creator_interpretation_manifest": docs / "dfo_staff_citation_interpretation.json",
        "institution_creator_interpretation_manifest": today / "source_citation_credits_412.json",
        "source_link_interpretation_manifest": docs / "historical_dataset_linkage_21.json",
        "source_title_interpretation_manifest": docs / "source_display_titles_35.json",
        "source_scope_attestation_manifest": docs / "source_scope_reconciliation_904.json",
        "dataset_access_interpretation_manifest": today / "finite_source_resource_access_596.json",
    }
    option_bindings = {name: {"path": str(path), "sha256": digest(path.read_bytes())}
                       for name, path in options.items()}
    # Historical categories only select a varied smoke; they do not decide current verdicts.
    smoke_ids = set()
    for wanted in ("FGDC-2953", "FGDC-2837", "FGDC-2872", "FGDC-2894"):
        smoke_ids.update(aliases[wanted]["equivalence_group_members"])
    for sid in sorted(aliases, key=number):
        reasons = aliases[sid]["historical_component_diagnostics_not_current_qa"]["hold_reasons"]
        if any("Contradictory or unsupported source access" in reason for reason in reasons):
            smoke_ids.update(aliases[sid]["equivalence_group_members"])
            break
    require(len(smoke_ids) == 10, "Smoke must contain five complete pairs")
    payload_evidence = {}
    phase_results = {}

    def run_phase(name, selected):
        source = output / name / "sources"
        destination = output / name / "prepared"
        source.mkdir(parents=True)
        for sid in sorted(selected, key=number):
            raw = (repo / "FGDC" / (sid + ".xml")).read_bytes()
            require(digest(raw) == aliases[sid]["source_sha256"], "Selected original changed")
            (source / (sid + ".xml")).write_bytes(raw)
        print(f"START {name}: {len(selected)} files, both members of every selected pair", flush=True)
        started = time.monotonic()
        report = classify_collection(source, destination, args.reviewed_at, **options)
        rows = {row["source_id"]: row for row in report["records"]}
        require(set(rows) == set(selected), "Measured source coverage differs")
        require(report["summary"]["source_status_counts"] ==
                {"supported": 0, "held": len(selected), "failed": 0}, "Alias gate not preserved")
        require(report["summary"]["exact_copy_groups"] == len(selected) // 2,
                "Complete pair gate coverage differs")
        paths = OutputPaths(str(destination), "sandbox")
        for sid, row in rows.items():
            require(row["source_sha256"] == aliases[sid]["source_sha256"], "Measured source hash differs")
            require(set(row["exact_copy_aliases"]) == set(aliases[sid]["equivalence_group_members"]),
                    "Classifier did not retain the exact pair")
            require(row["hold_reasons"].count(ALIAS_REASON) == 1, "Alias reason missing or duplicated")
            require(not row["remote_verified"] and not row["publication_approved"], "Release flag changed")
            require(row["rehosting_authority"] == "USER_ATTESTED", "Separate authority missing")
            copied = Path(paths.original_fgdc_dir) / (sid + ".xml")
            require(digest(copied.read_bytes()) == row["source_sha256"], "Prepared XML differs")
            payload_path = Path(paths.zenodo_json_dir) / (sid + ".json")
            raw_payload = payload_path.read_bytes()
            require(digest(raw_payload) == row["prepared_payload_sha256"], "Payload hash differs")
            payload = json.loads(raw_payload)
            metadata, policy = payload["metadata"], payload["artifact_policy"]
            require(metadata["access_right"] == "restricted" and metadata["license"] == "",
                    "Restricted unlicensed restoration policy changed")
            require(policy["rights_scope"] == "original_fgdc_xml"
                    and policy["rights_source_xpath"] == "./metainfo/metuc"
                    and policy["date_semantics"] == "source_metadata_date"
                    and policy.get("license") in (None, "")
                    and policy.get("rehosting_authority") is not None,
                    "Artifact authority, rights or date policy changed")
            if name == "all456":
                payload_evidence[sid] = {
                    "payload_path": str(payload_path.relative_to(output)),
                    "payload_sha256": digest(raw_payload),
                    "complete_metadata_canonical_sha256": digest(canonical(metadata)),
                    "prepared_original_xml_path": str(copied.relative_to(output)),
                    "prepared_original_xml_sha256": digest(copied.read_bytes()),
                }
        require(not any(guard.counts["tests"].values()), "Unexpected offline guard event")
        phase_results[name] = {
            "source_ids": sorted(selected, key=number), "seconds": round(time.monotonic() - started, 3),
            "profile_sha256": report["profile_sha256"], "summary": report["summary"],
            "classification_path": str((destination / "classification.json").relative_to(output)),
            "classification_sha256": digest((destination / "classification.json").read_bytes()),
        }
        print(f"PASS {name}: all {len(selected)} remain held; guard events zero", flush=True)
        return rows

    smoke = run_phase("smoke10", smoke_ids)
    measured = run_phase("all456", set(aliases))
    require(all(measured[sid] == smoke[sid] for sid in smoke), "Smoke/full semantic rows differ")
    component_counts = Counter(row["source_status_without_aliases"] for row in measured.values())
    class_counts = Counter()
    class_rows, source_rows = [], []
    reason_classes = defaultdict(list)
    asymmetries = []
    for group in sorted(groups, key=lambda g: g["canonical_content_id"]):
        ids = group["equivalence_group_members"]
        signatures = [{
            "source_status_without_aliases": measured[sid]["source_status_without_aliases"],
            "technical_metadata": measured[sid]["technical_metadata"],
            "additional_hold_reasons": [reason for reason in measured[sid]["hold_reasons"] if reason != ALIAS_REASON],
        } for sid in ids]
        agree = signatures[0] == signatures[1]
        label = ("otherwise_supported" if agree and signatures[0]["source_status_without_aliases"] == "supported"
                 else "additional_holds" if agree else "member_semantics_differ")
        class_counts[label] += 1
        if not agree:
            asymmetries.append(group["canonical_content_id"])
        reason_classes[canonical(signatures).decode()].append(group["canonical_content_id"])
        class_rows.append({
            "canonical_content_id": group["canonical_content_id"], "equivalence_group_members": ids,
            "current_component_classification": label, "member_semantics_agree": agree,
            "member_semantics": dict(zip(ids, signatures)),
            "prepared_metadata_equal": payload_evidence[ids[0]]["complete_metadata_canonical_sha256"] ==
                                       payload_evidence[ids[1]]["complete_metadata_canonical_sha256"],
            "current_final_source_statuses": {sid: measured[sid]["source_status"] for sid in ids},
            "canonical_source_id": None, "record_collapse_authorized": False,
        })
    for sid in sorted(aliases, key=number):
        source_rows.append({
            "source_id": sid, "source_sha256": measured[sid]["source_sha256"],
            "canonical_content_id": aliases[sid]["canonical_content_id"],
            "equivalence_group_members": aliases[sid]["equivalence_group_members"],
            "unchanged_baseline_ledger_record": baseline[sid],
            "actual_current_classification": measured[sid],
            "additional_hold_reasons": [reason for reason in measured[sid]["hold_reasons"] if reason != ALIAS_REASON],
            "prepared_artifacts": payload_evidence[sid],
            "canonical_source_id": None,
        })
    inputs_before = dict(guard.input_hashes)
    require(all(digest((repo / rel).read_bytes()) == sha for rel, sha in inputs_before.items()),
            "An actual repository input changed during QA")
    require(digest((repo / LEDGER).read_bytes()) == PINS[LEDGER], "Current ledger mutated")
    require(baseline_alias_digest == digest(canonical([row["unchanged_baseline_ledger_record"] for row in source_rows])),
            "An alias ledger object changed")
    require(not any(guard.counts["tests"].values()), "Unexpected offline guard event")
    result = {
        "schema_version": 1, "status": "MEASURED_CURRENT_SEMANTICS_ALIAS_GATE_RETAINED",
        "base_main": BASE, "reviewed_at": args.reviewed_at, "helper_sha256": helper_sha,
        "scope": "Ten-source pair-complete smoke, then both members of all 228 byte-content classes; fresh guarded actual outputs, no classification cache reuse or raw-pair byte audit.",
        "profile_options": option_bindings, "actual_profile_sha256": phase_results["all456"]["profile_sha256"],
        "pinned_inputs_sha256": PINS, "actual_repository_inputs_sha256": inputs_before,
        "actual_repository_inputs_unchanged": True, "baseline_ledger_alias_objects_canonical_sha256": baseline_alias_digest,
        "all456_current_ledger_status_objects_unchanged_held": True,
        "phases": phase_results, "source_count": len(source_rows), "content_class_count": len(class_rows),
        "current_final_source_status_counts": dict(Counter(row["source_status"] for row in measured.values())),
        "current_source_status_without_aliases_counts": dict(component_counts),
        "current_component_class_counts": dict(class_counts),
        "current_technical_metadata_counts": dict(Counter(row["technical_metadata"] for row in measured.values())),
        "member_semantic_asymmetry_content_ids": asymmetries,
        "additional_reason_class_groups": [{"paired_member_semantics": json.loads(key),
                                           "content_class_count": len(ids), "canonical_content_ids": ids}
                                          for key, ids in sorted(reason_classes.items())],
        "guard": {"implementation": "ci.run_offline_tests.OfflineGuard with public-input hash capture",
                  "environment_cleared_dummy_credentials_only": True,
                  "blocks": guard.counts, "unexpected_call_sites": guard.blocked_call_sites,
                  "in_process_public_revision_queries": guard.metadata_queries,
                  "limitation": "Accidental-I/O guard reused from CI; not a hostile-code sandbox."},
        "classes": class_rows, "sources": source_rows,
        "class_rows_canonical_sha256": digest(canonical(class_rows)),
        "source_rows_canonical_sha256": digest(canonical(source_rows)),
        "source_promotions": 0, "canonical_selections": 0, "record_collapse_or_rekey": 0,
        "provider_requests": 0, "publication_approvals": 0,
        "decision_status": "The one-restored-record-per-pair question is unanswered; no response or collapse authority is inferred.",
    }
    write_json(output / "current_alias_semantics.json", result)
    print(json.dumps({"receipt": str(output / "current_alias_semantics.json"),
                      "receipt_sha256": digest((output / "current_alias_semantics.json").read_bytes()),
                      "current_component_source_counts": dict(component_counts),
                      "current_component_class_counts": dict(class_counts),
                      "all456_final_held": True, "unexpected_guard_events": guard.counts["tests"]}), flush=True)


if __name__ == "__main__":
    main()
