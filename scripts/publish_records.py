"""
Script to publish uploaded Zenodo records so they appear in the PICES Community.
Records uploaded to Zenodo are in 'unsubmitted' state and need to be published
to be visible in communities and search results.
"""

import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
from tqdm import tqdm
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.zenodo_api import create_zenodo_client, ZenodoAPIError
from scripts.logger import initialize_logger, get_logger
from scripts.path_config import OutputPaths, default_log_dir


class RecordPublisher:
    """Handles publishing uploaded records to Zenodo."""
    
    def __init__(self, sandbox: bool = True, output_dir: str = "output"):
        self.sandbox = sandbox
        self.output_dir = output_dir
        self.paths = OutputPaths(output_dir)
        self.logger = get_logger()
        
        # Initialize Zenodo client
        self.client = create_zenodo_client(sandbox)
        
        # File paths
        self.upload_log_path = self.paths.upload_log_path
        self.publish_log_path = self.paths.publish_log_path
        self.publish_errors_path = self.paths.publish_errors_path
        
        # Publishing tracking
        self.publish_log = []
        self.publish_errors = []
        
        # Statistics
        self.stats = {
            'total_records': 0,
            'successful_publishes': 0,
            'failed_publishes': 0,
            'already_published': 0,
            'not_found': 0
        }
    
    def load_upload_log(self) -> List[Dict[str, Any]]:
        """Load the upload log to get list of uploaded records."""
        # First try to find the most recent batch upload log
        import glob
        batch_logs = glob.glob(os.path.join(self.paths.upload_reports_dir, 'batch_upload_log_*.json'))
        
        if batch_logs:
            # Sort by modification time and get the most recent
            latest_batch_log = max(batch_logs, key=os.path.getmtime)
            self.logger.log_info(f"Using batch upload log: {latest_batch_log}")
            
            with open(latest_batch_log, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
            
            # Extract successful uploads from all batches
            successful_uploads = []
            for batch in batch_data.get('batches', []):
                for upload in batch.get('uploads', []):
                    if upload.get('success', False):
                        successful_uploads.append(upload)
            
            self.logger.log_info(f"Loaded {len(successful_uploads)} successful uploads from batch log")
            return successful_uploads
        
        # Fallback to regular upload log
        if not os.path.exists(self.upload_log_path):
            raise FileNotFoundError(f"No upload logs found in {self.output_dir}")
        
        with open(self.upload_log_path, 'r', encoding='utf-8') as f:
            upload_log = json.load(f)
        
        # Filter only successful uploads
        successful_uploads = [upload for upload in upload_log if upload.get('success', False)]
        
        self.logger.log_info(f"Loaded {len(successful_uploads)} successful uploads from regular log")
        return successful_uploads
    
    def publish_records(self, upload_log: List[Dict[str, Any]], limit: int = None) -> Dict[str, Any]:
        """Publish uploaded records to make them visible in communities."""
        
        if limit:
            upload_log = upload_log[:limit]
        
        self.stats['total_records'] = len(upload_log)
        
        self.logger.log_info(f"Starting to publish {len(upload_log)} records...")
        
        # Process records with progress bar
        for upload in tqdm(upload_log, desc="Publishing records"):
            try:
                result = self._publish_single_record(upload)
                self.publish_log.append(result)
                
                if result['publish_successful']:
                    self.stats['successful_publishes'] += 1
                elif result.get('already_published'):
                    self.stats['already_published'] += 1
                elif result.get('not_found'):
                    self.stats['not_found'] += 1
                else:
                    self.stats['failed_publishes'] += 1
                    self.publish_errors.append(result)
                
            except Exception as e:
                error_result = {
                    'deposition_id': upload.get('deposition_id'),
                    'json_file': upload.get('json_file'),
                    'publish_successful': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                self.publish_errors.append(error_result)
                self.publish_log.append(error_result)
                self.stats['failed_publishes'] += 1
                
                self.logger.log_error(
                    upload.get('json_file', 'unknown'), "publish", "publish_failed",
                    str(e), "Successful record publishing",
                    "Review error details and retry if needed"
                )
        
        # Save results
        self._save_publish_results()
        
        # Generate summary
        summary = self._generate_publish_summary()
        
        self.logger.log_info(f"Publishing completed:")
        self.logger.log_info(f"  Total records: {summary['total_records']}")
        self.logger.log_info(f"  Successfully published: {summary['successful_publishes']}")
        self.logger.log_info(f"  Already published: {summary['already_published']}")
        self.logger.log_info(f"  Failed to publish: {summary['failed_publishes']}")
        self.logger.log_info(f"  Not found: {summary['not_found']}")
        self.logger.log_info(f"  Success rate: {summary['success_rate']:.1f}%")
        
        return summary
    
    def _publish_single_record(self, upload: Dict[str, Any]) -> Dict[str, Any]:
        """Publish a single uploaded record."""
        deposition_id = upload.get('deposition_id')
        json_file = upload.get('json_file')
        
        try:
            # First, check the current state of the deposition
            deposition = self.client.get_deposition(deposition_id)
            
            if not deposition:
                return {
                    'deposition_id': deposition_id,
                    'json_file': json_file,
                    'publish_successful': False,
                    'not_found': True,
                    'error': 'Deposition not found in Zenodo',
                    'timestamp': datetime.now().isoformat()
                }
            
            # Check if already published
            if deposition.get('state') == 'done':
                return {
                    'deposition_id': deposition_id,
                    'json_file': json_file,
                    'publish_successful': True,
                    'already_published': True,
                    'doi': deposition.get('metadata', {}).get('prereserve_doi', {}).get('doi'),
                    'timestamp': datetime.now().isoformat()
                }
            
            # Always enforce metadata-only publishing
            files = deposition.get('files', [])
            if files:
                self.logger.log_info(
                    f"Removing {len(files)} attached file(s) from deposition {deposition_id} before publishing"
                )
            self._mark_as_metadata_only(deposition_id)
            
            # Publish the deposition
            published_deposition = self.client.publish_deposition(deposition_id)
            
            # Get DOI
            doi = published_deposition.get('metadata', {}).get('prereserve_doi', {}).get('doi')
            
            result = {
                'deposition_id': deposition_id,
                'json_file': json_file,
                'publish_successful': True,
                'doi': doi,
                'state': published_deposition.get('state'),
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'title': published_deposition.get('metadata', {}).get('title', ''),
                    'communities': published_deposition.get('metadata', {}).get('communities', [])
                }
            }
            
            self.logger.log_info(
                f"Successfully published {os.path.basename(json_file)} - "
                f"Deposition ID: {deposition_id}, DOI: {doi}"
            )
            
            return result
            
        except ZenodoAPIError as e:
            return {
                'deposition_id': deposition_id,
                'json_file': json_file,
                'publish_successful': False,
                'error': f"Zenodo API error: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'deposition_id': deposition_id,
                'json_file': json_file,
                'publish_successful': False,
                'error': f"Unexpected error: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _mark_as_metadata_only(self, deposition_id: int):
        """Mark a deposition as metadata-only (no files)."""
        try:
            # Get current metadata
            deposition = self.client.get_deposition(deposition_id)
            metadata = deposition.get('metadata', {}).copy()
            
            # Update the metadata while disabling files
            self.client.update_deposition_metadata(
                deposition_id,
                metadata,
                files={'enabled': False},
            )
            self.logger.log_info(f"Marked deposition {deposition_id} as metadata-only")
            
        except Exception as e:
            self.logger.log_error(
                f"deposition_{deposition_id}",
                "metadata_update",
                "metadata_only_toggle_failed",
                str(e),
                "Deposition metadata updated with files.disabled flag",
                "Zenodo deposition API rejected metadata update",
                "Inspect deposition state and retry once client connectivity is restored"
            )
            raise
    
    def _save_publish_results(self):
        """Save publishing results to files."""
        # Save publish log
        with open(self.publish_log_path, 'w', encoding='utf-8') as f:
            json.dump(self.publish_log, f, indent=2, ensure_ascii=False)
        
        # Save errors
        if self.publish_errors:
            with open(self.publish_errors_path, 'w', encoding='utf-8') as f:
                json.dump(self.publish_errors, f, indent=2, ensure_ascii=False)
    
    def _generate_publish_summary(self) -> Dict[str, Any]:
        """Generate summary of publishing results."""
        total = self.stats['total_records']
        successful = self.stats['successful_publishes']
        already_published = self.stats['already_published']
        failed = self.stats['failed_publishes']
        not_found = self.stats['not_found']
        
        success_rate = ((successful + already_published) / total * 100) if total > 0 else 0
        
        return {
            'total_records': total,
            'successful_publishes': successful,
            'already_published': already_published,
            'failed_publishes': failed,
            'not_found': not_found,
            'success_rate': success_rate,
            'publish_log_file': self.publish_log_path,
            'errors_file': self.publish_errors_path if self.publish_errors else None,
            'timestamp': datetime.now().isoformat()
        }
    
    def generate_publish_report(self, summary: Dict[str, Any]) -> str:
        """Generate a human-readable publish report."""
        report = []
        report.append("=" * 80)
        report.append("ZENODO RECORD PUBLISHING REPORT")
        report.append("=" * 80)
        report.append(f"Timestamp: {summary['timestamp']}")
        report.append(f"Environment: {'Sandbox' if self.sandbox else 'Production'}")
        report.append("")
        
        # Summary statistics
        report.append("PUBLISHING SUMMARY:")
        report.append(f"  Total records processed: {summary['total_records']}")
        report.append(f"  Successfully published: {summary['successful_publishes']}")
        report.append(f"  Already published: {summary['already_published']}")
        report.append(f"  Failed to publish: {summary['failed_publishes']}")
        report.append(f"  Not found: {summary['not_found']}")
        report.append(f"  Overall success rate: {summary['success_rate']:.1f}%")
        report.append("")
        
        # Files
        report.append("OUTPUT FILES:")
        report.append(f"  Publish log: {summary['publish_log_file']}")
        if summary.get('errors_file'):
            report.append(f"  Errors log: {summary['errors_file']}")
        report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS:")
        if summary['failed_publishes'] > 0:
            report.append(f"  - {summary['failed_publishes']} records failed to publish. Check errors log for details.")
        if summary['not_found'] > 0:
            report.append(f"  - {summary['not_found']} records were not found. Verify deposition IDs.")
        if summary['success_rate'] == 100:
            report.append("  - All records published successfully! Records should now be visible in PICES Community.")
        elif summary['success_rate'] >= 95:
            report.append("  - Excellent success rate! Most records are now published and visible.")
        elif summary['success_rate'] >= 80:
            report.append("  - Good success rate. Review failed records and retry if needed.")
        else:
            report.append("  - Low success rate. Review errors and check Zenodo API status.")
        
        return "\n".join(report)


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Publish uploaded Zenodo records to make them visible in communities"
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
        '--output', 
        type=str, 
        default='output',
        help='Output directory (default: output)'
    )
    parser.add_argument(
        '--limit', 
        type=int, 
        help='Limit number of records to publish (for testing)'
    )
    
    args = parser.parse_args()
    
    # Determine environment
    sandbox = not args.production
    
    # Initialize logging
    initialize_logger(default_log_dir("publish"))
    logger = get_logger()
    
    try:
        # Create publisher
        publisher = RecordPublisher(sandbox, args.output)
        
        # Load upload log
        upload_log = publisher.load_upload_log()
        
        # Publish records
        logger.log_info(f"Starting publishing in {'sandbox' if sandbox else 'production'} Zenodo...")
        summary = publisher.publish_records(upload_log, args.limit)
        
        # Generate report
        publish_report = publisher.generate_publish_report(summary)
        
        # Print summary to console
        print("\n" + publish_report)
        
        # Exit with appropriate code
        if summary['failed_publishes'] > 0:
            logger.log_info("Publishing completed with some failures")
            exit(1)
        else:
            logger.log_info("Publishing completed successfully")
            exit(0)
            
    except Exception as e:
        logger.log_error(
            "publish_process", "main_process", "fatal_error",
            str(e), "Successful publishing process",
            "Review error details and fix issues"
        )
        print(f"Fatal error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
