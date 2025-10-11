"""
Batch processor for transforming FGDC XML files to Zenodo JSON format.
Orchestrates the transformation of all 4,206 files with comprehensive logging.
"""

import os
import json
import shutil
import argparse
import glob
from datetime import datetime
from typing import List, Dict, Any
from tqdm import tqdm
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.fgdc_to_zenodo import transform_fgdc_file
from scripts.logger import initialize_logger, get_logger
from scripts.validate_zenodo import validate_zenodo_directory


class BatchTransformer:
    """Handles batch transformation of FGDC XML files."""
    
    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.logger = get_logger()
        
        # Create output directories
        self.zenodo_json_dir = os.path.join(output_dir, 'zenodo_json')
        self.original_fgdc_dir = os.path.join(output_dir, 'original_fgdc')
        self.validation_report_path = os.path.join(output_dir, 'validation_report.json')
        
        os.makedirs(self.zenodo_json_dir, exist_ok=True)
        os.makedirs(self.original_fgdc_dir, exist_ok=True)
    
    def discover_xml_files(self) -> List[str]:
        """Discover all XML files in the input directory."""
        xml_pattern = os.path.join(self.input_dir, '*.xml')
        xml_files = glob.glob(xml_pattern)
        
        if not xml_files:
            raise FileNotFoundError(f"No XML files found in {self.input_dir}")
        
        # Sort files for consistent processing order
        xml_files.sort()
        
        self.logger.log_info(f"Discovered {len(xml_files)} XML files in {self.input_dir}")
        return xml_files
    
    def transform_files(self, xml_files: List[str], limit: int = None) -> Dict[str, Any]:
        """Transform XML files to Zenodo JSON format."""
        if limit:
            xml_files = xml_files[:limit]
            self.logger.log_info(f"Processing limited to {limit} files")
        
        successful_transforms = 0
        failed_transforms = 0
        files_processed = []
        
        # Process files with progress bar
        for xml_file in tqdm(xml_files, desc="Transforming FGDC files"):
            try:
                # Get base filename
                base_name = os.path.splitext(os.path.basename(xml_file))[0]
                json_file = os.path.join(self.zenodo_json_dir, f"{base_name}.json")
                
                # Transform the file
                result = transform_fgdc_file(xml_file)
                
                if result:
                    # Save transformed JSON
                    with open(json_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, indent=2, ensure_ascii=False)
                    
                    # Copy original FGDC XML for upload
                    original_copy = os.path.join(self.original_fgdc_dir, os.path.basename(xml_file))
                    shutil.copy2(xml_file, original_copy)
                    
                    successful_transforms += 1
                    files_processed.append({
                        'xml_file': xml_file,
                        'json_file': json_file,
                        'original_copy': original_copy,
                        'status': 'success'
                    })
                    
                    # Record successful processing with comprehensive analysis
                    fields_present = self._count_fields_present(result['metadata'])
                    
                    # Get field coverage and character analysis from validation
                    field_coverage = None
                    character_analysis = None
                    
                    # Get character analysis from transformation result
                    character_analysis = result.get('character_analysis', {})
                    
                    # Validate the file to get detailed analysis
                    try:
                        from validate_zenodo import validate_zenodo_file
                        validation_result = validate_zenodo_file(json_file)
                        field_coverage = validation_result.get('field_coverage', {})
                        # Use character analysis from transformation result if available
                        if not character_analysis:
                            character_analysis = validation_result.get('character_analysis', {})
                    except Exception as e:
                        self.logger.log_warning(f"Could not get detailed analysis for {xml_file}: {e}")
                    
                    self.logger.record_file_processed(
                        os.path.basename(xml_file), True, fields_present, [],
                        field_coverage, character_analysis
                    )
                else:
                    failed_transforms += 1
                    files_processed.append({
                        'xml_file': xml_file,
                        'json_file': None,
                        'original_copy': None,
                        'status': 'failed'
                    })
                    
                    # Record failed processing
                    self.logger.record_file_processed(
                        os.path.basename(xml_file), False, [], ['transformation_failed']
                    )
                
            except Exception as e:
                failed_transforms += 1
                files_processed.append({
                    'xml_file': xml_file,
                    'json_file': None,
                    'original_copy': None,
                    'status': 'error',
                    'error': str(e)
                })
                
                self.logger.log_error(
                    xml_file, "batch_processing", "processing_error",
                    str(e), "Successful file processing",
                    "Review error details and fix transformation logic"
                )
                
                # Record failed processing
                self.logger.record_file_processed(
                    os.path.basename(xml_file), False, [], [f'processing_error: {str(e)}']
                )
        
        # Finalize logging
        self.logger.finalize()
        
        # Generate summary
        summary = {
            'total_files': len(xml_files),
            'successful_transforms': successful_transforms,
            'failed_transforms': failed_transforms,
            'success_rate': (successful_transforms / len(xml_files) * 100) if xml_files else 0,
            'files_processed': files_processed,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.log_info(f"Batch transformation completed:")
        self.logger.log_info(f"  Total files: {summary['total_files']}")
        self.logger.log_info(f"  Successful: {summary['successful_transforms']}")
        self.logger.log_info(f"  Failed: {summary['failed_transforms']}")
        self.logger.log_info(f"  Success rate: {summary['success_rate']:.1f}%")
        
        return summary
    
    def _count_fields_present(self, metadata: Dict[str, Any]) -> List[str]:
        """Count which fields are present in the metadata."""
        fields = []
        
        # Check all possible Zenodo fields
        zenodo_fields = [
            'title', 'upload_type', 'publication_date', 'creators', 'description',
            'access_right', 'license', 'keywords', 'notes', 'related_identifiers',
            'contributors', 'references', 'communities', 'version', 'language',
            'locations', 'dates', 'method', 'journal_title', 'journal_volume',
            'journal_issue', 'journal_pages', 'conference_title', 'conference_acronym',
            'conference_dates', 'conference_place', 'conference_url', 'imprint_publisher',
            'imprint_isbn', 'imprint_place', 'partof_title', 'partof_pages',
            'thesis_supervisors', 'thesis_university', 'subjects', 'grants'
        ]
        
        for field in zenodo_fields:
            if field in metadata and metadata[field]:
                fields.append(field)
        
        return fields
    
    def validate_transformations(self) -> Dict[str, Any]:
        """Validate all transformed JSON files."""
        self.logger.log_info("Starting validation of transformed files...")
        
        try:
            validation_summary = validate_zenodo_directory(
                self.zenodo_json_dir, 
                self.validation_report_path
            )
            
            self.logger.log_info("Validation completed successfully")
            return validation_summary
            
        except Exception as e:
            self.logger.log_error(
                "validation", "validation_process", "validation_error",
                str(e), "Successful validation",
                "Review validation logic and file formats"
            )
            raise
    
    def generate_summary_report(self, transform_summary: Dict[str, Any], 
                              validation_summary: Dict[str, Any] = None) -> str:
        """Generate a comprehensive summary report."""
        report_lines = []
        report_lines.append("=== FGDC to Zenodo Batch Transformation Report ===")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Transformation summary
        report_lines.append("TRANSFORMATION SUMMARY:")
        report_lines.append(f"  Total files processed: {transform_summary['total_files']}")
        report_lines.append(f"  Successful transformations: {transform_summary['successful_transforms']}")
        report_lines.append(f"  Failed transformations: {transform_summary['failed_transforms']}")
        report_lines.append(f"  Success rate: {transform_summary['success_rate']:.1f}%")
        report_lines.append("")
        
        # Validation summary
        if validation_summary:
            report_lines.append("VALIDATION SUMMARY:")
            report_lines.append(f"  Total files validated: {validation_summary['summary']['total_files']}")
            report_lines.append(f"  Valid files: {validation_summary['summary']['valid_files']}")
            report_lines.append(f"  Invalid files: {validation_summary['summary']['invalid_files']}")
            report_lines.append(f"  Validation rate: {validation_summary['summary']['validation_rate']:.1f}%")
            report_lines.append(f"  Total issues: {validation_summary['summary']['total_issues']}")
            report_lines.append(f"  Total warnings: {validation_summary['summary']['total_warnings']}")
            report_lines.append("")
            
            # Top issues
            if validation_summary['issue_types']:
                report_lines.append("TOP VALIDATION ISSUES:")
                for issue_type, count in sorted(validation_summary['issue_types'].items(), 
                                              key=lambda x: x[1], reverse=True)[:10]:
                    report_lines.append(f"  {issue_type}: {count}")
                report_lines.append("")
        
        # File locations
        report_lines.append("OUTPUT FILES:")
        report_lines.append(f"  Transformed JSON files: {self.zenodo_json_dir}")
        report_lines.append(f"  Original FGDC copies: {self.original_fgdc_dir}")
        if validation_summary:
            report_lines.append(f"  Validation report: {self.validation_report_path}")
        report_lines.append(f"  Logs directory: logs/")
        report_lines.append("")
        
        # Next steps
        report_lines.append("NEXT STEPS:")
        if transform_summary['failed_transforms'] > 0:
            report_lines.append("  1. Review failed transformations in logs/errors.json")
            report_lines.append("  2. Fix transformation logic for common issues")
            report_lines.append("  3. Re-run transformation for failed files")
        else:
            report_lines.append("  1. Review validation issues if any")
            report_lines.append("  2. Test upload to Zenodo sandbox")
            report_lines.append("  3. Proceed with full upload")
        
        report_text = "\n".join(report_lines)
        
        # Save report
        report_path = os.path.join(self.output_dir, 'transformation_summary.txt')
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        self.logger.log_info(f"Summary report saved to {report_path}")
        return report_text


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Batch transform FGDC XML files to Zenodo JSON format"
    )
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input directory containing FGDC XML files'
    )
    parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output directory for transformed files'
    )
    parser.add_argument(
        '--limit', '-l',
        type=int,
        help='Limit number of files to process (for testing)'
    )
    parser.add_argument(
        '--skip-validation',
        action='store_true',
        help='Skip validation step'
    )
    parser.add_argument(
        '--log-dir',
        default='logs',
        help='Directory for log files (default: logs)'
    )
    
    args = parser.parse_args()
    
    # Initialize logger
    initialize_logger(args.log_dir)
    logger = get_logger()
    
    try:
        # Create batch transformer
        transformer = BatchTransformer(args.input, args.output)
        
        # Discover XML files
        xml_files = transformer.discover_xml_files()
        
        # Transform files
        logger.log_info("Starting batch transformation...")
        transform_summary = transformer.transform_files(xml_files, args.limit)
        
        # Validate transformations
        validation_summary = None
        if not args.skip_validation:
            validation_summary = transformer.validate_transformations()
        
        # Generate summary report
        summary_report = transformer.generate_summary_report(
            transform_summary, validation_summary
        )
        
        # Print summary to console
        print("\n" + summary_report)
        
        # Exit with appropriate code
        if transform_summary['failed_transforms'] > 0:
            logger.log_info("Batch transformation completed with some failures")
            exit(1)
        else:
            logger.log_info("Batch transformation completed successfully")
            exit(0)
            
    except Exception as e:
        logger.log_error(
            "batch_transform", "main_process", "fatal_error",
            str(e), "Successful batch processing",
            "Review error details and fix issues"
        )
        print(f"Fatal error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
