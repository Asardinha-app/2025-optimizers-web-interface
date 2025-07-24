# NFL Optimizer

A Daily Fantasy Sports lineup optimizer for NFL contests using constraint programming.

## Features

- **QB Stacking**: Automatically pairs QBs with skill position players from the same team
- **Team Limits**: Enforces maximum 4 players per team when QB is used, 2 otherwise
- **RB Team Limits**: Prevents multiple RBs from same team (configurable exceptions)
- **OIS Support**: Handles "Only In Stack" players that require QB pairing
- **Player Groups**: Configurable player group constraints for advanced strategies
- **Salary Optimization**: Maximizes projected fantasy points within salary cap
- **Lineup Uniqueness**: Ensures generated lineups are sufficiently different

## Requirements

- Python 3.7+
- pandas
- numpy
- ortools (Google OR-Tools)

## Installation

```bash
pip install pandas numpy ortools
```

## Usage

1. **Prepare your CSV data** with the following columns:
   - `Id`: Unique player identifier
   - `Player ID + Player Name`: Player name
   - `Position`: Position(s) separated by "/"
   - `Team`: Team abbreviation
   - `Opponent`: Opponent team abbreviation
   - `Salary`: Player salary
   - `FPPG`: Projected fantasy points
   - `Projected Ownership`: Ownership percentage
   - `OIS`: "Y" for Only In Stack players (optional)
   - `Rush`: Rush attempts for RBs (optional)
   - `Targets`: Targets for WR/TE/RB (optional)
   - `Projection Ceil`: Ceiling projection (optional)

2. **Configure the optimizer**:
   - Update `DATA_FILE` path in `NFL_Optimizer.py`
   - Adjust lineup generation settings in `Config` class
   - Configure QB stacks in `qb_stacks_config.py`
   - Add player groups in `player_groups_config.py`

3. **Run the optimizer**:
   ```bash
   python NFL_Optimizer.py
   ```

## Configuration

### QB Stacks (`qb_stacks_config.py`)

Define QB-specific stack configurations:

```python
QB_STACKS = {
    "Patrick Mahomes": {
        "exactly_players": 0,  # 0 = use global minimum of 2
        "players": ["Travis Kelce", "Isiah Pacheco", "Rashee Rice"]
    }
}
```

### Player Groups (`player_groups_config.py`)

Define player group constraints:

```python
PLAYER_GROUPS = [
    {
        "group_name": "PHI_WR_Duo",
        "type": "Min",
        "min_players": 1,
        "max_players": 1,
        "players": ["A.J. Brown", "DeVonta Smith"],
        "team": "PHI",
        "position": "WR"
    }
]
```

## Output

The optimizer generates:
- Console output showing each lineup with projections and statistics
- CSV file with lineup IDs and summary statistics
- Stack analysis for each generated lineup

## Constraints

- **Salary Cap**: $60,000 (configurable)
- **Roster**: 1 QB, 2 RB, 3 WR, 1 TE, 1 FLEX (RB only), 1 DEF
- **Team Limits**: Max 4 players per team when QB is used, 2 otherwise
- **Minimum Teams**: At least 3 different teams
- **Uniqueness**: Each lineup must have ≤6 players in common with previous lineups

## License

This project is licensed under the MIT License. 