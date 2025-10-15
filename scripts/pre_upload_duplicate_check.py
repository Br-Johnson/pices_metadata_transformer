#!/usr/bin/env python3
"""
Pre-upload duplicate check script that verifies records don't already exist on Zenodo
before attempting to upload them. This prevents duplicate uploads and saves API calls.
"""

import os
import json
import argparse
from datetime import datetime
from typing import Dict, List, Any, Set, Optional
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.zenodo_api import create_zenodo_client, ZenodoAPIError
from scripts.logger import initialize_logger, get_logger
from scripts.path_config import OutputPaths, default_log_dir


class PreUploadDuplicateChecker:
    """Checks for existing records on Zenodo before upload to prevent duplicates."""

    def __init__(self, sandbox: bool = True, output_dir: str = "output", allow_replacements: bool = False):
        self.sandbox = sandbox
        self.output_dir = output_dir
        self.paths = OutputPaths(output_dir)
        self.logger = get_logger()
        self.community_identifier = "pices"
        self.allow_replacements = allow_replacements

        if self.allow_replacements and not self.sandbox:
            raise ValueError("Duplicate replacements are only supported in the sandbox environment")

        # Initialize Zenodo client
        self.client = create_zenodo_client(sandbox)

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
        
    def load_existing_zenodo_records(self) -> Dict[str, Any]:
        """Load existing records from Zenodo to check against."""
        print("🔍 Loading existing records from Zenodo...")
        
        existing_records = {
            'titles': set(),
            'records': [],
            'title_to_record': {}
        }
        
        try:
            # Fetch published records in the target community
            published_hits = self.client.get_records_by_query(q=f"communities:{self.community_identifier}", size=200)
            self.logger.log_info(f"🔍 Retrieved {len(published_hits)} published records from community search")
            for hit in published_hits:
                metadata = hit.get('metadata', {})
                title = metadata.get('title', '').strip()
                if not title:
                    continue
                title_lower = title.lower()
                if title_lower in existing_records['title_to_record']:
                    continue
                communities = metadata.get('communities', [])
                record_info = {
                    'id': hit.get('id'),
                    'title': title,
                    'state': 'published',
                    'created': hit.get('created'),
                    'modified': hit.get('updated'),
                    'communities': [{'identifier': c.get('identifier')} for c in communities if c.get('identifier')]
                }
                existing_records['records'].append(record_info)
                existing_records['titles'].add(title_lower)
                existing_records['title_to_record'][title_lower] = record_info
            
            print(f"✅ Total existing records tracked: {len(existing_records['records'])}")
            return existing_records
            
        except ZenodoAPIError as e:
            print(f"❌ Error loading existing records: {e}")
            self.logger.log_error("pre_upload_check", "load_existing", "api_error", str(e), "Successful API call", "Check API credentials and network connection")
            return existing_records
        except Exception as e:
            print(f"❌ Unexpected error loading existing records: {e}")
            self.logger.log_error("pre_upload_check", "load_existing", "unexpected_error", str(e), "Successful record loading", "Review error details and fix issues")
            return existing_records
    
    def check_file_for_duplicates(self, json_file: str, existing_records: Dict[str, Any]) -> Dict[str, Any]:
        """Check a single JSON file for potential duplicates."""
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
            title_lower = title.lower()
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
        
        # Load existing records from Zenodo
        existing_records = self.load_existing_zenodo_records()
        
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
        
        print(f"   Checking {len(json_files)} files for duplicates...")
        
        # Check each file
        for i, json_file in enumerate(json_files, 1):
            if i % 100 == 0:
                print(f"   Progress: {i}/{len(json_files)} files checked")
            
            result = self.check_file_for_duplicates(json_file, existing_records)
            
            if result['safe_to_upload']:
                self.safe_to_upload.append(result)
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
            'timestamp': datetime.now().isoformat()
        }
    
    def _save_results(self, summary: Dict[str, Any]):
        """Save duplicate check results to file."""
        with open(self.duplicate_check_report, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"📄 Duplicate check report saved to: {self.duplicate_check_report}")

    def generate_upload_list(self) -> str:
        """Generate a list of files safe to upload."""
        safe_files = [f['file'] for f in self.safe_to_upload]
        
        # Save safe files list
        with open(self.paths.safe_to_upload_path, 'w', encoding='utf-8') as f:
            json.dump(safe_files, f, indent=2, ensure_ascii=False)
        
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
        if summary['summary']['duplicates_found'] > 0:
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
