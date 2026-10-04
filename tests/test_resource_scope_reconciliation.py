"""Finite resource controls and reviewer reconciliation preserve original statements."""

import copy
import hashlib
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.dataset_access_interpretation import validate_dataset_access_interpretation
from scripts.source_scope_attestation import validate_scope_attestation
from scripts.upload_service import (
    atomic_json,
    metadata_hash,
    prepare_metadata,
    read_json,
)
from tests import test_remaining_source_cohorts as previous

reference = previous.reference

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs/readiness/2026-10-03"
OLD = DOCS / "finite_source_resource_access_491.json"
NEW = DOCS / "finite_source_resource_access_514.json"
SCOPE_OLD = DOCS / "source_scope_attestation_821.json"
SCOPE_NEW = DOCS / "source_scope_reconciliation_904.json"
NEW_SHA = "203c050735a9dc755712acde70c0447b91f2bd6131dde53dd8195a0f2923d9a2"
RESOURCE_IDS = {m["source_id"] for m in read_json(NEW)["members"][491:]}
SCOPE_IDS = {m["source_id"] for m in read_json(SCOPE_NEW)["members"][821:]}
IDS = RESOURCE_IDS | SCOPE_IDS


class ResourceScopeReconciliationTests(unittest.TestCase):
    prepared = previous.RemainingSourceCohortTests.prepared

    def setUp(self):
        self.reviewed_at = previous.datetime.now(previous.timezone.utc).isoformat()

    def classify(self, tmp, ids, profile=NEW, scope=SCOPE_NEW, authority=True):
        return self.prepared(
            tmp,
            ids,
            authority=authority,
            replacements={"dataset_access_interpretation_manifest": profile,
                          "source_scope_attestation_manifest": scope},
        )

    def test_mixed_ten_then_exact106_delta_preserves_all_raw_metadata_and_xml(self):
        first_ten = set(sorted(RESOURCE_IDS)[:5] + sorted(SCOPE_IDS)[:5])
        with tempfile.TemporaryDirectory() as tmp:
            sample, _ = self.classify(tmp, first_ten)
            self.assertEqual(
                sample["summary"]["source_status_counts"],
                {"supported": 10, "held": 0, "failed": 0},
            )
            before, paths = self.classify(tmp, IDS, OLD, SCOPE_OLD)
            self.assertEqual(
                before["summary"]["source_status_counts"],
                {"supported": 0, "held": 106, "failed": 0},
            )
            metadata = {
                sid: read_json(Path(paths.zenodo_json_dir) / (sid + ".json"))[
                    "metadata"
                ]
                for sid in IDS
            }
            after, paths = self.classify(tmp, IDS)
            self.assertEqual(
                after["summary"]["source_status_counts"],
                {"supported": 106, "held": 0, "failed": 0},
            )
            for row in after["records"]:
                sid = row["source_id"]
                payload = read_json(Path(paths.zenodo_json_dir) / (sid + ".json"))
                self.assertEqual(payload["metadata"], metadata[sid])
                self.assertEqual(payload["metadata"]["access_right"], "restricted")
                self.assertEqual(payload["metadata"]["license"], "")
                self.assertEqual(
                    (Path(paths.original_fgdc_dir) / (sid + ".xml")).read_bytes(),
                    (REPO / "FGDC" / (sid + ".xml")).read_bytes(),
                )
                self.assertFalse(row["remote_verified"])
                self.assertFalse(row["publication_approved"])
            repeated, _ = self.classify(tmp, IDS)
            self.assertEqual(after, repeated)
            withdrawn, _ = self.classify(tmp, IDS, OLD, SCOPE_OLD)
            self.assertEqual(before, withdrawn)

    def test_additive_profiles_preserve_all_previous_objects_and_distinct_provenance(self):
        old, new = read_json(OLD), read_json(NEW)
        self.assertEqual(hashlib.sha256(NEW.read_bytes()).hexdigest(), NEW_SHA)
        self.assertEqual(new["members"][:491], old["members"])
        self.assertEqual(new["source_contexts"], old["source_contexts"])
        self.assertEqual({m["source_id"] for m in new["members"][491:]}, RESOURCE_IDS)
        self.assertEqual(len(RESOURCE_IDS), 23)
        for sid, value in old["acquisition_contexts"].items():
            self.assertEqual(new["acquisition_contexts"][sid], value)
        before, after = read_json(SCOPE_OLD), read_json(SCOPE_NEW)
        prior = copy.deepcopy(after)
        prior.pop("reconciled_scope_review")
        prior["members"] = prior["members"][:821]
        self.assertEqual(prior, before)
        self.assertEqual(len(SCOPE_IDS), 83)
        self.assertEqual(len(IDS), 106)
        resource = {m["source_id"]: m for m in new["members"]}
        scopes = {m["source_id"]: m for m in after["members"]}
        for sid in IDS:
            raw = (REPO / "FGDC" / (sid + ".xml")).read_bytes()
            if sid in RESOURCE_IDS:
                member = resource[sid]
                result = validate_dataset_access_interpretation(reference(NEW), sid, member["source_sha256"], ET.fromstring(raw))
                self.assertEqual(result["status"], "SOURCE_BACKED")
            else:
                member = scopes[sid]
                result = validate_scope_attestation(reference(SCOPE_NEW), sid, member["source_sha256"], ET.fromstring(raw), self.reviewed_at)
                self.assertEqual(result["status"], "REVIEWER_RECONCILED")
            self.assertEqual(hashlib.sha256(raw).hexdigest(), member["source_sha256"])
            self.assertFalse(result["grants_rehosting"])
            self.assertFalse(result["grants_new_license"])
            self.assertFalse(result["publication_approved"])
        sid = before["members"][0]["source_id"]
        result = validate_scope_attestation(reference(SCOPE_NEW), sid, scopes[sid]["source_sha256"], ET.parse(REPO / "FGDC" / (sid + ".xml")).getroot(), self.reviewed_at)
        self.assertEqual(result["status"], "USER_ATTESTED")
        self.assertEqual(result["statement"], before["statement"])

    def test_complete_context_and_metadata_security_changes_fail_closed(self):
        members = {m["source_id"]: m for m in read_json(NEW)["members"]}
        for sid in ("FGDC-218", "FGDC-2228", "FGDC-828"):
            root = ET.parse(REPO / "FGDC" / (sid + ".xml")).getroot()
            for xpath in (
                "./idinfo/useconst",
                "./distinfo/distliab",
                "./idinfo/descript/abstract",
            ):
                changed = copy.deepcopy(root)
                node = changed.find(xpath)
                self.assertIsNotNone(node)
                node.text = "Changed or resolved without source evidence"
                with self.subTest(sid=sid, xpath=xpath), self.assertRaises(ValueError):
                    validate_dataset_access_interpretation(
                        reference(NEW), sid, members[sid]["source_sha256"], changed
                    )
            for tag in ("metsi", "metextns"):
                changed = copy.deepcopy(root)
                ET.SubElement(changed.find("./metainfo"), tag)
                with self.assertRaises(ValueError):
                    validate_dataset_access_interpretation(
                        reference(NEW), sid, members[sid]["source_sha256"], changed
                    )

    def test_missing_authority_forged_manifest_and_unrelated_holds_remain_held(self):
        controls = {"FGDC-53", "FGDC-563", "FGDC-4060", "FGDC-885", "FGDC-1422", "FGDC-233", "FGDC-1257", "FGDC-10"}
        ids = IDS | controls
        with tempfile.TemporaryDirectory() as tmp:
            no_authority, _ = self.classify(tmp, ids, authority=False)
            self.assertTrue(
                all(r["source_status"] == "held" for r in no_authority["records"])
            )
            valid, _ = self.classify(tmp, ids)
            rows = {r["source_id"]: r for r in valid["records"]}
            self.assertTrue(
                all(rows[sid]["source_status"] == "held" for sid in controls)
            )
            forged = read_json(NEW)
            forged["acquisition_contexts"]["FGDC-218"]["constraints"][
                "./idinfo/useconst"
            ] = "None"
            target = Path(tmp) / "forged.json"
            atomic_json(target, forged)
            for profile in (target, Path(tmp) / "missing.json", None):
                held, _ = self.classify(tmp, ids, profile, SCOPE_OLD)
                self.assertTrue(
                    all(r["source_status"] == "held" for r in held["records"])
                )

    def test_agent_and_both_human_routes_reject_evidence_or_policy_changes(self):
        from scripts.agent_qa import assess_source
        from scripts.artifact_contract import prepare_artifact
        from scripts.qa_manifest import QA_CHECKS, validate_approval

        sid = "FGDC-218"
        with tempfile.TemporaryDirectory() as tmp:
            _, paths = self.classify(tmp, {sid})
            path = Path(paths.zenodo_json_dir) / (sid + ".json")
            payload = read_json(path)
            external = Path(tmp) / "evidence.json"
            external.write_bytes(NEW.read_bytes())
            payload["artifact_policy"]["dataset_access_interpretation"] = reference(
                external
            )
            atomic_json(path, payload)
            metadata, source, digest = prepare_metadata(str(path), paths)
            entry = {
                "environment": "sandbox",
                "deposition_id": 123,
                "json_file": str(path),
                "source_sha256": digest,
                "metadata_sha256": metadata_hash(metadata),
                "artifact_contract": prepare_artifact(payload, source),
                "zenodo_url": "https://sandbox.zenodo.org/deposit/123",
            }
            record = {
                "fgdc_id": sid,
                "deposition_id": 123,
                "source_sha256": digest,
                "metadata_sha256": entry["metadata_sha256"],
                "artifact_contract": entry["artifact_contract"],
                "qa": {
                    "approved": True,
                    "reviewer_type": "human",
                    "reviewer": "Offline fixture",
                    "reviewed_at": self.reviewed_at,
                    "rationale": "Fixture only",
                    "checks": dict.fromkeys(QA_CHECKS, True),
                    "run_id": "fixture",
                    "review_revision": "fixture",
                    "evidence": ["fixture"],
                },
                "duplicate_review": {
                    "status": "reviewed",
                    "classification": "checked_no_match",
                    "rationale": "Fixture only",
                    "evidence": ["fixture"],
                },
            }
            for schema in (1, 2):
                manifest = {
                    "schema_version": schema,
                    "source_revision": "fixture",
                    "environment": "sandbox",
                    "records": [record],
                }
                validate_approval(manifest, sid, entry, paths)
                assess_source(str(path), paths)
                external.write_bytes(NEW.read_bytes() + b" ")
                with self.assertRaises(ValueError):
                    assess_source(str(path), paths)
                with self.assertRaises(ValueError):
                    validate_approval(manifest, sid, entry, paths)
                external.write_bytes(NEW.read_bytes())
                for fault in ("withdraw", "license", "open", "conflict"):
                    changed = copy.deepcopy(payload)
                    if fault == "withdraw":
                        changed["artifact_policy"].pop("dataset_access_interpretation")
                    elif fault == "license":
                        changed["metadata"]["license"] = "cc-zero"
                    elif fault == "open":
                        changed["metadata"]["access_right"] = "open"
                    else:
                        changed["artifact_policy"]["source_scope_attestation"] = (
                            reference(DOCS / "source_scope_attestation_821.json")
                        )
                    atomic_json(path, changed)
                    with (
                        self.subTest(schema=schema, fault=fault),
                        self.assertRaises(ValueError),
                    ):
                        assess_source(str(path), paths)
                    with (
                        self.subTest(schema=schema, fault=fault),
                        self.assertRaises(ValueError),
                    ):
                        validate_approval(manifest, sid, entry, paths)
                    atomic_json(path, payload)


if __name__ == "__main__":
    unittest.main()
