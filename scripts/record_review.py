#!/usr/bin/env python3
"""
Record Review Helper - Comprehensive analysis tool for individual FGDC to Zenodo transformations.
Provides detailed before/after comparison, log analysis, and issue identification.
"""

import os
import json
import xml.etree.ElementTree as ET
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.zenodo_api import create_zenodo_client, ZenodoAPIError
from scripts.logger import initialize_logger, get_logger


class RecordReviewer:
    """Comprehensive record review and analysis tool."""
    
    def __init__(self, output_dir: str = "output", logs_dir: str = "logs"):
        self.output_dir = output_dir
        self.logs_dir = logs_dir
        self.logger = get_logger()
        
        # File paths
        self.fgdc_dir = "FGDC"
        self.original_fgdc_dir = os.path.join(output_dir, "original_fgdc")
        self.zenodo_json_dir = os.path.join(output_dir, "zenodo_json")
        self.upload_log_path = os.path.join(output_dir, "upload_log.json")
        self.registry_path = os.path.join(output_dir, "uploads_registry.json")
        self.warnings_path = os.path.join(logs_dir, "warnings.json")
        self.errors_path = os.path.join(logs_dir, "errors.json")
        self.validation_report_path = os.path.join(output_dir, "validation_report.json")
    
    def review_record(self, record_id: str, check_zenodo: bool = False, 
                     sandbox: bool = True) -> Dict[str, Any]:
        """Comprehensive review of a single record."""
        
        # Normalize record ID (remove .xml/.json extensions if present)
        base_id = record_id.replace('.xml', '').replace('.json', '')
        
        print(f"\n{'='*80}")
        print(f"RECORD REVIEW: {base_id}")
        print(f"{'='*80}")
        
        review = {
            'record_id': base_id,
            'timestamp': datetime.now().isoformat(),
            'files_found': {},
            'transformation_analysis': {},
            'upload_analysis': {},
            'issue_analysis': {},
            'zenodo_analysis': {},
            'summary': {}
        }
        
        # 1. Check file existence
        review['files_found'] = self._check_file_existence(base_id)
        
        if not review['files_found']['original_fgdc']:
            print(f"❌ ERROR: Original FGDC file not found: {base_id}.xml")
            return review
        
        # 2. Analyze original FGDC
        if review['files_found']['original_fgdc']:
            review['transformation_analysis']['original'] = self._analyze_original_fgdc(base_id)
        
        # 3. Analyze transformed JSON
        if review['files_found']['zenodo_json']:
            review['transformation_analysis']['transformed'] = self._analyze_transformed_json(base_id)
        
        # 4. Analyze upload status
        review['upload_analysis'] = self._analyze_upload_status(base_id)
        
        # 5. Analyze issues and warnings
        review['issue_analysis'] = self._analyze_issues(base_id)
        
        # 6. Check Zenodo if requested
        if check_zenodo and review['upload_analysis'].get('uploaded'):
            review['zenodo_analysis'] = self._analyze_zenodo_record(
                base_id, review['upload_analysis'], sandbox
            )
        
        # 7. Generate summary
        review['summary'] = self._generate_summary(review)
        
        # 8. Print comprehensive report
        self._print_review_report(review)
        
        return review
    
    def _check_file_existence(self, record_id: str) -> Dict[str, bool]:
        """Check which files exist for this record."""
        files = {
            'original_fgdc': os.path.exists(os.path.join(self.fgdc_dir, f"{record_id}.xml")),
            'original_fgdc_copy': os.path.exists(os.path.join(self.original_fgdc_dir, f"{record_id}.xml")),
            'zenodo_json': os.path.exists(os.path.join(self.zenodo_json_dir, f"{record_id}.json")),
            'validation_report': os.path.exists(self.validation_report_path)
        }
        return files
    
    def _analyze_original_fgdc(self, record_id: str) -> Dict[str, Any]:
        """Analyze the original FGDC XML file."""
        fgdc_path = os.path.join(self.fgdc_dir, f"{record_id}.xml")
        
        try:
            tree = ET.parse(fgdc_path)
            root = tree.getroot()
            
            analysis = {
                'file_size_bytes': os.path.getsize(fgdc_path),
                'file_size_kb': round(os.path.getsize(fgdc_path) / 1024, 2),
                'xml_structure': {},
                'key_fields': {},
                'data_quality': {}
            }
            
            # Extract key fields
            key_fields = {
                'title': './/title',
                'origin': './/origin', 
                'pubdate': './/pubdate',
                'abstract': './/abstract',
                'purpose': './/purpose',
                'themekey': './/themekey',
                'placekey': './/placekey',
                'westbc': './/westbc',
                'eastbc': './/eastbc',
                'northbc': './/northbc',
                'southbc': './/southbc',
                'accconst': './/accconst',
                'useconst': './/useconst'
            }
            
            for field_name, xpath in key_fields.items():
                elements = root.findall(xpath)
                if elements:
                    values = [elem.text.strip() for elem in elements if elem.text]
                    analysis['key_fields'][field_name] = {
                        'count': len(values),
                        'values': values[:3] if len(values) > 3 else values,  # Show first 3
                        'total_length': sum(len(v) for v in values)
                    }
                else:
                    analysis['key_fields'][field_name] = {'count': 0, 'values': [], 'total_length': 0}
            
            # XML structure analysis
            analysis['xml_structure'] = {
                'root_element': root.tag,
                'total_elements': len(list(root.iter())),
                'max_depth': self._get_xml_depth(root)
            }
            
            # Data quality indicators
            analysis['data_quality'] = {
                'has_title': analysis['key_fields']['title']['count'] > 0,
                'has_creators': analysis['key_fields']['origin']['count'] > 0,
                'has_abstract': analysis['key_fields']['abstract']['count'] > 0,
                'has_spatial_bounds': all([
                    analysis['key_fields']['westbc']['count'] > 0,
                    analysis['key_fields']['eastbc']['count'] > 0,
                    analysis['key_fields']['northbc']['count'] > 0,
                    analysis['key_fields']['southbc']['count'] > 0
                ]),
                'has_keywords': (analysis['key_fields']['themekey']['count'] + 
                               analysis['key_fields']['placekey']['count']) > 0
            }
            
            return analysis
            
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_transformed_json(self, record_id: str) -> Dict[str, Any]:
        """Analyze the transformed Zenodo JSON file."""
        json_path = os.path.join(self.zenodo_json_dir, f"{record_id}.json")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = data.get('metadata', {})
            char_analysis = data.get('character_analysis', {})
            
            analysis = {
                'file_size_bytes': os.path.getsize(json_path),
                'file_size_kb': round(os.path.getsize(json_path) / 1024, 2),
                'metadata_fields': {},
                'field_counts': {},
                'character_analysis': char_analysis,
                'data_quality': {}
            }
            
            # Analyze metadata fields
            key_zenodo_fields = [
                'title', 'upload_type', 'publication_date', 'creators', 'description',
                'access_right', 'license', 'keywords', 'notes', 'related_identifiers',
                'contributors', 'references', 'communities'
            ]
            
            for field in key_zenodo_fields:
                value = metadata.get(field)
                if value is not None:
                    if isinstance(value, list):
                        analysis['metadata_fields'][field] = {
                            'type': 'list',
                            'count': len(value),
                            'sample_values': value[:2] if len(value) > 2 else value
                        }
                    elif isinstance(value, str):
                        analysis['metadata_fields'][field] = {
                            'type': 'string',
                            'length': len(value),
                            'preview': value[:100] + '...' if len(value) > 100 else value
                        }
                    else:
                        analysis['metadata_fields'][field] = {
                            'type': type(value).__name__,
                            'value': str(value)[:100]
                        }
                else:
                    analysis['metadata_fields'][field] = {'type': 'missing', 'value': None}
            
            # Field coverage analysis
            analysis['field_counts'] = {
                'total_fields': len([f for f in key_zenodo_fields if metadata.get(f) is not None]),
                'required_fields_present': len([f for f in ['title', 'creators', 'publication_date', 'description'] 
                                              if metadata.get(f) is not None]),
                'optional_fields_present': len([f for f in key_zenodo_fields 
                                              if f not in ['title', 'creators', 'publication_date', 'description'] 
                                              and metadata.get(f) is not None])
            }
            
            # Data quality indicators
            analysis['data_quality'] = {
                'has_title': bool(metadata.get('title')),
                'has_creators': bool(metadata.get('creators')),
                'has_description': bool(metadata.get('description')),
                'has_publication_date': bool(metadata.get('publication_date')),
                'has_keywords': bool(metadata.get('keywords')),
                'has_notes': bool(metadata.get('notes')),
                'title_length_ok': len(metadata.get('title', '')) <= 250,
                'description_length_ok': len(metadata.get('description', '')) >= 10
            }
            
            return analysis
            
        except Exception as e:
            return {'error': str(e)}
    
    def _analyze_upload_status(self, record_id: str) -> Dict[str, Any]:
        """Analyze upload status from logs and registry."""
        analysis = {
            'uploaded': False,
            'upload_log_entry': None,
            'registry_entry': None,
            'deposition_id': None,
            'doi': None,
            'upload_timestamp': None,
            'upload_status': 'not_found'
        }
        
        # Check upload log
        if os.path.exists(self.upload_log_path):
            try:
                with open(self.upload_log_path, 'r') as f:
                    upload_log = json.load(f)
                
                for entry in upload_log:
                    if entry.get('json_file', '').endswith(f"{record_id}.json"):
                        analysis['upload_log_entry'] = entry
                        analysis['uploaded'] = entry.get('success', False)
                        analysis['deposition_id'] = entry.get('deposition_id')
                        analysis['doi'] = entry.get('doi')
                        analysis['upload_timestamp'] = entry.get('timestamp')
                        analysis['upload_status'] = 'success' if entry.get('success') else 'failed'
                        break
            except Exception as e:
                analysis['upload_log_error'] = str(e)
        
        # Check registry
        if os.path.exists(self.registry_path):
            try:
                with open(self.registry_path, 'r') as f:
                    registry = json.load(f)
                
                if record_id in registry:
                    analysis['registry_entry'] = registry[record_id]
                    analysis['uploaded'] = registry[record_id].get('upload_status') == 'success'
                    analysis['deposition_id'] = registry[record_id].get('deposition_id')
                    analysis['doi'] = registry[record_id].get('doi')
                    analysis['upload_timestamp'] = registry[record_id].get('uploaded_at')
                    analysis['upload_status'] = registry[record_id].get('upload_status', 'unknown')
            except Exception as e:
                analysis['registry_error'] = str(e)
        
        return analysis
    
    def _analyze_issues(self, record_id: str) -> Dict[str, Any]:
        """Analyze warnings and errors for this record."""
        analysis = {
            'warnings': [],
            'errors': [],
            'validation_issues': [],
            'total_issues': 0
        }
        
        # Check warnings
        if os.path.exists(self.warnings_path):
            try:
                with open(self.warnings_path, 'r') as f:
                    warnings = json.load(f)
                
                for warning in warnings:
                    if warning.get('file', '').endswith(f"{record_id}.xml"):
                        analysis['warnings'].append(warning)
            except Exception as e:
                analysis['warnings_error'] = str(e)
        
        # Check errors
        if os.path.exists(self.errors_path):
            try:
                with open(self.errors_path, 'r') as f:
                    errors = json.load(f)
                
                for error in errors:
                    if error.get('file', '').endswith(f"{record_id}.xml"):
                        analysis['errors'].append(error)
            except Exception as e:
                analysis['errors_error'] = str(e)
        
        # Check validation report
        if os.path.exists(self.validation_report_path):
            try:
                with open(self.validation_report_path, 'r') as f:
                    validation = json.load(f)
                
                for result in validation.get('results', []):
                    if result.get('file') == f"{record_id}.json":
                        analysis['validation_issues'] = result.get('issues', [])
                        break
            except Exception as e:
                analysis['validation_error'] = str(e)
        
        analysis['total_issues'] = len(analysis['warnings']) + len(analysis['errors']) + len(analysis['validation_issues'])
        
        return analysis
    
    def _analyze_zenodo_record(self, record_id: str, upload_analysis: Dict[str, Any], 
                              sandbox: bool) -> Dict[str, Any]:
        """Analyze the record in Zenodo."""
        analysis = {
            'found_in_zenodo': False,
            'zenodo_data': None,
            'metadata_match': False,
            'api_error': None
        }
        
        if not upload_analysis.get('deposition_id'):
            analysis['api_error'] = "No deposition ID available"
            return analysis
        
        try:
            client = create_zenodo_client(sandbox)
            deposition = client.get_deposition(upload_analysis['deposition_id'])
            
            analysis['found_in_zenodo'] = True
            analysis['zenodo_data'] = {
                'id': deposition.get('id'),
                'title': deposition.get('metadata', {}).get('title'),
                'doi': deposition.get('metadata', {}).get('prereserve_doi', {}).get('doi'),
                'created': deposition.get('created'),
                'modified': deposition.get('modified'),
                'state': deposition.get('state'),
                'files_count': len(deposition.get('files', []))
            }
            
            # Compare with local data
            json_path = os.path.join(self.zenodo_json_dir, f"{record_id}.json")
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    local_data = json.load(f)
                
                local_title = local_data.get('metadata', {}).get('title')
                zenodo_title = deposition.get('metadata', {}).get('title')
                analysis['metadata_match'] = local_title == zenodo_title
            
        except ZenodoAPIError as e:
            analysis['api_error'] = f"Zenodo API error: {str(e)}"
        except Exception as e:
            analysis['api_error'] = f"Error: {str(e)}"
        
        return analysis
    
    def _generate_summary(self, review: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of the review."""
        summary = {
            'overall_status': 'unknown',
            'key_issues': [],
            'data_quality_score': 0,
            'transformation_success': False,
            'upload_success': False
        }
        
        # Check transformation success
        if (review['files_found'].get('original_fgdc') and 
            review['files_found'].get('zenodo_json') and
            not review['transformation_analysis'].get('original', {}).get('error') and
            not review['transformation_analysis'].get('transformed', {}).get('error')):
            summary['transformation_success'] = True
        
        # Check upload success
        summary['upload_success'] = review['upload_analysis'].get('uploaded', False)
        
        # Calculate data quality score
        quality_indicators = []
        
        # Original data quality
        orig_quality = review['transformation_analysis'].get('original', {}).get('data_quality', {})
        quality_indicators.extend([
            orig_quality.get('has_title', False),
            orig_quality.get('has_creators', False),
            orig_quality.get('has_abstract', False),
            orig_quality.get('has_spatial_bounds', False),
            orig_quality.get('has_keywords', False)
        ])
        
        # Transformed data quality
        trans_quality = review['transformation_analysis'].get('transformed', {}).get('data_quality', {})
        quality_indicators.extend([
            trans_quality.get('has_title', False),
            trans_quality.get('has_creators', False),
            trans_quality.get('has_description', False),
            trans_quality.get('has_publication_date', False),
            trans_quality.get('has_keywords', False)
        ])
        
        summary['data_quality_score'] = round((sum(quality_indicators) / len(quality_indicators)) * 100, 1)
        
        # Identify key issues
        if review['issue_analysis'].get('total_issues', 0) > 0:
            summary['key_issues'].append(f"{review['issue_analysis']['total_issues']} warnings/errors found")
        
        if not summary['transformation_success']:
            summary['key_issues'].append("Transformation failed or incomplete")
        
        if not summary['upload_success']:
            summary['key_issues'].append("Upload failed or not attempted")
        
        if summary['data_quality_score'] < 70:
            summary['key_issues'].append("Low data quality score")
        
        # Overall status
        if summary['transformation_success'] and summary['upload_success'] and summary['data_quality_score'] >= 80:
            summary['overall_status'] = 'excellent'
        elif summary['transformation_success'] and summary['upload_success']:
            summary['overall_status'] = 'good'
        elif summary['transformation_success']:
            summary['overall_status'] = 'transformed_but_not_uploaded'
        else:
            summary['overall_status'] = 'failed'
        
        return summary
    
    def _print_review_report(self, review: Dict[str, Any]):
        """Print a comprehensive review report."""
        record_id = review['record_id']
        summary = review['summary']
        
        # Header
        status_emoji = {
            'excellent': '🟢',
            'good': '🟡', 
            'transformed_but_not_uploaded': '🟠',
            'failed': '🔴'
        }.get(summary['overall_status'], '⚪')
        
        print(f"\n{status_emoji} OVERALL STATUS: {summary['overall_status'].upper()}")
        print(f"📊 Data Quality Score: {summary['data_quality_score']}%")
        print(f"🔄 Transformation: {'✅' if summary['transformation_success'] else '❌'}")
        print(f"⬆️  Upload: {'✅' if summary['upload_success'] else '❌'}")
        
        if summary['key_issues']:
            print(f"\n⚠️  KEY ISSUES:")
            for issue in summary['key_issues']:
                print(f"   • {issue}")
        
        # File status
        print(f"\n📁 FILES:")
        files = review['files_found']
        print(f"   Original FGDC: {'✅' if files.get('original_fgdc') else '❌'}")
        print(f"   Transformed JSON: {'✅' if files.get('zenodo_json') else '❌'}")
        
        # Original FGDC analysis
        if review['transformation_analysis'].get('original'):
            orig = review['transformation_analysis']['original']
            print(f"\n📄 ORIGINAL FGDC ANALYSIS:")
            print(f"   File size: {orig.get('file_size_kb', 0)} KB")
            print(f"   XML elements: {orig.get('xml_structure', {}).get('total_elements', 0)}")
            print(f"   Max depth: {orig.get('xml_structure', {}).get('max_depth', 0)}")
            
            key_fields = orig.get('key_fields', {})
            print(f"   Title: {'✅' if key_fields.get('title', {}).get('count', 0) > 0 else '❌'}")
            print(f"   Creators: {'✅' if key_fields.get('origin', {}).get('count', 0) > 0 else '❌'}")
            print(f"   Abstract: {'✅' if key_fields.get('abstract', {}).get('count', 0) > 0 else '❌'}")
            print(f"   Keywords: {'✅' if (key_fields.get('themekey', {}).get('count', 0) + key_fields.get('placekey', {}).get('count', 0)) > 0 else '❌'}")
            print(f"   Spatial bounds: {'✅' if orig.get('data_quality', {}).get('has_spatial_bounds') else '❌'}")
        
        # Transformed JSON analysis
        if review['transformation_analysis'].get('transformed'):
            trans = review['transformation_analysis']['transformed']
            print(f"\n🔄 TRANSFORMED JSON ANALYSIS:")
            print(f"   File size: {trans.get('file_size_kb', 0)} KB")
            
            field_counts = trans.get('field_counts', {})
            print(f"   Fields present: {field_counts.get('total_fields', 0)}/13")
            print(f"   Required fields: {field_counts.get('required_fields_present', 0)}/4")
            print(f"   Optional fields: {field_counts.get('optional_fields_present', 0)}/9")
            
            char_analysis = trans.get('character_analysis', {})
            if char_analysis:
                print(f"   Data preservation: {char_analysis.get('data_preservation_ratio', 0):.1%}")
        
        # Upload analysis
        upload = review['upload_analysis']
        print(f"\n⬆️  UPLOAD ANALYSIS:")
        print(f"   Status: {upload.get('upload_status', 'unknown')}")
        if upload.get('deposition_id'):
            print(f"   Deposition ID: {upload['deposition_id']}")
        if upload.get('doi'):
            print(f"   DOI: {upload['doi']}")
        if upload.get('upload_timestamp'):
            print(f"   Uploaded: {upload['upload_timestamp']}")
        
        # Issues
        issues = review['issue_analysis']
        if issues.get('total_issues', 0) > 0:
            print(f"\n⚠️  ISSUES FOUND ({issues['total_issues']} total):")
            
            if issues.get('warnings'):
                print(f"   Warnings ({len(issues['warnings'])}):")
                for warning in issues['warnings'][:3]:  # Show first 3
                    print(f"     • {warning.get('issue_type', 'unknown')}: {warning.get('context', '')}")
            
            if issues.get('errors'):
                print(f"   Errors ({len(issues['errors'])}):")
                for error in issues['errors'][:3]:  # Show first 3
                    print(f"     • {error.get('issue_type', 'unknown')}: {error.get('context', '')}")
        
        # Zenodo analysis
        if review.get('zenodo_analysis', {}).get('found_in_zenodo'):
            zenodo = review['zenodo_analysis']
            print(f"\n🌐 ZENODO VERIFICATION:")
            print(f"   Found in Zenodo: ✅")
            print(f"   State: {zenodo['zenodo_data'].get('state', 'unknown')}")
            print(f"   Files uploaded: {zenodo['zenodo_data'].get('files_count', 0)}")
            print(f"   Metadata match: {'✅' if zenodo.get('metadata_match') else '❌'}")
        
        print(f"\n{'='*80}")
    
    def _get_xml_depth(self, element, depth=0):
        """Calculate maximum XML depth."""
        if not element:
            return depth
        return max([self._get_xml_depth(child, depth + 1) for child in element] + [depth])


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Comprehensive record review and analysis tool"
    )
    parser.add_argument(
        'record_id',
        help='Record ID to review (e.g., FGDC-1, FGDC-1234)'
    )
    parser.add_argument(
        '--check-zenodo',
        action='store_true',
        help='Check record in Zenodo (requires API access)'
    )
    parser.add_argument(
        '--sandbox',
        action='store_true',
        default=True,
        help='Use Zenodo sandbox (default: True)'
    )
    parser.add_argument(
        '--production',
        action='store_true',
        help='Use Zenodo production (overrides --sandbox)'
    )
    parser.add_argument(
        '--output-dir',
        default='output',
        help='Output directory (default: output)'
    )
    parser.add_argument(
        '--logs-dir',
        default='logs',
        help='Logs directory (default: logs)'
    )
    
    args = parser.parse_args()
    
    # Determine environment
    sandbox = not args.production
    
    # Initialize logger
    initialize_logger(args.logs_dir)
    
    try:
        # Create reviewer
        reviewer = RecordReviewer(args.output_dir, args.logs_dir)
        
        # Review record
        result = reviewer.review_record(
            args.record_id, 
            check_zenodo=args.check_zenodo,
            sandbox=sandbox
        )
        
        # Exit with appropriate code
        if result['summary']['overall_status'] in ['excellent', 'good']:
            exit(0)
        else:
            exit(1)
            
    except Exception as e:
        print(f"Fatal error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
