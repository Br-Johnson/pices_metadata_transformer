"""
Validation script for transformed Zenodo JSON metadata.
Verifies compliance with Zenodo requirements and generates validation reports.
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
import dateutil.parser
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.logger import get_logger


class ZenodoValidator:
    """Validates Zenodo JSON metadata against requirements."""
    
    def __init__(self):
        self.logger = get_logger()
        self.validation_results = []
        self.required_fields = [
            'title', 'upload_type', 'publication_date', 'creators', 'description', 'access_right'
        ]
        self.required_creator_fields = ['name']
        self.valid_upload_types = [
            'publication', 'poster', 'presentation', 'dataset', 'image', 
            'video', 'software', 'lesson', 'physicalobject', 'other'
        ]
        self.valid_access_rights = ['open', 'embargoed', 'restricted', 'closed']
        self.valid_relations = [
            'isCitedBy', 'cites', 'isSupplementTo', 'isSupplementedBy',
            'isContinuedBy', 'continues', 'isDescribedBy', 'describes',
            'hasMetadata', 'isMetadataFor', 'isNewVersionOf', 'isPreviousVersionOf',
            'isPartOf', 'hasPart', 'isReferencedBy', 'references',
            'isDocumentedBy', 'documents', 'isCompiledBy', 'compiles',
            'isVariantFormOf', 'isOriginalFormof', 'isIdenticalTo',
            'isAlternateIdentifier', 'isReviewedBy', 'reviews',
            'isDerivedFrom', 'isSourceOf', 'requires', 'isRequiredBy',
            'isObsoletedBy', 'obsoletes'
        ]
        
        # All possible Zenodo fields for comprehensive tracking
        self.all_zenodo_fields = [
            'title', 'upload_type', 'publication_date', 'creators', 'description', 'access_right',
            'license', 'communities', 'keywords', 'notes', 'related_identifiers', 'contributors',
            'references', 'subjects', 'grants', 'locations', 'dates', 'method', 'access_conditions',
            'embargo_date', 'version', 'language', 'imprint_publisher', 'imprint_place', 'imprint_isbn',
            'partof_title', 'partof_pages', 'journal_title', 'journal_volume', 'journal_issue',
            'journal_pages', 'conference_title', 'conference_acronym', 'conference_dates',
            'conference_place', 'conference_url', 'conference_session', 'conference_session_part',
            'thesis_supervisors', 'thesis_university'
        ]
        
        # Field length limits (characters)
        self.field_limits = {
            'title': 250,
            'description': 10000,
            'notes': 20000,
            'method': 20000,
            'access_conditions': 20000,
            'version': 50,
            'language': 10,
            'license': 50,
            'imprint_publisher': 250,
            'imprint_place': 250,
            'imprint_isbn': 50,
            'partof_title': 250,
            'partof_pages': 50,
            'journal_title': 250,
            'journal_volume': 50,
            'journal_issue': 50,
            'journal_pages': 50,
            'conference_title': 250,
            'conference_acronym': 50,
            'conference_dates': 50,
            'conference_place': 250,
            'conference_url': 500,
            'conference_session': 50,
            'conference_session_part': 50,
            'thesis_university': 250
        }
        
        # Array field limits
        self.array_limits = {
            'creators': 1000,
            'contributors': 1000,
            'keywords': 100,
            'related_identifiers': 100,
            'references': 1000,
            'subjects': 100,
            'grants': 100,
            'locations': 100,
            'dates': 100,
            'communities': 10,
            'thesis_supervisors': 100
        }
    
    def validate_file(self, json_path: str) -> Dict[str, Any]:
        """Validate a single Zenodo JSON file."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'metadata' not in data:
                return self._create_validation_result(
                    json_path, False, "Missing 'metadata' key in JSON structure"
                )
            
            metadata = data['metadata']
            issues = []
            warnings = []
            
            # Track field coverage and character counts
            field_coverage = self._analyze_field_coverage(metadata)
            character_analysis = self._analyze_character_counts(metadata)
            
            # Validate required fields
            for field in self.required_fields:
                if field not in metadata:
                    issues.append(f"Missing required field: {field}")
                elif not metadata[field]:
                    issues.append(f"Empty required field: {field}")
            
            # Validate specific fields
            self._validate_title(metadata, issues, warnings)
            self._validate_upload_type(metadata, issues, warnings)
            self._validate_publication_date(metadata, issues, warnings)
            self._validate_creators(metadata, issues, warnings)
            self._validate_description(metadata, issues, warnings)
            self._validate_access_right(metadata, issues, warnings)
            self._validate_license(metadata, issues, warnings)
            self._validate_keywords(metadata, issues, warnings)
            self._validate_related_identifiers(metadata, issues, warnings)
            self._validate_contributors(metadata, issues, warnings)
            self._validate_communities(metadata, issues, warnings)
            
            # Validate field length limits
            self._validate_field_limits(metadata, issues, warnings)
            
            is_valid = len(issues) == 0
            
            result = self._create_validation_result(
                json_path, is_valid, 
                f"Found {len(issues)} errors and {len(warnings)} warnings",
                issues=issues, warnings=warnings,
                field_coverage=field_coverage,
                character_analysis=character_analysis
            )
            
            self.validation_results.append(result)
            return result
            
        except json.JSONDecodeError as e:
            return self._create_validation_result(
                json_path, False, f"Invalid JSON: {str(e)}"
            )
        except Exception as e:
            return self._create_validation_result(
                json_path, False, f"Validation error: {str(e)}"
            )
    
    def _create_validation_result(self, file_path: str, is_valid: bool, 
                                message: str, issues: List[str] = None, 
                                warnings: List[str] = None, field_coverage: Dict = None,
                                character_analysis: Dict = None) -> Dict[str, Any]:
        """Create a validation result object."""
        return {
            'file': os.path.basename(file_path),
            'file_path': file_path,
            'is_valid': is_valid,
            'message': message,
            'issues': issues or [],
            'warnings': warnings or [],
            'field_coverage': field_coverage or {},
            'character_analysis': character_analysis or {},
            'timestamp': datetime.now().isoformat()
        }
    
    def _validate_title(self, metadata: Dict[str, Any], issues: List[str], warnings: List[str]):
        """Validate title field."""
        title = metadata.get('title', '')
        if not title or not title.strip():
            issues.append("Title is empty or missing")
        elif len(title) > 200:
            warnings.append(f"Title is very long ({len(title)} characters)")
    
    def _validate_upload_type(self, metadata: Dict[str, Any], issues: List[str], warnings: List[str]):
        """Validate upload_type field."""
        upload_type = metadata.get('upload_type', '')
        if upload_type not in self.valid_upload_types:
            issues.append(f"Invalid upload_type: {upload_type}")
    
    def _validate_publication_date(self, metadata: Dict[str, Any], issues: List[str], warnings: List[str]):
        """Validate publication_date field."""
        pub_date = metadata.get('publication_date', '')
        if not pub_date:
            issues.append("Publication date is missing")
        else:
            try:
                # Try to parse as ISO date
                dateutil.parser.parse(pub_date)
                # Check if it's in YYYY-MM-DD format
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', pub_date):
                    warnings.append(f"Publication date not in YYYY-MM-DD format: {pub_date}")
            except (ValueError, TypeError):
                issues.append(f"Invalid publication date format: {pub_date}")
    
    def _validate_creators(self, metadata: Dict[str, Any], issues: List[str], warnings: List[str]):
        """Validate creators field."""
        creators = metadata.get('creators', [])
        if not creators:
            issues.append("No creators specified")
        else:
            for i, creator in enumerate(creators):
                if not isinstance(creator, dict):
                    issues.append(f"Creator {i+1} is not a dictionary")
                    continue
                
                # Check required creator fields
                for field in self.required_creator_fields:
                    if field not in creator:
                        issues.append(f"Creator {i+1} missing required field: {field}")
                    elif not creator[field]:
                        issues.append(f"Creator {i+1} has empty {field}")
                
                # Validate name format
                name = creator.get('name', '')
                if name and ',' not in name:
                    warnings.append(f"Creator {i+1} name not in 'Family, Given' format: {name}")
                
                # Check for valid optional fields
                valid_creator_fields = ['name', 'affiliation', 'orcid', 'gnd', 'type']
                for field in creator:
                    if field not in valid_creator_fields:
                        warnings.append(f"Creator {i+1} has unknown field: {field}")
    
    def _validate_description(self, metadata: Dict[str, Any], issues: List[str], warnings: List[str]):
        """Validate description field."""
        description = metadata.get('description', '')
        if not description or not description.strip():
            issues.append("Description is empty or missing")
        elif len(description) < 10:
            warnings.append("Description is very short")
        elif len(description) > 10000:
            warnings.append(f"Description is very long ({len(description)} characters)")
    
    def _validate_access_right(self, metadata: Dict[str, Any], issues: List[str], warnings: List[str]):
        """Validate access_right field."""
        access_right = metadata.get('access_right', '')
        if access_right not in self.valid_access_rights:
            issues.append(f"Invalid access_right: {access_right}")
        
        # Check access_conditions for restricted access
        if access_right == 'restricted':
            if 'access_conditions' not in metadata or not metadata['access_conditions']:
                issues.append("access_conditions required for restricted access")
    
    def _validate_license(self, metadata: Dict[str, Any], issues: List[str], warnings: List[str]):
        """Validate license field."""
        access_right = metadata.get('access_right', '')
        license_field = metadata.get('license', '')
        
        if access_right in ['open', 'embargoed']:
            if not license_field:
                issues.append("License required for open/embargoed access")
            elif not self._is_valid_license(license_field):
                warnings.append(f"Unknown license: {license_field}")
    
    def _is_valid_license(self, license_id: str) -> bool:
        """Check if license ID is valid (basic check)."""
        # Common license patterns
        valid_licenses = [
            'cc-zero', 'cc-by-4.0', 'cc-by-sa-4.0', 'cc-by-nc-4.0',
            'mit', 'apache-2.0', 'gpl-3.0', 'gpl-2.0', 'bsd-3-clause',
            'lgpl-3.0', 'mpl-2.0', 'epl-1.0', 'cddl-1.0'
        ]
        return license_id in valid_licenses
    
    def _validate_keywords(self, metadata: Dict[str, Any], issues: List[str], warnings: List[str]):
        """Validate keywords field."""
        keywords = metadata.get('keywords', [])
        if not isinstance(keywords, list):
            issues.append("Keywords must be a list")
        else:
            for i, keyword in enumerate(keywords):
                if not isinstance(keyword, str):
                    issues.append(f"Keyword {i+1} is not a string")
                elif not keyword.strip():
                    issues.append(f"Keyword {i+1} is empty")
                elif len(keyword) > 100:
                    warnings.append(f"Keyword {i+1} is very long: {keyword}")
    
    def _validate_related_identifiers(self, metadata: Dict[str, Any], issues: List[str], warnings: List[str]):
        """Validate related_identifiers field."""
        related_ids = metadata.get('related_identifiers', [])
        if not isinstance(related_ids, list):
            issues.append("Related identifiers must be a list")
        else:
            for i, rel_id in enumerate(related_ids):
                if not isinstance(rel_id, dict):
                    issues.append(f"Related identifier {i+1} is not a dictionary")
                    continue
                
                # Check required fields
                if 'identifier' not in rel_id:
                    issues.append(f"Related identifier {i+1} missing 'identifier' field")
                elif 'relation' not in rel_id:
                    issues.append(f"Related identifier {i+1} missing 'relation' field")
                else:
                    # Validate relation
                    if rel_id['relation'] not in self.valid_relations:
                        issues.append(f"Related identifier {i+1} has invalid relation: {rel_id['relation']}")
                    
                    # Validate identifier format
                    identifier = rel_id['identifier']
                    if not self._is_valid_identifier(identifier):
                        warnings.append(f"Related identifier {i+1} may not be valid: {identifier}")
    
    def _is_valid_identifier(self, identifier: str) -> bool:
        """Check if identifier is valid (DOI, URL, etc.)."""
        # Check for DOI
        if re.match(r'^10\.\d+/', identifier):
            return True
        
        # Check for URL
        try:
            result = urlparse(identifier)
            return all([result.scheme, result.netloc])
        except:
            pass
        
        # Check for other common identifiers
        if re.match(r'^(isbn|issn|pmid|arxiv):', identifier.lower()):
            return True
        
        return False
    
    def _validate_contributors(self, metadata: Dict[str, Any], issues: List[str], warnings: List[str]):
        """Validate contributors field."""
        contributors = metadata.get('contributors', [])
        if not isinstance(contributors, list):
            issues.append("Contributors must be a list")
        else:
            valid_types = [
                'ContactPerson', 'DataCollector', 'DataCurator', 'DataManager',
                'Distributor', 'Editor', 'HostingInstitution', 'Producer',
                'ProjectLeader', 'ProjectManager', 'ProjectMember',
                'RegistrationAgency', 'RegistrationAuthority', 'RelatedPerson',
                'Researcher', 'ResearchGroup', 'RightsHolder', 'Supervisor',
                'Sponsor', 'WorkPackageLeader', 'Other'
            ]
            
            for i, contributor in enumerate(contributors):
                if not isinstance(contributor, dict):
                    issues.append(f"Contributor {i+1} is not a dictionary")
                    continue
                
                # Check required fields
                if 'name' not in contributor:
                    issues.append(f"Contributor {i+1} missing 'name' field")
                elif 'type' not in contributor:
                    issues.append(f"Contributor {i+1} missing 'type' field")
                elif contributor['type'] not in valid_types:
                    issues.append(f"Contributor {i+1} has invalid type: {contributor['type']}")
    
    def _validate_communities(self, metadata: Dict[str, Any], issues: List[str], warnings: List[str]):
        """Validate communities field."""
        communities = metadata.get('communities', [])
        if not isinstance(communities, list):
            issues.append("Communities must be a list")
        else:
            for i, community in enumerate(communities):
                if not isinstance(community, dict):
                    issues.append(f"Community {i+1} is not a dictionary")
                elif 'identifier' not in community:
                    issues.append(f"Community {i+1} missing 'identifier' field")
    
    def _analyze_field_coverage(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze which Zenodo fields are present in the metadata."""
        coverage = {
            'total_possible_fields': len(self.all_zenodo_fields),
            'fields_present': [],
            'fields_missing': [],
            'coverage_percentage': 0.0,
            'required_fields_present': 0,
            'required_fields_missing': [],
            'optional_fields_present': 0,
            'optional_fields_missing': []
        }
        
        for field in self.all_zenodo_fields:
            if field in metadata and metadata[field]:
                coverage['fields_present'].append(field)
                if field in self.required_fields:
                    coverage['required_fields_present'] += 1
                else:
                    coverage['optional_fields_present'] += 1
            else:
                coverage['fields_missing'].append(field)
                if field in self.required_fields:
                    coverage['required_fields_missing'].append(field)
                else:
                    coverage['optional_fields_missing'].append(field)
        
        coverage['coverage_percentage'] = (len(coverage['fields_present']) / len(self.all_zenodo_fields)) * 100
        
        return coverage
    
    def _analyze_character_counts(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze character counts in text fields."""
        analysis = {
            'total_characters': 0,
            'field_character_counts': {},
            'largest_fields': [],
            'fields_over_limit': [],
            'text_density': {}
        }
        
        # Count characters in all text fields
        for field, value in metadata.items():
            if isinstance(value, str):
                char_count = len(value)
                analysis['field_character_counts'][field] = char_count
                analysis['total_characters'] += char_count
                
                # Check if over limit
                if field in self.field_limits and char_count > self.field_limits[field]:
                    analysis['fields_over_limit'].append({
                        'field': field,
                        'count': char_count,
                        'limit': self.field_limits[field],
                        'excess': char_count - self.field_limits[field]
                    })
            
            elif isinstance(value, list):
                # Count characters in list items
                list_chars = 0
                for item in value:
                    if isinstance(item, str):
                        list_chars += len(item)
                    elif isinstance(item, dict):
                        # Count characters in dictionary values
                        for v in item.values():
                            if isinstance(v, str):
                                list_chars += len(v)
                
                if list_chars > 0:
                    analysis['field_character_counts'][field] = list_chars
                    analysis['total_characters'] += list_chars
        
        # Find largest fields
        sorted_fields = sorted(analysis['field_character_counts'].items(), 
                             key=lambda x: x[1], reverse=True)
        analysis['largest_fields'] = sorted_fields[:10]
        
        # Calculate text density (characters per field)
        if analysis['field_character_counts']:
            avg_chars = analysis['total_characters'] / len(analysis['field_character_counts'])
            analysis['text_density'] = {
                'average_chars_per_field': avg_chars,
                'fields_with_high_density': [
                    (field, count) for field, count in analysis['field_character_counts'].items()
                    if count > avg_chars * 2
                ]
            }
        
        return analysis
    
    def _validate_field_limits(self, metadata: Dict[str, Any], issues: List[str], warnings: List[str]):
        """Validate field length limits."""
        for field, limit in self.field_limits.items():
            if field in metadata:
                value = metadata[field]
                if isinstance(value, str):
                    if len(value) > limit:
                        issues.append(f"Field '{field}' exceeds character limit: {len(value)} > {limit}")
                elif isinstance(value, list):
                    if len(value) > self.array_limits.get(field, 1000):
                        issues.append(f"Field '{field}' exceeds array limit: {len(value)} > {self.array_limits.get(field, 1000)}")
    
    def validate_directory(self, directory_path: str) -> Dict[str, Any]:
        """Validate all JSON files in a directory."""
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        json_files = [f for f in os.listdir(directory_path) if f.endswith('.json')]
        
        if not json_files:
            raise ValueError(f"No JSON files found in {directory_path}")
        
        self.logger.log_info(f"Validating {len(json_files)} JSON files in {directory_path}")
        
        for json_file in json_files:
            json_path = os.path.join(directory_path, json_file)
            self.validate_file(json_path)
        
        return self._generate_validation_summary()
    
    def _generate_validation_summary(self) -> Dict[str, Any]:
        """Generate validation summary."""
        total_files = len(self.validation_results)
        valid_files = sum(1 for r in self.validation_results if r['is_valid'])
        invalid_files = total_files - valid_files
        
        total_issues = sum(len(r['issues']) for r in self.validation_results)
        total_warnings = sum(len(r['warnings']) for r in self.validation_results)
        
        # Count issues by type
        issue_types = {}
        for result in self.validation_results:
            for issue in result['issues']:
                issue_type = issue.split(':')[0] if ':' in issue else issue
                issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        # Analyze field coverage across all files
        field_coverage_stats = self._analyze_overall_field_coverage()
        character_stats = self._analyze_overall_character_counts()
        
        return {
            'summary': {
                'total_files': total_files,
                'valid_files': valid_files,
                'invalid_files': invalid_files,
                'total_issues': total_issues,
                'total_warnings': total_warnings,
                'validation_rate': (valid_files / total_files * 100) if total_files > 0 else 0
            },
            'issue_types': issue_types,
            'field_coverage_stats': field_coverage_stats,
            'character_stats': character_stats,
            'results': self.validation_results,
            'timestamp': datetime.now().isoformat()
        }
    
    def _analyze_overall_field_coverage(self) -> Dict[str, Any]:
        """Analyze field coverage across all files."""
        field_counts = {}
        total_coverage = 0
        
        for result in self.validation_results:
            if 'field_coverage' in result:
                coverage = result['field_coverage']
                total_coverage += coverage.get('coverage_percentage', 0)
                
                for field in coverage.get('fields_present', []):
                    field_counts[field] = field_counts.get(field, 0) + 1
        
        # Calculate coverage percentages for each field
        field_coverage_percentages = {}
        for field in self.all_zenodo_fields:
            count = field_counts.get(field, 0)
            percentage = (count / len(self.validation_results)) * 100 if self.validation_results else 0
            field_coverage_percentages[field] = {
                'count': count,
                'percentage': percentage,
                'is_required': field in self.required_fields
            }
        
        return {
            'average_coverage_percentage': total_coverage / len(self.validation_results) if self.validation_results else 0,
            'field_coverage_percentages': field_coverage_percentages,
            'most_common_fields': sorted(field_counts.items(), key=lambda x: x[1], reverse=True)[:10],
            'least_common_fields': sorted(field_counts.items(), key=lambda x: x[1])[:10]
        }
    
    def _analyze_overall_character_counts(self) -> Dict[str, Any]:
        """Analyze character counts across all files."""
        total_chars = 0
        field_char_totals = {}
        files_over_limit = 0
        
        for result in self.validation_results:
            if 'character_analysis' in result:
                analysis = result['character_analysis']
                total_chars += analysis.get('total_characters', 0)
                
                if analysis.get('fields_over_limit'):
                    files_over_limit += 1
                
                for field, count in analysis.get('field_character_counts', {}).items():
                    field_char_totals[field] = field_char_totals.get(field, 0) + count
        
        return {
            'total_characters_across_all_files': total_chars,
            'average_characters_per_file': total_chars / len(self.validation_results) if self.validation_results else 0,
            'files_with_fields_over_limit': files_over_limit,
            'field_character_totals': field_char_totals,
            'largest_fields_overall': sorted(field_char_totals.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def save_validation_report(self, output_path: str):
        """Save validation report to JSON file."""
        summary = self._generate_validation_summary()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        self.logger.log_info(f"Validation report saved to {output_path}")
        
        # Print summary to console
        print("\n=== Validation Summary ===")
        print(f"Total files: {summary['summary']['total_files']}")
        print(f"Valid files: {summary['summary']['valid_files']}")
        print(f"Invalid files: {summary['summary']['invalid_files']}")
        print(f"Validation rate: {summary['summary']['validation_rate']:.1f}%")
        print(f"Total issues: {summary['summary']['total_issues']}")
        print(f"Total warnings: {summary['summary']['total_warnings']}")
        
        if summary['issue_types']:
            print("\nTop issues:")
            for issue_type, count in sorted(summary['issue_types'].items(), 
                                          key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {issue_type}: {count}")


def validate_zenodo_file(json_path: str) -> Dict[str, Any]:
    """Validate a single Zenodo JSON file."""
    validator = ZenodoValidator()
    return validator.validate_file(json_path)


def validate_zenodo_directory(directory_path: str, output_path: str = None):
    """Validate all JSON files in a directory."""
    validator = ZenodoValidator()
    summary = validator.validate_directory(directory_path)
    
    if output_path:
        validator.save_validation_report(output_path)
    
    return summary


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python validate_zenodo.py <json_file_or_directory> [output_report.json]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    if os.path.isfile(input_path):
        result = validate_zenodo_file(input_path)
        print(f"File: {result['file']}")
        print(f"Valid: {result['is_valid']}")
        print(f"Message: {result['message']}")
        if result['issues']:
            print("Issues:")
            for issue in result['issues']:
                print(f"  - {issue}")
        if result['warnings']:
            print("Warnings:")
            for warning in result['warnings']:
                print(f"  - {warning}")
    else:
        validate_zenodo_directory(input_path, output_path)
