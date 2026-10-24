"""Reviewed exact corrections of a source's metadata date; no rights, access or release grant.

Purpose: five FGDC records cannot supply an exact metadata date (metainfo/metd) from their own
text. Three DFO Ocean Science and Productivity records read "2080207", a seven-digit typo for
20080207, and two NOAA bottom-trawl records leave the field blank. Brett decided the corrected
days on 2026-10-23 (docs/readiness/2026-10-23/held_sources_decisions.json, questions C1 and C2).
The pinned manifest binds each correction to the exact source bytes and the exact source value.

Invariants: the original XML is never changed; the corrected day replaces the source value only
in the prepared input's publication date, the artifact policy's date evidence and the public
record's note. A correction applies to one source hash and one exact source value, and nothing
here grants rehosting authority, a licence or a release.
"""
import hashlib
import json
import re
from datetime import date
from pathlib import Path

MANIFEST_SHA256 = 'e28c8da137b97e7747c862476e461cf359f060da2a4f3a0166568e111f6bebca'
KIND = 'pices-metadata-date-corrections-v1'
SOURCE_XPATH = './metainfo/metd'


def _manifest(reference):
    """Load only the pinned reviewed manifest; a refreshed hash cannot widen it."""
    if (not isinstance(reference, dict) or set(reference) != {'manifest_path', 'manifest_sha256'}
            or not isinstance(reference.get('manifest_path'), str) or not reference['manifest_path'].strip()
            or reference.get('manifest_sha256') != MANIFEST_SHA256):
        raise ValueError('Metadata date correction requires the exact reviewed manifest reference')
    try:
        raw = Path(reference['manifest_path']).read_bytes()
    except OSError as exc:
        raise ValueError('Metadata date correction manifest is unavailable') from exc
    if hashlib.sha256(raw).hexdigest() != reference['manifest_sha256']:
        raise ValueError('Metadata date correction manifest differs from the reviewed decisions')
    manifest = json.loads(raw)
    if (not isinstance(manifest, dict) or manifest.get('kind') != KIND or manifest.get('schema_version') != 1
            or manifest.get('status') != 'USER_DECIDED' or manifest.get('decided_by') != 'Brett Johnson'
            or manifest.get('decided_at') != '2026-10-23' or manifest.get('source_xpath') != SOURCE_XPATH
            or any(manifest.get(key) is not False for key in
                   ('grants_rehosting', 'grants_new_license', 'publication_approved'))
            or not isinstance(manifest.get('corrections'), dict) or not manifest['corrections']):
        raise ValueError('Metadata date correction manifest must preserve the exact USER_DECIDED corrections')
    for evidence in manifest['original_statement_references']:
        try:
            raw_evidence = (Path(__file__).resolve().parents[1] / evidence['manifest_path']).read_bytes()
        except OSError as exc:
            raise ValueError('Metadata date decision evidence is unavailable') from exc
        if hashlib.sha256(raw_evidence).hexdigest() != evidence['manifest_sha256']:
            raise ValueError('Metadata date correction requires unchanged decision evidence')
    return manifest


def correction_member_ids(reference):
    """Invalid or withdrawn evidence selects no source for a correction."""
    try:
        manifest = _manifest(reference)
    except ValueError:
        return frozenset()
    return frozenset(manifest['corrections'])


def validate_metadata_date_correction(reference, source_id, source_sha256, root):
    """Return the corrected day only for the exact source bytes and the exact source value."""
    manifest = _manifest(reference)
    entry = manifest['corrections'].get(source_id)
    if (not isinstance(entry, dict) or not isinstance(source_sha256, str)
            or not re.fullmatch(r'[0-9a-f]{64}', source_sha256) or entry.get('source_sha256') != source_sha256):
        raise ValueError('Source ID/hash is outside the reviewed metadata date corrections')
    nodes = root.findall(SOURCE_XPATH)
    if len(nodes) > 1 or any(list(node) or node.attrib for node in nodes):
        raise ValueError('Metadata date correction requires one plain source metadata date field')
    source_value = re.sub(r'\s+', ' ', nodes[0].text or '').strip() if nodes else ''
    if source_value != entry.get('source_value'):
        raise ValueError('Metadata date correction covers only its exact source value')
    corrected = entry.get('corrected_value')
    try:
        if not isinstance(corrected, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', corrected):
            raise ValueError
        date.fromisoformat(corrected)
    except ValueError as exc:
        raise ValueError('Metadata date correction must be an exact calendar day') from exc
    return {'status': 'USER_DECIDED', 'source_id': source_id, 'source_sha256': source_sha256,
            'source_value': source_value, 'corrected_value': corrected, 'question': entry['question'],
            'reason': entry['reason'], 'decided_by': manifest['decided_by'], 'decided_at': manifest['decided_at'],
            'grants_rehosting': False, 'grants_new_license': False, 'publication_approved': False}


def validate_metadata_date_policy(policy, source_id, source_sha256, root):
    """Common QA gate: a correction changes the day of the original XML artifact policy and nothing else."""
    if (policy.get('object_kind') != 'original_fgdc_xml' or policy.get('date_semantics') != 'source_metadata_date'
            or policy.get('rights_scope') != 'original_fgdc_xml'):
        raise ValueError('Metadata date correction requires the original XML artifact policy')
    return validate_metadata_date_correction(policy.get('metadata_date_correction'), source_id, source_sha256, root)
