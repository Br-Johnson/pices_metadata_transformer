"""
Comprehensive logging system for FGDC to Zenodo transformation.
Provides detailed issue tracking with actionable suggestions.
"""

import json
import csv
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import xml.etree.ElementTree as ET


class TransformationLogger:
    """Handles all logging for FGDC to Zenodo transformation."""
    
    def __init__(self, output_dir: str = "logs"):
        self.output_dir = output_dir
        self.run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.start_time = datetime.now()
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize data structures
        self.warnings = []
        self.errors = []
        self.statistics = {
            'total_files': 0,
            'successful': 0,
            'failed': 0,
            'field_coverage': defaultdict(int),
            'date_formats': Counter(),
            'bbox_issues': [],
            'missing_creators': [],
            'license_detected': 0,
            'issues_by_type': Counter(),
            'files_processed': [],
            'character_analysis': {
                'total_fgdc_chars': 0,
                'total_zenodo_chars': 0,
                'total_fgdc_data_chars': 0,
                'total_zenodo_data_chars': 0,
                'char_differences': [],
                'char_ratios': [],
                'data_preservation_ratios': []
            }
        }
        
        # Setup main logger
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Setup the main logger with file and console handlers."""
        logger = logging.getLogger('fgdc_transform')
        logger.setLevel(logging.DEBUG)
        
        # Clear any existing handlers
        logger.handlers.clear()
        
        # File handler
        log_file = os.path.join(self.output_dir, f"transform_{self.run_id}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def log_warning(self, file: str, field: str, issue_type: str, 
                   value_found: Any, expected: str, context: str = "", 
                   suggestion: str = ""):
        """Log a warning with detailed context."""
        warning = {
            "file": file,
            "field": field,
            "issue_type": issue_type,
            "severity": "warning",
            "value_found": str(value_found) if value_found is not None else None,
            "expected": expected,
            "context": context,
            "suggestion": suggestion,
            "timestamp": datetime.now().isoformat()
        }
        
        self.warnings.append(warning)
        self.statistics['issues_by_type'][issue_type] += 1
        
        self.logger.warning(
            f"WARNING in {file} - {field}: {issue_type}. "
            f"Found: {value_found}, Expected: {expected}. "
            f"Suggestion: {suggestion}"
        )
    
    def log_error(self, file: str, field: str, issue_type: str,
                 value_found: Any, expected: str, context: str = "",
                 suggestion: str = ""):
        """Log an error with detailed context."""
        error = {
            "file": file,
            "field": field,
            "issue_type": issue_type,
            "severity": "error",
            "value_found": str(value_found) if value_found is not None else None,
            "expected": expected,
            "context": context,
            "suggestion": suggestion,
            "timestamp": datetime.now().isoformat()
        }
        
        self.errors.append(error)
        self.statistics['issues_by_type'][issue_type] += 1
        
        self.logger.error(
            f"ERROR in {file} - {field}: {issue_type}. "
            f"Found: {value_found}, Expected: {expected}. "
            f"Suggestion: {suggestion}"
        )
    
    def log_info(self, message: str):
        """Log an info message."""
        self.logger.info(message)
    
    def log_debug(self, message: str):
        """Log a debug message."""
        self.logger.debug(message)
    
    def record_file_processed(self, file: str, success: bool, 
                            fields_present: List[str], issues: List[str],
                            field_coverage: Dict = None, character_analysis: Dict = None):
        """Record statistics for a processed file."""
        self.statistics['total_files'] += 1
        if success:
            self.statistics['successful'] += 1
        else:
            self.statistics['failed'] += 1
        
        # Track field coverage
        for field in fields_present:
            self.statistics['field_coverage'][field] += 1
        
        # Track character analysis
        if character_analysis:
            self.statistics['character_analysis']['total_fgdc_chars'] += character_analysis.get('fgdc_total_chars', 0)
            self.statistics['character_analysis']['total_zenodo_chars'] += character_analysis.get('zenodo_total_chars', 0)
            self.statistics['character_analysis']['total_fgdc_data_chars'] += character_analysis.get('fgdc_data_chars', 0)
            self.statistics['character_analysis']['total_zenodo_data_chars'] += character_analysis.get('zenodo_data_chars', 0)
            self.statistics['character_analysis']['char_differences'].append(character_analysis.get('char_difference', 0))
            self.statistics['character_analysis']['char_ratios'].append(character_analysis.get('char_ratio', 0))
            self.statistics['character_analysis']['data_preservation_ratios'].append(character_analysis.get('data_preservation_ratio', 0))
        
        # Record file processing info
        self.statistics['files_processed'].append({
            'file': file,
            'success': success,
            'fields_present': fields_present,
            'issues': issues,
            'field_coverage': field_coverage or {},
            'character_analysis': character_analysis or {},
            'timestamp': datetime.now().isoformat()
        })
    
    def record_date_format(self, date_str: str, file: str):
        """Record a date format encountered."""
        self.statistics['date_formats'][date_str] += 1
    
    def record_bbox_issue(self, file: str, issue: str, coordinates: Dict):
        """Record a bounding box issue."""
        self.statistics['bbox_issues'].append({
            'file': file,
            'issue': issue,
            'coordinates': coordinates
        })
    
    def record_missing_creator(self, file: str, context: str):
        """Record a missing creator issue."""
        self.statistics['missing_creators'].append({
            'file': file,
            'context': context
        })
    
    def record_license_detected(self):
        """Record that a license was successfully detected."""
        self.statistics['license_detected'] += 1
    
    def finalize(self):
        """Finalize logging and generate reports."""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        # Save structured logs
        self._save_warnings()
        self._save_errors()
        self._save_statistics()
        self._update_progress_csv(duration)
        self._generate_analysis_report()
        
        self.logger.info(f"Transformation completed. Duration: {duration:.1f}s")
        self.logger.info(f"Files processed: {self.statistics['total_files']}")
        self.logger.info(f"Successful: {self.statistics['successful']}")
        self.logger.info(f"Failed: {self.statistics['failed']}")
        self.logger.info(f"Warnings: {len(self.warnings)}")
        self.logger.info(f"Errors: {len(self.errors)}")
    
    def _save_warnings(self):
        """Save warnings to JSON file."""
        warnings_file = os.path.join(self.output_dir, "warnings.json")
        with open(warnings_file, 'w') as f:
            json.dump(self.warnings, f, indent=2)
    
    def _save_errors(self):
        """Save errors to JSON file."""
        errors_file = os.path.join(self.output_dir, "errors.json")
        with open(errors_file, 'w') as f:
            json.dump(self.errors, f, indent=2)
    
    def _save_statistics(self):
        """Save statistics to JSON file."""
        stats_file = os.path.join(self.output_dir, "statistics.json")
        
        # Convert defaultdict and Counter to regular dicts for JSON serialization
        stats = dict(self.statistics)
        stats['field_coverage'] = dict(stats['field_coverage'])
        stats['date_formats'] = dict(stats['date_formats'])
        stats['issues_by_type'] = dict(stats['issues_by_type'])
        
        with open(stats_file, 'w') as f:
            json.dump(stats, f, indent=2)
    
    def _update_progress_csv(self, duration: float):
        """Update the progress CSV file."""
        progress_file = os.path.join(self.output_dir, "progress.csv")
        
        # Calculate additional metrics
        avg_fields = (sum(self.statistics['field_coverage'].values()) / 
                     max(self.statistics['total_files'], 1))
        missing_creators = len(self.statistics['missing_creators'])
        invalid_dates = self.statistics['issues_by_type'].get('invalid_date_format', 0)
        bbox_issues = len(self.statistics['bbox_issues'])
        
        # Calculate field coverage and character metrics
        avg_field_coverage = 0
        avg_characters = 0
        files_over_limits = 0
        
        if self.statistics['successful'] > 0:
            total_coverage = 0
            total_chars = 0
            for file_data in self.statistics['files_processed']:
                if file_data['success'] and 'field_coverage' in file_data:
                    coverage = file_data['field_coverage']
                    if 'coverage_percentage' in coverage:
                        total_coverage += coverage['coverage_percentage']
                
                if 'character_analysis' in file_data:
                    char_analysis = file_data['character_analysis']
                    if 'total_characters' in char_analysis:
                        total_chars += char_analysis['total_characters']
                    
                    if 'fields_over_limit' in char_analysis and char_analysis['fields_over_limit']:
                        files_over_limits += 1
            
            avg_field_coverage = total_coverage / self.statistics['successful']
            avg_characters = total_chars / self.statistics['successful']
        
        # Check if file exists to determine if we need headers
        file_exists = os.path.exists(progress_file)
        
        with open(progress_file, 'a', newline='') as f:
            writer = csv.writer(f)
            
            if not file_exists:
                # Write header
                writer.writerow([
                    'timestamp', 'run_id', 'total_files', 'successful', 'warnings', 
                    'errors', 'avg_fields_per_record', 'missing_creators', 
                    'invalid_dates', 'bbox_issues', 'license_detected', 'duration_seconds',
                    'avg_field_coverage_pct', 'avg_characters_per_file', 'files_over_field_limits',
                    'avg_fgdc_total_chars', 'avg_zenodo_total_chars', 'avg_fgdc_data_chars', 'avg_zenodo_data_chars',
                    'avg_char_difference', 'avg_char_ratio', 'avg_data_preservation_ratio'
                ])
            
            # Calculate character analysis averages
            char_analysis = self.statistics['character_analysis']
            avg_fgdc_total_chars = char_analysis['total_fgdc_chars'] / max(1, self.statistics['successful'])
            avg_zenodo_total_chars = char_analysis['total_zenodo_chars'] / max(1, self.statistics['successful'])
            avg_fgdc_data_chars = char_analysis['total_fgdc_data_chars'] / max(1, self.statistics['successful'])
            avg_zenodo_data_chars = char_analysis['total_zenodo_data_chars'] / max(1, self.statistics['successful'])
            avg_char_difference = sum(char_analysis['char_differences']) / max(1, len(char_analysis['char_differences']))
            avg_char_ratio = sum(char_analysis['char_ratios']) / max(1, len(char_analysis['char_ratios']))
            avg_data_preservation_ratio = sum(char_analysis['data_preservation_ratios']) / max(1, len(char_analysis['data_preservation_ratios']))
            
            # Write data row
            writer.writerow([
                self.start_time.isoformat(),
                self.run_id,
                self.statistics['total_files'],
                self.statistics['successful'],
                len(self.warnings),
                len(self.errors),
                round(avg_fields, 1),
                missing_creators,
                invalid_dates,
                bbox_issues,
                self.statistics['license_detected'],
                round(duration, 1),
                round(avg_field_coverage, 1),
                round(avg_characters, 0),
                files_over_limits,
                round(avg_fgdc_total_chars, 0),
                round(avg_zenodo_total_chars, 0),
                round(avg_fgdc_data_chars, 0),
                round(avg_zenodo_data_chars, 0),
                round(avg_char_difference, 0),
                round(avg_char_ratio, 3),
                round(avg_data_preservation_ratio, 3)
            ])
    
    def _generate_analysis_report(self):
        """Generate a human-readable analysis report."""
        report_file = os.path.join(self.output_dir, f"analysis_{self.run_id}.txt")
        
        with open(report_file, 'w') as f:
            f.write("=== FGDC to Zenodo Transformation Analysis ===\n")
            f.write(f"Run ID: {self.run_id}\n")
            f.write(f"Date: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Top issues
            f.write("TOP 10 ISSUES:\n")
            top_issues = self.statistics['issues_by_type'].most_common(10)
            for i, (issue_type, count) in enumerate(top_issues, 1):
                f.write(f"{i}. [{count} files] {issue_type}\n")
                
                # Find example files for this issue
                example_files = []
                for warning in self.warnings:
                    if warning['issue_type'] == issue_type:
                        example_files.append(warning['file'])
                        if len(example_files) >= 3:
                            break
                
                if example_files:
                    f.write(f"   Files: {', '.join(example_files[:3])}")
                    if len(example_files) > 3:
                        f.write(f" ... (+{len(example_files)-3} more)")
                    f.write("\n")
                
                # Add suggestion if available
                for warning in self.warnings:
                    if warning['issue_type'] == issue_type and warning['suggestion']:
                        f.write(f"   Fix: {warning['suggestion']}\n")
                        break
                f.write("\n")
            
            # Field coverage
            f.write("FIELD COVERAGE:\n")
            total_files = self.statistics['total_files']
            for field, count in sorted(self.statistics['field_coverage'].items()):
                percentage = (count / total_files * 100) if total_files > 0 else 0
                missing = total_files - count
                f.write(f"- {field}: {percentage:.1f}% ({count}/{total_files})")
                if missing > 0:
                    f.write(f" [{missing} missing]")
                f.write("\n")
            
            # Summary statistics
            f.write(f"\nSUMMARY:\n")
            f.write(f"- Total files: {self.statistics['total_files']}\n")
            f.write(f"- Successful: {self.statistics['successful']}\n")
            f.write(f"- Failed: {self.statistics['failed']}\n")
            f.write(f"- Warnings: {len(self.warnings)}\n")
            f.write(f"- Errors: {len(self.errors)}\n")
            f.write(f"- License detection rate: {self.statistics['license_detected']}/{total_files}\n")


# Global logger instance
logger = None

def get_logger() -> TransformationLogger:
    """Get the global logger instance."""
    global logger
    if logger is None:
        logger = TransformationLogger()
    return logger

def initialize_logger(output_dir: str = "logs") -> TransformationLogger:
    """Initialize the global logger with custom output directory."""
    global logger
    logger = TransformationLogger(output_dir)
    return logger
