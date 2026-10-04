#!/usr/bin/env python3
"""
Pre-upload duplicate check script that verifies records don't already exist on Zenodo
before attempting to upload them. This prevents duplicate uploads and saves API calls.
"""

import os
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Set, Optional
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.zenodo_api import create_zenodo_client, ZenodoAPIError
from scripts.logger import initialize_logger, get_logger
from scripts.path_config import OutputPaths, default_log_dir
from scripts.content_class_targets import require_singleton_operation, preflight_inputs
from scripts.upload_service import atomic_json, metadata_hash, prepare_metadata


class PreUploadDuplicateChecker:
    """Checks for existing records on Zenodo before upload to prevent duplicates."""

    def __init__(self, sandbox: bool = True, output_dir: str = "output", allow_replacements: bool = False,
                 canary_plan: Optional[str] = None):
        from scripts.sandbox_canary import SandboxCanary
        self.canary = SandboxCanary(canary_plan, 'sandbox' if sandbox else 'production') if canary_plan else None
        self.sandbox = sandbox
        self.output_dir = output_dir
        self.paths = OutputPaths(output_dir, "sandbox" if sandbox else "production")
        self.logger = get_logger()
        self.community_identifier = "pices"
        if allow_replacements:
            raise ValueError("Automatic replacement retired; adjudicate duplicates and reconcile draft IDs")
        self.allow_replacements = False

        if self.allow_replacements and not self.sandbox:
            raise ValueError("Duplicate replacements are only supported in the sandbox environment")

        # Selection (including --limit) must precede the client's constructor probe.
        self.client = None
        self._client_factory = create_zenodo_client

        # File paths
        self.zenodo_json_dir = self.paths.zenodo_json_dir
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.duplicate_check_report = self.paths.pre_upload_report_path(timestamp)
        environment = 'sandbox' if sandbox else 'production'
        self.replacement_plan_path = self.paths.replacement_plan_path(environment)

        # Results storage
        self.duplicates_found = []
        self.safe_to_upload = []
        self.check_errors = []
        self.existing_titles = set()
        self.existing_dois = set()
        self.replacement_candidates = []
        
    def load_existing_zenodo_records(self, selected_files=None) -> Dict[str, Any]:
        """Load existing records from Zenodo to check against."""
        preflight_inputs(self.paths, selected_files)
        # Invalidate prior authorization before refreshing: failures must fail closed.
        atomic_json(self.paths.safe_to_upload_path, {
            'environment': 'sandbox' if self.sandbox else 'production',
            'inventory_complete': False, 'files': [], 'metadata_hashes': {},
        })
        records = {'titles': set(), 'records': [], 'title_to_record': {}, 'identifiers': set()}
        if self.client is None:
            self.client = self._client_factory(self.sandbox)
        if getattr(self, 'canary', None) and self.client.base_url != self.canary.plan['origin']:
            raise ValueError('Canary client must use the exact sandbox origin')
        published = self.client.get_records_by_query(q=f"communities:{self.community_identifier}", size=200)
        drafts = self.client.get_all_my_depositions()
        for hit in published + drafts:
            metadata = hit.get('metadata', {})
            title = metadata.get('title', '').strip()
            if not title:
                raise ValueError('Remote record lacks title; reconcile identity before upload')
            info = {'id': hit.get('id'), 'title': title, 'state': hit.get('state', 'published'),
                    'metadata': metadata, 'created': hit.get('created'), 'submitted': hit.get('submitted')}
            key = title.casefold()
            records['titles'].add(key)
            records['title_to_record'].setdefault(key, info)
            records['records'].append(info)
            for identifier in self._identifiers(metadata):
                records['identifiers'].add(identifier)
        records['inventory_complete'] = True
        return records

    @staticmethod
    def _identifiers(metadata):
        identifiers = [metadata.get('doi'), metadata.get('prereserve_doi', {}).get('doi')]
        identifiers += [link.get('identifier') for link in metadata.get('related_identifiers', [])
                        if link.get('relation') in ('isAlternateIdentifier', 'isIdenticalTo')]
        return {str(value).lower().removeprefix('https://doi.org/').removeprefix('http://doi.org/')
                for value in identifiers if value}

    def check_file_for_duplicates(self, json_file: str, existing_records: Dict[str, Any]) -> Dict[str, Any]:
        """Check a single JSON file for potential duplicates."""
        require_singleton_operation(json_file=json_file, paths=self.paths)
        try:
            # Load the JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = data.get('metadata', {})
            title = metadata.get('title', '').strip()
            filename = os.path.basename(json_file)
            
            if not title:
                return {
                    'file': filename,
                    'safe_to_upload': False,
                    'reason': 'No title found in metadata',
                    'duplicate_type': 'missing_title'
                }
            
            # Check for exact title duplicates
            if not existing_records.get('inventory_complete'):
                raise ValueError('Duplicate inventory incomplete')
            if self.canary:
                from scripts.upload_service import read_json
                historical_ids = self.canary.check_inventory(json_file, self.paths, existing_records,
                    read_json(self.paths.uploads_registry_path, {}))
                return {'file': filename, 'safe_to_upload': True, 'title': title,
                        'reason': 'Exact sandbox canary plan; own-run ledger remains strict',
                        'historical_duplicate_ids': historical_ids}
            title_lower = title.casefold()
            if title_lower in existing_records['titles']:
                # Get the existing record with this title
                existing_record = existing_records['title_to_record'].get(title_lower)

                if self.allow_replacements and existing_record:
                    base_name = os.path.splitext(filename)[0]
                    replacement_entry = {
                        'file': filename,
                        'base_name': base_name,
                        'title': title,
                        'existing_deposition_id': existing_record.get('id'),
                        'existing_record': existing_record,
                        'timestamp': datetime.now().isoformat()
                    }
                    self.replacement_candidates.append(replacement_entry)

                    return {
                        'file': filename,
                        'safe_to_upload': True,
                        'reason': 'Exact title duplicate will be replaced in sandbox',
                        'duplicate_type': 'exact_title_duplicate',
                        'existing_record': existing_record,
                        'title': title,
                        'replacement_planned': True
                    }

                return {
                    'file': filename,
                    'safe_to_upload': False,
                    'reason': f'Exact title match found on Zenodo',
                    'duplicate_type': 'exact_title_duplicate',
                    'existing_record': existing_record,
                    'title': title
                }
            
            if self._identifiers(metadata) & existing_records.get('identifiers', set()):
                return {'file': filename, 'safe_to_upload': False,
                        'reason': 'Persistent identifier match requires human adjudication',
                        'duplicate_type': 'identifier_duplicate', 'title': title}
            # Check for similar titles (fuzzy matching)
            # Safe to upload
            return {
                'file': filename,
                'safe_to_upload': True,
                'reason': 'No duplicates found',
                'title': title
            }
            
        except Exception as e:
            return {
                'file': os.path.basename(json_file),
                'safe_to_upload': False,
                'reason': f'Error checking file: {str(e)}',
                'duplicate_type': 'check_error'
            }
    
    def _find_similar_titles(self, title: str, existing_titles: Set[str]) -> List[str]:
        """Find similar titles using basic string matching."""
        similar = []
        
        # Simple similarity check - titles that are very similar
        for existing_title in existing_titles:
            # Check if one title contains the other (for very similar titles)
            if (len(title) > 10 and len(existing_title) > 10 and 
                (title in existing_title or existing_title in title)):
                similar.append(existing_title)
            # Check for high character overlap
            elif self._calculate_similarity(title, existing_title) > 0.8:
                similar.append(existing_title)
        
        return similar[:3]  # Return up to 3 similar titles
    
    def _calculate_similarity(self, title1: str, title2: str) -> float:
        """Calculate simple string similarity."""
        if not title1 or not title2:
            return 0.0
        
        # Simple character overlap calculation
        set1 = set(title1.lower())
        set2 = set(title2.lower())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def check_all_files(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Check all JSON files for duplicates."""
        print(f"🔍 Starting pre-upload duplicate check...")
        print(f"   Environment: {'sandbox' if self.sandbox else 'production'}")
        
        # Get all JSON files
        json_files = []
        if os.path.exists(self.zenodo_json_dir):
            for filename in os.listdir(self.zenodo_json_dir):
                if filename.endswith('.json'):
                    json_files.append(os.path.join(self.zenodo_json_dir, filename))
        
        json_files.sort()
        
        if limit:
            json_files = json_files[:limit]
            print(f"   Limited to {limit} files for testing")
        
        # A limited singleton selection does not select retained sibling aliases.
        preflight_inputs(self.paths, json_files)
        existing_records = self.load_existing_zenodo_records(json_files)

        print(f"   Checking {len(json_files)} files for duplicates...")
        
        # Check each file
        for i, json_file in enumerate(json_files, 1):
            if i % 100 == 0:
                print(f"   Progress: {i}/{len(json_files)} files checked")
            
            result = self.check_file_for_duplicates(json_file, existing_records)
            
            if result['safe_to_upload']:
                self.safe_to_upload.append(result)
                existing_records['titles'].add(result['title'].casefold())
                existing_records['title_to_record'][result['title'].casefold()] = {'title': result['title'], 'state': 'local_candidate'}
                with open(json_file, encoding='utf-8') as local_file:
                    local_metadata = json.load(local_file)['metadata']
                existing_records['identifiers'].update(self._identifiers(local_metadata))
            else:
                self.duplicates_found.append(result)
                if result.get('duplicate_type') == 'check_error':
                    self.check_errors.append(result)
        
        # Generate summary
        summary = self._generate_summary()
        
        # Save results
        self._save_results(summary)
        
        # Generate already uploaded list for filtering
        self.generate_already_uploaded_list(existing_records)
        
        # Generate pre-filter list for transformation
        self.generate_pre_filter_list(existing_records)

        # Persist replacement plan when applicable
        self.save_replacement_plan()

        return summary
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate summary of duplicate check results."""
        total_files = len(self.safe_to_upload) + len(self.duplicates_found)
        
        # Count duplicate types
        duplicate_types = {}
        for duplicate in self.duplicates_found:
            dup_type = duplicate.get('duplicate_type', 'unknown')
            duplicate_types[dup_type] = duplicate_types.get(dup_type, 0) + 1
        
        return {
            'summary': {
                'total_files_checked': total_files,
                'safe_to_upload': len(self.safe_to_upload),
                'duplicates_found': len(self.duplicates_found),
                'check_errors': len(self.check_errors),
                'duplicate_rate': (len(self.duplicates_found) / total_files * 100) if total_files > 0 else 0,
                'environment': 'sandbox' if self.sandbox else 'production',
                'replacements_planned': len(self.replacement_candidates)
            },
            'duplicate_types': duplicate_types,
            'safe_to_upload_files': [f['file'] for f in self.safe_to_upload],
            'duplicate_files': self.duplicates_found,
            'replacement_candidates': self.replacement_candidates,
            'check_errors': self.check_errors,
            'timestamp': datetime.now().isoformat(),
            **({'sandbox_canary': self.canary.binding,
                  'historical_duplicate_exceptions': {f['file']: f.get('historical_duplicate_ids', [])
                                                    for f in self.safe_to_upload}} if self.canary else {})
        }
    
    def _save_results(self, summary: Dict[str, Any]):
        """Save duplicate check results to file."""
        with open(self.duplicate_check_report, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Duplicate check report saved to: {self.duplicate_check_report}")

    def generate_upload_list(self) -> str:
        """Generate a list of files safe to upload."""
        safe_files = [f['file'] for f in self.safe_to_upload]
        preflight_inputs(self.paths, [os.path.join(self.zenodo_json_dir, name) for name in safe_files])
        if self.canary:
            from scripts.upload_service import ledger_lock, read_json
            with ledger_lock(self.paths):
                registry = read_json(self.paths.uploads_registry_path, {})
                self.canary.registry(registry)
                registry['_sandbox_canary'] = self.canary.binding
                atomic_json(self.paths.uploads_registry_path, registry)
                create_files = [name for name in safe_files if Path(name).stem not in registry]
        
        # Save safe files list
        with open(self.paths.safe_to_upload_path, 'w', encoding='utf-8') as f:
            json.dump({'environment': 'sandbox' if self.sandbox else 'production',
                       **({'sandbox_canary': self.canary.binding, 'canary_create_files': create_files} if self.canary else {}),
                       'inventory_complete': True, 'files': safe_files,
                       'checked_at': datetime.now(timezone.utc).isoformat(),
                       'valid_until': (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
                       'metadata_hashes': {name: metadata_hash(prepare_metadata(os.path.join(self.zenodo_json_dir, name), self.paths)[0]) for name in safe_files}}, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Safe to upload list saved to: {self.paths.safe_to_upload_path}")
        return self.paths.safe_to_upload_path
    
    def generate_already_uploaded_list(self, existing_records: Dict[str, Any]) -> str:
        """Generate a list of records already uploaded to Zenodo for filtering."""
        already_uploaded = {
            'total_records': len(existing_records['records']),
            'environment': 'sandbox' if self.sandbox else 'production',
            'check_date': datetime.now().isoformat(),
            'community': 'pices',
            'records': existing_records['records']
        }
        
        # Save already uploaded list
        with open(self.paths.already_uploaded_path, 'w', encoding='utf-8') as f:
            json.dump(already_uploaded, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Already uploaded records list saved to: {self.paths.already_uploaded_path}")
        return self.paths.already_uploaded_path
    
    def generate_pre_filter_list(self, existing_records: Dict[str, Any]) -> str:
        """Generate a pre-filter list for transformation to skip already uploaded files."""
        # Create a simple list of titles that are already uploaded
        already_uploaded_titles = [record['title'].lower() for record in existing_records['records']]
        
        pre_filter = {
            'total_records': len(already_uploaded_titles),
            'environment': 'sandbox' if self.sandbox else 'production',
            'check_date': datetime.now().isoformat(),
            'community': 'pices',
            'already_uploaded_titles': already_uploaded_titles,
            'description': 'List of titles already uploaded to PICES community on Zenodo - use to skip transformation'
        }
        
        # Save pre-filter list
        with open(self.paths.pre_filter_path, 'w', encoding='utf-8') as f:
            json.dump(pre_filter, f, indent=2, ensure_ascii=False)
        
        print(f"📋 Pre-filter list saved to: {self.paths.pre_filter_path}")
        return self.paths.pre_filter_path

    def save_replacement_plan(self) -> Optional[str]:
        """Persist duplicate replacement plan for downstream upload logic."""
        if not self.allow_replacements:
            return None

        plan_payload = {
            'generated_at': datetime.now().isoformat(),
            'environment': 'sandbox' if self.sandbox else 'production',
            'replacements': self.replacement_candidates,
        }

        with open(self.replacement_plan_path, 'w', encoding='utf-8') as fh:
            json.dump(plan_payload, fh, indent=2, ensure_ascii=False)

        print(f"📄 Replacement plan saved to: {self.replacement_plan_path}")
        return self.replacement_plan_path


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Check for duplicate records on Zenodo before upload"
    )
    parser.add_argument(
        '--sandbox',
        action='store_true',
        default=True,
        help='Check against Zenodo sandbox (default: True)'
    )
    parser.add_argument(
        '--production',
        action='store_true',
        help='Check against production Zenodo (overrides --sandbox)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        default='output',
        help='Output directory (default: output)'
    )
    parser.add_argument(
        '--allow-replacements',
        action='store_true',
        help='Allow sandbox duplicate replacements and generate replacement plan'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        help='Limit number of files to check (for testing)'
    )
    default_logs = default_log_dir("pre_upload")
    parser.add_argument(
        '--log-dir',
        default=default_logs,
        help=f'Directory for log files (default: {default_logs})'
    )
    
    args = parser.parse_args()
    
    # Determine environment
    sandbox = not args.production

    if args.allow_replacements and not sandbox:
        print("❌ Duplicate replacements are only allowed in sandbox runs")
        return 1

    # Initialize logger
    initialize_logger(args.log_dir)
    logger = get_logger()

    try:
        # Create checker
        checker = PreUploadDuplicateChecker(sandbox, args.output_dir, allow_replacements=args.allow_replacements)
        
        # Run duplicate check
        logger.log_info(f"Starting pre-upload duplicate check in {'sandbox' if sandbox else 'production'} Zenodo...")
        summary = checker.check_all_files(args.limit)
        
        # Generate upload list
        safe_files_path = checker.generate_upload_list()
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"PRE-UPLOAD DUPLICATE CHECK SUMMARY")
        print(f"{'='*80}")
        print(f"Total files checked: {summary['summary']['total_files_checked']}")
        print(f"Safe to upload: {summary['summary']['safe_to_upload']}")
        print(f"Duplicates found: {summary['summary']['duplicates_found']}")
        print(f"Check errors: {summary['summary']['check_errors']}")
        print(f"Duplicate rate: {summary['summary']['duplicate_rate']:.1f}%")
        if summary['summary'].get('replacements_planned'):
            print(f"Replacements planned (sandbox only): {summary['summary']['replacements_planned']}")

        if summary['duplicate_types']:
            print(f"\nDuplicate types:")
            for dup_type, count in summary['duplicate_types'].items():
                print(f"  {dup_type}: {count}")
        
        print(f"\nSafe to upload list: {safe_files_path}")
        print(f"Already uploaded list: {checker.paths.already_uploaded_path}")
        print(f"Pre-filter list: {checker.paths.pre_filter_path}")
        print(f"Duplicate check report: {checker.duplicate_check_report}")
        if checker.allow_replacements:
            print(f"Replacement plan: {checker.replacement_plan_path}")

        # Exit with appropriate code
        if summary['summary']['duplicates_found'] > 0 or summary['summary']['check_errors'] > 0:
            logger.log_info("Duplicate check completed with duplicates found")
            return 1  # Exit code 1 if duplicates found
        else:
            logger.log_info("Duplicate check completed - no duplicates found")
            return 0  # Exit code 0 if no duplicates
            
    except Exception as e:
        logger.log_error(
            "pre_upload_check", "main_process", "fatal_error",
            str(e), "Successful duplicate check process",
            "Review error details and fix issues"
        )
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
