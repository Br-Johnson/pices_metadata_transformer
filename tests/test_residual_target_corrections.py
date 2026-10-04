"""Finite residual profiles compose without weakening source or class-operation gates.

Six contracts use a ten-original/five-class fixture and one separate singleton. The human-QA assertions
exercise its mandatory alias refusal, not a bypass into singleton approval.
"""

import copy
import hashlib
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import citation_creator_interpretation as credits
from scripts import content_class_targets as classes
from scripts import dataset_access_interpretation as access
from scripts import source_title_interpretation as titles
from scripts.agent_qa import assess_source
from scripts.artifact_contract import fingerprint, prepare_artifact
from scripts.collection_qa import classify_collection
from scripts.path_config import OutputPaths
from scripts.qa_manifest import QA_CHECKS, validate_approval
from scripts.upload_service import (
    DraftUploadService,
    atomic_json,
    metadata_hash,
    prepare_metadata,
    read_json,
)
from tests.test_content_class_targets import current_profiles
from tests.test_derived_creator_extension import compare_notes

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs/readiness/2026-10-04"
OLD = {
    "access": DOCS / "finite_source_resource_access_607.json",
    "creator": DOCS / "source_citation_credits_423.json",
    "title": DOCS / "source_display_titles_36.json",
}
NEW = {
    "access": DOCS / "finite_source_resource_access_655.json",
    "creator": DOCS / "source_citation_credits_426.json",
    "title": DOCS / "source_display_titles_42.json",
}
PAIR_NUMBERS = (
    (2837, 3065),
    (2839, 3067),
    (2850, 3078),
    (2861, 3089),
    (2872, 3100),
    (2883, 3111),
    (2894, 3122),
    (2904, 3132),
    (2915, 3143),
    (2926, 3154),
    (2937, 3165),
    (2948, 3176),
    (2949, 3177),
    (2960, 3188),
    (2971, 3199),
    (2982, 3210),
    (2993, 3221),
    (3004, 3232),
    (3015, 3243),
    (3026, 3254),
    (3037, 3265),
    (3048, 3276),
    (3059, 3287),
    (3060, 3288),
)
ACCESS_IDS = {f"FGDC-{n}" for pair in PAIR_NUMBERS for n in pair}
TITLE_IDS = {f"FGDC-{n}" for n in (2872, 3100, 2894, 3122, 2960, 3188)}
CREATOR_ALIAS_IDS = {"FGDC-2837", "FGDC-3065"}
CREATOR_IDS = CREATOR_ALIAS_IDS | {"FGDC-2664"}
EXPECTED_CREATOR = [{"name": "Pat Livingston"}, {"name": "Douglas Smith"}]
SMOKE_PAIRS = tuple(
    tuple(f"FGDC-{n}" for n in pair)
    for pair in ((2837, 3065), (2872, 3100), (2894, 3122), (2948, 3176), (2953, 3181))
)
SMOKE_IDS = {sid for pair in SMOKE_PAIRS for sid in pair}
CONTROL = {"FGDC-2953", "FGDC-3181"}
CLASS_ERROR = r"(?i)(content.class|alias|pair|singleton|reconcil)"


def reference(path):
    return {
        "manifest_path": str(path),
        "manifest_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def source(sid):
    raw = (REPO / "FGDC" / (sid + ".xml")).read_bytes()
    return raw, hashlib.sha256(raw).hexdigest(), ET.fromstring(raw)


class ResidualTargetCorrectionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(prefix="pices-residual-targets-")
        cls.addClassCleanup(cls.fixture.cleanup)
        cls.reviewed_at = datetime.now(timezone.utc).isoformat()
        source_dir = Path(cls.fixture.name) / "sources"
        source_dir.mkdir()
        for sid in SMOKE_IDS:
            shutil.copyfile(REPO / "FGDC" / (sid + ".xml"), source_dir / (sid + ".xml"))
        cls.output = Path(cls.fixture.name) / "prepared"
        paths = OutputPaths(str(cls.output), "sandbox")
        cls.identities = {
            tuple(row["source_ids"]): row["record_target_id"]
            for row in classes.load_representation()["classes"]
        }
        cls.reports, cls.payloads, cls.targets = {}, {}, {}
        for phase in (
            "before",
            "after",
            "repeat",
            "access_withdrawn",
            "editorial_withdrawn",
            "withdrawn",
        ):
            active = dict(NEW if phase not in ("before", "withdrawn") else OLD)
            if phase == "access_withdrawn":
                active["access"] = OLD["access"]
            if phase == "editorial_withdrawn":
                active.update(creator=OLD["creator"], title=OLD["title"])
            profiles = current_profiles()
            profiles.update(
                dataset_access_interpretation_manifest=active["access"],
                institution_creator_interpretation_manifest=active["creator"],
                source_title_interpretation_manifest=active["title"],
            )
            cls.reports[phase] = classify_collection(
                source_dir, cls.output, cls.reviewed_at, **profiles
            )
            cls.payloads[phase] = {
                sid: read_json(Path(paths.zenodo_json_dir) / (sid + ".json"))
                for sid in SMOKE_IDS
            }
            cls.targets[phase] = {
                pair: classes.prepare_class_target(
                    cls.identities[pair], paths, reviewed_at=cls.reviewed_at
                )
                for pair in SMOKE_PAIRS
            }
            if phase == "after":
                cls.after_copy = Path(cls.fixture.name) / "after"
                shutil.copytree(cls.output, cls.after_copy)

    def setUp(self):
        self.old = {axis: read_json(path) for axis, path in OLD.items()}
        self.new = {axis: read_json(path) for axis, path in NEW.items()}
        self.creator_cohorts = {
            member["source_id"]: cohort
            for cohort in self.new["creator"]["cohorts"][
                len(self.old["creator"]["cohorts"]) :
            ]
            for member in cohort["members"]
        }
        self.title_members = {
            m["source_id"]: m for m in self.new["title"]["members"][36:]
        }

    def prepared_copy(self, directory):
        prepared = Path(directory) / "prepared"
        shutil.copytree(self.after_copy, prepared)
        return OutputPaths(str(prepared), "sandbox")

    def validate(self, axis, sid, root=None, digest=None, stamp=None, ref=None):
        _, actual_digest, actual_root = source(sid)
        root = actual_root if root is None else root
        digest = actual_digest if digest is None else digest
        ref = reference(NEW[axis]) if ref is None else ref
        if axis == "access":
            return access.validate_dataset_access_interpretation(
                ref, sid, digest, root, reviewed_at=stamp or self.reviewed_at
            )
        if axis == "creator":
            return credits.validate_creator_interpretation(ref, sid, digest, root, True)
        return titles.validate_source_title_interpretation(ref, sid, digest, root)

    def human_fixture(self, sid, paths):
        # Build a superficially complete historical singleton manifest directly:
        # prepare_manifest itself must refuse every member of these finite pairs.
        path = Path(paths.zenodo_json_dir) / (sid + ".json")
        metadata, original, digest = prepare_metadata(str(path), paths)
        entry = {
            "environment": "sandbox",
            "deposition_id": 123,
            "zenodo_url": "https://sandbox.zenodo.org/deposit/123",
            "json_file": str(path),
            "source_sha256": digest,
            "metadata_sha256": metadata_hash(metadata),
            "artifact_contract": prepare_artifact(read_json(path), original),
            "upload_status": "success",
            "publish_status": "draft",
            "success": True,
        }
        row = {
            k: copy.deepcopy(entry[k])
            for k in (
                "deposition_id",
                "source_sha256",
                "metadata_sha256",
                "artifact_contract",
            )
        }
        row.update(
            fgdc_id=sid,
            qa={
                "approved": True,
                "reviewer_type": "human",
                "reviewer": "Offline fixture",
                "reviewed_at": self.reviewed_at,
                "rationale": "Offline gate fixture only",
                "checks": dict.fromkeys(QA_CHECKS, True),
                "run_id": "fixture",
                "review_revision": "fixture",
                "evidence": ["fixture"],
            },
            duplicate_review={
                "status": "reviewed",
                "classification": "checked_no_match",
                "rationale": "Offline fixture only",
                "evidence": ["fixture"],
            },
        )
        manifest = {
            "schema_version": 1,
            "environment": "sandbox",
            "source_revision": "fixture",
            "records": [row],
        }
        return metadata, entry, manifest

    def test_additive_profiles_bind_all_originals_and_keep_previous_contracts(self):
        for axis in OLD:
            key = "cohorts" if axis == "creator" else "members"
            self.assertEqual(
                self.new[axis][key][: len(self.old[axis][key])], self.old[axis][key]
            )
            self.assertEqual(
                self.new[axis]["prior_manifest_sha256"],
                reference(OLD[axis])["manifest_sha256"],
            )
        self.assertEqual(
            self.new["access"]["source_contexts"], self.old["access"]["source_contexts"]
        )
        for sid, context in self.old["access"]["acquisition_contexts"].items():
            self.assertEqual(self.new["access"]["acquisition_contexts"][sid], context)
        for key, value in self.old["access"].items():
            if key.endswith("_review"):
                self.assertEqual(self.new["access"][key], value)
        added_access = self.new["access"]["members"][607:]
        self.assertEqual(len(self.new["access"]["members"]), 655)
        self.assertEqual(len(added_access), len(ACCESS_IDS))
        self.assertEqual({m["source_id"] for m in added_access}, ACCESS_IDS)
        all_creator_members = [
            m for c in self.new["creator"]["cohorts"] for m in c["members"]
        ]
        self.assertEqual(len(all_creator_members), 426)
        self.assertEqual(len({m["source_id"] for m in all_creator_members}), 426)
        self.assertEqual(set(self.creator_cohorts), CREATOR_IDS)
        self.assertEqual(len(self.new["title"]["members"]), 42)
        self.assertEqual(set(self.title_members), TITLE_IDS)
        self.assertEqual(
            (CREATOR_ALIAS_IDS | TITLE_IDS) & ACCESS_IDS, CREATOR_ALIAS_IDS | TITLE_IDS
        )
        for numbers in PAIR_NUMBERS:
            pair = tuple(f"FGDC-{n}" for n in numbers)
            self.assertEqual(source(pair[0])[0], source(pair[1])[0])
            self.assertEqual(self.identities[pair], "sha256:" + source(pair[0])[1])
            for sid in pair:
                _, digest, root = source(sid)
                self.assertIn({"source_id": sid, "source_sha256": digest}, added_access)
                self.assertEqual(
                    self.new["access"]["acquisition_contexts"][sid]["context_elements"],
                    {".": [ET.tostring(root, encoding="unicode")]},
                )
                result = self.validate("access", sid)
                self.assertEqual(result["status"], "REVIEWER_RECONCILED")
                for flag in (
                    "grants_rehosting",
                    "grants_new_license",
                    "publication_approved",
                    "new_user_attestation_event",
                    "underlying_data_rights_granted",
                    "original_direct_question_membership_enlarged",
                ):
                    self.assertFalse(result[flag])
        for sid, cohort in self.creator_cohorts.items():
            _, digest, root = source(sid)
            self.assertIn(
                {"source_id": sid, "source_sha256": digest}, cohort["members"]
            )
            self.assertEqual(
                cohort["supplemental_source_elements"],
                [{"xpath": ".", "element": credits.source_element(root)}],
            )
            self.assertEqual(
                self.validate("creator", sid)["creators"], cohort["creators"]
            )
            if sid in CREATOR_ALIAS_IDS:
                self.assertEqual(cohort["creators"], EXPECTED_CREATOR)
        for sid, member in self.title_members.items():
            _, digest, root = source(sid)
            self.assertEqual(member["source_sha256"], digest)
            self.assertEqual(
                member["source_root_element"], credits.source_element(root)
            )
            self.assertEqual(self.validate("title", sid), member)
            self.assertLessEqual(len(member["display_title"]), 250)

    def test_live_evidence_time_membership_and_complete_context_fail_closed(self):
        representatives = {
            "access": "FGDC-2948",
            "creator": "FGDC-2837",
            "title": "FGDC-2872",
        }
        for axis, sid in representatives.items():
            _, _, root = source(sid)
            for xpath in (
                "./idinfo/descript/abstract",
                "./metainfo/metd",
                "./idinfo/accconst",
            ):
                changed = copy.deepcopy(root)
                changed.find(xpath).text = "Unreviewed source change"
                with (
                    self.subTest(axis=axis, xpath=xpath),
                    self.assertRaises(ValueError),
                ):
                    self.validate(axis, sid, root=changed)
            for wrong_sid, digest in ((sid, "0" * 64), ("FGDC-288", source(sid)[1])):
                with (
                    self.subTest(axis=axis, membership=wrong_sid),
                    self.assertRaises(ValueError),
                ):
                    self.validate(axis, wrong_sid, root=root, digest=digest)
            with tempfile.TemporaryDirectory() as tmp:
                forged = Path(tmp) / "forged.json"
                forged.write_bytes(NEW[axis].read_bytes() + b" ")
                with self.assertRaises(ValueError):
                    self.validate(axis, sid, ref=reference(forged))
                forged.unlink()
                missing = {
                    "manifest_path": str(forged),
                    "manifest_sha256": reference(NEW[axis])["manifest_sha256"],
                }
                with self.assertRaises(ValueError):
                    self.validate(axis, sid, ref=missing)
        # The new finite access review requires an aware post-review time.
        for sid in ("FGDC-2837", "FGDC-2872", "FGDC-2948"):
            result = self.validate("access", sid)
            reviewed = datetime.fromisoformat(result["reconciliation_reviewed_at"])
            for invalid in (
                None,
                "not-a-time",
                "2026-10-04T01:00:00",
                (reviewed - timedelta(seconds=1)).isoformat(),
                (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            ):
                with (
                    self.subTest(source=sid, stamp=invalid),
                    self.assertRaises(ValueError),
                ):
                    access.validate_dataset_access_interpretation(
                        reference(NEW["access"]),
                        sid,
                        source(sid)[1],
                        source(sid)[2],
                        invalid,
                    )
        review = self.new["access"]["paired_resource24_review"]
        references = review["original_statement_references"]
        self.assertEqual(len(references), 9)
        self.assertEqual(
            references[:5],
            self.old["access"]["resource_reconciliation_review"][
                "original_statement_references"
            ],
        )
        self.assertEqual({m["source_id"] for m in review["members"]}, ACCESS_IDS)
        original_read = Path.read_bytes
        for evidence in references:
            target = (REPO / evidence["manifest_path"]).resolve()
            for missing in (True, False):

                def changed_read(candidate, _target=target, _missing=missing):
                    if candidate.resolve() == _target:
                        if _missing:
                            raise FileNotFoundError("Offline absent authority evidence")
                        return original_read(candidate) + b" "
                    return original_read(candidate)

                with (
                    self.subTest(evidence=target.name, missing=missing),
                    patch.object(Path, "read_bytes", changed_read),
                ):
                    self.assertEqual(
                        access.dataset_access_member_ids(reference(NEW["access"])),
                        frozenset(),
                    )
                    with self.assertRaises(ValueError):
                        self.validate("access", "FGDC-2948")
                    paths = OutputPaths(str(self.after_copy), "sandbox")
                    with self.assertRaises(ValueError):
                        assess_source(
                            str(Path(paths.zenodo_json_dir) / "FGDC-2948.json"), paths
                        )

    def test_same_output_retry_withdrawals_and_complete_metadata_preservation(self):
        for mapping in (self.reports, self.payloads, self.targets):
            self.assertEqual(mapping["after"], mapping["repeat"])
            self.assertEqual(mapping["before"], mapping["withdrawn"])
        for phase, report in self.reports.items():
            supported = set(SMOKE_IDS) if phase in ("after", "repeat") else set(CONTROL)
            if phase == "editorial_withdrawn":
                supported |= {"FGDC-2948", "FGDC-3176"}
            self.assertEqual({r["source_id"] for r in report["records"]}, SMOKE_IDS)
            for row in report["records"]:
                self.assertEqual(row["source_status"], "held")
                self.assertEqual(
                    row["source_status_without_aliases"],
                    "supported" if row["source_id"] in supported else "held",
                )
                self.assertFalse(row["remote_verified"])
                self.assertFalse(row["publication_approved"])
            for pair, target in self.targets[phase].items():
                self.assertEqual(
                    target["source_semantic_status"],
                    "supported" if set(pair) <= supported else "held",
                )
                self.assertEqual(target["source_ids"], list(pair))
                self.assertFalse(target["upload_eligible"])
                self.assertIsNone(target["canonical_source_id"])
                self.assertEqual(target["production_reconciliation_status"], "pending")
                self.assertEqual(len(target["artifact_contract"]["files"]), 2)
        paths = OutputPaths(str(self.after_copy), "sandbox")
        for sid in SMOKE_IDS:
            before, after = (
                self.payloads[p][sid]["metadata"] for p in ("before", "after")
            )
            for phase in self.payloads:
                metadata = self.payloads[phase][sid]["metadata"]
                self.assertEqual(metadata["access_right"], "restricted")
                self.assertEqual(metadata["license"], "")
                self.assertEqual(
                    self.payloads[phase][sid]["artifact_policy"]["date_semantics"],
                    "source_metadata_date",
                )
            self.assertEqual(
                (Path(paths.original_fgdc_dir) / (sid + ".xml")).read_bytes(),
                source(sid)[0],
            )
            if sid in CREATOR_ALIAS_IDS:
                self.assertEqual(after["creators"], EXPECTED_CREATOR)
                self.assertNotEqual(before["creators"], after["creators"])
                self.assertEqual(
                    {k: v for k, v in before.items() if k not in ("creators", "notes")},
                    {k: v for k, v in after.items() if k not in ("creators", "notes")},
                )
                compare_notes(
                    before["notes"],
                    after["notes"],
                    self.validate("creator", sid)["preservation_notes"],
                )
            elif sid in TITLE_IDS:
                self.assertEqual(
                    titles.apply_source_title_interpretation(
                        self.title_members[sid], before
                    ),
                    after,
                )
            else:
                self.assertEqual(before, after)
            # An access decision has no metadata rewrite, even on editorial members.
            self.assertEqual(self.payloads["access_withdrawn"][sid]["metadata"], after)
            self.assertEqual(
                self.payloads["editorial_withdrawn"][sid]["metadata"], before
            )

    def test_each_overlapping_gate_and_authority_is_required_for_both_members(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.prepared_copy(tmp)
            for pair in SMOKE_PAIRS[:-1]:
                for sid in pair:
                    path = Path(paths.zenodo_json_dir) / (sid + ".json")
                    original = read_json(path)
                    saved_target = classes.prepare_class_target(
                        self.identities[pair], paths, reviewed_at=self.reviewed_at
                    )
                    assess_source(str(path), paths)
                    faults = ["access", "authority", "license"]
                    if sid in CREATOR_ALIAS_IDS:
                        faults += ["creator_reference", "creators", "notes"]
                    if sid in TITLE_IDS:
                        faults += ["title_reference", "title", "notes"]
                    for fault in faults:
                        changed = copy.deepcopy(original)
                        policy = changed["artifact_policy"]
                        if fault == "access":
                            policy.pop("dataset_access_interpretation")
                        elif fault == "authority":
                            policy.pop("rehosting_authority")
                        elif fault == "creator_reference":
                            policy.pop("creator_interpretation")
                        elif fault == "title_reference":
                            policy.pop("source_title_interpretation")
                        elif fault == "creators":
                            changed["metadata"]["creators"][0]["type"] = "Organization"
                        elif fault == "license":
                            changed["metadata"]["license"] = "cc-zero"
                        else:
                            changed["metadata"][fault] = "Unreviewed replacement"
                        atomic_json(path, changed)
                        try:
                            with (
                                self.subTest(source=sid, fault=fault),
                                self.assertRaises(ValueError),
                            ):
                                assess_source(str(path), paths)
                            with self.assertRaises(ValueError):
                                classes.validate_class_target(saved_target, paths)
                            # Pure policy withdrawal retains common raw metadata;
                            # exactly the altered member must now hold the class.
                            if fault in (
                                "access",
                                "creator_reference",
                                "title_reference",
                            ):
                                held = classes.prepare_class_target(
                                    self.identities[pair],
                                    paths,
                                    reviewed_at=self.reviewed_at,
                                )
                                self.assertEqual(held["source_semantic_status"], "held")
                                self.assertEqual(
                                    {
                                        m["source_id"]
                                        for m in held["member_assessments"]
                                        if m["source_semantic_status"] == "held"
                                    },
                                    {sid},
                                )
                                self.assertFalse(held["upload_eligible"])
                        finally:
                            atomic_json(path, original)

    def test_supported_new_aliases_never_enable_human_approval_or_singleton_writes(
        self,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            paths = self.prepared_copy(tmp)
            client = Mock(base_url="https://sandbox.zenodo.org")
            service = DraftUploadService(paths, "sandbox")
            registry = Path(paths.uploads_registry_path)
            ledger_before = registry.read_bytes() if registry.exists() else None
            for pair in SMOKE_PAIRS[:-1]:
                target = classes.prepare_class_target(
                    self.identities[pair], paths, reviewed_at=self.reviewed_at
                )
                self.assertEqual(target["source_semantic_status"], "supported")
                for sid in pair:
                    path = Path(paths.zenodo_json_dir) / (sid + ".json")
                    original = read_json(path)
                    metadata, entry, manifest = self.human_fixture(sid, paths)
                    for fault in ("none", "authority", "metadata"):
                        altered = copy.deepcopy(original)
                        if fault == "authority":
                            altered["artifact_policy"].pop("rehosting_authority")
                        elif fault == "metadata":
                            altered["metadata"]["notes"] = "Unreviewed replacement"
                        atomic_json(path, altered)
                        try:
                            for schema in (1, 2):
                                manifest["schema_version"] = schema
                                with (
                                    self.subTest(
                                        source=sid, schema=schema, fault=fault
                                    ),
                                    self.assertRaisesRegex(ValueError, CLASS_ERROR),
                                ):
                                    validate_approval(
                                        manifest, sid, entry, paths, metadata
                                    )
                            with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                                classes.require_singleton_operation(
                                    source_id=sid, paths=paths
                                )
                            with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                                service.upload(str(path), client)
                            self.assertEqual(client.mock_calls, [])
                        finally:
                            atomic_json(path, original)
                forged = copy.deepcopy(target)
                forged["upload_eligible"] = True
                # Rehashing the already-bound artifact cannot confer operation authority.
                forged["artifact_contract"].pop("sha256")
                forged["artifact_contract"]["sha256"] = fingerprint(
                    forged["artifact_contract"]
                )
                with self.assertRaises(ValueError):
                    classes.validate_class_target(forged, paths)
            self.assertEqual(
                registry.read_bytes() if registry.exists() else None, ledger_before
            )

    def test_2664_current_singleton_credit_retry_and_withdrawal_preserve_metadata(self):
        sid = "FGDC-2664"
        with tempfile.TemporaryDirectory(prefix="pices-2664-current-") as directory:
            source_dir = Path(directory) / "sources"
            source_dir.mkdir()
            shutil.copyfile(REPO / "FGDC" / (sid + ".xml"), source_dir / (sid + ".xml"))
            destination = Path(directory) / "prepared"
            snapshots = {}
            for phase in ("before", "after", "repeat", "withdrawn"):
                profiles = current_profiles()
                profiles.update(
                    dataset_access_interpretation_manifest=NEW["access"],
                    source_title_interpretation_manifest=NEW["title"],
                    institution_creator_interpretation_manifest=(
                        NEW["creator"]
                        if phase in ("after", "repeat")
                        else OLD["creator"]
                    ),
                )
                report = classify_collection(
                    source_dir, destination, self.reviewed_at, **profiles
                )
                paths = OutputPaths(str(destination), "sandbox")
                payload = read_json(Path(paths.zenodo_json_dir) / (sid + ".json"))
                expected = "supported" if phase in ("after", "repeat") else "held"
                self.assertEqual(report["records"][0]["source_status"], expected)
                self.assertEqual(report["records"][0]["source_id"], sid)
                self.assertEqual(
                    (Path(paths.original_fgdc_dir) / (sid + ".xml")).read_bytes(),
                    (REPO / "FGDC" / (sid + ".xml")).read_bytes(),
                )
                self.assertFalse(report["records"][0]["remote_verified"])
                self.assertFalse(report["records"][0]["publication_approved"])
                snapshots[phase] = (report, payload)
            self.assertEqual(snapshots["before"], snapshots["withdrawn"])
            self.assertEqual(snapshots["after"], snapshots["repeat"])
            before, after = (snapshots[phase][1] for phase in ("before", "after"))
            self.assertEqual(
                after["metadata"]["creators"], [{"name": "Sapozhnikov, V. V."}]
            )
            _, source_hash, root = source(sid)
            result = credits.validate_creator_interpretation(
                reference(NEW["creator"]), sid, source_hash, root, True
            )
            compare_notes(
                before["metadata"]["notes"],
                after["metadata"]["notes"],
                result["preservation_notes"],
            )
            self.assertEqual(
                {
                    k: v
                    for k, v in before["metadata"].items()
                    if k not in ("creators", "notes")
                },
                {
                    k: v
                    for k, v in after["metadata"].items()
                    if k not in ("creators", "notes")
                },
            )
            restored = copy.deepcopy(after)
            self.assertEqual(
                restored["artifact_policy"].pop("creator_interpretation"),
                reference(NEW["creator"]),
            )
            restored["metadata"] = before["metadata"]
            self.assertEqual(restored, before)
