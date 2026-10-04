"""Five residual interpretations stay finite, reversible and rights-neutral.

The new review binds whole XML objects while preserving prior statements and
USER_ATTESTED restoration authority; it cannot grant underlying-data rights.
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
from scripts.upload_service import atomic_json, read_json
from tests import test_resource42_reconciliation as previous

REPO = previous.REPO
OLD = previous.NEW
NEW = REPO / "docs/readiness/2026-10-04/residual_source_access_561.json"
REFERENCE = previous.previous.reference
EXPECTED = {
    "FGDC-1257": "343d0e1b6c7d96a3899dfe5173b84ce12f8a5174d77b7fbdf65a897a00416b42",
    "FGDC-1258": "fb72564a17bf0535a1cfeaab04dd92d674dcb164ce4d608cdd17c19a5b1bfac9",
    "FGDC-1262": "3b9761159b7036598d96e2fcee9651c8f1c32428840106c4edb5cf53483d93cc",
    "FGDC-1273": "02957d0e04f214f4f02b72487d71923b613c01d81133967b17c2381626b1309a",
    "FGDC-4064": "1b3891fe9136b5a95182c3e0b5a06929a7524870ba09479fd59c5148da26806c",
}
IDS = set(EXPECTED)
CONTROL = "FGDC-4063"


class ResidualSourceAccessTests(unittest.TestCase):
    prepared = previous.Resource42Tests.prepared
    human_routes = previous.Resource42Tests.human_routes

    def setUp(self):
        self.reviewed_at = datetime.now(timezone.utc).isoformat()
        self.profile = read_json(NEW)
        self.members = self.profile["members"][556:]

    def classify(self, tmp, ids, profile=NEW, authority=True):
        return self.prepared(
            tmp,
            ids,
            authority=authority,
            replacements={
                "dataset_access_interpretation_manifest": profile,
                "source_scope_attestation_manifest": previous.previous.SCOPE_NEW,
            },
        )

    def validate(self, member, root=None, **kwargs):
        if root is None:
            root = ET.parse(REPO / "FGDC" / (member["source_id"] + ".xml")).getroot()
        options = {"reviewed_at": self.reviewed_at, **kwargs}
        return interpretation.validate_dataset_access_interpretation(
            REFERENCE(NEW), **member, root=root, **options
        )

    def test_exact_additive_membership_pin_and_unchanged_prior_evidence(self):
        old = read_json(OLD)
        self.assertEqual(len(self.profile["members"]), 561)
        self.assertEqual(self.profile["members"][:556], old["members"])
        self.assertEqual(self.profile["source_contexts"], old["source_contexts"])
        self.assertEqual(
            self.profile["resource_reconciliation_review"],
            old["resource_reconciliation_review"],
        )
        for sid, context in old["acquisition_contexts"].items():
            self.assertEqual(self.profile["acquisition_contexts"][sid], context)
        self.assertEqual(
            {m["source_id"]: m["source_sha256"] for m in self.members}, EXPECTED
        )
        review = self.profile["residual_source_review"]
        self.assertEqual(review["members"], self.members)
        self.assertTrue(review["original_statement_references"])
        self.assertEqual(
            hashlib.sha256(NEW.read_bytes()).hexdigest(),
            interpretation.RESIDUAL_SOURCE_MANIFEST_SHA256,
        )
        self.assertNotIn(CONTROL, interpretation.dataset_access_member_ids(REFERENCE(NEW)))
        scope_ids = {
            m["source_id"] for m in read_json(previous.previous.SCOPE_NEW)["members"]
        }
        self.assertFalse(IDS & scope_ids)
        with patch.object(interpretation, "RESIDUAL_SOURCE_MANIFEST_SHA256", "unaccepted"):
            self.assertEqual(interpretation.dataset_access_member_ids(REFERENCE(NEW)), frozenset())
            with self.assertRaises(ValueError):
                self.validate(self.members[0])

    def test_all_five_source_hashes_and_review_provenance_grant_no_new_rights(self):
        for member in self.members:
            with self.subTest(source_id=member["source_id"]):
                raw = (REPO / "FGDC" / (member["source_id"] + ".xml")).read_bytes()
                self.assertEqual(hashlib.sha256(raw).hexdigest(), member["source_sha256"])
                result = self.validate(member, ET.fromstring(raw))
                self.assertEqual(result["status"], "REVIEWER_RECONCILED")
                self.assertEqual(
                    result["reconciliation_reviewed_at"],
                    self.profile["residual_source_review"]["reviewed_at"],
                )
                for flag in (
                    "new_user_attestation_event",
                    "original_direct_question_membership_enlarged",
                    "underlying_data_rights_granted",
                    "grants_rehosting",
                    "grants_new_license",
                    "publication_approved",
                ):
                    self.assertIs(result[flag], False)
                for key, value in (("source_id", CONTROL), ("source_sha256", "0" * 64)):
                    with self.subTest(key=key), self.assertRaises(ValueError):
                        self.validate({**member, key: value}, ET.fromstring(raw))

    def test_all_prior_556_status_objects_and_user_attested_scope_are_preserved(self):
        from scripts.source_scope_attestation import validate_scope_attestation

        for member in read_json(OLD)["members"]:
            root = ET.parse(REPO / "FGDC" / (member["source_id"] + ".xml")).getroot()
            before = interpretation.validate_dataset_access_interpretation(
                REFERENCE(OLD), **member, root=root, reviewed_at=self.reviewed_at
            )
            with self.subTest(source_id=member["source_id"]):
                self.assertEqual(self.validate(member, root), before)
        scope = read_json(previous.previous.SCOPE_OLD)
        member = scope["members"][0]
        result = validate_scope_attestation(
            REFERENCE(previous.previous.SCOPE_NEW),
            member["source_id"],
            member["source_sha256"],
            ET.parse(REPO / "FGDC" / (member["source_id"] + ".xml")).getroot(),
            self.reviewed_at,
        )
        self.assertEqual(result["status"], "USER_ATTESTED")
        self.assertEqual(result["statement"], scope["statement"])

    def test_full_source_object_and_plain_constraints_reject_malformed_or_changed_roots(self):
        for member in self.members:
            original = ET.parse(REPO / "FGDC" / (member["source_id"] + ".xml")).getroot()
            for mutation in (
                "empty", "root_tag", "root_attribute", "unrelated_context", "extra_element",
                "constraint_text", "constraint_attribute", "constraint_child", "constraint_repeat",
                "constraint_missing", "security", "extension",
            ):
                root = copy.deepcopy(original)
                node = root.find("./idinfo/accconst")
                if mutation == "empty":
                    root = ET.Element("metadata")
                elif mutation == "root_tag":
                    root.tag = "unreviewed"
                elif mutation == "root_attribute":
                    root.set("scope", "unreviewed")
                elif mutation == "unrelated_context":
                    root.find("./metainfo/metd").text = "20990101"
                elif mutation == "extra_element":
                    ET.SubElement(root, "unreviewed").text = "unreviewed metadata product"
                elif mutation == "constraint_text":
                    node.text = "Unrestricted"
                elif mutation == "constraint_attribute":
                    node.set("scope", "metadata")
                elif mutation == "constraint_child":
                    ET.SubElement(node, "permission").text = "unreviewed"
                elif mutation == "constraint_repeat":
                    root.find("./idinfo").append(copy.deepcopy(node))
                elif mutation == "constraint_missing":
                    root.find("./idinfo").remove(node)
                else:
                    ET.SubElement(root.find("./metainfo"), "metsi" if mutation == "security" else "metextns")
                with self.subTest(source_id=member["source_id"], mutation=mutation), self.assertRaises(ValueError):
                    self.validate(member, root)

    def test_review_time_is_aware_current_and_after_this_review(self):
        reviewed = datetime.fromisoformat(self.profile["residual_source_review"]["reviewed_at"])
        for stamp in (
            None,
            "not-a-time",
            123,
            reviewed.replace(tzinfo=None).isoformat(),
            (reviewed - timedelta(seconds=1)).isoformat(),
            (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        ):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                self.validate(self.members[0], reviewed_at=stamp)
        self.assertEqual(
            self.validate(self.members[0], reviewed_at=reviewed.isoformat())["status"],
            "REVIEWER_RECONCILED",
        )

    def test_original_statement_evidence_is_live_for_both_review_blocks(self):
        original_read = Path.read_bytes
        references = {
            e["manifest_path"]: e
            for block in ("resource_reconciliation_review", "residual_source_review")
            for e in self.profile[block]["original_statement_references"]
        }
        for relative, evidence in references.items():
            target = REPO / relative
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), evidence["manifest_sha256"])
            for mutation in ("changed", "missing"):
                def altered(path, _target=target, _mutation=mutation):
                    if path == _target:
                        if _mutation == "missing":
                            raise FileNotFoundError("withdrawn fixture evidence")
                        return original_read(path) + b" "
                    return original_read(path)

                with self.subTest(evidence=relative, mutation=mutation), patch.object(Path, "read_bytes", altered):
                    self.assertEqual(interpretation.dataset_access_member_ids(REFERENCE(NEW)), frozenset())
                    with self.assertRaises(ValueError):
                        self.validate(self.members[0])

    def test_exact_five_delta_metadata_xml_preservation_repeat_and_withdrawal(self):
        selected = IDS | {CONTROL}
        with tempfile.TemporaryDirectory() as tmp:
            before, paths = self.classify(tmp, selected, OLD)
            self.assertEqual(before["summary"]["source_status_counts"], {"supported": 0, "held": 6, "failed": 0})
            metadata = {
                sid: read_json(Path(paths.zenodo_json_dir) / (sid + ".json"))["metadata"]
                for sid in selected
            }
            after, paths = self.classify(tmp, selected)
            self.assertEqual(after["summary"]["source_status_counts"], {"supported": 5, "held": 1, "failed": 0})
            for row in after["records"]:
                sid = row["source_id"]
                payload = read_json(Path(paths.zenodo_json_dir) / (sid + ".json"))
                self.assertEqual(payload["metadata"], metadata[sid])
                self.assertEqual(payload["metadata"]["access_right"], "restricted")
                self.assertEqual(payload["metadata"]["license"], "")
                self.assertEqual(row["rehosting_authority"], "USER_ATTESTED")
                self.assertEqual(row["source_status"], "held" if sid == CONTROL else "supported")
                if sid == CONTROL:
                    self.assertNotIn("dataset_access_interpretation", row)
                else:
                    self.assertEqual(row["dataset_access_interpretation"], "REVIEWER_RECONCILED")
                self.assertFalse(row["remote_verified"] or row["publication_approved"])
                self.assertEqual(
                    (Path(paths.original_fgdc_dir) / (sid + ".xml")).read_bytes(),
                    (REPO / "FGDC" / (sid + ".xml")).read_bytes(),
                )
            before_control = next(row for row in before["records"] if row["source_id"] == CONTROL)
            self.assertEqual(next(row for row in after["records"] if row["source_id"] == CONTROL), before_control)
            repeated, _ = self.classify(tmp, selected)
            self.assertEqual(after, repeated)
            withdrawn, _ = self.classify(tmp, selected, OLD)
            self.assertEqual(before, withdrawn)

    def test_agent_and_both_human_routes_revalidate_radio_and_post_database(self):
        for sid in ("FGDC-1257", "FGDC-4064"):
            with self.subTest(source_id=sid):
                self.human_routes(sid, "dataset_access_interpretation", NEW)

    def test_rehashed_cache_cannot_change_complete_creators_or_erase_source_context(self):
        from scripts.agent_qa import assess_source

        for sid in ("FGDC-1257", "FGDC-4064"):
            with tempfile.TemporaryDirectory() as tmp:
                baseline, paths = self.classify(tmp, {sid})
                payload_path = Path(paths.zenodo_json_dir) / (sid + ".json")
                original = read_json(payload_path)
                report_path = Path(tmp) / "output/classification.json"
                for mutation in ("creator_object", "retained_citation"):
                    payload = copy.deepcopy(original)
                    if mutation == "creator_object":
                        payload["metadata"]["creators"][0]["affiliation"] = "Unreviewed organization"
                    else:
                        payload["metadata"]["notes"] = ""
                    atomic_json(payload_path, payload)
                    forged_cache = copy.deepcopy(baseline)
                    forged_cache["records"][0]["prepared_payload_sha256"] = hashlib.sha256(payload_path.read_bytes()).hexdigest()
                    atomic_json(report_path, forged_cache)
                    with self.subTest(source_id=sid, mutation=mutation):
                        with self.assertRaises(ValueError):
                            assess_source(str(payload_path), paths)
                        held, _ = self.classify(tmp, {sid})
                        self.assertEqual(held["summary"]["source_status_counts"], {"supported": 0, "held": 1, "failed": 0})

    def test_forged_rehashed_and_withdrawn_profiles_cannot_clear_the_five(self):
        with tempfile.TemporaryDirectory() as tmp:
            forged = Path(tmp) / "forged.json"
            altered = copy.deepcopy(self.profile)
            altered["members"].append({"source_id": CONTROL, "source_sha256": "0" * 64})
            atomic_json(forged, altered)
            for profile in (forged, Path(tmp) / "withdrawn.json", None):
                with self.subTest(profile=str(profile)):
                    held, _ = self.classify(tmp, IDS, profile)
                    self.assertEqual(held["summary"]["source_status_counts"], {"supported": 0, "held": 5, "failed": 0})
            for reference in (
                {},
                {**REFERENCE(NEW), "manifest_path": str(forged)},
                REFERENCE(forged),
                {**REFERENCE(NEW), "manifest_sha256": "0" * 64},
            ):
                with self.subTest(reference=reference), self.assertRaises(ValueError):
                    interpretation.validate_dataset_access_interpretation(
                        reference, **self.members[0],
                        root=ET.parse(REPO / "FGDC" / (self.members[0]["source_id"] + ".xml")).getroot(),
                        reviewed_at=self.reviewed_at,
                    )

    def test_separate_authority_and_restricted_unlicensed_policy_are_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            held, _ = self.classify(tmp, IDS, authority=False)
            self.assertEqual(held["summary"]["source_status_counts"], {"supported": 0, "held": 5, "failed": 0})
            _, paths = self.classify(tmp, IDS)
            for member in self.members:
                sid = member["source_id"]
                payload = read_json(Path(paths.zenodo_json_dir) / (sid + ".json"))
                root = ET.parse(REPO / "FGDC" / (sid + ".xml")).getroot()
                for fault in ("authority", "policy_license", "metadata_license", "open", "scope", "xpath", "date", "conflict"):
                    policy = copy.deepcopy(payload["artifact_policy"])
                    metadata = copy.deepcopy(payload["metadata"])
                    if fault == "authority":
                        policy.pop("rehosting_authority")
                    elif fault == "policy_license":
                        policy["license"] = "cc-zero"
                    elif fault == "metadata_license":
                        metadata["license"] = "cc-zero"
                    elif fault == "open":
                        metadata["access_right"] = "open"
                    elif fault == "scope":
                        policy["rights_scope"] = "underlying_dataset"
                    elif fault == "xpath":
                        policy["rights_source_xpath"] = "./idinfo/useconst"
                    elif fault == "date":
                        policy["date_semantics"] = "dataset_date"
                    else:
                        policy["source_access_interpretation"] = REFERENCE(NEW)
                    with self.subTest(source_id=sid, fault=fault), self.assertRaises(ValueError):
                        interpretation.validate_dataset_access_policy(
                            policy, sid, member["source_sha256"], root, metadata
                        )


if __name__ == "__main__":
    unittest.main()
