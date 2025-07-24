#!/usr/bin/env python3
"""
Automated updater for the MLB optimizer.
Handles library updates, code compliance, and performance optimizations.
"""

import os
import sys
import subprocess
import logging
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation/logs/auto_update.log'),
        logging.StreamHandler()
    ]
)

class AutoUpdater:
    """Automated updater for the MLB optimizer."""
    
    def __init__(self, optimizer_dir: str = None):
        if optimizer_dir is None:
            self.optimizer_dir = Path(__file__).parent.parent.parent
        else:
            self.optimizer_dir = Path(optimizer_dir)
        self.automation_dir = self.optimizer_dir / "automation"
        self.backup_dir = self.automation_dir / "backups"
        self.log_file = self.optimizer_dir / "system_logs" / "update_log.json"
        self.last_update_file = self.optimizer_dir / "system_logs" / "last_update.txt"
        
        # Create backup directory if it doesn't exist
        self.backup_dir.mkdir(exist_ok=True)
        (self.optimizer_dir / "system_logs").mkdir(exist_ok=True)
        
        # Libraries to monitor
        self.libraries = {
            'numpy': {
                'min_version': '1.20.0',
                'critical_features': ['Generator', 'default_rng', 'standard_normal']
            },
            'pandas': {
                'min_version': '1.3.0',
                'critical_features': ['copy_on_write', 'to_numeric', 'read_csv']
            },
            'ortools': {
                'min_version': '9.0.0',
                'critical_features': ['CpSolver', 'CpModel', 'num_search_workers']
            }
        }
    
    def create_backup(self) -> bool:
        """Create a timestamped backup of the optimizer."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"MLB_Testing_Sandbox_{timestamp}.py"
            backup_path = self.backup_dir / backup_name
            
            source_file = self.optimizer_dir / "MLB_Testing_Sandbox.py"
            if source_file.exists():
                shutil.copy2(source_file, backup_path)
                logging.info(f"✅ Backup created: {backup_path}")
                return True
            else:
                logging.error(f"❌ Source file not found: {source_file}")
                return False
        except Exception as e:
            logging.error(f"❌ Failed to create backup: {e}")
            return False
    
    def check_last_update(self) -> Optional[datetime]:
        """Check when the last update was performed."""
        if self.last_update_file.exists():
            try:
                with open(self.last_update_file, 'r') as f:
                    timestamp_str = f.read().strip()
                    return datetime.fromisoformat(timestamp_str)
            except Exception as e:
                logging.warning(f"Could not read last update time: {e}")
        return None
    
    def update_last_update_time(self):
        """Update the last update timestamp."""
        try:
            with open(self.last_update_file, 'w') as f:
                f.write(datetime.now().isoformat())
        except Exception as e:
            logging.error(f"Failed to update timestamp: {e}")
    
    def check_library_versions(self) -> Dict[str, Dict]:
        """Check current and latest library versions."""
        versions = {}
        
        for lib_name in self.libraries.keys():
            try:
                # Get current version
                result = subprocess.run([
                    sys.executable, '-c', f'import {lib_name}; print({lib_name}.__version__)'
                ], capture_output=True, text=True, check=True)
                current_version = result.stdout.strip()
                
                # Get latest version from PyPI
                import requests
                response = requests.get(f"https://pypi.org/pypi/{lib_name}/json", timeout=10)
                latest_version = "Unknown"
                if response.status_code == 200:
                    latest_version = response.json()['info']['version']
                
                versions[lib_name] = {
                    'current': current_version,
                    'latest': latest_version,
                    'needs_update': self._version_compare(current_version, latest_version) < 0
                }
                
            except Exception as e:
                logging.warning(f"Could not check version for {lib_name}: {e}")
                versions[lib_name] = {
                    'current': 'Unknown',
                    'latest': 'Unknown',
                    'needs_update': False
                }
        
        return versions
    
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
    
    def update_libraries(self, libraries_to_update: List[str]) -> bool:
        """Update specified libraries."""
        success = True
        
        for lib in libraries_to_update:
            try:
                logging.info(f"🔄 Updating {lib}...")
                result = subprocess.run([
                    sys.executable, '-m', 'pip', 'install', '--upgrade', lib
                ], capture_output=True, text=True, check=True)
                logging.info(f"✅ Successfully updated {lib}")
            except subprocess.CalledProcessError as e:
                logging.error(f"❌ Failed to update {lib}: {e}")
                success = False
        
        return success
    
    def test_optimizer(self) -> bool:
        """Test the optimizer after updates."""
        try:
            logging.info("🧪 Testing optimizer...")
            
            # Test import
            result = subprocess.run([
                sys.executable, '-c', 
                f'import sys; sys.path.append("{self.optimizer_dir}"); import MLB_Testing_Sandbox'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logging.info("✅ Optimizer imports successfully")
                return True
            else:
                logging.error(f"❌ Optimizer import failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logging.error("❌ Optimizer test timed out")
            return False
        except Exception as e:
            logging.error(f"❌ Optimizer test failed: {e}")
            return False
    
    def run_update_checker(self) -> Dict:
        """Run the update checker and get results."""
        try:
            result = subprocess.run([
                sys.executable, 'automation/scripts/update_checker.py'
            ], capture_output=True, text=True, cwd=self.optimizer_dir, timeout=60)
            
            if result.returncode == 0:
                logging.info("✅ Update checker completed successfully")
                # Try to read the report
                report_path = self.optimizer_dir / "system_logs" / "update_report.json"
                if report_path.exists():
                    with open(report_path, 'r') as f:
                        return json.load(f)
            else:
                logging.error(f"❌ Update checker failed: {result.stderr}")
                
        except Exception as e:
            logging.error(f"❌ Failed to run update checker: {e}")
        
        return {}
    
    def update_requirements(self) -> bool:
        """Update requirements.txt with latest versions."""
        try:
            logging.info("📦 Updating requirements.txt...")
            
            result = subprocess.run([
                sys.executable, 'automation/scripts/requirements_updater.py'
            ], capture_output=True, text=True, cwd=self.optimizer_dir, timeout=120)
            
            if result.returncode == 0:
                logging.info("✅ Requirements updated successfully")
                return True
            else:
                logging.error(f"❌ Requirements update failed: {result.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Failed to update requirements: {e}")
            return False
    
    def apply_automatic_fixes(self) -> bool:
        """Apply automatic fixes to the optimizer code."""
        try:
            optimizer_file = self.optimizer_dir / "MLB_Testing_Sandbox.py"
            
            if not optimizer_file.exists():
                logging.error(f"❌ Optimizer file not found: {optimizer_file}")
                return False
            
            with open(optimizer_file, 'r') as f:
                content = f.read()
            
            # Apply automatic fixes
            fixes_applied = 0
            
            # Fix NumPy random usage
            if 'np.random.RandomState' in content:
                content = content.replace('np.random.RandomState', 'np.random.Generator')
                fixes_applied += 1
                logging.info("✅ Fixed NumPy RandomState usage")
            
            # Fix Pandas copy_on_write
            if 'pd.options.mode.copy_on_write' not in content:
                # Add copy_on_write optimization
                import_pattern = "import pandas as pd"
                if import_pattern in content:
                    copy_on_write_code = """
# Enable copy-on-write optimization for better memory efficiency
try:
    pd.options.mode.copy_on_write = True
except AttributeError:
    # Fallback for older Pandas versions
    pass"""
                    content = content.replace(import_pattern, import_pattern + copy_on_write_code)
                    fixes_applied += 1
                    logging.info("✅ Added Pandas copy_on_write optimization")
            
            # Fix OR-Tools solver parameters
            if 'solver.parameters.num_search_workers' not in content:
                # Add multi-worker support
                solver_pattern = "solver = cp_model.CpSolver()"
                if solver_pattern in content:
                    worker_code = """
    # Configure solver for better performance
    solver.parameters.num_search_workers = 8
    solver.parameters.max_time_in_seconds = 30.0
    solver.parameters.cp_model_presolve = True"""
                    content = content.replace(solver_pattern, solver_pattern + worker_code)
                    fixes_applied += 1
                    logging.info("✅ Added OR-Tools multi-worker support")
            
            # Fix MemoryUsage compatibility issue
            if 'solver.MemoryUsage()' in content and 'try:' not in content:
                # Replace direct MemoryUsage call with try-catch
                memory_pattern = r'print\(f"     - Memory usage: \{solver\.MemoryUsage\(\):\.1f\} MB"\)'
                memory_replacement = '''# Memory usage not available in current OR-Tools version
    # print(f"     - Memory usage: {solver.MemoryUsage():.1f} MB")'''
                content = re.sub(memory_pattern, memory_replacement, content)
                fixes_applied += 1
                logging.info("✅ Fixed OR-Tools MemoryUsage compatibility")
            
            # Write updated content
            with open(optimizer_file, 'w') as f:
                f.write(content)
            
            logging.info(f"✅ Applied {fixes_applied} automatic fixes")
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to apply automatic fixes: {e}")
            return False
    
    def run_full_update(self, force: bool = False) -> bool:
        """Run a full update of the optimizer."""
        try:
            logging.info("🚀 Starting MLB_Optimizer update process...")
            
            # Check if update is needed
            last_update = self.check_last_update()
            if last_update and not force:
                days_since = (datetime.now() - last_update).days
                if days_since < 7:
                    logging.info(f"✅ Last update was {days_since} days ago. Skipping update.")
                    return True
            
            # Create backup
            if not self.create_backup():
                logging.error("❌ Failed to create backup. Aborting update.")
                return False
            
            # Check library versions
            versions = self.check_library_versions()
            libraries_to_update = [
                lib for lib, info in versions.items() 
                if info['needs_update']
            ]
            
            if libraries_to_update:
                logging.info(f"🔄 Updating libraries: {', '.join(libraries_to_update)}")
                if not self.update_libraries(libraries_to_update):
                    logging.error("❌ Failed to update libraries")
                    return False
            else:
                logging.info("✅ All libraries are up to date")
            
            # Apply automatic fixes
            if not self.apply_automatic_fixes():
                logging.error("❌ Failed to apply automatic fixes")
                return False
            
            # Test the optimizer
            if not self.test_optimizer():
                logging.error("❌ Optimizer test failed after updates")
                return False
            
            # Update requirements.txt
            if not self.update_requirements():
                logging.error("❌ Failed to update requirements")
                return False
            
            # Run update checker
            update_report = self.run_update_checker()
            
            # Generate updated compliance report
            self.generate_compliance_report()
            
            # Update timestamp
            self.update_last_update_time()
            
            # Log success
            self._log_update_success(versions, update_report)
            
            logging.info("🎉 MLB_Optimizer update completed successfully!")
            return True
            
        except Exception as e:
            logging.error(f"❌ Update failed: {e}")
            return False
    
    def _log_update_success(self, versions: Dict, update_report: Dict):
        """Log successful update details."""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'versions': versions,
                'update_report': update_report,
                'status': 'success'
            }
            
            # Read existing log
            log_data = []
            if self.log_file.exists():
                with open(self.log_file, 'r') as f:
                    log_data = json.load(f)
            
            # Add new entry
            log_data.append(log_entry)
            
            # Keep only last 10 entries
            log_data = log_data[-10:]
            
            # Write updated log
            with open(self.log_file, 'w') as f:
                json.dump(log_data, f, indent=2)
                
        except Exception as e:
            logging.error(f"Failed to log update success: {e}")
    
    def generate_compliance_report(self) -> bool:
        """Generate an updated compliance audit report."""
        try:
            logging.info("📊 Generating updated compliance report...")
            
            result = subprocess.run([
                sys.executable, 'automation/scripts/compliance_generator.py'
            ], capture_output=True, text=True, cwd=self.optimizer_dir, timeout=60)
            
            if result.returncode == 0:
                logging.info("✅ Compliance report generated successfully")
                return True
            else:
                logging.error(f"❌ Compliance report generation failed: {result.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Failed to generate compliance report: {e}")
            return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='MLB_Optimizer Auto Updater')
    parser.add_argument('--check-only', action='store_true', 
                       help='Only check for updates without applying them')
    parser.add_argument('--force', action='store_true',
                       help='Force update even if recent update exists')
    parser.add_argument('--restore', action='store_true',
                       help='Restore from latest backup')
    parser.add_argument('--silent', action='store_true',
                       help='Run silently in background mode')
    
    args = parser.parse_args()
    
    # Configure logging for silent mode
    if args.silent:
        # Remove console handler for silent operation
        for handler in logging.root.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                logging.root.removeHandler(handler)
        # Set logging to file only
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('automation/logs/auto_update.log')
            ]
        )
    
    updater = AutoUpdater()
    
    if args.check_only:
        logging.info("🔍 Checking for updates only...")
        versions = updater.check_library_versions()
        
        if not args.silent:
            print("\n📊 Update Check Results:")
            print("=" * 40)
            for lib, info in versions.items():
                status = "✅ Up to Date" if not info['needs_update'] else "🔄 Needs Update"
                print(f"{lib}: {info['current']} → {info['latest']} {status}")
        
        # Run update checker
        update_report = updater.run_update_checker()
        return
    
    if args.restore:
        logging.info("🔄 Restoring from backup...")
        # Implementation for restore functionality
        return
    
    # Run full update
    success = updater.run_full_update(force=args.force)
    
    if success:
        if not args.silent:
            print("✅ Update completed successfully!")
        logging.info("✅ Update completed successfully!")
        sys.exit(0)
    else:
        if not args.silent:
            print("❌ Update failed!")
        logging.error("❌ Update failed!")
        sys.exit(1)

if __name__ == "__main__":
    main() 