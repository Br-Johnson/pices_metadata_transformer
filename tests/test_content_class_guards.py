"""Finite-pair operation gates under the existing offline I/O guard.

These tests deliberately use synthetic legacy metadata/approvals beside unchanged
real pair bytes. Their purpose is to prove that superficially valid singleton
inputs cannot route a known pair into provider, human QA, or release operations.
They do not attest that the synthetic metadata describes or licenses the source.
All provider clients in this module are inert test doubles.
"""

import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.batch_upload import BatchUploader
from scripts.content_class_targets import require_singleton_operation
from scripts.path_config import OutputPaths
from scripts.pre_upload_duplicate_check import PreUploadDuplicateChecker
from scripts.publish_records import RecordPublisher
from scripts.qa_manifest import QA_CHECKS, prepare_manifest, validate_approval
from scripts.reconcile_draft import reconcile
from scripts.release_manifest import prepare_release, validate_release
from scripts.upload_service import (
    DraftUploadService,
    atomic_json,
    metadata_hash,
    prepare_metadata,
    read_json,
)
from scripts.upload_to_zenodo import ZenodoUploader
from scripts.verify_uploads import ZenodoVerifier

REPO = Path(__file__).resolve().parents[1]
MEMBERS = ("FGDC-2953", "FGDC-3181")
SOURCE_SHA256 = "0025e59c5556d26b1c14ceac8c4c840057a271724b524c087db2dd0fb4315025"
CLASS_ID = "sha256:" + SOURCE_SHA256
CLASS_ERROR = r"(?i)(content.class|alias|pair|singleton|reconcil)"


class ContentClassGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pices-class-guard-")
        self.addCleanup(self.tmp.cleanup)
        self.paths = OutputPaths(self.tmp.name, "sandbox")
        self.raw = (REPO / "FGDC" / f"{MEMBERS[0]}.xml").read_bytes()
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), SOURCE_SHA256)
        self.assertEqual(
            self.raw, (REPO / "FGDC" / f"{MEMBERS[1]}.xml").read_bytes()
        )
        self.client = Mock(base_url="https://sandbox.zenodo.org")
        self.client.create_deposition.return_value = {"id": 123}
        self.client.update_deposition_metadata.return_value = {"metadata": {}}
        self.service = DraftUploadService(self.paths, "sandbox")
        self.file = self.write_input(MEMBERS[0], self.raw)
        self.entry = self.make_entry(self.file)
        self.authorize_inventory([self.file])

    def write_input(self, source_id, raw):
        source = Path(self.paths.original_fgdc_dir, f"{source_id}.xml")
        source.write_bytes(raw)
        path = Path(self.paths.zenodo_json_dir, f"{source_id}.json")
        payload = {"metadata": {
            "title": "Synthetic singleton-gate test input",
            "upload_type": "dataset",
            "publication_date": "2000-01-01",
            "description": "Synthetic gate fixture, not a source assessment.",
            "creators": [{"name": "Synthetic Fixture Institution"}],
            "access_right": "open", "license": "cc-zero", "notes": "",
        }}
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def make_entry(self, path, status="success"):
        metadata, source_path, digest = prepare_metadata(str(path), self.paths)
        return {
            "environment": self.paths.environment,
            "deposition_id": 123,
            "zenodo_url": "https://sandbox.zenodo.org/deposit/123",
            "json_file": str(path), "fgdc_file": source_path,
            "metadata": metadata, "metadata_sha256": metadata_hash(metadata),
            "source_sha256": digest, "artifact_contract": None,
            "upload_status": status, "success": status == "success",
            "publish_status": "draft", "needs_reconciliation": False,
        }

    def authorize_inventory(self, files):
        atomic_json(self.paths.safe_to_upload_path, {
            "environment": "sandbox", "inventory_complete": True,
            "files": [path.name for path in files],
            "metadata_hashes": {
                path.name: metadata_hash(prepare_metadata(str(path), self.paths)[0])
                for path in files
            },
            "valid_until": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        })

    def ledger_bytes(self):
        path = Path(self.paths.uploads_registry_path)
        return path.read_bytes() if path.exists() else None

    def assert_client_unused(self, client=None):
        self.assertEqual((client or self.client).mock_calls, [])

    def publisher(self):
        publisher = RecordPublisher.__new__(RecordPublisher)
        publisher.paths = self.paths
        publisher.sandbox = True
        publisher.client = self.client
        publisher.logger = Mock()
        publisher.qa_manifest = None
        publisher.release_manifest = None
        return publisher

    def verifier(self):
        verifier = ZenodoVerifier.__new__(ZenodoVerifier)
        verifier.paths = self.paths
        verifier.sandbox = True
        verifier.client = self.client
        verifier.logger = Mock()
        return verifier

    def human_manifest(self, entry=None, source_id=None):
        entry = copy.deepcopy(entry or self.entry)
        source_id = source_id or Path(entry["json_file"]).stem
        row = {key: entry.get(key) for key in (
            "deposition_id", "source_sha256", "metadata_sha256", "artifact_contract"
        )}
        row.update(
            fgdc_id=source_id,
            qa={"approved": True, "reviewer": "Synthetic human fixture",
                "reviewed_at": "2026-10-04", "rationale": "Offline gate fixture",
                "checks": dict.fromkeys(QA_CHECKS, True)},
            duplicate_review={
                "status": "reviewed", "classification": "checked_no_match",
                "rationale": "Synthetic gate fixture", "evidence": ["fixture"],
            },
        )
        return {"schema_version": 1, "environment": self.paths.environment,
                "source_revision": "synthetic-fixture-revision", "records": [row]}

    def forged_release(self, manifest, entry, source_id):
        # Assemble historical schema directly: prepare_release itself must reject pairs.
        return {
            "schema_version": 1, "environment": "production",
            "qa_manifest_sha256": metadata_hash(manifest),
            "release": {
                "approved": True, "authority_type": "human",
                "authority": "Synthetic fixture", "authorized_at": "2026-10-04",
                "rationale": "Offline guard fixture, no actual release authority",
            },
            "records": [dict(
                {key: entry.get(key) for key in (
                    "deposition_id", "source_sha256", "metadata_sha256", "artifact_contract"
                )}, fgdc_id=source_id,
            )],
        }

    def test_finite_identity_hash_and_nested_binding_gates(self):
        cases = [
            {"source_id": identity} for identity in (*MEMBERS, CLASS_ID)
        ] + [
            {"source_id": MEMBERS[0], "entry": entry}
            for entry in ({}, {"source_sha256": "0" * 64}, {"artifact_contract": None})
        ] + [
            {"source_id": "renamed", "entry": entry} for entry in (
                {"source_sha256": SOURCE_SHA256},
                {"record_target_id": CLASS_ID},
                {"canonical_content_id": CLASS_ID},
                {"artifact_contract": {"source_id": MEMBERS[1]}},
                {"artifact_contract": {"files": [
                    {"name": "renamed.xml", "sha256": SOURCE_SHA256}
                ]}},
            )
        ]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaisesRegex(ValueError, CLASS_ERROR):
                require_singleton_operation(**kwargs)

    def test_renamed_raw_bytes_cannot_downgrade_by_omission_or_forged_hash(self):
        path = self.write_input("renamed", self.raw)
        for entry in ({}, {"source_sha256": "0" * 64}):
            with self.subTest(entry=entry), self.assertRaisesRegex(ValueError, CLASS_ERROR):
                require_singleton_operation(
                    source_id="renamed", entry=entry,
                    json_file=str(path), paths=self.paths,
                )

    def test_unknown_singleton_and_source_only_preparation_remain_compatible(self):
        path = self.write_input("fixture-singleton", b"<metadata><title>Fixture</title></metadata>")
        entry = self.make_entry(path)
        require_singleton_operation(
            source_id=path.stem, entry=entry, json_file=str(path), paths=self.paths
        )
        # Source-only preparation still supports each alias member independently.
        metadata, _, digest = prepare_metadata(str(self.file), self.paths)
        self.assertEqual(digest, SOURCE_SHA256)
        self.assertIn("Original FGDC metadata (XML)", metadata["notes"])
        self.authorize_inventory([path])
        self.assertTrue(self.service.upload(str(path), self.client)["success"])
        self.client.create_deposition.assert_called_once_with()

    def test_direct_create_resume_retry_and_success_leave_client_and_ledger_untouched(self):
        for status in (None, "pending", "failed", "success"):
            states = (False, True) if status is not None else (False,)
            for uncertain in states:
                registry = {} if status is None else {MEMBERS[0]: dict(
                    self.entry, upload_status=status, needs_reconciliation=uncertain
                )}
                atomic_json(self.paths.uploads_registry_path, registry)
                before = self.ledger_bytes()
                with self.subTest(status=status, uncertain=uncertain):
                    with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                        self.service.upload(str(self.file), self.client)
                    self.assert_client_unused()
                    self.assertEqual(self.ledger_bytes(), before)
        path = self.write_input("renamed", self.raw)
        self.authorize_inventory([path])
        atomic_json(self.paths.uploads_registry_path, {})
        before = self.ledger_bytes()
        with self.assertRaisesRegex(ValueError, CLASS_ERROR):
            self.service.upload(str(path), self.client)
        self.assert_client_unused()
        self.assertEqual(self.ledger_bytes(), before)

    def test_pending_selection_checks_resume_success_and_missing_local_payload(self):
        for status in ("pending", "failed", "success"):
            atomic_json(self.paths.uploads_registry_path, {
                MEMBERS[0]: dict(self.entry, upload_status=status)
            })
            before = self.ledger_bytes()
            with self.subTest(status=status), self.assertRaisesRegex(ValueError, CLASS_ERROR):
                self.service.pending_files(limit=1)
            self.assertEqual(self.ledger_bytes(), before)
        # An old known-member ledger must not disappear behind an empty file glob.
        atomic_json(self.paths.uploads_registry_path, {MEMBERS[1]: self.entry})
        self.file.unlink()
        before = self.ledger_bytes()
        with self.assertRaisesRegex(ValueError, CLASS_ERROR):
            self.service.pending_files()
        self.assertEqual(self.ledger_bytes(), before)

    def test_publish_locked_and_verifier_guard_before_get_without_class_fields(self):
        renamed = self.write_input("renamed", self.raw)
        renamed_entry = self.make_entry(renamed)
        renamed_entry.pop("source_sha256")
        entries = (self.entry, dict(self.entry, source_sha256="0" * 64), renamed_entry)
        operations = (
            (self.publisher()._publish_locked, "publish_successful"),
            (self.verifier()._verify_single_record, "verification_successful"),
        )
        for operation, success_key in operations:
            for entry in entries:
                with self.subTest(operation=success_key, file=entry["json_file"]):
                    result = operation(entry)
                    self.assertFalse(result[success_key])
                    self.assertRegex(result.get("error", ""), CLASS_ERROR)
                    self.assert_client_unused()

    def test_reconcile_retains_prior_draft_identity_and_exact_ledger_bytes(self):
        atomic_json(self.paths.uploads_registry_path, {
            MEMBERS[0]: dict(self.entry, upload_status="failed", needs_reconciliation=True)
        })
        before = self.ledger_bytes()
        snapshot = {
            "endpoint": "https://sandbox.zenodo.org/api/deposit/depositions/123",
            "http_status": 200, "retrieved_at": "2026-10-04T00:00:00+00:00",
            "confirmed_fgdc_id": MEMBERS[0],
            "confirmed_source_sha256": SOURCE_SHA256,
            "confirmed_metadata_sha256": self.entry["metadata_sha256"],
            "body": {"id": 123, "state": "unsubmitted", "submitted": False,
                     "files": [], "metadata": {}},
        }
        with self.assertRaisesRegex(ValueError, CLASS_ERROR):
            reconcile(self.paths, MEMBERS[0], snapshot,
                      "Synthetic fixture reviewer", "Synthetic source correlation")
        self.assertEqual(self.ledger_bytes(), before)
        self.assertEqual(read_json(self.paths.uploads_registry_path)[MEMBERS[0]]["deposition_id"], 123)

    def test_human_qa_cannot_override_known_member_or_raw_hash(self):
        atomic_json(self.paths.uploads_registry_path, {MEMBERS[0]: self.entry})
        before = self.ledger_bytes()
        with patch("scripts.qa_manifest.subprocess.check_output") as revision:
            with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                prepare_manifest(self.paths)
            revision.assert_not_called()
        self.assertEqual(self.ledger_bytes(), before)
        for path in (self.file, self.write_input("renamed", self.raw)):
            entry = self.make_entry(path)
            manifest = self.human_manifest(entry, path.stem)
            with self.subTest(source_id=path.stem), self.assertRaisesRegex(ValueError, CLASS_ERROR):
                validate_approval(manifest, path.stem, entry, self.paths)

    def test_release_preparation_and_forged_historical_release_reject_pair_bindings(self):
        for source_id, source_hash in (
            (MEMBERS[0], "0" * 64), ("renamed", SOURCE_SHA256), (CLASS_ID, "0" * 64)
        ):
            # Isolate identity/hash gates: no alias JSON filename can mask a hash regression.
            entry = {"environment": "production", "deposition_id": 123,
                     "source_sha256": source_hash, "metadata_sha256": "fixture",
                     "artifact_contract": None}
            manifest = self.human_manifest(entry, source_id)
            manifest["environment"] = "production"
            with self.subTest(source_id=source_id, operation="prepare"):
                with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                    prepare_release(manifest)
            release = self.forged_release(manifest, entry, source_id)
            with self.subTest(source_id=source_id, operation="validate"):
                with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                    validate_release(release, manifest, source_id, entry)

    def test_constructor_preflight_blocks_member_and_hash_before_client_factory(self):
        constructors = (
            (RecordPublisher, "scripts.publish_records"),
            (ZenodoVerifier, "scripts.verify_uploads"),
            (PreUploadDuplicateChecker, "scripts.pre_upload_duplicate_check"),
        )
        # Publisher/verifier select the ledger; duplicate checking selects the input.
        atomic_json(self.paths.uploads_registry_path, {MEMBERS[0]: self.entry})
        for cls, module in constructors:
            with self.subTest(constructor=cls.__name__, evidence="selected_member"):
                with patch(module + ".create_zenodo_client") as factory:
                    with patch(module + ".get_logger", return_value=Mock()):
                        if cls is PreUploadDuplicateChecker:
                            checker = cls(sandbox=True, output_dir=self.tmp.name)
                            factory.assert_not_called()
                            with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                                checker.check_all_files()
                        else:
                            with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                                cls(sandbox=True, output_dir=self.tmp.name)
                    factory.assert_not_called()
        # Publisher/verifier select from historical ledgers even when files are absent.
        self.file.unlink()
        for ledger_key, entry in (
            (MEMBERS[0], dict(self.entry, source_sha256="0" * 64)),
            ("renamed", dict(self.entry, json_file="missing.json", fgdc_file="missing.xml")),
        ):
            atomic_json(self.paths.uploads_registry_path, {ledger_key: entry})
            for cls, module in constructors[:2]:
                with self.subTest(constructor=cls.__name__, ledger_key=ledger_key):
                    with patch(module + ".create_zenodo_client") as factory:
                        with patch(module + ".get_logger", return_value=Mock()):
                            with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                                cls(sandbox=True, output_dir=self.tmp.name)
                        factory.assert_not_called()

    def test_batch_compatibility_and_duplicate_entry_points_cannot_bypass_guard(self):
        uploader = BatchUploader.__new__(BatchUploader)
        uploader.paths, uploader.output_dir, uploader.sandbox = self.paths, self.tmp.name, True
        uploader.shutdown_requested = False
        with patch("scripts.batch_upload.create_zenodo_client") as factory:
            with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                uploader.upload_batch([str(self.file)], 1)
            factory.assert_not_called()
        compatibility = ZenodoUploader.__new__(ZenodoUploader)
        compatibility.paths = self.paths
        compatibility.environment, compatibility.client = "sandbox", self.client
        with self.assertRaisesRegex(ValueError, CLASS_ERROR):
            compatibility._upload_single_file(str(self.file))
        self.assert_client_unused()
        checker = PreUploadDuplicateChecker.__new__(PreUploadDuplicateChecker)
        checker.paths, checker.sandbox, checker.canary = self.paths, True, None
        checker.allow_replacements, checker.client, checker.logger = False, self.client, Mock()
        inventory = {"inventory_complete": True, "titles": set(), "records": [],
                     "title_to_record": {}, "identifiers": set()}
        try:
            result = checker.check_file_for_duplicates(str(self.file), inventory)
        except ValueError as error:
            self.assertRegex(str(error), CLASS_ERROR)
        else:
            self.assertFalse(result["safe_to_upload"])
            self.assertRegex(str(result), CLASS_ERROR)
        self.assert_client_unused()
        from scripts.upload_to_zenodo import main

        args = ["upload_to_zenodo", "--sandbox", "--output", self.tmp.name,
                "--log-dir", str(Path(self.tmp.name, "logs"))]
        with patch("sys.argv", args), patch("scripts.upload_to_zenodo.default_log_dir",
                                             return_value=str(Path(self.tmp.name, "logs"))):
            with patch("scripts.upload_to_zenodo.initialize_logger"), patch(
                "scripts.upload_to_zenodo.get_logger", return_value=Mock()
            ), patch("scripts.upload_to_zenodo.create_zenodo_client") as factory:
                try:
                    main()
                except ValueError as error:
                    self.assertRegex(str(error), CLASS_ERROR)
                except SystemExit as error:
                    self.assertNotEqual(error.code, 0)
                else:
                    self.fail("Compatibility CLI returned success for a known pair member")
                factory.assert_not_called()

    def test_id_only_metadata_helper_requires_unique_local_singleton_before_get(self):
        singleton = self.write_input("fixture-singleton", b"<metadata><title>Fixture</title></metadata>")
        singleton_entry = self.make_entry(singleton)
        registries = (
            {},
            {MEMBERS[0]: self.entry},
            {"renamed": dict(self.entry, json_file="renamed.json", fgdc_file="renamed.xml")},
            {"fixture-singleton": singleton_entry,
             "another-ledger-key": copy.deepcopy(singleton_entry)},
        )
        for registry in registries:
            atomic_json(self.paths.uploads_registry_path, registry)
            before = self.ledger_bytes()
            with self.subTest(keys=list(registry)), self.assertRaises(ValueError):
                self.publisher()._mark_as_metadata_only(123)
            self.assert_client_unused()
            self.assertEqual(self.ledger_bytes(), before)


if __name__ == "__main__":
    unittest.main()
