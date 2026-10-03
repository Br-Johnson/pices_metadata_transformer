"""Read-only exact-source census; reproduce with --baseline classification.json."""
import argparse,collections,hashlib,json
from pathlib import Path
import xml.etree.ElementTree as ET
parser=argparse.ArgumentParser();parser.add_argument('--baseline',required=True,type=Path);args=parser.parse_args()
root=Path(__file__).resolve().parents[3]; baseline=args.baseline
report=json.loads(baseline.read_bytes()); groups={k:collections.defaultdict(list) for k in ['creator','access','date','reasons']}; evidence=[]
for row in report['records']:
 if row['source_status']!='held':continue
 p=root/'FGDC'/(row['source_id']+'.xml');raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['source_sha256']; xml=ET.fromstring(raw)
 def texts(xpath):return [''.join(n.itertext()) for n in xml.findall(xpath)]
 entry={k:row[k] for k in ['source_id','source_sha256','hold_reasons']}; entry.update(origins=texts('./idinfo/citation/citeinfo/origin'),metadata_dates=texts('./metainfo/metd'),metadata_access=texts('./metainfo/metac'),title=texts('./idinfo/citation/citeinfo/title'),aliases=row.get('exact_copy_aliases',[]))
 evidence.append(entry)
 for kind,key in [('creator',entry['origins']),('access',entry['metadata_access']),('date',entry['metadata_dates']),('reasons',entry['hold_reasons'])]: groups[kind][json.dumps(key,sort_keys=True)].append(entry['source_id'])
summary={'baseline_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'baseline_commit':'c486d1fe138a1b515a3075840a113a3cdd5a8644','held_count':len(evidence),'groups':{kind:[{'value':json.loads(key),'count':len(ids),'source_ids':ids} for key,ids in sorted(values.items(),key=lambda x:(-len(x[1]),x[0]))] for kind,values in groups.items()},'records':evidence}
(root/'docs/readiness/2026-10-03/remaining_held_census.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
for kind in groups:
 print(kind)
 for g in summary['groups'][kind][:12]:print(g['count'],g['value'])
