#!/usr/bin/env python3
"""
Enhanced Metrics System for FGDC to Zenodo Migration.
Provides meaningful, well-defined metrics with clear rationale and percentages.
"""

import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class EnhancedMetricsCalculator:
    """Enhanced metrics calculator with meaningful, well-defined metrics."""
    
    def __init__(self):
        # Define field importance weights for quality scoring
        self.field_weights = {
            'critical': {
                'title': 20,
                'creators': 20, 
                'publication_date': 15,
                'description': 15
            },
            'important': {
                'keywords': 10,
                'access_right': 8,
                'license': 7,
                'communities': 5
            },
            'optional': {
                'notes': 3,
                'related_identifiers': 2,
                'contributors': 2,
                'references': 1,
                'version': 1,
                'imprint_publisher': 1
            }
        }
        
        # Define data quality thresholds
        self.quality_thresholds = {
            'excellent': 90,
            'good': 75,
            'fair': 60,
            'poor': 0
        }
    
    def calculate_comprehensive_metrics(self, fgdc_content: str, zenodo_metadata: Dict[str, Any], 
                                      file_path: str) -> Dict[str, Any]:
        """Calculate comprehensive metrics for a single record."""
        
        metrics = {
            'file_info': self._analyze_file_info(fgdc_content, zenodo_metadata, file_path),
            'data_preservation': self._calculate_data_preservation_metrics(fgdc_content, zenodo_metadata),
            'field_coverage': self._calculate_field_coverage_metrics(zenodo_metadata),
            'data_quality': self._calculate_data_quality_metrics(fgdc_content, zenodo_metadata),
            'transformation_effectiveness': self._calculate_transformation_effectiveness(fgdc_content, zenodo_metadata),
            'compliance': self._calculate_compliance_metrics(zenodo_metadata),
            'overall_score': 0
        }
        
        # Calculate overall score
        metrics['overall_score'] = self._calculate_overall_score(metrics)
        
        return metrics
    
    def _analyze_file_info(self, fgdc_content: str, zenodo_metadata: Dict[str, Any], 
                          file_path: str) -> Dict[str, Any]:
        """Analyze basic file information."""
        return {
            'fgdc_size_bytes': len(fgdc_content),
            'fgdc_size_kb': round(len(fgdc_content) / 1024, 2),
            'zenodo_size_bytes': len(json.dumps(zenodo_metadata, indent=2)),
            'zenodo_size_kb': round(len(json.dumps(zenodo_metadata, indent=2)) / 1024, 2),
            'filename': os.path.basename(file_path),
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_data_preservation_metrics(self, fgdc_content: str, 
                                           zenodo_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate meaningful data preservation metrics."""
        
        # Extract meaningful data from FGDC (not just character counts)
        fgdc_data = self._extract_meaningful_fgdc_data(fgdc_content)
        zenodo_data = self._extract_meaningful_zenodo_data(zenodo_metadata)
        
        # Calculate preservation ratios
        preservation_metrics = {
            'content_preservation_ratio': 0.0,
            'field_preservation_ratio': 0.0,
            'semantic_preservation_score': 0.0,
            'data_loss_indicators': [],
            'data_gain_indicators': []
        }
        
        # Content preservation (meaningful text content)
        if fgdc_data['total_meaningful_chars'] > 0:
            preservation_metrics['content_preservation_ratio'] = round(
                zenodo_data['total_meaningful_chars'] / fgdc_data['total_meaningful_chars'], 3
            )
        
        # Field preservation (how many FGDC fields made it to Zenodo)
        if fgdc_data['total_fields'] > 0:
            preservation_metrics['field_preservation_ratio'] = round(
                zenodo_data['mapped_fields'] / fgdc_data['total_fields'], 3
            )
        
        # Semantic preservation (quality of mapping)
        preservation_metrics['semantic_preservation_score'] = self._calculate_semantic_preservation(
            fgdc_data, zenodo_data
        )
        
        # Identify data loss/gain
        preservation_metrics['data_loss_indicators'] = self._identify_data_loss(fgdc_data, zenodo_data)
        preservation_metrics['data_gain_indicators'] = self._identify_data_gain(fgdc_data, zenodo_data)
        
        return preservation_metrics
    
    def _calculate_field_coverage_metrics(self, zenodo_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate enhanced field coverage metrics."""
        
        coverage = {
            'critical_fields_present': 0,
            'critical_fields_total': len(self.field_weights['critical']),
            'critical_fields_percentage': 0.0,
            'important_fields_present': 0,
            'important_fields_total': len(self.field_weights['important']),
            'important_fields_percentage': 0.0,
            'optional_fields_present': 0,
            'optional_fields_total': len(self.field_weights['optional']),
            'optional_fields_percentage': 0.0,
            'total_fields_present': 0,
            'total_fields_possible': 0,
            'overall_coverage_percentage': 0.0,
            'weighted_coverage_score': 0.0,
            'missing_critical_fields': [],
            'missing_important_fields': [],
            'present_optional_fields': []
        }
        
        # Count fields by category
        for category, fields in self.field_weights.items():
            for field, weight in fields.items():
                coverage['total_fields_possible'] += 1
                
                if zenodo_metadata.get(field) is not None:
                    coverage['total_fields_present'] += 1
                    
                    if category == 'critical':
                        coverage['critical_fields_present'] += 1
                    elif category == 'important':
                        coverage['important_fields_present'] += 1
                    elif category == 'optional':
                        coverage['optional_fields_present'] += 1
                        coverage['present_optional_fields'].append(field)
                else:
                    if category == 'critical':
                        coverage['missing_critical_fields'].append(field)
                    elif category == 'important':
                        coverage['missing_important_fields'].append(field)
        
        # Calculate percentages
        coverage['critical_fields_percentage'] = round(
            (coverage['critical_fields_present'] / coverage['critical_fields_total']) * 100, 1
        )
        coverage['important_fields_percentage'] = round(
            (coverage['important_fields_present'] / coverage['important_fields_total']) * 100, 1
        )
        coverage['optional_fields_percentage'] = round(
            (coverage['optional_fields_present'] / coverage['optional_fields_total']) * 100, 1
        )
        coverage['overall_coverage_percentage'] = round(
            (coverage['total_fields_present'] / coverage['total_fields_possible']) * 100, 1
        )
        
        # Calculate weighted coverage score
        total_weight = sum(weight for category in self.field_weights.values() for weight in category.values())
        present_weight = 0
        
        for category, fields in self.field_weights.items():
            for field, weight in fields.items():
                if zenodo_metadata.get(field) is not None:
                    present_weight += weight
        
        coverage['weighted_coverage_score'] = round((present_weight / total_weight) * 100, 1)
        
        return coverage
    
    def _calculate_data_quality_metrics(self, fgdc_content: str, 
                                      zenodo_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate data quality metrics."""
        
        quality = {
            'title_quality': self._assess_title_quality(zenodo_metadata.get('title', '')),
            'creator_quality': self._assess_creator_quality(zenodo_metadata.get('creators', [])),
            'description_quality': self._assess_description_quality(zenodo_metadata.get('description', '')),
            'keyword_quality': self._assess_keyword_quality(zenodo_metadata.get('keywords', [])),
            'date_quality': self._assess_date_quality(zenodo_metadata.get('publication_date', '')),
            'license_quality': self._assess_license_quality(zenodo_metadata.get('license', '')),
            'overall_quality_score': 0.0,
            'quality_grade': 'F'
        }
        
        # Calculate overall quality score
        quality_scores = [
            quality['title_quality']['score'],
            quality['creator_quality']['score'],
            quality['description_quality']['score'],
            quality['keyword_quality']['score'],
            quality['date_quality']['score'],
            quality['license_quality']['score']
        ]
        
        quality['overall_quality_score'] = round(sum(quality_scores) / len(quality_scores), 1)
        
        # Assign quality grade
        for grade, threshold in self.quality_thresholds.items():
            if quality['overall_quality_score'] >= threshold:
                quality['quality_grade'] = grade.upper()
                break
        
        return quality
    
    def _calculate_transformation_effectiveness(self, fgdc_content: str, 
                                              zenodo_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate transformation effectiveness metrics."""
        
        effectiveness = {
            'mapping_completeness': 0.0,
            'data_enrichment_score': 0.0,
            'format_compliance': 0.0,
            'semantic_accuracy': 0.0,
            'overall_effectiveness_score': 0.0
        }
        
        # Mapping completeness (how well FGDC fields were mapped)
        fgdc_fields = self._extract_fgdc_field_names(fgdc_content)
        mapped_fields = self._count_mapped_fields(zenodo_metadata)
        
        if len(fgdc_fields) > 0:
            effectiveness['mapping_completeness'] = round(
                (mapped_fields / len(fgdc_fields)) * 100, 1
            )
        
        # Data enrichment (how much additional value was added)
        effectiveness['data_enrichment_score'] = self._calculate_data_enrichment(fgdc_content, zenodo_metadata)
        
        # Format compliance (Zenodo schema compliance)
        effectiveness['format_compliance'] = self._calculate_format_compliance(zenodo_metadata)
        
        # Semantic accuracy (how well the meaning was preserved)
        effectiveness['semantic_accuracy'] = self._calculate_semantic_accuracy(fgdc_content, zenodo_metadata)
        
        # Overall effectiveness
        effectiveness['overall_effectiveness_score'] = round(
            (effectiveness['mapping_completeness'] + 
             effectiveness['data_enrichment_score'] + 
             effectiveness['format_compliance'] + 
             effectiveness['semantic_accuracy']) / 4, 1
        )
        
        return effectiveness
    
    def _calculate_compliance_metrics(self, zenodo_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate compliance metrics."""
        
        compliance = {
            'zenodo_required_fields': 0,
            'zenodo_required_total': 4,  # title, creators, publication_date, description
            'zenodo_required_percentage': 0.0,
            'zenodo_recommended_fields': 0,
            'zenodo_recommended_total': 6,  # keywords, license, access_right, communities, notes, related_identifiers
            'zenodo_recommended_percentage': 0.0,
            'pices_community_present': False,
            'open_access_compliant': False,
            'license_compliant': False,
            'overall_compliance_score': 0.0
        }
        
        # Required fields
        required_fields = ['title', 'creators', 'publication_date', 'description']
        for field in required_fields:
            if zenodo_metadata.get(field) is not None:
                compliance['zenodo_required_fields'] += 1
        
        compliance['zenodo_required_percentage'] = round(
            (compliance['zenodo_required_fields'] / compliance['zenodo_required_total']) * 100, 1
        )
        
        # Recommended fields
        recommended_fields = ['keywords', 'license', 'access_right', 'communities', 'notes', 'related_identifiers']
        for field in recommended_fields:
            if zenodo_metadata.get(field) is not None:
                compliance['zenodo_recommended_fields'] += 1
        
        compliance['zenodo_recommended_percentage'] = round(
            (compliance['zenodo_recommended_fields'] / compliance['zenodo_recommended_total']) * 100, 1
        )
        
        # Specific compliance checks
        compliance['pices_community_present'] = any(
            comm.get('identifier') == 'pices' 
            for comm in zenodo_metadata.get('communities', [])
        )
        
        compliance['open_access_compliant'] = zenodo_metadata.get('access_right') == 'open'
        
        compliance['license_compliant'] = zenodo_metadata.get('license') in [
            'cc-zero', 'cc-by-4.0', 'cc-by-sa-4.0', 'mit', 'apache-2.0', 'gpl-3.0'
        ]
        
        # Overall compliance score
        compliance_checks = [
            compliance['zenodo_required_percentage'] / 100,
            compliance['zenodo_recommended_percentage'] / 100,
            1.0 if compliance['pices_community_present'] else 0.0,
            1.0 if compliance['open_access_compliant'] else 0.0,
            1.0 if compliance['license_compliant'] else 0.0
        ]
        
        compliance['overall_compliance_score'] = round(sum(compliance_checks) / len(compliance_checks) * 100, 1)
        
        return compliance
    
    def _calculate_overall_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall score from all metrics."""
        
        # Weighted combination of different metric categories
        weights = {
            'data_preservation': 0.25,
            'field_coverage': 0.20,
            'data_quality': 0.25,
            'transformation_effectiveness': 0.20,
            'compliance': 0.10
        }
        
        scores = {
            'data_preservation': metrics['data_preservation']['content_preservation_ratio'] * 100,
            'field_coverage': metrics['field_coverage']['weighted_coverage_score'],
            'data_quality': metrics['data_quality']['overall_quality_score'],
            'transformation_effectiveness': metrics['transformation_effectiveness']['overall_effectiveness_score'],
            'compliance': metrics['compliance']['overall_compliance_score']
        }
        
        overall_score = sum(scores[category] * weight for category, weight in weights.items())
        return round(overall_score, 1)
    
    # Helper methods for detailed analysis
    def _extract_meaningful_fgdc_data(self, fgdc_content: str) -> Dict[str, Any]:
        """Extract meaningful data from FGDC content."""
        try:
            root = ET.fromstring(fgdc_content)
            
            # Count meaningful text content
            meaningful_elements = [
                './/title', './/origin', './/pubdate', './/abstract', './/purpose',
                './/supplinf', './/themekey', './/placekey', './/accconst', './/useconst'
            ]
            
            total_chars = 0
            field_count = 0
            
            for xpath in meaningful_elements:
                elements = root.findall(xpath)
                for elem in elements:
                    if elem.text and elem.text.strip():
                        total_chars += len(elem.text.strip())
                        field_count += 1
            
            return {
                'total_meaningful_chars': total_chars,
                'total_fields': field_count,
                'xml_elements': len(list(root.iter()))
            }
        except Exception:
            return {'total_meaningful_chars': 0, 'total_fields': 0, 'xml_elements': 0}
    
    def _extract_meaningful_zenodo_data(self, zenodo_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract meaningful data from Zenodo metadata."""
        total_chars = 0
        mapped_fields = 0
        
        for field, value in zenodo_metadata.items():
            if value is not None:
                mapped_fields += 1
                if isinstance(value, str):
                    total_chars += len(value)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            total_chars += len(item)
                        elif isinstance(item, dict):
                            for v in item.values():
                                if isinstance(v, str):
                                    total_chars += len(v)
        
        return {
            'total_meaningful_chars': total_chars,
            'mapped_fields': mapped_fields
        }
    
    def _calculate_semantic_preservation(self, fgdc_data: Dict[str, Any], 
                                       zenodo_data: Dict[str, Any]) -> float:
        """Calculate semantic preservation score."""
        # This is a simplified version - could be enhanced with more sophisticated analysis
        if fgdc_data['total_meaningful_chars'] == 0:
            return 0.0
        
        preservation_ratio = zenodo_data['total_meaningful_chars'] / fgdc_data['total_meaningful_chars']
        
        # Penalize if too much data was lost or gained (indicates poor mapping)
        if preservation_ratio < 0.5 or preservation_ratio > 2.0:
            return 0.5
        
        return min(preservation_ratio, 1.0)
    
    def _identify_data_loss(self, fgdc_data: Dict[str, Any], zenodo_data: Dict[str, Any]) -> List[str]:
        """Identify potential data loss indicators."""
        indicators = []
        
        if fgdc_data['total_meaningful_chars'] > 0:
            loss_ratio = 1 - (zenodo_data['total_meaningful_chars'] / fgdc_data['total_meaningful_chars'])
            if loss_ratio > 0.3:
                indicators.append(f"Significant data loss: {loss_ratio:.1%} of content not preserved")
        
        return indicators
    
    def _identify_data_gain(self, fgdc_data: Dict[str, Any], zenodo_data: Dict[str, Any]) -> List[str]:
        """Identify potential data gain indicators."""
        indicators = []
        
        if fgdc_data['total_meaningful_chars'] > 0:
            gain_ratio = (zenodo_data['total_meaningful_chars'] / fgdc_data['total_meaningful_chars']) - 1
            if gain_ratio > 0.5:
                indicators.append(f"Significant data expansion: {gain_ratio:.1%} more content than original")
        
        return indicators
    
    # Quality assessment methods
    def _assess_title_quality(self, title: str) -> Dict[str, Any]:
        """Assess title quality."""
        if not title:
            return {'score': 0, 'issues': ['Missing title'], 'grade': 'F'}
        
        issues = []
        score = 100
        
        if len(title) < 10:
            issues.append('Title too short')
            score -= 30
        elif len(title) > 250:
            issues.append('Title too long')
            score -= 20
        
        if not title[0].isupper():
            issues.append('Title should start with capital letter')
            score -= 10
        
        if title.endswith('.'):
            issues.append('Title should not end with period')
            score -= 5
        
        grade = 'A' if score >= 90 else 'B' if score >= 80 else 'C' if score >= 70 else 'D' if score >= 60 else 'F'
        
        return {'score': max(0, score), 'issues': issues, 'grade': grade}
    
    def _assess_creator_quality(self, creators: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess creator quality."""
        if not creators:
            return {'score': 0, 'issues': ['No creators specified'], 'grade': 'F'}
        
        issues = []
        score = 100
        
        if len(creators) == 0:
            issues.append('No creators')
            score = 0
        elif len(creators) > 10:
            issues.append('Too many creators')
            score -= 20
        
        for i, creator in enumerate(creators):
            name = creator.get('name', '')
            if not name:
                issues.append(f'Creator {i+1} missing name')
                score -= 20
            elif len(name) < 3:
                issues.append(f'Creator {i+1} name too short')
                score -= 10
            elif ',' not in name and ' ' not in name:
                issues.append(f'Creator {i+1} name format unclear')
                score -= 5
        
        grade = 'A' if score >= 90 else 'B' if score >= 80 else 'C' if score >= 70 else 'D' if score >= 60 else 'F'
        
        return {'score': max(0, score), 'issues': issues, 'grade': grade}
    
    def _assess_description_quality(self, description: str) -> Dict[str, Any]:
        """Assess description quality."""
        if not description:
            return {'score': 0, 'issues': ['Missing description'], 'grade': 'F'}
        
        issues = []
        score = 100
        
        if len(description) < 20:
            issues.append('Description too short')
            score -= 40
        elif len(description) > 5000:
            issues.append('Description too long')
            score -= 20
        
        if description.count('.') < 2:
            issues.append('Description should have multiple sentences')
            score -= 15
        
        grade = 'A' if score >= 90 else 'B' if score >= 80 else 'C' if score >= 70 else 'D' if score >= 60 else 'F'
        
        return {'score': max(0, score), 'issues': issues, 'grade': grade}
    
    def _assess_keyword_quality(self, keywords: List[str]) -> Dict[str, Any]:
        """Assess keyword quality."""
        if not keywords:
            return {'score': 50, 'issues': ['No keywords provided'], 'grade': 'C'}
        
        issues = []
        score = 100
        
        if len(keywords) < 3:
            issues.append('Too few keywords')
            score -= 30
        elif len(keywords) > 20:
            issues.append('Too many keywords')
            score -= 20
        
        for keyword in keywords:
            if len(keyword) < 2:
                issues.append(f'Keyword too short: "{keyword}"')
                score -= 10
            elif len(keyword) > 50:
                issues.append(f'Keyword too long: "{keyword}"')
                score -= 5
        
        grade = 'A' if score >= 90 else 'B' if score >= 80 else 'C' if score >= 70 else 'D' if score >= 60 else 'F'
        
        return {'score': max(0, score), 'issues': issues, 'grade': grade}
    
    def _assess_date_quality(self, date: str) -> Dict[str, Any]:
        """Assess date quality."""
        if not date:
            return {'score': 0, 'issues': ['Missing publication date'], 'grade': 'F'}
        
        issues = []
        score = 100
        
        try:
            from datetime import datetime
            parsed_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
            
            # Check if date is reasonable
            if parsed_date.year < 1900:
                issues.append('Date too early')
                score -= 30
            elif parsed_date.year > datetime.now().year + 1:
                issues.append('Date in future')
                score -= 30
                
        except ValueError:
            issues.append('Invalid date format')
            score = 0
        
        grade = 'A' if score >= 90 else 'B' if score >= 80 else 'C' if score >= 70 else 'D' if score >= 60 else 'F'
        
        return {'score': max(0, score), 'issues': issues, 'grade': grade}
    
    def _assess_license_quality(self, license: str) -> Dict[str, Any]:
        """Assess license quality."""
        if not license:
            return {'score': 0, 'issues': ['Missing license'], 'grade': 'F'}
        
        valid_licenses = ['cc-zero', 'cc-by-4.0', 'cc-by-sa-4.0', 'mit', 'apache-2.0', 'gpl-3.0']
        
        if license in valid_licenses:
            return {'score': 100, 'issues': [], 'grade': 'A'}
        else:
            return {'score': 50, 'issues': [f'Unrecognized license: {license}'], 'grade': 'C'}
    
    # Additional helper methods
    def _extract_fgdc_field_names(self, fgdc_content: str) -> List[str]:
        """Extract field names from FGDC content."""
        try:
            root = ET.fromstring(fgdc_content)
            return [elem.tag for elem in root.iter() if elem.text and elem.text.strip()]
        except Exception:
            return []
    
    def _count_mapped_fields(self, zenodo_metadata: Dict[str, Any]) -> int:
        """Count how many fields have been mapped."""
        return len([v for v in zenodo_metadata.values() if v is not None])
    
    def _calculate_data_enrichment(self, fgdc_content: str, zenodo_metadata: Dict[str, Any]) -> float:
        """Calculate data enrichment score."""
        # Simplified version - could be enhanced
        enrichment_fields = ['notes', 'related_identifiers', 'contributors', 'references']
        enriched_count = sum(1 for field in enrichment_fields if zenodo_metadata.get(field))
        return round((enriched_count / len(enrichment_fields)) * 100, 1)
    
    def _calculate_format_compliance(self, zenodo_metadata: Dict[str, Any]) -> float:
        """Calculate format compliance score."""
        # Check Zenodo schema compliance
        required_fields = ['title', 'creators', 'publication_date', 'description']
        present_required = sum(1 for field in required_fields if zenodo_metadata.get(field))
        return round((present_required / len(required_fields)) * 100, 1)
    
    def _calculate_semantic_accuracy(self, fgdc_content: str, zenodo_metadata: Dict[str, Any]) -> float:
        """Calculate semantic accuracy score."""
        # Simplified version - could be enhanced with more sophisticated analysis
        return 85.0  # Placeholder - would need more sophisticated analysis


def generate_metrics_summary(metrics_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate summary statistics from a list of metrics."""
    
    if not metrics_list:
        return {}
    
    summary = {
        'total_records': len(metrics_list),
        'overall_scores': {
            'average': 0.0,
            'median': 0.0,
            'min': 0.0,
            'max': 0.0,
            'std_dev': 0.0
        },
        'quality_distribution': {
            'excellent': 0,
            'good': 0,
            'fair': 0,
            'poor': 0
        },
        'field_coverage_stats': {
            'avg_critical_fields': 0.0,
            'avg_important_fields': 0.0,
            'avg_optional_fields': 0.0,
            'avg_overall_coverage': 0.0
        },
        'compliance_stats': {
            'zenodo_required_avg': 0.0,
            'zenodo_recommended_avg': 0.0,
            'pices_community_present': 0,
            'open_access_compliant': 0,
            'license_compliant': 0
        }
    }
    
    # Calculate overall scores
    scores = [m['overall_score'] for m in metrics_list]
    summary['overall_scores'] = {
        'average': round(sum(scores) / len(scores), 1),
        'median': round(sorted(scores)[len(scores) // 2], 1),
        'min': min(scores),
        'max': max(scores),
        'std_dev': round((sum((s - summary['overall_scores']['average']) ** 2 for s in scores) / len(scores)) ** 0.5, 1)
    }
    
    # Quality distribution
    for metrics in metrics_list:
        grade = metrics['data_quality']['quality_grade']
        if grade == 'EXCELLENT':
            summary['quality_distribution']['excellent'] += 1
        elif grade == 'GOOD':
            summary['quality_distribution']['good'] += 1
        elif grade == 'FAIR':
            summary['quality_distribution']['fair'] += 1
        else:
            summary['quality_distribution']['poor'] += 1
    
    # Field coverage stats
    coverage_data = [m['field_coverage'] for m in metrics_list]
    summary['field_coverage_stats'] = {
        'avg_critical_fields': round(sum(c['critical_fields_percentage'] for c in coverage_data) / len(coverage_data), 1),
        'avg_important_fields': round(sum(c['important_fields_percentage'] for c in coverage_data) / len(coverage_data), 1),
        'avg_optional_fields': round(sum(c['optional_fields_percentage'] for c in coverage_data) / len(coverage_data), 1),
        'avg_overall_coverage': round(sum(c['overall_coverage_percentage'] for c in coverage_data) / len(coverage_data), 1)
    }
    
    # Compliance stats
    compliance_data = [m['compliance'] for m in metrics_list]
    summary['compliance_stats'] = {
        'zenodo_required_avg': round(sum(c['zenodo_required_percentage'] for c in compliance_data) / len(compliance_data), 1),
        'zenodo_recommended_avg': round(sum(c['zenodo_recommended_percentage'] for c in compliance_data) / len(compliance_data), 1),
        'pices_community_present': sum(1 for c in compliance_data if c['pices_community_present']),
        'open_access_compliant': sum(1 for c in compliance_data if c['open_access_compliant']),
        'license_compliant': sum(1 for c in compliance_data if c['license_compliant'])
    }
    
    return summary
