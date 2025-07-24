# MLB Optimizer Reorganization Plan

## 🎯 Overview
This plan reorganizes the MLB_Optimizer to create a cleaner, more maintainable structure while preserving all existing functionality. The new structure will be more modular, easier to navigate, and better organized for future development.

## 📊 Current State Analysis

### Current Structure Issues:
1. **Mixed Responsibilities**: Main optimizer files mixed with utilities and documentation
2. **Scattered Components**: Related functionality spread across different directories
3. **Inconsistent Naming**: Some directories use different naming conventions
4. **Documentation Spread**: Documentation scattered across multiple directories
5. **Log Files Everywhere**: Logs in multiple locations
6. **No Clear Entry Points**: Unclear which files are main entry points

### Current Components:
- **Core Optimizers**: `MLB_Optimizer.py`, `MLB_Late_Swap_Optimizer.py`
- **Data Scrapers**: `Scrapes/` directory with 4 projection sources
- **Late Swap System**: `late_swap/` with modular components
- **Automation**: `automation/` with scripts and configuration
- **Documentation**: Multiple documentation directories
- **Logs**: Scattered across multiple locations

## 🏗️ Proposed New Structure

```
MLB_Optimizer/
├── README.md                           # Main project documentation
├── requirements.txt                    # Dependencies
├── setup.py                           # Installation script
├── main.py                            # Main entry point
├── config/
│   ├── __init__.py
│   ├── settings.py                    # Centralized configuration
│   ├── constraints.py                 # Constraint definitions
│   └── automation_config.json         # Automation settings
├── core/
│   ├── __init__.py
│   ├── optimizer.py                   # Main optimizer logic
│   ├── late_swap/
│   │   ├── __init__.py
│   │   ├── engine.py                  # Late swap engine
│   │   ├── analyzer.py                # Swap analysis
│   │   ├── validator.py               # Constraint validation
│   │   └── optimizer.py               # Swap optimization
│   └── models/
│       ├── __init__.py
│       ├── player.py                  # Player data model
│       ├── lineup.py                  # Lineup data model
│       └── swap.py                    # Swap data models
├── data/
│   ├── __init__.py
│   ├── scrapers/
│   │   ├── __init__.py
│   │   ├── awesemo.py                 # Awesemo scraper
│   │   ├── labs.py                    # Labs scraper
│   │   ├── sabersim.py                # SaberSim scraper
│   │   └── the_bat.py                 # The Bat scraper
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── csv_handler.py             # CSV processing
│   │   ├── lineup_parser.py           # Lineup parsing
│   │   └── data_cleaner.py            # Data cleaning
│   └── validators/
│       ├── __init__.py
│       └── constraint_validator.py    # Constraint validation
├── utils/
│   ├── __init__.py
│   ├── logging.py                     # Logging utilities
│   ├── performance.py                 # Performance monitoring
│   └── helpers.py                     # General utilities
├── automation/
│   ├── __init__.py
│   ├── scripts/
│   │   ├── __init__.py
│   │   ├── auto_update.py
│   │   ├── compliance_generator.py
│   │   ├── requirements_monitor.py
│   │   └── setup.py
│   ├── docs/
│   │   ├── automation_guide.md
│   │   └── compliance_summary.md
│   └── logs/
│       └── automation.log
├── tests/
│   ├── __init__.py
│   ├── test_optimizer.py
│   ├── test_late_swap.py
│   ├── test_scrapers.py
│   └── test_integration.py
├── docs/
│   ├── README.md                      # User guide
│   ├── DEPLOYMENT.md                  # Deployment guide
│   ├── API.md                         # API documentation
│   └── TROUBLESHOOTING.md             # Troubleshooting guide
├── logs/
│   ├── optimizer.log
│   ├── late_swap.log
│   └── scrapers.log
├── examples/
│   ├── basic_usage.py
│   ├── advanced_usage.py
│   └── sample_data/
└── scripts/
    ├── run_optimizer.py               # CLI entry point
    ├── run_late_swap.py               # Late swap CLI
    └── run_scrapers.py                # Scraper CLI
```

## 🔄 Migration Strategy

### Phase 1: Create New Structure (Safe - No Deletion)
1. **Create new directories** without removing existing ones
2. **Move files gradually** to new locations
3. **Update imports** in moved files
4. **Test functionality** after each move
5. **Keep old structure** as backup until migration complete

### Phase 2: Update Entry Points
1. **Create new main.py** as primary entry point
2. **Update scripts** to use new structure
3. **Test all functionality** with new entry points
4. **Update documentation** to reflect new structure

### Phase 3: Cleanup and Optimization
1. **Remove old files** after confirming new structure works
2. **Optimize imports** and dependencies
3. **Update documentation** with new structure
4. **Create comprehensive tests** for new structure

## 📋 Detailed Migration Plan

### Step 1: Create New Directory Structure
```bash
# Create new directories
mkdir -p config core/late_swap core/models data/scrapers data/processors data/validators
mkdir -p utils automation/scripts automation/docs tests docs examples scripts
```

### Step 2: Move Core Components
```bash
# Move main optimizer
mv MLB_Optimizer.py core/optimizer.py

# Move late swap components
mv late_swap/core/late_swap_engine.py core/late_swap/engine.py
mv late_swap/core/swap_analyzer.py core/late_swap/analyzer.py
mv late_swap/core/constraint_validator.py core/late_swap/validator.py
mv late_swap/core/multi_swap_optimizer.py core/late_swap/optimizer.py

# Move data models
# Create new model files from existing dataclasses
```

### Step 3: Move Data Components
```bash
# Move scrapers
mv Scrapes/New_Awesemo_MLB.py data/scrapers/awesemo.py
mv Scrapes/Labs.py data/scrapers/labs.py
mv Scrapes/SaberSim.py data/scrapers/sabersim.py
mv Scrapes/The_Bat.py data/scrapers/the_bat.py

# Move processors
mv late_swap/utils/csv_handler.py data/processors/csv_handler.py
mv late_swap/utils/lineup_parser.py data/processors/lineup_parser.py
```

### Step 4: Move Utilities
```bash
# Move utility components
mv late_swap/utils/swap_logger.py utils/logging.py
mv simple_lineup_parser.py utils/helpers.py
```

### Step 5: Move Automation
```bash
# Move automation components
mv automation/scripts/* automation/scripts/
mv automation/docs/* automation/docs/
```

### Step 6: Move Documentation
```bash
# Move documentation
mv USER_GUIDE.md docs/README.md
mv DEPLOYMENT_GUIDE.md docs/DEPLOYMENT.md
mv documentation/* docs/
```

### Step 7: Move Tests
```bash
# Move tests
mv late_swap/tests/* tests/
```

### Step 8: Consolidate Logs
```bash
# Create centralized logging
mkdir -p logs
# Move all log files to logs/ directory
```

## 🔧 Configuration Updates

### New Configuration Structure:
```python
# config/settings.py
class OptimizerConfig:
    # File paths
    DATA_FILE = "/path/to/MLB_FD.csv"
    OUTPUT_PATH = "/path/to/output/"
    
    # Optimization settings
    NUM_LINEUPS = 300
    MAX_SALARY = 35000
    MAX_ATTEMPTS = 1000
    
    # Stack settings
    MAX_PRIMARY_STACK_PCT = 0.2083
    MAX_SECONDARY_STACK_PCT = 0.126
    
    # Late swap settings
    PRESERVE_STACKS = True
    MAX_SWAP_ATTEMPTS = 100
    
    # Logging settings
    LOG_LEVEL = "INFO"
    LOG_FILE = "logs/optimizer.log"
```

### New Entry Points:
```python
# main.py
from core.optimizer import MLBOptimizer
from core.late_swap.engine import LateSwapEngine
from data.scrapers import AwesemoScraper, LabsScraper

def main():
    """Main entry point for MLB Optimizer"""
    # Initialize components
    optimizer = MLBOptimizer()
    late_swap = LateSwapEngine()
    
    # Run optimization
    lineups = optimizer.generate_lineups()
    
    # Export results
    optimizer.export_lineups(lineups)

if __name__ == "__main__":
    main()
```

## 🧪 Testing Strategy

### Test Structure:
```python
# tests/test_optimizer.py
class TestOptimizer:
    def test_lineup_generation(self):
        """Test basic lineup generation"""
        
    def test_constraint_validation(self):
        """Test constraint validation"""
        
    def test_late_swap_functionality(self):
        """Test late swap functionality"""

# tests/test_integration.py
class TestIntegration:
    def test_full_workflow(self):
        """Test complete workflow from data to output"""
        
    def test_scraper_integration(self):
        """Test scraper integration"""
```

## 📈 Benefits of New Structure

### 1. **Clear Separation of Concerns**
- Core optimization logic separated from utilities
- Data processing separated from business logic
- Configuration centralized

### 2. **Improved Maintainability**
- Related functionality grouped together
- Clear entry points and interfaces
- Consistent naming conventions

### 3. **Better Testing**
- Dedicated test directory
- Clear test organization
- Integration tests for full workflow

### 4. **Enhanced Documentation**
- Centralized documentation
- Clear API documentation
- User guides and deployment guides

### 5. **Easier Development**
- Clear module boundaries
- Consistent import patterns
- Simplified dependency management

## 🚀 Implementation Timeline

### Week 1: Foundation
- [ ] Create new directory structure
- [ ] Move core optimizer files
- [ ] Update basic imports
- [ ] Test core functionality

### Week 2: Data Layer
- [ ] Move scrapers and processors
- [ ] Update data models
- [ ] Test data processing
- [ ] Validate scrapers work

### Week 3: Late Swap System
- [ ] Move late swap components
- [ ] Update late swap imports
- [ ] Test late swap functionality
- [ ] Validate constraint checking

### Week 4: Utilities and Automation
- [ ] Move utilities and automation
- [ ] Update logging system
- [ ] Test automation scripts
- [ ] Validate all components

### Week 5: Documentation and Testing
- [ ] Move and update documentation
- [ ] Create comprehensive tests
- [ ] Update entry points
- [ ] Final validation

### Week 6: Cleanup
- [ ] Remove old files
- [ ] Optimize imports
- [ ] Performance testing
- [ ] Documentation review

## ⚠️ Risk Mitigation

### 1. **Backup Strategy**
- Keep original structure until migration complete
- Create git branches for each phase
- Regular backups during migration

### 2. **Testing Strategy**
- Test each component after moving
- Integration tests for full workflow
- Performance benchmarks

### 3. **Rollback Plan**
- Maintain original file locations
- Keep import compatibility during transition
- Document all changes for rollback

### 4. **Validation Steps**
- Verify all scrapers work
- Confirm optimizer generates valid lineups
- Test late swap functionality
- Validate constraint checking

## 🎯 Success Criteria

### Functional Requirements:
- [ ] All scrapers work in new structure
- [ ] Optimizer generates valid lineups
- [ ] Late swap functionality works
- [ ] All constraints properly validated
- [ ] Automation scripts function

### Performance Requirements:
- [ ] No performance degradation
- [ ] Faster import times
- [ ] Reduced memory usage
- [ ] Improved maintainability

### Quality Requirements:
- [ ] 90%+ test coverage
- [ ] All documentation updated
- [ ] Clear API documentation
- [ ] Consistent code style

## 📋 Next Steps

1. **Review this plan** and provide feedback
2. **Approve migration strategy** and timeline
3. **Begin Phase 1** implementation
4. **Monitor progress** and adjust as needed
5. **Complete migration** with full testing

---

**Status**: Planning Phase  
**Next Action**: Review and approve plan  
**Estimated Duration**: 6 weeks  
**Risk Level**: Low (safe migration strategy) 