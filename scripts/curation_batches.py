"""Compile reviewed FGDC correction cohorts to ordinary curator decisions.

Original XML is immutable. Selectors inspect source text, never generated output
or provider records. Compilation supplies no publication or rehosting authority.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from scripts.artifact_contract import fingerprint, prepare_artifact
from scripts.fgdc_to_zenodo import transform_fgdc_file
from scripts.validate_zenodo import ZenodoValidator


SELECTOR_PATHS = {
    'idinfo/citation/citeinfo/origin', 'idinfo/citation/citeinfo/title',
    'idinfo/citation/citeinfo/pubdate', 'idinfo/accconst', 'idinfo/useconst',
    'metainfo/metd', 'metainfo/metrd', 'metainfo/metac', 'metainfo/metuc',
}
NORMALIZATION = 'strip_xml_text'


def _inventory(source_dir):
    sources = {}
    unparsed = []
    for path in sorted(Path(source_dir).glob('*.xml')):
        if path.is_symlink():
            raise ValueError('Source inventory must not contain symlinks')
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        try:
            root = ET.fromstring(raw.decode('utf-8-sig').lstrip('\0\ufeff'))
        except (ET.ParseError, UnicodeError) as exc:
            root = None
            unparsed.append({'source_id': path.stem, 'source_sha256': digest,
                             'error': str(exc)})
        sources[path.stem] = {'path': path, 'sha256': digest, 'root': root}
    if not sources:
        raise ValueError('Source inventory is empty')
    return sources, unparsed


def _select(sources, selector):
    paths = selector['fgdc_paths_equal']
    return sorted(source_id for source_id, source in sources.items()
                  if source['root'] is not None and all(
                      [''.join(node.itertext()).strip()
                       for node in source['root'].findall(path)] == values
                      for path, values in paths.items()))


def compile_batches(manifests, source_dir):
    """Return keyed decisions and a deterministic audit; perform no writes."""
    sources, unparsed = _inventory(source_dir)
    decisions = {}
    batch_audits = []
    for manifest in manifests:
        for batch in manifest['batches']:
            selected = _select(sources, batch['selector'])
            members = sorted(batch['members'], key=lambda member: member['source_id'])
            if sorted(member['source_id'] for member in members) != selected:
                raise ValueError('Exact member list differs from full source selector cohort')
            for member in members:
                source_id = member['source_id']
                if member['source_sha256'] != sources[source_id]['sha256']:
                    raise ValueError('Batch member source hash is stale: ' + source_id)
                decisions[source_id] = dict(deepcopy(batch['correction']), **{
                    'source_sha256': member['source_sha256'],
                    'reviewer': batch['reviewer'], 'reviewed_at': batch['reviewed_at'],
                    'rationale': batch['rationale'], 'evidence': deepcopy(batch['evidence']),
                    'curation_batches': [{'batch_id': batch['batch_id'], 'version': batch['version'],
                                         'batch_sha256': fingerprint(batch)}],
                })
            batch_audits.append({'batch_id': batch['batch_id'], 'version': batch['version'],
                                 'batch_sha256': fingerprint(batch), 'member_count': len(members),
                                 'membership_sha256': fingerprint(members), 'members': members,
                                 'selector': deepcopy(batch['selector'])})
    decisions = dict(sorted(decisions.items()))
    inventory = [{'source_id': source_id, 'source_sha256': source['sha256']}
                 for source_id, source in sorted(sources.items())]
    audit = {'schema_version': 1, 'source_count': len(sources),
             'source_inventory_sha256': fingerprint(inventory), 'unparsed_sources': unparsed,
             'manifests_sha256': fingerprint(manifests), 'batches': batch_audits,
             'decision_count': len(decisions), 'decisions_sha256': fingerprint(decisions),
             'publication_authorized': False}
    return decisions, audit


def validate_outputs(decisions, source_dir):
    """Validate real affected transformations and their existing artifact contracts."""
    validator = ZenodoValidator()
    validated = []
    for source_id, decision in sorted(decisions.items()):
        source = Path(source_dir) / (source_id + '.xml')
        if hashlib.sha256(source.read_bytes()).hexdigest() != decision['source_sha256']:
            raise ValueError('Source changed after batch compilation: ' + source_id)
        payload = transform_fgdc_file(str(source), decisions=decisions)
        if payload is None:
            raise ValueError('Corrected source does not transform: ' + source_id)
        issues, warnings = validator.validate_metadata(payload['metadata'])
        if issues:
            raise ValueError('Corrected output validation failed for ' + source_id + ': ' + '; '.join(issues))
        contract = prepare_artifact(payload, source)
        validated.append({'source_id': source_id, 'source_sha256': decision['source_sha256'],
                          'metadata_sha256': fingerprint(payload['metadata']),
                          'artifact_contract_sha256': contract['sha256'] if contract else None,
                          'warnings': warnings})
    return {'validated_count': len(validated), 'records': validated,
            'records_sha256': fingerprint(validated)}


def _load_json(path):
    with Path(path).open(encoding='utf-8') as handle:
        return json.load(handle)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', required=True, help='Canonical original FGDC directory')
    parser.add_argument('--manifest', action='append', required=True, help='Reviewed batch manifest, in precedence order')
    parser.add_argument('--decisions-out', required=True, help='Ordinary batch_transform --decisions JSON')
    parser.add_argument('--audit-out', required=True, help='Membership, provenance and output validation audit')
    args = parser.parse_args(argv)
    try:
        decisions, audit = compile_batches([_load_json(path) for path in args.manifest], args.sources)
        audit['output_validation'] = validate_outputs(decisions, args.sources)
        for path, value in ((args.decisions_out, decisions), (args.audit_out, audit)):
            Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n')
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, 'Correction batch rejected: ' + str(exc) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
