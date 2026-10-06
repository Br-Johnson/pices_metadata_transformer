"""Real-source schema8 preparations cannot claim historical runtime authority.

Only synthetic standalone preparation packets are backdated. The successfully
created dummy draft's actual journal, intent, grant, receipts and preparation
remain byte-for-byte intact. No real provider or historical migration is used.
"""

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import modern_publication as publication
from scripts import modern_singleton as mapping
from scripts import modern_singleton_executor as draft
from tests import modern_singleton_fixtures as fixtures
from tests.test_modern_organizational_coverage import PublicationFixture
from tests.test_modern_upload_compatibility import CompatibilityTransport


class ModernSchema8HistoryBoundaryTests(unittest.TestCase):
    def test_actual_schema8_source_cannot_backdate_before_any_history_read(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
                draft, 'Transport', side_effect=AssertionError('Real transport forbidden')):
            root = Path(directory)
            source_root = root / 'source'
            source_root.mkdir()
            prepared_root = fixtures.prepare_sources(source_root, ids=['FGDC-1'])
            fixture = fixtures.Fixture(root / 'draft', prepared_root, source_id='FGDC-1')
            self.assertEqual(fixture.prepared.source_id, 'FGDC-1')
            self.assertEqual(fixture.prepared.evidence['schema_version'], 8)
            self.assertEqual(fixture.prepared.evidence['policy'], mapping.REVIEWED_CREATORS_POLICY)
            self.assertEqual(fixture.prepared.evidence['mapping_manifest_sha256'],
                             mapping.REVIEWED_CREATORS_MAPPING_SHA)
            self.assertEqual(fixture.prepared.xml, (mapping.ROOT / 'FGDC/FGDC-1.xml').read_bytes())
            fixture.transport = CompatibilityTransport(fixture, complete_on_content=True)
            harness = PublicationFixture(fixture)
            prepared, bound = harness.bridge()
            self.assertEqual(prepared, fixture.prepared)
            self.assertEqual(bound['original_runtime_sha256'], prepared.evidence['runtime_sha256'])
            self.assertEqual(bound['runtime_sha256'], prepared.evidence['runtime_sha256'])
            journal_path = Path(fixture.paths.uploads_registry_path + '.modern-v1.json')
            journal = mapping.parse(journal_path.read_bytes())
            self.assertEqual(journal['targets']['FGDC-1']['counts'],
                             {'get': 5, 'create': 1, 'init': 1, 'content': 1, 'commit': 0})
            calls = list(fixture.transport.calls)
            self.assertEqual([call[0] for call in calls if call[0] != 'GET'], ['POST', 'POST', 'PUT'])
            original_packet = mapping.parse(harness.packet.read_bytes())
            originals = {path: path.read_bytes() for path in fixture.root.rglob('*') if path.is_file()}
            for number in range(34, 47):
                with self.subTest(historical_release=number):
                    runtime = getattr(publication, f'PR{number}_RUNTIME')
                    self.assertNotEqual(runtime, prepared.evidence['runtime_sha256'])
                    packet = copy.deepcopy(original_packet)
                    packet['evidence']['runtime_sha256'] = runtime
                    packet['binding'] = mapping.sha(mapping.encode(packet['evidence']))
                    self.assertEqual(packet['evidence'], dict(prepared.evidence, runtime_sha256=runtime))
                    # Only this standalone, synthetic packet is changed. The
                    # controller must reject it before reading the true history;
                    # an inconsistent old journal cannot explain this rejection.
                    forged = root / f'backdated-PR{number}-preparation.json'
                    forged.write_bytes(mapping.encode(packet))
                    before = forged.read_bytes()
                    with patch.object(draft, 'read_document', wraps=draft.read_document) as reads:
                        with self.assertRaises(ValueError):
                            publication.bridge(fixture.json_file, fixture.paths, forged,
                                               fixture.grant_path, fixture.proof_path)
                    self.assertEqual([call.args[0] for call in reads.call_args_list], [forged])
                    self.assertEqual(forged.read_bytes(), before)
                    self.assertEqual({path: path.read_bytes() for path in originals}, originals)
                    self.assertEqual(fixture.transport.calls, calls)


if __name__ == '__main__':
    unittest.main()
