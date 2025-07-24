# NHL Optimizer

A sophisticated daily fantasy sports lineup generator specifically designed for NHL contests on FanDuel.

## Features

- **Advanced Line Stacking**: Primary and secondary line stacks with goalie correlation
- **Exposure Management**: Prevents over-exposure using lockout mechanisms
- **Premium Defensemen**: Focuses on high-salary, high-shot defensemen
- **Deterministic Generation**: Consistent, reproducible lineups
- **Comprehensive Export**: Detailed statistics, rankings, and z-scores

## Quick Start

1. **Prepare your data file** (`NHL_FD.csv`) with the required columns:
   - `Id`, `Player ID + Player Name`, `Position`, `Team`, `Opponent`
   - `Salary`, `FPPG`, `Roster Order`
   - Optional: `Goalie`, `shatt`, `Projection Ceil`, `Projected Ownership`, `pp_line`

2. **Update the configuration** in `NHL_Optimizer.py`:
   ```python
   class Config:
       DATA_FILE = "/path/to/your/NHL_FD.csv"
       NUM_LINEUPS = 300
       MAX_SALARY = 55000
   ```

3. **Run the optimizer**:
   ```bash
   python NHL_Optimizer.py
   ```

4. **Check the output**:
   - Console output shows detailed lineup information
   - `nhl_lineups.csv` contains exported lineups with rankings

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `DATA_FILE` | `/Users/adamsardinha/Desktop/NHL_FD.csv` | Path to player data CSV |
| `NUM_LINEUPS` | 300 | Number of lineups to generate |
| `MAX_SALARY` | 55000 | Maximum salary cap per lineup |
| `MAX_PRIMARY_STACK_PCT` | 0.20 | Max exposure for primary stacks (20%) |
| `MAX_SECONDARY_STACK_PCT` | 0.15 | Max exposure for secondary stacks (15%) |

## Lineup Structure

Each lineup contains exactly 9 players:
- **2 Centers** (C1, C2)
- **4 Wings** (W1, W2, W3, W4)
- **2 Defensemen** (D1, D2)
- **1 Goalie** (G)

## Stacking Strategy

### Primary Stack
- 3 forwards + 1 goalie from same team
- Maximum 20% exposure
- Goalie correlation constraint applied

### Secondary Stack
- 3 forwards from different team
- Maximum 15% exposure
- Cannot pair with primary stack from same team

## Data Requirements

### Required Columns
- `Id`: Unique player identifier
- `Player ID + Player Name`: Format "ID: Name"
- `Position`: C, W, D, or G
- `Team`: Player's team
- `Opponent`: Opposing team
- `Salary`: Player salary
- `FPPG`: Fantasy points projection
- `Roster Order`: Line number (1-4 for forwards)

### Optional Columns
- `Goalie`: "Confirmed" or "Expected" for goalies
- `shatt`: Shots attempted
- `Projection Ceil`: Ceiling projection
- `Projected Ownership`: Ownership percentage
- `pp_line`: Power play line (0 = no PP time)

## Output Format

The optimizer exports lineups to CSV with:

### Slot Columns
- C1, C2, W1, W2, W3, W4, D1, D2, G

### Summary Columns
- Primary_Stack, Secondary_Stack
- Total_Projection, Total_Salary, Total Ceiling, Total Shots
- Product Ownership

### Ranking Columns
- Projection Rank, Ceiling Rank, Shots Rank, Ownership Rank
- Average rank and z-scores for each metric

## Advanced Features

### Premium Defensemen Filter
- 65th percentile salary threshold
- 50th percentile shots threshold
- Only defensemen meeting both criteria are used

### Exposure Management
- Automatic lockout after each use
- Unlocks when exposure drops below threshold
- Prevents over-concentration

### Popular Line Prevention
- Top 2 most popular lines cannot be paired together
- Based on ownership projections

## Troubleshooting

### Common Issues

**No eligible primary stacks**
- Check that lines have 3+ C/W players
- Verify goalie availability
- Ensure goalie correlation constraint

**Salary cap violations**
- Verify salary data format
- Check for data entry errors

**No premium defensemen**
- Review salary and shots data
- Adjust percentile thresholds if needed

## Performance Notes

- Deterministic algorithms ensure reproducible results
- Processing time scales with lineup count and player pool size
- Memory usage is minimal due to efficient data structures

## Documentation

For detailed documentation, see `docs/nhl-optimizer.rst` in the main documentation directory.

## License

This optimizer is part of the pydfs-lineup-optimizer project. 