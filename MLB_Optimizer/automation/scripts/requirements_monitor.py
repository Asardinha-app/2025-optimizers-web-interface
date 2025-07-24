#!/usr/bin/env python3
"""
Requirements Monitor for MLB Optimizer
Tracks dependencies and their documentation changes.
"""

import subprocess
import sys
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

class RequirementsMonitor:
    """Monitor requirements and documentation changes."""
    
    def __init__(self):
        self.requirements_file = Path("requirements.txt")
        self.dependencies = {
            'numpy': {
                'min_version': '1.20.0',
                'recommended_version': '1.26.0',
                'docs_url': 'https://numpy.org/doc/stable/',
                'critical_features': ['Generator', 'default_rng', 'standard_normal']
            },
            'pandas': {
                'min_version': '1.3.0',
                'recommended_version': '2.1.0',
                'docs_url': 'https://pandas.pydata.org/docs/',
                'critical_features': ['copy_on_write', 'to_numeric', 'read_csv']
            },
            'ortools': {
                'min_version': '9.0.0',
                'recommended_version': '9.8.0',
                'docs_url': 'https://developers.google.com/optimization',
                'critical_features': ['CpSolver', 'CpModel', 'num_search_workers']
            }
        }
    
    def check_installed_versions(self) -> Dict[str, str]:
        """Check currently installed package versions."""
        versions = {}
        for package in self.dependencies.keys():
            try:
                result = subprocess.run([
                    sys.executable, '-c', f'import {package}; print({package}.__version__)'
                ], capture_output=True, text=True, check=True)
                versions[package] = result.stdout.strip()
            except subprocess.CalledProcessError:
                versions[package] = "Not installed"
        return versions
    
    def check_latest_versions(self) -> Dict[str, str]:
        """Check latest available versions from PyPI."""
        latest_versions = {}
        for package in self.dependencies.keys():
            try:
                response = requests.get(f"https://pypi.org/pypi/{package}/json", timeout=10)
                if response.status_code == 200:
                    latest_versions[package] = response.json()['info']['version']
            except Exception as e:
                print(f"Warning: Could not check latest version for {package}: {e}")
        return latest_versions
    
    def generate_requirements_report(self) -> Dict:
        """Generate a comprehensive requirements report."""
        installed = self.check_installed_versions()
        latest = self.check_latest_versions()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'installed_versions': installed,
            'latest_versions': latest,
            'recommendations': [],
            'warnings': [],
            'critical_updates': []
        }
        
        for package, info in self.dependencies.items():
            current = installed.get(package, "Not installed")
            latest_version = latest.get(package, "Unknown")
            
            if current == "Not installed":
                report['warnings'].append(f"{package} is not installed")
                report['recommendations'].append(f"Install {package} >= {info['min_version']}")
            else:
                # Check if version meets minimum requirements
                if self._version_compare(current, info['min_version']) < 0:
                    report['critical_updates'].append(f"{package} {current} < {info['min_version']}")
                    report['recommendations'].append(f"Update {package} to >= {info['min_version']}")
                
                # Check if version is outdated
                if latest_version != "Unknown" and self._version_compare(current, latest_version) < 0:
                    report['recommendations'].append(f"Update {package} from {current} to {latest_version}")
        
        return report
    
    def _version_compare(self, version1: str, version2: str) -> int:
        """Compare version strings."""
        try:
            from packaging import version
            return version.parse(version1).__cmp__(version.parse(version2))
        except ImportError:
            # Fallback version comparison
            v1_parts = [int(x) for x in version1.split('.')]
            v2_parts = [int(x) for x in version2.split('.')]
            
            for i in range(max(len(v1_parts), len(v2_parts))):
                v1_part = v1_parts[i] if i < len(v1_parts) else 0
                v2_part = v2_parts[i] if i < len(v2_parts) else 0
                
                if v1_part < v2_part:
                    return -1
                elif v1_part > v2_part:
                    return 1
            
            return 0
    
    def create_requirements_file(self) -> bool:
        """Create or update requirements.txt file."""
        try:
            installed = self.check_installed_versions()
            latest = self.check_latest_versions()
            
            requirements = []
            for package, info in self.dependencies.items():
                current = installed.get(package, "Not installed")
                latest_version = latest.get(package, "Unknown")
                
                if current != "Not installed":
                    # Use current version if it meets minimum, otherwise use recommended
                    if self._version_compare(current, info['min_version']) >= 0:
                        requirements.append(f"{package}=={current}")
                    else:
                        requirements.append(f"{package}>={info['recommended_version']}")
                else:
                    requirements.append(f"{package}>={info['min_version']}")
            
            with open(self.requirements_file, 'w') as f:
                f.write("# MLB_Optimizer Requirements\n")
                f.write(f"# Generated on {datetime.now().isoformat()}\n\n")
                for req in requirements:
                    f.write(f"{req}\n")
            
            print(f"✅ Requirements file created: {self.requirements_file}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create requirements file: {e}")
            return False

def main():
    """Main function to run the requirements monitor."""
    print("📦 MLB_Optimizer Requirements Monitor")
    print("=" * 50)
    
    monitor = RequirementsMonitor()
    
    # Generate report
    print("\n📊 Checking requirements...")
    report = monitor.generate_requirements_report()
    
    # Display current status
    print("\n📦 Current Package Versions:")
    for package, version in report['installed_versions'].items():
        print(f"  {package}: {version}")
    
    # Display warnings
    if report['warnings']:
        print("\n⚠️  Warnings:")
        for warning in report['warnings']:
            print(f"  - {warning}")
    
    # Display critical updates
    if report['critical_updates']:
        print("\n🚨 Critical Updates Required:")
        for update in report['critical_updates']:
            print(f"  - {update}")
    
    # Display recommendations
    if report['recommendations']:
        print("\n💡 Recommendations:")
        for rec in report['recommendations']:
            print(f"  - {rec}")
    
    # Create requirements file
    print("\n📄 Creating requirements.txt...")
    if monitor.create_requirements_file():
        print("✅ Requirements file created successfully!")
    else:
        print("❌ Failed to create requirements file!")
    
    print("\n✨ Requirements check completed!")

if __name__ == "__main__":
    main() 