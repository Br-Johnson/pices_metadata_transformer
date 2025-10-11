#!/usr/bin/env python3
"""
Upload audit and verification script that provides comprehensive reporting
on upload status, success rates, and data integrity.
"""

import os
import json
import glob
from datetime import datetime
from typing import Dict, List, Any
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collections import defaultdict, Counter

class UploadAuditor:
    """Audits upload results and provides comprehensive reporting."""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self.audit_report_file = os.path.join(output_dir, f"upload_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    def analyze_upload_logs(self) -> Dict[str, Any]:
        """Analyze all upload logs and generate comprehensive audit report."""
        
        # Collect all upload data
        all_uploads = []
        all_errors = []
        batch_summaries = []
        
        # Process batch upload logs
        for log_file in glob.glob(os.path.join(self.output_dir, "batch_upload_log_*.json")):
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    batch_data = json.load(f)
                    batch_summaries.append(batch_data)
                    
                    # Extract individual uploads
                    for batch in batch_data.get('batches', []):
                        all_uploads.extend(batch.get('uploads', []))
                        all_errors.extend(batch.get('errors', []))
        
        # Process legacy upload logs
        legacy_log = os.path.join(self.output_dir, "upload_log.json")
        if os.path.exists(legacy_log):
            with open(legacy_log, 'r') as f:
                legacy_data = json.load(f)
                if isinstance(legacy_data, list):
                    all_uploads.extend(legacy_data)
        
        # Analyze the data
        analysis = self._analyze_uploads(all_uploads, all_errors, batch_summaries)
        
        # Save audit report
        with open(self.audit_report_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        return analysis
    
    def _analyze_uploads(self, uploads: List[Dict], errors: List[Dict], batches: List[Dict]) -> Dict[str, Any]:
        """Perform detailed analysis of upload data."""
        
        # Basic statistics
        total_files = len(uploads) + len(errors)
        successful_uploads = len([u for u in uploads if u.get('success', False)])
        failed_uploads = len(errors) + len([u for u in uploads if not u.get('success', False)])
        
        # Success rate analysis
        success_rate = (successful_uploads / total_files * 100) if total_files > 0 else 0
        
        # Error analysis
        error_types = Counter()
        error_files = []
        
        for error in errors:
            error_type = error.get('error', 'Unknown error')
            error_types[error_type] += 1
            error_files.append({
                'file': error.get('json_file', 'Unknown'),
                'error': error_type,
                'timestamp': error.get('timestamp', 'Unknown')
            })
        
        # Upload type analysis
        upload_types = Counter()
        communities = Counter()
        creators_count = []
        
        for upload in uploads:
            if upload.get('success', False):
                metadata = upload.get('metadata', {})
                upload_types[metadata.get('upload_type', 'unknown')] += 1
                
                # Count communities
                for community in metadata.get('communities', []):
                    communities[community.get('identifier', 'unknown')] += 1
                
                # Count creators
                creators_count.append(metadata.get('creators_count', 0))
        
        # Batch analysis
        batch_stats = []
        for batch in batches:
            batch_stats.append({
                'batch_number': batch.get('batch_number', 0),
                'size': batch.get('batch_size', 0),
                'successful': batch.get('successful_uploads', 0),
                'failed': batch.get('failed_uploads', 0),
                'duration': batch.get('duration_seconds', 0),
                'success_rate': (batch.get('successful_uploads', 0) / batch.get('batch_size', 1) * 100)
            })
        
        # Performance analysis
        avg_batch_duration = sum(b.get('duration_seconds', 0) for b in batch_stats) / len(batch_stats) if batch_stats else 0
        avg_creators = sum(creators_count) / len(creators_count) if creators_count else 0
        
        # Data integrity checks
        integrity_issues = self._check_data_integrity(uploads)
        
        return {
            'audit_timestamp': datetime.now().isoformat(),
            'summary': {
                'total_files_processed': total_files,
                'successful_uploads': successful_uploads,
                'failed_uploads': failed_uploads,
                'success_rate_percent': round(success_rate, 2),
                'total_batches': len(batches)
            },
            'error_analysis': {
                'error_types': dict(error_types.most_common()),
                'error_files': error_files[:50],  # Top 50 errors
                'total_error_types': len(error_types)
            },
            'content_analysis': {
                'upload_types': dict(upload_types),
                'communities': dict(communities),
                'avg_creators_per_record': round(avg_creators, 2),
                'creators_distribution': {
                    'min': min(creators_count) if creators_count else 0,
                    'max': max(creators_count) if creators_count else 0,
                    'total_records': len(creators_count)
                }
            },
            'performance_analysis': {
                'batch_statistics': batch_stats,
                'avg_batch_duration_seconds': round(avg_batch_duration, 2),
                'avg_files_per_batch': round(sum(b.get('batch_size', 0) for b in batch_stats) / len(batch_stats), 2) if batch_stats else 0
            },
            'data_integrity': integrity_issues,
            'recommendations': self._generate_recommendations(success_rate, error_types, batch_stats)
        }
    
    def _check_data_integrity(self, uploads: List[Dict]) -> Dict[str, Any]:
        """Check for data integrity issues in successful uploads."""
        issues = {
            'missing_titles': [],
            'missing_creators': [],
            'missing_descriptions': [],
            'invalid_dates': [],
            'missing_licenses': []
        }
        
        for upload in uploads:
            if not upload.get('success', False):
                continue
                
            metadata = upload.get('metadata', {})
            file_name = upload.get('json_file', 'Unknown')
            
            # Check required fields
            if not metadata.get('title'):
                issues['missing_titles'].append(file_name)
            
            if not metadata.get('creators') or len(metadata.get('creators', [])) == 0:
                issues['missing_creators'].append(file_name)
            
            if not metadata.get('description'):
                issues['missing_descriptions'].append(file_name)
            
            # Check date format
            pub_date = metadata.get('publication_date', '')
            if pub_date and not self._is_valid_date(pub_date):
                issues['invalid_dates'].append(file_name)
            
            # Check license for open access
            if metadata.get('access_right') == 'open' and not metadata.get('license'):
                issues['missing_licenses'].append(file_name)
        
        return {
            'missing_titles_count': len(issues['missing_titles']),
            'missing_creators_count': len(issues['missing_creators']),
            'missing_descriptions_count': len(issues['missing_descriptions']),
            'invalid_dates_count': len(issues['invalid_dates']),
            'missing_licenses_count': len(issues['missing_licenses']),
            'sample_issues': {k: v[:10] for k, v in issues.items() if v}  # Top 10 of each type
        }
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Check if date string is in valid ISO format."""
        try:
            datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return True
        except:
            return False
    
    def _generate_recommendations(self, success_rate: float, error_types: Counter, batch_stats: List[Dict]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        if success_rate < 95:
            recommendations.append(f"Success rate is {success_rate:.1f}%. Consider investigating common error types.")
        
        if error_types:
            top_error = error_types.most_common(1)[0]
            recommendations.append(f"Most common error: '{top_error[0]}' ({top_error[1]} occurrences). Consider addressing this issue.")
        
        if batch_stats:
            avg_success_rate = sum(b.get('success_rate', 0) for b in batch_stats) / len(batch_stats)
            if avg_success_rate < 90:
                recommendations.append("Batch success rates are low. Consider reducing batch size or improving error handling.")
        
        if not recommendations:
            recommendations.append("Upload process appears to be working well. No immediate issues identified.")
        
        return recommendations
    
    def generate_human_report(self, analysis: Dict[str, Any]) -> str:
        """Generate a human-readable audit report."""
        report = []
        report.append("=" * 80)
        report.append("ZENODO UPLOAD AUDIT REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {analysis['audit_timestamp']}")
        report.append("")
        
        # Summary
        summary = analysis['summary']
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Total files processed: {summary['total_files_processed']:,}")
        report.append(f"Successful uploads: {summary['successful_uploads']:,}")
        report.append(f"Failed uploads: {summary['failed_uploads']:,}")
        report.append(f"Success rate: {summary['success_rate_percent']:.1f}%")
        report.append(f"Total batches: {summary['total_batches']}")
        report.append("")
        
        # Error analysis
        error_analysis = analysis['error_analysis']
        report.append("ERROR ANALYSIS")
        report.append("-" * 40)
        report.append(f"Total error types: {error_analysis['total_error_types']}")
        report.append("Top error types:")
        for error_type, count in list(error_analysis['error_types'].items())[:5]:
            report.append(f"  - {error_type}: {count} occurrences")
        report.append("")
        
        # Content analysis
        content = analysis['content_analysis']
        report.append("CONTENT ANALYSIS")
        report.append("-" * 40)
        report.append(f"Upload types: {content['upload_types']}")
        report.append(f"Communities: {content['communities']}")
        report.append(f"Average creators per record: {content['avg_creators_per_record']}")
        report.append("")
        
        # Data integrity
        integrity = analysis['data_integrity']
        report.append("DATA INTEGRITY")
        report.append("-" * 40)
        report.append(f"Missing titles: {integrity['missing_titles_count']}")
        report.append(f"Missing creators: {integrity['missing_creators_count']}")
        report.append(f"Missing descriptions: {integrity['missing_descriptions_count']}")
        report.append(f"Invalid dates: {integrity['invalid_dates_count']}")
        report.append(f"Missing licenses: {integrity['missing_licenses_count']}")
        report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS")
        report.append("-" * 40)
        for i, rec in enumerate(analysis['recommendations'], 1):
            report.append(f"{i}. {rec}")
        report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)

def main():
    """Main function to run audit."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Audit Zenodo upload results')
    parser.add_argument('--output-dir', default='output',
                       help='Output directory containing upload logs')
    parser.add_argument('--report-file', 
                       help='File to save human-readable report')
    
    args = parser.parse_args()
    
    auditor = UploadAuditor(args.output_dir)
    
    print("Analyzing upload logs...")
    analysis = auditor.analyze_upload_logs()
    
    print("Generating human-readable report...")
    report = auditor.generate_human_report(analysis)
    
    # Print report
    print(report)
    
    # Save report if requested
    if args.report_file:
        with open(args.report_file, 'w') as f:
            f.write(report)
        print(f"\nReport saved to: {args.report_file}")
    
    print(f"\nDetailed audit data saved to: {auditor.audit_report_file}")

if __name__ == "__main__":
    main()
