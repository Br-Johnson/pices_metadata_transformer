"""Record the v1 wire SHA256 of every prepared input under a copy of the production data (creators64 regression check).

Purpose: show that adding the creators64 policy (2026-10-22) changed no prepared source's v1 wire.
The production data folder is never written: pass a copy of `<OUTPUT>/data` as --data-root.

Usage:
  python -B docs/readiness/2026-10-22/check_creators64_wire_regression.py record --data-root COPY --output OUT.json [--ids FILE]
  python -B docs/readiness/2026-10-22/check_creators64_wire_regression.py compare BEFORE.json AFTER.json

`record` prepares every data/zenodo_json/FGDC-*.json (or the ids listed) with the live
modern_singleton.prepare and writes, per source, the policy, schema version, wire SHA256,
prepared-input SHA256 and the evidence without the runtime binding. A source the mapper
holds is recorded as held with the exception text. `compare` reports every source whose
wire, policy or evidence (runtime excluded) differs between two recordings.
"""
import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from scripts import modern_singleton as mapping  # noqa: E402
from scripts.path_config import OutputPaths  # noqa: E402


def record(data_root, output, ids=None):
    paths = OutputPaths(data_root, 'production')
    folder = Path(paths.zenodo_json_dir)
    files = sorted(folder.glob('FGDC-*.json'), key=lambda p: int(p.stem[5:]))
    if ids:
        wanted = set(ids)
        files = [f for f in files if f.stem in wanted]
    rows, started = {}, time.time()
    for index, json_file in enumerate(files, 1):
        try:
            prepared = mapping.prepare(json_file, paths)
            evidence = {k: v for k, v in prepared.evidence.items() if k != 'runtime_sha256'}
            rows[json_file.stem] = {'status': 'prepared', 'policy': prepared.evidence['policy'],
                                    'schema_version': prepared.evidence['schema_version'],
                                    'wire_sha256': prepared.evidence['wire_sha256'],
                                    'prepared_input_sha256': prepared.evidence['prepared_input_sha256'],
                                    'source_sha256': prepared.evidence['source_sha256'],
                                    'evidence_without_runtime_sha256': mapping.sha(mapping.encode(evidence))}
        except Exception as exc:  # noqa: BLE001 - a hold is a result here, not a failure
            rows[json_file.stem] = {'status': 'held', 'error': type(exc).__name__ + ': ' + str(exc)[:200]}
        if index % 250 == 0:
            print(f'{index}/{len(files)} in {time.time() - started:.0f}s', flush=True)
    summary = {}
    for row in rows.values():
        key = row.get('policy', 'held')
        summary[key] = summary.get(key, 0) + 1
    Path(output).write_text(json.dumps({'runtime_sha256': mapping.runtime_binding(), 'count': len(rows),
                                        'summary': summary, 'rows': rows}, indent=1, sort_keys=True))
    print(json.dumps(summary, indent=1, sort_keys=True))


def compare(before, after):
    old = json.loads(Path(before).read_text())
    new = json.loads(Path(after).read_text())
    differences = []
    for sid in sorted(set(old['rows']) | set(new['rows']), key=lambda s: int(s[5:])):
        a, b = old['rows'].get(sid), new['rows'].get(sid)
        if a != b:
            differences.append({'source_id': sid, 'before': a, 'after': b})
    result = {'before_runtime': old['runtime_sha256'], 'after_runtime': new['runtime_sha256'],
              'compared': len(set(old['rows']) & set(new['rows'])), 'before_count': old['count'],
              'after_count': new['count'], 'differences': differences,
              'identical_wires': all(a == b for a, b in ((old['rows'].get(s), new['rows'].get(s))
                                                          for s in set(old['rows']) | set(new['rows'])))}
    print(json.dumps({k: v for k, v in result.items() if k != 'differences'}, indent=1))
    print('differences:', len(differences))
    for diff in differences[:20]:
        print(json.dumps(diff))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    rec = sub.add_parser('record')
    rec.add_argument('--data-root', required=True)
    rec.add_argument('--output', required=True)
    rec.add_argument('--ids')
    cmp_ = sub.add_parser('compare')
    cmp_.add_argument('before')
    cmp_.add_argument('after')
    cmp_.add_argument('--output')
    args = parser.parse_args()
    if args.command == 'record':
        ids = Path(args.ids).read_text().split() if args.ids else None
        record(args.data_root, args.output, ids)
    else:
        result = compare(args.before, args.after)
        if args.output:
            Path(args.output).write_text(json.dumps(result, indent=1, sort_keys=True))
        sys.exit(0 if not result['differences'] else 1)


if __name__ == '__main__':
    main()
