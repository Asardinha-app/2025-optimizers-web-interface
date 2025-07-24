# MLB Late Swap Optimizer - User Guide

## 📖 Overview

The MLB Late Swap Optimizer is a powerful tool designed to automatically optimize DFS lineups when players are scratched or moved in the batting order. It preserves team stacking while maintaining all original constraints.

### Key Features
- ✅ **Automatic Player Replacement**: Finds optimal substitutes for scratched players
- ✅ **Stack Preservation**: Maintains team stacking integrity
- ✅ **Salary Cap Compliance**: Ensures lineups stay under $35,000
- ✅ **Real Data Support**: Works with actual FanDuel templates
- ✅ **High Performance**: Processes 150+ lineups in under 1 second

## 🚀 Getting Started

### Step 1: Prepare Your Data

#### Required Files
1. **Player Pool CSV** (`MLB_FD.csv`)
   - Contains all available players with projections
   - Must include: Player ID, Name, Position, Team, Salary, Projection, Roster Order

2. **FanDuel Template CSV**
   - Your lineup entries in FanDuel format
   - Contains player IDs for each position

#### File Format Example
```csv
# Player Pool (MLB_FD.csv)
Player ID + Player Name,Id,Position,Salary,FPPG,Team,Roster Order
118836-52859:Jacob deGrom,118836-52859,P,11000,36.92,TEX,0
118836-102396:Logan Gilbert,118836-102396,P,9700,36.76,SEA,0

# Template (FanDuel-MLB-template.csv)
entry_id,P,C/1B,2B,3B,SS,OF,OF,OF,UTIL
3548288478,118836-52142,118836-21887,118836-102301,118836-13719,118836-16952,118836-79282,118836-163706,118836-17097,118836-135366
```

### Step 2: Configure File Paths

Edit `MLB_Late_Swap_Optimizer.py` and update the file paths:

```python
class LateSwapConfig:
    TEMPLATE_FILE_PATH = "/path/to/your/FanDuel-MLB-template.csv"
    DATA_FILE = "/path/to/your/MLB_FD.csv"
    OUTPUT_FILE_PATH = "/path/to/output/FD_MLB_Late_Swap_Lineups.csv"
```

### Step 3: Run the Optimizer

```bash
python3 MLB_Late_Swap_Optimizer.py
```

## 📊 Understanding the Output

### Console Output
```
✅ Late Swap Optimizer completed successfully
Total lineups processed: 150
Lineups with successful swaps: 5
Lineups skipped (no swaps needed): 145
```

### Output Files

#### 1. Processed Lineups CSV
- **File**: `FD_MLB_Late_Swap_Lineups.csv`
- **Format**: FanDuel upload template
- **Usage**: Upload to FanDuel for late swaps

#### 2. Log Files
- **Location**: `logs/late_swap_YYYYMMDD_HHMMSS.log`
- **Content**: Detailed processing information
- **Usage**: Troubleshooting and monitoring

## 🔧 Configuration Options

### Swap Settings
```python
# Maximum attempts to find valid swaps
MAX_SWAP_ATTEMPTS = 100

# Preserve team stacking
PRESERVE_STACKS = True

# Maintain salary cap
MAINTAIN_SALARY_CAP = True

# Skip lineups that can't be optimized
SKIP_INVALID_LINEUPS = True

# Prefer multi-swap optimization
PREFER_MULTI_SWAP = True

# Prefer stack preservation over projection
PREFER_STACK_PRESERVATION = True
```

### Performance Settings
```python
# Logging level (INFO for production, DEBUG for troubleshooting)
LOG_LEVEL = logging.INFO

# Filter players with roster order 0
FILTER_ROSTER_ORDER_ZERO = False
```

### Locked Teams
```python
# Teams whose games have started (players cannot be swapped)
LOCKED_TEAMS = [
    "NYY", "BOS", "LAD", "SFG"
]
```

## 📈 Performance Optimization

### Current Performance
- **Processing Speed**: 0.004s per lineup
- **Success Rate**: 100% parsing success
- **Memory Usage**: < 100MB for 150 lineups

### Optimization Features
1. **Enhanced Candidate Filtering**
   - Pre-filters players by position
   - Limits salary increases to $500
   - Requires minimum 0.5 point projection improvement

2. **Performance Optimizations**
   - Dictionary caching for player lookup
   - Early termination in candidate loops
   - Reduced logging overhead

3. **Parser Improvements**
   - Real FanDuel template support
   - Flexible player ID matching
   - OF column handling (OF, OF.1, OF.2)

## 🛠️ Troubleshooting

### Common Issues

#### Issue 1: Player ID Not Found
```
Player ID 118836-52142 not found in player pool
```

**Causes**:
- Player not in current player pool
- ID format mismatch
- Template contains outdated players

**Solutions**:
1. Update player pool CSV with latest data
2. Verify ID formats match between template and pool
3. Check for typos in player IDs

#### Issue 2: Template Loading Errors
```
Missing required columns: ['OF']
```

**Causes**:
- Incorrect CSV format
- Missing position columns
- Wrong file path

**Solutions**:
1. Verify template CSV has correct FanDuel format
2. Check file path in configuration
3. Ensure all required columns are present

#### Issue 3: Performance Issues
```
Average time per lineup: 0.103s
```

**Causes**:
- Debug logging enabled
- Large candidate pools
- Inefficient filtering

**Solutions**:
1. Set `LOG_LEVEL = logging.INFO`
2. Reduce candidate pool sizes
3. Check for memory issues

### Debug Mode
Enable detailed logging for troubleshooting:

```python
LOG_LEVEL = logging.DEBUG
```

This will show:
- Detailed parsing information
- Candidate filtering steps
- Optimization progress
- Performance metrics

## 📋 Best Practices

### Data Preparation
1. **Keep Player Pool Updated**
   - Use latest projections
   - Include all active players
   - Verify roster orders

2. **Validate Template Format**
   - Check column headers
   - Verify player IDs exist in pool
   - Ensure proper CSV encoding

3. **Monitor Performance**
   - Track processing time
   - Check success rates
   - Monitor memory usage

### Processing Workflow
1. **Pre-Processing**
   - Backup original templates
   - Validate file formats
   - Check file paths

2. **Processing**
   - Run with INFO logging
   - Monitor console output
   - Check for errors

3. **Post-Processing**
   - Validate output CSV
   - Review log files
   - Upload to FanDuel

### Maintenance
1. **Regular Updates**
   - Update player pool daily
   - Monitor performance metrics
   - Clean up old log files

2. **Backup Strategy**
   - Archive processed results
   - Maintain template backups
   - Version control configurations

## 🎯 Advanced Usage

### Custom Constraints
Add custom constraints by modifying the optimizer:

```python
# Add custom salary constraints
if player.salary > current_salary + 1000:
    continue

# Add custom projection requirements
if player.projection < current_projection + 1.0:
    continue
```

### Batch Processing
Process multiple templates:

```python
templates = [
    "/path/to/template1.csv",
    "/path/to/template2.csv",
    "/path/to/template3.csv"
]

for template in templates:
    config.TEMPLATE_FILE_PATH = template
    optimizer = LateSwapOptimizer(config)
    optimizer.run()
```

### Performance Monitoring
Monitor performance in real-time:

```python
import time

start_time = time.time()
optimizer.run()
end_time = time.time()

print(f"Processing time: {end_time - start_time:.2f} seconds")
```

## 📞 Support

### Log Analysis
Check log files for detailed information:
```bash
tail -f logs/late_swap_*.log
```

### Performance Monitoring
```bash
# Monitor processing time
time python3 MLB_Late_Swap_Optimizer.py

# Check memory usage
python3 -m memory_profiler MLB_Late_Swap_Optimizer.py
```

### Data Validation
```bash
# Validate CSV formats
python3 -c "import pandas as pd; df = pd.read_csv('your_file.csv'); print(df.head())"
```

---

**Version**: 1.0.0  
**Last Updated**: 2025-07-22  
**Status**: ✅ Production Ready 