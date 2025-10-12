"""
Upload script for transformed Zenodo JSON records to Zenodo sandbox.
Handles bulk upload with comprehensive error handling and logging.
"""

import os
import json
import argparse
import glob
from datetime import datetime
from typing import Dict, List, Any, Optional
from tqdm import tqdm
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.zenodo_api import create_zenodo_client, ZenodoAPIError
from scripts.logger import initialize_logger, get_logger


class ZenodoUploader:
    """Handles uploading transformed records to Zenodo."""
    
    def __init__(self, sandbox: bool = True, output_dir: str = "output"):
        self.sandbox = sandbox
        self.output_dir = output_dir
        self.logger = get_logger()
        
        # Initialize Zenodo client (will be set by batch uploader)
        self.client = None
        
        # File paths - use transformed directory for the main files
        self.zenodo_json_dir = os.path.join(self.output_dir, 'zenodo_json')
        self.original_fgdc_dir = os.path.join(self.output_dir, 'original_fgdc')
        self.upload_log_path = os.path.join(output_dir, 'upload_log.json')
        self.upload_errors_path = os.path.join(output_dir, 'upload_errors.json')
        
        # Upload tracking
        self.upload_log = []
        self.upload_errors = []
        
        # Statistics
        self.stats = {
            'total_files': 0,
            'successful_uploads': 0,
            'failed_uploads': 0,
            'skipped_files': 0
        }
    
    def discover_json_files(self) -> List[str]:
        """Discover all JSON files in the output directory."""
        if not os.path.isdir(self.zenodo_json_dir):
            raise FileNotFoundError(
                f"Zenodo JSON directory not found: {self.zenodo_json_dir}. "
                "Run the transformation pipeline or update --output to the correct path."
            )

        json_pattern = os.path.join(self.zenodo_json_dir, '*.json')
        json_files = glob.glob(json_pattern)
        
        if not json_files:
            raise FileNotFoundError(f"No JSON files found in {self.zenodo_json_dir}")
        
        # Sort files for consistent processing order
        json_files.sort()
        
        self.logger.log_info(f"Discovered {len(json_files)} JSON files in {self.zenodo_json_dir}")
        return json_files
    
    def upload_files(self, json_files: List[str], limit: int = None) -> Dict[str, Any]:
        """Upload JSON files to Zenodo."""
        if limit:
            json_files = json_files[:limit]
            self.logger.log_info(f"Uploading limited to {limit} files")
        
        self.stats['total_files'] = len(json_files)
        
        # Process files with progress bar
        for json_file in tqdm(json_files, desc="Uploading to Zenodo"):
            try:
                result = self._upload_single_file(json_file)
                
                if result['success']:
                    self.stats['successful_uploads'] += 1
                    self.upload_log.append(result)
                else:
                    self.stats['failed_uploads'] += 1
                    self.upload_errors.append(result)
                
            except Exception as e:
                self.stats['failed_uploads'] += 1
                error_result = {
                    'json_file': json_file,
                    'success': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                self.upload_errors.append(error_result)
                
                self.logger.log_error(
                    json_file, "upload_process", "upload_error",
                    str(e), "Successful upload",
                    "Review error details and fix upload logic"
                )
        
        # Save upload logs
        self._save_upload_logs()
        
        # Generate summary
        summary = self._generate_upload_summary()
        
        self.logger.log_info(f"Upload completed:")
        self.logger.log_info(f"  Total files: {summary['total_files']}")
        self.logger.log_info(f"  Successful: {summary['successful_uploads']}")
        self.logger.log_info(f"  Failed: {summary['failed_uploads']}")
        self.logger.log_info(f"  Success rate: {summary['success_rate']:.1f}%")
        
        return summary
    
    def _upload_single_file(self, json_file: str) -> Dict[str, Any]:
        """Upload a single JSON file to Zenodo."""
        try:
            if not os.path.isdir(self.original_fgdc_dir):
                raise FileNotFoundError(
                    f"Original FGDC directory not found: {self.original_fgdc_dir}. "
                    "Ensure transformed FGDC copies exist under the selected output directory."
                )

            # Load JSON data
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'metadata' not in data:
                raise ValueError("JSON file missing 'metadata' key")
            
            metadata = data['metadata']
            original_fgdc_file = data.get('original_fgdc_file', '')
            
            # Get base filename
            base_name = os.path.splitext(os.path.basename(json_file))[0]
            
            # Find corresponding FGDC XML file
            fgdc_file = os.path.join(self.original_fgdc_dir, f"{base_name}.xml")
            if not os.path.exists(fgdc_file):
                fgdc_file = None
            
            # Create deposition
            deposition = self.client.create_deposition()
            deposition_id = deposition['id']
            
            # Upload original FGDC XML file if available
            if fgdc_file:
                try:
                    self.client.upload_file(deposition_id, fgdc_file, f"{base_name}.xml")
                except Exception as e:
                    self.logger.log_warning(
                        json_file, "file_upload", "fgdc_upload_failed",
                        str(e), "Successful FGDC file upload",
                        f"Failed to upload FGDC file: {str(e)}",
                        "Check file permissions and size limits"
                    )
            
            # Update metadata
            updated_deposition = self.client.update_deposition_metadata(deposition_id, metadata)
            
            # Get DOI if reserved
            doi = None
            if 'metadata' in updated_deposition and 'prereserve_doi' in updated_deposition['metadata']:
                doi = updated_deposition['metadata']['prereserve_doi'].get('doi')
            
            result = {
                'json_file': json_file,
                'fgdc_file': fgdc_file,
                'deposition_id': deposition_id,
                'doi': doi,
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'title': metadata.get('title', ''),
                    'upload_type': metadata.get('upload_type', ''),
                    'creators_count': len(metadata.get('creators', [])),
                    'keywords_count': len(metadata.get('keywords', [])),
                    'communities': metadata.get('communities', [])
                }
            }
            
            self.logger.log_info(
                f"Successfully uploaded {base_name} - Deposition ID: {deposition_id}, DOI: {doi}"
            )
            
            return result
            
        except ZenodoAPIError as e:
            return {
                'json_file': json_file,
                'success': False,
                'error': f"Zenodo API error: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'json_file': json_file,
                'success': False,
                'error': f"Upload error: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _save_upload_logs(self):
        """Save upload logs to JSON files."""
        # Save successful uploads
        with open(self.upload_log_path, 'w', encoding='utf-8') as f:
            json.dump(self.upload_log, f, indent=2, ensure_ascii=False)
        
        # Save errors
        with open(self.upload_errors_path, 'w', encoding='utf-8') as f:
            json.dump(self.upload_errors, f, indent=2, ensure_ascii=False)
        
        self.logger.log_info(f"Upload logs saved to {self.upload_log_path}")
        self.logger.log_info(f"Upload errors saved to {self.upload_errors_path}")
    
    def _generate_upload_summary(self) -> Dict[str, Any]:
        """Generate upload summary statistics."""
        total_files = self.stats['total_files']
        successful = self.stats['successful_uploads']
        failed = self.stats['failed_uploads']
        
        # Analyze errors
        error_types = {}
        for error in self.upload_errors:
            error_msg = error.get('error', 'Unknown error')
            error_type = error_msg.split(':')[0] if ':' in error_msg else error_msg
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # Analyze successful uploads
        upload_types = {}
        communities = {}
        for upload in self.upload_log:
            metadata = upload.get('metadata', {})
            upload_type = metadata.get('upload_type', 'unknown')
            upload_types[upload_type] = upload_types.get(upload_type, 0) + 1
            
            for community in metadata.get('communities', []):
                comm_id = community.get('identifier', 'unknown')
                communities[comm_id] = communities.get(comm_id, 0) + 1
        
        return {
            'total_files': total_files,
            'successful_uploads': successful,
            'failed_uploads': failed,
            'success_rate': (successful / total_files * 100) if total_files > 0 else 0,
            'sandbox': self.sandbox,
            'error_types': error_types,
            'upload_types': upload_types,
            'communities': communities,
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_upload_report(self, summary: Dict[str, Any]) -> str:
        """Generate a comprehensive upload report."""
        report_lines = []
        report_lines.append("=== Zenodo Upload Report ===")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Environment: {'Sandbox' if self.sandbox else 'Production'}")
        report_lines.append("")
        
        # Upload summary
        report_lines.append("UPLOAD SUMMARY:")
        report_lines.append(f"  Total files: {summary['total_files']}")
        report_lines.append(f"  Successful uploads: {summary['successful_uploads']}")
        report_lines.append(f"  Failed uploads: {summary['failed_uploads']}")
        report_lines.append(f"  Success rate: {summary['success_rate']:.1f}%")
        report_lines.append("")
        
        # Upload types
        if summary['upload_types']:
            report_lines.append("UPLOAD TYPES:")
            for upload_type, count in summary['upload_types'].items():
                report_lines.append(f"  {upload_type}: {count}")
            report_lines.append("")
        
        # Communities
        if summary['communities']:
            report_lines.append("COMMUNITIES:")
            for community, count in summary['communities'].items():
                report_lines.append(f"  {community}: {count}")
            report_lines.append("")
        
        # Error analysis
        if summary['error_types']:
            report_lines.append("ERROR ANALYSIS:")
            for error_type, count in sorted(summary['error_types'].items(), 
                                          key=lambda x: x[1], reverse=True):
                report_lines.append(f"  {error_type}: {count}")
            report_lines.append("")
        
        # File locations
        report_lines.append("OUTPUT FILES:")
        report_lines.append(f"  Upload log: {self.upload_log_path}")
        report_lines.append(f"  Upload errors: {self.upload_errors_path}")
        report_lines.append("")
        
        # Next steps
        report_lines.append("NEXT STEPS:")
        if summary['failed_uploads'] > 0:
            report_lines.append("  1. Review failed uploads in upload_errors.json")
            report_lines.append("  2. Fix common issues and retry failed uploads")
            report_lines.append("  3. Consider manual upload for problematic records")
        else:
            report_lines.append("  1. Review uploaded records in Zenodo sandbox")
            report_lines.append("  2. Verify metadata accuracy")
            report_lines.append("  3. Test publishing a few records")
            report_lines.append("  4. Proceed with production upload when ready")
        
        report_text = "\n".join(report_lines)
        
        # Save report
        report_path = os.path.join(self.output_dir, 'upload_report.txt')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        self.logger.log_info(f"Upload report saved to {report_path}")
        return report_text


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Upload transformed Zenodo JSON files to Zenodo"
    )
    parser.add_argument(
        '--sandbox',
        action='store_true',
        default=True,
        help='Upload to Zenodo sandbox (default: True)'
    )
    parser.add_argument(
        '--production',
        action='store_true',
        help='Upload to production Zenodo (overrides --sandbox)'
    )
    parser.add_argument(
        '--output', '-o',
        default='output',
        help='Output directory containing transformed files (default: output)'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        help='Limit number of files to upload (for testing)'
    )
    parser.add_argument(
        '--log-dir',
        default='logs',
        help='Directory for log files (default: logs)'
    )
    
    args = parser.parse_args()
    
    # Determine environment
    sandbox = not args.production
    
    # Initialize logger
    initialize_logger(args.log_dir)
    logger = get_logger()
    
    try:
        with create_zenodo_client(sandbox) as client:
            # Create uploader
            uploader = ZenodoUploader(sandbox, args.output)
            uploader.client = client

            # Discover JSON files
            json_files = uploader.discover_json_files()

            # Upload files
            logger.log_info(f"Starting upload to {'sandbox' if sandbox else 'production'} Zenodo...")
            summary = uploader.upload_files(json_files, args.limit)

        # Generate report
        upload_report = uploader.generate_upload_report(summary)
        
        # Print summary to console
        print("\n" + upload_report)
        
        # Exit with appropriate code
        if summary['failed_uploads'] > 0:
            logger.log_info("Upload completed with some failures")
            exit(1)
        else:
            logger.log_info("Upload completed successfully")
            exit(0)
            
    except Exception as e:
        logger.log_error(
            "upload_process", "main_process", "fatal_error",
            str(e), "Successful upload process",
            "Review error details and fix issues"
        )
        print(f"Fatal error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
