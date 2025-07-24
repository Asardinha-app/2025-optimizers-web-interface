# NFL Optimizer Configuration Guide

This guide explains how to configure the NFL Optimizer for your specific needs.

## Quick Start

1. **Update the data file path** in `NFL_Optimizer.py`:
   ```python
   DATA_FILE = "/path/to/your/NFL_FD.csv"
   ```

2. **Configure lineup generation settings**:
   ```python
   NUM_LINEUPS_TO_GENERATE = 10
   MAX_SALARY = 60000
   MIN_SALARY = 59000
   ```

3. **Add QB stacks** in `qb_stacks_config.py`:
   ```python
   QB_STACKS = {
       "Patrick Mahomes": {
           "exactly_players": 0,
           "players": ["Travis Kelce", "Isiah Pacheco", "Rashee Rice"]
       }
   }
   ```

4. **Add player groups** in `player_groups_config.py`:
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

## CSV File Requirements

Your CSV file must contain these columns:

| Column | Required | Description |
|--------|----------|-------------|
| `Id` | Yes | Unique player identifier |
| `Player ID + Player Name` | Yes | Player name |
| `Position` | Yes | Position(s) separated by "/" |
| `Team` | Yes | Team abbreviation |
| `Opponent` | Yes | Opponent team abbreviation |
| `Salary` | Yes | Player salary |
| `FPPG` | Yes | Projected fantasy points |
| `Projected Ownership` | Yes | Ownership percentage |
| `OIS` | No | "Y" for Only In Stack players |
| `Rush` | No | Rush attempts for RBs |
| `Targets` | No | Targets for WR/TE/RB |
| `Projection Ceil` | No | Ceiling projection |

## QB Stack Configuration

### Structure
```python
QB_STACKS = {
    "QB Name": {
        "exactly_players": 0,  # 0 = use global minimum of 2
        "players": ["Player1", "Player2", "Player3"]
    }
}
```

### Parameters
- **exactly_players**: Exact number of skill players required (0 = use global minimum of 2)
- **players**: List of skill position players to include in the stack

### Validation Rules
- `exactly_players` must be 0 or ≥ 2
- `exactly_players` must be ≤ 4
- All player names must exist in your CSV data

## Player Group Configuration

### Group Types

#### Min/Max Groups
```python
{
    "group_name": "PHI_WR_Duo",
    "type": "Min",  # or "Max"
    "min_players": 1,  # for Min groups
    "max_players": 1,  # for Max groups
    "players": ["A.J. Brown", "DeVonta Smith"],
    "team": "PHI",  # optional
    "position": "WR"  # optional
}
```

#### QB-RB Restriction Groups
```python
{
    "group_name": "QB-RB Same Team Restriction",
    "type": "QB_RB_Restriction",
    "allowed_pairs": ["Player A", "Player B", "Player C"]
}
```

### Conditional Logic (Optional)
```python
{
    "group_name": "KC_Team_Stack",
    "type": "Min",
    "min_players": 3,
    "max_players": 4,
    "players": ["Travis Kelce", "Isiah Pacheco", "Rashee Rice"],
    "team": "KC",
    "conditional_players": ["Patrick Mahomes"],
    "conditional_logic": "ANY"  # ANY, ALL, XOR, NAND, NOR, AT_LEAST_1, etc.
}
```

## Main Configuration Options

### Lineup Generation
```python
NUM_LINEUPS_TO_GENERATE = 10
MAX_ATTEMPTS = 1000
```

### Salary Constraints
```python
MAX_SALARY = 60000
MIN_SALARY = 59000
```

### RB Team Limits
```python
RB_TEAM_LIMIT = {
    "enabled": True,
    "max_rbs_per_team": 1,
    "excluded_teams": ["DET"]  # Teams where multiple RBs are allowed
}
```

### Roster Structure
```python
SLOTS = {
    "QB": 1,
    "RB": 2,
    "WR": 3,
    "TE": 1,
    "FLEX": 1,  # Can only be RB
    "D": 1  # Defense position
}
```

## Validation

The optimizer automatically validates your configurations:

1. **QB Stack Validation**: Checks that all players exist in your CSV data
2. **Player Group Validation**: Verifies group configurations and player availability
3. **Configuration Warnings**: Alerts you to missing players or invalid settings

Run the optimizer to see validation results:
```bash
python NFL_Optimizer.py
```

## Troubleshooting

### Common Issues

1. **Missing Players**: Ensure all player names in configurations match exactly with your CSV data
2. **Invalid Groups**: Check that group types and parameters are correct
3. **No Lineups Generated**: Verify that constraints aren't too restrictive
4. **File Not Found**: Update the `DATA_FILE` path in `NFL_Optimizer.py`

### Debugging

- Check the validation output at the start of optimization
- Review warnings about missing players
- Verify CSV file format and column names
- Test with simpler configurations first

## Advanced Configuration

### Custom Constraints

You can add custom constraints by modifying the constraint functions in `NFL_Optimizer.py`:

- `add_skill_position_team_limit()`: Team limits when QB is used
- `add_qb_stack_constraint()`: QB stacking rules
- `add_rb_team_limit()`: RB team restrictions
- `add_ois_constraints()`: Only In Stack rules
- `add_player_group_constraints()`: Player group logic

### Performance Tuning

- Reduce `NUM_LINEUPS_TO_GENERATE` for faster testing
- Increase `MAX_ATTEMPTS` if not enough lineups are generated
- Simplify player groups to reduce constraint complexity 