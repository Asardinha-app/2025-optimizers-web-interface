# MLB Optimizer API Documentation

## Core Components

### MLBOptimizer
Main optimizer class for generating lineups.

### LateSwapEngine
Engine for late swap optimization.

### Data Scrapers
Various scrapers for projection data.

## Usage Examples

```python
from core.optimizer import MLBOptimizer

optimizer = MLBOptimizer()
lineups = optimizer.generate_lineups()
```