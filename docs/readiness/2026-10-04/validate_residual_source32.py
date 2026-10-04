"""Measure exact 29 resource and three creator corrections offline.

A guarded ten-source smoke precedes the
bounded measurements; all 4,206 original hashes and the frozen ledger are checked.
The resulting accounting is an offline delta, not fresh full-corpus QA or release.
"""

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

BASE_MAIN = "b5291c3d9cc7e6fd8fef455120329d00a46a6156"
LEDGER_SHA = "30bae947685d6d22fe3863aacbd6c06735d9e7a8986133a232d9a55c2493d0f7"
RESOURCE_SHA = "7dc625fe5fac625d1fe36f3fdf481c0ba63bd40acb0acc2c9b148079a6f9d550"
CREATOR_SHA = "c6aa4f9c2e4c80ea565b3a92d66d0e066b12f77534bd23feb92807bd18894ee3"
PHYSICAL_IDS = {"FGDC-" + str(i) for i in (740, 815, 851, 879)}
RESOURCE_IDS = PHYSICAL_IDS | {
    "FGDC-" + str(i)
    for i in (
        669, 753, 779, 784, 817, 832, 834, 836, 845, 853, 855, 860, 861,
        880, 882, 883, 1341, 1710, 1767, 1903, 2603, 2698, 2702, 3541, 4037,
    )
}
CREATOR_IDS = {"FGDC-10", "FGDC-3957", "FGDC-3961"}
IDS = RESOURCE_IDS | CREATOR_IDS
CONTROLS = {"FGDC-" + str(i) for i in (288, 762, 849, 859, 1770, 2244, 4063)}
SMOKE_RESOURCES = PHYSICAL_IDS | {"FGDC-753", "FGDC-784", "FGDC-4037"}
REVIEW_BLOCKS = (
    "resource_reconciliation_review", "npafc_report_notification_review", "residual_source_review",
)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def forbidden(*args, **kwargs):
    raise AssertionError("Provider transport, sockets and DNS forbidden")


def reference(path):
    return {"manifest_path": str(path), "manifest_sha256": digest(path.read_bytes())}


def inventory(repo):
    return {p.stem: digest(p.read_bytes()) for p in sorted((repo / "FGDC").glob("*.xml"))}


def require_rights(payload):
    metadata, policy = payload["metadata"], payload["artifact_policy"]
    require(metadata["access_right"] == "restricted" and metadata["license"] == "", "Rights changed")
    require(policy["rights_scope"] == "original_fgdc_xml", "Artifact rights scope changed")
    require(policy["rights_source_xpath"] == "./metainfo/metuc", "Rights source changed")
    require(policy["date_semantics"] == "source_metadata_date", "Artifact date mode changed")
    require(policy.get("license") in ("", None), "A policy license was added")
    require(policy.get("rehosting_authority") is not None, "Restoration authority was removed")


def creator_notes_preserved(before, after, result):
    """Reuse the established full-note and Curator decision JSON comparison."""
    restored = after
    for note in result["preservation_notes"]:
        require("\n" + note in restored, "Literal creator role/source preservation note missing")
        restored = restored.replace("\n" + note, "", 1)
    old_lines = [line for line in before.splitlines() if line.startswith("Curator decision: ")]
    new_lines = [line for line in restored.splitlines() if line.startswith("Curator decision: ")]
    require(len(old_lines) == len(new_lines) == 1, "Expected one complete Curator decision line")
    old_decision = json.loads(old_lines[0].removeprefix("Curator decision: "))
    new_decision = json.loads(new_lines[0].removeprefix("Curator decision: "))
    new_decision["metadata"]["creators"] = old_decision["metadata"]["creators"]
    require(new_decision == old_decision, "Curator decision changed beyond creator objects")
    require(restored.replace(new_lines[0], old_lines[0], 1) == before, "Other source notes changed")


def validate(repo, output, reviewed_at):
    repo = repo.resolve()
    sys.path.insert(0, str(repo))
    os.chdir(repo)
    docs = repo / "docs/readiness/2026-10-03"
    today = repo / "docs/readiness/2026-10-04"
    ledger_path = today / "combined_source7_integrated_source_status.json"
    old_resource = today / "finite_source_resource_access_563.json"
    new_resource = today / "finite_source_resource_access_592.json"
    old_creator = docs / "source_citation_credits_409.json"
    new_creator = today / "source_citation_credits_412.json"
    require(digest(ledger_path.read_bytes()) == LEDGER_SHA, "Frozen baseline ledger changed")
    require(digest(new_resource.read_bytes()) == RESOURCE_SHA, "Resource592 pin changed")
    require(digest(new_creator.read_bytes()) == CREATOR_SHA, "Creator412 pin changed")
    ledger = json.loads(ledger_path.read_bytes())
    rows_by_id = {r["source_id"]: r for r in ledger["records"]}
    require(len(rows_by_id) == len(ledger["records"]) == 4206, "Source accounting mismatch")
    before_counts = Counter(r["source_status"] for r in ledger["records"])
    require(before_counts == {"supported": 3645, "held": 555, "failed": 6}, "Baseline counts differ")
    require(len(RESOURCE_IDS) == 29 and len(IDS) == 32 and not IDS & CONTROLS, "Scope overlaps")
    require(len(SMOKE_RESOURCES | CREATOR_IDS) == 10, "Smoke must contain ten exact sources")
    prior_resource, resource = json.loads(old_resource.read_bytes()), json.loads(new_resource.read_bytes())
    require(len(resource["members"]) == 592 and resource["members"][:563] == prior_resource["members"], "Prior563 members changed")
    additions = resource["members"][563:]
    require(len(additions) == 29 and {m["source_id"] for m in additions} == RESOURCE_IDS, "Resource29 membership differs")
    require(resource["source_contexts"] == prior_resource["source_contexts"], "Prior source contexts changed")
    require(all(resource["acquisition_contexts"][sid] == value for sid, value in prior_resource["acquisition_contexts"].items()), "Prior acquisition contexts changed")
    require(all(resource[key] == prior_resource[key] for key in REVIEW_BLOCKS), "Prior review blocks changed")
    require(resource["residual_resource_review"]["members"] == [m for m in additions if m["source_id"] not in PHYSICAL_IDS], "Reviewer block must contain only25")
    prior_credit, credit = json.loads(old_creator.read_bytes()), json.loads(new_creator.read_bytes())
    old_cohort_count = len(prior_credit["cohorts"])
    require(sum(len(c["members"]) for c in prior_credit["cohorts"]) == 409, "Old creator binding count differs")
    require(credit["cohorts"][:old_cohort_count] == prior_credit["cohorts"], "Prior409 cohort objects changed")
    creator_additions = [m for c in credit["cohorts"][old_cohort_count:] for m in c["members"]]
    require(sum(len(c["members"]) for c in credit["cohorts"]) == 412, "New creator binding count differs")
    require(len(creator_additions) == 3 and {m["source_id"] for m in creator_additions} == CREATOR_IDS, "Creator3 membership differs")
    original_hashes = inventory(repo)
    require(len(original_hashes) == 4206, "Original inventory count differs")
    require(original_hashes == {sid: row["source_sha256"] for sid, row in rows_by_id.items()}, "All4206 originals differ from the baseline")
    require(all(original_hashes[m["source_id"]] == m["source_sha256"] for m in additions + creator_additions), "Added source binding differs")
    duplicate_hashes = {sha for sha, count in Counter(original_hashes.values()).items() if count > 1}
    aliases = {sid for sid, sha in original_hashes.items() if sha in duplicate_hashes}
    protected = aliases | set(ledger["held31_exception_ids"]) | CONTROLS
    require(len(aliases) == 456 and not IDS & protected, "Protected source overlap")
    require(all(rows_by_id[sid]["source_status"] == "held" for sid in IDS | protected), "Expected baseline hold changed")
    batches, measured_rows = [], []
    with (
        patch.dict(os.environ, {"ZENODO_SANDBOX_TOKEN": "offline-fixture-token"}, clear=True),
        patch("requests.sessions.Session.send", forbidden),
        patch("socket.socket.connect", forbidden),
        patch("socket.create_connection", forbidden),
        patch("socket.getaddrinfo", forbidden),
    ):
        import scripts.logger

        with patch.object(scripts.logger, "get_logger", return_value=Mock()):
            from scripts.citation_creator_interpretation import (
                validate_creator_interpretation,
            )
            from scripts.collection_qa import classify_collection
            from scripts.path_config import OutputPaths

            older = repo / "docs/readiness/2026-10-02"
            common = {
                "authority_manifest": older / "rehosting_authority.json",
                "access_interpretation_manifest": older / "contact_source_interpretation.json",
                "creator_interpretation_manifest": older / "exxon_citation_interpretation.json",
                "contributor_access_interpretation_manifest": older / "contributor_source_interpretation.json",
                "collective_creator_interpretation_manifest": docs / "dfo_staff_citation_interpretation.json",
                "source_link_interpretation_manifest": docs / "historical_dataset_linkage_21.json",
                "source_title_interpretation_manifest": docs / "source_display_titles_35.json",
                "source_scope_attestation_manifest": docs / "source_scope_reconciliation_904.json",
            }

            def measure(name, selected, axis, keep_rows=True):
                directory = output / name
                source = directory / "sources"
                source.mkdir(parents=True)
                for sid in sorted(selected):
                    shutil.copyfile(repo / "FGDC" / (sid + ".xml"), source / (sid + ".xml"))
                reports, payloads, payload_hashes = {}, {}, {}
                for phase in ("before", "after", "repeat", "withdrawn"):
                    active = phase in ("after", "repeat")
                    destination = directory / ("after" if phase == "repeat" else phase)
                    # Isolate the two axes: resource29 always uses old409; creator3 always uses old563.
                    options = {
                        **common,
                        "dataset_access_interpretation_manifest": new_resource if axis in ("resource", "control") and active else old_resource,
                        "institution_creator_interpretation_manifest": new_creator if axis == "creator" and active else old_creator,
                    }
                    reports[phase] = classify_collection(source, destination, reviewed_at, **options)
                    paths = OutputPaths(str(destination), "sandbox")
                    payloads[phase], payload_hashes[phase] = {}, {}
                    for sid in sorted(selected):
                        raw = (Path(paths.zenodo_json_dir) / (sid + ".json")).read_bytes()
                        payloads[phase][sid], payload_hashes[phase][sid] = json.loads(raw), digest(raw)
                        require_rights(payloads[phase][sid])
                        require(digest((source / (sid + ".xml")).read_bytes()) == original_hashes[sid], "Input copy changed")
                        require(digest((Path(paths.original_fgdc_dir) / (sid + ".xml")).read_bytes()) == original_hashes[sid], "Prepared XML copy changed")
                    supported = len(selected) if active and axis != "control" else 0
                    require(reports[phase]["summary"]["source_status_counts"] == {"supported": supported, "held": len(selected) - supported, "failed": 0}, f"Unexpected {name}/{phase} counts")
                    require(len(reports[phase]["records"]) == len(selected), "Bounded report membership differs")
                    for row in reports[phase]["records"]:
                        require(row["source_sha256"] == original_hashes[row["source_id"]], "Report source hash changed")
                        require(not row["remote_verified"] and not row["publication_approved"], "Remote/release authority added")
                        require(row["rehosting_authority"] == "USER_ATTESTED", "Separate authority changed")
                        require(row["source_status"] == ("supported" if supported else "held"), "Unexpected status")
                        if active and axis == "resource":
                            require(row["dataset_access_interpretation"] == ("SOURCE_BACKED" if row["source_id"] in PHYSICAL_IDS else "REVIEWER_RECONCILED"), "Resource provenance differs")
                        if active and axis == "creator":
                            require(row["creator_interpretation"] == "source_primary_citation_attribution", "Creator provenance differs")
                require(reports["after"] == reports["repeat"], "Repeat report changed")
                if axis == "control":
                    # The selected-profile fingerprint changes; held rows and payloads must not.
                    require(reports["before"]["records"] == reports["after"]["records"], "Held control record objects changed")
                require(payload_hashes["after"] == payload_hashes["repeat"], "Repeat payload bytes changed")
                require(payload_hashes["before"] == payload_hashes["withdrawn"], "Withdrawal did not restore payload bytes")
                for sid in sorted(selected):
                    before, after = payloads["before"][sid], payloads["after"][sid]
                    require({k: v for k, v in before.items() if k not in ("metadata", "artifact_policy")} == {k: v for k, v in after.items() if k not in ("metadata", "artifact_policy")}, "Payload envelope changed")
                    policy = copy.deepcopy(after["artifact_policy"])
                    if axis == "resource":
                        require(before["metadata"] == after["metadata"], "Resource complete metadata changed")
                        require(policy.pop("dataset_access_interpretation") == reference(new_resource), "Resource reference differs")
                    elif axis == "creator":
                        root = ET.parse(repo / "FGDC" / (sid + ".xml")).getroot()
                        result = validate_creator_interpretation(reference(new_creator), sid, original_hashes[sid], root, True)
                        require(after["metadata"]["creators"] == result["creators"], "Complete creator objects differ")
                        require(before["metadata"]["creators"] != after["metadata"]["creators"], "Creator change was not measured")
                        require({k: v for k, v in before["metadata"].items() if k not in ("creators", "notes")} == {k: v for k, v in after["metadata"].items() if k not in ("creators", "notes")}, "Other creator metadata changed")
                        creator_notes_preserved(before["metadata"]["notes"], after["metadata"]["notes"], result)
                        require(policy.pop("creator_interpretation") == reference(new_creator), "Creator reference differs")
                    else:
                        require(before == after, "Held control payload changed")
                    require(policy == before["artifact_policy"], "Policy changed beyond the one exact interpretation reference")
                    if keep_rows:
                        measured_rows.append({
                            "source_id": sid, "source_sha256": original_hashes[sid], "axis": axis,
                            "before_status": "held", "after_status": "held" if axis == "control" else "supported",
                            "before_payload_sha256": payload_hashes["before"][sid], "after_payload_sha256": payload_hashes["after"][sid],
                            "before_metadata_canonical_sha256": digest(canonical(before["metadata"])),
                            "after_metadata_canonical_sha256": digest(canonical(after["metadata"])),
                            "before_notes_sha256": digest(before["metadata"]["notes"].encode()),
                            "after_notes_sha256": digest(after["metadata"]["notes"].encode()),
                            "permitted_metadata_changes": ["creators", "notes"] if axis == "creator" else [],
                            "whole_metadata_unchanged": before["metadata"] == after["metadata"],
                            "other_notes_and_curator_decision_preserved": True,
                            "original_and_all_input_prepared_xml_copies_unchanged": True,
                        })
                batches.append({"name": name, "axis": axis, "source_ids": sorted(selected), "phase_counts": {phase: reports[phase]["summary"]["source_status_counts"] for phase in reports}, "after_report_canonical_sha256": digest(canonical(reports["after"])), "repeat_identical": True, "withdrawal_restores_holds_and_payload_bytes": True})

            measure("smoke-resource7", SMOKE_RESOURCES, "resource", False)
            measure("smoke-creator3", CREATOR_IDS, "creator", False)
            measure("resource29", RESOURCE_IDS, "resource")
            measure("creator3", CREATOR_IDS, "creator")
            measure("controls7", CONTROLS, "control")
    require(len(measured_rows) == 39 and {r["source_id"] for r in measured_rows} == IDS | CONTROLS, "Measured row scope differs")
    proposed = copy.deepcopy(ledger["records"])
    for row in proposed:
        sid = row["source_id"]
        if sid in IDS:
            row.update(source_status="supported", evidence="measured_residual_source32")
        else:
            require(row == rows_by_id[sid], "Unselected ledger object changed")
    after_counts = Counter(row["source_status"] for row in proposed)
    require(after_counts == {"supported": 3677, "held": 523, "failed": 6}, "Combined measured counts differ")
    require(sum(row != rows_by_id[row["source_id"]] for row in proposed) == 32, "Ledger change count differs")
    require(all(row["source_status"] == "held" for row in proposed if row["source_id"] in protected), "Protected hold changed")
    require(original_hashes == inventory(repo), "Any original XML changed during measurement")
    result = {
        "schema_version": 1, "status": "MEASURED_OFFLINE", "base_main": BASE_MAIN, "reviewed_at": reviewed_at,
        "scope": "Ten-source smoke then isolated resource29/creator3/controls7 guarded before/after/repeat/withdrawal; frozen4206 ledger plus measured32 delta, not fresh full-corpus QA",
        "prior_ledger_sha256": LEDGER_SHA, "resource592_sha256": RESOURCE_SHA, "creator412_sha256": CREATOR_SHA,
        "current_counts_recounted": dict(before_counts), "combined_counts_computed": dict(after_counts),
        "combined_status_rows_sha256": digest(canonical(proposed)), "measured_promotions": 32,
        "resource29_provenance_counts": {"SOURCE_BACKED": 4, "REVIEWER_RECONCILED": 25},
        "creator3_provenance": "source_primary_citation_attribution",
        "all4174_unselected_ledger_objects_unchanged": True, "all563_prior_resource_members_contexts_review_blocks_unchanged": True,
        "all409_prior_creator_bindings_and_cohort_objects_unchanged": True,
        "all4206_original_xml_sha256_verified_before_and_after": True, "original_xml_inventory_sha256": digest(canonical(original_hashes)),
        "all456_alias_identities_and31_exceptions_and_seven_controls_still_held": True,
        "resume_identical": True, "withdrawal_restores_holds": True,
        "provider_requests": 0, "new_remote_verifications_or_publication_approvals": 0,
        "batches": batches, "rows": measured_rows,
    }
    integrated = copy.deepcopy(ledger)
    integrated['previous_combined_profile_sha256'] = integrated.pop('combined_profile_sha256')
    integrated['previous_combined_validation_canonical_sha256'] = integrated.pop('combined_validation_canonical_sha256')
    integrated.update(
        scope=result["scope"], records=proposed,
        integrated_counts={"supported": 3677, "held": 523, "malformed": 6},
        promoted_source_count=ledger["promoted_source_count"] + 32,
        per_source_status_sha256=result["combined_status_rows_sha256"], measured32_source_ids=sorted(IDS),
        resource29_provenance_counts=result["resource29_provenance_counts"], creator3_source_ids=sorted(CREATOR_IDS),
        residual_source32_validation_canonical_sha256=digest(canonical(result)),
        resource592_sha256=RESOURCE_SHA, creator412_sha256=CREATOR_SHA,
        all4206_original_xml_sha256_verified_before_and_after=True,
        all4174_unselected_prior_status_objects_unchanged=True, provider_requests=0,
        remote_verification_or_publication_approval_added=False,
    )
    (output / "integrated_source_status.json").write_text(json.dumps(integrated, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="Checkout root")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reviewed-at", default=None)
    args = parser.parse_args()
    output = args.output.resolve()
    require(not output.exists(), "Use a new output directory")
    result = validate(args.repo, output, args.reviewed_at or datetime.now(timezone.utc).isoformat())
    (output / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in ("rows", "batches")}, indent=2))


if __name__ == "__main__":
    main()
