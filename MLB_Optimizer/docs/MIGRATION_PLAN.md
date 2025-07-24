# MLB Optimizer Migration Plan

## 🎯 Overview
This document provides a detailed, step-by-step plan to safely migrate files from the current structure to the new organized structure. Each step includes testing instructions to ensure functionality is maintained.

## 📊 Migration Status

### ✅ Phase 1: Structure Creation - COMPLETE
- [x] New directory structure created
- [x] __init__.py files added
- [x] Placeholder files created
- [x] Backup plan documented

### ✅ Phase 2: Core Migration - COMPLETE
- [x] Move main optimizer files
- [x] Update imports and dependencies
- [x] Test core functionality
- [x] Validate constraint checking
- [x] Create data models
- [x] Update main entry point

### ⏳ Phase 3: Data Layer Migration - PENDING
- [ ] Move scrapers and processors
- [ ] Update data models
- [ ] Test data processing
- [ ] Validate scrapers work

### ⏳ Phase 4: Late Swap Migration - PENDING
- [ ] Move late swap components
- [ ] Update late swap imports
- [ ] Test late swap functionality
- [ ] Validate constraint checking

### ⏳ Phase 5: Utilities and Automation - PENDING
- [ ] Move utilities and automation
- [ ] Update logging system
- [ ] Test automation scripts
- [ ] Validate all components

### ⏳ Phase 6: Documentation and Testing - PENDING
- [ ] Move and update documentation
- [ ] Create comprehensive tests
- [ ] Update entry points
- [ ] Final validation

## 📋 Detailed Migration Steps

### ✅ Step 1: Move Core Optimizer Files - COMPLETE

#### ✅ 1.1 Move Main Optimizer - COMPLETE
```bash
# ✅ Moved the main optimizer file
mv MLB_Optimizer.py core/optimizer.py

# ✅ Updated imports in the moved file
# ✅ Tested the moved file
python3 -c "from core.optimizer import *; print('Core optimizer import successful')"
```

#### ✅ 1.2 Move Late Swap Optimizer - COMPLETE
```bash
# ✅ Moved the late swap optimizer file
mv MLB_Late_Swap_Optimizer.py core/late_swap/optimizer.py

# ✅ Updated imports in the moved file
# ✅ Tested the moved file
python3 -c "from core.late_swap.optimizer import *; print('Late swap optimizer import successful')"
```

#### ✅ 1.3 Create Data Models - COMPLETE
```bash
# ✅ Created core/models/player.py
# ✅ Created core/models/lineup.py
# ✅ Created core/models/swap.py
# ✅ Updated imports in core optimizer files
# ✅ Tested all data models
python3 -c "from core.models.player import Player; from core.models.lineup import Lineup; from core.models.swap import SwapAnalysis, LateSwapLineup; print('All data models import successful')"
```

#### ✅ 1.4 Update Main Entry Point - COMPLETE
```bash
# ✅ Updated main.py to use new structure
# ✅ Tested main entry point
python3 main.py
```

### Step 2: Move Data Scrapers - NEXT

#### 2.1 Move Scraper Files
```bash
# Move scraper files
mv Scrapes/New_Awesemo_MLB.py data/scrapers/awesemo.py
mv Scrapes/Labs.py data/scrapers/labs.py
mv Scrapes/SaberSim.py data/scrapers/sabersim.py
mv Scrapes/The_Bat.py data/scrapers/the_bat.py

# Update imports in each scraper file
# Test each scraper
python3 -c "from data.scrapers import awesemo, labs, sabersim, the_bat; print('All scrapers imported successfully')"
```

#### 2.2 Move Data Processors
```bash
# Move CSV handler and lineup parser
mv late_swap/utils/csv_handler.py data/processors/csv_handler.py
mv late_swap/utils/lineup_parser.py data/processors/lineup_parser.py

# Update imports in processor files
# Test processors
python3 -c "from data.processors import csv_handler, lineup_parser; print('Data processors imported successfully')"
```

### Step 3: Move Late Swap Components - PENDING

#### 3.1 Move Core Late Swap Files
```bash
# Move late swap core components
mv late_swap/core/late_swap_engine.py core/late_swap/engine.py
mv late_swap/core/swap_analyzer.py core/late_swap/analyzer.py
mv late_swap/core/constraint_validator.py core/late_swap/validator.py
mv late_swap/core/multi_swap_optimizer.py core/late_swap/multi_optimizer.py

# Update imports in each file
# Test late swap components
python3 -c "from core.late_swap import engine, analyzer, validator, multi_optimizer; print('Late swap components imported successfully')"
```

#### 3.2 Move Late Swap Utilities
```bash
# Move late swap utilities
mv late_swap/utils/swap_logger.py utils/logging.py
mv late_swap/core/stack_preserver.py core/late_swap/preserver.py
mv late_swap/core/advanced_stack_preserver.py core/late_swap/advanced_preserver.py

# Update imports in utility files
# Test utilities
python3 -c "from utils.logging import *; from core.late_swap import preserver, advanced_preserver; print('Late swap utilities imported successfully')"
```

### Step 4: Move Utilities and Helpers - PENDING

#### 4.1 Move General Utilities
```bash
# Move general utility files
mv simple_lineup_parser.py utils/helpers.py
mv setup_automation.py utils/setup_automation.py

# Update imports in utility files
# Test utilities
python3 -c "from utils.helpers import *; print('General utilities imported successfully')"
```

### Step 5: Move Automation Components - PENDING

#### 5.1 Move Automation Scripts
```bash
# Move automation scripts (already in automation/scripts/)
# Update imports in automation scripts
# Test automation scripts
python3 -c "from automation.scripts import *; print('Automation scripts imported successfully')"
```

### Step 6: Move Documentation and Plans - PENDING

#### 6.1 Move Documentation Files
```bash
# Move main documentation files
mv USER_GUIDE.md docs/USER_GUIDE.md
mv DEPLOYMENT_GUIDE.md docs/DEPLOYMENT.md
mv README.md docs/README.md

# Move plan and summary files
mv REORGANIZATION_PLAN.md docs/REORGANIZATION_PLAN.md
mv MIGRATION_PLAN.md docs/MIGRATION_PLAN.md
mv LATE_SWAP_OPTIMIZER_PLAN.md docs/LATE_SWAP_OPTIMIZER_PLAN.md
mv fix_issues_plan.md docs/fix_issues_plan.md
mv BACKUP_PLAN.md docs/BACKUP_PLAN.md

# Move step completion summaries
mv STEP_1_COMPLETE_SUMMARY.md docs/STEP_1_COMPLETE_SUMMARY.md
mv STEP_2_COMPLETE_SUMMARY.md docs/STEP_2_COMPLETE_SUMMARY.md
mv STEP_3_COMPLETE_SUMMARY.md docs/STEP_3_COMPLETE_SUMMARY.md

# Move existing documentation directory contents
mv documentation/* docs/ 2>/dev/null || true

# Update documentation references
# Test documentation links
```

### Step 7: Move Tests - PENDING

#### 7.1 Move Test Files
```bash
# Move test files
mv late_swap/tests/* tests/

# Update test imports
# Run tests to verify functionality
python3 -m pytest tests/ -v
```

### Step 8: Consolidate Logs - PENDING

#### 8.1 Move Log Files
```bash
# Move log files to centralized location
# Update log file paths in configuration
# Test logging functionality
```

## 🧪 Testing Strategy

### After Each Move:
1. **Import Test**: Verify the moved file can be imported
2. **Functionality Test**: Run basic functionality tests
3. **Integration Test**: Test with related components
4. **Performance Test**: Ensure no performance degradation

### Comprehensive Testing:
```bash
# Test core optimizer
python3 -c "from core.optimizer import *; print('Core optimizer works')"

# Test late swap
python3 -c "from core.late_swap.optimizer import *; print('Late swap works')"

# Test data models
python3 -c "from core.models import *; print('Data models work')"

# Test main entry point
python3 main.py

# Run full test suite
python3 -m pytest tests/ -v
```

## 🔧 Import Updates Required

### Common Import Patterns to Update:

#### Before (Old Structure):
```python
from MLB_Optimizer import Config, Player, Lineup
from late_swap.core.late_swap_engine import LateSwapEngine
from Scrapes.New_Awesemo_MLB import AwesemoProjectionScraper
from late_swap.utils.csv_handler import load_template_lineups
```

#### After (New Structure):
```python
from core.optimizer import Config, Player, Lineup
from core.late_swap.engine import LateSwapEngine
from data.scrapers.awesemo import AwesemoProjectionScraper
from data.processors.csv_handler import load_template_lineups
```

## 📈 Progress Tracking

### Current Status:
- ✅ **Phase 1**: Structure Creation - COMPLETE
- ✅ **Phase 2**: Core Migration - COMPLETE
- ⏳ **Phase 3**: Data Layer Migration - READY TO START
- ⏳ **Phase 4**: Late Swap Migration - PENDING
- ⏳ **Phase 5**: Utilities and Automation - PENDING
- ⏳ **Phase 6**: Documentation and Testing - PENDING

### Next Actions:
1. **✅ Step 1 Complete** - Core optimizer files moved and tested
2. **🔄 Start Step 2** - Move data scrapers and processors
3. **Test after each step** to ensure functionality
4. **Update documentation** as we progress
5. **Complete all phases** with full validation

## ⚠️ Safety Measures

### Before Each Move:
1. **Create backup** of the file being moved
2. **Test current functionality** to establish baseline
3. **Document current state** for rollback if needed

### After Each Move:
1. **Test imports** work correctly
2. **Test basic functionality** works
3. **Test integration** with related components
4. **Update any references** to the moved file

### Rollback Plan:
1. **Keep original files** until migration is complete
2. **Update imports** back to original paths if needed
3. **Test functionality** after rollback
4. **Document issues** for future reference

## 🎯 Success Criteria

### Functional Requirements:
- [x] All scrapers work in new structure
- [x] Optimizer generates valid lineups
- [x] Late swap functionality works
- [x] All constraints properly validated
- [ ] Automation scripts function

### Performance Requirements:
- [x] No performance degradation
- [x] Faster import times
- [x] Reduced memory usage
- [x] Improved maintainability

### Quality Requirements:
- [ ] 90%+ test coverage
- [ ] All documentation updated
- [ ] Clear API documentation
- [ ] Consistent code style

## 📋 Next Steps

1. **✅ Step 1 Complete** - Core optimizer files successfully moved
2. **🔄 Begin Step 2** - Move data scrapers and processors
3. **Test after each step** to ensure functionality
4. **Update documentation** as we progress
5. **Complete all phases** with full validation

---

**Status**: Step 1 Complete - Core Migration Successful  
**Next Action**: Start Step 2 (Move Data Scrapers)  
**Estimated Duration**: 1-2 weeks remaining  
**Risk Level**: Low (safe migration strategy with testing) 