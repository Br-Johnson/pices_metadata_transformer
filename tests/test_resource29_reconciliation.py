"""Exact 29-resource extension preserves evidence, bytes and release gates.

These offline contracts cover the resource extension and its preserved release
gates. The independent creator extension must not change these inputs.
"""

import copy
import hashlib
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import dataset_access_interpretation as interpretation
from scripts.upload_service import (
    atomic_json,
    metadata_hash,
    prepare_metadata,
    read_json,
)
from tests import test_resource_scope_reconciliation as previous

REPO = previous.REPO
DOCS = REPO / "docs/readiness/2026-10-04"
OLD = DOCS / "finite_source_resource_access_563.json"
NEW = DOCS / "finite_source_resource_access_592.json"
REFERENCE = previous.reference
PHYSICAL_IDS = {"FGDC-" + str(i) for i in (740, 815, 851, 879)}
RECONCILED_IDS = {
    "FGDC-" + str(i)
    for i in (
        669, 753, 779, 784, 817, 832, 834, 836, 845, 853, 855, 860, 861,
        880, 882, 883, 1341, 1710, 1767, 1903, 2603, 2698, 2702, 3541, 4037,
    )
}
IDS = PHYSICAL_IDS | RECONCILED_IDS
CONTROLS = {"FGDC-" + str(i) for i in (288, 762, 849, 859, 1770, 2244, 4063)}
OLD_REVIEW_BLOCKS = (
    "resource_reconciliation_review",
    "npafc_report_notification_review",
    "residual_source_review",
)
SMOKE_IDS = PHYSICAL_IDS | {
    "FGDC-753", "FGDC-784", "FGDC-832", "FGDC-853", "FGDC-1903", "FGDC-4037",
}


class Resource29ReconciliationTests(unittest.TestCase):
    prepared = previous.ResourceScopeReconciliationTests.prepared

    def setUp(self):
        self.reviewed_at = datetime.now(timezone.utc).isoformat()
        self.profile = read_json(NEW)
        self.members = self.profile["members"][563:]

    def classify(self, tmp, ids, profile=NEW, authority=True):
        return self.prepared(
            tmp,
            ids,
            authority=authority,
            replacements={
                "dataset_access_interpretation_manifest": profile,
                "source_scope_attestation_manifest": previous.SCOPE_NEW,
            },
        )

    def validate(self, member, root=None, profile=NEW, **kwargs):
        if root is None:
            root = ET.parse(REPO / "FGDC" / (member["source_id"] + ".xml")).getroot()
        return interpretation.validate_dataset_access_interpretation(
            REFERENCE(profile),
            **member,
            root=root,
            **{"reviewed_at": self.reviewed_at, **kwargs},
        )

    def test_exact_29_pin_additivity_and_all_prior_563_results_remain_compatible(self):
        old = read_json(OLD)
        self.assertEqual(len(IDS), 29)
        self.assertEqual(len(PHYSICAL_IDS), 4)
        self.assertEqual(len(RECONCILED_IDS), 25)
        self.assertEqual(len(self.profile["members"]), 592)
        self.assertEqual(len({m["source_id"] for m in self.profile["members"]}), 592)
        self.assertEqual({m["source_id"] for m in self.members}, IDS)
        self.assertEqual(self.profile["members"][:563], old["members"])
        self.assertEqual(self.profile["source_contexts"], old["source_contexts"])
        self.assertFalse(IDS & {m["source_id"] for m in old["members"]})
        for sid, context in old["acquisition_contexts"].items():
            self.assertEqual(self.profile["acquisition_contexts"][sid], context)
        for key in OLD_REVIEW_BLOCKS:
            self.assertEqual(self.profile[key], old[key])
        review = self.profile["residual_resource_review"]
        self.assertEqual(
            review["members"],
            [m for m in self.members if m["source_id"] in RECONCILED_IDS],
        )
        self.assertEqual(
            review["original_statement_references"],
            old["residual_source_review"]["original_statement_references"],
        )
        self.assertEqual(len(review["original_statement_references"]), 5)
        self.assertFalse(IDS & {m["source_id"] for m in read_json(previous.SCOPE_OLD)["members"]})
        self.assertFalse(IDS & {m["source_id"] for m in read_json(previous.SCOPE_NEW)["members"]})
        self.assertFalse(CONTROLS & interpretation.dataset_access_member_ids(REFERENCE(NEW)))
        self.assertEqual(
            hashlib.sha256(NEW.read_bytes()).hexdigest(),
            interpretation.RESIDUAL_RESOURCE_MANIFEST_SHA256,
        )
        # Later additive reviews cannot move the assessment time of old members.
        old_time = max(datetime.fromisoformat(old[k]["reviewed_at"]) for k in OLD_REVIEW_BLOCKS)
        for member in old["members"]:
            with self.subTest(prior_source=member["source_id"]):
                self.assertEqual(
                    self.validate(member, reviewed_at=old_time.isoformat()),
                    self.validate(member, profile=OLD, reviewed_at=old_time.isoformat()),
                )
        for member in self.members:
            if member["source_id"] in RECONCILED_IDS:
                with self.subTest(new_source=member["source_id"]), self.assertRaises(ValueError):
                    self.validate(member, reviewed_at=old_time.isoformat())
        with patch.object(interpretation, "RESIDUAL_RESOURCE_MANIFEST_SHA256", "unaccepted"):
            self.assertEqual(interpretation.dataset_access_member_ids(REFERENCE(NEW)), frozenset())
            with self.assertRaises(ValueError):
                self.validate(self.members[0])

    def test_exact_source_full_root_plain_constraints_and_review_time_fail_closed(self):
        reviewed = datetime.fromisoformat(self.profile["residual_resource_review"]["reviewed_at"])
        bad_times = (
            None,
            "not-a-time",
            reviewed.replace(tzinfo=None).isoformat(),
            (reviewed - timedelta(seconds=1)).isoformat(),
            (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        )
        for member in self.members:
            sid = member["source_id"]
            raw = (REPO / "FGDC" / (sid + ".xml")).read_bytes()
            root = ET.fromstring(raw)
            context = self.profile["acquisition_contexts"][sid]
            with self.subTest(source_id=sid):
                self.assertEqual(hashlib.sha256(raw).hexdigest(), member["source_sha256"])
                self.assertEqual(context["context_elements"]["."], [ET.tostring(root, encoding="unicode")])
                for xpath, value in context["constraints"].items():
                    nodes = root.findall(xpath)
                    self.assertEqual(len(nodes), 1)
                    self.assertFalse(nodes[0].attrib or list(nodes[0]))
                    self.assertEqual(nodes[0].text, value)
                result = self.validate(member, root)
                self.assertEqual(result["status"], "SOURCE_BACKED" if sid in PHYSICAL_IDS else "REVIEWER_RECONCILED")
                for flag in ("grants_rehosting", "grants_new_license", "publication_approved"):
                    self.assertIs(result[flag], False)
                if sid in RECONCILED_IDS:
                    self.assertEqual(result["reconciliation_reviewed_at"], reviewed.isoformat())
                    for flag in ("new_user_attestation_event", "original_direct_question_membership_enlarged", "underlying_data_rights_granted"):
                        self.assertIs(result[flag], False)
                    for stamp in bad_times:
                        with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                            self.validate(member, reviewed_at=stamp)
                else:
                    self.assertEqual(self.validate(member, reviewed_at=None)["status"], "SOURCE_BACKED")
                for key, value in (("source_id", "FGDC-4063"), ("source_sha256", "0" * 64)):
                    with self.subTest(binding=key), self.assertRaises(ValueError):
                        self.validate({**member, key: value}, root)
                for mutation in (
                    "root_attribute", "unrelated_context", "constraint_text", "constraint_attribute",
                    "constraint_child", "constraint_repeat", "constraint_missing", "security", "extension",
                ):
                    changed = copy.deepcopy(root)
                    node = changed.find("./idinfo/accconst")
                    if mutation == "root_attribute":
                        changed.set("unreviewed", "scope")
                    elif mutation == "unrelated_context":
                        ET.SubElement(changed, "unreviewed_context").text = "different source context"
                    elif mutation == "constraint_text":
                        node.text = "Unrestricted"
                    elif mutation == "constraint_attribute":
                        node.set("scope", "metadata")
                    elif mutation == "constraint_child":
                        ET.SubElement(node, "permission").text = "unreviewed"
                    elif mutation == "constraint_repeat":
                        changed.find("./idinfo").append(copy.deepcopy(node))
                    elif mutation == "constraint_missing":
                        changed.find("./idinfo").remove(node)
                    else:
                        ET.SubElement(changed.find("./metainfo"), "metsi" if mutation == "security" else "metextns")
                    with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                        self.validate(member, changed)

    def test_live_original_evidence_and_rehashed_missing_or_withdrawn_profiles_fail_closed(self):
        original_read = Path.read_bytes
        for evidence in self.profile["residual_resource_review"]["original_statement_references"]:
            target = REPO / evidence["manifest_path"]
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), evidence["manifest_sha256"])
            for mutation in ("changed", "missing"):
                def altered(path, _target=target, _mutation=mutation):
                    if path == _target:
                        if _mutation == "missing":
                            raise FileNotFoundError("withdrawn fixture evidence")
                        return original_read(path) + b" "
                    return original_read(path)

                with self.subTest(evidence=target.name, mutation=mutation), patch.object(Path, "read_bytes", altered):
                    self.assertEqual(interpretation.dataset_access_member_ids(REFERENCE(NEW)), frozenset())
                    for sid in ("FGDC-740", "FGDC-784"):
                        member = next(m for m in self.members if m["source_id"] == sid)
                        with self.assertRaises(ValueError):
                            self.validate(member)
        with tempfile.TemporaryDirectory() as tmp:
            forged = Path(tmp) / "forged.json"
            changed = copy.deepcopy(self.profile)
            changed["members"].append({"source_id": "FGDC-4063", "source_sha256": "0" * 64})
            changed["acquisition_contexts"]["FGDC-784"]["constraints"]["./metainfo/metuc"] = "None"
            atomic_json(forged, changed)
            representative_ids = {"FGDC-740", "FGDC-784"}
            for profile in (forged, Path(tmp) / "missing.json", None):
                with self.subTest(profile=str(profile)):
                    held, _ = self.classify(tmp, representative_ids, profile)
                    self.assertEqual(held["summary"]["source_status_counts"], {"supported": 0, "held": 2, "failed": 0})
            for ref in (
                {},
                REFERENCE(forged),
                {**REFERENCE(NEW), "manifest_path": str(forged)},
                {**REFERENCE(NEW), "manifest_sha256": "0" * 64},
                {**REFERENCE(NEW), "unreviewed_scope": "expanded"},
            ):
                with self.subTest(reference=ref), self.assertRaises(ValueError):
                    interpretation.validate_dataset_access_interpretation(
                        ref,
                        **self.members[0],
                        root=ET.parse(REPO / "FGDC" / (self.members[0]["source_id"] + ".xml")).getroot(),
                        reviewed_at=self.reviewed_at,
                    )

    def test_ten_smoke_then_exact_29_payload_and_xml_preservation_repeat_withdrawal_and_controls(self):
        self.assertEqual(len(SMOKE_IDS), 10)
        for selected in (SMOKE_IDS, IDS):
            with self.subTest(size=len(selected)), tempfile.TemporaryDirectory() as tmp:
                before, paths = self.classify(tmp, selected, OLD)
                self.assertEqual(before["summary"]["source_status_counts"], {"supported": 0, "held": len(selected), "failed": 0})
                payloads = {sid: read_json(Path(paths.zenodo_json_dir) / (sid + ".json")) for sid in selected}
                after, paths = self.classify(tmp, selected)
                self.assertEqual(after["summary"]["source_status_counts"], {"supported": len(selected), "held": 0, "failed": 0})
                for row in after["records"]:
                    sid = row["source_id"]
                    payload = read_json(Path(paths.zenodo_json_dir) / (sid + ".json"))
                    stripped = copy.deepcopy(payload)
                    self.assertEqual(stripped["artifact_policy"].pop("dataset_access_interpretation"), REFERENCE(NEW))
                    self.assertEqual(stripped, payloads[sid])
                    self.assertEqual(payload["metadata"]["access_right"], "restricted")
                    self.assertEqual(payload["metadata"]["license"], "")
                    self.assertEqual(row["rehosting_authority"], "USER_ATTESTED")
                    self.assertEqual(row["dataset_access_interpretation"], "SOURCE_BACKED" if sid in PHYSICAL_IDS else "REVIEWER_RECONCILED")
                    self.assertFalse(row["remote_verified"] or row["publication_approved"])
                    self.assertEqual(
                        (Path(paths.original_fgdc_dir) / (sid + ".xml")).read_bytes(),
                        (REPO / "FGDC" / (sid + ".xml")).read_bytes(),
                    )
                self.assertEqual(after, self.classify(tmp, selected)[0])
                self.assertEqual(before, self.classify(tmp, selected, OLD)[0])
        with tempfile.TemporaryDirectory() as tmp:
            before, paths = self.classify(tmp, CONTROLS, OLD)
            payloads = {sid: (Path(paths.zenodo_json_dir) / (sid + ".json")).read_bytes() for sid in CONTROLS}
            after, paths = self.classify(tmp, CONTROLS)
            self.assertEqual(after["summary"]["source_status_counts"], {"supported": 0, "held": 7, "failed": 0})
            # The selected profile fingerprint changes even when every source stays held.
            self.assertNotEqual(before['profile_sha256'], after['profile_sha256'])
            self.assertEqual(
                {k: v for k, v in before.items() if k != 'profile_sha256'},
                {k: v for k, v in after.items() if k != 'profile_sha256'},
            )
            for sid in CONTROLS:
                self.assertEqual((Path(paths.zenodo_json_dir) / (sid + ".json")).read_bytes(), payloads[sid])

    def test_agent_and_both_human_schemas_require_authority_restricted_rights_and_current_evidence(self):
        from scripts.agent_qa import assess_source
        from scripts.artifact_contract import prepare_artifact
        from scripts.qa_manifest import QA_CHECKS, validate_approval

        with tempfile.TemporaryDirectory() as tmp:
            held, _ = self.classify(tmp, IDS, authority=False)
            self.assertEqual(held["summary"]["source_status_counts"], {"supported": 0, "held": 29, "failed": 0})
        for sid in ("FGDC-740", "FGDC-784", "FGDC-1903"):
            with self.subTest(source_id=sid), tempfile.TemporaryDirectory() as tmp:
                _, paths = self.classify(tmp, {sid})
                path = Path(paths.zenodo_json_dir) / (sid + ".json")
                original = read_json(path)
                external = Path(tmp) / "reviewed-profile.json"
                external.write_bytes(NEW.read_bytes())
                original["artifact_policy"]["dataset_access_interpretation"] = REFERENCE(external)
                atomic_json(path, original)
                metadata, source, source_hash = prepare_metadata(str(path), paths)
                contract = prepare_artifact(original, source)
                entry = {
                    "environment": "sandbox", "deposition_id": 123, "json_file": str(path),
                    "source_sha256": source_hash, "metadata_sha256": metadata_hash(metadata),
                    "artifact_contract": contract, "zenodo_url": "https://sandbox.zenodo.org/deposit/123",
                }
                record = {
                    "fgdc_id": sid, "deposition_id": 123, "source_sha256": source_hash,
                    "metadata_sha256": entry["metadata_sha256"], "artifact_contract": contract,
                    "qa": {
                        "approved": True, "reviewer_type": "human", "reviewer": "Offline fixture",
                        "reviewed_at": self.reviewed_at, "rationale": "Fixture only",
                        "checks": dict.fromkeys(QA_CHECKS, True), "run_id": "fixture",
                        "review_revision": "fixture", "evidence": ["fixture"],
                    },
                    "duplicate_review": {
                        "status": "reviewed", "classification": "checked_no_match",
                        "rationale": "Fixture only", "evidence": ["fixture"],
                    },
                }
                for schema in (1, 2):
                    manifest = {"schema_version": schema, "source_revision": "fixture", "environment": "sandbox", "records": [record]}
                    validate_approval(manifest, sid, entry, paths)
                    assess_source(str(path), paths)
                    external.write_bytes(NEW.read_bytes() + b" ")
                    with self.assertRaises(ValueError):
                        validate_approval(manifest, sid, entry, paths)
                    with self.assertRaises(ValueError):
                        assess_source(str(path), paths)
                    external.write_bytes(NEW.read_bytes())
                    for fault in (
                        "withdraw", "authority", "policy_license", "metadata_license", "open",
                        "scope", "xpath", "date", "conflict", "old_time",
                    ):
                        changed = copy.deepcopy(original)
                        policy, raw_metadata = changed["artifact_policy"], changed["metadata"]
                        if fault == "withdraw":
                            policy.pop("dataset_access_interpretation")
                        elif fault == "authority":
                            policy.pop("rehosting_authority")
                        elif fault == "policy_license":
                            policy["license"] = "cc-zero"
                        elif fault == "metadata_license":
                            raw_metadata["license"] = "cc-zero"
                        elif fault == "open":
                            raw_metadata["access_right"] = "open"
                        elif fault == "scope":
                            policy["rights_scope"] = "underlying_dataset"
                        elif fault == "xpath":
                            policy["rights_source_xpath"] = "./idinfo/useconst"
                        elif fault == "date":
                            policy["date_semantics"] = "metadata_artifact_publication"
                        elif fault == "conflict":
                            policy["source_access_interpretation"] = REFERENCE(NEW)
                        else:
                            if sid in PHYSICAL_IDS:
                                continue
                            review_time = datetime.fromisoformat(self.profile["residual_resource_review"]["reviewed_at"])
                            policy["reviewed_at"] = (review_time - timedelta(seconds=1)).isoformat()
                        atomic_json(path, changed)
                        # Rights/authority faults must fail even with refreshed fixture hashes.
                        # Withdrawal invalidates the existing approval, so keep its old binding.
                        candidate_metadata, candidate_source, _ = prepare_metadata(str(path), paths)
                        candidate_contract = prepare_artifact(changed, candidate_source)
                        candidate_entry = {
                            **entry, "metadata_sha256": metadata_hash(candidate_metadata),
                            "artifact_contract": candidate_contract,
                        }
                        candidate_record = {
                            **record, "metadata_sha256": candidate_entry["metadata_sha256"],
                            "artifact_contract": candidate_contract,
                        }
                        candidate_manifest = {**manifest, "records": [candidate_record]}
                        if fault == "withdraw":
                            candidate_manifest, candidate_entry = manifest, entry
                        with self.subTest(schema=schema, fault=fault):
                            with self.assertRaises(ValueError):
                                validate_approval(candidate_manifest, sid, candidate_entry, paths)
                            with self.assertRaises(ValueError):
                                assess_source(str(path), paths)
                        atomic_json(path, original)


if __name__ == "__main__":
    unittest.main()
