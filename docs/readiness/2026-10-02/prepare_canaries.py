"""Prepare source-backed and synthetic sandbox drafts offline; never upload.

Run from repo root with --output-dir PATH to a new local task workspace.
Source-policy uncertainties are retained; no publication approval is generated.
"""
import argparse
import hashlib
import json
import socket
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path.cwd()))
from scripts.artifact_contract import prepare_artifact
from scripts.fgdc_to_zenodo import FGDCToZenodoTransformer
from scripts.path_config import OutputPaths
from scripts.upload_service import atomic_json, metadata_hash, prepare_metadata
from scripts.validate_zenodo import ZenodoValidator


def prepare(output_dir):
    root = Path(output_dir)
    if root.exists():
        raise ValueError('Use a new workspace to preserve previous canary evidence')
    paths = OutputPaths(str(root), 'sandbox')
    records = []
    today = datetime.now(timezone.utc).date().isoformat()
    with patch('scripts.fgdc_to_zenodo.get_logger', return_value=Mock()), patch('scripts.validate_zenodo.get_logger', return_value=Mock()):
        transformer, validator = FGDCToZenodoTransformer(), ZenodoValidator()
        for sid in ('FGDC-767', 'FGDC-832', 'FGDC-854', 'SYNTHETIC-TRANSPORT-ONLY'):
            synthetic = sid.startswith('SYNTHETIC')
            raw = ((f'<metadata><idinfo><citation><citeinfo><origin>Synthetic fixture author (fictional)</origin>'
                    f'<pubdate>{today.replace("-", "")}</pubdate><title>SYNTHETIC TEST ONLY - transport fixture</title>'
                    '</citeinfo></citation><descript><abstract>Newly authored fictional descriptive XML for sandbox transport testing. '
                    'Contains no authentic PICES source or research data.</abstract></descript><useconst>Unresolved; not for publication</useconst>'
                    f'</idinfo><metainfo><metd>{today.replace("-", "")}</metd></metainfo></metadata>').encode()
                   if synthetic else (Path('FGDC') / (sid + '.xml')).read_bytes())
            source_path = Path(paths.original_fgdc_dir) / (sid + '.xml')
            source_path.write_bytes(raw)  # Copy only: never mutate repository sources.
            xml = ET.fromstring(raw)
            source_hash = hashlib.sha256(raw).hexdigest()
            origin = xml.findtext('./idinfo/citation/citeinfo/origin')
            metadata_date = xml.findtext('./metainfo/metd')
            rights = xml.findtext('./idinfo/useconst')
            policy = {'schema_version': 1, 'object_kind': 'original_fgdc_xml', 'resource_type': 'other',
                      'source_sha256': source_hash, 'date_semantics': 'source_metadata_date',
                      'reviewer': 'Codex - authorized technical preparer, not human publication approver',
                      'reviewed_at': today, 'rationale': 'Nonpublishing sandbox technical preparation only',
                      'date_evidence': 'Source metainfo/metd: ' + metadata_date + '; retained as metadata date, not underlying work publication date',
                      'rights_evidence': 'No license assigned. Raw source use constraints: ' + rights + '; technical test authorization is not a redistribution license or publication approval.'}
            classification = {'inventory_complete': True, 'reviewer': policy['reviewer'], 'reviewed_at': today,
                              'rationale': 'Inspected descriptive XML only; underlying research data absent',
                              'files': [{'name': source_path.name, 'role': 'descriptive_metadata',
                                         'evidence': 'Raw XML contains descriptive metadata fields, not underlying observations'}]}
            transformer.active_decision = {'metadata': {'publication_date': metadata_date,
                                                       'creators': [{'name': origin, 'type': 'Organization'}], 'license': ''},
                                           'artifact_policy': policy, 'content_classification': classification}
            metadata = transformer._build_zenodo_metadata(xml, str(source_path))
            if metadata is None:
                raise ValueError(sid + ': technical metadata construction failed')
            metadata['title'] = ('SYNTHETIC TEST ONLY - transport fixture' if synthetic
                                 else '[SANDBOX TECHNICAL TEST ONLY] ' + metadata['title'] + ' - FGDC XML metadata artifact')
            metadata['access_right'] = 'restricted'
            metadata['access_conditions'] = 'Sandbox technical test only; no public release approved.'
            metadata['notes'] += ('\n\nSandbox technical draft only; not approved for publication. Date field preserves source metadata date. '
                                  'Creator name preserves institutional source origin as imported source attribution; '
                                  'metadata-artifact authorship is not independently established. Original research dates and rights remain in raw XML.')
            metadata['communities'] = []  # No community submission for a technical test.
            payload = {'metadata': metadata, 'artifact_policy': policy, 'content_classification': classification}
            json_file = Path(paths.zenodo_json_dir) / (sid + '.json')
            atomic_json(json_file, payload)
            submitted, _, digest = prepare_metadata(str(json_file), paths)
            issues, _ = validator.validate_metadata(submitted)
            if issues:
                raise ValueError(sid + ': ' + '; '.join(issues))
            records.append({'source_id': sid, 'synthetic': synthetic, 'source_sha256': digest,
                            'metadata_sha256': metadata_hash(submitted),
                            'artifact_contract': prepare_artifact(payload, source_path),
                            'technical_validation': 'pass', 'publication_approved': False,
                            'raw_research_date': xml.findtext('./idinfo/citation/citeinfo/pubdate'),
                            'prepared_metadata_date': submitted['publication_date'],
                            'raw_origin': origin, 'license_assigned': False, 'remote_writes_performed': 0})
    manifest = {'environment': 'sandbox', 'purpose': 'offline technical preparation only',
                'maximum_first_live_batch': 1, 'recommended_first_case': 'SYNTHETIC-TRANSPORT-ONLY',
                'inventory_status': 'unchecked', 'authentication_status': 'unavailable_in_execution_environment',
                'live_execution_eligible': False, 'records': records}
    atomic_json(root / 'canary_preparation.json', manifest)
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    with patch.object(socket.socket, 'connect', side_effect=AssertionError('Offline preparation')):
        result = prepare(args.output_dir)
    print(json.dumps(result, indent=2))
