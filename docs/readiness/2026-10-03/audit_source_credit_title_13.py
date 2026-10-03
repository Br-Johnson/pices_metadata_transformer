"""Audit all original/copy/payload bytes and the exact thirteen source corrections."""
import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[3]
DOCS = Path(__file__).resolve().parent
BASELINE_SHA = 'f89ea06557eced0b0184d723a5a2fd576c036e795e4028ba55fb81baa67e69a0'
CREDIT_SHA = '217a11a96ffbc1f55d6e065cfcc5fac34efd4a10057b399e4a6e25faa076887a'
TITLE_SHA = 'fa08a25108bbd90a03fe0c107d5b4398403deabd76df2b839830fde05eb46780'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fp(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())


def audit(before_dir, after_dir):
    before_raw = (before_dir / 'classification.json').read_bytes()
    after_raw = (after_dir / 'classification.json').read_bytes()
    assert sha(before_raw) == BASELINE_SHA
    before, after = json.loads(before_raw), json.loads(after_raw)
    assert before['summary']['source_status_counts'] == {'supported': 2430, 'held': 1770, 'failed': 6}
    assert after['summary']['source_status_counts'] == {'supported': 2443, 'held': 1757, 'failed': 6}
    assert after['summary']['technical_metadata_counts'] == {'pass': 4142, 'held': 52, 'not_constructed': 12}
    for key in set(before['summary']) - {'source_status_counts', 'technical_metadata_counts'}:
        assert before['summary'][key] == after['summary'][key]
    assert before['reviewed_at'] == after['reviewed_at']
    credit_path, title_path = DOCS / 'source_citation_credits_401.json', DOCS / 'source_display_titles_8.json'
    assert sha(credit_path.read_bytes()) == CREDIT_SHA and sha(title_path.read_bytes()) == TITLE_SHA
    credits, title_manifest = json.loads(credit_path.read_bytes()), json.loads(title_path.read_bytes())
    previous = json.loads((DOCS / 'access_held_source_citations_396.json').read_bytes())
    assert credits['cohorts'][:220] == previous['cohorts']
    all_credits = {m['source_id']: c for c in credits['cohorts'] for m in c['members']}
    added = {m['source_id']: c for c in credits['cohorts'][220:] for m in c['members']}
    titles = {m['source_id']: m for m in title_manifest['members']}
    promoted = set(added) | set(titles)
    assert len(all_credits) == 401 and len(added) == 5 and len(titles) == 8 and len(promoted) == 13
    protected = {m['source_id'] for m in json.loads((DOCS / 'remaining_source_credit_candidates_86.json').read_bytes())['members']}
    protected |= {m['source_id'] for g in json.loads((DOCS / 'joint_collection_source_decisions.json').read_bytes())['remaining_meaning_decisions'] for m in g['members']}
    assert len(protected) == 176 and not promoted & protected
    left, right = [{r['source_id']: r for r in report['records']} for report in (before, after)]
    originals, copies, payloads, metadata = [], [], [], []
    changed_policy, changed_metadata, assessed_changed = [], [], []
    buckets = defaultdict(list)
    sources = sorted((REPO / 'FGDC').glob('*.xml'))
    assert {p.stem for p in sources} == set(left) == set(right)
    for source in sources:
        sid, raw = source.stem, source.read_bytes(); l, r = left[sid], right[sid]
        assert l['source_sha256'] == r['source_sha256'] == sha(raw)
        originals.append({'source_id': sid, 'source_sha256': sha(raw)}); buckets[sha(raw)].append(sid)
        assert l['exact_copy_aliases'] == r['exact_copy_aliases']
        assert not r['remote_verified'] and not r['publication_approved']
        if sid in promoted:
            assert l['source_status'] == 'held' and r['source_status'] == 'supported'
            assert not r['hold_reasons'] and not r['exact_copy_aliases']
        else:
            assert l['source_status'] == r['source_status'] and l['hold_reasons'] == r['hold_reasons']
            assert l['technical_metadata'] == r['technical_metadata']
        if sid in protected or r['exact_copy_aliases']:
            assert r['source_status'] == 'held'
        if l.get('metadata_sha256') != r.get('metadata_sha256'):
            assert sid in all_credits; assessed_changed.append(sid)
        if r['source_status'] == 'failed':
            continue
        for directory in (before_dir, after_dir):
            assert (directory / 'data/original_fgdc' / source.name).read_bytes() == raw
        copies.append({'source_id': sid, 'source_sha256': sha(raw)})
        if not r.get('prepared_payload_sha256'):
            assert not l.get('prepared_payload_sha256'); continue
        raws = [(directory / 'data/zenodo_json' / (sid + '.json')).read_bytes() for directory in (before_dir, after_dir)]
        assert sha(raws[0]) == l['prepared_payload_sha256'] and sha(raws[1]) == r['prepared_payload_sha256']
        old, new = map(json.loads, raws); expected = deepcopy(old)
        if sid in all_credits:
            expected['artifact_policy']['creator_interpretation'] = {'manifest_path': str(credit_path.relative_to(REPO)), 'manifest_sha256': CREDIT_SHA}
            changed_policy.append(sid)
        else:
            assert raws[0] == raws[1]
        if sid in added:
            c = added[sid]; expected['metadata']['creators'] = c['creators']
            line = next(line for line in old['metadata']['notes'].splitlines() if line.startswith('Curator decision: '))
            decision = json.loads(line.removeprefix('Curator decision: ')); decision['metadata']['creators'] = c['creators']
            expected['metadata']['notes'] = expected['metadata']['notes'].replace(line, 'Curator decision: ' + json.dumps(decision, sort_keys=True), 1)
            suffix = '\nSource dataset citation originators are preserved for attribution; XML authorship is not independently established.'
            assert expected['metadata']['notes'].endswith(suffix)
            # Preserve the parsed primary origin and the exact reviewed role note.
            origin = ET.parse(source).getroot().find('./idinfo/citation/citeinfo/origin'); origin.tail = None
            notes = ['Original primary citation origin XML (parsed representation): ' + ET.tostring(origin, encoding='unicode'), c['context_note']]
            expected['metadata']['notes'] = expected['metadata']['notes'][:-len(suffix)] + ''.join('\n' + note for note in notes) + suffix
        if sid in titles:
            m = titles[sid]; assert fp(old['metadata']) == m['metadata_before_sha256']
            expected['artifact_policy']['source_title_interpretation'] = {'manifest_path': str(title_path.relative_to(REPO)), 'manifest_sha256': TITLE_SHA}
            expected['metadata']['title'] = m['display_title']; expected['metadata']['notes'] += '\n\n' + m['preservation_note']
            assert fp(expected['metadata']) == m['metadata_after_sha256']
        assert expected == new, sid
        if old['metadata'] != new['metadata']:
            changed_metadata.append(sid)
        assert new['metadata']['license'] == '' and new['metadata']['access_right'] == 'restricted'
        payloads.append({'source_id': sid, 'prepared_payload_sha256': sha(raws[1])})
        metadata.append({'source_id': sid, 'metadata_sha256': fp(new['metadata'])})
    assert len(originals) == 4206 and len(copies) == 4200 and len(payloads) == 4194
    assert set(changed_metadata) == promoted and set(changed_policy) == set(all_credits)
    aliases = sorted(sorted(ids) for ids in buckets.values() if len(ids) > 1)
    assert len(aliases) == 228 and sum(map(len, aliases)) == 456
    for directory in (before_dir, after_dir):
        assert len(list((directory / 'data/original_fgdc').glob('*.xml'))) == 4200
        assert len(list((directory / 'data/zenodo_json').glob('*.json'))) == 4194
    return {'scope': 'Exact five source credits and eight preserved display titles; no provider approval',
        'baseline_report_sha256': sha(before_raw), 'after_report_sha256': sha(after_raw), 'summary': after['summary'],
        'promoted_source_ids': sorted(promoted), 'promotions': 13, 'creator_corrections': 5, 'title_corrections': 8,
        'previous_220_cohort_objects_396_members_unchanged': True, 'full_metadata_objects_unchanged': 4181,
        'policy_references_changed': 401, 'payload_bytes_unchanged': 3793, 'assessed_artifact_fingerprints_changed': len(assessed_changed),
        'all_other_statuses_and_hold_reasons_unchanged': True, 'protected_access_holds_held': 176, 'alias_identities_held': 456,
        'originals_verified': 4206, 'copies_verified': 4200, 'payloads_verified': 4194,
        'original_inventory_sha256': fp(originals), 'copy_inventory_sha256': fp(copies),
        'payload_inventory_sha256': fp(payloads), 'metadata_inventory_sha256': fp(metadata), 'alias_groups_sha256': fp(aliases),
        'new_licenses': 0, 'provider_requests': 0, 'provider_writes': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', type=Path, required=True); parser.add_argument('--after', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.before, args.after), indent=2))
