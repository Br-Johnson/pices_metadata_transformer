"""Offline stratified source audit; no credentials, source edits or remote requests.

Run from repository root: python docs/readiness/2026-10-02/audit_sources.py
Uses strict raw XML parsing and transformation builder; recovery paths and live
service compatibility are outside this audit. Output is written beside this file.
"""
import collections,hashlib,json,re,socket,sys,xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path.cwd()))
from scripts.fgdc_to_zenodo import FGDCToZenodoTransformer
from scripts.validate_zenodo import ZenodoValidator
from scripts.fgdc_utils import build_metadata_notes
from scripts.content_classification import classify_content
socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('Offline audit'))
ids=['FGDC-2057','FGDC-2043','FGDC-2725','FGDC-1238','FGDC-2731','FGDC-120','FGDC-122','FGDC-1773','FGDC-1752','FGDC-1007','FGDC-767','FGDC-832','FGDC-854','FGDC-1220','FGDC-1334','FGDC-2920','FGDC-3148','FGDC-633','FGDC-3373','FGDC-21']
rows=[]
with patch('scripts.fgdc_to_zenodo.get_logger',return_value=Mock()),patch('scripts.validate_zenodo.get_logger',return_value=Mock()):
 t=FGDCToZenodoTransformer();v=ZenodoValidator()
 for sid in ids:
  p=Path('FGDC')/(sid+'.xml');raw=p.read_bytes();row={'source_id':sid,'source_sha256':hashlib.sha256(raw).hexdigest(),'file_bytes':len(raw),'remote_write_eligible':False,'human_semantic_holds':['Deposited-object/DOI/date/creator/rights policy not yet signed off.','No reviewed external inventory or final source-to-existing-record disposition.']}
  try:root=ET.fromstring(raw)
  except ET.ParseError as exc:row.update(technical_status='raw_xml_parse_hold',parse_error=str(exc));rows.append(row);continue
  def f(path):
   e=root.find(path);return ''.join(e.itertext()).strip() if e is not None else ''
  source={name:f(path) for name,path in {'title':'./idinfo/citation/citeinfo/title','origin':'./idinfo/citation/citeinfo/origin','publication_date':'./idinfo/citation/citeinfo/pubdate','abstract':'./idinfo/descript/abstract','use_constraints':'./idinfo/useconst','metadata_date':'./metainfo/metd'}.items()}
  row['source_fields']=source
  row['independent_source_observations']={'has_primary_title':bool(source['title']),'has_substantive_primary_abstract':len(source['abstract'])>50,'explicit_license_in_source':bool(re.search(r'Creative Commons|CC-BY|CC0|MIT License|Apache|GNU General Public License',source['use_constraints'],re.I)),'raw_calendar_shape':bool(re.fullmatch(r'\d{4}(?:\d{2}){0,2}|\d{4}-\d{2}-\d{2}',source['publication_date'])),'procite':re.findall(r'Procite\s*#\s*(\d+)',source['abstract'],re.I)}
  metadata=t._build_zenodo_metadata(root,str(p))
  if not metadata:row['technical_status']='transformation_hold'
  else:
   metadata['notes']=build_metadata_notes(metadata.get('notes',''),raw.decode().strip());issues,warnings=v.validate_metadata(metadata)
   row.update(technical_status='offline_contract_pass' if not issues else 'validation_hold',validation_issues=issues,transformed_fields={key:metadata.get(key) for key in ('publication_date','creators','license','access_right','keywords')})
   row['source_comparison']={'title_equal':metadata['title']==source['title'],'description_includes_raw_abstract':source['abstract'] in metadata['description'],'description_preserves_abstract_after_whitespace_normalization':re.sub(r'\s+', ' ',source['abstract']).strip() in re.sub(r'\s+', ' ', metadata['description']).strip(),'raw_xml_in_notes':raw.decode().strip() in metadata['notes']}
  if not source['publication_date']:
   row['human_semantic_holds'].append('Primary publication date absent; metadata-date fallback is technically accepted but requires explicit deposited-object/date review.')
  if source['publication_date']=='122003':row['human_semantic_holds'].append('Raw122003 ambiguous; cited publication year and metadata_date are different concepts.')
  if re.search(r'Unknown|Present|thru|Planned|Unpublished',source['publication_date'],re.I):row['human_semantic_holds'].append('Primary date is unknown/status/coverage, not an established individual publication date.')
  if source['publication_date'] in ('September 2001','October 2001'):row['human_semantic_holds'].append('Month precision requires representation rule; do not invent a known day.')
  if '-' in source['publication_date'] and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',source['publication_date']):row['human_semantic_holds'].append('Range must be retained; parser acceptance alone does not establish publication date.')
  row['human_semantic_holds'].append('Source use constraints do not establish a recognized license grant; restricted access does not resolve rights.')
  if sid in ('FGDC-2920','FGDC-3148'):row['human_semantic_holds'].append('Same title/ProCite438 pair requires source/work/subset comparison, not automatic title dedup.')
  declaration={'inventory_complete':True,'reviewer':'Offline preparer, not final publication approver','reviewed_at':'2026-10-02','rationale':'Raw source structurally contains descriptive FGDC fields; inspected as a proposed original-XML artifact, not underlying observations.','files':[{'name':sid+'.xml','role':'descriptive_metadata','evidence':'Raw parsed source contains metadata/idinfo/citation/descript, citation and metadata field descriptions.'}]}
  row['proposed_file_role_classification']=classify_content(declaration)
  rows.append(row)
for row in rows:
 row['audit_verdict'] = 'held' if row['technical_status'] != 'offline_contract_pass' else 'technical_pass_human_review_required'
 if row.get('source_comparison'):
  row['field_fidelity_verdict'] = 'correct_after_whitespace_normalization' if all(row['source_comparison'].get(k,False) for k in ('title_equal','description_preserves_abstract_after_whitespace_normalization','raw_xml_in_notes')) else 'mismatch_requires_review'
counts=collections.Counter(row['technical_status'] for row in rows)
pair={}
for sid in ('FGDC-2920','FGDC-3148'):
 root=ET.fromstring(Path('FGDC/'+sid+'.xml').read_bytes());pair[sid]=root
r1,r2=pair.values();comparison={'sources':list(pair),'raw_bytes_equal':Path('FGDC/FGDC-2920.xml').read_bytes()==Path('FGDC/FGDC-3148.xml').read_bytes(),'serialized_xml_equal':ET.tostring(r1)==ET.tostring(r2),'scope':'These two raw XML files are byte-identical. Preserve both source aliases; this does not authorize deleting either source or prove cross-repository work equivalence.'}
report={'scope':'20 intentionally stratified cases; not random sample, population estimate, human signoff or live API validation. Raw source comparisons independent of validation output.','source_revision':'e85caaef8db418c6b4328122ec9fe83eea86aa75','counts':dict(counts),'remote_write_eligible_count':0,'records':rows,'duplicate_pair_check':comparison,'external_duplicate_evidence_status':'unchecked_unavailable: earlier AquaDocs endpoint findings do not prove duplicate absence; no new external requests.'}
Path(__file__).with_name('representative_spotcheck.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('records',)},indent=2))
print('TECHNICAL_PASSES',[row['source_id'] for row in rows if row['technical_status']=='offline_contract_pass'])

# Exact-copy inventory uses bytes only; no repair or semantic merging.
buckets = collections.defaultdict(list)
for source_path in sorted(Path('FGDC').glob('*.xml')):
 buckets[hashlib.sha256(source_path.read_bytes()).hexdigest()].append(source_path.stem)
groups = [{'source_sha256':digest,'source_ids':aliases} for digest,aliases in buckets.items() if len(aliases)>1]
copy_report = {'scope':'Exact raw byte equivalence only; not title/semantic/work/rights equivalence.','source_files':sum(map(len,buckets.values())),'unique_raw_byte_contents':len(buckets),'exact_copy_groups':len(groups),'files_in_exact_copy_groups':sum(len(g['source_ids']) for g in groups),'redundant_raw_copies':sum(len(g['source_ids'])-1 for g in groups),'groups':groups}
Path(__file__).with_name('exact_source_copy_groups.json').write_text(json.dumps(copy_report,indent=2)+'\n')
