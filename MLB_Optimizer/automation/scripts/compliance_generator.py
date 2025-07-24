#!/usr/bin/env python3
"""
MLB Optimizer Compliance Generator
Automatically analyzes the optimizer code and generates compliance audit reports.
"""

import ast
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import subprocess
import sys

class ComplianceAnalyzer:
    """Analyze code for compliance with OR-Tools, NumPy, and Pandas best practices."""
    
    def __init__(self, optimizer_path: str):
        self.optimizer_path = Path(optimizer_path)
        self.compliance_scores = {}
        self.issues_found = []
        self.recommendations = []
        
    def analyze_ortools_compliance(self) -> Dict:
        """Analyze OR-Tools compliance."""
        score = 100
        issues = []
        recommendations = []
        
        try:
            with open(self.optimizer_path, 'r') as f:
                content = f.read()
            
            # Check for correct imports
            if 'from ortools.sat.python import cp_model' in content:
                score += 5  # Bonus for correct import
            else:
                score -= 10
                issues.append("Missing correct OR-Tools import")
            
            # Check for modern model creation
            if 'cp_model.CpModel()' in content:
                score += 5
            else:
                score -= 10
                issues.append("Not using modern CpModel()")
            
            # Check for modern variable creation
            if 'model.NewBoolVar(' in content and 'model.NewIntVar(' in content:
                score += 10
            else:
                score -= 5
                issues.append("Not using modern variable creation methods")
            
            # Check for advanced solver parameters
            advanced_params = [
                'num_search_workers',
                'cp_model_presolve',
                'linearization_level',
                'interleave_search'
            ]
            
            param_count = sum(1 for param in advanced_params if param in content)
            if param_count >= 3:
                score += 15
                recommendations.append("Excellent use of advanced solver parameters")
            elif param_count >= 1:
                score += 5
                recommendations.append("Good use of some advanced parameters")
            else:
                score -= 10
                issues.append("Missing advanced solver parameters")
            
            # Check for comprehensive status handling
            status_checks = [
                'cp_model.OPTIMAL',
                'cp_model.FEASIBLE',
                'cp_model.INFEASIBLE',
                'cp_model.MODEL_INVALID'
            ]
            
            status_count = sum(1 for status in status_checks if status in content)
            if status_count >= 3:
                score += 10
                recommendations.append("Excellent status handling")
            elif status_count >= 1:
                score += 5
                recommendations.append("Good status handling")
            else:
                score -= 5
                issues.append("Missing comprehensive status handling")
            
            # Check for performance metrics
            if 'solver.NumBranches()' in content or 'solver.NumConflicts()' in content:
                score += 5
                recommendations.append("Good performance monitoring")
            else:
                score -= 5
                issues.append("Missing performance metrics")
            
            # Check for model validation
            if 'test_solver' in content and 'test_status' in content:
                score += 5
                recommendations.append("Good model validation")
            else:
                score -= 5
                issues.append("Missing model validation")
            
        except Exception as e:
            score -= 20
            issues.append(f"Error analyzing OR-Tools compliance: {e}")
        
        return {
            'score': max(0, min(100, score)),
            'issues': issues,
            'recommendations': recommendations
        }
    
    def analyze_numpy_compliance(self) -> Dict:
        """Analyze NumPy compliance."""
        score = 100
        issues = []
        recommendations = []
        
        try:
            with open(self.optimizer_path, 'r') as f:
                content = f.read()
            
            # Check for modern random generator
            if 'np.random.default_rng(' in content:
                score += 15
                recommendations.append("Excellent: Using modern NumPy Generator")
            elif 'np.random.RandomState(' in content:
                score -= 20
                issues.append("Using deprecated RandomState instead of default_rng")
                recommendations.append("Replace np.random.RandomState with np.random.default_rng")
            else:
                score -= 10
                issues.append("Not using modern NumPy random generator")
            
            # Check for performance optimized methods
            if 'standard_normal()' in content:
                score += 10
                recommendations.append("Good: Using standard_normal() for performance")
            elif 'normal(' in content:
                score -= 5
                issues.append("Using normal() instead of standard_normal()")
                recommendations.append("Consider using standard_normal() for better performance")
            
            # Check for vectorized operations
            if 'np.clip(' in content:
                score += 5
                recommendations.append("Good: Using vectorized operations")
            
            # Check for safe numerical operations
            if 'max(' in content and '0.1' in content:
                score += 5
                recommendations.append("Good: Safe numerical operations with bounds")
            
        except Exception as e:
            score -= 20
            issues.append(f"Error analyzing NumPy compliance: {e}")
        
        return {
            'score': max(0, min(100, score)),
            'issues': issues,
            'recommendations': recommendations
        }
    
    def analyze_pandas_compliance(self) -> Dict:
        """Analyze Pandas compliance."""
        score = 100
        issues = []
        recommendations = []
        
        try:
            with open(self.optimizer_path, 'r') as f:
                content = f.read()
            
            # Check for copy-on-write optimization
            if 'pd.options.mode.copy_on_write' in content:
                score += 15
                recommendations.append("Excellent: Using copy-on-write optimization")
            else:
                score -= 10
                issues.append("Missing copy-on-write optimization")
                recommendations.append("Add copy-on-write optimization for memory efficiency")
            
            # Check for safe data loading
            if 'pd.read_csv(' in content and 'encoding=' in content:
                score += 10
                recommendations.append("Good: Safe CSV loading with encoding")
            elif 'pd.read_csv(' in content:
                score += 5
                recommendations.append("Good: Using pandas for data loading")
            else:
                score -= 5
                issues.append("Not using pandas for data loading")
            
            # Check for safe data type conversion
            if 'pd.to_numeric(' in content and 'errors=' in content:
                score += 10
                recommendations.append("Excellent: Safe data type conversion")
            elif 'pd.to_numeric(' in content:
                score += 5
                recommendations.append("Good: Using to_numeric for conversion")
            else:
                score -= 5
                issues.append("Not using safe data type conversion")
            
            # Check for vectorized operations
            if '.isin(' in content or '.unique(' in content:
                score += 5
                recommendations.append("Good: Using vectorized operations")
            
        except Exception as e:
            score -= 20
            issues.append(f"Error analyzing Pandas compliance: {e}")
        
        return {
            'score': max(0, min(100, score)),
            'issues': issues,
            'recommendations': recommendations
        }
    
    def analyze_python_best_practices(self) -> Dict:
        """Analyze Python best practices compliance."""
        score = 100
        issues = []
        recommendations = []
        
        try:
            with open(self.optimizer_path, 'r') as f:
                content = f.read()
            
            # Check for type hints
            type_hint_patterns = [
                r': List\[',
                r': Dict\[',
                r': Optional\[',
                r': Tuple\[',
                r'-> '
            ]
            
            type_hint_count = sum(1 for pattern in type_hint_patterns if re.search(pattern, content))
            if type_hint_count >= 5:
                score += 15
                recommendations.append("Excellent: Comprehensive type hints")
            elif type_hint_count >= 2:
                score += 10
                recommendations.append("Good: Using type hints")
            else:
                score -= 10
                issues.append("Missing type hints")
                recommendations.append("Add type hints for better code clarity")
            
            # Check for dataclasses
            if '@dataclass' in content:
                score += 10
                recommendations.append("Good: Using dataclasses")
            else:
                score -= 5
                issues.append("Not using dataclasses")
                recommendations.append("Consider using dataclasses for data structures")
            
            # Check for comprehensive docstrings
            docstring_pattern = r'"""[^"]*"""'
            docstring_count = len(re.findall(docstring_pattern, content))
            if docstring_count >= 5:
                score += 10
                recommendations.append("Excellent: Comprehensive documentation")
            elif docstring_count >= 2:
                score += 5
                recommendations.append("Good: Using docstrings")
            else:
                score -= 5
                issues.append("Missing comprehensive docstrings")
                recommendations.append("Add docstrings for better documentation")
            
            # Check for error handling
            if 'try:' in content and 'except:' in content:
                score += 10
                recommendations.append("Good: Error handling implemented")
            else:
                score -= 5
                issues.append("Missing error handling")
                recommendations.append("Add error handling for robustness")
            
            # Check for validation
            if 'raise ValueError(' in content or 'assert ' in content:
                score += 5
                recommendations.append("Good: Input validation")
            else:
                score -= 5
                issues.append("Missing input validation")
                recommendations.append("Add input validation for safety")
            
        except Exception as e:
            score -= 20
            issues.append(f"Error analyzing Python best practices: {e}")
        
        return {
            'score': max(0, min(100, score)),
            'issues': issues,
            'recommendations': recommendations
        }
    
    def analyze_dfs_specific_logic(self) -> Dict:
        """Analyze DFS-specific logic compliance."""
        score = 100
        issues = []
        recommendations = []
        
        try:
            with open(self.optimizer_path, 'r') as f:
                content = f.read()
            
            # Check for proper constraint programming
            if 'CpModel()' in content and 'AddBoolOr(' in content:
                score += 15
                recommendations.append("Excellent: Proper constraint programming for DFS")
            elif 'CpModel()' in content:
                score += 10
                recommendations.append("Good: Using constraint programming")
            else:
                score -= 15
                issues.append("Not using constraint programming for DFS")
            
            # Check for complex stacking logic
            if 'OnlyEnforceIf(' in content and 'team_stack_vars' in content:
                score += 15
                recommendations.append("Excellent: Complex stacking logic implemented")
            elif 'OnlyEnforceIf(' in content:
                score += 10
                recommendations.append("Good: Using conditional constraints")
            else:
                score -= 10
                issues.append("Missing advanced stacking logic")
            
            # Check for exposure management
            if 'exposure' in content and 'primary_stack_counts' in content:
                score += 10
                recommendations.append("Good: Exposure management implemented")
            else:
                score -= 5
                issues.append("Missing exposure management")
                recommendations.append("Add exposure management for DFS")
            
            # Check for salary cap constraints
            if 'MAX_SALARY' in content and 'salary' in content:
                score += 10
                recommendations.append("Good: Salary cap constraints")
            else:
                score -= 10
                issues.append("Missing salary cap constraints")
            
        except Exception as e:
            score -= 20
            issues.append(f"Error analyzing DFS-specific logic: {e}")
        
        return {
            'score': max(0, min(100, score)),
            'issues': issues,
            'recommendations': recommendations
        }
    
    def analyze_performance_optimization(self) -> Dict:
        """Analyze performance optimization compliance."""
        score = 100
        issues = []
        recommendations = []
        
        try:
            with open(self.optimizer_path, 'r') as f:
                content = f.read()
            
            # Check for pre-computed lists
            if 'pitchers = [' in content and 'batters = [' in content:
                score += 10
                recommendations.append("Excellent: Pre-computed lists for performance")
            else:
                score -= 5
                issues.append("Missing pre-computed lists")
                recommendations.append("Add pre-computed lists for better performance")
            
            # Check for conditional constraint creation
            if 'if slot_players:' in content:
                score += 10
                recommendations.append("Good: Conditional constraint creation")
            else:
                score -= 5
                issues.append("Missing conditional constraint creation")
            
            # Check for batch processing
            if 'standard_normal(len(' in content:
                score += 10
                recommendations.append("Excellent: Batch processing for efficiency")
            else:
                score -= 5
                issues.append("Missing batch processing")
                recommendations.append("Add batch processing for better performance")
            
            # Check for vectorized operations
            if '.isin(' in content or '.unique(' in content:
                score += 5
                recommendations.append("Good: Vectorized operations")
            
        except Exception as e:
            score -= 20
            issues.append(f"Error analyzing performance optimization: {e}")
        
        return {
            'score': max(0, min(100, score)),
            'issues': issues,
            'recommendations': recommendations
        }
    
    def generate_compliance_report(self) -> Dict:
        """Generate a comprehensive compliance report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'optimizer_file': str(self.optimizer_path),
            'categories': {
                'OR-Tools Usage': self.analyze_ortools_compliance(),
                'NumPy Compliance': self.analyze_numpy_compliance(),
                'Pandas Compliance': self.analyze_pandas_compliance(),
                'Python Best Practices': self.analyze_python_best_practices(),
                'DFS-Specific Logic': self.analyze_dfs_specific_logic(),
                'Performance Optimization': self.analyze_performance_optimization()
            }
        }
        
        # Calculate overall score
        scores = [cat['score'] for cat in report['categories'].values()]
        report['overall_score'] = sum(scores) / len(scores)
        
        # Collect all issues and recommendations
        all_issues = []
        all_recommendations = []
        
        for category_name, category_data in report['categories'].items():
            all_issues.extend([f"{category_name}: {issue}" for issue in category_data['issues']])
            all_recommendations.extend([f"{category_name}: {rec}" for rec in category_data['recommendations']])
        
        report['all_issues'] = all_issues
        report['all_recommendations'] = all_recommendations
        
        return report

def generate_markdown_report(report: Dict) -> str:
    """Generate a markdown compliance report."""
    md_content = f"""# MLB_Optimizer Compliance Audit Report

## 📋 Executive Summary

**Overall Compliance Score: {report['overall_score']:.0f}/100** {'✅' if report['overall_score'] >= 90 else '⚠️' if report['overall_score'] >= 70 else '❌'}

The MLB_Testing_Sandbox.py file demonstrates {'excellent' if report['overall_score'] >= 90 else 'good' if report['overall_score'] >= 70 else 'needs improvement in'} compliance with the latest OR-Tools documentation and best practices.

**Generated on:** {datetime.fromisoformat(report['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}

## 🏆 Compliance Score Breakdown

| Category | Score | Status |
|----------|-------|--------|
"""
    
    for category_name, category_data in report['categories'].items():
        score = category_data['score']
        status = '✅ Excellent' if score >= 90 else '⚠️ Good' if score >= 70 else '❌ Needs Improvement'
        md_content += f"| **{category_name}** | {score:.0f}/100 | {status} |\n"
    
    md_content += f"""
| **Overall** | {report['overall_score']:.0f}/100 | {'✅ Excellent' if report['overall_score'] >= 90 else '⚠️ Good' if report['overall_score'] >= 70 else '❌ Needs Improvement'} |

## 📊 Detailed Analysis

"""
    
    for category_name, category_data in report['categories'].items():
        md_content += f"### {category_name}\n\n"
        md_content += f"**Score: {category_data['score']:.0f}/100**\n\n"
        
        if category_data['issues']:
            md_content += "**Issues Found:**\n"
            for issue in category_data['issues']:
                md_content += f"- ❌ {issue}\n"
            md_content += "\n"
        
        if category_data['recommendations']:
            md_content += "**Recommendations:**\n"
            for rec in category_data['recommendations']:
                md_content += f"- 💡 {rec}\n"
            md_content += "\n"
        
        md_content += "---\n\n"
    
    if report['all_issues']:
        md_content += "## ⚠️ Issues Summary\n\n"
        for issue in report['all_issues']:
            md_content += f"- {issue}\n"
        md_content += "\n"
    
    if report['all_recommendations']:
        md_content += "## 💡 Recommendations Summary\n\n"
        for rec in report['all_recommendations']:
            md_content += f"- {rec}\n"
        md_content += "\n"
    
    md_content += f"""## 🎉 Conclusion

The MLB_Testing_Sandbox.py file demonstrates {'excellent' if report['overall_score'] >= 90 else 'good' if report['overall_score'] >= 70 else 'needs improvement in'} compliance with the latest OR-Tools documentation and best practices.

**Overall Assessment:** {'Highly Compliant ✅' if report['overall_score'] >= 90 else 'Mostly Compliant ⚠️' if report['overall_score'] >= 70 else 'Needs Improvement ❌'}

*This report was automatically generated by the compliance analyzer.*
"""
    
    return md_content

def main():
    """Main function to generate compliance report."""
    optimizer_path = "MLB_Testing_Sandbox.py"
    
    if not Path(optimizer_path).exists():
        print(f"❌ Optimizer file not found: {optimizer_path}")
        return
    
    print("🔍 MLB_Optimizer Compliance Analyzer")
    print("=" * 50)
    
    # Initialize analyzer
    analyzer = ComplianceAnalyzer(optimizer_path)
    
    # Generate report
    print("\n📊 Generating compliance report...")
    report = analyzer.generate_compliance_report()
    
    # Display summary
    print(f"\n📋 Overall Compliance Score: {report['overall_score']:.0f}/100")
    print("\n📊 Category Scores:")
    for category_name, category_data in report['categories'].items():
        print(f"  {category_name}: {category_data['score']:.0f}/100")
    
    # Generate markdown report
    md_content = generate_markdown_report(report)
    
    # Save markdown report
    report_path = Path("compliance/COMPLIANCE_AUDIT_REPORT.md")
    with open(report_path, 'w') as f:
        f.write(md_content)
    
    print(f"\n📄 Compliance report saved to: {report_path}")
    
    # Save JSON report for automation
    json_path = Path("system_logs") / "compliance_report.json"
    json_path.parent.mkdir(exist_ok=True)
    with open(json_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📊 JSON report saved to: {json_path}")
    print("\n✨ Compliance analysis completed!")

if __name__ == "__main__":
    main() 