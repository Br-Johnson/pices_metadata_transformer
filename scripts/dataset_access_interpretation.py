"""Pinned source-evidenced data acquisition; no authority or license grant.

Finite audited profiles only. Recheck paired raw constraints and per-source
abstract structure/text; separate restricted XML rehosting policy remains required.
"""
import copy
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

MANIFEST_SHA256 = '2d18139656b78f96404561afcee7d2ae77022655873958c3fa98619a2717bdee'
ACQUISITION_MANIFEST_SHA256 = '5c141ea3e0fae8e9b6673a2dc3f5aadba0d16c949767f80b5892ac589e6a0dbf'
EXTENDED_ACQUISITION_MANIFEST_SHA256 = '76a5ca8a8cdadbe0c1b0157d559068c98b16e18619a8561ff66a203a5008730a'
CNF_COPY_MEDIA_MANIFEST_SHA256 = '13e82e2375da3bf17cf352fff7a8cda43fa6d781a3e436ca7321c8428ac77abe'
RESOURCE_CONFIDENTIALITY_MANIFEST_SHA256 = '203c050735a9dc755712acde70c0447b91f2bd6131dde53dd8195a0f2923d9a2'
RESOURCE_RECONCILIATION_MANIFEST_SHA256 = '81c719c546146eb7ad39e04db115710747935df6cb142aaf5854127bf8ddcc6a'
NPAFC_REPORT_MANIFEST_SHA256 = 'a9dee2d1191eab69d85a20e3a3c856b9e56eec7283e024a50db91974cdd316a0'
RESIDUAL_SOURCE_MANIFEST_SHA256 = 'b0a0f90f8d61b1908ea1a291284a04d8047186e63b2dc9427181a39af6a292f7'
COMBINED_SOURCE_MANIFEST_SHA256 = '7e9f66fc19968c3f2784ff0ea5ab6d1169c1bd165035e5612c78332567636224'
RESIDUAL_RESOURCE_MANIFEST_SHA256 = '7dc625fe5fac625d1fe36f3fdf481c0ba63bd40acb0acc2c9b148079a6f9d550'
RESOURCE4_MANIFEST_SHA256 = '4719b46cfe46a2b950b3abc695fd8778ffc7bd3041e5bb0bae253c613c55ec2c'
SENSITIVE_RESOURCE11_MANIFEST_SHA256 = '83bdb0b1ab689e5fbf844467975ad9d279b6bba759cb3db3a18a11704715679c'
PAIRED_RESOURCE24_MANIFEST_SHA256 = '8aec41a5c27176c284bc0249c2619d1caa61ac1c245e986a3ba15201edfdee34'
REVIEW_BLOCKS = ('resource_reconciliation_review', 'npafc_report_notification_review',
                 'residual_source_review', 'residual_resource_review', 'residual_resource4_review',
                 'sensitive_resource11_review', 'paired_resource24_review')
REGISTRATION_WORDING = 'First time users must register to gain database access.'


def _manifest(reference):
    """Load only reviewed immutable evidence; a refreshed hash cannot expand it."""
    if (not isinstance(reference, dict) or set(reference) != {'manifest_path', 'manifest_sha256'}
            or not isinstance(reference.get('manifest_path'), str) or not reference['manifest_path'].strip()
            or reference.get('manifest_sha256') not in (MANIFEST_SHA256, ACQUISITION_MANIFEST_SHA256,
                                                      EXTENDED_ACQUISITION_MANIFEST_SHA256,
                                                      CNF_COPY_MEDIA_MANIFEST_SHA256,
                                                      RESOURCE_CONFIDENTIALITY_MANIFEST_SHA256,
                                                      RESOURCE_RECONCILIATION_MANIFEST_SHA256,
                                                      NPAFC_REPORT_MANIFEST_SHA256,
                                                      RESIDUAL_SOURCE_MANIFEST_SHA256,
                                                      COMBINED_SOURCE_MANIFEST_SHA256,
                                                      RESIDUAL_RESOURCE_MANIFEST_SHA256,
                                                      RESOURCE4_MANIFEST_SHA256,
                                                      SENSITIVE_RESOURCE11_MANIFEST_SHA256,
                                                      PAIRED_RESOURCE24_MANIFEST_SHA256)):
        raise ValueError('Dataset access interpretation requires the exact reviewed manifest reference')
    try:
        raw = Path(reference['manifest_path']).read_bytes()
    except OSError as exc:
        raise ValueError('Dataset access interpretation manifest is unavailable') from exc
    if hashlib.sha256(raw).hexdigest() != reference['manifest_sha256']:
        raise ValueError('Dataset access interpretation manifest differs from the reviewed profile')
    manifest = json.loads(raw)
    for key in REVIEW_BLOCKS:
        if key not in manifest:
            continue
        for evidence in manifest[key]['original_statement_references']:
            try:
                raw_evidence = (Path(__file__).resolve().parents[1] / evidence['manifest_path']).read_bytes()
            except OSError as exc:
                raise ValueError('Original resource-scope statement evidence is unavailable') from exc
            if hashlib.sha256(raw_evidence).hexdigest() != evidence['manifest_sha256']:
                raise ValueError('Resource reconciliation requires unchanged original statement evidence')
    return manifest


def dataset_access_member_ids(reference):
    """Select immutable added members once; each selected source is revalidated."""
    try:
        manifest = _manifest(reference)
    except ValueError:
        return frozenset()  # Unsupported access remains held without interpretation.
    return frozenset(manifest.get('acquisition_contexts', {}))


def _elements(root, xpath):
    result = []
    for node in root.findall(xpath):
        node = copy.deepcopy(node)
        node.tail = None
        result.append(ET.tostring(node, encoding='unicode'))
    return result


def validate_dataset_access_interpretation(reference, source_id, source_sha256, root, reviewed_at=None):
    """Return source-backed meaning only for the pinned exact source membership."""
    manifest = _manifest(reference)
    if not any(member['source_id'] == source_id and member['source_sha256'] == source_sha256
               for member in manifest['members']):
        raise ValueError('Source ID/hash is outside reviewed dataset access membership')
    acquisition = manifest.get('acquisition_contexts', {}).get(source_id)
    constraints = (acquisition['constraints'].items() if acquisition else
                   (('./metainfo/metac', REGISTRATION_WORDING),
                    ('./idinfo/accconst', REGISTRATION_WORDING),
                    ('./metainfo/metuc', 'None'), ('./idinfo/useconst', 'None')))
    for xpath, expected in constraints:
        nodes = root.findall(xpath)
        if len(nodes) != 1 or list(nodes[0]) or nodes[0].attrib or nodes[0].text != expected:
            raise ValueError('Dataset access interpretation requires exact plain paired constraints')
    if root.find('./metainfo/metsi') is not None or root.find('./metainfo/metextns') is not None:
        raise ValueError('Metadata security/extensions require separate adjudication')
    if acquisition:
        if any(_elements(root, xpath) != expected
               for xpath, expected in acquisition['context_elements'].items()):
            raise ValueError('Dataset access interpretation requires exact audited source context')
    else:
        abstracts = root.findall('./idinfo/descript/abstract')
        context = manifest['source_contexts'][source_id]
        if (len(abstracts) != 1
                or hashlib.sha256(ET.tostring(abstracts[0], encoding='utf-8')).hexdigest() != context['abstract_xml_sha256']
                or re.sub(r'\s+', ' ', ''.join(abstracts[0].itertext())).strip() != context['abstract_text']):
            raise ValueError('Dataset access interpretation requires exact audited abstract context')
    reviews = [manifest[key] for key in REVIEW_BLOCKS if key in manifest
               and {'source_id': source_id, 'source_sha256': source_sha256} in manifest[key]['members']]
    if len(reviews) > 1:
        raise ValueError('Source must have only one exact reviewer reconciliation')
    review = reviews[0] if reviews else None
    reconciled = review is not None
    if reconciled:
        try:
            stamp = datetime.fromisoformat(reviewed_at.replace('Z', '+00:00'))
            reviewed = datetime.fromisoformat(review['reviewed_at'])
            if stamp.tzinfo is None or stamp < reviewed or stamp > datetime.now(timezone.utc):
                raise ValueError
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError('Resource reconciliation requires current aware assessment time after review') from exc
    result = {'status': 'REVIEWER_RECONCILED' if reconciled else 'SOURCE_BACKED',
            'meaning': acquisition['meaning'] if acquisition else 'underlying_dataset_acquisition',
            'source_id': source_id, 'source_sha256': source_sha256,
            'grants_rehosting': False, 'grants_new_license': False, 'publication_approved': False}
    if reconciled:
        result.update(reconciliation_reviewed_at=review['reviewed_at'], new_user_attestation_event=False,
                      original_direct_question_membership_enlarged=False, underlying_data_rights_granted=False)
    return result


def validate_dataset_access_policy(policy, source_id, source_sha256, root, metadata):
    """Common all-QA-route gate: interpretation cannot replace rights authority."""
    from scripts.rehosting_authority import (
        validate_authority,
        validate_restricted_metadata,
    )
    if policy.get('source_access_interpretation') is not None:
        raise ValueError('Conflicting access interpretations require separate adjudication')
    authority = policy.get('rehosting_authority')
    if authority is None:
        raise ValueError('Dataset access interpretation requires separate rehosting authority')
    validate_authority(authority, source_id, source_sha256)
    validate_restricted_metadata(metadata)
    if (policy.get('license') not in ('', None) or policy.get('rights_scope') != 'original_fgdc_xml'
            or policy.get('rights_source_xpath') != './metainfo/metuc'
            or policy.get('date_semantics') != 'source_metadata_date'):
        raise ValueError('Dataset access interpretation requires restricted unlicensed XML policy')
    return validate_dataset_access_interpretation(policy.get('dataset_access_interpretation'),
                                                  source_id, source_sha256, root, policy.get('reviewed_at'))
