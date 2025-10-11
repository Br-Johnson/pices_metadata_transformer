"""
Core FGDC to Zenodo transformation script.
Implements complete crosswalk mapping with comprehensive error handling.
"""

import xml.etree.ElementTree as ET
import re
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse
import dateutil.parser
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.logger import get_logger
from scripts.enhanced_metrics import EnhancedMetricsCalculator


class FGDCToZenodoTransformer:
    """Transforms FGDC XML metadata to Zenodo JSON format."""
    
    def __init__(self):
        self.logger = get_logger()
        self.metrics_calculator = EnhancedMetricsCalculator()
        
        # Common license patterns
        self.license_patterns = {
            'cc-zero': [r'cc.?zero', r'public.?domain', r'no.?rights.?reserved', r'public.?domain'],
            'cc-by-4.0': [r'cc.?by.?4', r'creative.?commons.?attribution', r'cc.?by'],
            'cc-by-sa-4.0': [r'cc.?by.?sa.?4', r'creative.?commons.?sharealike', r'cc.?by.?sa'],
            'mit': [r'mit.?license', r'massachusetts.?institute.?of.?technology'],
            'apache-2.0': [r'apache.?2', r'apache.?license'],
            'gpl-3.0': [r'gpl.?3', r'gnu.?general.?public.?license.?3'],
            'open': [r'open.?access', r'freely.?available', r'no.?restrictions']
            # Note: Removed 'none' pattern to prevent invalid license values
        }
        
        # Organization patterns for creator detection
        self.org_patterns = [
            r'noaa', r'national.?oceanic', r'university.?of', r'institute',
            r'center', r'lab', r'department', r'ministry', r'agency',
            r'corporation', r'inc\.', r'ltd\.', r'corp\.'
        ]
    
    def transform_file(self, xml_path: str) -> Optional[Dict[str, Any]]:
        """Transform a single FGDC XML file to Zenodo JSON format."""
        try:
            # Read original FGDC file for character count
            with open(xml_path, 'r', encoding='utf-8', errors='ignore') as f:
                fgdc_content = f.read()
            fgdc_char_count = len(fgdc_content)
            
            # Parse XML
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            # Extract metadata
            zenodo_metadata = self._build_zenodo_metadata(root, xml_path)
            
            if zenodo_metadata:
                # Calculate character counts for actual data content only
                fgdc_data_chars = self._count_fgdc_data_content(fgdc_content)
                zenodo_data_chars = self._count_zenodo_data_content(zenodo_metadata)
                
                # Also calculate total JSON size for reference
                zenodo_json = json.dumps(zenodo_metadata, indent=2)
                zenodo_total_chars = len(zenodo_json)
                
                # Calculate enhanced metrics
                enhanced_metrics = self.metrics_calculator.calculate_comprehensive_metrics(
                    fgdc_content, zenodo_metadata, xml_path
                )
                
                # Legacy character analysis for backward compatibility
                char_difference = zenodo_data_chars - fgdc_data_chars
                char_ratio = zenodo_data_chars / fgdc_data_chars if fgdc_data_chars > 0 else 0
                
                self.logger.log_info(f"Successfully transformed {xml_path}")
                return {
                    "metadata": zenodo_metadata,
                    "original_fgdc_file": os.path.basename(xml_path),
                    "character_analysis": {
                        "fgdc_total_chars": fgdc_char_count,
                        "fgdc_data_chars": fgdc_data_chars,
                        "zenodo_total_chars": zenodo_total_chars,
                        "zenodo_data_chars": zenodo_data_chars,
                        "char_difference": char_difference,
                        "char_ratio": char_ratio,
                        "data_preservation_ratio": char_ratio
                    },
                    "enhanced_metrics": enhanced_metrics
                }
            else:
                self.logger.log_error(
                    xml_path, "root", "transformation_failed",
                    "XML parsed but no metadata generated", 
                    "Valid FGDC metadata structure",
                    "Check XML structure and required fields"
                )
                return None
                
        except ET.ParseError as e:
            self.logger.log_error(
                xml_path, "xml_parsing", "parse_error",
                str(e), "Valid XML format",
                "Fix XML syntax errors"
            )
            return None
        except Exception as e:
            self.logger.log_error(
                xml_path, "transformation", "unexpected_error",
                str(e), "Successful transformation",
                "Review error details and fix transformation logic"
            )
            return None
    
    def _build_zenodo_metadata(self, root: ET.Element, file_path: str) -> Optional[Dict[str, Any]]:
        """Build Zenodo metadata from FGDC root element."""
        try:
            # Required fields
            title = self._extract_title(root, file_path)
            if not title:
                return None
            
            creators = self._extract_creators(root, file_path)
            if not creators:
                return None
            
            publication_date = self._extract_publication_date(root, file_path)
            if not publication_date:
                return None
            
            description = self._extract_description(root, file_path)
            if not description:
                return None
            
            # Build base metadata
            metadata = {
                "title": title,
                "upload_type": "dataset",
                "publication_date": publication_date,
                "creators": creators,
                "description": description,
                "access_right": "open",  # Default, will be updated based on constraints
                "license": "cc-zero",    # Default for datasets
                "keywords": [],
                "notes": "",
                "related_identifiers": [],
                "contributors": [],
                "references": [],
                "communities": [{"identifier": "pices"}]
            }
            
            # Optional fields
            self._add_optional_fields(metadata, root, file_path)
            
            return metadata
            
        except Exception as e:
            self.logger.log_error(
                file_path, "metadata_building", "build_error",
                str(e), "Complete metadata object",
                "Review transformation logic"
            )
            return None
    
    def _count_fgdc_data_content(self, fgdc_content: str) -> int:
        """Count only the text content of FGDC fields, excluding XML markup."""
        try:
            root = ET.fromstring(fgdc_content)
            total_chars = 0
            
            # Count text content from key FGDC elements
            key_elements = [
                './/title', './/origin', './/pubdate', './/abstract', './/purpose',
                './/supplinf', './/themekey', './/placekey', './/stratum', './/temporal',
                './/westbc', './/eastbc', './/northbc', './/southbc', './/accconst',
                './/useconst', './/cntper', './/cntorg', './/cntpos', './/cntaddr',
                './/cntvoice', './/cntemail', './/onlink', './/crossref', './/lworkcit',
                './/procstep', './/procdesc', './/procdate', './/proccont', './/srcscale',
                './/typesrc', './/srctime', './/srccite', './/srcprod', './/srcused',
                './/srcinfo', './/attrlabl', './/attrdef', './/attrdefs', './/attrdomv',
                './/attrdomc', './/attrdomr', './/attrmfrq'
            ]
            
            for xpath in key_elements:
                elements = root.findall(xpath)
                for elem in elements:
                    if elem.text:
                        total_chars += len(elem.text.strip())
            
            return total_chars
        except Exception:
            # Fallback: estimate data content as 30% of total (rough estimate)
            return int(len(fgdc_content) * 0.3)
    
    def _count_zenodo_data_content(self, metadata: Dict[str, Any]) -> int:
        """Count only the text content of Zenodo fields, excluding JSON structure."""
        total_chars = 0
        
        # Count text content from key Zenodo fields
        text_fields = [
            'title', 'description', 'notes', 'version', 'imprint_publisher',
            'imprint_place', 'partof_title', 'journal_title', 'conference_title',
            'thesis_university'
        ]
        
        for field in text_fields:
            if field in metadata and metadata[field]:
                if isinstance(metadata[field], str):
                    total_chars += len(metadata[field])
        
        # Count creators
        if 'creators' in metadata:
            for creator in metadata['creators']:
                if 'name' in creator:
                    total_chars += len(creator['name'])
                if 'affiliation' in creator:
                    total_chars += len(creator['affiliation'])
        
        # Count keywords
        if 'keywords' in metadata:
            for keyword in metadata['keywords']:
                total_chars += len(keyword)
        
        # Count contributors
        if 'contributors' in metadata:
            for contributor in metadata['contributors']:
                if 'name' in contributor:
                    total_chars += len(contributor['name'])
                if 'affiliation' in contributor:
                    total_chars += len(contributor['affiliation'])
        
        # Count related identifiers
        if 'related_identifiers' in metadata:
            for rel_id in metadata['related_identifiers']:
                if 'identifier' in rel_id:
                    total_chars += len(rel_id['identifier'])
                if 'description' in rel_id:
                    total_chars += len(rel_id['description'])
        
        return total_chars
    
    def _extract_title(self, root: ET.Element, file_path: str) -> Optional[str]:
        """Extract title from FGDC."""
        title_elem = root.find('.//title')
        if title_elem is not None and title_elem.text:
            title = title_elem.text.strip()
            if title:
                # Truncate title if it exceeds Zenodo's 250 character limit
                if len(title) > 250:
                    truncated_title = title[:247] + "..."
                    self.logger.log_warning(
                        file_path, "idinfo.citation.citeinfo.title", "title_truncated",
                        f"Title length: {len(title)} characters", "Title under 250 characters",
                        f"Truncated from {len(title)} to 250 characters: '{truncated_title}'"
                    )
                    return truncated_title
                
                return title
        
        self.logger.log_error(
            file_path, "idinfo.citation.citeinfo.title", "missing_required_field",
            None, "Non-empty title text",
            "Add title element to citation section"
        )
        return None
    
    def _extract_creators(self, root: ET.Element, file_path: str) -> List[Dict[str, str]]:
        """Extract and format creators from FGDC origin elements."""
        creators = []
        origin_elements = root.findall('.//origin')
        
        if not origin_elements:
            self.logger.log_error(
                file_path, "idinfo.citation.citeinfo.origin", "missing_required_field",
                None, "At least one origin element",
                "Add origin element to citation section"
            )
            return []
        
        for origin_elem in origin_elements:
            if origin_elem.text:
                origin_text = origin_elem.text.strip()
                if origin_text:
                    # Handle multiple creators in a single origin element
                    if ' and ' in origin_text.lower():
                        # Split on "and" and process each creator
                        parts = re.split(r'\s+and\s+', origin_text, flags=re.IGNORECASE)
                        for part in parts:
                            creator = self._parse_single_creator(part.strip(), file_path)
                            if creator:
                                creators.append(creator)
                    else:
                        # Single creator
                        creator = self._format_creator_name(origin_text, file_path)
                        if creator:
                            creators.append(creator)
        
        if not creators:
            self.logger.log_error(
                file_path, "idinfo.citation.citeinfo.origin", "no_valid_creators",
                "Empty or invalid origin text", "Valid creator names",
                "Ensure origin elements contain valid creator information"
            )
        
        return creators
    
    def _format_creator_name(self, origin_text: str, file_path: str) -> Optional[Dict[str, str]]:
        """Format creator name to Zenodo 'Family, Given' format."""
        try:
            # Check if it's an organization
            if self._is_organization(origin_text):
                return {
                    "name": origin_text,
                    "type": "Organization"
                }
            
            # Handle multiple creators separated by "and"
            if ' and ' in origin_text.lower():
                creators = []
                # Split on "and" but be careful about "and" in names
                parts = re.split(r'\s+and\s+', origin_text, flags=re.IGNORECASE)
                for part in parts:
                    creator = self._parse_single_creator(part.strip(), file_path)
                    if creator:
                        creators.append(creator)
                return creators[0] if len(creators) == 1 else None  # Return first for now
            
            # Try to parse as single person name
            return self._parse_single_creator(origin_text, file_path)
            
        except Exception as e:
            self.logger.log_error(
                file_path, "creator_formatting", "format_error",
                origin_text, "Valid creator object",
                f"Error formatting creator: {str(e)}"
            )
            return None
    
    def _parse_single_creator(self, name_text: str, file_path: str) -> Optional[Dict[str, str]]:
        """Parse a single creator name."""
        try:
            # Common patterns: "Last, First", "First Last", "Last, First Middle"
            if ',' in name_text:
                # "Last, First" format
                parts = [p.strip() for p in name_text.split(',', 1)]
                if len(parts) == 2:
                    family_name = parts[0]
                    given_names = parts[1]
                    return {
                        "name": f"{family_name}, {given_names}"
                    }
            else:
                # "First Last" format - assume last word is family name
                words = name_text.split()
                if len(words) >= 2:
                    family_name = words[-1]
                    given_names = ' '.join(words[:-1])
                    return {
                        "name": f"{family_name}, {given_names}"
                    }
            
            # If we can't parse it properly, use as-is but log warning
            self.logger.log_warning(
                file_path, "idinfo.citation.citeinfo.origin", "unparseable_creator_name",
                name_text, "Family, Given format or Organization",
                f"Could not parse creator name: {name_text}",
                "Review name format or add organization detection"
            )
            
            return {
                "name": name_text
            }
            
        except Exception as e:
            self.logger.log_error(
                file_path, "creator_formatting", "format_error",
                name_text, "Valid creator object",
                f"Error formatting single creator: {str(e)}"
            )
            return None
    
    def _is_organization(self, text: str) -> bool:
        """Check if text represents an organization."""
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in self.org_patterns)
    
    def _extract_publication_date(self, root: ET.Element, file_path: str) -> Optional[str]:
        """Extract and normalize publication date."""
        pubdate_elem = root.find('.//pubdate')
        if pubdate_elem is not None and pubdate_elem.text:
            date_text = pubdate_elem.text.strip()
            if date_text:
                normalized_date = self._normalize_date(date_text, file_path)
                if normalized_date:
                    return normalized_date
        
        # Try metadata date as fallback
        metd_elem = root.find('.//metd')
        if metd_elem is not None and metd_elem.text:
            date_text = metd_elem.text.strip()
            if date_text:
                normalized_date = self._normalize_date(date_text, file_path)
                if normalized_date:
                    self.logger.log_warning(
                        file_path, "idinfo.citation.citeinfo.pubdate", "missing_publication_date",
                        None, "Publication date in citation",
                        f"Using metadata date as fallback: {date_text}",
                        "Add publication date to citation section"
                    )
                    return normalized_date
        
        self.logger.log_error(
            file_path, "idinfo.citation.citeinfo.pubdate", "missing_required_field",
            None, "Publication date (YYYY, YYYYMM, or YYYYMMDD)",
            "Add pubdate element to citation section"
        )
        return None
    
    def _normalize_date(self, date_str: str, file_path: str) -> Optional[str]:
        """Normalize FGDC date to ISO format."""
        try:
            date_str = date_str.strip()
            
            # Record the date format encountered
            self.logger.record_date_format(date_str, file_path)
            
            # Handle special cases
            if not date_str or date_str.lower() in ['varies', 'unknown', 'not specified', 'present']:
                self.logger.log_warning(
                    file_path, "date_normalization", "vague_date",
                    date_str or "empty", "Specific date (YYYY-MM-DD)",
                    f"Vague or empty date encountered: {date_str or 'empty'}",
                    "Use metadata date or current date as fallback"
                )
                return None
            
            # Handle common "unpublished" or "planned" cases
            if date_str.lower() in ['planned', 'unpublished', 'unpublished material', 'unpublished material']:
                from datetime import datetime
                current_year = datetime.now().year
                self.logger.log_warning(
                    file_path, "date_normalization", "status_date",
                    date_str, "Specific date (YYYY-MM-DD)",
                    f"Status date encountered: {date_str}",
                    f"Using current year {current_year} for unpublished/planned material"
                )
                return f"{current_year}-01-01"
            
            # Handle YYYY-YYYY ranges (e.g., "1950-1980")
            if re.match(r'^\d{4}-\d{4}$', date_str):
                year = int(date_str[:4])
                self.logger.log_warning(
                    file_path, "date_normalization", "date_range",
                    date_str, "Single date (YYYY-MM-DD)",
                    f"Date range encountered: {date_str}",
                    f"Using first year {year} from range"
                )
                return f"{year}-01-01"
            
            # Handle YYYYMMDD-YYYYMMDD ranges (e.g., "19970101-20021231")
            if re.match(r'^\d{8}-\d{8}$', date_str):
                year = date_str[:4]
                month = date_str[4:6]
                day = date_str[6:8]
                self.logger.log_warning(
                    file_path, "date_normalization", "date_range",
                    date_str, "Single date (YYYY-MM-DD)",
                    f"Date range encountered: {date_str}",
                    f"Using first date {year}-{month}-{day} from range"
                )
                return f"{year}-{month}-{day}"
            
            # Handle comma-separated years (e.g., "1991, 1992", "1988, 1989, 1991")
            if ',' in date_str and re.search(r'\d{4}', date_str):
                years = re.findall(r'\d{4}', date_str)
                if years:
                    year = int(years[0])
                    self.logger.log_warning(
                        file_path, "date_normalization", "multiple_years",
                        date_str, "Single date (YYYY-MM-DD)",
                        f"Multiple years encountered: {date_str}",
                        f"Using first year {year}"
                    )
                    return f"{year}-01-01"
            
            # Handle YYYY-Present format (e.g., "1992-Present")
            if date_str.endswith('-Present'):
                year_match = re.search(r'(\d{4})-Present', date_str)
                if year_match:
                    year = int(year_match.group(1))
                    self.logger.log_warning(
                        file_path, "date_normalization", "present_range",
                        date_str, "Single date (YYYY-MM-DD)",
                        f"Present range encountered: {date_str}",
                        f"Using year {year}"
                    )
                    return f"{year}-01-01"
            
            # Handle YYYYMM-YYYYMM format (e.g., "196205-196207")
            if re.match(r'^\d{6}-\d{6}$', date_str):
                year = date_str[:4]
                month = date_str[4:6]
                self.logger.log_warning(
                    file_path, "date_normalization", "month_range",
                    date_str, "Single date (YYYY-MM-DD)",
                    f"Month range encountered: {date_str}",
                    f"Using first month {year}-{month}"
                )
                return f"{year}-{month}-01"
            
            # Handle space-separated years (e.g., "1983 1994")
            if ' ' in date_str and re.match(r'^\d{4}\s+\d{4}$', date_str):
                year = int(date_str.split()[0])
                self.logger.log_warning(
                    file_path, "date_normalization", "space_separated_years",
                    date_str, "Single date (YYYY-MM-DD)",
                    f"Space-separated years: {date_str}",
                    f"Using first year {year}"
                )
                return f"{year}-01-01"
            
            # Handle complex formats like "72-88  thru  87-98" FIRST
            if 'thru' in date_str.lower():
                # Extract first 2-digit year and convert to 4-digit
                year_match = re.search(r'(\d{2})', date_str)
                if year_match:
                    year = int(year_match.group(1))
                    # Convert 2-digit years to 4-digit (assume 1900s)
                    if year < 50:  # Assume 20xx
                        year += 2000
                    else:  # Assume 19xx
                        year += 1900
                    self.logger.log_warning(
                        file_path, "date_normalization", "complex_date_range",
                        date_str, "Single date (YYYY-MM-DD)",
                        f"Complex date range: {date_str}",
                        f"Using first year {year} from range"
                    )
                    return f"{year}-01-01"
                else:
                    # Try to extract any 2-digit number
                    all_numbers = re.findall(r'\d{2}', date_str)
                    if all_numbers:
                        year = int(all_numbers[0])
                        # Convert 2-digit years to 4-digit (assume 1900s)
                        if year < 50:  # Assume 20xx
                            year += 2000
                        else:  # Assume 19xx
                            year += 1900
                        self.logger.log_warning(
                            file_path, "date_normalization", "complex_date_range",
                            date_str, "Single date (YYYY-MM-DD)",
                            f"Complex date range: {date_str}",
                            f"Using first 2-digit number {year} from range"
                        )
                        return f"{year}-01-01"
                    else:
                        # Debug: log what we found
                        self.logger.log_error(
                            file_path, "date_normalization", "no_numbers_found",
                            date_str, "Date with extractable numbers",
                            f"No 2-digit numbers found in: {date_str}",
                            "Check regex pattern"
                        )
            
            # Handle range dates like "1988 - Present" (but not "thru" which is handled above)
            if ' - ' in date_str or ' to ' in date_str:
                # Extract the first year from the range
                year_match = re.search(r'(\d{4})', date_str)
                if year_match:
                    year = year_match.group(1)
                    self.logger.log_warning(
                        file_path, "date_normalization", "date_range",
                        date_str, "Single date (YYYY-MM-DD)",
                        f"Date range encountered: {date_str}",
                        f"Using first year {year} from range"
                    )
                    return f"{year}-01-01"
                else:
                    self.logger.log_error(
                        file_path, "date_normalization", "invalid_date_range",
                        date_str, "Date range with extractable year",
                        f"Could not extract year from range: {date_str}",
                        "Add parsing logic for date ranges"
                    )
                    return None
            
            # Handle 2-digit years (assume 1900s)
            if re.match(r'^\d{2}-\d{2}$', date_str):
                # Format like "72-88"
                parts = date_str.split('-')
                if len(parts) == 2:
                    year1 = int(parts[0])
                    year2 = int(parts[1])
                    # Convert 2-digit years to 4-digit (assume 1900s)
                    if year1 < 50:  # Assume 20xx
                        year1 += 2000
                    else:  # Assume 19xx
                        year1 += 1900
                    self.logger.log_warning(
                        file_path, "date_normalization", "two_digit_year",
                        date_str, "Four-digit year (YYYY)",
                        f"Two-digit year range: {date_str}",
                        f"Converted to {year1}"
                    )
                    return f"{year1}-01-01"
            
            # Try different date formats
            if len(date_str) == 4:  # YYYY
                return f"{date_str}-01-01"
            elif len(date_str) == 6:  # YYYYMM
                year = date_str[:4]
                month = date_str[4:6]
                return f"{year}-{month}-01"
            elif len(date_str) == 8:  # YYYYMMDD
                year = date_str[:4]
                month = date_str[4:6]
                day = date_str[6:8]
                return f"{year}-{month}-{day}"
            else:
                # Try to parse with dateutil
                parsed_date = dateutil.parser.parse(date_str)
                return parsed_date.strftime('%Y-%m-%d')
                
        except Exception as e:
            self.logger.log_error(
                file_path, "date_normalization", "invalid_date_format",
                date_str, "YYYY, YYYYMM, or YYYYMMDD format",
                f"Could not parse date: {str(e)}",
                "Review date format and add parsing logic"
            )
            return None
    
    def _extract_description(self, root: ET.Element, file_path: str) -> Optional[str]:
        """Extract description from abstract."""
        abstract_elem = root.find('.//abstract')
        if abstract_elem is not None and abstract_elem.text:
            abstract = abstract_elem.text.strip()
            if abstract:
                return abstract
        
        # Try alternative description fields if abstract is missing
        purpose_elem = root.find('.//purpose')
        if purpose_elem is not None and purpose_elem.text:
            purpose = purpose_elem.text.strip()
            if purpose:
                self.logger.log_warning(
                    file_path, "idinfo.descript.abstract", "missing_required_field",
                    "No abstract found, using purpose", "Non-empty abstract text",
                    "Using purpose as fallback description"
                )
                return purpose
        
        # Try supplinf (supplemental information) as last resort
        supplinf_elem = root.find('.//supplinf')
        if supplinf_elem is not None and supplinf_elem.text:
            supplinf = supplinf_elem.text.strip()
            if supplinf:
                self.logger.log_warning(
                    file_path, "idinfo.descript.abstract", "missing_required_field",
                    "No abstract or purpose found, using supplinf", "Non-empty abstract text",
                    "Using supplemental information as fallback description"
                )
                return supplinf
        
        # If still no description, create a minimal one from title
        title_elem = root.find('.//title')
        if title_elem is not None and title_elem.text:
            title = title_elem.text.strip()
            if title:
                self.logger.log_warning(
                    file_path, "idinfo.descript.abstract", "missing_required_field",
                    "No description found, using title", "Non-empty abstract text",
                    "Using title as minimal description"
                )
                return f"Dataset: {title}"
        
        self.logger.log_error(
            file_path, "idinfo.descript.abstract", "missing_required_field",
            None, "Non-empty abstract text",
            "Add abstract element to descript section"
        )
        return None
    
    def _add_optional_fields(self, metadata: Dict[str, Any], root: ET.Element, file_path: str):
        """Add optional fields to metadata."""
        # Keywords
        keywords = self._extract_keywords(root, file_path)
        metadata['keywords'] = keywords
        
        # Subjects (from controlled vocabularies)
        subjects = self._extract_subjects(root, file_path)
        metadata['subjects'] = subjects
        
        # Access rights and license
        self._extract_access_constraints(metadata, root, file_path)
        
        # Temporal coverage
        self._extract_temporal_coverage(metadata, root, file_path)
        
        # Spatial coverage
        self._extract_spatial_coverage(metadata, root, file_path)
        
        # Contributors
        contributors = self._extract_contributors(root, file_path)
        metadata['contributors'] = contributors
        
        # Related identifiers
        related_ids = self._extract_related_identifiers(root, file_path)
        metadata['related_identifiers'] = related_ids
        
        # References
        references = self._extract_references(root, file_path)
        metadata['references'] = references
        
        # Notes (combine various fields)
        notes = self._build_notes(root, file_path)
        metadata['notes'] = notes
        
        # Extract additional fields from crosswalk
        self._extract_additional_fields(root, metadata, file_path)
    
    def _extract_keywords(self, root: ET.Element, file_path: str) -> List[str]:
        """Extract and flatten keywords."""
        keywords = []
        keyword_sections = root.findall('.//keywords')
        
        for section in keyword_sections:
            # Theme keywords
            theme_keys = section.findall('.//themekey')
            for key in theme_keys:
                if key.text:
                    keyword = key.text.strip()
                    if keyword and keyword not in keywords:
                        keywords.append(keyword)
            
            # Place keywords
            place_keys = section.findall('.//placekey')
            for key in place_keys:
                if key.text:
                    keyword = key.text.strip()
                    if keyword and keyword not in keywords:
                        keywords.append(keyword)
            
            # Stratum keywords
            stratum_keys = section.findall('.//stratumkey')
            for key in stratum_keys:
                if key.text:
                    keyword = key.text.strip()
                    if keyword and keyword not in keywords:
                        keywords.append(keyword)
            
            # Temporal keywords
            temporal_keys = section.findall('.//temporalkey')
            for key in temporal_keys:
                if key.text:
                    keyword = key.text.strip()
                    if keyword and keyword not in keywords:
                        keywords.append(keyword)
        
        return keywords
    
    def _extract_subjects(self, root: ET.Element, file_path: str) -> List[Dict[str, str]]:
        """Extract subjects from controlled vocabularies."""
        subjects = []
        keyword_sections = root.findall('.//keywords')
        
        for section in keyword_sections:
            # Get thesaurus name
            themekt_elem = section.find('.//themekt')
            thesaurus_name = themekt_elem.text.strip() if themekt_elem is not None and themekt_elem.text else None
            
            # Only create subjects if we have a thesaurus name and it's not "Other" or "None"
            if thesaurus_name and thesaurus_name.lower() not in ['other', 'none', '']:
                # Get theme keywords for this thesaurus
                theme_keys = section.findall('.//themekey')
                for key in theme_keys:
                    if key.text:
                        term = key.text.strip()
                        if term:
                            subjects.append({
                                'term': term,
                                'identifier': f"{thesaurus_name}:{term}",
                                'scheme': 'thesaurus'
                            })
        
        return subjects
    
    def _extract_access_constraints(self, metadata: Dict[str, Any], root: ET.Element, file_path: str):
        """Extract access constraints and determine access_right and license."""
        # Access constraints
        accconst_elem = root.find('.//accconst')
        accconst_text = accconst_elem.text.strip() if accconst_elem is not None and accconst_elem.text else ""
        
        # Use constraints (often contains license info)
        useconst_elem = root.find('.//useconst')
        useconst_text = useconst_elem.text.strip() if useconst_elem is not None and useconst_elem.text else ""
        
        # Determine access right
        if accconst_text.lower() in ['none', 'open', 'public']:
            metadata['access_right'] = 'open'
        elif any(word in accconst_text.lower() for word in ['restricted', 'by request', 'registration']):
            metadata['access_right'] = 'restricted'
            metadata['access_conditions'] = accconst_text
        else:
            # Default to open
            metadata['access_right'] = 'open'
        
        # Try to detect license
        license_detected = self._detect_license(useconst_text, file_path)
        if license_detected:
            metadata['license'] = license_detected
            self.logger.record_license_detected()
        elif metadata['access_right'] in ['open', 'embargoed']:
            # Zenodo requires license for open/embargoed records
            metadata['license'] = 'cc-zero'  # Default for datasets
    
    def _detect_license(self, useconst_text: str, file_path: str) -> Optional[str]:
        """Detect license from use constraints text."""
        if not useconst_text:
            return None
        
        text_lower = useconst_text.lower().strip()
        
        # Skip if the text is just "none" or similar
        if text_lower in ['none', 'n/a', 'not applicable', 'not specified']:
            self.logger.log_warning(
                file_path, "idinfo.useconst", "invalid_license_detected",
                useconst_text, "Valid license identifier",
                f"Invalid license '{useconst_text}' detected, using default cc-zero"
            )
            return "cc-zero"  # Use default instead of None
        
        for license_id, patterns in self.license_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return license_id
        
        return None
    
    def _extract_temporal_coverage(self, metadata: Dict[str, Any], root: ET.Element, file_path: str):
        """Extract temporal coverage and add to notes."""
        timeperd = root.find('.//timeperd')
        if timeperd is None:
            return
        
        temporal_info = []
        
        # Currentness reference
        current_elem = timeperd.find('.//current')
        if current_elem is not None and current_elem.text:
            temporal_info.append(f"Currentness: {current_elem.text.strip()}")
        
        # Date range
        rngdates = timeperd.find('.//rngdates')
        if rngdates is not None:
            begdate = rngdates.find('.//begdate')
            enddate = rngdates.find('.//enddate')
            
            if begdate is not None and begdate.text:
                beg_date = self._normalize_date(begdate.text.strip(), file_path)
                if beg_date:
                    if enddate is not None and enddate.text:
                        end_date = self._normalize_date(enddate.text.strip(), file_path)
                        if end_date:
                            temporal_info.append(f"Temporal coverage: {beg_date} to {end_date}")
                        else:
                            temporal_info.append(f"Temporal coverage: {beg_date} onwards")
                    else:
                        temporal_info.append(f"Temporal coverage: {beg_date} onwards")
        
        # Single date
        sngdate = timeperd.find('.//sngdate')
        if sngdate is not None and sngdate.text:
            single_date = self._normalize_date(sngdate.text.strip(), file_path)
            if single_date:
                temporal_info.append(f"Temporal coverage: {single_date}")
        
        if temporal_info:
            # Add to notes
            if metadata['notes']:
                metadata['notes'] += "\n\n"
            metadata['notes'] += "Temporal Information:\n" + "\n".join(temporal_info)
    
    def _extract_spatial_coverage(self, metadata: Dict[str, Any], root: ET.Element, file_path: str):
        """Extract spatial coverage and add to notes."""
        bounding = root.find('.//spdom/bounding')
        if bounding is None:
            return
        
        try:
            westbc = bounding.find('.//westbc')
            eastbc = bounding.find('.//eastbc')
            northbc = bounding.find('.//northbc')
            southbc = bounding.find('.//southbc')
            
            if all(elem is not None and elem.text for elem in [westbc, eastbc, northbc, southbc]):
                west = float(westbc.text.strip())
                east = float(eastbc.text.strip())
                north = float(northbc.text.strip())
                south = float(southbc.text.strip())
                
                # Check for dateline crossing and handle it
                if west > east:
                    # This is likely a dateline crossing case
                    # Convert to -180 to 180 range and adjust
                    if west > 180:
                        west -= 360
                    if east > 180:
                        east -= 360
                    
                    # If still crossing, it's a true dateline crossing
                    if west > east:
                        self.logger.record_bbox_issue(
                            file_path, "dateline_crossing",
                            {"west": west, "east": east, "north": north, "south": south}
                        )
                        self.logger.log_warning(
                            file_path, "spdom.bounding", "dateline_crossing",
                            f"west={west}, east={east}", "west < east",
                            "Bounding box crosses dateline",
                            "Consider splitting into two bounding boxes or using a different representation"
                        )
                        # For now, we'll use the original values but note the crossing
                        spatial_info = f"Spatial coverage: W{west}, E{east}, N{north}, S{south} (crosses dateline)"
                    else:
                        spatial_info = f"Spatial coverage: W{west}, E{east}, N{north}, S{south}"
                else:
                    # Normal case - normalize longitude to -180 to 180 range
                    if west > 180:
                        west -= 360
                    if east > 180:
                        east -= 360
                    spatial_info = f"Spatial coverage: W{west}, E{east}, N{north}, S{south}"
                
                # Add to notes
                if metadata['notes']:
                    metadata['notes'] += "\n\n"
                metadata['notes'] += spatial_info
                
        except (ValueError, TypeError) as e:
            self.logger.log_error(
                file_path, "spdom.bounding", "invalid_coordinates",
                f"Could not parse coordinates: {str(e)}", "Valid numeric coordinates",
                "Check coordinate format and values"
            )
    
    def _extract_contributors(self, root: ET.Element, file_path: str) -> List[Dict[str, str]]:
        """Extract contributors from point of contact and distributor."""
        contributors = []
        
        # Point of contact
        ptcontac = root.find('.//ptcontac')
        if ptcontac is not None:
            contact = self._extract_contact_info(ptcontac, "ContactPerson", file_path)
            if contact:
                contributors.append(contact)
        
        # Distributor
        distrib = root.find('.//distrib')
        if distrib is not None:
            distributor = self._extract_contact_info(distrib, "Distributor", file_path)
            if distributor:
                contributors.append(distributor)
        
        return contributors
    
    def _extract_contact_info(self, contact_elem: ET.Element, contact_type: str, file_path: str) -> Optional[Dict[str, str]]:
        """Extract contact information from contact element."""
        try:
            cntinfo = contact_elem.find('.//cntinfo')
            if cntinfo is None:
                return None
            
            # Get person name
            cntper = cntinfo.find('.//cntper')
            name = cntper.text.strip() if cntper is not None and cntper.text else ""
            
            if not name:
                return None
            
            # Format name
            formatted_name = self._format_creator_name(name, file_path)
            if formatted_name:
                contributor = {
                    "name": formatted_name["name"],
                    "type": contact_type
                }
                
                # Add email if available
                cntemail = cntinfo.find('.//cntemail')
                if cntemail is not None and cntemail.text:
                    # Note: Zenodo contributor object doesn't have email field
                    # This would go in notes
                    pass
                
                return contributor
            
        except Exception as e:
            self.logger.log_error(
                file_path, "contact_extraction", "extraction_error",
                str(e), "Valid contact information",
                "Review contact element structure"
            )
        
        return None
    
    def _extract_related_identifiers(self, root: ET.Element, file_path: str) -> List[Dict[str, str]]:
        """Extract related identifiers from online linkage and cross references."""
        related_ids = []
        
        # Online linkage
        onlinks = root.findall('.//onlink')
        for onlink in onlinks:
            if onlink.text:
                url = onlink.text.strip()
                if self._is_valid_url(url):
                    related_ids.append({
                        "identifier": url,
                        "relation": "isAlternateIdentifier"
                    })
        
        # Cross references
        crossrefs = root.findall('.//crossref')
        for crossref in crossrefs:
            if crossref.text:
                ref_text = crossref.text.strip()
                # Try to extract URLs or DOIs
                urls = self._extract_urls_from_text(ref_text)
                for url in urls:
                    related_ids.append({
                        "identifier": url,
                        "relation": "isRelatedTo"
                    })
        
        return related_ids
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if string is a valid URL."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _extract_urls_from_text(self, text: str) -> List[str]:
        """Extract URLs from text."""
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        return re.findall(url_pattern, text)
    
    def _extract_references(self, root: ET.Element, file_path: str) -> List[str]:
        """Extract references from various citation fields."""
        references = []
        
        # Other citation details
        othercit = root.find('.//othercit')
        if othercit is not None and othercit.text:
            references.append(othercit.text.strip())
        
        # Larger work citation
        lworkcit = root.find('.//lworkcit')
        if lworkcit is not None and lworkcit.text:
            references.append(lworkcit.text.strip())
        
        return references
    
    def _build_notes(self, root: ET.Element, file_path: str) -> str:
        """Build comprehensive notes from various FGDC fields."""
        notes_parts = []
        
        # Purpose
        purpose = root.find('.//purpose')
        if purpose is not None and purpose.text:
            notes_parts.append(f"Purpose: {purpose.text.strip()}")
        
        # Supplemental information
        supplinf = root.find('.//supplinf')
        if supplinf is not None and supplinf.text:
            notes_parts.append(f"Supplemental Information: {supplinf.text.strip()}")
        
        # Status information
        progress = root.find('.//progress')
        if progress is not None and progress.text:
            notes_parts.append(f"Status: {progress.text.strip()}")
        
        update = root.find('.//update')
        if update is not None and update.text:
            notes_parts.append(f"Maintenance frequency: {update.text.strip()}")
        
        # Access and use constraints
        accconst = root.find('.//accconst')
        if accconst is not None and accconst.text:
            notes_parts.append(f"Access constraints: {accconst.text.strip()}")
        
        useconst = root.find('.//useconst')
        if useconst is not None and useconst.text:
            notes_parts.append(f"Use constraints: {useconst.text.strip()}")
        
        # Note: Distribution liability and FGDC metadata information are handled in 
        # _extract_distribution_info and _extract_metadata_info respectively to avoid duplication
        
        return "\n\n".join(notes_parts)
    
    def _extract_additional_fields(self, root: ET.Element, metadata: Dict[str, Any], file_path: str):
        """Extract additional fields from FGDC based on crosswalk mapping."""
        
        # Edition/Version (row 5)
        edition_elem = root.find('.//edition')
        if edition_elem is not None and edition_elem.text:
            metadata['version'] = edition_elem.text.strip()
        
        # Series Name (row 6)
        sername_elem = root.find('.//sername')
        if sername_elem is not None and sername_elem.text:
            metadata['partof_title'] = sername_elem.text.strip()
        
        # Issue Identification (row 7)
        issue_elem = root.find('.//issue')
        if issue_elem is not None and issue_elem.text:
            metadata['journal_issue'] = issue_elem.text.strip()
        
        # Publication Place (row 8)
        pubplace_elem = root.find('.//pubplace')
        if pubplace_elem is not None and pubplace_elem.text:
            metadata['imprint_place'] = pubplace_elem.text.strip()
        
        # Publisher (row 9)
        publish_elem = root.find('.//publish')
        if publish_elem is not None and publish_elem.text:
            metadata['imprint_publisher'] = publish_elem.text.strip()
        
        # Other Citation Details (row 10)
        othercit_elem = root.find('.//othercit')
        if othercit_elem is not None and othercit_elem.text:
            if 'references' not in metadata:
                metadata['references'] = []
            metadata['references'].append(othercit_elem.text.strip())
        
        # Larger Work Citation (row 12)
        lworkcit_elem = root.find('.//lworkcit')
        if lworkcit_elem is not None and lworkcit_elem.text:
            if 'related_identifiers' not in metadata:
                metadata['related_identifiers'] = []
            metadata['related_identifiers'].append({
                'identifier': lworkcit_elem.text.strip(),
                'relation': 'isPartOf'
            })
        
        # Browse Graphic (row 28)
        browse_elems = root.findall('.//browse')
        for browse_elem in browse_elems:
            browsed_elem = browse_elem.find('browsed')
            if browsed_elem is not None and browsed_elem.text:
                if 'related_identifiers' not in metadata:
                    metadata['related_identifiers'] = []
                metadata['related_identifiers'].append({
                    'identifier': browsed_elem.text.strip(),
                    'relation': 'isDocumentedBy'
                })
        
        # Native Data Set Environment (row 29)
        native_elem = root.find('.//native')
        if native_elem is not None and native_elem.text:
            if 'notes' not in metadata:
                metadata['notes'] = ""
            metadata['notes'] += f"\n\nNative data set environment: {native_elem.text.strip()}"
        
        # Cloud Cover (row 36)
        cloudcov_elem = root.find('.//cloudcov')
        if cloudcov_elem is not None and cloudcov_elem.text:
            if 'notes' not in metadata:
                metadata['notes'] = ""
            metadata['notes'] += f"\n\nCloud cover: {cloudcov_elem.text.strip()}"
        
        # Security Information (row 26)
        self._extract_security_info(root, metadata, file_path)
        
        # Data Quality Reports (rows 31-35)
        self._extract_data_quality(root, metadata, file_path)
        
        # Spatial Reference Information (rows 37-41)
        self._extract_spatial_reference(root, metadata, file_path)
        
        # Entity and Attribute Information (rows 42-46)
        self._extract_entity_attribute_info(root, metadata, file_path)
        
        # Distribution Information (rows 47-55)
        self._extract_distribution_info(root, metadata, file_path)
        
        # Metadata Information (rows 56-59)
        self._extract_metadata_info(root, metadata, file_path)
    
    def _extract_security_info(self, root: ET.Element, metadata: Dict[str, Any], file_path: str):
        """Extract security information (row 26)."""
        secinfo = root.find('.//secinfo')
        if secinfo is not None:
            secclass = secinfo.find('.//secclass')
            if secclass is not None and secclass.text:
                secclass_text = secclass.text.strip().lower()
                if secclass_text in ['restricted', 'confidential', 'secret']:
                    metadata['access_right'] = 'restricted'
                    if 'access_conditions' not in metadata:
                        metadata['access_conditions'] = f"Security classification: {secclass.text.strip()}"
                    
                    # Add security handling info
                    sechandl = secinfo.find('.//sechandl')
                    if sechandl is not None and sechandl.text:
                        metadata['access_conditions'] += f"; Handling: {sechandl.text.strip()}"
    
    def _extract_data_quality(self, root: ET.Element, metadata: Dict[str, Any], file_path: str):
        """Extract data quality reports (rows 31-35)."""
        dataqual = root.find('.//dataqual')
        if dataqual is None:
            return
        
        notes_parts = []
        
        # Attribute Accuracy Report (row 31)
        attraccr = dataqual.find('.//attraccr')
        if attraccr is not None and attraccr.text:
            notes_parts.append(f"Data quality - Attribute accuracy: {attraccr.text.strip()}")
        
        # Logical Consistency Report (row 32)
        logic = dataqual.find('.//logic')
        if logic is not None and logic.text:
            notes_parts.append(f"Data quality - Logical consistency: {logic.text.strip()}")
        
        # Completeness Report (row 33)
        complete = dataqual.find('.//complete')
        if complete is not None and complete.text:
            notes_parts.append(f"Data quality - Completeness: {complete.text.strip()}")
        
        # Positional Accuracy (row 34)
        posacc = dataqual.find('.//posacc')
        if posacc is not None:
            horizpa = posacc.find('.//horizpa')
            vertacc = posacc.find('.//vertacc')
            if horizpa is not None and horizpa.text:
                notes_parts.append(f"Data quality - Horizontal positional accuracy: {horizpa.text.strip()}")
            if vertacc is not None and vertacc.text:
                notes_parts.append(f"Data quality - Vertical positional accuracy: {vertacc.text.strip()}")
        
        # Lineage: Sources & Process Steps (row 35)
        lineage = dataqual.find('.//lineage')
        if lineage is not None:
            # Process steps
            procsteps = lineage.findall('.//procstep')
            if procsteps:
                notes_parts.append("Lineage - Process steps:")
                for i, procstep in enumerate(procsteps, 1):
                    procdesc = procstep.find('.//procdesc')
                    if procdesc is not None and procdesc.text:
                        notes_parts.append(f"  {i}. {procdesc.text.strip()}")
            
            # Source citations
            srcinfos = lineage.findall('.//srcinfo')
            for srcinfo in srcinfos:
                srccite = srcinfo.find('.//srccite')
                if srccite is not None and srccite.text:
                    if 'references' not in metadata:
                        metadata['references'] = []
                    metadata['references'].append(f"Source: {srccite.text.strip()}")
        
        # Add to notes
        if notes_parts:
            if 'notes' not in metadata:
                metadata['notes'] = ""
            metadata['notes'] += "\n\n" + "\n".join(notes_parts)
    
    def _extract_spatial_reference(self, root: ET.Element, metadata: Dict[str, Any], file_path: str):
        """Extract spatial reference information (rows 37-41)."""
        notes_parts = []
        
        # Indirect/Direct Spatial Reference (row 37)
        spdoinfo = root.find('.//spdoinfo')
        if spdoinfo is not None:
            indspref = spdoinfo.find('.//indspref')
            direct = spdoinfo.find('.//direct')
            if indspref is not None and indspref.text:
                notes_parts.append(f"Spatial reference: {indspref.text.strip()}")
            elif direct is not None and direct.text:
                notes_parts.append(f"Spatial reference: {direct.text.strip()}")
            
            # Raster/Point/Vector Object Info (row 38)
            rastinfo = spdoinfo.find('.//rastinfo')
            ptvctinf = spdoinfo.find('.//ptvctinf')
            if rastinfo is not None:
                rasttype = rastinfo.find('.//rasttype')
                if rasttype is not None and rasttype.text:
                    notes_parts.append(f"Raster type: {rasttype.text.strip()}")
            elif ptvctinf is not None:
                sdtsterm = ptvctinf.find('.//sdtsterm')
                if sdtsterm is not None and sdtsterm.text:
                    notes_parts.append(f"Vector type: {sdtsterm.text.strip()}")
        
        # Horizontal Coordinate System Definition (row 39)
        horizsys = root.find('.//horizsys')
        if horizsys is not None:
            # Map projection
            mapproj = horizsys.find('.//mapproj')
            if mapproj is not None:
                mapprojn = mapproj.find('.//mapprojn')
                if mapprojn is not None and mapprojn.text:
                    notes_parts.append(f"Map projection: {mapprojn.text.strip()}")
            
            # Geographic coordinate system
            geograph = horizsys.find('.//geograph')
            if geograph is not None:
                geogunit = geograph.find('.//geogunit')
                if geogunit is not None and geogunit.text:
                    notes_parts.append(f"Geographic units: {geogunit.text.strip()}")
        
        # Geodetic Model (row 40)
        geodetic = root.find('.//geodetic')
        if geodetic is not None:
            horizdn = geodetic.find('.//horizdn')
            if horizdn is not None and horizdn.text:
                notes_parts.append(f"Horizontal datum: {horizdn.text.strip()}")
            
            ellips = geodetic.find('.//ellips')
            if ellips is not None:
                semiaxis = ellips.find('.//semiaxis')
                if semiaxis is not None and semiaxis.text:
                    notes_parts.append(f"Ellipsoid semi-major axis: {semiaxis.text.strip()}")
        
        # Vertical Coordinate System (row 41)
        vertdef = root.find('.//vertdef')
        if vertdef is not None:
            altsys = vertdef.find('.//altsys')
            if altsys is not None:
                altdatum = altsys.find('.//altdatum')
                if altdatum is not None and altdatum.text:
                    notes_parts.append(f"Vertical datum: {altdatum.text.strip()}")
            
            depthsys = vertdef.find('.//depthsys')
            if depthsys is not None:
                depthdatum = depthsys.find('.//depthdatum')
                if depthdatum is not None and depthdatum.text:
                    notes_parts.append(f"Depth datum: {depthdatum.text.strip()}")
        
        # Add to notes
        if notes_parts:
            if 'notes' not in metadata:
                metadata['notes'] = ""
            metadata['notes'] += "\n\n" + "\n".join(notes_parts)
    
    def _extract_entity_attribute_info(self, root: ET.Element, metadata: Dict[str, Any], file_path: str):
        """Extract entity and attribute information (rows 42-46)."""
        eainfo = root.find('.//eainfo')
        if eainfo is None:
            return
        
        notes_parts = []
        
        # Entity & Attribute Overview (row 46)
        overview = eainfo.find('.//overview')
        if overview is not None:
            eaover = overview.find('.//eaover')
            if eaover is not None and eaover.text:
                notes_parts.append(f"Entity and attribute overview: {eaover.text.strip()}")
            
            eadetcit = overview.find('.//eadetcit')
            if eadetcit is not None and eadetcit.text:
                if 'related_identifiers' not in metadata:
                    metadata['related_identifiers'] = []
                metadata['related_identifiers'].append({
                    'identifier': eadetcit.text.strip(),
                    'relation': 'isDocumentedBy'
                })
        
        # Detailed entity and attribute information
        detailed = eainfo.find('.//detailed')
        if detailed is not None:
            notes_parts.append("Data dictionary:")
            
            # Entity types
            enttyps = detailed.findall('.//enttyp')
            for enttyp in enttyps:
                enttypl = enttyp.find('.//enttypl')
                enttypd = enttyp.find('.//enttypd')
                if enttypl is not None and enttypl.text:
                    entity_name = enttypl.text.strip()
                    entity_def = enttypd.text.strip() if enttypd is not None and enttypd.text else "No definition"
                    notes_parts.append(f"  Entity: {entity_name} - {entity_def}")
                
                # Attributes for this entity
                attrs = enttyp.findall('.//attr')
                for attr in attrs:
                    attrlabl = attr.find('.//attrlabl')
                    attrdef = attr.find('.//attrdef')
                    if attrlabl is not None and attrlabl.text:
                        attr_name = attrlabl.text.strip()
                        attr_def = attrdef.text.strip() if attrdef is not None and attrdef.text else "No definition"
                        notes_parts.append(f"    Attribute: {attr_name} - {attr_def}")
                        
                        # Attribute domain
                        attrdomv = attr.find('.//attrdomv')
                        if attrdomv is not None:
                            edom = attrdomv.find('.//edom')
                            rdom = attrdomv.find('.//rdom')
                            codesetd = attrdomv.find('.//codesetd')
                            
                            if edom is not None:
                                edomv = edom.find('.//edomv')
                                edomvd = edom.find('.//edomvd')
                                if edomv is not None and edomv.text:
                                    enum_value = edomv.text.strip()
                                    enum_def = edomvd.text.strip() if edomvd is not None and edomvd.text else ""
                                    notes_parts.append(f"      Enumerated value: {enum_value} - {enum_def}")
                            
                            elif rdom is not None:
                                rdommin = rdom.find('.//rdommin')
                                rdommax = rdom.find('.//rdommax')
                                if rdommin is not None and rdommax is not None:
                                    min_val = rdommin.text.strip()
                                    max_val = rdommax.text.strip()
                                    notes_parts.append(f"      Range: {min_val} to {max_val}")
                            
                            elif codesetd is not None:
                                codesetn = codesetd.find('.//codesetn')
                                if codesetn is not None and codesetn.text:
                                    notes_parts.append(f"      Code set: {codesetn.text.strip()}")
        
        # Add to notes
        if notes_parts:
            if 'notes' not in metadata:
                metadata['notes'] = ""
            metadata['notes'] += "\n\n" + "\n".join(notes_parts)
    
    def _extract_distribution_info(self, root: ET.Element, metadata: Dict[str, Any], file_path: str):
        """Extract distribution information (rows 47-55)."""
        distinfo = root.find('.//distinfo')
        if distinfo is None:
            return
        
        notes_parts = []
        
        # Distribution Liability (row 48)
        distliab = distinfo.find('.//distliab')
        if distliab is not None and distliab.text:
            notes_parts.append(f"Distribution liability: {distliab.text.strip()}")
        
        # Standard Order Process
        stdorder = distinfo.find('.//stdorder')
        if stdorder is not None:
            # Non-digital Form (row 49)
            nondig = stdorder.find('.//nondig')
            if nondig is not None and nondig.text:
                notes_parts.append(f"Non-digital ordering: {nondig.text.strip()}")
            
            # Digital Transfer Information (row 50)
            digform = stdorder.find('.//digform')
            if digform is not None:
                digtinfo = digform.find('.//digtinfo')
                if digtinfo is not None:
                    formname = digtinfo.find('.//formname')
                    formvern = digtinfo.find('.//formvern')
                    formspec = digtinfo.find('.//formspec')
                    formcont = digtinfo.find('.//formcont')
                    transize = digtinfo.find('.//transize')
                    
                    format_parts = []
                    if formname is not None and formname.text:
                        format_parts.append(f"Format: {formname.text.strip()}")
                    if formvern is not None and formvern.text:
                        format_parts.append(f"Version: {formvern.text.strip()}")
                    if formspec is not None and formspec.text:
                        format_parts.append(f"Specification: {formspec.text.strip()}")
                    if formcont is not None and formcont.text:
                        format_parts.append(f"Content: {formcont.text.strip()}")
                    if transize is not None and transize.text:
                        format_parts.append(f"Size: {transize.text.strip()}")
                    
                    if format_parts:
                        notes_parts.append(f"Distribution format: {'; '.join(format_parts)}")
            
            # Digital Transfer Option: Online (row 51)
            digtopt = stdorder.find('.//digtopt')
            if digtopt is not None:
                onlinopt = digtopt.find('.//onlinopt')
                if onlinopt is not None:
                    computer = onlinopt.find('.//computer')
                    if computer is not None:
                        networka = computer.find('.//networka')
                        if networka is not None:
                            networkr = networka.find('.//networkr')
                            if networkr is not None and networkr.text:
                                if 'related_identifiers' not in metadata:
                                    metadata['related_identifiers'] = []
                                metadata['related_identifiers'].append({
                                    'identifier': networkr.text.strip(),
                                    'relation': 'isSupplementedBy'
                                })
            
            # Digital Transfer Option: Offline media (row 52)
            offoptn = stdorder.find('.//offoptn')
            if offoptn is not None and offoptn.text:
                notes_parts.append(f"Offline distribution: {offoptn.text.strip()}")
            
            # Fees (row 53)
            fees = stdorder.find('.//fees')
            if fees is not None and fees.text:
                if metadata.get('access_right') == 'restricted':
                    if 'access_conditions' not in metadata:
                        metadata['access_conditions'] = ""
                    metadata['access_conditions'] += f" Fees: {fees.text.strip()}"
                else:
                    notes_parts.append(f"Fees: {fees.text.strip()}")
            
            # Ordering Instructions (row 54)
            ordinst = stdorder.find('.//ordinst')
            if ordinst is not None and ordinst.text:
                notes_parts.append(f"Ordering instructions: {ordinst.text.strip()}")
            
            # Turnaround (row 55)
            turnaround = stdorder.find('.//turnaround')
            if turnaround is not None and turnaround.text:
                notes_parts.append(f"Turnaround: {turnaround.text.strip()}")
        
        # Add to notes
        if notes_parts:
            if 'notes' not in metadata:
                metadata['notes'] = ""
            metadata['notes'] += "\n\n" + "\n".join(notes_parts)
    
    def _extract_metadata_info(self, root: ET.Element, metadata: Dict[str, Any], file_path: str):
        """Extract metadata information (rows 56-59)."""
        metainfo = root.find('.//metainfo')
        if metainfo is None:
            return
        
        notes_parts = []
        
        # Metadata Date (row 56)
        metd = metainfo.find('.//metd')
        if metd is not None and metd.text:
            notes_parts.append(f"FGDC metadata date: {metd.text.strip()}")
        
        # Metadata Contact (row 57)
        metc = metainfo.find('.//metc')
        if metc is not None:
            cntinfo = metc.find('.//cntinfo')
            if cntinfo is not None:
                cntperp = cntinfo.find('.//cntperp')
                if cntperp is not None:
                    cntper = cntperp.find('.//cntper')
                    if cntper is not None and cntper.text:
                        notes_parts.append(f"FGDC metadata contact: {cntper.text.strip()}")
        
        # Metadata Standard Name/Version (row 58)
        metstdn = metainfo.find('.//metstdn')
        metstdv = metainfo.find('.//metstdv')
        if metstdn is not None and metstdn.text:
            standard_info = f"FGDC metadata standard: {metstdn.text.strip()}"
            if metstdv is not None and metstdv.text:
                standard_info += f" (version: {metstdv.text.strip()})"
            notes_parts.append(standard_info)
        
        # Metadata Access/Use Constraints (row 59)
        # Note: Access/Use constraints are already handled in _build_notes to avoid duplication
        metac = metainfo.find('.//metac')
        if metac is not None and metac.text:
            # Only add if different from main access constraints
            accconst = root.find('.//accconst')
            if accconst is None or accconst.text != metac.text:
                notes_parts.append(f"FGDC metadata access constraints: {metac.text.strip()}")
        
        metuc = metainfo.find('.//metuc')
        if metuc is not None and metuc.text:
            # Only add if different from main use constraints
            useconst = root.find('.//useconst')
            if useconst is None or useconst.text != metuc.text:
                notes_parts.append(f"FGDC metadata use constraints: {metuc.text.strip()}")
        
        # Add to notes
        if notes_parts:
            if 'notes' not in metadata:
                metadata['notes'] = ""
            metadata['notes'] += "\n\n" + "\n".join(notes_parts)


def transform_fgdc_file(xml_path: str) -> Optional[Dict[str, Any]]:
    """Transform a single FGDC XML file to Zenodo JSON format."""
    transformer = FGDCToZenodoTransformer()
    return transformer.transform_file(xml_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python fgdc_to_zenodo.py <xml_file>")
        sys.exit(1)
    
    result = transform_fgdc_file(sys.argv[1])
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("Transformation failed")
        sys.exit(1)
