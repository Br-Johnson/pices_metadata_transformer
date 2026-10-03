"""Exact GIS copy-media cohort preserves Unknown and unrelated source holds."""

import copy
import hashlib
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.dataset_access_interpretation import validate_dataset_access_interpretation
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
OLD = DOCS / "finite_source_resource_access_469.json"
NEW = DOCS / "finite_source_resource_access_491.json"
NEW_SHA = "13e82e2375da3bf17cf352fff7a8cda43fa6d781a3e436ca7321c8428ac77abe"
IDS = {
    "FGDC-" + str(i)
    for i in (
        607,
        638,
        645,
        646,
        692,
        695,
        698,
        702,
        704,
        713,
        722,
        727,
        738,
        744,
        745,
        746,
        747,
        765,
        772,
        773,
        774,
        776,
    )
}


class CNFCopyMediaAccessTests(unittest.TestCase):
    prepared = previous.RemainingSourceCohortTests.prepared

    def setUp(self):
        self.reviewed_at = "2026-10-03T23:00:00+00:00"

    def classify(self, tmp, ids, profile=NEW, authority=True):
        return self.prepared(
            tmp,
            ids,
            authority=authority,
            replacements={"dataset_access_interpretation_manifest": profile},
        )

    def test_limit_ten_then_exact22_delta_preserves_all_raw_metadata_and_xml(self):
        first_ten = set(sorted(IDS)[:10])
        with tempfile.TemporaryDirectory() as tmp:
            sample, _ = self.classify(tmp, first_ten)
            self.assertEqual(
                sample["summary"]["source_status_counts"],
                {"supported": 10, "held": 0, "failed": 0},
            )
            before, paths = self.classify(tmp, IDS, OLD)
            self.assertEqual(
                before["summary"]["source_status_counts"],
                {"supported": 0, "held": 22, "failed": 0},
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
                {"supported": 22, "held": 0, "failed": 0},
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
            withdrawn, _ = self.classify(tmp, IDS, OLD)
            self.assertEqual(before, withdrawn)

    def test_additive491_pin_preserves469_objects_and_validates_every_member(self):
        old, new = read_json(OLD), read_json(NEW)
        self.assertEqual(hashlib.sha256(NEW.read_bytes()).hexdigest(), NEW_SHA)
        self.assertEqual(new["members"][:469], old["members"])
        self.assertEqual(new["source_contexts"], old["source_contexts"])
        self.assertEqual({m["source_id"] for m in new["members"][469:]}, IDS)
        self.assertEqual(
            new["prior_manifest_sha256"], reference(OLD)["manifest_sha256"]
        )
        for sid, context in old["acquisition_contexts"].items():
            self.assertEqual(new["acquisition_contexts"][sid], context)
        for member in new["members"]:
            sid = member["source_id"]
            raw = (REPO / "FGDC" / (sid + ".xml")).read_bytes()
            result = validate_dataset_access_interpretation(
                reference(NEW), sid, member["source_sha256"], ET.fromstring(raw)
            )
            self.assertFalse(result["grants_rehosting"])
            self.assertFalse(result["grants_new_license"])
            self.assertFalse(result["publication_approved"])
        for sid in IDS:
            self.assertEqual(
                new["acquisition_contexts"][sid]["constraints"],
                {
                    "./idinfo/accconst": "Available upon request at cost of copy media.",
                    "./idinfo/useconst": "Unknown",
                    "./metainfo/metac": "Available upon request at cost of copy media.",
                    "./metainfo/metuc": "Unknown",
                },
            )
            self.assertIn(".", new["acquisition_contexts"][sid]["context_elements"])

    def test_complete_context_and_metadata_security_changes_fail_closed(self):
        members = {m["source_id"]: m for m in read_json(NEW)["members"]}
        for sid in ("FGDC-607", "FGDC-747", "FGDC-765"):
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
        controls = {"FGDC-1890", "FGDC-1422", "FGDC-233", "FGDC-218", "FGDC-1257"}
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
            forged["acquisition_contexts"]["FGDC-607"]["constraints"][
                "./idinfo/useconst"
            ] = "None"
            target = Path(tmp) / "forged.json"
            atomic_json(target, forged)
            for profile in (target, Path(tmp) / "missing.json", None):
                held, _ = self.classify(tmp, ids, profile)
                self.assertTrue(
                    all(r["source_status"] == "held" for r in held["records"])
                )

    def test_agent_and_both_human_routes_reject_evidence_or_policy_changes(self):
        from scripts.agent_qa import assess_source
        from scripts.artifact_contract import prepare_artifact
        from scripts.qa_manifest import QA_CHECKS, validate_approval

        sid = "FGDC-765"
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
