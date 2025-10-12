#!/usr/bin/env python3
"""
Comprehensive duplicate detection script for Zenodo uploads.
Checks for duplicates across local logs, centralized registry, and Zenodo API.
"""

import os
import json
import glob
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Set, Optional
from collections import defaultdict
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.zenodo_api import create_zenodo_client, ZenodoAPIError
from scripts.logger import initialize_logger, get_logger
from scripts.path_config import OutputPaths, default_log_dir


class DuplicateChecker:
    """Comprehensive duplicate detection for Zenodo uploads."""
    
    def __init__(
        self,
        sandbox: bool = True,
        output_dir: str = "output",
        hours_back: int = 6,
        cache_ttl_minutes: int = 15,
        use_cache: bool = True,
    ):
        self.sandbox = sandbox
        self.output_dir = output_dir
        self.paths = OutputPaths(output_dir)
        self.hours_back = hours_back
        self.cache_ttl_minutes = cache_ttl_minutes
        self.use_cache = use_cache
        self.logger = get_logger()
        
        # Initialize Zenodo client
        self.client = create_zenodo_client(sandbox)
        
        # File paths
        self.registry_path = self.paths.uploads_registry_path
        self.legacy_log_path = self.paths.upload_log_path
        self.cache_dir = self.paths.cache_directory
        self.upload_reports_dir = self.paths.upload_reports_dir
        self.duplicates_reports_dir = self.paths.duplicates_reports_dir
        
        # Results storage
        self.duplicates_found = []
        self.registry_entries = {}
        self.zenodo_depositions = []
        self.local_uploads = set()
        
    def load_uploads_registry(self) -> Dict[str, Any]:
        """Load centralized uploads registry."""
        if not os.path.exists(self.registry_path):
            self.logger.log_info("No uploads registry found, creating empty one")
            return {}
        
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                registry = json.load(f)
            self.logger.log_info(f"Loaded {len(registry)} entries from uploads registry")
            return registry
        except Exception as e:
            self.logger.log_error(
                "registry_load", "file_io", "load_error",
                str(e), "Valid JSON registry file",
                f"Failed to load registry: {str(e)}"
            )
            return {}
    
    def load_local_uploads(self) -> Set[str]:
        """Load all locally tracked uploads from various log formats."""
        uploaded_files = set()
        
        # Load from centralized registry
        registry = self.registry_entries or self.load_uploads_registry()
        for filename in registry.keys():
            uploaded_files.add(filename)
        
        # Load from batch upload logs
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
                    self.logger.log_warning(
                        log_file, "batch_log_load", "load_error",
                        str(e), "Valid batch log file",
                        f"Failed to load batch log {log_file}: {str(e)}"
                    )
        
        # Load from legacy upload log
        if os.path.exists(self.legacy_log_path):
            try:
                with open(self.legacy_log_path, 'r') as f:
                    legacy_data = json.load(f)
                    if isinstance(legacy_data, list):
                        for upload in legacy_data:
                            if upload.get('success', False):
                                filename = os.path.basename(upload['json_file']).replace('.json', '')
                                uploaded_files.add(filename)
            except Exception as e:
                self.logger.log_warning(
                    self.legacy_log_path, "legacy_log_load", "load_error",
                    str(e), "Valid legacy log file",
                    f"Failed to load legacy log: {str(e)}"
                )
        
        self.local_uploads = uploaded_files
        self.logger.log_info(f"Found {len(uploaded_files)} locally tracked uploads")
        return uploaded_files
    
    def load_zenodo_depositions(self) -> List[Dict[str, Any]]:
        """Load all depositions from Zenodo API."""
        # Attempt to use cached data if enabled and fresh
        if self.use_cache:
            cached = self._load_cached_depositions()
            if cached is not None:
                self.zenodo_depositions = cached
                self.logger.log_info(f"Using cached Zenodo depositions ({len(cached)} records)")
                return cached
        
        try:
            self.logger.log_info(
                f"Fetching depositions modified in the last {self.hours_back} hour(s) from Zenodo..."
            )
            since = datetime.utcnow() - timedelta(hours=self.hours_back)
            depositions = self.client.get_all_my_depositions(modified_since=since)
            self.zenodo_depositions = depositions
            self.logger.log_info(f"Found {len(depositions)} recent depositions in Zenodo")
            if self.use_cache:
                self._save_cached_depositions(depositions)
            return depositions
        except ZenodoAPIError as e:
            self.logger.log_error(
                "zenodo_api", "deposition_fetch", "api_error",
                str(e), "Successful API call",
                f"Failed to fetch depositions from Zenodo: {str(e)}"
            )
            return []
    
    def _cache_file_path(self) -> str:
        """Return cache file path scoped to environment."""
        env = "sandbox" if self.sandbox else "production"
        return os.path.join(self.cache_dir, f"zenodo_depositions_{env}.json")
    
    def _load_cached_depositions(self) -> Optional[List[Dict[str, Any]]]:
        """Load cached depositions if within TTL."""
        cache_file = self._cache_file_path()
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
            fetched_raw = payload.get("fetched_at")
            if not fetched_raw:
                return None
            fetched_at = datetime.fromisoformat(fetched_raw)
            if datetime.utcnow() - fetched_at > timedelta(minutes=self.cache_ttl_minutes):
                return None
            return payload.get("depositions", [])
        except Exception as e:
            self.logger.log_warning(
                cache_file,
                "cache_load",
                "cache_unusable",
                str(e),
                "Cache file readable and valid JSON",
                "Removing stale cache entry",
                "Will refetch from Zenodo on this run"
            )
            return None
    
    def _save_cached_depositions(self, depositions: List[Dict[str, Any]]):
        """Persist depositions to cache."""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            payload = {
                "fetched_at": datetime.utcnow().isoformat(),
                "depositions": depositions,
                "hours_back": self.hours_back,
            }
            with open(self._cache_file_path(), "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            self.logger.log_warning(
                self._cache_file_path(),
                "cache_save",
                "cache_write_failed",
                str(e),
                "Cache directory writable",
                "Unable to write Zenodo cache",
                "Check filesystem permissions or available space"
            )
    
    def find_title_duplicates(self) -> List[Dict[str, Any]]:
        """Find potential duplicates by comparing titles."""
        duplicates = []
        title_map = defaultdict(list)
        
        # Group depositions by title
        for deposition in self.zenodo_depositions:
            metadata = deposition.get('metadata', {})
            title = metadata.get('title', '').strip()
            if title:
                title_map[title.lower()].append({
                    'deposition_id': deposition['id'],
                    'title': title,
                    'doi': metadata.get('prereserve_doi', {}).get('doi'),
                    'created': deposition.get('created'),
                    'modified': deposition.get('modified')
                })
        
        # Find titles with multiple depositions
        for title, depositions in title_map.items():
            if len(depositions) > 1:
                duplicates.append({
                    'type': 'title_duplicate',
                    'title': title,
                    'count': len(depositions),
                    'depositions': depositions
                })
        
        return duplicates
    
    def find_registry_mismatches(self) -> List[Dict[str, Any]]:
        """Find mismatches between local registry and Zenodo."""
        mismatches = []
        registry = self.load_uploads_registry()
        cutoff = datetime.utcnow() - timedelta(hours=self.hours_back)
        
        def is_recent(entry: Dict[str, Any]) -> bool:
            uploaded_at = entry.get('uploaded_at')
            if not uploaded_at:
                return False
            try:
                uploaded_dt = datetime.fromisoformat(uploaded_at)
                return uploaded_dt >= cutoff
            except Exception:
                return False
        
        recent_registry_items = {
            filename: entry
            for filename, entry in registry.items()
            if not filename.startswith('_') and is_recent(entry)
        }
        
        self.logger.log_info(
            f"Registry entries considered within {self.hours_back} hour(s): {len(recent_registry_items)}"
        )
        
        # Check if recent registry entries exist in Zenodo
        for filename, registry_entry in recent_registry_items.items():
            deposition_id = registry_entry.get('deposition_id')
            if deposition_id:
                # Check if this deposition exists in Zenodo
                found = False
                for deposition in self.zenodo_depositions:
                    if deposition['id'] == deposition_id:
                        found = True
                        break
                
                if not found:
                    mismatches.append({
                        'type': 'missing_in_zenodo',
                        'filename': filename,
                        'deposition_id': deposition_id,
                        'registry_entry': registry_entry
                    })
        
        # Check if Zenodo depositions are missing from registry
        zenodo_ids = {dep['id'] for dep in self.zenodo_depositions}
        registry_ids = {
            entry.get('deposition_id')
            for entry in recent_registry_items.values()
            if entry.get('deposition_id')
        }
        
        missing_from_registry = zenodo_ids - registry_ids
        for deposition_id in missing_from_registry:
            # Find the deposition
            for deposition in self.zenodo_depositions:
                if deposition['id'] == deposition_id:
                    mismatches.append({
                        'type': 'missing_from_registry',
                        'deposition_id': deposition_id,
                        'title': deposition.get('metadata', {}).get('title', 'Unknown'),
                        'created': deposition.get('created')
                    })
                    break
        
        return mismatches
    
    def check_specific_files(self, filenames: List[str]) -> List[Dict[str, Any]]:
        """Check specific files for duplicates."""
        results = []
        
        for filename in filenames:
            # Check if file is in local uploads
            in_local = filename in self.local_uploads
            
            # Check if file has registry entry
            registry_entry = self.registry_entries.get(filename)
            
            # Check if file title exists in Zenodo
            json_file = os.path.join('transformed', 'zenodo_json', f'{filename}.json')
            zenodo_matches = []
            
            if os.path.exists(json_file):
                try:
                    with open(json_file, 'r') as f:
                        data = json.load(f)
                        title = data.get('metadata', {}).get('title', '')
                        if title:
                            zenodo_matches = self.client.search_by_title(title)
                except Exception as e:
                    self.logger.log_warning(
                        json_file, "file_check", "read_error",
                        str(e), "Valid JSON file",
                        f"Failed to read {json_file}: {str(e)}"
                    )
            
            results.append({
                'filename': filename,
                'in_local_uploads': in_local,
                'registry_entry': registry_entry,
                'zenodo_matches': len(zenodo_matches),
                'zenodo_depositions': zenodo_matches
            })
        
        return results
    
    def generate_report(self, duplicates: List[Dict], mismatches: List[Dict], 
                       specific_checks: List[Dict] = None) -> str:
        """Generate comprehensive duplicate detection report."""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("ZENODO DUPLICATE DETECTION REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Environment: {'Sandbox' if self.sandbox else 'Production'}")
        report_lines.append("")
        
        # Summary
        report_lines.append("SUMMARY")
        report_lines.append("-" * 40)
        report_lines.append(f"Local uploads tracked: {len(self.local_uploads)}")
        report_lines.append(f"Zenodo depositions found: {len(self.zenodo_depositions)}")
        report_lines.append(f"Remote lookback window (hours): {self.hours_back}")
        report_lines.append(
            f"Cache TTL (minutes): {self.cache_ttl_minutes if self.use_cache else 'disabled'}"
        )
        report_lines.append(f"Title duplicates found: {len(duplicates)}")
        report_lines.append(f"Registry mismatches: {len(mismatches)}")
        report_lines.append("")
        
        # Title duplicates
        if duplicates:
            report_lines.append("TITLE DUPLICATES")
            report_lines.append("-" * 40)
            for dup in duplicates:
                report_lines.append(f"Title: {dup['title']}")
                report_lines.append(f"  Count: {dup['count']} depositions")
                for dep in dup['depositions']:
                    report_lines.append(f"    - ID: {dep['deposition_id']}, DOI: {dep.get('doi', 'N/A')}")
                report_lines.append("")
        
        # Registry mismatches
        if mismatches:
            report_lines.append("REGISTRY MISMATCHES")
            report_lines.append("-" * 40)
            for mismatch in mismatches:
                if mismatch['type'] == 'missing_in_zenodo':
                    report_lines.append(f"Missing in Zenodo: {mismatch['filename']} (ID: {mismatch['deposition_id']})")
                elif mismatch['type'] == 'missing_from_registry':
                    report_lines.append(f"Missing from registry: {mismatch['deposition_id']} - {mismatch['title']}")
            report_lines.append("")
        
        # Specific file checks
        if specific_checks:
            report_lines.append("SPECIFIC FILE CHECKS")
            report_lines.append("-" * 40)
            for check in specific_checks:
                report_lines.append(f"File: {check['filename']}")
                report_lines.append(f"  In local uploads: {check['in_local_uploads']}")
                report_lines.append(f"  Registry entry: {'Yes' if check['registry_entry'] else 'No'}")
                report_lines.append(f"  Zenodo matches: {check['zenodo_matches']}")
                report_lines.append("")
        
        # Recommendations
        report_lines.append("RECOMMENDATIONS")
        report_lines.append("-" * 40)
        if duplicates:
            report_lines.append("1. Review title duplicates and consider merging or deleting duplicates")
            report_lines.append("2. Use --delete-duplicates flag to remove duplicates (with confirmation)")
        if mismatches:
            report_lines.append("3. Update registry to match Zenodo state")
            report_lines.append("4. Investigate missing depositions")
        if not duplicates and not mismatches:
            report_lines.append("1. No duplicates found - system is clean!")
        
        report_lines.append("")
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)
    
    def save_report(self, report: str, filename: str = None):
        """Save report to file."""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = self.paths.duplicate_report_path(timestamp)
        else:
            if os.path.isabs(filename):
                report_path = filename
            else:
                report_path = os.path.join(self.duplicates_reports_dir, filename)
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        self.logger.log_info(f"Duplicate check report saved to {report_path}")
        return report_path
    
    def run_duplicate_check(self, specific_files: List[str] = None, 
                           report_only: bool = True) -> Dict[str, Any]:
        """Run comprehensive duplicate check."""
        self.logger.log_info("Starting comprehensive duplicate check...")
        
        # Load all data
        self.load_local_uploads()
        self.load_zenodo_depositions()
        self.registry_entries = self.load_uploads_registry()
        
        # Find duplicates and mismatches
        title_duplicates = self.find_title_duplicates()
        registry_mismatches = self.find_registry_mismatches()
        
        # Check specific files if requested
        specific_checks = None
        if specific_files:
            specific_checks = self.check_specific_files(specific_files)
        
        # Generate report
        report = self.generate_report(title_duplicates, registry_mismatches, specific_checks)
        
        # Save report
        report_path = self.save_report(report)
        
        # Print summary
        print(report)
        
        return {
            'title_duplicates': title_duplicates,
            'registry_mismatches': registry_mismatches,
            'specific_checks': specific_checks,
            'report_path': report_path,
            'summary': {
                'local_uploads': len(self.local_uploads),
                'zenodo_depositions': len(self.zenodo_depositions),
                'title_duplicates_count': len(title_duplicates),
                'registry_mismatches_count': len(registry_mismatches),
                'hours_back': self.hours_back,
                'cache_ttl_minutes': self.cache_ttl_minutes if self.use_cache else None,
            }
        }


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Comprehensive duplicate detection for Zenodo uploads"
    )
    parser.add_argument(
        '--sandbox',
        action='store_true',
        default=True,
        help='Check sandbox Zenodo (default: True)'
    )
    parser.add_argument(
        '--production',
        action='store_true',
        help='Check production Zenodo (overrides --sandbox)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        default='output',
        help='Output directory for reports (default: output)'
    )
    parser.add_argument(
        '--check-files',
        help='Comma-separated list of specific files to check (e.g., FGDC-1,FGDC-2)'
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        default=True,
        help='Generate report only, do not delete duplicates (default: True)'
    )
    parser.add_argument(
        '--hours-back',
        type=int,
        default=6,
        help='Limit Zenodo lookup to records modified within the last N hours (default: 6)'
    )
    parser.add_argument(
        '--cache-ttl',
        type=int,
        default=15,
        help='Reuse cached Zenodo responses for N minutes (default: 15)'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable caching of Zenodo API responses'
    )
    default_logs = default_log_dir("duplicates")
    parser.add_argument(
        '--log-dir',
        default=default_logs,
        help=f'Directory for log files (default: {default_logs})'
    )
    
    args = parser.parse_args()
    
    if args.hours_back <= 0:
        print("❌ --hours-back must be positive")
        exit(1)
    if not args.no_cache and args.cache_ttl <= 0:
        print("❌ --cache-ttl must be positive when caching is enabled")
        exit(1)
    
    # Determine environment
    sandbox = not args.production
    
    # Initialize logger
    initialize_logger(args.log_dir)
    logger = get_logger()
    
    try:
        # Create checker
        checker = DuplicateChecker(
            sandbox,
            args.output_dir,
            hours_back=args.hours_back,
            cache_ttl_minutes=args.cache_ttl,
            use_cache=not args.no_cache,
        )
        
        # Parse specific files if provided
        specific_files = None
        if args.check_files:
            specific_files = [f.strip() for f in args.check_files.split(',')]
        
        # Run duplicate check
        logger.log_info(f"Starting duplicate check in {'sandbox' if sandbox else 'production'} Zenodo...")
        results = checker.run_duplicate_check(specific_files, args.report_only)
        
        # Exit with appropriate code
        if results['summary']['title_duplicates_count'] > 0 or results['summary']['registry_mismatches_count'] > 0:
            logger.log_info("Duplicate check completed with issues found")
            exit(1)
        else:
            logger.log_info("Duplicate check completed - no issues found")
            exit(0)
            
    except Exception as e:
        logger.log_error(
            "duplicate_check", "main_process", "fatal_error",
            str(e), "Successful duplicate check process",
            "Review error details and fix issues"
        )
        print(f"Fatal error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
