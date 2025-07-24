# MLB Optimizer

A comprehensive MLB lineup optimization system with late swap capabilities, automated updates, and advanced stack preservation algorithms.

## 📁 Project Structure

```
MLB_Optimizer/
├── core/                    # Core optimization components
│   ├── optimizer.py         # Main optimizer
│   ├── models/             # Data models (Player, Lineup, etc.)
│   └── late_swap/          # Late swap optimization
├── data/                   # Data processing
│   ├── scrapers/           # Data scrapers (Awesemo, Labs, etc.)
│   └── processors/         # Data processors
├── utils/                  # Utility functions
│   ├── helpers.py          # Lineup parsing and helpers
│   ├── logging.py          # Logging utilities
│   └── setup_automation.py # Automation setup
├── config/                 # Configuration files
│   └── scraper_config.py   # Scraper configuration
├── automation/             # Automation components
│   ├── scripts/            # Automation scripts
│   ├── docs/              # Automation documentation
│   └── logs/              # Automation logs
├── docs/                   # Documentation and plans
│   ├── USER_GUIDE.md      # User guide
│   ├── DEPLOYMENT.md      # Deployment guide
│   ├── REORGANIZATION_PLAN.md # Reorganization plan
│   └── [Other documentation]
├── tests/                  # Test files
├── logs/                   # Application logs
└── main.py                 # Main entry point
```

## 🚀 Quick Start

### Basic Usage
```bash
# Run the main optimizer
python3 main.py

# Run late swap optimizer
python3 -c "from core.late_swap.optimizer import main; main()"
```

### Import Examples
```python
# Import core optimizer
from core.optimizer import *

# Import late swap components
from core.late_swap import LateSwapEngine, SwapAnalysis

# Import utilities
from utils.helpers import parse_lineup_simple
from utils.logging import setup_logger

# Import data processors
from data.processors import csv_handler, lineup_parser
```

## 📚 Documentation

- **[User Guide](docs/USER_GUIDE.md)** - Complete user guide
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Deployment instructions
- **[Reorganization Plan](docs/REORGANIZATION_PLAN.md)** - Project reorganization details
- **[Migration Plan](docs/MIGRATION_PLAN.md)** - Migration strategy
- **[Late Swap Plan](docs/LATE_SWAP_OPTIMIZER_PLAN.md)** - Late swap optimization details

## 🔧 Features

- **Advanced Lineup Optimization** - OR-Tools based constraint programming
- **Late Swap Optimization** - Real-time lineup adjustments
- **Stack Preservation** - Maintain team stacks during swaps
- **Automated Updates** - Weekly library and compliance updates
- **Data Scraping** - Multiple data source integration
- **Comprehensive Logging** - Detailed operation tracking

## 🧪 Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test categories
python3 -m pytest tests/test_optimizer.py -v
python3 -m pytest tests/test_late_swap.py -v
```

## 📊 Status

- ✅ **Core Optimizer** - Fully functional
- ✅ **Late Swap Engine** - Complete with advanced algorithms
- ✅ **Data Processing** - Scrapers and processors organized
- ✅ **Utilities** - Helper functions and logging
- ✅ **Automation** - Automated updates and monitoring
- ✅ **Documentation** - Comprehensive documentation organized

## 🔄 Recent Reorganization

This project has been reorganized for better maintainability and structure. All components are now properly organized into logical directories with clean imports and comprehensive documentation.

For detailed information about the reorganization process, see the [Reorganization Plan](docs/REORGANIZATION_PLAN.md) and individual step summaries in the `docs/` directory. 