"""Three finite external credits preserve source context and independent QA gates."""

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from scripts import citation_creator_interpretation as interpretation
from scripts.path_config import OutputPaths
from scripts.upload_service import (
    atomic_json,
    metadata_hash,
    prepare_metadata,
    read_json,
)

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs/readiness/2026-10-04"
PREVIOUS = REPO / "docs/readiness/2026-10-03/source_citation_credits_409.json"
NEW = DOCS / "source_citation_credits_412.json"
PROPOSALS = DOCS / "residual_creator3_proposals.json"
IDS = {"FGDC-10", "FGDC-3957", "FGDC-3961"}
CONTROL = "FGDC-3954"
EXPECTED = {
    "FGDC-10": [{"name": "Jarrett, N.E."}, {"name": "E.L. Bousfield"}],
    "FGDC-3957": [{"name": "Office of Marine Prediction, the JMA"}],
    "FGDC-3961": [
        {"name": "Office of Marine Prediction of the Japan Meteorological Agency"}
    ],
}


def reference(path):
    return {
        "manifest_path": str(path),
        "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


class ResidualCreator3Tests(unittest.TestCase):
    # Adapt the bounded source-credit fixtures without importing a TestCase class:
    # unittest discovery must load only these four new contracts.
    def setUp(self):
        self.reviewed_at = datetime.now(timezone.utc).isoformat()
        self.manifest = read_json(NEW)
        self.prior = read_json(PREVIOUS)
        self.added = self.manifest["cohorts"][len(self.prior["cohorts"]) :]
        self.profiles = {
            member["source_id"]: cohort
            for cohort in self.added
            for member in cohort["members"]
        }

    def prepared(self, tmp, ids, creators=NEW, authority=True):
        from scripts.collection_qa import classify_collection

        source = Path(tmp) / "sources"
        source.mkdir(exist_ok=True)
        for stale in source.glob("*.xml"):
            if stale.stem not in ids:
                stale.unlink()
        for sid in ids:
            shutil.copyfile(REPO / "FGDC" / (sid + ".xml"), source / (sid + ".xml"))
        output = Path(tmp) / "output"
        old = REPO / "docs/readiness/2026-10-02"
        previous = REPO / "docs/readiness/2026-10-03"
        report = classify_collection(
            source,
            output,
            self.reviewed_at,
            authority_manifest=old / "rehosting_authority.json" if authority else None,
            access_interpretation_manifest=old / "contact_source_interpretation.json",
            creator_interpretation_manifest=old / "exxon_citation_interpretation.json",
            dataset_access_interpretation_manifest=DOCS
            / "finite_source_resource_access_563.json",
            contributor_access_interpretation_manifest=old
            / "contributor_source_interpretation.json",
            collective_creator_interpretation_manifest=previous
            / "dfo_staff_citation_interpretation.json",
            institution_creator_interpretation_manifest=creators,
            source_link_interpretation_manifest=previous
            / "historical_dataset_linkage_21.json",
            source_title_interpretation_manifest=previous
            / "source_display_titles_35.json",
            source_scope_attestation_manifest=previous
            / "source_scope_reconciliation_904.json",
        )
        return report, OutputPaths(str(output), "sandbox")

    def source(self, sid):
        raw = (REPO / "FGDC" / (sid + ".xml")).read_bytes()
        return hashlib.sha256(raw).hexdigest(), ET.fromstring(raw)

    def human_fixture(self, sid, paths):
        from scripts.artifact_contract import prepare_artifact
        from scripts.qa_manifest import QA_CHECKS, prepare_manifest

        path = Path(paths.zenodo_json_dir) / (sid + ".json")
        payload = read_json(path)
        metadata, source, source_sha = prepare_metadata(str(path), paths)
        entry = {
            "environment": "sandbox",
            "zenodo_url": "https://sandbox.zenodo.org/deposit/123",
            "deposition_id": 123,
            "upload_status": "success",
            "publish_status": "draft",
            "success": True,
            "json_file": str(path),
            "source_sha256": source_sha,
            "metadata_sha256": metadata_hash(metadata),
            "artifact_contract": prepare_artifact(payload, source),
        }
        atomic_json(paths.uploads_registry_path, {sid: entry})
        manifest = prepare_manifest(paths)
        record = manifest["records"][0]
        record["qa"].update(
            approved=True,
            reviewer_type="human",
            reviewer="Offline fixture",
            reviewed_at=self.reviewed_at,
            rationale="Dummy contract fixture only",
            checks=dict.fromkeys(QA_CHECKS, True),
            run_id="fixture",
            review_revision=manifest["source_revision"],
            evidence=["fixture"],
        )
        record["duplicate_review"].update(
            status="reviewed",
            classification="checked_no_match",
            rationale="Offline fixture only",
            evidence=["fixture"],
        )
        return path, payload, metadata, entry, manifest

    def assert_shared_rejection(self, sid, path, paths, metadata, entry, manifest):
        from scripts.agent_qa import assess_source
        from scripts.qa_manifest import validate_approval

        with self.assertRaises(ValueError):
            assess_source(str(path), paths)
        for schema in (1, 2):
            manifest["schema_version"] = schema
            with self.subTest(source=sid, schema=schema), self.assertRaises(ValueError):
                validate_approval(manifest, sid, entry, paths, metadata)

    def test_additive_412_preserves_409_and_exact_complete_three_credit_objects(self):
        self.assertEqual(
            self.manifest["cohorts"][: len(self.prior["cohorts"])],
            self.prior["cohorts"],
        )
        self.assertEqual(
            self.manifest["previous_cohort_count"], len(self.prior["cohorts"])
        )
        self.assertEqual(
            self.manifest["prior_manifest_sha256"],
            reference(PREVIOUS)["manifest_sha256"],
        )
        self.assertEqual(
            reference(NEW)["manifest_sha256"],
            interpretation.SOURCE_CREDIT_412_MANIFEST_SHA256,
        )
        self.assertEqual(sum(len(c["members"]) for c in self.manifest["cohorts"]), 412)
        all_ids = [
            m["source_id"] for c in self.manifest["cohorts"] for m in c["members"]
        ]
        self.assertEqual(len(set(all_ids)), 412)
        self.assertEqual(set(self.profiles), IDS)
        self.assertEqual(len(self.added), 3)
        proposals = {p["source_id"]: p for p in read_json(PROPOSALS)["proposals"]}
        for sid in sorted(IDS):
            cohort = self.profiles[sid]
            sha, root = self.source(sid)
            self.assertEqual(
                cohort["members"], [{"source_id": sid, "source_sha256": sha}]
            )
            self.assertEqual(cohort["creators"], EXPECTED[sid])
            self.assertTrue(
                all(set(creator) == {"name"} for creator in cohort["creators"])
            )
            for field in (
                "creators",
                "context_note",
                "primary_origin_element",
                "supplemental_source_elements",
                "external_credit_evidence",
            ):
                self.assertEqual(
                    cohort[field], proposals[sid]["proposed_cohort"][field]
                )
            self.assertEqual(
                cohort["supplemental_source_elements"],
                [{"xpath": ".", "element": interpretation.source_element(root)}],
            )
            self.assertEqual(
                cohort["evidence_type"], "EXTERNAL_SOURCE_SUPPORTED_SAME_WORK_CITATION"
            )
            self.assertEqual(
                interpretation.validate_creator_interpretation(
                    reference(NEW), sid, sha, root
                ),
                EXPECTED[sid],
            )
            self.assertEqual(
                root.find("./idinfo/citation/citeinfo/origin").text,
                "83 Havelock St." if sid == "FGDC-10" else None,
            )

    def test_full_root_origin_source_hash_and_full_metadata_tampering_rejects(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, paths = self.prepared(tmp, IDS)
            for sid in sorted(IDS):
                sha, root = self.source(sid)
                before = ET.tostring(root)
                interpretation.validate_creator_interpretation(
                    reference(NEW), sid, sha, root
                )
                self.assertEqual(ET.tostring(root), before)
                for source_id, source_sha in ((sid, "0" * 64), (CONTROL, sha)):
                    with self.assertRaises(ValueError):
                        interpretation.validate_creator_interpretation(
                            reference(NEW), source_id, source_sha, root
                        )
                for xpath in (
                    "./idinfo/citation/citeinfo/origin",
                    "./idinfo/descript/abstract",
                    "./idinfo/descript/purpose",
                    "./idinfo/accconst",
                    "./idinfo/useconst",
                    "./metainfo/metac",
                    "./metainfo/metuc",
                    "./metainfo/metd",
                    "./distinfo/distliab",
                ):
                    changed = copy.deepcopy(root)
                    node = changed.find(xpath)
                    self.assertIsNotNone(node)
                    node.text = "Forged source content"
                    with (
                        self.subTest(source=sid, xpath=xpath),
                        self.assertRaises(ValueError),
                    ):
                        interpretation.validate_creator_interpretation(
                            reference(NEW), sid, sha, changed
                        )
                for mutation in ("attribute", "tail", "extra", "order"):
                    changed = copy.deepcopy(root)
                    origin = changed.find("./idinfo/citation/citeinfo/origin")
                    if mutation == "attribute":
                        origin.set("role", "XML author")
                    elif mutation == "tail":
                        origin.tail = "Forged surrounding source context"
                    elif mutation == "extra":
                        ET.SubElement(changed, "creator").text = "Invented"
                    else:
                        changed[:] = list(reversed(list(changed)))
                    with (
                        self.subTest(source=sid, mutation=mutation),
                        self.assertRaises(ValueError),
                    ):
                        interpretation.validate_creator_interpretation(
                            reference(NEW), sid, sha, changed
                        )
                payload = read_json(Path(paths.zenodo_json_dir) / (sid + ".json"))
                for fault in (
                    "name",
                    "order",
                    "type",
                    "affiliation",
                    "identifier",
                    "context",
                ):
                    altered = copy.deepcopy(payload["metadata"])
                    if fault == "name":
                        altered["creators"][0]["name"] = "Inferred contact author"
                    elif fault == "order":
                        if len(altered["creators"]) > 1:
                            altered["creators"].reverse()
                        else:
                            altered["creators"].append({"name": "Input-data provider"})
                    elif fault == "context":
                        altered["notes"] = "Source and external role context discarded"
                    else:
                        altered["creators"][0][
                            {
                                "type": "type",
                                "affiliation": "affiliation",
                                "identifier": "orcid",
                            }[fault]
                        ] = "Invented"
                    with (
                        self.subTest(source=sid, metadata_fault=fault),
                        self.assertRaises(ValueError),
                    ):
                        interpretation.validate_creator_metadata(
                            reference(NEW), sid, sha, root, altered
                        )
            for fault in ("membership", "credit", "context", "evidence", "scope"):
                forged = copy.deepcopy(self.manifest)
                cohort = forged["cohorts"][-1]
                if fault == "membership":
                    cohort["members"][0]["source_id"] = CONTROL
                elif fault == "credit":
                    cohort["creators"][0]["type"] = "Organization"
                elif fault == "context":
                    cohort["context_note"] = "XML authorship inferred"
                elif fault == "evidence":
                    cohort["external_evidence_references"] = []
                else:
                    forged["scope"] = "All hosted database products"
                target = Path(tmp) / "forged.json"
                atomic_json(target, forged)
                sha, root = self.source("FGDC-3961")
                with self.subTest(profile_fault=fault), self.assertRaises(ValueError):
                    interpretation.validate_creator_interpretation(
                        reference(target), "FGDC-3961", sha, root
                    )

    def test_live_external_evidence_missing_or_tampered_rejects_common_qa_only_new_cohorts(
        self,
    ):
        from scripts.agent_qa import assess_source
        from scripts.qa_manifest import validate_approval

        expected_files = {
            "residual_creator3_proposals.json",
            "residual_creator3_evidence_erratum.json",
            "residual_creator3_source_review.json",
        }
        for cohort in self.added:
            refs = cohort["external_evidence_references"]
            self.assertEqual(len(refs), 3)
            self.assertEqual(
                {Path(e["manifest_path"]).name for e in refs}, expected_files
            )
            self.assertTrue(
                all(set(e) == {"manifest_path", "manifest_sha256"} for e in refs)
            )
            for evidence in refs:
                self.assertEqual(
                    reference(REPO / evidence["manifest_path"])["manifest_sha256"],
                    evidence["manifest_sha256"],
                )
        original_read = Path.read_bytes
        old_member = self.prior["cohorts"][0]["members"][0]
        old_sha, old_root = self.source(old_member["source_id"])
        with tempfile.TemporaryDirectory() as tmp:
            _, paths = self.prepared(tmp, IDS)
            sid = "FGDC-3957"
            path, payload, metadata, entry, manifest = self.human_fixture(sid, paths)
            assess_source(str(path), paths)
            for schema in (1, 2):
                manifest["schema_version"] = schema
                self.assertTrue(
                    validate_approval(manifest, sid, entry, paths, metadata)["qa"][
                        "approved"
                    ]
                )
            for evidence in self.profiles[sid]["external_evidence_references"]:
                target = (REPO / evidence["manifest_path"]).resolve()
                for fault in ("missing", "tampered"):

                    def read_with_fault(candidate, _target=target, _fault=fault):
                        if candidate.resolve() == _target:
                            if _fault == "missing":
                                raise FileNotFoundError(
                                    "Offline fixture: evidence absent"
                                )
                            return original_read(candidate) + b" "
                        return original_read(candidate)

                    with (
                        self.subTest(evidence=target.name, fault=fault),
                        patch.object(Path, "read_bytes", read_with_fault),
                    ):
                        for new_sid in sorted(IDS):
                            sha, root = self.source(new_sid)
                            with self.assertRaises(ValueError):
                                interpretation.validate_creator_interpretation(
                                    reference(NEW), new_sid, sha, root
                                )
                        self.assertEqual(
                            interpretation.validate_creator_interpretation(
                                reference(NEW),
                                old_member["source_id"],
                                old_sha,
                                old_root,
                            ),
                            self.prior["cohorts"][0]["creators"],
                        )
                        self.assert_shared_rejection(
                            sid, path, paths, metadata, entry, manifest
                        )

    def test_bounded_before_after_repeat_withdrawal_preserves_xml_roles_rights_and_authority(
        self,
    ):
        from scripts.agent_qa import assess_source
        from scripts.qa_manifest import validate_approval

        ids = IDS | {CONTROL}
        with tempfile.TemporaryDirectory() as tmp:
            before, paths = self.prepared(tmp, ids, PREVIOUS)
            old = {
                sid: read_json(Path(paths.zenodo_json_dir) / (sid + ".json"))
                for sid in ids
            }
            self.assertEqual(
                before["summary"]["source_status_counts"],
                {"supported": 0, "held": 4, "failed": 0},
            )
            after, paths = self.prepared(tmp, ids)
            self.assertEqual(
                after["summary"]["source_status_counts"],
                {"supported": 3, "held": 1, "failed": 0},
            )
            after_payloads = {}
            for row in after["records"]:
                sid = row["source_id"]
                payload = read_json(Path(paths.zenodo_json_dir) / (sid + ".json"))
                after_payloads[sid] = payload
                self.assertEqual(payload["metadata"]["access_right"], "restricted")
                self.assertEqual(payload["metadata"]["license"], "")
                self.assertFalse(row["remote_verified"] or row["publication_approved"])
                self.assertEqual(
                    (Path(paths.original_fgdc_dir) / (sid + ".xml")).read_bytes(),
                    (REPO / "FGDC" / (sid + ".xml")).read_bytes(),
                )
                if sid == CONTROL:
                    self.assertEqual(payload["metadata"], old[sid]["metadata"])
                    self.assertEqual(row["source_status"], "held")
                    continue
                self.assertEqual(payload["metadata"]["creators"], EXPECTED[sid])
                self.assertEqual(
                    {
                        k: v
                        for k, v in payload["metadata"].items()
                        if k not in ("creators", "notes")
                    },
                    {
                        k: v
                        for k, v in old[sid]["metadata"].items()
                        if k not in ("creators", "notes")
                    },
                )
                sha, root = self.source(sid)
                result = interpretation.validate_creator_interpretation(
                    reference(NEW), sid, sha, root, True
                )
                restored = payload["metadata"]["notes"]
                for note in result["preservation_notes"]:
                    self.assertIn(note, restored)
                    restored = restored.replace("\n" + note, "", 1)
                self.assertIn(
                    "Original primary citation origin XML (parsed representation):",
                    payload["metadata"]["notes"],
                )
                old_line = next(
                    line
                    for line in old[sid]["metadata"]["notes"].splitlines()
                    if line.startswith("Curator decision: ")
                )
                new_line = next(
                    line
                    for line in restored.splitlines()
                    if line.startswith("Curator decision: ")
                )
                old_decision = json.loads(old_line.removeprefix("Curator decision: "))
                new_decision = json.loads(new_line.removeprefix("Curator decision: "))
                new_decision["metadata"]["creators"] = old_decision["metadata"][
                    "creators"
                ]
                self.assertEqual(new_decision, old_decision)
                self.assertEqual(
                    restored.replace(new_line, old_line, 1),
                    old[sid]["metadata"]["notes"],
                )
            self.assertEqual(after, self.prepared(tmp, ids)[0])
            for sid in ids:
                self.assertEqual(
                    read_json(Path(paths.zenodo_json_dir) / (sid + ".json")),
                    after_payloads[sid],
                )
            for sid in sorted(IDS):
                path, payload, metadata, entry, manifest = self.human_fixture(
                    sid, paths
                )
                assess_source(str(path), paths)
                for schema in (1, 2):
                    manifest["schema_version"] = schema
                    self.assertTrue(
                        validate_approval(manifest, sid, entry, paths, metadata)["qa"][
                            "approved"
                        ]
                    )
                for fault in (
                    "withdraw_credit",
                    "withdraw_authority",
                    "open",
                    "license",
                    "rights_context",
                ):
                    changed = copy.deepcopy(payload)
                    if fault == "withdraw_credit":
                        changed["artifact_policy"].pop("creator_interpretation")
                    elif fault == "withdraw_authority":
                        changed["artifact_policy"].pop("rehosting_authority")
                    elif fault == "open":
                        changed["metadata"]["access_right"] = "open"
                    elif fault == "license":
                        changed["metadata"]["license"] = "cc-by-4.0"
                    else:
                        changed["metadata"]["access_conditions"] = ""
                    atomic_json(path, changed)
                    with self.subTest(source=sid, independent_gate=fault):
                        self.assert_shared_rejection(
                            sid, path, paths, metadata, entry, manifest
                        )
                    atomic_json(path, payload)
            withdrawn, paths = self.prepared(tmp, ids, PREVIOUS)
            self.assertEqual(withdrawn, before)
            for sid in ids:
                self.assertEqual(
                    read_json(Path(paths.zenodo_json_dir) / (sid + ".json")), old[sid]
                )
            for profile in (None, Path(tmp) / "missing-profile.json"):
                held, _ = self.prepared(tmp, ids, profile)
                self.assertEqual(
                    held["summary"]["source_status_counts"],
                    {"supported": 0, "held": 4, "failed": 0},
                )
            held, _ = self.prepared(tmp, IDS, authority=False)
            self.assertEqual(
                held["summary"]["source_status_counts"],
                {"supported": 0, "held": 3, "failed": 0},
            )


if __name__ == "__main__":
    unittest.main()
