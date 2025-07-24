#!/usr/bin/env python3
"""
MLB Optimizer Update Checker
Automated tool to monitor and update the MLB optimizer for latest library documentation.
"""

import subprocess
import sys
import json
import requests
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import importlib.util

class LibraryVersionChecker:
    """Check and monitor library versions for updates."""
    
    def __init__(self):
        self.libraries = {
            'numpy': {
                'current': None,
                'latest': None,
                'docs_url': 'https://numpy.org/doc/stable/',
                'changelog_url': 'https://numpy.org/doc/stable/release/',
                'critical_updates': ['random', 'Generator', 'default_rng']
            },
            'pandas': {
                'current': None,
                'latest': None,
                'docs_url': 'https://pandas.pydata.org/docs/',
                'changelog_url': 'https://pandas.pydata.org/docs/whatsnew/',
                'critical_updates': ['copy_on_write', 'to_numeric', 'read_csv']
            },
            'ortools': {
                'current': None,
                'latest': None,
                'docs_url': 'https://developers.google.com/optimization',
                'changelog_url': 'https://github.com/google/or-tools/releases',
                'critical_updates': ['CpSolver', 'CpModel', 'parameters']
            }
        }
    
    def get_current_versions(self) -> Dict[str, str]:
        """Get currently installed library versions."""
        versions = {}
        for lib in self.libraries.keys():
            try:
                result = subprocess.run([
                    sys.executable, '-c', f'import {lib}; print({lib}.__version__)'
                ], capture_output=True, text=True, check=True)
                versions[lib] = result.stdout.strip()
                self.libraries[lib]['current'] = versions[lib]
            except subprocess.CalledProcessError:
                print(f"Warning: Could not get version for {lib}")
                versions[lib] = "Unknown"
        return versions
    
    def check_for_updates(self) -> Dict[str, Dict]:
        """Check for available updates and documentation changes."""
        updates = {}
        
        for lib_name, lib_info in self.libraries.items():
            try:
                # Get latest version from PyPI
                response = requests.get(f"https://pypi.org/pypi/{lib_name}/json", timeout=10)
                if response.status_code == 200:
                    latest_version = response.json()['info']['version']
                    lib_info['latest'] = latest_version
                    
                    if lib_info['current'] and lib_info['current'] != latest_version:
                        updates[lib_name] = {
                            'current': lib_info['current'],
                            'latest': latest_version,
                            'docs_url': lib_info['docs_url'],
                            'changelog_url': lib_info['changelog_url'],
                            'critical_updates': lib_info['critical_updates']
                        }
            except Exception as e:
                print(f"Warning: Could not check updates for {lib_name}: {e}")
        
        return updates

class CodeAnalyzer:
    """Analyze code for potential compatibility issues."""
    
    def __init__(self, optimizer_path: str):
        self.optimizer_path = Path(optimizer_path)
        self.imports = {}
        self.function_calls = {}
        self.deprecated_patterns = {
            'numpy': {
                'np.random.RandomState': 'np.random.default_rng',
                'np.random.normal': 'np.random.standard_normal',
                'np.random.rand': 'np.random.random'
            },
            'pandas': {
                'pd.read_csv.*encoding=None': 'pd.read_csv with explicit encoding',
                'df.mean\\(axis=0\\)': 'df.mean() (default behavior)',
                'df.std\\(ddof=1\\)': 'df.std() (default behavior)'
            },
            'ortools': {
                'solver.parameters.log_search_progress = True': 'solver.parameters.log_search_progress = False',
                'model.Add\\(.*\\)': 'model.Add() with enhanced validation'
            }
        }
    
    def analyze_imports(self) -> Dict[str, List[str]]:
        """Analyze imports and their usage patterns."""
        imports = {}
        
        with open(self.optimizer_path, 'r') as f:
            content = f.read()
        
        # Find import statements
        import_pattern = r'^(?:from\s+(\w+)\s+import\s+(.+)|import\s+(\w+))'
        for line in content.split('\n'):
            match = re.match(import_pattern, line.strip())
            if match:
                if match.group(1):  # from ... import ...
                    lib = match.group(1)
                    modules = [m.strip() for m in match.group(2).split(',')]
                    imports[lib] = modules
                else:  # import ...
                    lib = match.group(3)
                    imports[lib] = ['*']
        
        return imports
    
    def check_deprecated_patterns(self) -> List[Dict]:
        """Check for deprecated or outdated code patterns."""
        issues = []
        
        with open(self.optimizer_path, 'r') as f:
            content = f.read()
        
        for library, patterns in self.deprecated_patterns.items():
            for old_pattern, suggestion in patterns.items():
                matches = re.finditer(old_pattern, content, re.MULTILINE)
                for match in matches:
                    issues.append({
                        'library': library,
                        'pattern': old_pattern,
                        'suggestion': suggestion,
                        'line': content[:match.start()].count('\n') + 1,
                        'context': match.group(0)
                    })
        
        return issues

class DocumentationMonitor:
    """Monitor documentation changes and API updates."""
    
    def __init__(self):
        self.docs_endpoints = {
            'numpy': 'https://numpy.org/doc/stable/reference/',
            'pandas': 'https://pandas.pydata.org/docs/reference/',
            'ortools': 'https://developers.google.com/optimization/reference/python/sat/python'
        }
    
    def check_documentation_changes(self, library: str) -> List[Dict]:
        """Check for recent documentation changes."""
        changes = []
        
        try:
            if library == 'numpy':
                changes = self._check_numpy_docs()
            elif library == 'pandas':
                changes = self._check_pandas_docs()
            elif library == 'ortools':
                changes = self._check_ortools_docs()
        except Exception as e:
            print(f"Warning: Could not check docs for {library}: {e}")
        
        return changes
    
    def _check_numpy_docs(self) -> List[Dict]:
        """Check NumPy documentation for recent changes."""
        changes = []
        
        # Check for random module updates
        try:
            response = requests.get('https://numpy.org/doc/stable/reference/random/index.html', timeout=10)
            if response.status_code == 200:
                if 'Generator' in response.text and 'default_rng' in response.text:
                    changes.append({
                        'type': 'feature',
                        'description': 'NumPy Generator and default_rng available',
                        'url': 'https://numpy.org/doc/stable/reference/random/index.html'
                    })
        except Exception:
            pass
        
        return changes
    
    def _check_pandas_docs(self) -> List[Dict]:
        """Check Pandas documentation for recent changes."""
        changes = []
        
        # Check for copy-on-write updates
        try:
            response = requests.get('https://pandas.pydata.org/docs/user_guide/indexing.html', timeout=10)
            if response.status_code == 200:
                if 'copy_on_write' in response.text:
                    changes.append({
                        'type': 'feature',
                        'description': 'Pandas copy-on-write mode available',
                        'url': 'https://pandas.pydata.org/docs/user_guide/indexing.html'
                    })
        except Exception:
            pass
        
        return changes
    
    def _check_ortools_docs(self) -> List[Dict]:
        """Check OR-Tools documentation for recent changes."""
        changes = []
        
        # Check for solver parameter updates
        try:
            response = requests.get('https://developers.google.com/optimization/reference/python/sat/python/cp_model', timeout=10)
            if response.status_code == 200:
                if 'num_search_workers' in response.text:
                    changes.append({
                        'type': 'feature',
                        'description': 'OR-Tools multi-worker support available',
                        'url': 'https://developers.google.com/optimization/reference/python/sat/python/cp_model'
                    })
        except Exception:
            pass
        
        return changes

class UpdateManager:
    """Manage the update process for the optimizer."""
    
    def __init__(self, optimizer_path: str):
        self.optimizer_path = Path(optimizer_path)
        self.backup_path = self.optimizer_path.with_suffix('.backup')
        self.version_checker = LibraryVersionChecker()
        self.code_analyzer = CodeAnalyzer(optimizer_path)
        self.doc_monitor = DocumentationMonitor()
    
    def create_backup(self) -> bool:
        """Create a backup of the current optimizer."""
        try:
            import shutil
            shutil.copy2(self.optimizer_path, self.backup_path)
            print(f"✅ Backup created: {self.backup_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to create backup: {e}")
            return False
    
    def restore_backup(self) -> bool:
        """Restore from backup if needed."""
        try:
            import shutil
            if self.backup_path.exists():
                shutil.copy2(self.backup_path, self.optimizer_path)
                print(f"✅ Restored from backup: {self.backup_path}")
                return True
        except Exception as e:
            print(f"❌ Failed to restore backup: {e}")
        return False
    
    def generate_update_report(self) -> Dict:
        """Generate a comprehensive update report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'current_versions': self.version_checker.get_current_versions(),
            'available_updates': self.version_checker.check_for_updates(),
            'code_analysis': {
                'imports': self.code_analyzer.analyze_imports(),
                'deprecated_patterns': self.code_analyzer.check_deprecated_patterns()
            },
            'documentation_changes': {},
            'recommendations': []
        }
        
        # Check documentation changes for each library
        for library in ['numpy', 'pandas', 'ortools']:
            report['documentation_changes'][library] = self.doc_monitor.check_documentation_changes(library)
        
        # Generate recommendations
        report['recommendations'] = self._generate_recommendations(report)
        
        return report
    
    def _generate_recommendations(self, report: Dict) -> List[str]:
        """Generate specific recommendations based on the analysis."""
        recommendations = []
        
        # Check for version updates
        for lib, update_info in report['available_updates'].items():
            recommendations.append(f"Update {lib} from {update_info['current']} to {update_info['latest']}")
        
        # Check for deprecated patterns
        for issue in report['code_analysis']['deprecated_patterns']:
            recommendations.append(f"Line {issue['line']}: Replace '{issue['pattern']}' with '{issue['suggestion']}'")
        
        # Check for documentation changes
        for lib, changes in report['documentation_changes'].items():
            for change in changes:
                recommendations.append(f"Review {lib} documentation: {change['description']}")
        
        return recommendations
    
    def apply_automatic_updates(self) -> bool:
        """Apply automatic updates that are safe to apply."""
        try:
            # Create backup first
            if not self.create_backup():
                return False
            
            # Read current file
            with open(self.optimizer_path, 'r') as f:
                content = f.read()
            
            # Apply safe updates
            updated_content = content
            
            # Update NumPy random usage if needed
            if 'np.random.RandomState' in content:
                updated_content = updated_content.replace(
                    'np.random.RandomState',
                    'np.random.default_rng'
                )
                print("✅ Updated NumPy random generator usage")
            
            # Update Pandas copy-on-write if needed
            if 'pd.options.mode.copy_on_write' not in content:
                # Add copy-on-write optimization
                copy_on_write_code = '''
# Enable copy-on-write for better memory efficiency
try:
    pd.options.mode.copy_on_write = True
except AttributeError:
    # Fallback for older Pandas versions
    pass
'''
                # Find the right place to insert this code
                if 'import pandas as pd' in updated_content:
                    updated_content = updated_content.replace(
                        'import pandas as pd',
                        'import pandas as pd' + copy_on_write_code
                    )
                    print("✅ Added Pandas copy-on-write optimization")
            
            # Write updated content
            with open(self.optimizer_path, 'w') as f:
                f.write(updated_content)
            
            print("✅ Automatic updates applied successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to apply automatic updates: {e}")
            self.restore_backup()
            return False

def main():
    """Main function to run the update checker."""
    optimizer_path = "MLB_Optimizer/MLB_Testing_Sandbox.py"
    
    if not Path(optimizer_path).exists():
        print(f"❌ Optimizer file not found: {optimizer_path}")
        return
    
    print("🔍 MLB_Optimizer Update Checker")
    print("=" * 50)
    
    # Initialize update manager
    manager = UpdateManager(optimizer_path)
    
    # Generate comprehensive report
    print("\n📊 Generating update report...")
    report = manager.generate_update_report()
    
    # Display current versions
    print("\n📦 Current Library Versions:")
    for lib, version in report['current_versions'].items():
        print(f"  {lib}: {version}")
    
    # Display available updates
    if report['available_updates']:
        print("\n🔄 Available Updates:")
        for lib, update_info in report['available_updates'].items():
            print(f"  {lib}: {update_info['current']} → {update_info['latest']}")
    else:
        print("\n✅ All libraries are up to date!")
    
    # Display code analysis
    if report['code_analysis']['deprecated_patterns']:
        print("\n⚠️  Code Issues Found:")
        for issue in report['code_analysis']['deprecated_patterns']:
            print(f"  Line {issue['line']}: {issue['suggestion']}")
    else:
        print("\n✅ No deprecated code patterns found!")
    
    # Display recommendations
    if report['recommendations']:
        print("\n💡 Recommendations:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"  {i}. {rec}")
    
    # Save report
    report_path = Path("update_report.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\n📄 Detailed report saved to: {report_path}")
    
    # Ask user if they want to apply automatic updates
    if report['available_updates'] or report['code_analysis']['deprecated_patterns']:
        print("\n🤖 Would you like to apply automatic updates? (y/n): ", end="")
        try:
            response = input().lower().strip()
            if response in ['y', 'yes']:
                if manager.apply_automatic_updates():
                    print("✅ Automatic updates applied successfully!")
                else:
                    print("❌ Automatic updates failed!")
        except KeyboardInterrupt:
            print("\n⏹️  Update cancelled by user")
    
    print("\n✨ Update check completed!")

if __name__ == "__main__":
    main() 