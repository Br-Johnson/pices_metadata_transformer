"""Guarded four-resource delta and three controls, preserving all originals.

The seven-source batch is below the ten-source smoke limit. Frozen accounting plus this measured delta is not fresh full
corpus QA, remote verification, underlying-rights clearance or publication approval.
"""

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

BASE_MAIN = "e998e9c97945da60cf9c15fb39ab5fc2a5b11d47"
LEDGER_SHA = "8d70adb44b599f7b0707f3565d43b2356ee7973054ca66c5592f3826a2c555f2"
OLD_SHA = "7dc625fe5fac625d1fe36f3fdf481c0ba63bd40acb0acc2c9b148079a6f9d550"
NEW_SHA = "4719b46cfe46a2b950b3abc695fd8778ffc7bd3041e5bb0bae253c613c55ec2c"
CREATOR_SHA = "c6aa4f9c2e4c80ea565b3a92d66d0e066b12f77534bd23feb92807bd18894ee3"
IDS = {"FGDC-762", "FGDC-849", "FGDC-859", "FGDC-2244"}
CONTROLS = {"FGDC-288", "FGDC-1770", "FGDC-4063"}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def forbidden(*args, **kwargs):
    raise AssertionError("Provider transport, sockets and DNS forbidden")


def inventory(repo):
    return {p.stem: digest(p.read_bytes()) for p in sorted((repo / "FGDC").glob("*.xml"))}


def reference(path):
    return {"manifest_path": str(path), "manifest_sha256": digest(path.read_bytes())}


def validate(repo, output, reviewed_at):
    repo = repo.resolve()
    sys.path.insert(0, str(repo))
    os.chdir(repo)
    docs = repo / "docs/readiness/2026-10-03"
    today = repo / "docs/readiness/2026-10-04"
    ledger_path = today / "residual_source32_integrated_source_status.json"
    old_path = today / "finite_source_resource_access_592.json"
    new_path = today / "finite_source_resource_access_596.json"
    creator = today / "source_citation_credits_412.json"
    require(digest(ledger_path.read_bytes()) == LEDGER_SHA, "Frozen baseline ledger changed")
    require(digest(old_path.read_bytes()) == OLD_SHA, "Prior592 profile changed")
    require(digest(new_path.read_bytes()) == NEW_SHA, "New596 profile changed")
    require(digest(creator.read_bytes()) == CREATOR_SHA, "Constant creator412 profile changed")
    ledger = json.loads(ledger_path.read_bytes())
    rows_by_id = {row["source_id"]: row for row in ledger["records"]}
    require(len(rows_by_id) == len(ledger["records"]) == 4206, "Ledger inventory differs")
    before_counts = Counter(row["source_status"] for row in ledger["records"])
    require(before_counts == {"supported": 3677, "held": 523, "failed": 6}, "Baseline counts differ")
    old, new = json.loads(old_path.read_bytes()), json.loads(new_path.read_bytes())
    require(len(new["members"]) == 596 and new["members"][:592] == old["members"], "Prior592 membership changed")
    additions = new["members"][592:]
    require(len(additions) == 4 and {m["source_id"] for m in additions} == IDS, "Exact four membership differs")
    require(new["source_contexts"] == old["source_contexts"], "Prior source contexts changed")
    require(all(new["acquisition_contexts"][sid] == value for sid, value in old["acquisition_contexts"].items()), "Prior acquisition context changed")
    require(all(new[key] == value for key, value in old.items() if key.endswith("_review")), "Prior review object or time changed")
    require(new["residual_resource4_review"]["members"] == additions, "New review membership differs")
    original_hashes = inventory(repo)
    require(len(original_hashes) == 4206, "Original count differs")
    require(original_hashes == {sid: row["source_sha256"] for sid, row in rows_by_id.items()}, "All4206 originals differ from baseline")
    require(all(original_hashes[m["source_id"]] == m["source_sha256"] for m in additions), "Added source binding differs")
    duplicates = {sha for sha, count in Counter(original_hashes.values()).items() if count > 1}
    aliases = {sid for sid, sha in original_hashes.items() if sha in duplicates}
    protected = aliases | set(ledger["held31_exception_ids"]) | CONTROLS
    require(len(aliases) == 456 and not IDS & protected, "Protected identity overlap")
    require(all(rows_by_id[sid]["source_status"] == "held" for sid in IDS | protected), "Baseline hold differs")
    source = output / "sources"
    source.mkdir(parents=True)
    selected = IDS | CONTROLS
    require(len(selected) == 7 and len(selected) <= 10, "Smoke exceeds exact bounded scope")
    for sid in sorted(selected):
        shutil.copyfile(repo / "FGDC" / (sid + ".xml"), source / (sid + ".xml"))
    reports, payloads, payload_hashes = {}, {}, {}
    with (
        patch.dict(os.environ, {"ZENODO_SANDBOX_TOKEN": "offline-fixture-token"}, clear=True),
        patch("requests.sessions.Session.send", forbidden),
        patch("socket.socket.connect", forbidden),
        patch("socket.create_connection", forbidden),
        patch("socket.getaddrinfo", forbidden),
    ):
        import scripts.logger

        with patch.object(scripts.logger, "get_logger", return_value=Mock()):
            from scripts import dataset_access_interpretation as interpretation
            from scripts.collection_qa import classify_collection
            from scripts.path_config import OutputPaths

            require(interpretation.RESOURCE4_MANIFEST_SHA256 == NEW_SHA, "Runtime new-profile pin differs")
            older = repo / "docs/readiness/2026-10-02"
            options = {
                "authority_manifest": older / "rehosting_authority.json",
                "access_interpretation_manifest": older / "contact_source_interpretation.json",
                "creator_interpretation_manifest": older / "exxon_citation_interpretation.json",
                "contributor_access_interpretation_manifest": older / "contributor_source_interpretation.json",
                "collective_creator_interpretation_manifest": docs / "dfo_staff_citation_interpretation.json",
                "institution_creator_interpretation_manifest": creator,
                "source_link_interpretation_manifest": docs / "historical_dataset_linkage_21.json",
                "source_title_interpretation_manifest": docs / "source_display_titles_35.json",
                "source_scope_attestation_manifest": docs / "source_scope_reconciliation_904.json",
            }
            for phase in ("before", "after", "repeat", "withdrawn"):
                active = phase in ("after", "repeat")
                destination = output / ("after" if phase == "repeat" else phase)
                reports[phase] = classify_collection(source, destination, reviewed_at, dataset_access_interpretation_manifest=new_path if active else old_path, **options)
                paths = OutputPaths(str(destination), "sandbox")
                payloads[phase], payload_hashes[phase] = {}, {}
                for sid in sorted(selected):
                    raw = (Path(paths.zenodo_json_dir) / (sid + ".json")).read_bytes()
                    payloads[phase][sid], payload_hashes[phase][sid] = json.loads(raw), digest(raw)
                    require(digest((source / (sid + ".xml")).read_bytes()) == original_hashes[sid], "Input XML copy changed")
                    require(digest((Path(paths.original_fgdc_dir) / (sid + ".xml")).read_bytes()) == original_hashes[sid], "Prepared XML copy changed")
                    metadata, policy = payloads[phase][sid]["metadata"], payloads[phase][sid]["artifact_policy"]
                    require(metadata["access_right"] == "restricted" and metadata["license"] == "", "Metadata rights changed")
                    require(policy.get("license") in ("", None) and policy["rights_scope"] == "original_fgdc_xml" and policy["rights_source_xpath"] == "./metainfo/metuc" and policy["date_semantics"] == "source_metadata_date", "Artifact rights/date policy changed")
                    require(policy.get("rehosting_authority") is not None, "Separate restoration authority missing")
                expected = {"supported": 4, "held": 3, "failed": 0} if active else {"supported": 0, "held": 7, "failed": 0}
                require(reports[phase]["summary"]["source_status_counts"] == expected, f"Unexpected {phase} counts")
                require({row["source_id"] for row in reports[phase]["records"]} == selected, "Report scope differs")
                for row in reports[phase]["records"]:
                    sid = row["source_id"]
                    require(row["source_sha256"] == original_hashes[sid], "Report source hash changed")
                    require(not row["remote_verified"] and not row["publication_approved"], "Remote/release authority added")
                    require(row["rehosting_authority"] == "USER_ATTESTED", "Separate authority changed")
                    require(row["source_status"] == ("supported" if active and sid in IDS else "held"), "Unexpected source status")
                    if active and sid in IDS:
                        require(row["dataset_access_interpretation"] == "REVIEWER_RECONCILED", "Unexpected source provenance")
            require(reports["after"] == reports["repeat"], "Repeat report changed")
            require(payload_hashes["after"] == payload_hashes["repeat"], "Repeat payload bytes changed")
            require(payload_hashes["before"] == payload_hashes["withdrawn"], "Withdrawal changed payload bytes")
    before_rows = {row["source_id"]: row for row in reports["before"]["records"]}
    after_rows = {row["source_id"]: row for row in reports["after"]["records"]}
    evidence_rows = []
    for sid in sorted(selected):
        before, after = payloads["before"][sid], payloads["after"][sid]
        stripped = copy.deepcopy(after)
        if sid in IDS:
            require(stripped["artifact_policy"].pop("dataset_access_interpretation") == reference(new_path), "Interpretation reference differs")
        else:
            # The selected-profile fingerprint may change; each control row and payload must not.
            require(before_rows[sid] == after_rows[sid], "Held control row changed")
        require(stripped == before, "Payload changed beyond exact interpretation reference")
        require(before["metadata"] == after["metadata"], "Complete metadata changed")
        evidence_rows.append({
            "source_id": sid, "source_sha256": original_hashes[sid],
            "before_status": "held", "after_status": "supported" if sid in IDS else "held",
            "before_payload_sha256": payload_hashes["before"][sid], "after_payload_sha256": payload_hashes["after"][sid],
            "unchanged_metadata_canonical_sha256": digest(canonical(after["metadata"])),
            "unchanged_notes_sha256": digest(after["metadata"]["notes"].encode()),
            "complete_metadata_and_original_input_prepared_xml_unchanged": True,
        })
    proposed = copy.deepcopy(ledger["records"])
    for row in proposed:
        sid = row["source_id"]
        if sid in IDS:
            row.update(source_status="supported", evidence="measured_residual_resource4")
        else:
            require(row == rows_by_id[sid], "Unselected ledger object changed")
    after_counts = Counter(row["source_status"] for row in proposed)
    require(after_counts == {"supported": 3681, "held": 519, "failed": 6}, "Measured combined counts differ")
    require(sum(row != rows_by_id[row["source_id"]] for row in proposed) == 4, "Ledger change count differs")
    require(all(row["source_status"] == "held" for row in proposed if row["source_id"] in protected), "Protected hold changed")
    require(original_hashes == inventory(repo), "Any original changed during measurement")
    result = {
        "schema_version": 1, "status": "MEASURED_OFFLINE", "base_main": BASE_MAIN, "reviewed_at": reviewed_at,
        "scope": "Seven-source guarded smoke/before/after/repeat/withdrawal; frozen4206 ledger plus measuredfour delta, not fresh full-corpus QA",
        "prior_ledger_sha256": LEDGER_SHA, "prior592_sha256": OLD_SHA, "profile596_sha256": NEW_SHA, "constant_creator412_sha256": CREATOR_SHA,
        "current_counts_recounted": dict(before_counts), "combined_counts_computed": dict(after_counts),
        "combined_status_rows_sha256": digest(canonical(proposed)), "measured_promotions": 4,
        "new4_provenance_counts": {"REVIEWER_RECONCILED": 4}, "measured_source_ids": sorted(IDS), "held_control_ids": sorted(CONTROLS),
        "all592_prior_members_context_review_objects_times_unchanged": True,
        "all4202_unselected_ledger_objects_unchanged": True,
        "all4206_original_xml_sha256_verified_before_and_after": True, "original_xml_inventory_sha256": digest(canonical(original_hashes)),
        "all456_alias_identities_and31_exceptions_and_three_controls_still_held": True,
        "phase_counts": {phase: reports[phase]["summary"]["source_status_counts"] for phase in reports},
        "repeat_identical": True, "withdrawal_restores_holds_and_payload_bytes": True,
        "provider_requests": 0, "new_remote_verifications_or_publication_approvals": 0, "rows": evidence_rows,
    }
    integrated = copy.deepcopy(ledger)
    integrated.update(
        scope=result["scope"], records=proposed,
        integrated_counts={"supported": 3681, "held": 519, "malformed": 6},
        promoted_source_count=ledger["promoted_source_count"] + 4,
        per_source_status_sha256=result["combined_status_rows_sha256"], measured_resource4_source_ids=sorted(IDS),
        new4_provenance_counts=result["new4_provenance_counts"], resource596_sha256=NEW_SHA,
        residual_resource4_validation_canonical_sha256=digest(canonical(result)),
        all4206_original_xml_sha256_verified_before_and_after=True, all4202_unselected_prior_status_objects_unchanged=True,
        provider_requests=0, remote_verification_or_publication_approval_added=False,
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
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))


if __name__ == "__main__":
    main()
