#!/usr/bin/env python3
"""
Enhanced Metrics Analysis Script.
Analyzes enhanced metrics across all transformed records to provide comprehensive insights.
"""

import os
import json
import glob
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict, Counter
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.enhanced_metrics import generate_metrics_summary
from scripts.logger import initialize_logger, get_logger


class MetricsAnalyzer:
    """Analyzes enhanced metrics across all transformed records."""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self.logger = get_logger()
        self.zenodo_json_dir = os.path.join(output_dir, "zenodo_json")
    
    def analyze_all_metrics(self) -> Dict[str, Any]:
        """Analyze enhanced metrics across all transformed records."""
        
        print("🔍 Analyzing enhanced metrics across all transformed records...")
        
        # Find all transformed JSON files
        json_files = glob.glob(os.path.join(self.zenodo_json_dir, "*.json"))
        print(f"Found {len(json_files)} transformed records")
        
        all_metrics = []
        failed_analyses = []
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if 'enhanced_metrics' in data:
                    all_metrics.append(data['enhanced_metrics'])
                else:
                    # Legacy record without enhanced metrics
                    failed_analyses.append({
                        'file': os.path.basename(json_file),
                        'reason': 'No enhanced_metrics found'
                    })
                    
            except Exception as e:
                failed_analyses.append({
                    'file': os.path.basename(json_file),
                    'reason': f'Error reading file: {str(e)}'
                })
        
        print(f"Successfully analyzed {len(all_metrics)} records")
        if failed_analyses:
            print(f"Failed to analyze {len(failed_analyses)} records")
        
        # Generate comprehensive analysis
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'total_records_analyzed': len(all_metrics),
            'failed_analyses': failed_analyses,
            'summary_statistics': generate_metrics_summary(all_metrics),
            'detailed_analysis': self._generate_detailed_analysis(all_metrics),
            'quality_distribution': self._analyze_quality_distribution(all_metrics),
            'field_coverage_analysis': self._analyze_field_coverage(all_metrics),
            'compliance_analysis': self._analyze_compliance(all_metrics),
            'transformation_effectiveness': self._analyze_transformation_effectiveness(all_metrics),
            'recommendations': self._generate_recommendations(all_metrics)
        }
        
        return analysis
    
    def _generate_detailed_analysis(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate detailed analysis of metrics."""
        
        analysis = {
            'data_preservation_stats': {},
            'quality_scores': {},
            'file_size_analysis': {},
            'issue_patterns': {}
        }
        
        if not metrics_list:
            return analysis
        
        # Data preservation statistics
        preservation_ratios = [m['data_preservation']['content_preservation_ratio'] for m in metrics_list]
        analysis['data_preservation_stats'] = {
            'avg_preservation_ratio': round(sum(preservation_ratios) / len(preservation_ratios), 3),
            'min_preservation_ratio': min(preservation_ratios),
            'max_preservation_ratio': max(preservation_ratios),
            'records_with_data_loss': sum(1 for r in preservation_ratios if r < 0.8),
            'records_with_data_gain': sum(1 for r in preservation_ratios if r > 1.5)
        }
        
        # Quality scores
        quality_scores = [m['data_quality']['overall_quality_score'] for m in metrics_list]
        analysis['quality_scores'] = {
            'average_quality_score': round(sum(quality_scores) / len(quality_scores), 1),
            'min_quality_score': min(quality_scores),
            'max_quality_score': max(quality_scores),
            'high_quality_records': sum(1 for s in quality_scores if s >= 90),
            'low_quality_records': sum(1 for s in quality_scores if s < 70)
        }
        
        # File size analysis
        fgdc_sizes = [m['file_info']['fgdc_size_kb'] for m in metrics_list]
        zenodo_sizes = [m['file_info']['zenodo_size_kb'] for m in metrics_list]
        
        analysis['file_size_analysis'] = {
            'avg_fgdc_size_kb': round(sum(fgdc_sizes) / len(fgdc_sizes), 2),
            'avg_zenodo_size_kb': round(sum(zenodo_sizes) / len(zenodo_sizes), 2),
            'size_compression_ratio': round(sum(zenodo_sizes) / sum(fgdc_sizes), 3),
            'largest_fgdc_file': max(fgdc_sizes),
            'smallest_fgdc_file': min(fgdc_sizes)
        }
        
        return analysis
    
    def _analyze_quality_distribution(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze quality grade distribution."""
        
        grade_counts = Counter(m['data_quality']['quality_grade'] for m in metrics_list)
        total = len(metrics_list)
        
        distribution = {}
        for grade in ['A', 'B', 'C', 'D', 'F']:
            count = grade_counts.get(grade, 0)
            distribution[grade] = {
                'count': count,
                'percentage': round((count / total) * 100, 1) if total > 0 else 0
            }
        
        return distribution
    
    def _analyze_field_coverage(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze field coverage patterns."""
        
        if not metrics_list:
            return {}
        
        coverage_data = [m['field_coverage'] for m in metrics_list]
        
        # Analyze missing fields
        missing_critical = defaultdict(int)
        missing_important = defaultdict(int)
        
        for coverage in coverage_data:
            for field in coverage.get('missing_critical_fields', []):
                missing_critical[field] += 1
            for field in coverage.get('missing_important_fields', []):
                missing_important[field] += 1
        
        return {
            'avg_critical_coverage': round(sum(c['critical_fields_percentage'] for c in coverage_data) / len(coverage_data), 1),
            'avg_important_coverage': round(sum(c['important_fields_percentage'] for c in coverage_data) / len(coverage_data), 1),
            'avg_optional_coverage': round(sum(c['optional_fields_percentage'] for c in coverage_data) / len(coverage_data), 1),
            'most_missing_critical_fields': dict(missing_critical.most_common(5)),
            'most_missing_important_fields': dict(missing_important.most_common(5)),
            'complete_coverage_records': sum(1 for c in coverage_data if c['overall_coverage_percentage'] == 100.0)
        }
    
    def _analyze_compliance(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze compliance patterns."""
        
        if not metrics_list:
            return {}
        
        compliance_data = [m['compliance'] for m in metrics_list]
        
        return {
            'avg_zenodo_required_compliance': round(sum(c['zenodo_required_percentage'] for c in compliance_data) / len(compliance_data), 1),
            'avg_zenodo_recommended_compliance': round(sum(c['zenodo_recommended_percentage'] for c in compliance_data) / len(compliance_data), 1),
            'pices_community_compliance': round((sum(1 for c in compliance_data if c['pices_community_present']) / len(compliance_data)) * 100, 1),
            'open_access_compliance': round((sum(1 for c in compliance_data if c['open_access_compliant']) / len(compliance_data)) * 100, 1),
            'license_compliance': round((sum(1 for c in compliance_data if c['license_compliant']) / len(compliance_data)) * 100, 1),
            'fully_compliant_records': sum(1 for c in compliance_data if c['overall_compliance_score'] == 100.0)
        }
    
    def _analyze_transformation_effectiveness(self, metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze transformation effectiveness."""
        
        if not metrics_list:
            return {}
        
        effectiveness_data = [m['transformation_effectiveness'] for m in metrics_list]
        
        return {
            'avg_mapping_completeness': round(sum(e['mapping_completeness'] for e in effectiveness_data) / len(effectiveness_data), 1),
            'avg_data_enrichment': round(sum(e['data_enrichment_score'] for e in effectiveness_data) / len(effectiveness_data), 1),
            'avg_format_compliance': round(sum(e['format_compliance'] for e in effectiveness_data) / len(effectiveness_data), 1),
            'avg_semantic_accuracy': round(sum(e['semantic_accuracy'] for e in effectiveness_data) / len(effectiveness_data), 1),
            'high_effectiveness_records': sum(1 for e in effectiveness_data if e['overall_effectiveness_score'] >= 90)
        }
    
    def _generate_recommendations(self, metrics_list: List[Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        
        recommendations = []
        
        if not metrics_list:
            return ["No data available for analysis"]
        
        # Analyze patterns and generate recommendations
        quality_scores = [m['data_quality']['overall_quality_score'] for m in metrics_list]
        avg_quality = sum(quality_scores) / len(quality_scores)
        
        if avg_quality < 80:
            recommendations.append("Overall data quality is below 80%. Review transformation logic for common quality issues.")
        
        # Check field coverage
        coverage_data = [m['field_coverage'] for m in metrics_list]
        avg_critical_coverage = sum(c['critical_fields_percentage'] for c in coverage_data) / len(coverage_data)
        
        if avg_critical_coverage < 100:
            recommendations.append("Critical fields are missing in some records. Ensure all required fields are properly mapped.")
        
        # Check compliance
        compliance_data = [m['compliance'] for m in metrics_list]
        pices_compliance = sum(1 for c in compliance_data if c['pices_community_present']) / len(compliance_data)
        
        if pices_compliance < 0.95:
            recommendations.append("PICES community is missing from some records. Ensure community membership is properly set.")
        
        # Check data preservation
        preservation_ratios = [m['data_preservation']['content_preservation_ratio'] for m in metrics_list]
        data_loss_count = sum(1 for r in preservation_ratios if r < 0.8)
        
        if data_loss_count > len(metrics_list) * 0.1:  # More than 10% have significant data loss
            recommendations.append("Significant data loss detected in multiple records. Review field mapping completeness.")
        
        # Check for data expansion issues
        data_gain_count = sum(1 for r in preservation_ratios if r > 2.0)
        if data_gain_count > len(metrics_list) * 0.2:  # More than 20% have excessive data expansion
            recommendations.append("Excessive data expansion detected. Review transformation logic for data duplication.")
        
        if not recommendations:
            recommendations.append("All metrics look good! No major issues detected.")
        
        return recommendations
    
    def save_analysis_report(self, analysis: Dict[str, Any], output_file: str = None) -> str:
        """Save analysis report to file."""
        
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(self.output_dir, f"enhanced_metrics_analysis_{timestamp}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        return output_file
    
    def print_analysis_summary(self, analysis: Dict[str, Any]):
        """Print a human-readable analysis summary."""
        
        print("\n" + "="*80)
        print("ENHANCED METRICS ANALYSIS SUMMARY")
        print("="*80)
        print(f"Analysis Date: {analysis['timestamp']}")
        print(f"Records Analyzed: {analysis['total_records_analyzed']}")
        
        if analysis['failed_analyses']:
            print(f"Failed Analyses: {len(analysis['failed_analyses'])}")
        
        # Summary statistics
        summary = analysis['summary_statistics']
        if summary:
            print(f"\n📊 OVERALL SCORES:")
            print(f"   Average Score: {summary['overall_scores']['average']}")
            print(f"   Median Score: {summary['overall_scores']['median']}")
            print(f"   Score Range: {summary['overall_scores']['min']} - {summary['overall_scores']['max']}")
            print(f"   Standard Deviation: {summary['overall_scores']['std_dev']}")
        
        # Quality distribution
        quality_dist = analysis['quality_distribution']
        print(f"\n🎯 QUALITY DISTRIBUTION:")
        for grade in ['A', 'B', 'C', 'D', 'F']:
            dist = quality_dist.get(grade, {})
            print(f"   Grade {grade}: {dist.get('count', 0)} records ({dist.get('percentage', 0)}%)")
        
        # Field coverage
        field_coverage = analysis['field_coverage_analysis']
        if field_coverage:
            print(f"\n📋 FIELD COVERAGE:")
            print(f"   Critical Fields: {field_coverage['avg_critical_coverage']}%")
            print(f"   Important Fields: {field_coverage['avg_important_coverage']}%")
            print(f"   Optional Fields: {field_coverage['avg_optional_coverage']}%")
            print(f"   Complete Coverage: {field_coverage['complete_coverage_records']} records")
        
        # Compliance
        compliance = analysis['compliance_analysis']
        if compliance:
            print(f"\n✅ COMPLIANCE:")
            print(f"   Zenodo Required: {compliance['avg_zenodo_required_compliance']}%")
            print(f"   Zenodo Recommended: {compliance['avg_zenodo_recommended_compliance']}%")
            print(f"   PICES Community: {compliance['pices_community_compliance']}%")
            print(f"   Open Access: {compliance['open_access_compliance']}%")
            print(f"   License Compliant: {compliance['license_compliance']}%")
        
        # Recommendations
        recommendations = analysis['recommendations']
        print(f"\n💡 RECOMMENDATIONS:")
        for i, rec in enumerate(recommendations, 1):
            print(f"   {i}. {rec}")
        
        print("\n" + "="*80)


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Analyze enhanced metrics across all transformed records"
    )
    parser.add_argument(
        '--output-dir',
        default='output',
        help='Output directory (default: output)'
    )
    parser.add_argument(
        '--save-report',
        action='store_true',
        help='Save detailed report to JSON file'
    )
    parser.add_argument(
        '--report-file',
        help='Custom report file path (requires --save-report)'
    )
    
    args = parser.parse_args()
    
    # Initialize logger
    initialize_logger(os.path.join(args.output_dir, 'logs'))
    
    try:
        # Create analyzer
        analyzer = MetricsAnalyzer(args.output_dir)
        
        # Run analysis
        analysis = analyzer.analyze_all_metrics()
        
        # Print summary
        analyzer.print_analysis_summary(analysis)
        
        # Save report if requested
        if args.save_report:
            report_file = analyzer.save_analysis_report(analysis, args.report_file)
            print(f"\n📄 Detailed report saved to: {report_file}")
        
        # Exit with appropriate code
        if analysis['total_records_analyzed'] > 0:
            exit(0)
        else:
            exit(1)
            
    except Exception as e:
        print(f"Fatal error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
