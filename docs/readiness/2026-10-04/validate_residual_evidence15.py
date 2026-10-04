"""Measure eleven resource, three creator and one editorial correction offline.

Ten exact sources are measured first, then all fifteen candidates and seven
controls. All original hashes and unselected ledger rows remain frozen. This
bounded delta is not a fresh full-corpus assessment or provider release approval.
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

BASE_MAIN = "05d699e93572345c0591ca932a03089a9dd9ba9c"
LEDGER_SHA = "4e24fbe4859644d7fe1ddfbd87bf207df8dd6f4f8a9ea288713a1fb9a15aed7b"
OLD_RESOURCE_SHA = "4719b46cfe46a2b950b3abc695fd8778ffc7bd3041e5bb0bae253c613c55ec2c"
NEW_RESOURCE_SHA = "83bdb0b1ab689e5fbf844467975ad9d279b6bba759cb3db3a18a11704715679c"
OLD_CREATOR_SHA = "c6aa4f9c2e4c80ea565b3a92d66d0e066b12f77534bd23feb92807bd18894ee3"
NEW_CREATOR_SHA = "ae4404c40238542c517822fe4424d14a0cbe93efef542bf42d359717fd4ba2e3"
OLD_TITLE_SHA = "db24d027d65b9e4392ede772172b04ada1fca4d14e576df70998d759303fe5c5"
NEW_TITLE_SHA = "c776b324f43a3e7560ef016f12b7a345bbb2f21cc016b74bd5298b8ed1e10781"
RESOURCE_IDS = {"FGDC-" + str(i) for i in (53, 563, 564, 565, 627, 754, 755, 757, 760, 2086, 2234)}
CREATOR_IDS = {"FGDC-2552", "FGDC-3954", "FGDC-3956"}
TITLE_IDS = {"FGDC-233"}
IDS = RESOURCE_IDS | CREATOR_IDS | TITLE_IDS
HELD_CONTROLS = {"FGDC-" + str(i) for i in (288, 909, 1318, 1770, 1994, 4063)}
SUPPORTED_CONTROLS = {"FGDC-621"}
CONTROLS = HELD_CONTROLS | SUPPORTED_CONTROLS
SMOKE = TITLE_IDS | CREATOR_IDS | {"FGDC-" + str(i) for i in (53, 563, 627, 754, 2086, 2234)}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def reference(path):
    return {"manifest_path": str(path), "manifest_sha256": digest(path.read_bytes())}


def inventory(repo):
    return {path.stem: digest(path.read_bytes()) for path in sorted((repo / "FGDC").glob("*.xml"))}


def require_rights(payload):
    metadata, policy = payload["metadata"], payload["artifact_policy"]
    require(metadata["access_right"] == "restricted" and metadata["license"] == "", "Metadata rights changed")
    require(policy["rights_scope"] == "original_fgdc_xml", "Artifact rights scope changed")
    require(policy["rights_source_xpath"] == "./metainfo/metuc", "Artifact rights source changed")
    require(policy["date_semantics"] == "source_metadata_date", "Artifact date semantics changed")
    require(policy.get("license") in ("", None), "A policy license was added")
    require(policy.get("rehosting_authority") is not None, "Separate restoration authority missing")


def creator_notes_preserved(before, after, result):
    """Compare all notes after removing only exact reviewed creator additions."""
    restored = after
    for note in result["preservation_notes"]:
        require("\n" + note in restored, "Literal creator source/context preservation note missing")
        restored = restored.replace("\n" + note, "", 1)
    old_lines = [line for line in before.splitlines() if line.startswith("Curator decision: ")]
    new_lines = [line for line in restored.splitlines() if line.startswith("Curator decision: ")]
    require(len(old_lines) == len(new_lines) == 1, "Expected one complete Curator decision line")
    old_decision = json.loads(old_lines[0].removeprefix("Curator decision: "))
    new_decision = json.loads(new_lines[0].removeprefix("Curator decision: "))
    new_decision["metadata"]["creators"] = old_decision["metadata"]["creators"]
    require(new_decision == old_decision, "Curator decision changed beyond reviewed creator objects")
    require(restored.replace(new_lines[0], old_lines[0], 1) == before, "Other complete source notes changed")


def validate(repo, output, reviewed_at, guard):
    """Called only after the complete OfflineGuard has been installed."""
    require(guard.phase == "tests" and guard.repo == repo and guard.fixture_root == output,
            "Installed offline guard does not cover this exact checkout/output")
    # Import scripts only inside the guard, with a logger that cannot create repo logs.
    import scripts.logger
    from ci.run_offline_tests import source_bindings

    scripts.logger.get_logger = lambda *args, **kwargs: Mock()
    from scripts import dataset_access_interpretation as access_runtime
    from scripts import source_title_interpretation as title_runtime
    from scripts.citation_creator_interpretation import validate_creator_interpretation
    from scripts.collection_qa import classify_collection
    from scripts.path_config import OutputPaths
    from scripts.upload_service import metadata_hash, prepare_metadata

    bindings_before = source_bindings(repo)
    older = repo / "docs/readiness/2026-10-02"
    previous = repo / "docs/readiness/2026-10-03"
    today = repo / "docs/readiness/2026-10-04"
    ledger_path = today / "residual_resource4_integrated_source_status.json"
    paths = {
        "old_resource": today / "finite_source_resource_access_596.json",
        "new_resource": today / "finite_source_resource_access_607.json",
        "old_creator": today / "source_citation_credits_412.json",
        "new_creator": today / "source_citation_credits_415.json",
        "old_title": previous / "source_display_titles_35.json",
        "new_title": today / "source_display_titles_36.json",
    }
    pins = {
        "old_resource": OLD_RESOURCE_SHA, "new_resource": NEW_RESOURCE_SHA,
        "old_creator": OLD_CREATOR_SHA, "new_creator": NEW_CREATOR_SHA,
        "old_title": OLD_TITLE_SHA, "new_title": NEW_TITLE_SHA,
    }
    require(digest(ledger_path.read_bytes()) == LEDGER_SHA, "Frozen baseline ledger changed")
    for key, path in paths.items():
        require(len(pins[key]) == 64 and digest(path.read_bytes()) == pins[key], "Reviewed profile pin differs: " + key)
    require(access_runtime.SENSITIVE_RESOURCE11_MANIFEST_SHA256 == NEW_RESOURCE_SHA, "Runtime resource607 pin differs")
    require(title_runtime.TITLE233_MANIFEST_SHA256 == NEW_TITLE_SHA, "Runtime title36 pin differs")
    profiles = {key: json.loads(path.read_bytes()) for key, path in paths.items()}
    refs = {key: reference(path) for key, path in paths.items()}
    ledger = json.loads(ledger_path.read_bytes())
    rows_by_id = {row["source_id"]: row for row in ledger["records"]}
    require(len(rows_by_id) == len(ledger["records"]) == 4206, "Ledger inventory differs")
    before_counts = Counter(row["source_status"] for row in ledger["records"])
    require(before_counts == {"supported": 3681, "held": 519, "failed": 6}, "Baseline counts differ")
    require(len(RESOURCE_IDS) == 11 and len(CREATOR_IDS) == 3 and len(IDS) == 15, "Candidate axes overlap")
    require(len(CONTROLS) == 7 and not IDS & CONTROLS, "Control scope overlaps")
    require(len(SMOKE) == 10 and SMOKE <= IDS, "Smoke scope differs or exceeds ten")

    old_resource, new_resource = profiles["old_resource"], profiles["new_resource"]
    require(len(new_resource["members"]) == 607 and new_resource["members"][:596] == old_resource["members"],
            "Prior596 resource members changed")
    resource_additions = new_resource["members"][596:]
    require(len(resource_additions) == 11 and {member["source_id"] for member in resource_additions} == RESOURCE_IDS,
            "Exact resource11 membership differs")
    require(new_resource["source_contexts"] == old_resource["source_contexts"], "Prior resource source contexts changed")
    require(set(new_resource["acquisition_contexts"]) - set(old_resource["acquisition_contexts"]) == RESOURCE_IDS,
            "Resource acquisition context extension differs")
    require(all(new_resource["acquisition_contexts"][sid] == value
                for sid, value in old_resource["acquisition_contexts"].items()), "Prior acquisition context changed")
    require(all(new_resource[key] == value for key, value in old_resource.items() if key.endswith("_review")),
            "Prior resource review objects or times changed")
    require(new_resource["sensitive_resource11_review"]["members"] == resource_additions, "New review membership differs")

    old_creator, new_creator = profiles["old_creator"], profiles["new_creator"]
    old_cohort_count = len(old_creator["cohorts"])
    require(sum(len(cohort["members"]) for cohort in old_creator["cohorts"]) == 412, "Prior creator412 count differs")
    require(new_creator["cohorts"][:old_cohort_count] == old_creator["cohorts"], "Prior412 creator cohort objects changed")
    creator_additions = [member for cohort in new_creator["cohorts"][old_cohort_count:] for member in cohort["members"]]
    require(sum(len(cohort["members"]) for cohort in new_creator["cohorts"]) == 415, "New creator415 count differs")
    require(len(creator_additions) == 3 and {member["source_id"] for member in creator_additions} == CREATOR_IDS,
            "Exact creator3 membership differs")
    old_title, new_title = profiles["old_title"], profiles["new_title"]
    require(len(new_title["members"]) == 36 and new_title["members"][:35] == old_title["members"],
            "Prior35 exact title member objects changed")
    title_member = new_title["members"][-1]
    require(title_member["source_id"] == "FGDC-233", "Editorial title extension differs")
    require(len(title_member["display_title"]) == 250, "Editorial title length differs")

    original_hashes = inventory(repo)
    require(len(original_hashes) == 4206, "Original count differs")
    require(original_hashes == {sid: row["source_sha256"] for sid, row in rows_by_id.items()},
            "Original4206 hashes differ from baseline")
    for member in resource_additions + creator_additions + [title_member]:
        require(original_hashes[member["source_id"]] == member["source_sha256"], "New source binding differs")
    duplicate_hashes = {sha for sha, count in Counter(original_hashes.values()).items() if count > 1}
    aliases = {sid for sid, sha in original_hashes.items() if sha in duplicate_hashes}
    historical_exceptions = set(ledger["held31_exception_ids"])
    current_exceptions = historical_exceptions - RESOURCE_IDS
    require(len(historical_exceptions) == 31 and RESOURCE_IDS <= historical_exceptions and len(current_exceptions) == 20,
            "Historical31/current20 exception membership differs")
    protected = aliases | current_exceptions | HELD_CONTROLS
    require(len(aliases) == 456 and not IDS & protected, "Alias/protected membership overlap")
    require(all(rows_by_id[sid]["source_status"] == "held" for sid in IDS | protected), "Baseline candidate/hold differs")
    require(all(rows_by_id[sid]["source_status"] == "supported" for sid in SUPPORTED_CONTROLS),
            "Prior supported control changed")

    common = {
        "authority_manifest": older / "rehosting_authority.json",
        "access_interpretation_manifest": older / "contact_source_interpretation.json",
        "creator_interpretation_manifest": older / "exxon_citation_interpretation.json",
        "contributor_access_interpretation_manifest": older / "contributor_source_interpretation.json",
        "collective_creator_interpretation_manifest": previous / "dfo_staff_citation_interpretation.json",
        "source_link_interpretation_manifest": previous / "historical_dataset_linkage_21.json",
        "source_scope_attestation_manifest": previous / "source_scope_reconciliation_904.json",
    }
    batches, evidence_rows = [], []

    def normalize_prior_refs(policy, baseline_policy, sid, root):
        """Replace only validated, identical prior-member profile references."""
        changes = []
        for key, axis in (("dataset_access_interpretation", "resource"),
                          ("creator_interpretation", "creator"),
                          ("source_title_interpretation", "title")):
            if baseline_policy.get(key) != refs["old_" + axis]:
                continue
            require(policy.get(key) == refs["new_" + axis], "Existing exact profile reference upgrade differs")
            old_ref, new_ref = refs["old_" + axis], refs["new_" + axis]
            if axis == "resource":
                before = access_runtime.validate_dataset_access_interpretation(old_ref, sid, original_hashes[sid], root, reviewed_at)
                after = access_runtime.validate_dataset_access_interpretation(new_ref, sid, original_hashes[sid], root, reviewed_at)
            elif axis == "creator":
                before = validate_creator_interpretation(old_ref, sid, original_hashes[sid], root, True)
                after = validate_creator_interpretation(new_ref, sid, original_hashes[sid], root, True)
            else:
                before = title_runtime.validate_source_title_interpretation(old_ref, sid, original_hashes[sid], root)
                after = title_runtime.validate_source_title_interpretation(new_ref, sid, original_hashes[sid], root)
            require(before == after, "Previously reviewed interpretation content changed")
            policy[key] = copy.deepcopy(old_ref)
            changes.append({"policy_key": key, "before": old_ref, "after": new_ref,
                            "unchanged_member_validation_result": True})
        return changes

    def measure(name, selected, retain_rows):
        directory = output / name
        source = directory / "sources"
        source.mkdir(parents=True)
        for sid in sorted(selected):
            shutil.copyfile(repo / "FGDC" / (sid + ".xml"), source / (sid + ".xml"))
        reports, payloads, payload_hashes, saved = {}, {}, {}, {}
        for phase in ("before", "after", "repeat", "withdrawn"):
            active = phase in ("after", "repeat")
            destination = directory / ("after" if phase == "repeat" else phase)
            prefix = "new_" if active else "old_"
            reports[phase] = classify_collection(
                source, destination, reviewed_at, **common,
                dataset_access_interpretation_manifest=paths[prefix + "resource"],
                institution_creator_interpretation_manifest=paths[prefix + "creator"],
                source_title_interpretation_manifest=paths[prefix + "title"],
            )
            output_paths = OutputPaths(str(destination), "sandbox")
            payloads[phase], payload_hashes[phase], saved[phase] = {}, {}, {}
            for sid in sorted(selected):
                payload_path = Path(output_paths.zenodo_json_dir) / (sid + ".json")
                original_path = Path(output_paths.original_fgdc_dir) / (sid + ".xml")
                raw = payload_path.read_bytes()
                payloads[phase][sid], payload_hashes[phase][sid] = json.loads(raw), digest(raw)
                require_rights(payloads[phase][sid])
                require(digest((source / (sid + ".xml")).read_bytes()) == original_hashes[sid], "Input XML copy changed")
                require(digest(original_path.read_bytes()) == original_hashes[sid], "Prepared XML copy changed")
                saved[phase][sid] = {
                    "payload_path": str(payload_path.relative_to(output)),
                    "payload_sha256": digest(raw),
                    "prepared_xml_path": str(original_path.relative_to(output)),
                    "prepared_xml_sha256": original_hashes[sid],
                }
            supported = (selected & IDS if active else set()) | (selected & SUPPORTED_CONTROLS)
            require(reports[phase]["summary"]["source_status_counts"] == {
                "supported": len(supported), "held": len(selected - supported), "failed": 0,
            }, "Unexpected bounded phase counts: " + name + "/" + phase)
            require({row["source_id"] for row in reports[phase]["records"]} == selected, "Report scope differs")
            for row in reports[phase]["records"]:
                sid = row["source_id"]
                require(row["source_sha256"] == original_hashes[sid], "Report source hash changed")
                require(row["prepared_payload_sha256"] == payload_hashes[phase][sid], "Reported payload binding differs")
                if "metadata_sha256" in row:
                    submitted = prepare_metadata(str(Path(output_paths.zenodo_json_dir) / (sid + ".json")), output_paths)[0]
                    require(metadata_hash(submitted) == row["metadata_sha256"], "Reported submission metadata hash differs")
                require(not row["remote_verified"] and not row["publication_approved"], "Release/remote authority added")
                require(row["rehosting_authority"] == "USER_ATTESTED", "Separate restoration authority changed")
                require(row["source_status"] == ("supported" if sid in supported else "held"), "Unexpected per-source status")
                if active and sid in RESOURCE_IDS:
                    require(row["dataset_access_interpretation"] == "REVIEWER_RECONCILED", "Resource provenance differs")
                if active and sid in CREATOR_IDS:
                    require(row["creator_interpretation"] == "source_primary_citation_attribution", "Creator provenance differs")
                if active and sid in TITLE_IDS:
                    require(row["source_title_interpretation"] == "SOURCE_BACKED", "Title provenance differs")
            if phase == "after":
                # Preserve the first after bytes before exercising the same-directory cache.
                shutil.copytree(destination, directory / "after_snapshot")
                for item in saved[phase].values():
                    for key in ("payload_path", "prepared_xml_path"):
                        item[key] = item[key].replace(name + "/after/", name + "/after_snapshot/", 1)
        require(reports["after"] == reports["repeat"], "Unchanged repeat report differs")
        require(reports["before"] == reports["withdrawn"], "Withdrawal report differs from baseline")
        require(payload_hashes["after"] == payload_hashes["repeat"], "Unchanged repeat payload bytes differ")
        require(payload_hashes["before"] == payload_hashes["withdrawn"], "Withdrawal payload bytes differ")
        require((directory / "after_snapshot/classification.json").read_bytes()
                == (directory / "after/classification.json").read_bytes(), "Saved repeat classification bytes differ")
        before_rows = {row["source_id"]: row for row in reports["before"]["records"]}
        after_rows = {row["source_id"]: row for row in reports["after"]["records"]}
        for sid in sorted(selected):
            before, after = payloads["before"][sid], payloads["after"][sid]
            root = ET.parse(repo / "FGDC" / (sid + ".xml")).getroot()
            stripped = copy.deepcopy(after)
            permitted = []
            if sid in RESOURCE_IDS:
                require(stripped["artifact_policy"].pop("dataset_access_interpretation") == refs["new_resource"],
                        "New resource reference differs")
                require(before["metadata"] == after["metadata"], "Complete resource metadata changed")
            elif sid in CREATOR_IDS:
                result = validate_creator_interpretation(refs["new_creator"], sid, original_hashes[sid], root, True)
                require(after["metadata"]["creators"] == result["creators"], "Complete reviewed creator objects differ")
                require(before["metadata"]["creators"] != after["metadata"]["creators"], "Creator change not measured")
                creator_notes_preserved(before["metadata"]["notes"], after["metadata"]["notes"], result)
                require({key: value for key, value in before["metadata"].items() if key not in ("creators", "notes")}
                        == {key: value for key, value in after["metadata"].items() if key not in ("creators", "notes")},
                        "Creator metadata changed beyond exact creators and preserved notes")
                require(stripped["artifact_policy"].pop("creator_interpretation") == refs["new_creator"],
                        "New creator reference differs")
                stripped["metadata"] = copy.deepcopy(before["metadata"])
                permitted = ["creators", "notes"]
            elif sid in TITLE_IDS:
                require(digest(canonical(before["metadata"])) == title_member["metadata_before_sha256"],
                        "Complete pre-editorial metadata differs from reviewed member")
                require(digest(canonical(after["metadata"])) == title_member["metadata_after_sha256"],
                        "Complete editorial metadata differs from reviewed member")
                expected = copy.deepcopy(before["metadata"])
                expected["title"] = title_member["display_title"]
                expected["notes"] += "\n\n" + title_member["preservation_note"]
                require(after["metadata"] == expected, "Editorial selection changed other complete metadata")
                require(stripped["artifact_policy"].pop("source_title_interpretation") == refs["new_title"],
                        "New exact editorial title reference differs")
                stripped["metadata"] = copy.deepcopy(before["metadata"])
                permitted = ["title", "notes"]
            else:
                require(before["metadata"] == after["metadata"], "Complete control metadata changed")
                comparable_row = copy.deepcopy(after_rows[sid])
                comparable_row["prepared_payload_sha256"] = before_rows[sid]["prepared_payload_sha256"]
                # A validated prior-profile reference upgrade changes the artifact
                # fingerprint in submission notes; complete raw metadata is exact.
                require(("metadata_sha256" in comparable_row) == ("metadata_sha256" in before_rows[sid]),
                        "Control submission-hash presence changed")
                if "metadata_sha256" in comparable_row:
                    comparable_row["metadata_sha256"] = before_rows[sid]["metadata_sha256"]
                require(comparable_row == before_rows[sid], "Control assessment changed beyond verified derived hashes")
            upgrades = normalize_prior_refs(stripped["artifact_policy"], before["artifact_policy"], sid, root)
            require(stripped == before, "Payload differs beyond exact changes and validated prior reference upgrades")
            for phase in saved:
                item = saved[phase][sid]
                require(digest((output / item["payload_path"]).read_bytes()) == item["payload_sha256"],
                        "Saved phase payload differs from measured bytes")
                require(digest((output / item["prepared_xml_path"]).read_bytes()) == original_hashes[sid],
                        "Saved phase source differs from original")
            if retain_rows:
                evidence_rows.append({
                    "source_id": sid, "source_sha256": original_hashes[sid],
                    "axis": ("resource" if sid in RESOURCE_IDS else "creator" if sid in CREATOR_IDS
                             else "title" if sid in TITLE_IDS else "control"),
                    "before_status": before_rows[sid]["source_status"], "after_status": after_rows[sid]["source_status"],
                    "before_metadata_canonical_sha256": digest(canonical(before["metadata"])),
                    "after_metadata_canonical_sha256": digest(canonical(after["metadata"])),
                    "before_notes_sha256": digest(before["metadata"]["notes"].encode()),
                    "after_notes_sha256": digest(after["metadata"]["notes"].encode()),
                    "permitted_metadata_changes": permitted,
                    "complete_metadata_unchanged": before["metadata"] == after["metadata"],
                    "validated_prior_profile_reference_upgrades": upgrades,
                    "original_and_all_input_prepared_xml_copies_unchanged": True,
                    "saved_phases": {phase: saved[phase][sid] for phase in saved},
                })
        batches.append({
            "name": name, "source_ids": sorted(selected),
            "phase_counts": {phase: reports[phase]["summary"]["source_status_counts"] for phase in reports},
            "report_canonical_sha256": {phase: digest(canonical(reports[phase])) for phase in reports},
            "after_snapshot_path": str((directory / "after_snapshot").relative_to(output)),
            "repeat_path": str((directory / "after").relative_to(output)),
            "repeat_semantics": "First after directory copied to after_snapshot before unchanged same-directory retry; snapshot retains original after paths, no semantic path normalization",
            "repeat_report_and_payload_bytes_identical": True,
            "withdrawal_restores_baseline_statuses_and_complete_payload_bytes": True,
        })

    measure("smoke10", SMOKE, False)
    measure("candidates15_controls7", IDS | CONTROLS, True)
    require(len(evidence_rows) == 22 and {row["source_id"] for row in evidence_rows} == IDS | CONTROLS,
            "Measured exact22 evidence rows differ")
    proposed = copy.deepcopy(ledger["records"])
    for row in proposed:
        sid = row["source_id"]
        if sid in IDS:
            row.update(source_status="supported", evidence="measured_residual_evidence15")
        else:
            require(row == rows_by_id[sid], "Unselected ledger object changed")
    after_counts = Counter(row["source_status"] for row in proposed)
    require(after_counts == {"supported": 3696, "held": 504, "failed": 6}, "Measured integrated counts differ")
    require(sum(row != rows_by_id[row["source_id"]] for row in proposed) == 15, "Ledger delta is not exact15")
    require(all(row["source_status"] == "held" for row in proposed if row["source_id"] in protected),
            "An alias or remaining exception/control hold changed")
    require(original_hashes == inventory(repo), "Any original XML changed during measurement")
    require(bindings_before == source_bindings(repo), "Code/test/contract source bindings changed during measurement")
    require(not any(guard.counts["tests"].values()) and not guard.blocked_call_sites, "Unexpected offline guard violation")
    result = {
        "schema_version": 1, "status": "MEASURED_OFFLINE", "base_main": BASE_MAIN, "reviewed_at": reviewed_at,
        "scope": "Guarded exact10 smoke, then15 candidates plus7 controls; before/after/unchanged same-directory repeat/withdrawal with saved snapshots. Frozen4206 ledger plus measured15 delta, not fresh full-corpus QA or release.",
        "prior_ledger_sha256": LEDGER_SHA, "profile_sha256": pins,
        "current_counts_recounted": dict(before_counts), "combined_counts_computed": dict(after_counts),
        "combined_status_rows_sha256": digest(canonical(proposed)), "measured_promotions": 15,
        "resource11_source_ids": sorted(RESOURCE_IDS), "creator3_source_ids": sorted(CREATOR_IDS),
        "editorial233_source_ids": sorted(TITLE_IDS), "held_control_ids": sorted(HELD_CONTROLS),
        "supported_control_ids": sorted(SUPPORTED_CONTROLS),
        "resource11_provenance_counts": {"REVIEWER_RECONCILED": 11},
        "creator3_provenance": "source_primary_citation_attribution", "editorial233_provenance": "SOURCE_BACKED",
        "all596_prior_resource_members_contexts_review_objects_times_unchanged": True,
        "all412_prior_creator_members_and_cohort_objects_unchanged": True,
        "all35_prior_title_member_objects_unchanged": True,
        "all4191_unselected_ledger_objects_unchanged": True,
        "all4206_original_xml_sha256_verified_before_and_after": True,
        "original_xml_inventory_sha256": digest(canonical(original_hashes)),
        "all456_alias_identities_still_held_without_rekey_or_canonical_selection": True,
        "historical31_exception_source_ids": sorted(historical_exceptions),
        "current_held20_exception_source_ids": sorted(current_exceptions),
        "promoted11_from_historical31_exception_source_ids": sorted(RESOURCE_IDS),
        "source_bindings_unchanged": True,
        "source_tree_sha256": digest(json.dumps(bindings_before, sort_keys=True).encode()),
        "environment_cleared_dummy_credentials_only": True,
        "guard_blocks": guard.counts, "unexpected_guard_call_sites": guard.blocked_call_sites,
        "guard_in_process_read_only_git_queries": guard.metadata_queries,
        "provider_requests": 0, "new_remote_verifications_or_publication_approvals": 0,
        "batches": batches, "rows": evidence_rows,
    }
    integrated = copy.deepcopy(ledger)
    # Preserve historical membership/hash explicitly without claiming all31 remain held.
    historical_ids = integrated.pop("held31_exception_ids")
    historical_sha = integrated.pop("held31_exception_membership_sha256")
    integrated["historical_exception_cohort31"] = {
        "source_ids": historical_ids, "membership_sha256": historical_sha,
        "source_ledger_sha256": LEDGER_SHA,
        "meaning": "Frozen prior31 exception membership; current held subset below excludes the measured11 resource corrections",
    }
    integrated.update(
        scope=result["scope"], records=proposed,
        integrated_counts={"supported": 3696, "held": 504, "malformed": 6},
        promoted_source_count=ledger["promoted_source_count"] + 15,
        per_source_status_sha256=result["combined_status_rows_sha256"],
        measured_evidence15_source_ids=sorted(IDS),
        current_held_exception_ids=sorted(current_exceptions),
        current_held_exception_count=20,
        current_held_exception_membership_sha256=digest(canonical(sorted(current_exceptions))),
        promoted11_from_historical31_exception_ids=sorted(RESOURCE_IDS),
        resource607_sha256=NEW_RESOURCE_SHA, creator415_sha256=NEW_CREATOR_SHA, title36_sha256=NEW_TITLE_SHA,
        residual_evidence15_validation_canonical_sha256=digest(canonical(result)),
        all4206_original_xml_sha256_verified_before_and_after=True,
        all4191_unselected_prior_status_objects_unchanged=True,
        all456_alias_identities_still_held=True,
        provider_requests=0, remote_verification_or_publication_approval_added=False,
    )
    (output / "integrated_source_status.json").write_text(json.dumps(integrated, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="Checkout root")
    parser.add_argument("--output", type=Path, required=True, help="New directory below /tmp, outside the checkout")
    parser.add_argument("--reviewed-at", default=None)
    args = parser.parse_args()
    repo, output = args.repo.resolve(), args.output.resolve()
    require(output.is_relative_to(Path("/tmp").resolve()) and output != Path("/tmp").resolve()
            and not output.is_relative_to(repo), "Use a new isolated /tmp output directory outside the checkout")
    require(not output.exists() and output.parent.is_dir(), "Use a new output directory with an existing parent")
    os.environ.clear()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repo))
    os.chdir(repo)
    # Import only the stdlib-based CI guard before installing it; no scripts imports.
    from ci.run_offline_tests import OfflineGuard, clean_environment

    os.environ.update(clean_environment(output))
    tempfile.tempdir = str(output)
    guard = OfflineGuard(repo, output, BASE_MAIN)
    guard.install()
    guard.self_check()
    output.mkdir()
    result = validate(repo, output, args.reviewed_at or datetime.now(timezone.utc).isoformat(), guard)
    require(not any(guard.counts["tests"].values()), "Unexpected guard violation during receipt writing")
    (output / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in ("rows", "batches")}, indent=2))


if __name__ == "__main__":
    main()
