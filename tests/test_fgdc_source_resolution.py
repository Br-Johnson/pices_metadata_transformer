"""Original-source identity is established before payload or provider operations."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

from scripts.fgdc_utils import locate_fgdc_xml, load_fgdc_xml
from scripts.path_config import OutputPaths
from scripts.upload_service import DraftUploadService, atomic_json, metadata_hash, prepare_metadata


class FGDCSourceResolutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        previous = os.getcwd()
        os.chdir(self.tmp.name)
        self.addCleanup(os.chdir, previous)
        self.paths = OutputPaths(str(Path(self.tmp.name, 'output')), 'sandbox')
        self.canonical = Path('FGDC/sample.xml')
        self.canonical.parent.mkdir()
        self.copy = Path(self.paths.original_fgdc_dir, 'sample.xml')
        self.legacy = Path(self.paths.base, 'sample.xml')
        self.raw = b'\r\n<metadata><title>Canonical descriptive source</title></metadata>\r\n'
        self.json_file = Path(self.paths.zenodo_json_dir, 'sample.json')
        self.json_file.write_text(json.dumps({'metadata': {
            'title': 'Canonical descriptive source', 'notes': '', 'description': 'Descriptive source fixture',
            'upload_type': 'dataset', 'publication_date': '2000-01-01',
            'creators': [{'name': 'Smith, Jane'}], 'license': 'cc-zero', 'access_right': 'open'}}))

    def assert_source_bytes(self, path):
        metadata, source, digest = prepare_metadata(str(self.json_file), self.paths)
        self.assertEqual(source, str(path))
        self.assertEqual(digest, hashlib.sha256(self.raw).hexdigest())
        self.assertIn('<metadata><title>Canonical descriptive source</title></metadata>', metadata['notes'])
        self.assertEqual(path.read_bytes(), self.raw)

    def test_canonical_only_and_compatible_copied_or_legacy_fallback(self):
        for path in (self.canonical, self.copy, self.legacy):
            with self.subTest(path=path):
                path.write_bytes(self.raw)
                self.assert_source_bytes(path)
                path.unlink()
        self.assertEqual(load_fgdc_xml('missing', self.paths), (None, None))

    def test_identical_fallbacks_preserve_bytes_and_existing_precedence(self):
        self.copy.write_bytes(self.raw); self.legacy.write_bytes(self.raw)
        self.assert_source_bytes(self.copy)

    def test_canonical_source_precedes_identical_prepared_copies(self):
        self.canonical.write_bytes(self.raw); self.copy.write_bytes(self.raw); self.legacy.write_bytes(self.raw)
        self.assert_source_bytes(self.canonical)
        self.assertEqual(locate_fgdc_xml('sample', self.paths), str(self.canonical))

    def test_divergent_copy_blocks_upload_before_any_client_call(self):
        self.canonical.write_bytes(self.raw)
        metadata = prepare_metadata(str(self.json_file), self.paths)[0]
        atomic_json(self.paths.safe_to_upload_path, {
            'environment': 'sandbox', 'inventory_complete': True, 'files': ['sample.json'],
            'metadata_hashes': {'sample.json': metadata_hash(metadata)},
            'valid_until': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()})
        self.copy.write_bytes(b'<metadata><title>Divergent prepared source</title></metadata>')
        original_copy = self.copy.read_bytes()
        client = Mock(base_url='https://sandbox.zenodo.org')
        client.create_deposition.return_value = {'id': 123}
        client.update_deposition_metadata.return_value = {'metadata': {}}
        with self.assertRaisesRegex(ValueError, 'Conflicting FGDC'):
            DraftUploadService(self.paths, 'sandbox').upload(str(self.json_file), client)
        self.assertEqual(client.mock_calls, [])
        self.assertEqual(self.canonical.read_bytes(), self.raw)
        self.assertEqual(self.copy.read_bytes(), original_copy)
        self.assertFalse(Path(self.paths.uploads_registry_path).exists())

    def test_divergent_fallbacks_are_not_silently_selected(self):
        self.copy.write_bytes(self.raw)
        self.legacy.write_bytes(b'<metadata><title>Different legacy source</title></metadata>')
        with self.assertRaisesRegex(ValueError, 'Conflicting FGDC'):
            load_fgdc_xml('sample', self.paths)

    def test_identical_paths_and_symlink_aliases_preserve_canonical_hash(self):
        self.canonical.write_bytes(self.raw)
        self.copy.symlink_to(self.canonical.resolve())
        self.assert_source_bytes(self.canonical)
        overlapping_paths = OutputPaths('FGDC', 'sandbox')
        self.assertEqual(locate_fgdc_xml('sample', overlapping_paths), str(self.canonical))

    def test_unreadable_present_copy_is_not_ignored(self):
        self.canonical.write_bytes(self.raw); self.copy.write_bytes(self.raw)
        original_read = Path.read_bytes
        def read(path):
            if path == self.copy:
                raise PermissionError('Unreadable prepared source fixture')
            return original_read(path)
        with patch.object(Path, 'read_bytes', read), self.assertRaisesRegex(PermissionError, 'Unreadable'):
            prepare_metadata(str(self.json_file), self.paths)

    def test_present_nonfile_and_dangling_candidates_are_ambiguous(self):
        self.copy.write_bytes(self.raw)
        for kind in ('directory', 'dangling_symlink'):
            with self.subTest(kind=kind):
                if kind == 'directory': self.canonical.mkdir()
                else: self.canonical.symlink_to('missing-source.xml')
                with self.assertRaisesRegex(ValueError, 'Ambiguous FGDC'):
                    locate_fgdc_xml('sample', self.paths)
                if kind == 'directory': self.canonical.rmdir()
                else: self.canonical.unlink()


if __name__ == '__main__':
    unittest.main()
