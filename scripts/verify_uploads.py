"""
Verification script for uploaded Zenodo records.
Validates that uploaded records accurately reflect the transformed metadata.
"""

import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
from zenodo_api import create_zenodo_client, ZenodoAPIError
from logger import initialize_logger, get_logger
from path_config import OutputPaths, default_log_dir


class ZenodoVerifier:
    """Verifies uploaded records in Zenodo."""
    
    def __init__(self, sandbox: bool = True, output_dir: str = "output"):
        self.sandbox = sandbox
        self.output_dir = output_dir
        self.paths = OutputPaths(output_dir)
        self.logger = get_logger()
        
        # Initialize Zenodo client
        self.client = create_zenodo_client(sandbox)
        
        # File paths
        self.upload_log_path = self.paths.upload_log_path
        self.verification_report_path = self.paths.verification_report_path
        self.verification_summary_path = self.paths.verification_summary_path
        
        # Verification results
        self.verification_results = []
        self.verification_stats = {
            'total_records': 0,
            'verified_successfully': 0,
            'verification_failed': 0,
            'records_not_found': 0,
            'metadata_mismatches': 0
        }
    
    def load_upload_log(self) -> List[Dict[str, Any]]:
        """Load the upload log to get list of uploaded records."""
        if not os.path.exists(self.upload_log_path):
            self.logger.log_info(f"No upload log found at {self.upload_log_path}; skipping verification.")
            return []
        
        with open(self.upload_log_path, 'r', encoding='utf-8') as f:
            upload_log = json.load(f)
        
        # Filter only successful uploads
        successful_uploads = [upload for upload in upload_log if upload.get('success', False)]
        
        self.logger.log_info(f"Loaded {len(successful_uploads)} successful uploads from log")
        return successful_uploads
    
    def verify_uploads(self, upload_log: List[Dict[str, Any]], limit: int = None) -> Dict[str, Any]:
        """Verify uploaded records in Zenodo."""
        if limit:
            upload_log = upload_log[:limit]
            self.logger.log_info(f"Verifying limited to {limit} records")
        
        self.verification_stats['total_records'] = len(upload_log)
        
        for upload in upload_log:
            try:
                result = self._verify_single_record(upload)
                self.verification_results.append(result)
                
                if result['verification_successful']:
                    self.verification_stats['verified_successfully'] += 1
                else:
                    self.verification_stats['verification_failed'] += 1
                    
                    if result['record_not_found']:
                        self.verification_stats['records_not_found'] += 1
                    if result['metadata_mismatches']:
                        self.verification_stats['metadata_mismatches'] += 1
                
            except Exception as e:
                self.verification_stats['verification_failed'] += 1
                error_result = {
                    'deposition_id': upload.get('deposition_id'),
                    'json_file': upload.get('json_file'),
                    'verification_successful': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                self.verification_results.append(error_result)
                
                self.logger.log_error(
                    upload.get('json_file', 'unknown'), "verification_process", "verification_error",
                    str(e), "Successful verification",
                    "Review error details and fix verification logic"
                )
        
        # Save verification results
        self._save_verification_results()
        
        # Generate summary
        summary = self._generate_verification_summary()
        
        self.logger.log_info(f"Verification completed:")
        summary_stats = summary.get('summary', {})
        self.logger.log_info(f"  Total records: {summary_stats.get('total_records', 0)}")
        self.logger.log_info(f"  Verified successfully: {summary_stats.get('verified_successfully', 0)}")
        self.logger.log_info(f"  Verification failed: {summary_stats.get('verification_failed', 0)}")
        self.logger.log_info(f"  Success rate: {summary_stats.get('success_rate', 0):.1f}%")
        
        return summary
    
    def _verify_single_record(self, upload: Dict[str, Any]) -> Dict[str, Any]:
        """Verify a single uploaded record."""
        deposition_id = upload.get('deposition_id')
        json_file = upload.get('json_file')
        
        try:
            # Get deposition from Zenodo
            deposition = self.client.get_deposition(deposition_id)
            
            if not deposition:
                return {
                    'deposition_id': deposition_id,
                    'json_file': json_file,
                    'verification_successful': False,
                    'record_not_found': True,
                    'error': 'Deposition not found in Zenodo',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Load original metadata
            with open(json_file, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
            original_metadata = original_data['metadata']
            
            # Get Zenodo metadata
            zenodo_metadata = deposition.get('metadata', {})
            
            # Compare metadata
            mismatches = self._compare_metadata(original_metadata, zenodo_metadata)
            
            # Check if files were uploaded
            files_uploaded = len(deposition.get('files', [])) > 0
            
            verification_successful = len(mismatches) == 0 and files_uploaded
            
            result = {
                'deposition_id': deposition_id,
                'json_file': json_file,
                'doi': upload.get('doi'),
                'verification_successful': verification_successful,
                'record_not_found': False,
                'metadata_mismatches': len(mismatches) > 0,
                'mismatches': mismatches,
                'files_uploaded': files_uploaded,
                'zenodo_url': f"{self.client.base_url}/deposit/{deposition_id}",
                'timestamp': datetime.now().isoformat()
            }
            
            if verification_successful:
                self.logger.log_info(f"Successfully verified deposition {deposition_id}")
            else:
                self.logger.log_warning(
                    json_file, "verification", "verification_failed",
                    f"Mismatches: {len(mismatches)}, Files uploaded: {files_uploaded}",
                    "Perfect match with files uploaded",
                    f"Verification issues for deposition {deposition_id}",
                    "Review mismatches and fix if necessary"
                )
            
            return result
            
        except ZenodoAPIError as e:
            return {
                'deposition_id': deposition_id,
                'json_file': json_file,
                'verification_successful': False,
                'record_not_found': True,
                'error': f"Zenodo API error: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'deposition_id': deposition_id,
                'json_file': json_file,
                'verification_successful': False,
                'error': f"Verification error: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _compare_metadata(self, original: Dict[str, Any], zenodo: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Compare original metadata with Zenodo metadata."""
        mismatches = []
        
        # Key fields to compare
        key_fields = [
            'title', 'upload_type', 'publication_date', 'access_right', 'license'
        ]
        
        for field in key_fields:
            original_value = original.get(field)
            zenodo_value = zenodo.get(field)
            
            if original_value != zenodo_value:
                mismatches.append({
                    'field': field,
                    'original': original_value,
                    'zenodo': zenodo_value,
                    'type': 'value_mismatch'
                })
        
        # Compare creators
        original_creators = original.get('creators', [])
        zenodo_creators = zenodo.get('creators', [])
        
        if len(original_creators) != len(zenodo_creators):
            mismatches.append({
                'field': 'creators',
                'original': f"{len(original_creators)} creators",
                'zenodo': f"{len(zenodo_creators)} creators",
                'type': 'count_mismatch'
            })
        else:
            # Compare creator names
            for i, (orig_creator, zen_creator) in enumerate(zip(original_creators, zenodo_creators)):
                if orig_creator.get('name') != zen_creator.get('name'):
                    mismatches.append({
                        'field': f'creators[{i}].name',
                        'original': orig_creator.get('name'),
                        'zenodo': zen_creator.get('name'),
                        'type': 'value_mismatch'
                    })
        
        # Compare keywords
        original_keywords = set(original.get('keywords', []))
        zenodo_keywords = set(zenodo.get('keywords', []))
        
        if original_keywords != zenodo_keywords:
            mismatches.append({
                'field': 'keywords',
                'original': list(original_keywords),
                'zenodo': list(zenodo_keywords),
                'type': 'set_mismatch'
            })
        
        # Compare communities
        original_communities = set(c.get('identifier') for c in original.get('communities', []))
        zenodo_communities = set(c.get('identifier') for c in zenodo.get('communities', []))
        
        if original_communities != zenodo_communities:
            mismatches.append({
                'field': 'communities',
                'original': list(original_communities),
                'zenodo': list(zenodo_communities),
                'type': 'set_mismatch'
            })
        
        return mismatches
    
    def _save_verification_results(self):
        """Save verification results to JSON file."""
        with open(self.verification_report_path, 'w', encoding='utf-8') as f:
            json.dump(self.verification_results, f, indent=2, ensure_ascii=False)
        
        self.logger.log_info(f"Verification results saved to {self.verification_report_path}")
    
    def _generate_verification_summary(self) -> Dict[str, Any]:
        """Generate verification summary statistics."""
        total_records = self.verification_stats['total_records']
        successful = self.verification_stats['verified_successfully']
        failed = self.verification_stats['verification_failed']
        
        # Analyze mismatch types
        mismatch_types = {}
        for result in self.verification_results:
            if result.get('mismatches'):
                for mismatch in result['mismatches']:
                    mismatch_type = mismatch.get('type', 'unknown')
                    mismatch_types[mismatch_type] = mismatch_types.get(mismatch_type, 0) + 1
        
        # Analyze field mismatches
        field_mismatches = {}
        for result in self.verification_results:
            if result.get('mismatches'):
                for mismatch in result['mismatches']:
                    field = mismatch.get('field', 'unknown')
                    field_mismatches[field] = field_mismatches.get(field, 0) + 1
        
        return {
            'summary': {
                'total_records': total_records,
                'verified_successfully': successful,
                'verification_failed': failed,
                'records_not_found': self.verification_stats['records_not_found'],
                'metadata_mismatches': self.verification_stats['metadata_mismatches'],
                'success_rate': (successful / total_records * 100) if total_records > 0 else 0,
                'sandbox': self.sandbox
            },
            'mismatch_types': mismatch_types,
            'field_mismatches': field_mismatches,
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_verification_report(self, summary: Dict[str, Any]) -> str:
        """Generate a comprehensive verification report."""
        report_lines = []
        report_lines.append("=== Zenodo Verification Report ===")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Environment: {'Sandbox' if self.sandbox else 'Production'}")
        report_lines.append("")
        
        # Verification summary
        report_lines.append("VERIFICATION SUMMARY:")
        report_lines.append(f"  Total records: {summary['summary']['total_records']}")
        report_lines.append(f"  Verified successfully: {summary['summary']['verified_successfully']}")
        report_lines.append(f"  Verification failed: {summary['summary']['verification_failed']}")
        report_lines.append(f"  Records not found: {summary['summary']['records_not_found']}")
        report_lines.append(f"  Metadata mismatches: {summary['summary']['metadata_mismatches']}")
        report_lines.append(f"  Success rate: {summary['summary']['success_rate']:.1f}%")
        report_lines.append("")
        
        # Mismatch analysis
        if summary['mismatch_types']:
            report_lines.append("MISMATCH TYPES:")
            for mismatch_type, count in summary['mismatch_types'].items():
                report_lines.append(f"  {mismatch_type}: {count}")
            report_lines.append("")
        
        # Field mismatches
        if summary['field_mismatches']:
            report_lines.append("FIELD MISMATCHES:")
            for field, count in sorted(summary['field_mismatches'].items(), 
                                     key=lambda x: x[1], reverse=True):
                report_lines.append(f"  {field}: {count}")
            report_lines.append("")
        
        # File locations
        report_lines.append("OUTPUT FILES:")
        report_lines.append(f"  Verification report: {self.verification_report_path}")
        report_lines.append("")
        
        # Next steps
        report_lines.append("NEXT STEPS:")
        if summary['summary']['verification_failed'] > 0:
            report_lines.append("  1. Review verification failures in verification_report.json")
            report_lines.append("  2. Check for common mismatch patterns")
            report_lines.append("  3. Fix transformation logic if needed")
            report_lines.append("  4. Re-upload problematic records")
        else:
            report_lines.append("  1. All records verified successfully!")
            report_lines.append("  2. Review a few records manually in Zenodo")
            report_lines.append("  3. Test publishing a few records")
            report_lines.append("  4. Proceed with production upload when ready")
        
        report_text = "\n".join(report_lines)
        
        # Save report
        report_path = self.verification_summary_path
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        self.logger.log_info(f"Verification report saved to {report_path}")
        return report_text


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Verify uploaded records in Zenodo"
    )
    parser.add_argument(
        '--sandbox',
        action='store_true',
        default=True,
        help='Verify records in Zenodo sandbox (default: True)'
    )
    parser.add_argument(
        '--production',
        action='store_true',
        help='Verify records in production Zenodo (overrides --sandbox)'
    )
    parser.add_argument(
        '--output', '-o',
        default='output',
        help='Output directory containing upload logs (default: output)'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        help='Limit number of records to verify (for testing)'
    )
    default_logs = default_log_dir("verification")
    parser.add_argument(
        '--log-dir',
        default=default_logs,
        help=f'Directory for log files (default: {default_logs})'
    )
    
    args = parser.parse_args()
    
    # Determine environment
    sandbox = not args.production
    
    # Initialize logger
    initialize_logger(args.log_dir)
    logger = get_logger()
    
    try:
        # Create verifier
        verifier = ZenodoVerifier(sandbox, args.output)
        
        # Load upload log
        upload_log = verifier.load_upload_log()
        
        # Verify uploads
        logger.log_info(f"Starting verification in {'sandbox' if sandbox else 'production'} Zenodo...")
        summary = verifier.verify_uploads(upload_log, args.limit)
        
        # Generate report
        verification_report = verifier.generate_verification_report(summary)
        
        # Print summary to console
        print("\n" + verification_report)
        
        # Exit with appropriate code
        if summary['summary']['verification_failed'] > 0:
            logger.log_info("Verification completed with some failures")
            exit(1)
        else:
            logger.log_info("Verification completed successfully")
            exit(0)
            
    except Exception as e:
        logger.log_error(
            "verification_process", "main_process", "fatal_error",
            str(e), "Successful verification process",
            "Review error details and fix issues"
        )
        print(f"Fatal error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
