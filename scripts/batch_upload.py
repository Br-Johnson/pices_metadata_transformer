#!/usr/bin/env python3
"""
Batched upload script that processes files in manageable chunks with proper error handling,
resource cleanup, and progress tracking.
"""

import os
import json
import glob
import time
import signal
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ZenodoUploader functionality is now integrated into this script
from scripts.zenodo_api import create_zenodo_client
from scripts.path_config import OutputPaths, default_log_dir

class BatchUploader:
    """Handles batched uploads with proper resource management and error recovery."""
    
    def __init__(self, output_dir: str = "output", sandbox: bool = True, batch_size: int = 1000, limit: Optional[int] = None, interactive: bool = False):
        self.output_dir = output_dir
        self.paths = OutputPaths(output_dir)
        self.sandbox = sandbox
        self.batch_size = batch_size
        self.limit = limit
        self.interactive = interactive
        self.shutdown_requested = False
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.batch_log_file = self.paths.upload_batch_log_path(timestamp)
        self.batch_errors_file = self.paths.upload_batch_errors_path(timestamp)
        self.upload_log_path = self.paths.upload_log_path
        self.safe_to_upload_path = self.paths.safe_to_upload_path
        self.uploads_registry_path = self.paths.uploads_registry_path
        self.zenodo_json_dir = self.paths.zenodo_json_dir
        self.original_fgdc_dir = self.paths.original_fgdc_dir
        self.upload_reports_dir = self.paths.upload_reports_dir
        
        # Track progress across batches
        self.total_uploaded = 0
        self.total_failed = 0
        self.batch_log = []
        self.batch_errors = []
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _upload_single_file(self, json_file: str, client) -> Dict[str, Any]:
        """Upload a single JSON file to Zenodo."""
        metadata = {}
        timestamp = datetime.now().isoformat()
        try:
            # Load the JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            metadata = data.get('metadata', {})
            
            # Create deposition
            deposition = client.create_deposition(metadata)
            
            if not deposition:
                return {
                    'success': False,
                    'json_file': json_file,
                    'error': 'Failed to create deposition'
                }
            
            # Upload files if they exist
            if 'files' in data and data['files']:
                for file_info in data['files']:
                    file_path = file_info.get('path')
                    if file_path and os.path.exists(file_path):
                        client.upload_file(deposition['id'], file_path)
            
            # Get the DOI
            doi = f"10.5281/zenodo.{deposition['id']}"
            
            return {
                'success': True,
                'json_file': json_file,
                'deposition_id': deposition['id'],
                'doi': doi,
                'zenodo_url': f"{client.base_url}/deposit/{deposition['id']}",
                'metadata': metadata,
                'timestamp': timestamp
            }
            
        except Exception as e:
            return {
                'success': False,
                'json_file': json_file,
                'error': str(e),
                'metadata': metadata,
                'timestamp': timestamp
            }
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\nReceived signal {signum}. Shutting down gracefully...")
        self.shutdown_requested = True
    
    def get_remaining_files(self) -> List[str]:
        """Get list of files that haven't been uploaded yet."""
        # First, check if we have a safe-to-upload list from pre-upload duplicate check
        safe_files_path = self.safe_to_upload_path
        if os.path.exists(safe_files_path):
            print("📋 Using safe-to-upload list from pre-upload duplicate check...")
            try:
                with open(safe_files_path, 'r') as f:
                    safe_files = json.load(f)
                
                # Convert to full paths
                safe_json_files = []
                for filename in safe_files:
                    full_path = os.path.join(self.zenodo_json_dir, filename)
                    if os.path.exists(full_path):
                        safe_json_files.append(full_path)
                
                print(f"✅ Found {len(safe_json_files)} files safe to upload (pre-filtered for duplicates)")
                all_json_files = safe_json_files
                
            except Exception as e:
                print(f"⚠️  Could not load safe-to-upload list: {e}")
                print("   Falling back to checking all files...")
                # Fall back to getting all JSON files
                json_pattern = os.path.join(self.zenodo_json_dir, "*.json")
                all_json_files = glob.glob(json_pattern)
                all_json_files.sort()
        else:
            print("⚠️  No safe-to-upload list found. Checking all files...")
            print("   Consider running pre-upload duplicate check first.")
            # Get all JSON files
            json_pattern = os.path.join(self.zenodo_json_dir, "*.json")
            all_json_files = glob.glob(json_pattern)
            all_json_files.sort()
        
        # Get already uploaded files from centralized registry first
        uploaded_files = set()
        if os.path.exists(self.uploads_registry_path):
            try:
                with open(self.uploads_registry_path, 'r') as f:
                    registry = json.load(f)
                    for filename, entry in registry.items():
                        if entry.get('upload_status') == 'success':
                            uploaded_files.add(filename)
            except Exception as e:
                print(f"Warning: Could not load registry: {e}")
        
        # Get already uploaded files from all batch logs
        for log_file in glob.glob(os.path.join(self.upload_reports_dir, "batch_upload_log_*.json")):
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        batch_data = json.load(f)
                        # Handle both old and new batch log formats
                        if 'batches' in batch_data:
                            for batch in batch_data.get('batches', []):
                                for upload in batch.get('uploads', []):
                                    if upload.get('success', False):
                                        filename = os.path.basename(upload['json_file']).replace('.json', '')
                                        uploaded_files.add(filename)
                        else:
                            # Handle flat structure
                            for upload in batch_data.get('uploads', []):
                                if upload.get('success', False):
                                    filename = os.path.basename(upload['json_file']).replace('.json', '')
                                    uploaded_files.add(filename)
                except Exception as e:
                    print(f"Warning: Could not load batch log {log_file}: {e}")
        
        # Get already uploaded files from legacy upload log
        if os.path.exists(self.upload_log_path):
            try:
                with open(self.upload_log_path, 'r') as f:
                    legacy_data = json.load(f)
                    if isinstance(legacy_data, list):
                        for upload in legacy_data:
                            if upload.get('success', False):
                                filename = os.path.basename(upload['json_file']).replace('.json', '')
                                uploaded_files.add(filename)
            except Exception as e:
                print(f"Warning: Could not load legacy log: {e}")
        
        # Filter out already uploaded files
        remaining_files = []
        for json_file in all_json_files:
            filename = os.path.basename(json_file).replace('.json', '')
            if filename not in uploaded_files:
                remaining_files.append(json_file)

        # Apply limit if specified
        if self.limit is not None:
            remaining_files = remaining_files[:self.limit]

        print(f"Found {len(uploaded_files)} already uploaded files")
        print(f"Found {len(remaining_files)} remaining files to upload")
        if self.limit is not None:
            print(f"Limited to {self.limit} files for testing")

        return remaining_files
    
    def upload_batch(self, batch_files: List[str], batch_number: int) -> Dict[str, Any]:
        """Upload a single batch of files."""
        print(f"\n=== BATCH {batch_number} ===")
        print(f"Uploading {len(batch_files)} files...")
        
        batch_start_time = datetime.now()
        batch_uploads = []
        batch_errors = []
        
        # Use context manager for proper resource cleanup
        with create_zenodo_client(self.sandbox) as client:
            for i, json_file in enumerate(batch_files):
                if self.shutdown_requested:
                    print(f"Shutdown requested. Stopping batch {batch_number} at file {i+1}/{len(batch_files)}")
                    break
                
                try:
                    # Upload single file
                    result = self._upload_single_file(json_file, client)
                    result['batch_number'] = batch_number

                    if result['success']:
                        batch_uploads.append(result)
                        self.total_uploaded += 1
                        print(f"  ✓ {os.path.basename(json_file)} -> {result['doi']}")
                        # Update registry for successful uploads
                        self._update_registry(result, batch_number=batch_number)
                    else:
                        batch_errors.append(result)
                        self.total_failed += 1
                        print(f"  ✗ {os.path.basename(json_file)} -> {result.get('error', 'Unknown error')}")
                        # Update registry for failed uploads too
                        self._update_registry(result, batch_number=batch_number)

                except Exception as e:
                    error_result = {
                        'json_file': json_file,
                        'success': False,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat(),
                        'batch_number': batch_number
                    }
                    batch_errors.append(error_result)
                    self.total_failed += 1
                    print(f"  ✗ {os.path.basename(json_file)} -> {str(e)}")
                    # Update registry for failed uploads too
                    self._update_registry(error_result, batch_number=batch_number)
                # Small delay between files to be gentle on the API
                time.sleep(0.1)
        
        batch_end_time = datetime.now()
        batch_duration = (batch_end_time - batch_start_time).total_seconds()
        
        # Log batch results
        batch_result = {
            'batch_number': batch_number,
            'batch_size': len(batch_files),
            'successful_uploads': len(batch_uploads),
            'failed_uploads': len(batch_errors),
            'start_time': batch_start_time.isoformat(),
            'end_time': batch_end_time.isoformat(),
            'duration_seconds': batch_duration,
            'uploads': batch_uploads,
            'errors': batch_errors
        }
        
        self.batch_log.append(batch_result)
        self.batch_errors.extend(batch_errors)
        
        # Save progress after each batch
        self._save_progress()
        
        print(f"Batch {batch_number} completed: {len(batch_uploads)}/{len(batch_files)} successful")
        print(f"Total progress: {self.total_uploaded} uploaded, {self.total_failed} failed")
        
        return batch_result
    
    def _update_registry(self, upload_result: Dict[str, Any], batch_number: Optional[int] = None):
        """Update centralized uploads registry."""
        registry_path = self.uploads_registry_path
        
        # Load existing registry
        registry = {}
        if os.path.exists(registry_path):
            try:
                with open(registry_path, 'r') as f:
                    registry = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load registry: {e}")
                registry = {}
        
        # Extract filename from json_file path
        json_file = upload_result.get('json_file', '')
        filename = os.path.basename(json_file).replace('.json', '')
        
        if filename:
            # Update registry entry
            registry[filename] = {
                'deposition_id': upload_result.get('deposition_id'),
                'doi': upload_result.get('doi'),
                'title': upload_result.get('metadata', {}).get('title', ''),
                'uploaded_at': upload_result.get('timestamp'),
                'upload_status': 'success' if upload_result.get('success', False) else 'failed',
                'batch_number': batch_number if batch_number is not None else upload_result.get('batch_number'),
                'error_message': upload_result.get('error') if not upload_result.get('success', False) else None
            }
            
            # Update metadata
            if '_metadata' not in registry:
                registry['_metadata'] = {
                    'description': 'Centralized registry of all FGDC to Zenodo uploads',
                    'version': '1.0',
                    'created': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat(),
                    'total_entries': 0
                }
            
            registry['_metadata']['last_updated'] = datetime.now().isoformat()
            registry['_metadata']['total_entries'] = len([k for k in registry.keys() if not k.startswith('_')])
            
            # Save updated registry
            try:
                with open(registry_path, 'w') as f:
                    json.dump(registry, f, indent=2)
            except Exception as e:
                print(f"Warning: Could not save registry: {e}")
    
    def _interactive_batch_review(self, current_batch: int, total_batches: int):
        """Interactive review between batches for production uploads."""
        print(f"\n{'='*80}")
        print(f"BATCH {current_batch}/{total_batches} COMPLETED - INTERACTIVE REVIEW")
        print(f"{'='*80}")
        
        # Show batch summary
        print(f"Batch {current_batch} Summary:")
        print(f"  Files processed: {self.batch_size}")
        print(f"  Successful uploads: {self.total_uploaded}")
        print(f"  Failed uploads: {self.total_failed}")
        print(f"  Success rate: {(self.total_uploaded / (self.total_uploaded + self.total_failed) * 100):.1f}%" if (self.total_uploaded + self.total_failed) > 0 else "N/A")
        
        # Show recent logs
        print(f"\nRecent upload logs:")
        print(f"  Batch log: {self.batch_log_file}")
        print(f"  Error log: {self.batch_errors_file}")
        
        # Show registry status
        if os.path.exists(self.uploads_registry_path):
            try:
                with open(self.uploads_registry_path, 'r') as f:
                    registry = json.load(f)
                    total_entries = registry.get('_metadata', {}).get('total_entries', 0)
                    print(f"  Registry entries: {total_entries}")
            except Exception:
                pass
        
        # Display recent logs and reports
        self._display_recent_logs()
        
        print(f"\nNext steps:")
        print(f"  1. Review the logs and reports above")
        print(f"  2. Run duplicate check: python scripts/deduplicate_check.py {'--sandbox' if self.sandbox else '--production'}")
        print(f"  3. Run audit: python scripts/upload_audit.py")
        print(f"  4. Review individual records: python scripts/record_review.py <filename>")
        
        # Interactive prompt
        while True:
            print(f"\nOptions:")
            print(f"  [c]ontinue to next batch")
            print(f"  [s]top here and exit")
            print(f"  [r]un duplicate check now")
            print(f"  [a]udit current uploads")
            print(f"  [h]elp - show more commands")
            
            try:
                print(f"\n⏸️  WAITING FOR YOUR INPUT...")
                choice = input(f"What would you like to do? [c/s/r/a/h]: ").lower().strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\nInput interrupted. Stopping upload process.")
                self.shutdown_requested = True
                break
            
            if choice in ['c', 'continue']:
                print(f"Continuing to batch {current_batch + 1}...")
                break
            elif choice in ['s', 'stop', 'exit', 'quit']:
                print(f"Stopping upload process. Progress saved.")
                self.shutdown_requested = True
                break
            elif choice in ['r', 'duplicate', 'check']:
                print(f"Running duplicate check...")
                self._run_duplicate_check()
            elif choice in ['a', 'audit']:
                print(f"Running upload audit...")
                self._run_upload_audit()
            elif choice in ['h', 'help']:
                self._show_interactive_help()
            else:
                print(f"Invalid choice. Please try again.")
    
    def _run_duplicate_check(self):
        """Run duplicate check script."""
        import subprocess
        try:
            # Get the project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cmd = ['python3', 'scripts/deduplicate_check.py']
            if self.sandbox:
                cmd.append('--sandbox')
            else:
                cmd.append('--production')
            cmd.extend(['--output-dir', self.output_dir])
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            print(result.stdout)
            if result.stderr:
                print("Errors:", result.stderr)
        except Exception as e:
            print(f"Error running duplicate check: {e}")
    
    def _run_upload_audit(self):
        """Run upload audit script."""
        import subprocess
        try:
            # Get the project root directory
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cmd = ['python3', 'scripts/upload_audit.py', '--output-dir', self.output_dir]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            print(result.stdout)
            if result.stderr:
                print("Errors:", result.stderr)
        except Exception as e:
            print(f"Error running upload audit: {e}")
    
    def _display_recent_logs(self):
        """Display recent logs and reports in the terminal."""
        print(f"\n" + "="*80)
        print(f"RECENT LOGS AND REPORTS")
        print(f"="*80)
        
        # Display batch log summary
        if os.path.exists(self.batch_log_file):
            try:
                with open(self.batch_log_file, 'r') as f:
                    batch_data = json.load(f)
                    print(f"\n📊 BATCH LOG SUMMARY:")
                    print(f"  Total uploaded: {batch_data.get('total_uploaded', 0)}")
                    print(f"  Total failed: {batch_data.get('total_failed', 0)}")
                    print(f"  Batches completed: {len(batch_data.get('batches', []))}")
                    
                    # Show last batch details
                    if batch_data.get('batches'):
                        last_batch = batch_data['batches'][-1]
                        print(f"\n  Last batch ({last_batch.get('batch_number', 'N/A')}):")
                        print(f"    Successful: {last_batch.get('successful_uploads', 0)}")
                        print(f"    Failed: {last_batch.get('failed_uploads', 0)}")
                        print(f"    Duration: {last_batch.get('duration_seconds', 0):.1f}s")
                        
                        # Show recent uploads
                        if last_batch.get('uploads'):
                            print(f"    Recent uploads:")
                            for upload in last_batch['uploads'][-3:]:  # Last 3 uploads
                                status = "✅" if upload.get('success') else "❌"
                                title = upload.get('metadata', {}).get('title', 'Unknown')[:50]
                                print(f"      {status} {title}...")
            except Exception as e:
                print(f"  Error reading batch log: {e}")
        
        # Display error log summary
        if os.path.exists(self.batch_errors_file):
            try:
                with open(self.batch_errors_file, 'r') as f:
                    errors = json.load(f)
                    if errors:
                        print(f"\n❌ RECENT ERRORS ({len(errors)} total):")
                        for error in errors[-3:]:  # Last 3 errors
                            filename = os.path.basename(error.get('json_file', 'Unknown'))
                            error_msg = error.get('error', 'Unknown error')[:60]
                            print(f"  • {filename}: {error_msg}...")
                    else:
                        print(f"\n✅ NO RECENT ERRORS")
            except Exception as e:
                print(f"  Error reading error log: {e}")
        
        # Display registry summary
        registry_path = self.uploads_registry_path
        if os.path.exists(registry_path):
            try:
                with open(registry_path, 'r') as f:
                    registry = json.load(f)
                    total_entries = registry.get('_metadata', {}).get('total_entries', 0)
                    last_updated = registry.get('_metadata', {}).get('last_updated', 'Unknown')
                    print(f"\n📋 REGISTRY SUMMARY:")
                    print(f"  Total entries: {total_entries}")
                    print(f"  Last updated: {last_updated}")
            except Exception as e:
                print(f"  Error reading registry: {e}")
        
        print(f"\n" + "="*80)

    def _show_interactive_help(self):
        """Show help for interactive mode."""
        print(f"\nInteractive Mode Help:")
        print(f"  [c]ontinue - Proceed to the next batch")
        print(f"  [s]top - Stop the upload process and exit")
        print(f"  [r]un duplicate check - Check for duplicate records")
        print(f"  [a]udit - Run comprehensive upload audit")
        print(f"  [h]elp - Show this help message")
        print(f"\nAdditional commands you can run manually:")
        print(f"  python scripts/record_review.py <filename> - Review specific record")
        print(f"  python scripts/deduplicate_check.py {'--sandbox' if self.sandbox else '--production'} - Check duplicates")
        print(f"  python scripts/upload_audit.py - Audit all uploads")
        print(f"  python scripts/metrics_analysis.py - Analyze transformation metrics")
    
    def _append_to_upload_log(self, upload_result: Dict[str, Any]):
        """Append an entry to the legacy upload log for downstream verification."""
        json_path = upload_result.get('json_file')
        if not json_path:
            return
        
        # Derive the copied FGDC path if it exists
        fgdc_path = None
        base_name = os.path.splitext(os.path.basename(json_path))[0]
        candidate_fgdc = os.path.join(self.original_fgdc_dir, f"{base_name}.xml")
        if os.path.exists(candidate_fgdc):
            fgdc_path = candidate_fgdc
        
        log_entry = {
            'json_file': json_path,
            'fgdc_file': fgdc_path,
            'deposition_id': upload_result.get('deposition_id'),
            'doi': upload_result.get('doi'),
            'success': upload_result.get('success', False),
            'timestamp': upload_result.get('timestamp'),
            'metadata': upload_result.get('metadata', {}),
            'batch_number': upload_result.get('batch_number')
        }
        
        if upload_result.get('zenodo_url'):
            log_entry['zenodo_url'] = upload_result['zenodo_url']
        if upload_result.get('error'):
            log_entry['error'] = upload_result['error']
        
        try:
            existing_entries = []
            if os.path.exists(self.upload_log_path):
                with open(self.upload_log_path, 'r', encoding='utf-8') as f:
                    existing_entries = json.load(f)
                    if not isinstance(existing_entries, list):
                        existing_entries = []
            existing_entries.append(log_entry)
            with open(self.upload_log_path, 'w', encoding='utf-8') as f:
                json.dump(existing_entries, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not update upload log: {e}")
    
    def _save_progress(self):
        """Save current progress to files."""
        # Save batch log
        with open(self.batch_log_file, 'w') as f:
            json.dump({
                'total_uploaded': self.total_uploaded,
                'total_failed': self.total_failed,
                'batches': self.batch_log,
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
        
        # Save errors
        with open(self.batch_errors_file, 'w') as f:
            json.dump(self.batch_errors, f, indent=2)
    
    def upload_all_batches(self):
        """Upload all remaining files in batches."""
        remaining_files = self.get_remaining_files()
        
        if not remaining_files:
            print("No files remaining to upload!")
            # Ensure verification step finds an upload log, even when nothing was uploaded
            if not os.path.exists(self.upload_log_path):
                with open(self.upload_log_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=2)
            return
        
        print(f"Found {len(remaining_files)} files remaining to upload")
        print(f"Will process in batches of {self.batch_size}")
        
        # Split into batches
        batches = [remaining_files[i:i + self.batch_size] 
                  for i in range(0, len(remaining_files), self.batch_size)]
        
        print(f"Created {len(batches)} batches")
        
        start_time = datetime.now()
        
        for i, batch_files in enumerate(batches, 1):
            if self.shutdown_requested:
                print(f"Shutdown requested. Stopping at batch {i}/{len(batches)}")
                break
            
            try:
                self.upload_batch(batch_files, i)
                
                # Interactive mode: stop between batches for review
                if self.interactive and i < len(batches) and not self.shutdown_requested:
                    self._interactive_batch_review(i, len(batches))
                elif i < len(batches) and not self.shutdown_requested:
                    # Non-interactive mode: pause between batches to respect rate limits
                    print(f"Pausing 30 seconds before next batch...")
                    time.sleep(30)
                    
            except KeyboardInterrupt:
                print(f"\nInterrupted at batch {i}. Saving progress...")
                break
            except Exception as e:
                print(f"Error in batch {i}: {e}")
                continue
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # Final summary
        print(f"\n=== UPLOAD COMPLETE ===")
        print(f"Total files uploaded: {self.total_uploaded}")
        print(f"Total files failed: {self.total_failed}")
        print(f"Total duration: {total_duration/3600:.1f} hours")
        print(f"Batch log: {self.batch_log_file}")
        print(f"Error log: {self.batch_errors_file}")

def main():
    """Main function with command line argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload FGDC records to Zenodo in batches')
    parser.add_argument('--sandbox', action='store_true', default=True,
                       help='Use Zenodo sandbox (default: True)')
    parser.add_argument('--production', action='store_true',
                       help='Use Zenodo production (overrides --sandbox)')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Number of files per batch (default: 1000)')
    parser.add_argument('--limit', type=int,
                       help='Limit number of files to process (for testing)')
    parser.add_argument('--interactive', action='store_true',
                       help='Interactive mode: stop between batches for review (recommended for production)')
    parser.add_argument('--output-dir', default='output',
                       help='Output directory for logs (default: output)')
    
    args = parser.parse_args()
    
    # Determine environment
    sandbox = not args.production
    
    print(f"Starting batch upload to {'sandbox' if sandbox else 'production'} Zenodo")
    print(f"Batch size: {args.batch_size}")
    print(f"Interactive mode: {'ON' if args.interactive else 'OFF'}")
    print(f"Output directory: {args.output_dir}")
    
    if args.interactive:
        print(f"\n🔍 INTERACTIVE MODE ENABLED")
        print(f"This will stop between each batch for review and validation.")
        print(f"Use this mode for production uploads to ensure quality control.")
    
    uploader = BatchUploader(
        output_dir=args.output_dir,
        sandbox=sandbox,
        batch_size=args.batch_size,
        limit=args.limit,
        interactive=args.interactive
    )
    
    try:
        uploader.upload_all_batches()
    except KeyboardInterrupt:
        print("\nUpload interrupted by user")
    except Exception as e:
        print(f"Upload failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
