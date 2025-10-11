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

from scripts.upload_to_zenodo import ZenodoUploader
from scripts.zenodo_api import create_zenodo_client

class BatchUploader:
    """Handles batched uploads with proper resource management and error recovery."""
    
    def __init__(self, output_dir: str = "output", sandbox: bool = True, batch_size: int = 1000):
        self.output_dir = output_dir
        self.sandbox = sandbox
        self.batch_size = batch_size
        self.batch_log_file = os.path.join(output_dir, f"batch_upload_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        self.batch_errors_file = os.path.join(output_dir, f"batch_upload_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        # Track progress across batches
        self.total_uploaded = 0
        self.total_failed = 0
        self.batch_log = []
        self.batch_errors = []
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.shutdown_requested = False
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        print(f"\nReceived signal {signum}. Shutting down gracefully...")
        self.shutdown_requested = True
    
    def get_remaining_files(self) -> List[str]:
        """Get list of files that haven't been uploaded yet."""
        # Get all JSON files
        json_pattern = os.path.join(self.output_dir, "zenodo_json/*.json")
        all_json_files = glob.glob(json_pattern)
        all_json_files.sort()
        
        # Get already uploaded files from centralized registry first
        uploaded_files = set()
        registry_path = os.path.join(self.output_dir, 'uploads_registry.json')
        if os.path.exists(registry_path):
            try:
                with open(registry_path, 'r') as f:
                    registry = json.load(f)
                    for filename, entry in registry.items():
                        if entry.get('upload_status') == 'success':
                            uploaded_files.add(filename)
            except Exception as e:
                print(f"Warning: Could not load registry: {e}")
        
        # Get already uploaded files from all batch logs
        for log_file in glob.glob(os.path.join(self.output_dir, "batch_upload_log_*.json")):
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
        legacy_log_path = os.path.join(self.output_dir, 'upload_log.json')
        if os.path.exists(legacy_log_path):
            try:
                with open(legacy_log_path, 'r') as f:
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
        
        print(f"Found {len(uploaded_files)} already uploaded files")
        print(f"Found {len(remaining_files)} remaining files to upload")
        
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
            uploader = ZenodoUploader(self.sandbox, self.output_dir)
            uploader.client = client  # Use our managed client
            
            for i, json_file in enumerate(batch_files):
                if self.shutdown_requested:
                    print(f"Shutdown requested. Stopping batch {batch_number} at file {i+1}/{len(batch_files)}")
                    break
                
                try:
                    # Upload single file
                    result = uploader._upload_single_file(json_file)
                    
                    if result['success']:
                        batch_uploads.append(result)
                        self.total_uploaded += 1
                        print(f"  ✓ {os.path.basename(json_file)} -> {result['doi']}")
                        # Update registry for successful uploads
                        self._update_registry(result)
                    else:
                        batch_errors.append(result)
                        self.total_failed += 1
                        print(f"  ✗ {os.path.basename(json_file)} -> {result.get('error', 'Unknown error')}")
                        # Update registry for failed uploads too
                        self._update_registry(result)
                
                except Exception as e:
                    error_result = {
                        'json_file': json_file,
                        'success': False,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    }
                    batch_errors.append(error_result)
                    self.total_failed += 1
                    print(f"  ✗ {os.path.basename(json_file)} -> {str(e)}")
                
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
    
    def _update_registry(self, upload_result: Dict[str, Any]):
        """Update centralized uploads registry."""
        registry_path = os.path.join(self.output_dir, 'uploads_registry.json')
        
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
                'batch_number': upload_result.get('batch_number'),
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
                
                # Longer pause between batches to be gentle on the API
                if i < len(batches) and not self.shutdown_requested:
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
    parser.add_argument('--output-dir', default='output',
                       help='Output directory for logs (default: output)')
    
    args = parser.parse_args()
    
    # Determine environment
    sandbox = not args.production
    
    print(f"Starting batch upload to {'sandbox' if sandbox else 'production'} Zenodo")
    print(f"Batch size: {args.batch_size}")
    print(f"Output directory: {args.output_dir}")
    
    uploader = BatchUploader(
        output_dir=args.output_dir,
        sandbox=sandbox,
        batch_size=args.batch_size
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
