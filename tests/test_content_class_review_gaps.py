"""Additive review-gap tests: ordinary bytes cannot conceal missing class gates.

All default source/payload/ledger bindings are synthetic, nonclass singletons.
Known pair bytes appear only in the dedicated nested-path test. Provider objects
are inert mocks. These regressions isolate independent identity evidence.
"""

import copy
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.agent_qa import assess, build_manifest
from scripts.batch_upload import BatchUploader
from scripts.content_class_targets import preflight_inputs, require_singleton_operation
from scripts.deduplicate_check import DuplicateChecker
from scripts.path_config import OutputPaths
from scripts.pre_upload_duplicate_check import PreUploadDuplicateChecker
from scripts.publish_records import RecordPublisher
from scripts.record_review import RecordReviewer
from scripts.release_manifest import prepare_release, record_binding, validate_release
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
SOURCE_ID = "synthetic-review-gap-singleton"
PAIR_ID = "FGDC-2953"
PAIR_HASH = "0025e59c5556d26b1c14ceac8c4c840057a271724b524c087db2dd0fb4315025"
CLASS_ID = "sha256:" + PAIR_HASH
CLASS_ERROR = r"Content-class.*reconciliation"


class ContentClassReviewGapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="pices-class-review-gap-")
        self.addCleanup(self.tmp.cleanup)
        self.paths = OutputPaths(self.tmp.name, "sandbox")
        self.raw = b"<metadata><title>Synthetic nonclass guard fixture</title></metadata>"
        self.assertNotEqual(hashlib.sha256(self.raw).hexdigest(), PAIR_HASH)
        self.source = Path(self.paths.original_fgdc_dir, SOURCE_ID + ".xml")
        self.source.write_bytes(self.raw)
        self.file = Path(self.paths.zenodo_json_dir, SOURCE_ID + ".json")
        self.payload = {"metadata": {
            "title": "Synthetic nonclass guard fixture", "upload_type": "dataset",
            "publication_date": "2000-01-01", "description": "Synthetic guard fixture only.",
            "creators": [{"name": "Synthetic Fixture Institution"}],
            "access_right": "open", "license": "cc-zero", "notes": "",
        }}
        self.file.write_text(json.dumps(self.payload), encoding="utf-8")
        metadata, xml_path, source_hash = prepare_metadata(str(self.file), self.paths)
        self.entry = {
            "environment": "sandbox", "deposition_id": 123,
            "zenodo_url": "https://sandbox.zenodo.org/deposit/123",
            "json_file": str(self.file), "fgdc_file": xml_path,
            "metadata": metadata, "metadata_sha256": metadata_hash(metadata),
            "source_sha256": source_hash, "artifact_contract": None,
            "upload_status": "success", "success": True,
            "publish_status": "draft", "needs_reconciliation": False,
        }
        self.safe = {
            "environment": "sandbox", "inventory_complete": True,
            "files": [self.file.name],
            "metadata_hashes": {self.file.name: self.entry["metadata_sha256"]},
            "valid_until": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        }
        atomic_json(self.paths.safe_to_upload_path, self.safe)
        atomic_json(self.paths.uploads_registry_path, {})
        self.client = Mock(base_url="https://sandbox.zenodo.org")

    def write_ledger(self, entry):
        atomic_json(self.paths.uploads_registry_path, {SOURCE_ID: entry})
        return Path(self.paths.uploads_registry_path).read_bytes()

    def publisher(self):
        value = RecordPublisher.__new__(RecordPublisher)
        value.paths, value.sandbox, value.client = self.paths, True, self.client
        value.logger, value.qa_manifest, value.release_manifest = Mock(), None, None
        return value

    def verifier(self):
        value = ZenodoVerifier.__new__(ZenodoVerifier)
        value.paths, value.sandbox, value.client = self.paths, True, self.client
        value.logger = Mock()
        return value

    def reviewer(self):
        value = RecordReviewer.__new__(RecordReviewer)
        value.paths, value.output_dir, value.logger = self.paths, self.tmp.name, Mock()
        value.zenodo_json_dir = self.paths.zenodo_json_dir
        value.registry_path = self.paths.uploads_registry_path
        return value

    def duplicate_checker(self, cached_entry):
        value = DuplicateChecker.__new__(DuplicateChecker)
        value.paths, value.output_dir, value.sandbox = self.paths, self.tmp.name, True
        value.client, value.logger = self.client, Mock()
        value.registry_path = self.paths.uploads_registry_path
        value.registry_entries = {SOURCE_ID: copy.deepcopy(cached_entry)}
        value.local_uploads, value.zenodo_depositions = set(), []
        value.load_local_uploads = Mock()
        value.load_zenodo_depositions = Mock(
            side_effect=AssertionError("Selected protected source reached inventory")
        )
        return value

    def assert_no_client_calls(self):
        self.assertEqual(self.client.mock_calls, [])

    def test_selected_history_and_cached_identity_survive_old_field_projection(self):
        for marker in ({"source_id": PAIR_ID}, {"record_target_id": CLASS_ID}):
            for protected_location in ("disk", "cached"):
                disk = dict(self.entry, **marker) if protected_location == "disk" else copy.deepcopy(self.entry)
                cached = dict(self.entry, **marker) if protected_location == "cached" else copy.deepcopy(self.entry)
                before_disk, before_cached = self.write_ledger(disk), copy.deepcopy(cached)
                with self.subTest(marker=marker, protected_location=protected_location):
                    with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                        require_singleton_operation(entry=cached, paths=self.paths)
                    for operation, key in (
                        (self.publisher()._publish_locked, "publish_successful"),
                        (self.publisher()._publish_single_record, "publish_successful"),
                        (self.verifier()._verify_single_record, "verification_successful"),
                    ):
                        with self.subTest(operation=operation.__name__):
                            result = operation(cached)
                            self.assertFalse(result[key])
                            self.assertRegex(result.get("error", ""), CLASS_ERROR)
                            self.assert_no_client_calls()
                    # No source-only assessment or saved remote evidence is needed to reject it.
                    with patch("scripts.agent_qa.assess_source") as source_assessment:
                        with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                            assess(cached, self.paths, "absent-remote.json", "absent-duplicate.json")
                        source_assessment.assert_not_called()
                    with patch("scripts.record_review.create_zenodo_client") as factory:
                        analysis = self.reviewer()._analyze_zenodo_record(SOURCE_ID, cached, True)
                        self.assertFalse(analysis["found_in_zenodo"])
                        self.assertRegex(analysis.get("api_error", ""), CLASS_ERROR)
                        factory.assert_not_called()
                    if protected_location == "disk":
                        with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                            preflight_inputs(self.paths, [str(self.file)])
                        with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                            DraftUploadService(self.paths, "sandbox").pending_files()
                        uploader = BatchUploader.__new__(BatchUploader)
                        uploader.paths, uploader.sandbox = self.paths, True
                        with patch("scripts.batch_upload.create_zenodo_client") as factory:
                            with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                                uploader.upload_batch([str(self.file)], 1)
                            factory.assert_not_called()
                        manifest = build_manifest(
                            self.paths, {SOURCE_ID: {"remote_snapshot": "absent-remote.json",
                                                    "duplicate_snapshot": "absent-duplicate.json"}},
                            "Synthetic fixture agent", "fixture-run", revision="fixture-revision",
                        )
                        self.assertFalse(manifest["records"][0]["qa"]["approved"])
                        self.assertRegex(" ".join(manifest["records"][0]["hold_reasons"]), CLASS_ERROR)
                    self.assertEqual(Path(self.paths.uploads_registry_path).read_bytes(), before_disk)
                    self.assertEqual(cached, before_cached)
                    self.assertEqual(self.source.read_bytes(), self.raw)

    def test_nested_saved_paths_read_renamed_protected_bytes_even_with_ordinary_outer_path(self):
        # Only this test uses protected original bytes; the outer source stays nonclass.
        raw = (REPO / "FGDC" / (PAIR_ID + ".xml")).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), PAIR_HASH)
        hidden_source = Path(self.paths.original_fgdc_dir, "nested-renamed.xml")
        hidden_source.write_bytes(raw)
        hidden_json = Path(self.paths.zenodo_json_dir, "nested-renamed.json")
        hidden_json.write_text(json.dumps(self.payload), encoding="utf-8")
        for container in ("registry_entry", "upload_log_entry"):
            for field, path in (("fgdc_file", hidden_source), ("json_file", hidden_json)):
                nested = dict(self.entry, **{container: {field: str(path)}})
                before = copy.deepcopy(nested)
                with self.subTest(container=container, field=field):
                    with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                        require_singleton_operation(
                            source_id=SOURCE_ID, entry=nested,
                            json_file=str(self.file), paths=self.paths,
                        )
                    with patch("scripts.record_review.create_zenodo_client") as factory:
                        analysis = self.reviewer()._analyze_zenodo_record(SOURCE_ID, nested, True)
                        self.assertFalse(analysis["found_in_zenodo"])
                        self.assertRegex(analysis.get("api_error", ""), CLASS_ERROR)
                        factory.assert_not_called()
                    self.assertEqual(nested, before)
                    self.assertEqual(self.source.read_bytes(), self.raw)
                    self.assert_no_client_calls()

    def test_complete_qa_identity_cannot_disappear_from_projected_release_binding(self):
        entry = dict(self.entry, environment="production")
        entry["zenodo_url"] = "https://zenodo.org/deposit/123"
        for marker in ({"source_id": PAIR_ID}, {"record_target_id": CLASS_ID}):
            qa_row = dict(record_binding(dict(entry, fgdc_id=SOURCE_ID)),
                          qa={"approved": True}, **marker)
            manifest = {"schema_version": 1, "environment": "production", "records": [qa_row]}
            # The forged projection has only old fields and a correct hash of the *complete* QA manifest.
            release = {
                "schema_version": 1, "environment": "production",
                "qa_manifest_sha256": metadata_hash(manifest),
                "release": {"approved": True, "authority_type": "human",
                            "authority": "Synthetic fixture", "authorized_at": "2026-10-04",
                            "rationale": "Synthetic fixture, no release authority"},
                "records": [record_binding(qa_row)],
            }
            self.assertNotIn(next(iter(marker)), release["records"][0])
            with self.subTest(marker=marker):
                with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                    prepare_release(manifest, [SOURCE_ID])
                with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                    validate_release(release, manifest, SOURCE_ID, entry)

    def test_registry_key_and_nested_source_path_identity_cannot_be_discarded(self):
        # The historical row's key contradicts its otherwise ordinary old fields.
        atomic_json(self.paths.uploads_registry_path, {PAIR_ID: self.entry})
        before = Path(self.paths.uploads_registry_path).read_bytes()
        with self.assertRaisesRegex(ValueError, CLASS_ERROR):
            self.verifier().load_upload_log()
        result = self.verifier()._verify_single_record(self.entry)
        self.assertFalse(result['verification_successful'])
        self.assertRegex(result['error'], CLASS_ERROR)
        self.assert_no_client_calls()
        self.assertEqual(Path(self.paths.uploads_registry_path).read_bytes(), before)
        # A different source path also contributes a selected registry identity,
        # even when its current bytes and all outer fields are nonclass.
        nested = Path(self.paths.original_fgdc_dir) / 'nested-ordinary.xml'
        nested.write_bytes(self.raw)
        atomic_json(self.paths.uploads_registry_path, {
            'nested-ordinary': {'source_id': PAIR_ID},
        })
        for field in ('source_path', 'fgdc_file'):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, CLASS_ERROR):
                require_singleton_operation(entry=dict(self.entry, registry_entry={field: str(nested)}),
                                            paths=self.paths)
        for field in ('members', 'source_ids', 'equivalence_group_members'):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, CLASS_ERROR):
                require_singleton_operation(entry={field: ['nested-ordinary']}, paths=self.paths)

    def test_duplicate_limit_selects_before_client_construction(self):
        first = Path(self.paths.zenodo_json_dir) / '000-singleton.json'
        first.write_bytes(self.file.read_bytes())
        (Path(self.paths.original_fgdc_dir) / '000-singleton.xml').write_bytes(self.raw)
        class_file = Path(self.paths.zenodo_json_dir) / ('XMLCLASS-' + PAIR_HASH + '.json')
        class_file.write_text(json.dumps({'record_target_id': CLASS_ID}), encoding='utf-8')
        self.client.get_records_by_query.return_value = []
        self.client.get_all_my_depositions.return_value = []
        with patch('scripts.pre_upload_duplicate_check.create_zenodo_client',
                   return_value=self.client) as factory:
            checker = PreUploadDuplicateChecker(output_dir=self.tmp.name)
            factory.assert_not_called()
            with patch('builtins.print'):
                checker.check_all_files(limit=1)
            factory.assert_called_once_with(True)
        self.assertEqual([row['file'] for row in checker.safe_to_upload], [first.name])
        self.client.get_records_by_query.assert_called_once()
        self.client.get_all_my_depositions.assert_called_once()
        self.client.reset_mock()
        with self.assertRaisesRegex(ValueError, CLASS_ERROR), patch('builtins.print'):
            checker.check_all_files()
        self.assert_no_client_calls()

    def test_unselected_class_payload_does_not_block_singleton_inventory_selection(self):
        class_file = Path(self.paths.zenodo_json_dir, "XMLCLASS-" + PAIR_HASH + ".json")
        class_file.write_text(json.dumps({
            "record_target_id": CLASS_ID, "identity_kind": "exact_xml_content_class",
            "upload_eligible": False,
        }), encoding="utf-8")
        class_before = class_file.read_bytes()
        # No legacy class resume exists; only the actual singleton has an inventory grant.
        atomic_json(self.paths.uploads_registry_path, {})
        service = DraftUploadService(self.paths, "sandbox")
        self.assertEqual(service.pending_files(), [str(self.file)])
        preflight_inputs(self.paths, [str(self.file)])
        self.client.create_deposition.return_value = {"id": 123}
        self.client.update_deposition_metadata.return_value = {"id": 123, "metadata": {}}
        result = service.upload(str(self.file), self.client)
        self.assertTrue(result["success"], result.get("error"))
        self.client.create_deposition.assert_called_once_with()
        self.client.update_deposition_metadata.assert_called_once()
        self.client.get_deposition.assert_not_called()
        self.client.publish_deposition.assert_not_called()
        self.client.delete_deposition.assert_not_called()
        self.assertEqual(set(read_json(self.paths.uploads_registry_path)), {SOURCE_ID})
        self.assertEqual(class_file.read_bytes(), class_before)

    def test_selected_duplicate_diagnostics_and_retired_helpers_never_reach_provider(self):
        for marker in ({"source_id": PAIR_ID}, {"record_target_id": CLASS_ID}):
            for protected_location in ("disk", "cached"):
                disk = dict(self.entry, **marker) if protected_location == "disk" else copy.deepcopy(self.entry)
                cached = dict(self.entry, **marker) if protected_location == "cached" else copy.deepcopy(self.entry)
                before = self.write_ledger(disk)
                checker = self.duplicate_checker(cached)
                cached_before = copy.deepcopy(checker.registry_entries)
                with self.subTest(marker=marker, protected_location=protected_location):
                    with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                        checker.check_specific_files([SOURCE_ID])
                    with self.assertRaisesRegex(ValueError, CLASS_ERROR):
                        checker.run_duplicate_check([SOURCE_ID])
                    checker.load_zenodo_depositions.assert_not_called()
                    self.assert_no_client_calls()
                    self.assertEqual(checker.registry_entries, cached_before)
                    self.assertEqual(Path(self.paths.uploads_registry_path).read_bytes(), before)
                if protected_location == "disk":
                    from scripts.deduplicate_check import main

                    argv = ["deduplicate_check", "--output-dir", self.tmp.name,
                            "--check-files", SOURCE_ID, "--log-dir", str(Path(self.tmp.name, "logs"))]
                    logger = Mock()
                    with patch("sys.argv", argv), patch(
                        "scripts.deduplicate_check.default_log_dir", return_value=str(Path(self.tmp.name, "logs"))
                    ), patch("scripts.deduplicate_check.initialize_logger"), patch(
                        "scripts.deduplicate_check.get_logger", return_value=logger
                    ), patch("scripts.deduplicate_check.create_zenodo_client") as factory:
                        try:
                            main()
                        except ValueError as error:
                            self.assertRegex(str(error), CLASS_ERROR)
                        except SystemExit as error:
                            self.assertNotEqual(error.code, 0)
                            self.assertRegex(str(logger.log_error.call_args), CLASS_ERROR)
                        else:
                            self.fail("Selected protected diagnostic returned success")
                        factory.assert_not_called()
        # Retiring the CLI flag must also retire previously reachable direct helpers.
        for cls in (BatchUploader, ZenodoUploader):
            for source_id in (SOURCE_ID, PAIR_ID):
                uploader = cls.__new__(cls)
                uploader.replace_duplicates, uploader.sandbox = True, True
                uploader._replacement_attempted = set()
                uploader.replacement_plan = {source_id: {"existing_deposition_id": 123}}
                uploader.client, uploader.logger = self.client, Mock()
                with self.subTest(helper=cls.__name__, source_id=source_id):
                    with self.assertRaisesRegex(ValueError, "retired"):
                        if cls is BatchUploader:
                            uploader._maybe_replace_existing(source_id, "Synthetic fixture", self.client)
                        else:
                            uploader._maybe_replace_existing(source_id, "Synthetic fixture")
                    self.assert_no_client_calls()
                    self.assertEqual(uploader._replacement_attempted, set())


if __name__ == "__main__":
    unittest.main()
