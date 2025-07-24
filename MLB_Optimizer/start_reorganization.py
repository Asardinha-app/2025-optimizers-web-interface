#!/usr/bin/env python3
"""
MLB Optimizer Reorganization Starter Script

This script safely creates the new directory structure for the MLB Optimizer
reorganization without moving any existing files. This allows us to:

1. Create the new structure alongside the existing one
2. Test the new structure before moving files
3. Maintain all existing functionality during transition
4. Have a clear rollback path if needed

Usage:
    python start_reorganization.py
"""

import os
import shutil
import sys
from pathlib import Path

def create_directory_structure():
    """Create the new directory structure for reorganization"""
    
    # Base directory
    base_dir = Path(__file__).parent
    
    # New directory structure
    new_dirs = [
        "config",
        "core",
        "core/late_swap", 
        "core/models",
        "data",
        "data/scrapers",
        "data/processors", 
        "data/validators",
        "utils",
        "automation/scripts",
        "automation/docs",
        "tests",
        "docs",
        "logs",
        "examples",
        "examples/sample_data",
        "scripts"
    ]
    
    print("Creating new directory structure...")
    
    for dir_path in new_dirs:
        full_path = base_dir / dir_path
        if not full_path.exists():
            full_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created: {dir_path}")
        else:
            print(f"⚠️  Already exists: {dir_path}")
    
    print("\n✅ Directory structure created successfully!")

def create_init_files():
    """Create __init__.py files for Python packages"""
    
    base_dir = Path(__file__).parent
    
    # Directories that need __init__.py files
    init_dirs = [
        "config",
        "core", 
        "core/late_swap",
        "core/models",
        "data",
        "data/scrapers",
        "data/processors",
        "data/validators", 
        "utils",
        "automation",
        "automation/scripts",
        "automation/docs",
        "tests",
        "examples"
    ]
    
    print("\nCreating __init__.py files...")
    
    for dir_path in init_dirs:
        init_file = base_dir / dir_path / "__init__.py"
        if not init_file.exists():
            init_file.touch()
            print(f"✅ Created: {dir_path}/__init__.py")
        else:
            print(f"⚠️  Already exists: {dir_path}/__init__.py")
    
    print("✅ __init__.py files created successfully!")

def create_placeholder_files():
    """Create placeholder files for new structure"""
    
    base_dir = Path(__file__).parent
    
    # Placeholder files to create
    placeholders = {
        "README.md": "# MLB Optimizer\n\nMain project documentation and user guide.",
        "requirements.txt": "# MLB Optimizer Dependencies\n\npandas\nortools\nnumpy\nrequests",
        "setup.py": "# MLB Optimizer Setup\n\nfrom setuptools import setup, find_packages\n\nsetup(\n    name='mlb-optimizer',\n    version='1.0.0',\n    packages=find_packages(),\n    install_requires=[\n        'pandas',\n        'ortools',\n        'numpy',\n        'requests'\n    ]\n)",
        "main.py": "# MLB Optimizer Main Entry Point\n\nfrom core.optimizer import MLBOptimizer\nfrom core.late_swap.engine import LateSwapEngine\n\ndef main():\n    \"\"\"Main entry point for MLB Optimizer\"\"\"\n    print(\"MLB Optimizer - Main Entry Point\")\n    # TODO: Implement main functionality\n\nif __name__ == \"__main__\":\n    main()",
        "config/settings.py": "# MLB Optimizer Configuration\n\nclass OptimizerConfig:\n    # File paths\n    DATA_FILE = \"/path/to/MLB_FD.csv\"\n    OUTPUT_PATH = \"/path/to/output/\"\n    \n    # Optimization settings\n    NUM_LINEUPS = 300\n    MAX_SALARY = 35000\n    MAX_ATTEMPTS = 1000\n    \n    # Stack settings\n    MAX_PRIMARY_STACK_PCT = 0.2083\n    MAX_SECONDARY_STACK_PCT = 0.126\n    \n    # Late swap settings\n    PRESERVE_STACKS = True\n    MAX_SWAP_ATTEMPTS = 100\n    \n    # Logging settings\n    LOG_LEVEL = \"INFO\"\n    LOG_FILE = \"logs/optimizer.log\"",
        "config/constraints.py": "# MLB Optimizer Constraints\n\n# Position requirements\nSLOTS = {\n    \"P\": 1,\n    \"C/1B\": 1,\n    \"2B\": 1,\n    \"3B\": 1,\n    \"SS\": 1,\n    \"OF\": 3,\n    \"UTIL\": 1\n}\n\n# Salary cap\nMAX_SALARY = 35000\n\n# Stack rules\nMAX_PRIMARY_STACK_PCT = 0.2083\nMAX_SECONDARY_STACK_PCT = 0.126",
        "scripts/run_optimizer.py": "#!/usr/bin/env python3\n\"\"\"CLI entry point for MLB Optimizer\"\"\"\n\nimport sys\nimport os\nsys.path.append(os.path.dirname(os.path.dirname(__file__)))\n\nfrom core.optimizer import MLBOptimizer\n\ndef main():\n    \"\"\"Run the MLB Optimizer\"\"\"\n    optimizer = MLBOptimizer()\n    # TODO: Add command line argument parsing\n    print(\"MLB Optimizer CLI - Coming Soon\")\n\nif __name__ == \"__main__\":\n    main()",
        "scripts/run_late_swap.py": "#!/usr/bin/env python3\n\"\"\"CLI entry point for Late Swap Optimizer\"\"\"\n\nimport sys\nimport os\nsys.path.append(os.path.dirname(os.path.dirname(__file__)))\n\nfrom core.late_swap.engine import LateSwapEngine\n\ndef main():\n    \"\"\"Run the Late Swap Optimizer\"\"\"\n    engine = LateSwapEngine()\n    # TODO: Add command line argument parsing\n    print(\"Late Swap Optimizer CLI - Coming Soon\")\n\nif __name__ == \"__main__\":\n    main()",
        "scripts/run_scrapers.py": "#!/usr/bin/env python3\n\"\"\"CLI entry point for Data Scrapers\"\"\"\n\nimport sys\nimport os\nsys.path.append(os.path.dirname(os.path.dirname(__file__)))\n\nfrom data.scrapers import AwesemoScraper, LabsScraper, SaberSimScraper, TheBatScraper\n\ndef main():\n    \"\"\"Run the Data Scrapers\"\"\"\n    # TODO: Add command line argument parsing\n    print(\"Data Scrapers CLI - Coming Soon\")\n\nif __name__ == \"__main__\":\n    main()",
        "docs/README.md": "# MLB Optimizer User Guide\n\nThis is the main user guide for the MLB Optimizer.\n\n## Quick Start\n\n1. Install dependencies: `pip install -r requirements.txt`\n2. Run optimizer: `python main.py`\n3. Run late swap: `python scripts/run_late_swap.py`\n\n## Features\n\n- Lineup optimization\n- Late swap functionality\n- Multiple projection sources\n- Constraint validation\n- Automation tools",
        "docs/DEPLOYMENT.md": "# MLB Optimizer Deployment Guide\n\nThis guide covers deployment and production setup.\n\n## Prerequisites\n\n- Python 3.8+\n- Required dependencies\n- Proper file paths configured\n\n## Installation\n\n1. Clone repository\n2. Install dependencies\n3. Configure settings\n4. Test functionality\n\n## Configuration\n\nUpdate `config/settings.py` with your specific paths and settings.",
        "docs/API.md": "# MLB Optimizer API Documentation\n\n## Core Components\n\n### MLBOptimizer\nMain optimizer class for generating lineups.\n\n### LateSwapEngine\nEngine for late swap optimization.\n\n### Data Scrapers\nVarious scrapers for projection data.\n\n## Usage Examples\n\n```python\nfrom core.optimizer import MLBOptimizer\n\noptimizer = MLBOptimizer()\nlineups = optimizer.generate_lineups()\n```",
        "docs/TROUBLESHOOTING.md": "# MLB Optimizer Troubleshooting Guide\n\n## Common Issues\n\n### Import Errors\n- Check Python path\n- Verify dependencies\n- Ensure __init__.py files exist\n\n### File Path Errors\n- Update config/settings.py\n- Verify file permissions\n- Check file existence\n\n### Performance Issues\n- Monitor memory usage\n- Check log levels\n- Optimize data processing\n\n## Getting Help\n\n1. Check logs in logs/ directory\n2. Review error messages\n3. Test individual components\n4. Consult documentation"
    }
    
    print("\nCreating placeholder files...")
    
    for file_path, content in placeholders.items():
        full_path = base_dir / file_path
        if not full_path.exists():
            full_path.write_text(content)
            print(f"✅ Created: {file_path}")
        else:
            print(f"⚠️  Already exists: {file_path}")
    
    print("✅ Placeholder files created successfully!")

def create_backup_plan():
    """Create a backup plan document"""
    
    base_dir = Path(__file__).parent
    backup_plan = base_dir / "BACKUP_PLAN.md"
    
    content = """# MLB Optimizer Backup Plan

## Current State
- Original files remain in their current locations
- New structure created alongside existing structure
- No files have been moved yet

## Backup Strategy

### Phase 1: Safe Creation ✅
- [x] New directory structure created
- [x] __init__.py files added
- [x] Placeholder files created
- [x] No existing files modified

### Phase 2: Gradual Migration (Next)
- [ ] Move files one by one
- [ ] Update imports after each move
- [ ] Test functionality after each move
- [ ] Keep original files as backup

### Phase 3: Validation (Future)
- [ ] Test all functionality in new structure
- [ ] Verify performance is maintained
- [ ] Confirm all features work
- [ ] Update documentation

### Phase 4: Cleanup (Future)
- [ ] Remove old files only after validation
- [ ] Update all references
- [ ] Final testing
- [ ] Documentation updates

## Rollback Plan

If issues arise during migration:

1. **Immediate Rollback**: Use original file locations
2. **Import Fixes**: Update imports back to original paths
3. **Testing**: Verify all functionality restored
4. **Documentation**: Update docs to reflect original structure

## Current File Locations

### Original Structure (Preserved)
- `MLB_Optimizer.py` - Main optimizer
- `MLB_Late_Swap_Optimizer.py` - Late swap optimizer
- `Scrapes/` - Data scrapers
- `late_swap/` - Late swap components
- `automation/` - Automation scripts
- `documentation/` - Documentation
- `logs/` - Log files

### New Structure (Created)
- `core/` - Core optimizer components
- `data/` - Data processing components
- `config/` - Configuration files
- `utils/` - Utility functions
- `tests/` - Test files
- `docs/` - Documentation
- `scripts/` - CLI entry points

## Next Steps

1. **Review new structure** - Ensure it meets requirements
2. **Plan file moves** - Create detailed migration plan
3. **Begin migration** - Move files one by one
4. **Test thoroughly** - Verify all functionality
5. **Update documentation** - Reflect new structure

## Safety Measures

- ✅ Original files untouched
- ✅ New structure created safely
- ✅ Backup plan documented
- ✅ Rollback strategy ready
- ✅ Testing plan in place

---
**Status**: Phase 1 Complete - Safe Structure Created
**Next Action**: Review and approve migration plan
**Risk Level**: Very Low (no files moved yet)
"""
    
    if not backup_plan.exists():
        backup_plan.write_text(content)
        print(f"✅ Created: BACKUP_PLAN.md")
    else:
        print(f"⚠️  Already exists: BACKUP_PLAN.md")

def main():
    """Main function to start reorganization"""
    
    print("🚀 MLB Optimizer Reorganization Starter")
    print("=" * 50)
    print("This script will create the new directory structure")
    print("without moving any existing files.")
    print()
    
    # Check if we're in the right directory
    if not Path("MLB_Optimizer.py").exists():
        print("❌ Error: This script must be run from the MLB_Optimizer directory")
        print("Current directory:", Path.cwd())
        sys.exit(1)
    
    try:
        # Create new structure
        create_directory_structure()
        create_init_files()
        create_placeholder_files()
        create_backup_plan()
        
        print("\n" + "=" * 50)
        print("✅ Reorganization structure created successfully!")
        print()
        print("📋 Next Steps:")
        print("1. Review the new directory structure")
        print("2. Check BACKUP_PLAN.md for details")
        print("3. Plan the file migration process")
        print("4. Begin moving files one by one")
        print("5. Test functionality after each move")
        print()
        print("🔒 Safety: No existing files were modified")
        print("📁 New structure created alongside existing structure")
        
    except Exception as e:
        print(f"❌ Error during reorganization: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 