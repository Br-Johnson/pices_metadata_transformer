#!/usr/bin/env python3
"""
Generate exclusion lists for files that cannot be transformed or validated.
"""

import json
import os
import glob
from collections import defaultdict

def generate_exclusion_lists():
    """Generate lists of files to exclude from upload."""
    
    # Lists to track problematic files
    transformation_failures = []
    validation_failures = []
    parse_errors = []
    
    # Check for transformation failures in logs
    if os.path.exists('logs/errors.json'):
        with open('logs/errors.json', 'r') as f:
            errors = json.load(f)
        
        for error in errors:
            file_name = error['file'].split('/')[-1]  # Get just the filename
            if error['issue_type'] == 'parse_error':
                parse_errors.append(file_name)
            elif error['issue_type'] == 'transformation_failed':
                transformation_failures.append(file_name)
    
    # Check for validation failures
    if os.path.exists('output/validation_report.json'):
        with open('output/validation_report.json', 'r') as f:
            validation_report = json.load(f)
        
        # Get files with validation issues
        for result in validation_report.get('results', []):
            if not result.get('is_valid', True):
                file_name = result['file'].split('/')[-1]
                validation_failures.append(file_name)
    
    # Get all FGDC files
    all_fgdc_files = [os.path.basename(f) for f in glob.glob('FGDC/*.xml')]
    
    # Get successfully transformed files
    transformed_files = [os.path.basename(f) for f in glob.glob('output/zenodo_json/*.json')]
    
    # Find files that weren't transformed
    untransformed_files = [f for f in all_fgdc_files if f.replace('.xml', '.json') not in transformed_files]
    
    # Create exclusion lists
    exclusion_lists = {
        'transformation_failures': list(set(transformation_failures)),
        'validation_failures': list(set(validation_failures)),
        'parse_errors': list(set(parse_errors)),
        'untransformed_files': list(set(untransformed_files)),
        'all_problematic_files': list(set(transformation_failures + validation_failures + parse_errors + untransformed_files))
    }
    
    # Save exclusion lists
    with open('exclusion_lists.json', 'w') as f:
        json.dump(exclusion_lists, f, indent=2)
    
    # Generate summary report
    summary = {
        'total_fgdc_files': len(all_fgdc_files),
        'successfully_transformed': len(transformed_files),
        'transformation_failures': len(exclusion_lists['transformation_failures']),
        'validation_failures': len(exclusion_lists['validation_failures']),
        'parse_errors': len(exclusion_lists['parse_errors']),
        'untransformed_files': len(exclusion_lists['untransformed_files']),
        'total_problematic_files': len(exclusion_lists['all_problematic_files']),
        'success_rate': len(transformed_files) / len(all_fgdc_files) * 100 if all_fgdc_files else 0
    }
    
    with open('exclusion_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Print summary
    print("=== Exclusion Lists Generated ===")
    print(f"Total FGDC files: {summary['total_fgdc_files']}")
    print(f"Successfully transformed: {summary['successfully_transformed']}")
    print(f"Transformation failures: {summary['transformation_failures']}")
    print(f"Validation failures: {summary['validation_failures']}")
    print(f"Parse errors: {summary['parse_errors']}")
    print(f"Untransformed files: {summary['untransformed_files']}")
    print(f"Total problematic files: {summary['total_problematic_files']}")
    print(f"Success rate: {summary['success_rate']:.1f}%")
    
    print(f"\nFiles saved to:")
    print(f"- exclusion_lists.json (detailed lists)")
    print(f"- exclusion_summary.json (summary statistics)")
    
    return exclusion_lists, summary

if __name__ == "__main__":
    generate_exclusion_lists()
