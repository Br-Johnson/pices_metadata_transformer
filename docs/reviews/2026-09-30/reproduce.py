"""Historical bug demonstrations: run against an isolated checkout of the audited revision.
These describe pre-fix behavior, not assertions for current code. Never contacts Zenodo.
"""
import sys, json, socket, tempfile, xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, patch
ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
sys.path[:0] = [str(SOURCE), str(SOURCE/'scripts')]
socket.socket = Mock(side_effect=AssertionError('Network forbidden during review'))
from scripts.fgdc_to_zenodo import FGDCToZenodoTransformer
from scripts.batch_upload import BatchUploader
from scripts.path_config import OutputPaths
from scripts.publish_records import RecordPublisher
from scripts.pre_upload_duplicate_check import PreUploadDuplicateChecker
from scripts.zenodo_api import ZenodoAPIError
from scripts.dto import build_canonical_dto
from scripts.generate_jsonld_catalogue import build_jsonld
from scripts.bibliographic_linkage import apply_decisions
from scripts.dto import save_dto
from verify_uploads import ZenodoVerifier
from scripts.validate_zenodo import ZenodoValidator

log=Mock()
with patch('scripts.fgdc_to_zenodo.get_logger', return_value=log):
    t=FGDCToZenodoTransformer()
out={}
out['dates']={s:t._normalize_date(s,'fixture') for s in ['1994-12-20','2020-01-02','122003','1977 through 1978','December 20, 1994']}
out['creators']={s:t._extract_creators(ET.fromstring('<metadata><origin>'+s+'</origin></metadata>'),'fixture') for s in ['Smith, Jane','National Oceanic and Atmospheric Administration, Office of Research','Jane Smith<br/>John Doe']}
out['licenses']={s:t._detect_license(s,'fixture') for s in ['CC-BY-SA 4.0','Creative Commons Attribution-ShareAlike 4.0','CC BY-NC 4.0','open access']}
m={'access_right':'open','license':'cc-zero'}
t._extract_access_constraints(m,ET.fromstring('<metadata><useconst>All rights reserved. Permission required.</useconst></metadata>'),'fixture')
out['all_rights_reserved']=m
out['source_dates']=[]
out['source_creators']=[]
for p in sorted((SOURCE/'FGDC').glob('*.xml')):
    try: r=ET.fromstring(p.read_text(errors='ignore').lstrip('\ufeff\0'))
    except ET.ParseError: continue
    pub=r.find('.//pubdate')
    if pub is not None and pub.text and pub.text.strip()=='122003': out['source_dates'].append(p.name)
    origins=r.findall('.//origin')
    for o in origins:
        s=''.join(o.itertext()).strip()
        if ',' in s and not t._is_organization(s) and len(out['source_creators'])<12:
            out['source_creators'].append({'file':p.name,'origin':s,'creators':t._extract_creators(r,p.name)})
with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
    paths=OutputPaths(tmp)
    f=Path(paths.zenodo_json_dir)/'sample.json'
    metadata={'title':'Example','upload_type':'dataset','publication_date':'2020-01-01','access_right':'open','license':'cc-zero','creators':[{'name':'Smith, Jane'}],'description':'original description','notes':'original notes','related_identifiers':[]}
    f.write_text(json.dumps({'metadata':metadata}))
    Path(paths.uploads_registry_path).write_text(json.dumps({'sample':{'upload_status':'success','deposition_id':123,'zenodo_url':'https://sandbox.zenodo.org/deposit/123'}}))
    b=BatchUploader(tmp,sandbox=False,publish_on_upload=True)
    out['production_remaining_after_sandbox_success']=b.get_remaining_files()
    out['production_auto_publish']=b.publish_on_upload
    # Constructors for publisher/checker/verifier contact the API: bypass them.
    p=RecordPublisher.__new__(RecordPublisher); p.paths=paths; p.upload_log_path=paths.upload_log_path; p.logger=log; p.sandbox=False
    entry={'success':True,'deposition_id':123,'json_file':'output/data/zenodo_json/sample.json','zenodo_url':'https://sandbox.zenodo.org/deposit/123'}
    Path(paths.upload_log_path).write_text(json.dumps([entry]))
    out['production_publisher_accepts_sandbox_entry']=p.load_upload_log()
    entry['json_file']=str(f); Path(paths.upload_log_path).write_text(json.dumps([entry]))
    try: p.load_upload_log(); out['publisher_custom_output']='accepted'
    except FileNotFoundError as e: out['publisher_custom_output']=str(e)
    v=ZenodoVerifier.__new__(ZenodoVerifier); v.logger=log; v.client=Mock(base_url='https://example.invalid')
    v.client.get_deposition.return_value={'metadata':metadata,'files':[]}
    out['metadata_only_verification']=v._verify_single_record({'deposition_id':1,'json_file':str(f)})
    changed=dict(metadata,description='WRONG',notes='DELETED',related_identifiers=[{'identifier':'https://wrong.invalid','relation':'cites'}])
    out['verifier_misses_changed_fields']=v._compare_metadata(metadata,changed)
    c=PreUploadDuplicateChecker.__new__(PreUploadDuplicateChecker); c.client=Mock(); c.logger=log; c.community_identifier='pices'; c.allow_replacements=False
    c.client.get_records_by_query.side_effect=ZenodoAPIError('offline simulated failure')
    existing=c.load_existing_zenodo_records()
    out['duplicate_check_after_api_failure']=c.check_file_for_duplicates(str(f),existing)
    # Simulate metadata update failure, without creating or updating any real record.
    client=Mock(); client.create_deposition.return_value={'id':999}; client.update_deposition_metadata.side_effect=ZenodoAPIError('invalid metadata')
    result=b._upload_single_file(str(f),client)
    out['failed_upload_loses_created_id']={'result':result,'create_calls':client.create_deposition.call_count,'delete_calls':client.delete_deposition.call_count}
    dto=build_canonical_dto(source_path='FGDC/sample.xml',zenodo_metadata=dict(metadata,notes='Free text notes',creators=[{'name':'NOAA','type':'Organization'}]))
    out['jsonld']=build_jsonld(dto,'https://example.invalid/sample.jsonld')
    ancient=dict(metadata,publication_date='1220-03-01')
    f.write_text(json.dumps({'metadata':ancient}))
    val=ZenodoValidator(); out['ancient_date_validation']=val.validate_file(str(f))
    dto_path=Path(tmp)/'dto.json'; save_dto(str(dto_path),dto)
    decisions=[{'decision':'accept','source':'datacite','identifier':'https://doi.org/10.1234/example','confidence':0.99}]
    linked=apply_decisions(dto_path,dto,decisions,paths)
    issues=[]; warnings=[]
    val._validate_related_identifiers(linked.zenodo_metadata,issues,warnings)
    out['accepted_link_validation_errors']=issues
    first_notes=linked.zenodo_metadata['notes']
    linked=apply_decisions(dto_path,linked,decisions,paths)
    out['linkage_repeat_appends_notes']=linked.zenodo_metadata['notes']!=first_notes
    out['full_source_examples']={}
    for name in ['FGDC-3413.xml','FGDC-1990.xml','FGDC-1284.xml','FGDC-150.xml']:
        source=SOURCE/'FGDC'/name
        r=ET.fromstring(source.read_text(errors='ignore').lstrip('\ufeff\0'))
        meta=t._build_zenodo_metadata(r,name)
        out['full_source_examples'][name]={'publication_date':meta.get('publication_date'),'creators':meta.get('creators')}
    temporal_root=ET.fromstring('<metadata><title>Example temporal dataset</title><origin>Jane Smith</origin><pubdate>2020</pubdate><abstract>Example abstract</abstract><timeperd><timeinfo><rngdates><begdate>19940101</begdate><enddate>19941231</enddate></rngdates></timeinfo><current>ground condition</current></timeperd></metadata>')
    temporal_metadata=t._build_zenodo_metadata(temporal_root,'temporal_fixture')
    out['temporal_coverage_missing_from_final_notes']={'notes':temporal_metadata['notes'],'dates':temporal_metadata.get('dates')}
# Historical evidence is committed separately; print results only.
print(json.dumps({k:v for k,v in out.items() if k not in ['source_dates','source_creators','ancient_date_validation']},indent=2))
print('Source 122003 count:',len(out['source_dates']))
print('Ancient date valid:',out['ancient_date_validation']['is_valid'])
