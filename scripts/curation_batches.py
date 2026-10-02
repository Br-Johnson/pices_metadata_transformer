"""Compile reviewed FGDC correction cohorts to ordinary curator decisions.

Original XML is immutable. Selectors inspect source text, never generated output
or provider records. Compilation supplies no publication or rehosting authority.
"""
import argparse
from copy import deepcopy
from datetime import datetime
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


def _object(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError('Invalid or unknown contract fields')


def _text(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Expected nonempty text')


def _review(value):
    for key in ('reviewer', 'reviewed_at', 'rationale'):
        _text(value[key])
    try:
        stamp = datetime.fromisoformat(value['reviewed_at'].replace('Z', '+00:00'))
        if stamp.utcoffset() is None:
            raise ValueError('Timezone required')
    except ValueError as exc:
        raise ValueError('Invalid timezone-aware reviewed_at') from exc


def _strings(value):
    if not isinstance(value, list) or not value:
        raise ValueError('Expected nonempty text list')
    for item in value:
        _text(item)


def _validate_manifest(manifest):
    _object(manifest, ('schema_version', 'batches'))
    if type(manifest['schema_version']) is not int or manifest['schema_version'] != 1:
        raise ValueError('Unsupported schema version')
    if not isinstance(manifest['batches'], list) or not manifest['batches']:
        raise ValueError('Expected nonempty batches')
    for batch in manifest['batches']:
        _object(batch, ('batch_id', 'version', 'selector', 'members', 'correction',
                        'reviewer', 'reviewed_at', 'rationale', 'evidence'), ('supersedes',))
        _text(batch['batch_id'])
        if type(batch['version']) is not int or batch['version'] != 1:
            raise ValueError('Unsupported batch version')
        _review(batch)
        if not isinstance(batch['evidence'], list) or not batch['evidence']:
            raise ValueError('Expected nonempty evidence')
        for evidence in batch['evidence']:
            if isinstance(evidence, dict):
                _text(evidence.get('kind'))
                try:
                    json.dumps(evidence, allow_nan=False)
                except (TypeError, ValueError) as exc:
                    raise ValueError('Evidence must be finite JSON') from exc
            else:
                _text(evidence)
        if 'supersedes' in batch:
            _strings(batch['supersedes'])
            if len(set(batch['supersedes'])) != len(batch['supersedes']):
                raise ValueError('Duplicate supersedes')
        selector = batch['selector']
        _object(selector, ('normalization',), ('fgdc_paths_equal', 'source_ids'))
        if selector['normalization'] != NORMALIZATION or len(selector) != 2:
            raise ValueError('Unsupported selector semantics')
        if 'source_ids' in selector:
            _strings(selector['source_ids'])
            if len(set(selector['source_ids'])) != len(selector['source_ids']):
                raise ValueError('Duplicate selector source IDs')
        else:
            paths = selector['fgdc_paths_equal']
            if not isinstance(paths, dict) or not paths or set(paths) - SELECTOR_PATHS:
                raise ValueError('Unsupported selector paths')
            for values in paths.values():
                _strings(values)
                if any(value != value.strip() for value in values):
                    raise ValueError('Selector text must use declared normalization')
        members = batch['members']
        if not isinstance(members, list) or not members:
            raise ValueError('Expected nonempty members')
        ids = set()
        for member in members:
            _object(member, ('source_id', 'source_sha256'))
            if not isinstance(member['source_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]+', member['source_id']):
                raise ValueError('Invalid source ID')
            if member['source_id'] in ids:
                raise ValueError('Duplicate member')
            ids.add(member['source_id'])
            if not isinstance(member['source_sha256'], str) or not re.fullmatch(r'[0-9a-f]{64}', member['source_sha256']):
                raise ValueError('Invalid source hash')
        correction = batch['correction']
        _object(correction, (), ('metadata', 'artifact_policy', 'content_classification'))
        if not correction:
            raise ValueError('Empty correction')
        if 'metadata' in correction:
            metadata = correction['metadata']
            _object(metadata, (), ('creators', 'publication_date', 'license'))
            if not metadata:
                raise ValueError('Empty metadata correction')
            for key, value in metadata.items():
                if key == 'creators':
                    if not isinstance(value, list) or not value:
                        raise ValueError('Creators must be nonempty')
                    for creator in value:
                        _object(creator, ('name',), ('type', 'affiliation', 'orcid', 'gnd'))
                        for entry in creator.values():
                            _text(entry)
                        if 'type' in creator and creator['type'] not in ('Personal', 'Organizational', 'Person', 'Organization'):
                            raise ValueError('Invalid creator type')
                else:
                    _text(value)
                    if key == 'publication_date':
                        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
                            raise ValueError('Expected ISO date')
                        datetime.strptime(value, '%Y-%m-%d')
        policy = correction.get('artifact_policy')
        content = correction.get('content_classification')
        if policy is not None:
            _object(policy, ('schema_version', 'object_kind', 'resource_type', 'date_semantics',
                             'reviewer', 'reviewed_at', 'rationale', 'rights_evidence', 'date_evidence', 'source_sha256'),
                    ('source_access_interpretation', 'rehosting_authority', 'creator_interpretation'))
            for key in ('source_access_interpretation', 'rehosting_authority', 'creator_interpretation'):
                if key in policy:
                    reference = policy[key]
                    _object(reference, ('manifest_path', 'manifest_sha256'))
                    _text(reference['manifest_path'])
                    if (not isinstance(reference['manifest_sha256'], str)
                            or not re.fullmatch(r'[0-9a-f]{64}', reference['manifest_sha256'])):
                        raise ValueError('Invalid bound interpretation reference')
            _review(policy)
            for key in ('rights_evidence', 'date_evidence'):
                _text(policy[key])
            if (type(policy['schema_version']) is not int or policy['schema_version'] != 1
                    or policy['object_kind'] != 'original_fgdc_xml' or policy['resource_type'] != 'other'
                    or policy['date_semantics'] not in ('metadata_artifact_publication', 'source_metadata_date')
                    or policy['source_sha256'] != '$source_sha256' or content is None):
                raise ValueError('Invalid source-bound artifact policy')
        elif 'artifact_policy' in correction:
            raise ValueError('Null artifact policy')
        if content is not None:
            _object(content, ('inventory_complete', 'reviewer', 'reviewed_at', 'rationale', 'files'), ('content_status',))
            _review(content)
            if content['inventory_complete'] is not True or not isinstance(content['files'], list) or len(content['files']) != 1:
                raise ValueError('Only complete original XML inventory supported')
            item = content['files'][0]
            _object(item, ('name', 'role', 'evidence'))
            _text(item['evidence'])
            if item['name'] != '$source_filename' or item['role'] != 'descriptive_metadata' or content.get('content_status', 'metadata_only') != 'metadata_only':
                raise ValueError('Only source-bound descriptive metadata supported')
            if policy is None:
                raise ValueError('Content inventory requires matching artifact policy')
        elif 'content_classification' in correction:
            raise ValueError('Null content classification')


def load_manifest(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    with Path(path).open(encoding='utf-8') as handle:
        manifest = json.load(handle, object_pairs_hook=unique,
                             parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON value')))
    _validate_manifest(manifest)
    return manifest


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
    if 'source_ids' in selector:
        selected = sorted(selector['source_ids'])
        if any(source_id not in sources or sources[source_id]['root'] is None for source_id in selected):
            raise ValueError('Explicit selector references missing or malformed source')
        return selected
    paths = selector['fgdc_paths_equal']
    return sorted(source_id for source_id, source in sources.items()
                  if source['root'] is not None and all(
                      [''.join(node.itertext()).strip()
                       for node in source['root'].findall(path)] == values
                      for path, values in paths.items()))


def compile_batches(manifests, source_dir):
    """Return keyed decisions and a deterministic audit; perform no writes."""
    if not isinstance(manifests, list) or not manifests:
        raise ValueError("Expected nonempty manifests")
    for manifest in manifests:
        _validate_manifest(manifest)
    sources, unparsed = _inventory(source_dir)
    seen = set()
    active = {}
    overlaps = []
    decisions = {}
    batch_audits = []
    for manifest in manifests:
        for batch in manifest['batches']:
            batch_id = batch['batch_id']
            supersedes = set(batch.get('supersedes', []))
            if batch_id in seen or supersedes - seen:
                raise ValueError('Duplicate batch ID or supersedes must name earlier batch IDs')
            seen.add(batch_id)
            selected = _select(sources, batch['selector'])
            members = sorted(batch['members'], key=lambda member: member['source_id'])
            if sorted(member['source_id'] for member in members) != selected:
                raise ValueError('Exact member list differs from full source selector cohort')
            for member in members:
                source_id = member['source_id']
                if member['source_sha256'] != sources[source_id]['sha256']:
                    raise ValueError('Batch member source hash is stale: ' + source_id)
                correction = deepcopy(batch['correction'])
                if 'artifact_policy' in correction:
                    correction['artifact_policy']['source_sha256'] = member['source_sha256']
                    correction['content_classification']['files'][0]['name'] = source_id + '.xml'
                fields = {('metadata.' + key): value for key, value in correction.pop('metadata', {}).items()}
                fields.update(correction)
                decision = decisions.setdefault(source_id, {'source_sha256': member['source_sha256'],
                    'reviewer': '', 'reviewed_at': batch['reviewed_at'], 'rationale': '',
                    'evidence': [], 'curation_batches': []})
                owners = active.setdefault(source_id, {})
                for field, value in fields.items():
                    if field in owners:
                        previous, prior_ids = owners[field]
                        conflict = previous != value
                        if conflict and not prior_ids <= supersedes:
                            raise ValueError('Unreviewed field conflict: ' + source_id + '/' + field)
                        overlaps.append({'source_id': source_id, 'field': field,
                            'prior_batch_ids': sorted(prior_ids), 'batch_id': batch_id,
                            'resolution': 'superseded' if conflict else 'equal'})
                        owners[field] = (value, {batch_id} if conflict else prior_ids | {batch_id})
                    else:
                        owners[field] = (value, {batch_id})
                    if field.startswith('metadata.'):
                        decision.setdefault('metadata', {})[field.split('.', 1)[1]] = value
                    else:
                        decision[field] = value
                decision['reviewer'] += ('; ' if decision['reviewer'] else '') + batch['reviewer']
                decision['rationale'] += ('\n' if decision['rationale'] else '') + batch['rationale']
                decision['reviewed_at'] = batch['reviewed_at']
                decision['evidence'].extend(deepcopy(batch['evidence']))
                decision['curation_batches'].append({key: deepcopy(batch[key]) for key in
                    ('batch_id', 'version', 'reviewer', 'reviewed_at', 'rationale', 'evidence')})
                decision['curation_batches'][-1].update(batch_sha256=fingerprint(batch),
                    supersedes=sorted(supersedes))
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
             'overlaps': overlaps, 'publication_authorized': False}
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sources', required=True, help='Canonical original FGDC directory')
    parser.add_argument('--manifest', action='append', required=True, help='Reviewed batch manifest, in precedence order')
    parser.add_argument('--decisions-out', required=True, help='Ordinary batch_transform --decisions JSON')
    parser.add_argument('--audit-out', required=True, help='Membership, provenance and output validation audit')
    args = parser.parse_args(argv)
    try:
        outputs = [Path(args.decisions_out).resolve(), Path(args.audit_out).resolve()]
        source_root = Path(args.sources).resolve()
        if (outputs[0] == outputs[1] or any(source_root == path or source_root in path.parents for path in outputs)
                or set(outputs) & {Path(path).resolve() for path in args.manifest}):
            raise ValueError('Output paths must be distinct and outside source inventory and input manifests')
        if any(path.exists() for path in outputs):
            raise ValueError('Output paths must be new files; existing files are never overwritten')
        decisions, audit = compile_batches([load_manifest(path) for path in args.manifest], args.sources)
        audit['output_validation'] = validate_outputs(decisions, args.sources)
        for path, value in ((args.decisions_out, decisions), (args.audit_out, audit)):
            with Path(path).open('x', encoding='utf-8') as handle:
                handle.write(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n')
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(1, 'Correction batch rejected: ' + str(exc) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
