"""Measure a finite creator-credit delta and project unchanged historical classes.

Fresh source QA is limited to the declared candidates and controls. All original
XML bytes and unselected ledger rows remain fixed; historical class artifacts
are neither rebuilt nor claimed as newly assessed or upload eligible.
"""

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

BASE_MAIN = "173a4b0613e915b2915ae815b01f9f8823f2ced8"
DOCS = "docs/readiness/2026-10-04/"
LEDGER = DOCS + "residual_evidence15_integrated_source_status.json"
TARGETS = DOCS + "alias228_record_targets.json"
OLD_CREATOR = DOCS + "source_citation_credits_415.json"
CREATOR_IDS = {"FGDC-" + str(value) for value in (1314, 3951, 3952, 3953, 3966, 3967, 3968, 3969)}
SUPPORTED_CONTROLS = {"FGDC-3954"}
HELD_CONTROLS = {"FGDC-3975", "FGDC-909"}
SMOKE = CREATOR_IDS | SUPPORTED_CONTROLS | {"FGDC-3975"}
FULL = CREATOR_IDS | {"FGDC-909"}
PRIOR_CREATOR_COUNT = 415
BASE_SOURCE_COUNTS = {"supported": 3696, "held": 504, "failed": 6}
BASE_TARGET_COUNTS = {"supported": 3900, "held": 72, "failed": 6}
PINS = {
    "ci/run_offline_tests.py": "1b1f9823488dda1d66dc6bd12bd8e841f84c3e2add727ac254961b3a9e322d05",
    LEDGER: "4a4ef82f9da793c0a83cd58f6388991dd38f7a5f92947b2d089855b259af4e4a",
    TARGETS: "fd9bcba857c5d9816f44bbca0ac4c826c10527f64a7e6330468ee2fe814981d4",
    OLD_CREATOR: "ae4404c40238542c517822fe4424d14a0cbe93efef542bf42d359717fd4ba2e3",
    DOCS + "finite_source_resource_access_607.json": "83bdb0b1ab689e5fbf844467975ad9d279b6bba759cb3db3a18a11704715679c",
    DOCS + "source_display_titles_36.json": "c776b324f43a3e7560ef016f12b7a345bbb2f21cc016b74bd5298b8ed1e10781",
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def file_receipt(path, output):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(output)), "sha256": digest(raw), "bytes": len(raw)}


def inventory(repo):
    return {path.stem: digest(path.read_bytes()) for path in sorted((repo / "FGDC").glob("*.xml"))}


def reference(path):
    return {"manifest_path": str(path), "manifest_sha256": digest(path.read_bytes())}


def require_rights(payload):
    metadata, policy = payload["metadata"], payload["artifact_policy"]
    require(metadata["access_right"] == "restricted" and metadata["license"] == "", "Metadata rights changed")
    require(policy["rights_scope"] == "original_fgdc_xml" and policy["rights_source_xpath"] == "./metainfo/metuc"
            and policy["date_semantics"] == "source_metadata_date" and policy.get("license") in (None, "")
            and policy.get("rehosting_authority") is not None, "Artifact rights/date/restoration authority changed")


def creator_notes_preserved(before, after, result):
    """Remove only exact reviewed additions and the exact creator decision change."""
    restored = after
    for note in result["preservation_notes"]:
        require("\n" + note in restored, "Literal creator preservation note missing")
        restored = restored.replace("\n" + note, "", 1)
    old_lines = [line for line in before.splitlines() if line.startswith("Curator decision: ")]
    new_lines = [line for line in restored.splitlines() if line.startswith("Curator decision: ")]
    require(len(old_lines) == len(new_lines) == 1, "Expected one complete Curator decision line")
    old_decision = json.loads(old_lines[0].removeprefix("Curator decision: "))
    new_decision = json.loads(new_lines[0].removeprefix("Curator decision: "))
    new_decision["metadata"]["creators"] = old_decision["metadata"]["creators"]
    require(new_decision == old_decision, "Curator decision changed beyond reviewed creators")
    require(restored.replace(new_lines[0], old_lines[0], 1) == before, "Other complete source notes changed")


def project_targets(historical, integrated, integrated_sha, reviewed_at):
    """Update singleton statuses only, retaining frozen class evidence verbatim."""
    classes = historical["class_targets"]
    aliases = {sid for row in classes for sid in row["source_ids"]}
    require(len(classes) == 228 and len(aliases) == 456 and not CREATOR_IDS & aliases,
            "Creator delta must not include class members")
    require(Counter(row["source_semantic_status"] for row in classes) == {"supported": 204, "held": 24},
            "Historical class assessment counts differ")
    require(all(row["upload_eligible"] is False and row["remote_verified"] is False
                and row["publication_approved"] is False
                and row["production_reconciliation_status"] == "pending" for row in classes),
            "Historical class upload/reconciliation holds changed")
    prior_singletons = {row["record_target_id"]: row for row in historical["singleton_targets"]}
    require(len(prior_singletons) == len(historical["singleton_targets"]) == 3750,
            "Historical singleton coverage differs")
    proposed = copy.deepcopy(historical)
    changed = []
    for row in proposed["singleton_targets"]:
        sid = row["record_target_id"]
        if sid in CREATOR_IDS:
            require(row["source_semantic_status"] == "held", "Candidate singleton was not held")
            row["source_semantic_status"] = "supported"
            changed.append(sid)
        else:
            require(row == prior_singletons[sid], "Unselected singleton target changed")
    require(set(changed) == CREATOR_IDS, "Projected singleton delta differs from measured candidates")
    expected = [{"record_target_id": row["source_id"], "source_ids": [row["source_id"]],
                 "source_sha256": row["source_sha256"], "source_semantic_status": row["source_status"]}
                for row in integrated["records"] if row["source_id"] not in aliases]
    require(proposed["singleton_targets"] == expected, "Projected targets differ from the integrated source ledger")
    require(proposed["class_targets"] == classes and proposed["source_to_target"] == historical["source_to_target"],
            "Historical class rows, payload pins or member index changed")
    counts = Counter(row["source_semantic_status"] for row in proposed["singleton_targets"] + classes)
    expected_counts = {"supported": BASE_TARGET_COUNTS["supported"] + len(CREATOR_IDS),
                       "held": BASE_TARGET_COUNTS["held"] - len(CREATOR_IDS), "failed": 6}
    require(counts == expected_counts, "Unique target count delta differs")
    require(proposed["summary"]["unique_record_targets"] == sum(counts.values()) == 3978,
            "Unique target inventory size changed")
    proposed["summary"].update(source_supported_targets=counts["supported"],
                                source_held_targets=counts["held"], malformed_targets=counts["failed"])
    proposed.update(
        kind="offline_record_target_singleton_delta_projection",
        source_ledger_sha256=integrated_sha,
        projection_reviewed_at=reviewed_at,
        historical_record_target_index_sha256=PINS[TARGETS],
        historical_class_source_ledger_sha256=historical["source_ledger_sha256"],
        class_assessment_reviewed_at=historical["reviewed_at"],
        fresh_class_assessment_performed=False,
        class_artifacts_rebuilt=False,
        class_rows_source_index_and_payload_pins_unchanged=True,
        all_class_uploads_remain_held=True,
        projection_scope=("Only the measured creator singleton statuses are projected; all 228 class rows, "
                          "member-index rows and payload/contract pins retain their historical assessment. "
                          "This is neither fresh class QA nor production identity reconciliation."),
        measured_singleton_status_delta=[{"record_target_id": sid, "before": "held", "after": "supported"}
                                        for sid in sorted(changed)],
    )
    return proposed


def validate(repo, output, creator_manifest, reviewed_at, revision, helper_sha, guard):
    require(guard.phase == "tests" and guard.repo == repo and guard.fixture_root == output,
            "Installed offline guard does not cover this checkout/output")
    import scripts.logger
    from ci.run_offline_tests import source_bindings

    scripts.logger.get_logger = lambda *args, **kwargs: Mock()
    from scripts.artifact_contract import prepare_artifact
    from scripts.citation_creator_interpretation import validate_creator_interpretation
    from scripts.collection_qa import classify_collection
    from scripts.path_config import OutputPaths
    from scripts.upload_service import metadata_hash, prepare_metadata

    bindings_before = source_bindings(repo)
    for relative, expected in PINS.items():
        require(digest((repo / relative).read_bytes()) == expected, "Frozen input changed: " + relative)
    ledger_raw, target_raw = (repo / LEDGER).read_bytes(), (repo / TARGETS).read_bytes()
    ledger, historical_targets = json.loads(ledger_raw), json.loads(target_raw)
    rows_by_id = {row["source_id"]: row for row in ledger["records"]}
    require(len(rows_by_id) == len(ledger["records"]) == 4206, "Frozen source ledger coverage differs")
    require(Counter(row["source_status"] for row in ledger["records"]) == BASE_SOURCE_COUNTS,
            "Frozen source counts differ")
    require(len(SMOKE) == 10 and CREATOR_IDS <= SMOKE and CREATOR_IDS <= FULL,
            "Ten-source smoke and full candidate scope differ")
    require(not CREATOR_IDS & (SUPPORTED_CONTROLS | HELD_CONTROLS), "Candidate/control scopes overlap")
    require(all(rows_by_id[sid]["source_status"] == "held" for sid in CREATOR_IDS | HELD_CONTROLS)
            and all(rows_by_id[sid]["source_status"] == "supported" for sid in SUPPORTED_CONTROLS),
            "Baseline candidate/control state differs")
    old_creator = json.loads((repo / OLD_CREATOR).read_bytes())
    new_creator = json.loads(creator_manifest.read_bytes())
    old_ref, new_ref = reference(repo / OLD_CREATOR), reference(creator_manifest)
    old_cohorts = old_creator["cohorts"]
    require(sum(len(cohort["members"]) for cohort in old_cohorts) == PRIOR_CREATOR_COUNT,
            "Prior creator profile member count differs")
    require(new_creator["cohorts"][:len(old_cohorts)] == old_cohorts,
            "Prior creator cohort objects, members or review evidence changed")
    require(new_creator["prior_manifest_sha256"] == PINS[OLD_CREATOR]
            and new_creator["previous_cohort_count"] == len(old_cohorts), "New profile lineage differs")
    added = [member for cohort in new_creator["cohorts"][len(old_cohorts):] for member in cohort["members"]]
    all_members = [member for cohort in new_creator["cohorts"] for member in cohort["members"]]
    require(len(added) == len(CREATOR_IDS) and {member["source_id"] for member in added} == CREATOR_IDS
            and len(all_members) == PRIOR_CREATOR_COUNT + len(CREATOR_IDS)
            and len({member["source_id"] for member in all_members}) == len(all_members),
            "New creator manifest must extend exactly the finite candidate membership")
    original_hashes = inventory(repo)
    require(len(original_hashes) == 4206
            and original_hashes == {sid: row["source_sha256"] for sid, row in rows_by_id.items()},
            "All original source hashes must agree with the frozen ledger")
    require(all(original_hashes[member["source_id"]] == member["source_sha256"] for member in added),
            "A new cohort source hash differs from the actual original")
    aliases = {sid for row in historical_targets["class_targets"] for sid in row["source_ids"]}
    require(len(aliases) == 456 and not aliases & (SMOKE | FULL), "Measurement includes a protected alias source")
    # The manifest argument never authorizes itself: actual runtime validation
    # must accept every member using the runtime's independently pinned manifest.
    reviewed_results = {}
    for sid in sorted(CREATOR_IDS):
        root = ET.parse(repo / "FGDC" / (sid + ".xml")).getroot()
        reviewed_results[sid] = validate_creator_interpretation(new_ref, sid, original_hashes[sid], root, True)
    older, previous, today = (repo / "docs/readiness/2026-10-02",
                              repo / "docs/readiness/2026-10-03", repo / DOCS)
    common = {
        "authority_manifest": older / "rehosting_authority.json",
        "access_interpretation_manifest": older / "contact_source_interpretation.json",
        "creator_interpretation_manifest": older / "exxon_citation_interpretation.json",
        "contributor_access_interpretation_manifest": older / "contributor_source_interpretation.json",
        "collective_creator_interpretation_manifest": previous / "dfo_staff_citation_interpretation.json",
        "source_link_interpretation_manifest": previous / "historical_dataset_linkage_21.json",
        "source_scope_attestation_manifest": previous / "source_scope_reconciliation_904.json",
        "dataset_access_interpretation_manifest": today / "finite_source_resource_access_607.json",
        "source_title_interpretation_manifest": today / "source_display_titles_36.json",
    }
    option_bindings = {key: {"path": str(path.relative_to(repo)), "sha256": digest(path.read_bytes())}
                       for key, path in common.items()}
    batches, evidence_rows = [], []

    def measure(name, selected):
        directory = output / name
        source, destination = directory / "sources", directory / "prepared"
        source.mkdir(parents=True)
        for sid in sorted(selected):
            shutil.copyfile(repo / "FGDC" / (sid + ".xml"), source / (sid + ".xml"))
        reports, payloads, payload_hashes, submitted, artifacts, saved = {}, {}, {}, {}, {}, {}
        print(f"START {name}: {len(selected)} sources, same-output before/after/retry/withdrawal", flush=True)
        for phase in ("before", "after", "repeat", "withdrawn"):
            active = phase in ("after", "repeat")
            reports[phase] = classify_collection(source, destination, reviewed_at, **common,
                                                institution_creator_interpretation_manifest=(
                                                    creator_manifest if active else repo / OLD_CREATOR))
            paths = OutputPaths(str(destination), "sandbox")
            payloads[phase], payload_hashes[phase], submitted[phase], artifacts[phase], saved[phase] = {}, {}, {}, {}, {}
            rows = {row["source_id"]: row for row in reports[phase]["records"]}
            require(len(rows) == len(selected) and set(rows) == selected, "Bounded phase source coverage differs")
            supported = (selected & CREATOR_IDS if active else set()) | (selected & SUPPORTED_CONTROLS)
            require(reports[phase]["summary"]["source_status_counts"] == {
                "supported": len(supported), "held": len(selected - supported), "failed": 0,
            }, "Unexpected phase status counts: " + name + "/" + phase)
            for sid in sorted(selected):
                payload_path = Path(paths.zenodo_json_dir) / (sid + ".json")
                original_path = Path(paths.original_fgdc_dir) / (sid + ".xml")
                raw = payload_path.read_bytes()
                payload = json.loads(raw)
                payloads[phase][sid], payload_hashes[phase][sid] = payload, digest(raw)
                require_rights(payload)
                require(digest(original_path.read_bytes()) == digest((source / (sid + ".xml")).read_bytes())
                        == original_hashes[sid], "Original/prepared source bytes changed")
                prepared, _, prepared_source_sha = prepare_metadata(str(payload_path), paths)
                require(prepared_source_sha == original_hashes[sid], "Submission metadata source hash differs")
                submitted[phase][sid] = prepared
                artifacts[phase][sid] = prepare_artifact(payload, original_path)
                row = rows[sid]
                require(row["source_sha256"] == original_hashes[sid]
                        and row["prepared_payload_sha256"] == digest(raw), "Report source/payload binding differs")
                if "metadata_sha256" in row:
                    require(row["metadata_sha256"] == metadata_hash(prepared), "Actual submission metadata hash differs")
                require(row["source_status"] == ("supported" if sid in supported else "held")
                        and row["remote_verified"] is False and row["publication_approved"] is False
                        and row["rehosting_authority"] == "USER_ATTESTED", "Source/release/restoration state differs")
                if active and sid in CREATOR_IDS:
                    require(row["creator_interpretation"] == "source_primary_citation_attribution",
                            "New creator source provenance differs")
            snapshot = directory / (phase + "_snapshot")
            shutil.copytree(destination, snapshot)
            snapshot_paths = OutputPaths(str(snapshot), "sandbox")
            for sid in sorted(selected):
                saved[phase][sid] = {
                    "payload": file_receipt(Path(snapshot_paths.zenodo_json_dir) / (sid + ".json"), output),
                    "prepared_xml": file_receipt(Path(snapshot_paths.original_fgdc_dir) / (sid + ".xml"), output),
                    "prepared_metadata_sha256": metadata_hash(submitted[phase][sid]),
                    "prepared_metadata_canonical_sha256": digest(canonical(submitted[phase][sid])),
                    "artifact_contract_sha256": artifacts[phase][sid]["sha256"],
                }
            require(not any(guard.counts["tests"].values()), "Unexpected guard event during bounded measurement")
        require(reports["after"] == reports["repeat"] and payload_hashes["after"] == payload_hashes["repeat"]
                and submitted["after"] == submitted["repeat"], "Unchanged same-output retry differs")
        require(reports["before"] == reports["withdrawn"] and payload_hashes["before"] == payload_hashes["withdrawn"]
                and submitted["before"] == submitted["withdrawn"], "Same-output withdrawal did not restore exact baseline")
        for first, second in (("after", "repeat"), ("before", "withdrawn")):
            require((directory / (first + "_snapshot/classification.json")).read_bytes() ==
                    (directory / (second + "_snapshot/classification.json")).read_bytes(),
                    "Retained classification report bytes differ")
        before_rows = {row["source_id"]: row for row in reports["before"]["records"]}
        after_rows = {row["source_id"]: row for row in reports["after"]["records"]}
        for sid in sorted(selected):
            before, after = payloads["before"][sid], payloads["after"][sid]
            stripped = copy.deepcopy(after)
            root = ET.parse(repo / "FGDC" / (sid + ".xml")).getroot()
            permitted, upgrades = [], []
            if sid in CREATOR_IDS:
                result = reviewed_results[sid]
                require(after["metadata"]["creators"] == result["creators"]
                        and before["metadata"]["creators"] != after["metadata"]["creators"],
                        "Actual metadata must contain the complete reviewed creator change")
                creator_notes_preserved(before["metadata"]["notes"], after["metadata"]["notes"], result)
                require({key: value for key, value in before["metadata"].items() if key not in ("creators", "notes")} ==
                        {key: value for key, value in after["metadata"].items() if key not in ("creators", "notes")},
                        "Raw metadata changed beyond exact creators and preservation notes")
                require(stripped["artifact_policy"].pop("creator_interpretation") == new_ref,
                        "Exact new creator policy reference differs")
                stripped["metadata"] = copy.deepcopy(before["metadata"])
                permitted = ["creators", "notes"]
            else:
                require(before["metadata"] == after["metadata"], "Complete control raw metadata changed")
                if before["artifact_policy"].get("creator_interpretation") == old_ref:
                    require(stripped["artifact_policy"].get("creator_interpretation") == new_ref,
                            "Prior-supported creator profile-reference upgrade differs")
                    old_result = validate_creator_interpretation(old_ref, sid, original_hashes[sid], root, True)
                    new_result = validate_creator_interpretation(new_ref, sid, original_hashes[sid], root, True)
                    require(old_result == new_result, "Prior creator interpretation content changed")
                    stripped["artifact_policy"]["creator_interpretation"] = copy.deepcopy(old_ref)
                    upgrades.append({"policy_key": "creator_interpretation", "before": old_ref,
                                     "after": new_ref, "unchanged_member_validation_result": True})
                comparable = copy.deepcopy(after_rows[sid])
                comparable["prepared_payload_sha256"] = before_rows[sid]["prepared_payload_sha256"]
                require(("metadata_sha256" in comparable) == ("metadata_sha256" in before_rows[sid]),
                        "Control submission hash presence changed")
                if "metadata_sha256" in comparable:
                    comparable["metadata_sha256"] = before_rows[sid]["metadata_sha256"]
                require(comparable == before_rows[sid], "Control assessment changed beyond verified derived hashes")
                # The supported control's source metadata is exact; the changed
                # profile pin may change only its artifact-contract note suffix.
                old_prepared, new_prepared = submitted["before"][sid], submitted["after"][sid]
                require({key: value for key, value in old_prepared.items() if key != "notes"} ==
                        {key: value for key, value in new_prepared.items() if key != "notes"},
                        "Control submission metadata changed beyond its contract note")
                bases = []
                for phase in ("before", "after"):
                    suffix = ("\n\nDeposited object: original FGDC XML metadata artifact; underlying research data are not included. "
                              "Artifact contract SHA-256: " + artifacts[phase][sid]["sha256"])
                    notes = submitted[phase][sid]["notes"]
                    require(notes.endswith(suffix), "Control exact artifact note missing")
                    bases.append(notes[:-len(suffix)])
                require(bases[0] == bases[1], "Control submission notes changed beyond the exact contract hash")
            require(stripped == before, "Complete payload changed beyond reviewed creators/notes and exact policy references")
            for phase in saved:
                require(digest((output / saved[phase][sid]["payload"]["path"]).read_bytes()) == payload_hashes[phase][sid]
                        and digest((output / saved[phase][sid]["prepared_xml"]["path"]).read_bytes()) == original_hashes[sid],
                        "Retained phase payload or original differs")
            evidence_rows.append({
                "batch": name, "source_id": sid, "source_sha256": original_hashes[sid],
                "axis": "creator" if sid in CREATOR_IDS else "control",
                "before_status": before_rows[sid]["source_status"], "after_status": after_rows[sid]["source_status"],
                "before_metadata_sha256": digest(canonical(before["metadata"])),
                "after_metadata_sha256": digest(canonical(after["metadata"])),
                "before_notes_sha256": digest(before["metadata"]["notes"].encode()),
                "after_notes_sha256": digest(after["metadata"]["notes"].encode()),
                "permitted_metadata_changes": permitted,
                "complete_raw_metadata_unchanged": before["metadata"] == after["metadata"],
                "validated_prior_profile_reference_upgrades": upgrades,
                "saved_phases": {phase: saved[phase][sid] for phase in saved},
            })
        batches.append({
            "name": name, "source_ids": sorted(selected),
            "phase_counts": {phase: reports[phase]["summary"]["source_status_counts"] for phase in reports},
            "profile_sha256": {phase: reports[phase]["profile_sha256"] for phase in reports},
            "classification_snapshots": {phase: file_receipt(directory / (phase + "_snapshot/classification.json"), output)
                                         for phase in reports},
            "same_live_output_for_all_four_phases": True,
            "snapshot_semantics": "Each phase directory copied immediately; embedded paths retain the same live prepared path, without normalization.",
            "unchanged_retry_report_payload_and_submission_bytes_equal": True,
            "withdrawal_restores_exact_baseline_report_payload_and_submission": True,
        })
        print(f"PASS {name}: exact bounded delta, same-output retry and withdrawal", flush=True)
        return reports, payload_hashes

    smoke_reports, smoke_hashes = measure("smoke10", SMOKE)
    full_reports, full_hashes = measure("candidates", FULL)
    for phase in full_reports:
        smoke_rows = {row["source_id"]: row for row in smoke_reports[phase]["records"]}
        require(all(row == smoke_rows[row["source_id"]] for row in full_reports[phase]["records"]
                    if row["source_id"] in smoke_rows),
                "Smoke/full candidate source rows differ")
        require(all(value == smoke_hashes[phase][sid] for sid, value in full_hashes[phase].items()
                    if sid in smoke_hashes[phase]),
                "Smoke/full candidate payload bytes differ")
    proposed_rows = copy.deepcopy(ledger["records"])
    for row in proposed_rows:
        if row["source_id"] in CREATOR_IDS:
            row.update(source_status="supported", evidence="measured_finite_creator_credit_delta")
        else:
            require(row == rows_by_id[row["source_id"]], "An unselected source ledger object changed")
    expected_counts = {"supported": BASE_SOURCE_COUNTS["supported"] + len(CREATOR_IDS),
                       "held": BASE_SOURCE_COUNTS["held"] - len(CREATOR_IDS), "failed": 6}
    require(Counter(row["source_status"] for row in proposed_rows) == expected_counts
            and sum(row != rows_by_id[row["source_id"]] for row in proposed_rows) == len(CREATOR_IDS),
            "Integrated source delta differs from the measured candidate set")
    require(all(row["source_status"] == "held" for row in proposed_rows if row["source_id"] in aliases | HELD_CONTROLS),
            "A protected alias or control source hold changed")
    integrated = copy.deepcopy(ledger)
    integrated.update(
        scope="Frozen 4206-source ledger plus the finite measured creator-only delta; not fresh full-corpus QA or release.",
        records=proposed_rows,
        integrated_counts={"supported": expected_counts["supported"], "held": expected_counts["held"], "malformed": 6},
        promoted_source_count=ledger["promoted_source_count"] + len(CREATOR_IDS),
        per_source_status_sha256=digest(canonical(proposed_rows)),
        measured_creator_delta_source_ids=sorted(CREATOR_IDS),
        prior_source_ledger_sha256=PINS[LEDGER],
        active_creator_manifest={"path": str(creator_manifest.relative_to(repo)), "sha256": new_ref["manifest_sha256"]},
        all_unselected_prior_status_objects_unchanged=True,
        unselected_prior_status_objects_count=4206 - len(CREATOR_IDS),
        all4206_original_xml_sha256_verified_before_and_after=True,
        all456_alias_identities_still_held=True,
        provider_requests=0, remote_verification_or_publication_approval_added=False,
    )
    integrated_path = output / "integrated_source_status.json"
    write_json(integrated_path, integrated)
    projected_targets = project_targets(historical_targets, integrated, digest(integrated_path.read_bytes()), reviewed_at)
    projected_path = output / "record_target_delta_projection.json"
    write_json(projected_path, projected_targets)
    require(original_hashes == inventory(repo), "An original XML file changed during measurement")
    require(bindings_before == source_bindings(repo), "Runtime/test/contract bindings changed during measurement")
    require((repo / LEDGER).read_bytes() == ledger_raw and (repo / TARGETS).read_bytes() == target_raw,
            "A frozen source ledger or historical target index changed")
    actual_inputs = dict(guard.input_hashes)
    # The complete second inventory above already rechecked every original.
    # Recheck other actual inputs without a redundant third full XML scan.
    require(all((original_hashes[Path(relative).stem] == sha if relative.startswith("FGDC/")
                 else digest((repo / relative).read_bytes()) == sha)
                for relative, sha in actual_inputs.items()),
            "An actual runtime/profile/evidence input changed during measurement")
    require(not any(guard.counts["tests"].values()) and not guard.blocked_call_sites, "Unexpected offline guard event")
    result = {
        "schema_version": 1, "status": "MEASURED_FINITE_CREATOR_DELTA_WITH_HISTORICAL_CLASS_PROJECTION",
        "base_main": BASE_MAIN, "actual_checkout_revision": revision, "reviewed_at": reviewed_at,
        "helper_sha256": helper_sha, "pinned_inputs_sha256": PINS,
        "new_creator_manifest": {"path": str(creator_manifest.relative_to(repo)), "sha256": new_ref["manifest_sha256"]},
        "new_manifest_accepted_by_runtime_validation_for_every_candidate": True,
        "all415_prior_creator_cohort_objects_verbatim": True,
        "profile_options": option_bindings,
        "actual_repository_inputs_sha256": actual_inputs, "actual_repository_inputs_unchanged": True,
        "source_bindings_unchanged": True, "source_bindings_canonical_sha256": digest(canonical(bindings_before)),
        "original_xml_inventory_sha256": digest(canonical(original_hashes)),
        "all4206_original_xml_sha256_verified_before_and_after": True,
        "source_file_counts_before": BASE_SOURCE_COUNTS, "source_file_counts_after": expected_counts,
        "measured_creator_source_ids": sorted(CREATOR_IDS), "measured_promotions": len(CREATOR_IDS),
        "all_unselected_source_ledger_rows_exact": True, "unselected_source_row_count": 4206 - len(CREATOR_IDS),
        "integrated_source_ledger": file_receipt(integrated_path, output),
        "record_target_projection": file_receipt(projected_path, output),
        "unique_record_target_summary": projected_targets["summary"],
        "historical_class_rows_canonical_sha256": digest(canonical(historical_targets["class_targets"])),
        "historical_source_to_target_index_canonical_sha256": digest(canonical(historical_targets["source_to_target"])),
        "class_rows_source_index_payload_and_contract_pins_unchanged": True,
        "fresh_class_assessment_performed": False, "class_artifacts_rebuilt": False,
        "all_class_uploads_remain_held": True,
        "class_evidence_limit": "Class artifact byte hashes are retained from the pinned historical index; no class payload regeneration, revalidation, new provider crosswalk or fresh class assessment is claimed.",
        "guard": {"implementation": "ci.run_offline_tests.OfflineGuard with actual-public-input hashing",
                  "environment_cleared_dummy_credentials_only": True, "blocks": guard.counts,
                  "unexpected_call_sites": guard.blocked_call_sites,
                  "in_process_public_revision_queries": guard.metadata_queries,
                  "limitation": "Accidental-I/O guard reused from CI; not a hostile-code sandbox."},
        "batches": batches, "rows": evidence_rows,
        "provider_requests": 0, "new_remote_verifications_or_publication_approvals": 0,
    }
    receipt = output / "creator_delta_validation.json"
    write_json(receipt, result)
    require(not any(guard.counts["tests"].values()), "Unexpected guard event while writing evidence")
    print(json.dumps({"receipt": str(receipt), "receipt_sha256": digest(receipt.read_bytes()),
                      "source_counts": expected_counts, "target_summary": projected_targets["summary"],
                      "unexpected_guard_events": guard.counts["tests"]}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--creator-manifest", type=Path, required=True)
    parser.add_argument("--reviewed-at", required=True)
    args = parser.parse_args()
    os.environ.clear()
    sys.dont_write_bytecode = True
    repo, output, creator_manifest = args.repo.resolve(), args.output.resolve(), args.creator_manifest.resolve()
    reviewed = datetime.fromisoformat(args.reviewed_at.replace("Z", "+00:00"))
    require(reviewed.utcoffset() is not None and reviewed <= datetime.now(timezone.utc),
            "Use an explicit timezone-aware nonfuture assessment time")
    require(output.is_relative_to(Path("/tmp").resolve()) and output != Path("/tmp").resolve()
            and not output.is_relative_to(repo), "Use a fresh /tmp output outside the checkout")
    require(not output.exists() and output.parent.is_dir(), "Output must be new with an existing parent")
    require(creator_manifest.is_relative_to(repo), "Reviewed creator manifest must be a public repository input")
    require(digest((repo / "ci/run_offline_tests.py").read_bytes()) == PINS["ci/run_offline_tests.py"],
            "Pinned offline guard implementation changed")
    helper_sha = digest(Path(__file__).read_bytes())
    sys.path.insert(0, str(repo))
    # Only the stdlib-based guard module may load before the guard is installed.
    from ci.run_offline_tests import OfflineGuard, checkout_revision, clean_environment

    revision = checkout_revision(repo)
    os.chdir(repo)
    os.environ.update(clean_environment(output))
    tempfile.tempdir = str(output)

    class ReadBoundGuard(OfflineGuard):
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
    guard.library_files.add(Path(__file__).resolve())
    guard.install()
    guard.self_check()
    output.mkdir()
    validate(repo, output, creator_manifest, args.reviewed_at, revision, helper_sha, guard)


if __name__ == "__main__":
    main()
