"""Measure approved alias-class targets with fresh guarded source-only outputs.

The frozen source ledger remains unchanged. Content classes retain both original
files, cannot be uploaded, and do not claim remote identity reconciliation.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

BASE_MAIN = "dc10c9955e0e28ac1069d8b50ad729e40a255697"
DOCS = "docs/readiness/2026-10-04/"
LEDGER = DOCS + "residual_evidence15_integrated_source_status.json"
MAPPING = DOCS + "alias456_source_to_content.json"
REPRESENTATION = DOCS + "approved_alias_representation_228.json"
PRIOR_QA = DOCS + "alias228_current_semantics.json"
ALIAS_REASON = "Exact-copy aliases require identity adjudication"
PINS = {
    "ci/run_offline_tests.py": "1b1f9823488dda1d66dc6bd12bd8e841f84c3e2add727ac254961b3a9e322d05",
    LEDGER: "4a4ef82f9da793c0a83cd58f6388991dd38f7a5f92947b2d089855b259af4e4a",
    MAPPING: "9c110638bd161483727aed1b42e516fdc7a3c9d8134c97a9a70abff690750bbb",
    REPRESENTATION: "9e45fc869b0fe03220b44734cf429129f78dc93eb9fd20bf9b802398b684dda6",
    PRIOR_QA: "10536d3193b4aa915bbc614d66d4172456e4e2f0b66dd2005b1ea791d9d2f3f0",
    DOCS + "alias_pair_approach_authority.json": "ea3c0dba61ba03a330c80fc204f70ae3b88669f5ede5f22e60015b4bdb828130",
    DOCS + "finite_source_resource_access_607.json": "83bdb0b1ab689e5fbf844467975ad9d279b6bba759cb3db3a18a11704715679c",
    DOCS + "source_citation_credits_415.json": "ae4404c40238542c517822fe4424d14a0cbe93efef542bf42d359717fd4ba2e3",
    DOCS + "source_display_titles_36.json": "c776b324f43a3e7560ef016f12b7a345bbb2f21cc016b74bd5298b8ed1e10781",
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


def file_receipt(path, output):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(output)), "sha256": digest(raw), "bytes": len(raw)}


def validate(repo, output, reviewed_at, revision, helper_sha, guard):
    """Import repository runtime only after the complete guard is installed."""
    require(guard.phase == "tests" and guard.repo == repo and guard.fixture_root == output,
            "Installed guard must cover this exact checkout and output")
    import scripts.logger

    scripts.logger.get_logger = lambda *args, **kwargs: Mock()
    from scripts.artifact_contract import prepare_artifact
    from scripts.collection_qa import classify_collection
    from scripts.content_class_targets import (
        build_target_view,
        load_representation,
        prepare_class_target,
    )
    from scripts.path_config import OutputPaths
    from scripts.upload_service import prepare_metadata

    for relative, expected in PINS.items():
        require(digest((repo / relative).read_bytes()) == expected, "Pinned input changed: " + relative)
    ledger_raw = (repo / LEDGER).read_bytes()
    ledger = json.loads(ledger_raw)
    ledger_rows = ledger["records"]
    baseline = {row["source_id"]: row for row in ledger_rows}
    require(len(baseline) == len(ledger_rows) == 4206, "Frozen source inventory must contain 4206 unique rows")
    require(Counter(row["source_status"] for row in ledger_rows) ==
            {"supported": 3696, "held": 504, "failed": 6}, "Frozen source status counts differ")
    source_inventory = {sid: row["source_sha256"] for sid, row in baseline.items()}
    require(all(re.fullmatch(r"[0-9a-f]{64}", sha) for sha in source_inventory.values()),
            "Frozen source inventory has invalid byte bindings")
    mapping = json.loads((repo / MAPPING).read_bytes())
    aliases = {row["source_id"]: row for row in mapping["source_to_content"]}
    representation = load_representation()
    classes = {row["record_target_id"]: row for row in representation["classes"]}
    previous = json.loads((repo / PRIOR_QA).read_bytes())
    prior_classes = {row["canonical_content_id"]: row for row in previous["classes"]}
    require(len(aliases) == 456 and len(classes) == 228 and set(classes) == set(prior_classes),
            "Finite class coverage differs from prior measured evidence")
    require({sid for row in classes.values() for sid in row["source_ids"]} == set(aliases),
            "Class membership does not cover exactly the 456 alias sources")
    require(all(baseline[sid]["source_status"] == "held"
                and source_inventory[sid] == row["source_sha256"] for sid, row in aliases.items()),
            "An original source hash or legacy alias hold differs")
    prior_held = {cid for cid, row in prior_classes.items()
                  if row["current_component_classification"] == "additional_holds"}
    require(len(prior_held) == 24 and all(row["member_semantics_agree"] for row in prior_classes.values()),
            "Prior component-semantic evidence differs")
    singleton_rows = [row for row in ledger_rows if row["source_id"] not in aliases]
    require(len(singleton_rows) == 3750, "Singleton source projection count differs")
    expected_singletons = [
        {"record_target_id": row["source_id"], "source_ids": [row["source_id"]],
         "source_sha256": row["source_sha256"], "source_semantic_status": row["source_status"]}
        for row in singleton_rows
    ]
    old = repo / "docs/readiness/2026-10-02"
    yesterday = repo / "docs/readiness/2026-10-03"
    today = repo / DOCS
    options = {
        "authority_manifest": old / "rehosting_authority.json",
        "access_interpretation_manifest": old / "contact_source_interpretation.json",
        "creator_interpretation_manifest": old / "exxon_citation_interpretation.json",
        "contributor_access_interpretation_manifest": old / "contributor_source_interpretation.json",
        "collective_creator_interpretation_manifest": yesterday / "dfo_staff_citation_interpretation.json",
        "institution_creator_interpretation_manifest": today / "source_citation_credits_415.json",
        "source_link_interpretation_manifest": yesterday / "historical_dataset_linkage_21.json",
        "source_title_interpretation_manifest": today / "source_display_titles_36.json",
        "source_scope_attestation_manifest": yesterday / "source_scope_reconciliation_904.json",
        "dataset_access_interpretation_manifest": today / "finite_source_resource_access_607.json",
    }
    option_bindings = {name: {"path": str(path.relative_to(repo)), "sha256": digest(path.read_bytes())}
                       for name, path in options.items()}
    # Reuse the previous varied five-pair selection; it does not supply verdicts.
    smoke_ids = set()
    for sid in ("FGDC-2953", "FGDC-2837", "FGDC-2872", "FGDC-2894"):
        smoke_ids.update(aliases[sid]["equivalence_group_members"])
    for sid in sorted(aliases, key=number):
        reasons = aliases[sid]["historical_component_diagnostics_not_current_qa"]["hold_reasons"]
        if any("Contradictory or unsupported source access" in reason for reason in reasons):
            smoke_ids.update(aliases[sid]["equivalence_group_members"])
            break
    require(len(smoke_ids) == 10, "Smoke must contain ten sources in five complete classes")
    require(smoke_ids == set(previous["phases"]["smoke10"]["source_ids"]), "Varied smoke selection changed")
    phase_receipts = {}

    def classify_phase(name, selected):
        source_dir = output / name / "sources"
        prepared_dir = output / name / "prepared"
        source_dir.mkdir(parents=True)
        for sid in sorted(selected, key=number):
            raw = (repo / "FGDC" / (sid + ".xml")).read_bytes()
            require(digest(raw) == source_inventory[sid], "An actual selected source differs from the frozen ledger")
            (source_dir / (sid + ".xml")).write_bytes(raw)
        require(not prepared_dir.exists(), "Classification must use a fresh output without caches")
        print(f"START {name}: {len(selected)} sources, complete pairs", flush=True)
        started = time.monotonic()
        report = classify_collection(source_dir, prepared_dir, reviewed_at, **options)
        rows = {row["source_id"]: row for row in report["records"]}
        require(len(rows) == len(report["records"]) == len(selected) and set(rows) == selected,
                "Fresh classifier source coverage differs")
        require(report["summary"]["source_status_counts"] ==
                {"supported": 0, "held": len(selected), "failed": 0}, "Legacy source alias gate changed")
        require(report["summary"]["exact_copy_groups"] == len(selected) // 2,
                "Classifier must observe each complete pair")
        paths = OutputPaths(str(prepared_dir), "sandbox")
        payloads, evidence = {}, {}
        for sid, row in rows.items():
            require(row["source_sha256"] == source_inventory[sid]
                    and set(row["exact_copy_aliases"]) == set(aliases[sid]["equivalence_group_members"]),
                    "Classifier original/pair binding differs")
            require(row["hold_reasons"].count(ALIAS_REASON) == 1
                    and not row["remote_verified"] and not row["publication_approved"],
                    "Classifier alias/release state changed")
            require(row["rehosting_authority"] == "USER_ATTESTED", "Separate restoration authority missing")
            payload_path = Path(paths.zenodo_json_dir) / (sid + ".json")
            copied_path = Path(paths.original_fgdc_dir) / (sid + ".xml")
            raw_payload, copied = payload_path.read_bytes(), copied_path.read_bytes()
            require(digest(copied) == source_inventory[sid]
                    and copied == (source_dir / (sid + ".xml")).read_bytes(), "Prepared original copy differs")
            require(digest(raw_payload) == row["prepared_payload_sha256"], "Classifier payload byte receipt differs")
            payload = json.loads(raw_payload)
            metadata, policy = payload["metadata"], payload["artifact_policy"]
            require(metadata["access_right"] == "restricted" and metadata["license"] == ""
                    and policy["rights_scope"] == "original_fgdc_xml"
                    and policy["rights_source_xpath"] == "./metainfo/metuc"
                    and policy["date_semantics"] == "source_metadata_date"
                    and policy.get("license") in (None, "")
                    and policy.get("rehosting_authority") is not None, "Rights/date/source authority policy changed")
            payloads[sid] = payload
            evidence[sid] = {
                "source_id": sid, "source_sha256": source_inventory[sid],
                "source_component_status": row["source_status_without_aliases"],
                "source_status": row["source_status"],
                "payload": file_receipt(payload_path, output),
                "prepared_original": file_receipt(copied_path, output),
                "complete_raw_metadata_sha256": digest(canonical(metadata)),
                "policy_sha256": digest(canonical(policy)),
            }
        require(not any(guard.counts["tests"].values()), "Unexpected guard event during classification")
        phase_receipts[name] = {
            "source_ids": sorted(selected, key=number), "seconds": round(time.monotonic() - started, 3),
            "classification": file_receipt(prepared_dir / "classification.json", output),
            "profile_sha256": report["profile_sha256"], "summary": report["summary"],
        }
        return paths, rows, payloads, evidence

    def check_target(target, paths, rows, payloads, evidence):
        cid = target["record_target_id"]
        identity = classes[cid]
        ids = identity["source_ids"]
        require(all(target[key] == value for key, value in identity.items()), "Class identity/provenance changed")
        require(target["reviewed_at"] == reviewed_at
                and target["representation_manifest_sha256"] == PINS[REPRESENTATION]
                and target["identity_representation_status"] == "approved"
                and target["production_reconciliation_status"] == "pending"
                and target["execution_status"] == "class_execution_not_implemented"
                and target["upload_eligible"] is False and target["remote_verified"] is False
                and target["publication_approved"] is False, "Class operation or release gate changed")
        require(payloads[ids[0]]["metadata"] == payloads[ids[1]]["metadata"],
                "Both complete raw member metadata objects must match")
        require(target["common_source_metadata_sha256"] == digest(canonical(payloads[ids[0]]["metadata"])),
                "Class common metadata does not bind the actual current member payload")
        require(target["metadata_sha256"] == digest(canonical(target["metadata"])), "Class metadata receipt differs")
        contract = target["artifact_contract"]
        require(contract is not None and contract["schema_version"] == 2
                and contract["record_target_id"] == cid and contract["members"] == target["members"]
                and contract["member_set_sha256"] == target["member_set_sha256"]
                and contract["member_set_sha256"] == digest(canonical(target["members"]))
                and contract["sha256"] == digest(canonical({key: value for key, value in contract.items() if key != "sha256"})),
                "Class contract or member-set receipt differs")
        require([member["source_id"] for member in target["members"]] == ids
                and [item["name"] for item in contract["files"]] == identity["source_filenames"],
                "Class must retain both original identities and filenames")
        require(target["content_classification"]["content_status"] == "metadata_only"
                and target["content_classification"]["inventory_complete"] is True
                and [item["name"] for item in target["content_classification"]["files"]] == identity["source_filenames"]
                and all(item["role"] == "descriptive_metadata" for item in target["content_classification"]["files"]),
                "Class content declaration must represent both original XML files only")
        statuses = [rows[sid]["source_status_without_aliases"] for sid in ids]
        require(statuses[0] == statuses[1], "Current class member source semantics differ")
        assessments = target["member_assessments"]
        require([item["source_id"] for item in assessments] == ids
                and [item["source_semantic_status"] for item in assessments] == statuses
                and target["source_semantic_status"] == statuses[0], "Class source assessment differs from actual classifier")
        require((cid in prior_held) == (target["source_semantic_status"] == "held"),
                "An additional source hold changed or a supported class regressed")
        notes_suffix = ("\n\nOriginal XML content class: " + cid +
                        ". Both original source identities/files are retained: " +
                        ", ".join(identity["source_filenames"]) +
                        ". The preserved XML text applies to both byte-identical originals; "
                        "no historical canonical source filename is selected. "
                        "Underlying research data are not included. Class artifact contract SHA-256: " + contract["sha256"])
        require(target["metadata"]["notes"].endswith(notes_suffix), "Exact class provenance note missing")
        class_base_notes = target["metadata"]["notes"][:-len(notes_suffix)]
        for sid, member, item in zip(ids, target["members"], contract["files"], strict=True):
            raw_path = Path(paths.original_fgdc_dir) / (sid + ".xml")
            raw = raw_path.read_bytes()
            require(item == {"name": sid + ".xml", "size": len(raw), "sha256": source_inventory[sid],
                             "md5": hashlib.md5(raw, usedforsecurity=False).hexdigest(), "role": "descriptive_metadata"},
                    "Class file contract differs from exact original bytes")
            artifact = prepare_artifact(payloads[sid], raw_path)
            require(member == {"source_id": sid, "source_filename": sid + ".xml", "source_sha256": source_inventory[sid],
                               "payload_sha256": evidence[sid]["payload"]["sha256"],
                               "policy_sha256": evidence[sid]["policy_sha256"], "artifact_v1_sha256": artifact["sha256"]},
                    "Class member evidence differs from current source payload and artifact policy")
            prepared, _, prepared_source_sha = prepare_metadata(str(Path(paths.zenodo_json_dir) / (sid + ".json")), paths)
            require(prepared_source_sha == source_inventory[sid], "Member metadata prepared from different source bytes")
            require({key: value for key, value in target["metadata"].items() if key != "notes"} ==
                    {key: value for key, value in prepared.items() if key != "notes"},
                    "Class metadata changed beyond provenance/contract notes")
            old_suffix = ("\n\nDeposited object: original FGDC XML metadata artifact; underlying research data are not included. "
                          "Artifact contract SHA-256: " + artifact["sha256"])
            require(prepared["notes"].endswith(old_suffix)
                    and prepared["notes"][:-len(old_suffix)] == class_base_notes,
                    "Complete notes changed beyond exact class provenance and artifact-contract replacement")
            evidence[sid]["prepared_metadata_sha256"] = digest(canonical(prepared))
            evidence[sid]["prepared_notes_sha256"] = digest(prepared["notes"].encode())
        return {"record_target_id": cid, "source_ids": ids,
                "source_semantic_status": target["source_semantic_status"],
                "member_semantics_agree": True, "both_complete_raw_metadata_objects_equal": True,
                "non_notes_metadata_exact_to_both_prepared_members": True,
                "notes_differ_only_by_exact_class_provenance_and_contract": True,
                "common_source_metadata_sha256": target["common_source_metadata_sha256"],
                "class_metadata_sha256": target["metadata_sha256"], "artifact_contract_sha256": contract["sha256"],
                "upload_eligible": False, "production_reconciliation_status": "pending"}

    smoke_paths, smoke_rows, smoke_payloads, smoke_evidence = classify_phase("smoke10", smoke_ids)
    smoke_targets = {}
    smoke_dir = output / "smoke10" / "class_targets"
    smoke_dir.mkdir()
    for cid, identity in classes.items():
        if not set(identity["source_ids"]) <= smoke_ids:
            continue
        first = prepare_class_target(cid, smoke_paths, reviewed_at=reviewed_at)
        repeated = prepare_class_target(cid, smoke_paths, reviewed_at=reviewed_at)
        require(first == repeated, "Unchanged class preparation retry differs")
        check_target(first, smoke_paths, smoke_rows, smoke_payloads, smoke_evidence)
        smoke_targets[cid] = first
        write_json(smoke_dir / ("XMLCLASS-" + identity["source_sha256"] + ".json"), first)
    require(len(smoke_targets) == 5, "Smoke must prepare and repeat five whole class targets")
    phase_receipts["smoke10"].update(prepared_classes=5, unchanged_retry_exact=True, upload_eligible_classes=0)
    print("PASS smoke10: five repeated class targets, both originals retained, zero eligible", flush=True)

    paths, measured, payloads, evidence = classify_phase("all456", set(aliases))
    require(all(measured[sid] == smoke_rows[sid] for sid in smoke_rows), "Smoke/full source classification rows differ")
    require(phase_receipts["smoke10"]["profile_sha256"] == phase_receipts["all456"]["profile_sha256"],
            "Smoke/full runtime and source profile bindings differ")
    target_dir = output / "record_target_view"
    report = build_target_view(paths, repo / LEDGER, target_dir, reviewed_at=reviewed_at)
    require(report["summary"] == {
        "original_source_files": 4206, "class_targets": 228, "represented_source_files": 456,
        "source_supported_classes": 204, "source_held_classes": 24, "upload_eligible_classes": 0,
        "complete_target_population": True, "unique_record_targets": 3978,
        "source_supported_targets": 3900, "source_held_targets": 72, "malformed_targets": 6,
    }, "Measured source-file and unique-target counts differ")
    require(report["source_ledger_sha256"] == PINS[LEDGER]
            and report["representation_manifest_sha256"] == PINS[REPRESENTATION]
            and report["legacy_source_ledger_changed"] is False, "Target view ledger binding differs")
    require(report["singleton_targets"] == expected_singletons,
            "All 3750 singleton rows must be the exact frozen-ledger projection")
    require(len(report["class_targets"]) == 228
            and {row["record_target_id"] for row in report["class_targets"]} == set(classes),
            "Target view class coverage differs")
    expected_index = [{"source_id": sid, "source_sha256": identity["source_sha256"],
                       "record_target_id": cid, "represented_by_class": True, "canonical_source_id": None}
                      for cid, identity in classes.items() for sid in identity["source_ids"]]
    require(report["source_to_target"] == expected_index, "Both original source identities must map exactly once")
    require({path.name for path in (target_dir / "originals").iterdir()} == {sid + ".xml" for sid in aliases},
            "Class artifact original inventory must contain exactly 456 files")
    require({path.name for path in (target_dir / "class_payloads").iterdir()} ==
            {"XMLCLASS-" + identity["source_sha256"] + ".json" for identity in classes.values()},
            "Class payload inventory must contain exactly 228 targets")
    class_evidence = []
    for row in report["class_targets"]:
        target_path = target_dir / row["payload_path"]
        target_raw = target_path.read_bytes()
        require(digest(target_raw) == row["payload_sha256"], "Target index payload receipt differs")
        target = json.loads(target_raw)
        checked = check_target(target, paths, measured, payloads, evidence)
        require(row["artifact_contract_sha256"] == target["artifact_contract"]["sha256"]
                and row["member_assessments"] == target["member_assessments"]
                and row["hold_reasons"] == target.get("hold_reasons", []), "Target index lost class evidence")
        require(all(row[key] == target[key] for key in (
            "record_target_id", "source_ids", "source_sha256", "canonical_source_id",
            "identity_representation_status", "source_semantic_status", "production_reconciliation_status",
            "upload_eligible", "remote_verified", "publication_approved")), "Target index state differs from artifact")
        if target["record_target_id"] in smoke_targets:
            require(target == smoke_targets[target["record_target_id"]], "Smoke/full target objects differ")
        checked["payload"] = file_receipt(target_path, output)
        checked["originals"] = []
        for sid in target["source_ids"]:
            copy_path = target_dir / "originals" / (sid + ".xml")
            require(copy_path.read_bytes() == (Path(paths.original_fgdc_dir) / (sid + ".xml")).read_bytes()
                    and digest(copy_path.read_bytes()) == source_inventory[sid], "Target copied original differs")
            checked["originals"].append(file_receipt(copy_path, output))
        class_evidence.append(checked)
    held_classes = {row["record_target_id"] for row in class_evidence if row["source_semantic_status"] == "held"}
    require(held_classes == prior_held, "The 24 additional-held content identities changed")
    require(Counter(row["source_status_without_aliases"] for row in measured.values()) ==
            {"supported": 408, "held": 48}, "Measured component source counts differ")
    require((repo / LEDGER).read_bytes() == ledger_raw, "Frozen source ledger changed")
    # Read only actual inputs again, including the selected 456 originals. Do not
    # claim a new byte audit of the 3750 unselected originals from this measurement.
    actual_inputs = dict(guard.input_hashes)
    require(all(digest((repo / relative).read_bytes()) == sha for relative, sha in actual_inputs.items()),
            "An actual runtime or evidence input changed during measurement")
    require(not any(guard.counts["tests"].values()), "Unexpected offline guard event")
    write_json(output / "frozen_source_inventory.json", source_inventory)
    result = {
        "schema_version": 1, "status": "MEASURED_OFFLINE_CONTENT_CLASS_REPRESENTATION_ALL_UPLOAD_HELD",
        "base_main": BASE_MAIN, "actual_checkout_revision": revision, "reviewed_at": reviewed_at,
        "helper_sha256": helper_sha, "pinned_inputs_sha256": PINS,
        "actual_repository_inputs_sha256": actual_inputs, "actual_repository_inputs_unchanged": True,
        "scope": "Fresh ten-source five-pair smoke, unchanged target retry, then fresh all456 classification and complete228 target assembly; no provider or remote identity evidence.",
        "profile_options": option_bindings, "actual_profile_sha256": phase_receipts["all456"]["profile_sha256"],
        "phases": phase_receipts, "record_target_view": file_receipt(target_dir / "record_targets.json", output),
        "source_file_status_counts": {"supported": 3696, "held": 504, "malformed": 6, "total": 4206},
        "record_target_summary": report["summary"],
        "source_ledger_full_bytes_unchanged": True, "source_ledger_sha256": digest(ledger_raw),
        "source_ledger_records_canonical_sha256": digest(canonical(ledger_rows)),
        "source_file_inventory": file_receipt(output / "frozen_source_inventory.json", output),
        "source_file_inventory_canonical_sha256": digest(canonical(source_inventory)),
        "all3750_singleton_projections_exact": True,
        "singleton_original_rows_canonical_sha256": digest(canonical(singleton_rows)),
        "singleton_target_projection_canonical_sha256": digest(canonical(expected_singletons)),
        "all456_legacy_alias_rows_still_held": True,
        "all228_classes_have_complete_artifacts_and_both_originals": True,
        "all24_additional_hold_content_ids_unchanged": True, "additional_hold_content_ids": sorted(held_classes),
        "member_semantic_asymmetry_content_ids": [], "smoke_full_targets_identical": True,
        "all_class_uploads_held_for_production_reconciliation_and_execution_support": True,
        "source_validation_scope": "All4206 ID/hash bindings retained from the byte-pinned input ledger; only selected456 original XML files read and rechecked here. Unselected original bytes are not reread by this helper; unchanged FGDC Git trees and the prior source15 full inventory remain separate preservation evidence.",
        "guard": {"implementation": "ci.run_offline_tests.OfflineGuard with public-input hash capture",
                  "environment_cleared_dummy_credentials_only": True, "blocks": guard.counts,
                  "unexpected_call_sites": guard.blocked_call_sites,
                  "in_process_public_revision_queries": guard.metadata_queries,
                  "limitation": "Accidental-I/O guard reused from CI; not a hostile-code sandbox."},
        "classes": class_evidence, "sources": [evidence[sid] for sid in sorted(evidence, key=number)],
        "provider_requests": 0, "production_identity_reconciliations": 0,
        "publication_approvals": 0, "new_rights_or_licenses": 0, "canonical_source_selections": 0,
    }
    write_json(output / "alias228_target_measurement.json", result)
    require(not any(guard.counts["tests"].values()), "Unexpected guard event while writing evidence")
    print(json.dumps({"receipt": str(output / "alias228_target_measurement.json"),
                      "receipt_sha256": digest((output / "alias228_target_measurement.json").read_bytes()),
                      "summary": report["summary"], "unexpected_guard_events": guard.counts["tests"]}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviewed-at", required=True)
    args = parser.parse_args()
    os.environ.clear()
    sys.dont_write_bytecode = True
    repo, output = args.repo.resolve(), args.output.resolve()
    reviewed = datetime.fromisoformat(args.reviewed_at.replace("Z", "+00:00"))
    require(reviewed.utcoffset() is not None and reviewed <= datetime.now(timezone.utc),
            "Assessment time must be explicit, timezone aware and nonfuture")
    require(output.is_relative_to(Path("/tmp").resolve()) and output != Path("/tmp").resolve()
            and not output.is_relative_to(repo), "Use a new /tmp output directory outside the source checkout")
    require(not output.exists() and output.parent.is_dir(), "Use a fresh output with an existing parent")
    require(digest((repo / "ci/run_offline_tests.py").read_bytes()) == PINS["ci/run_offline_tests.py"],
            "Pinned guard implementation changed")
    helper_sha = digest(Path(__file__).read_bytes())
    sys.path.insert(0, str(repo))
    # Only this stdlib guard module may be imported before guard installation.
    from ci.run_offline_tests import OfflineGuard, checkout_revision, clean_environment

    revision = checkout_revision(repo)
    os.chdir(repo)
    os.environ.update(clean_environment(output))
    tempfile.tempdir = str(output)

    class ReadBoundGuard(OfflineGuard):
        """Capture exact public repository inputs without extending read scope."""

        def __init__(self):
            super().__init__(repo, output, revision)
            self.input_hashes = {}
            self.hashing = False

        def check_read(self, target):
            super().check_read(target)
            if (not self.hashing and target.is_relative_to(repo) and target.is_file()
                    and str(target.relative_to(repo)) not in self.input_hashes):
                self.hashing = True
                try:
                    self.input_hashes[str(target.relative_to(repo))] = digest(target.read_bytes())
                finally:
                    self.hashing = False

    guard = ReadBoundGuard()
    # Allow the exact public helper file when root runs a reviewed /tmp draft.
    guard.library_files.add(Path(__file__).resolve())
    guard.install()
    guard.self_check()
    output.mkdir()
    validate(repo, output, args.reviewed_at, revision, helper_sha, guard)


if __name__ == "__main__":
    main()
