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
from scripts.upload_service import validate_registry_identities, validate_deposition_response, assert_environment, atomic_json, ledger_lock, read_json
from scripts.qa_manifest import validate_approval, validate_program_review
from scripts.artifact_contract import prepare_artifact, assert_artifact_binding, validate_files
from scripts.upload_service import prepare_metadata
from scripts.release_manifest import validate_release


class RecordPublisher:
    """Handles publishing uploaded records to Zenodo."""
    
    def __init__(self, sandbox: bool = True, output_dir: str = "output", qa_manifest=None, release_manifest=None):
        self.qa_manifest = read_json(qa_manifest) if isinstance(qa_manifest, (str, os.PathLike)) else qa_manifest
        self.release_manifest = read_json(release_manifest) if isinstance(release_manifest, (str, os.PathLike)) else release_manifest
        if not sandbox and not self.qa_manifest:
            raise ValueError('Production publication requires --qa-manifest with supported record QA')
        if not sandbox and not self.release_manifest:
            raise ValueError('Production publication requires separate --release-manifest authorization')
        self.sandbox = sandbox
        self.output_dir = output_dir
        self.paths = OutputPaths(output_dir, "sandbox" if sandbox else "production")
        if read_json(self.paths.uploads_registry_path, {}).get('_sandbox_canary'):
            raise ValueError('Sandbox canary ledgers cannot be published')
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
    
    def _record_publication(self, fgdc_id, deposition_id, communities):
        registry = read_json(self.paths.uploads_registry_path, {})
        entry = registry.get(fgdc_id)
        if not entry or entry.get('deposition_id') != deposition_id:
            raise ValueError('Upload ledger changed during publication')
        entry['publish_status'] = 'published'
        entry['published_at'] = datetime.now().isoformat()
        entry['community_status'] = 'reported' if any(c.get('identifier') == 'pices' for c in communities) else 'unconfirmed'
        atomic_json(self.paths.uploads_registry_path, registry)

    def load_upload_log(self) -> List[Dict[str, Any]]:
        """Load upload metadata and aggregate successful records for publishing."""
        registry = read_json(self.paths.uploads_registry_path, {})
        uploads = []
        approved_ids = {record.get('fgdc_id') for record in (self.qa_manifest or {}).get('records', [])
                        if record.get('qa', {}).get('approved') is True}
        if not self.sandbox:
            release = getattr(self, 'release_manifest', None)
            if not isinstance(release, dict):
                raise ValueError('Separate publication release required')
            # Apply bounded release selection before --limit, then validate every selected row.
            approved_ids &= {record.get('fgdc_id') for record in release.get('records', [])}
        for fgdc_id, entry in sorted(registry.items()):
            if fgdc_id.startswith('_') or entry.get('upload_status') != 'success':
                continue
            if not self.sandbox and fgdc_id not in approved_ids:
                continue
            assert_environment(entry, self.paths.environment)
            uploads.append(dict(entry, success=True))
        if not uploads:
            raise ValueError('No successful environment-scoped drafts found')
        return uploads

    def publish_records(self, upload_log: List[Dict[str, Any]], limit: int = None) -> Dict[str, Any]:
        """Publish uploaded records to make them visible in communities."""
        if read_json(self.paths.uploads_registry_path, {}).get('_sandbox_canary'):
            raise ValueError('Sandbox canary ledgers cannot be published')
        
        if limit:
            upload_log = upload_log[:limit]
        
        self.stats['total_records'] = len(upload_log)
        
        self.logger.log_info(f"Starting to publish {len(upload_log)} records...")
        
        # Process records with progress bar
        for upload in tqdm(upload_log, desc="Publishing records"):
            try:
                result = self._publish_single_record(upload)
                self.publish_log.append(result)
                
                if result.get('already_published'):
                    self.stats['already_published'] += 1
                elif result['publish_successful']:
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
    
    def _publish_single_record(self, upload):
        # Keep reconciliation/upload writers out of the entire approval-to-POST interval.
        try:
            with ledger_lock(self.paths):
                registry = read_json(self.paths.uploads_registry_path, {})
                if registry.get('_sandbox_canary'):
                    raise ValueError('Sandbox canary ledgers cannot be published')
                validate_registry_identities(registry)
                fgdc_id = os.path.splitext(os.path.basename(upload['json_file']))[0]
                current = registry.get(fgdc_id, {})
                if any(current.get(key) != upload.get(key) for key in
                       ('deposition_id', 'metadata_sha256', 'source_sha256', 'environment', 'json_file', 'artifact_contract')):
                    raise ValueError('Upload ledger binding changed before publication')
                return self._publish_locked(upload)
        except Exception as exc:
            return {'deposition_id': upload.get('deposition_id'), 'json_file': upload.get('json_file'),
                    'publish_successful': False, 'error': str(exc), 'timestamp': datetime.now().isoformat()}

    def _publish_locked(self, upload: Dict[str, Any]) -> Dict[str, Any]:
        """Publish a single uploaded record."""
        deposition_id = upload.get('deposition_id')
        json_file = upload.get('json_file')
        
        try:
            assert_environment(upload, self.paths.environment)
            fgdc_id = os.path.splitext(os.path.basename(json_file))[0]
            if not self.sandbox:
                validate_approval(self.qa_manifest, fgdc_id, upload, self.paths)
                if self.qa_manifest.get('schema_version') == 2:
                    validate_program_review(self.qa_manifest)
                validate_release(getattr(self, 'release_manifest', None), self.qa_manifest, fgdc_id, upload)
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
            
            validate_deposition_response(deposition, deposition_id)
            _, source_path, _ = prepare_metadata(json_file, self.paths)
            artifact = prepare_artifact(read_json(json_file), source_path)
            assert_artifact_binding(upload, artifact)
            validate_files(deposition['files'], artifact)

            if not self.sandbox:
                validate_approval(self.qa_manifest, fgdc_id, upload, self.paths, deposition.get('metadata', {}), deposition['files'])

            # Check if already published
            if deposition.get('state') == 'done':
                metadata_payload = deposition.get('metadata', {})
                communities = metadata_payload.get('communities', []) or []
                if not any(comm.get('identifier') == 'pices' for comm in communities):
                    self.logger.log_warning(
                        json_file,
                        "publish",
                        "missing_pices_community",
                        "Already-published record is not associated with the PICES community",
                        "Published record includes the 'pices' community",
                        "Zenodo deposition metadata lacks 'pices' community",
                        "Confirm community membership in the Zenodo UI; add manually if required"
                    )
                self._record_publication(fgdc_id, deposition_id, communities)
                return {
                    'deposition_id': deposition_id,
                    'json_file': json_file,
                    'publish_successful': True,
                    'already_published': True,
                    'doi': metadata_payload.get('prereserve_doi', {}).get('doi'),
                    'timestamp': datetime.now().isoformat(),
                    'metadata': {
                        'title': metadata_payload.get('title', ''),
                        'communities': communities
                    }
                }
            
            # Publish the deposition
            published_deposition = self.client.publish_deposition(deposition_id)
            
            # Re-fetch metadata to ensure communities and final state are captured
            final_deposition = None
            try:
                final_deposition = self.client.get_deposition(deposition_id)
            except Exception as fetch_error:
                self.logger.log_warning(
                    json_file,
                    "publish",
                    "post_publish_fetch_failed",
                    str(fetch_error),
                    "Published record metadata available for verification",
                    "Zenodo API returned minimal publish payload; continuing with limited metadata",
                    "Retry fetching deposition details manually if community membership needs confirmation"
                )
            
            # Prefer the refreshed metadata when available
            metadata_payload = (final_deposition or published_deposition).get('metadata', {}) if (final_deposition or published_deposition) else {}
            
            # Get DOI and communities from the final payload
            doi = metadata_payload.get('prereserve_doi', {}).get('doi')
            communities = metadata_payload.get('communities', []) or []
            
            # Warn if the PICES community is missing
            if not any(comm.get('identifier') == 'pices' for comm in communities):
                self.logger.log_warning(
                    json_file,
                    "publish",
                    "missing_pices_community",
                    "Published record is not associated with the PICES community",
                    "Published record includes the 'pices' community",
                    "Zenodo returned communities list without 'pices'",
                    "Confirm community membership in the Zenodo UI; add manually if required"
                )
            
            confirmed = validate_deposition_response(final_deposition or published_deposition, deposition_id)
            validate_files(confirmed['files'], artifact)
            final_state = confirmed['state']
            if final_state != 'done':
                raise ValueError('Publication state is unconfirmed; reconcile before retry')
            if not self.sandbox:
                validate_approval(self.qa_manifest, fgdc_id, upload, self.paths,
                                  confirmed['metadata'], confirmed['files'])
            self._record_publication(fgdc_id, deposition_id, communities)

            result = {
                'deposition_id': deposition_id,
                'json_file': json_file,
                'publish_successful': True,
                'doi': doi,
                'state': final_state,
                'timestamp': datetime.now().isoformat(),
                'metadata': {
                    'title': metadata_payload.get('title', ''),
                    'communities': communities
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
        if summary['failed_publishes'] > 0 or summary['not_found'] > 0:
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
    
    parser.add_argument("--qa-manifest", help="Evidence-bound record QA manifest required for production")
    parser.add_argument("--release-manifest", help="Separate explicit release authorization required for production")
    args = parser.parse_args()
    
    # Determine environment
    sandbox = not args.production
    
    # Initialize logging
    initialize_logger(default_log_dir("publish"))
    logger = get_logger()
    
    try:
        # Create publisher
        publisher = RecordPublisher(sandbox, args.output, args.qa_manifest, args.release_manifest)
        
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
        if summary['failed_publishes'] > 0 or summary['not_found'] > 0:
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
