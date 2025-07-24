"""
MLB Daily Fantasy Sports Lineup Optimizer
This script generates optimized lineups for MLB DFS contests using constraint programming.
"""

from typing import List, Dict, Set, Tuple, Optional
import pandas as pd
from ortools.sat.python import cp_model
import os
from dataclasses import dataclass
from pathlib import Path
import csv

# ===== Configuration =====
class Config:
    # File paths
    DATA_FILE = "/Users/adamsardinha/Desktop/MLB_FD.csv"
    
    # Lineup generation settings
    NUM_LINEUPS_TO_GENERATE = 300
    MAX_PRIMARY_STACK_PCT = 0.2083 # Default max exposure for primary stacks
    MAX_SECONDARY_STACK_PCT = 0.126 # Default max exposure for secondary stacks
    MAX_SALARY = 35000
    MAX_ATTEMPTS = 1000
    
    # Players to exclude from lineups
    EXCLUDED_PLAYERS = [

    ]
    # Teams to exclude from primary stack usage
    PRIMARY_STACK_EXCLUDED_TEAMS = [

    ]
    
    # One-off player settings
    ENABLE_ONE_OFF_PLAYERS = True  # Toggle one-off player constraints
    ONE_OFF_PLAYERS = [

    ]
    
    # Stack rules
    ENABLED_STACK_RULES = True
    AVOID_STACK_PITCHER_PAIRS = [
    {"pitchers": ["Brandon Pfaadt"], "stacks": ["LAD","STL"]},

    ]
    REQUIRE_STACK_PITCHER_PAIRS = [
        {"pitchers": [], 
         "primary": [], 
         "secondary": []},
        
    ]
    
    # Primary-Secondary Stack Pairing Rules
    # Format: "primary_team": ["allowed_secondary_team1", "allowed_secondary_team2", ...]
    PRIMARY_SECONDARY_PAIRS = {
        # "CLE": ["CHC","NYY"],
        # "PIT": ["CHC","NYY"],
    }
    

    
    # Roster settings
    SLOTS = {
        "P": 1,
        "C/1B": 1,
        "2B": 1,
        "3B": 1,
        "SS": 1,
        "OF": 3,
        "UTIL": 1
    }
    
    # Exposure settings
    RECENT_TEAMS_WINDOW = 5  # Number of recent lineups to track for each team
    MIN_TEAM_EXPOSURE = 0.05  # Minimum exposure for each team

@dataclass
class Player:
    id: int
    name: str
    positions: List[str]
    team: str
    opponent: str
    salary: int
    projection: float
    is_pitcher: bool
    ownership: float
    roster_order: int = 0  # Added for consecutive order constraints

    def __post_init__(self):
        self.current_projection = self.projection  # Initialize current projection



@dataclass
class Lineup:
    players: List[Dict]
    primary_stack: str
    secondary_stack: str
    


def load_and_clean_data(file_path: str) -> Tuple[pd.DataFrame, Set[int]]:
    """Load and clean the player data from CSV file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data file not found: {file_path}")
    
    df = pd.read_csv(file_path)
    
    # Convert columns to appropriate types
    numeric_columns = ["FPPG", "Salary", "Roster Order"]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    df["Position"] = df["Position"].astype(str)
    
    # Filter out invalid roster positions
    df = df[(df["Roster Order"] > 0) | (df["Position"] == "P")]
    
    # Get IDs of players in roster positions 8 and 9
    ro8_9_ids = set(df[df["Roster Order"].isin([8, 9])]["Id"])
    
    return df, ro8_9_ids

def create_player_objects(df: pd.DataFrame) -> List[Player]:
    """Convert DataFrame rows to Player objects."""
    players = []
    for _, row in df.iterrows():
        positions = row["Position"].split("/")
        name = row["Player ID + Player Name"]
        
        # Get roster order, defaulting to 0 for pitchers
        roster_order = 0
        if "P" not in positions:
            try:
                roster_order = int(row["Roster Order"])
            except (ValueError, TypeError):
                print(f"Warning: Invalid roster order for {name}: {row['Roster Order']}")
                roster_order = 0
        
        players.append(Player(
            id=row["Id"],
            name=name,
            positions=positions,
            team=row["Team"],
            opponent=row["Opponent"],
            salary=int(row["Salary"]),
            projection=round(row["FPPG"], 2),
            is_pitcher="P" in positions,
            ownership=float(row.get("Projected Ownership", 0)),
            roster_order=roster_order
        ))
    return players

def create_lineup_model(players: List[Player], 
                       teams: List[str],
                       primary_stack_counts: Dict[str, int],
                       secondary_stack_counts: Dict[str, int],
                       recent_primary_teams: Dict[str, int],
                       recent_secondary_teams: Dict[str, int],
                       used_lineups_sets: List[Set[int]],
                       ro8_9_ids: Set[int],
                       num_generated_lineups: int) -> Tuple[cp_model.CpModel, Dict]:
    """Create the constraint programming model for lineup optimization."""
    model = cp_model.CpModel()
    
    # Set model name for better debugging
    model.Name = "MLB_Lineup_Optimization"
    
    # Pre-compute player lists for better performance (optimized)
    pitchers = [p for p in players if p.is_pitcher]
    batters = [p for p in players if not p.is_pitcher]
    team_batters = {team: [p for p in batters if p.team == team] for team in teams}
    
    # Pre-compute excluded players set for faster lookups
    excluded_players_set = set(Config.EXCLUDED_PLAYERS)
    one_off_players_set = set(Config.ONE_OFF_PLAYERS)
    
    # Create player variables (optimized with early filtering)
    player_vars = {}
    assign = {}
    is_primary_team = {}
    is_secondary_team = {}
    
    # Only create variables for non-excluded players
    valid_players = [p for p in players if p.name.split(":")[-1].strip() not in excluded_players_set]
    
    for p in valid_players:
        player_vars[p.id] = model.NewBoolVar(f"player_{p.id}")
        assign[p.id] = {}
        
        # Optimize assignment variable creation
        for slot in Config.SLOTS:
            can_play = (
                (slot == "P" and p.is_pitcher) or
                (slot == "C/1B" and any(pos in ["C", "1B", "C/1B"] for pos in p.positions)) or
                (slot == "UTIL" and not p.is_pitcher) or
                (slot in p.positions)
            )
            if can_play:
                assign[p.id][slot] = model.NewBoolVar(f"assign_{p.id}_{slot}")
    
    # Add roster constraints (optimized)
    for slot, count in Config.SLOTS.items():
        slot_players = [p for p in valid_players if slot in assign.get(p.id, {})]
        if slot_players:
            model.Add(sum(assign[p.id][slot] for p in slot_players) == count)
    
    # Optimize player assignment constraints
    for p in valid_players:
        if assign[p.id]:
            model.Add(sum(assign[p.id][s] for s in assign[p.id]) <= 1)
            model.Add(sum(assign[p.id][s] for s in assign[p.id]) == player_vars[p.id])
    
    # Core lineup constraints (optimized)
    model.Add(sum(player_vars[p.id] for p in valid_players) == 9)
    model.Add(sum(p.salary * player_vars[p.id] for p in valid_players) <= Config.MAX_SALARY)
    model.Add(sum(player_vars[p.id] for p in valid_players if p.is_pitcher) == 1)
    
    # Optimize pitcher-opponent constraints with pre-computed lists
    for p in pitchers:
        if p.id in player_vars:  # Only if pitcher is valid
            opponents = [opp for opp in batters if opp.team == p.opponent and opp.id in player_vars]
            if opponents:
                # Use more efficient constraint: at most one of pitcher or opponent can be selected
                for opp in opponents:
                    model.Add(player_vars[p.id] + player_vars[opp.id] <= 1)
    
    # Optimize Roster Order 8/9 constraint
    ro8_9_batters = [p for p in batters if p.id in ro8_9_ids and p.id in player_vars]
    if ro8_9_batters:
        model.Add(sum(player_vars[p.id] for p in ro8_9_batters) <= 1)
    
    # Optimize team stack variables
    team_stack_vars = {t: model.NewIntVar(0, 8, f"stack_{t}") for t in teams}
    for team in teams:
        team_valid_batters = [p for p in team_batters[team] if p.id in player_vars]
        if team_valid_batters:
            model.Add(team_stack_vars[team] == sum(
                player_vars[p.id] for p in team_valid_batters
            ))
        else:
            model.Add(team_stack_vars[team] == 0)
    
    # Optimize stack constraints
    primary_flags = []
    secondary_flags = []
    
    for team in teams:
        is_primary = model.NewBoolVar(f"primary_{team}")
        is_secondary = model.NewBoolVar(f"secondary_{team}")
        is_primary_team[team] = is_primary
        is_secondary_team[team] = is_secondary
        
        # Optimize stack constraints
        model.Add(team_stack_vars[team] == 4).OnlyEnforceIf(is_primary)
        model.Add(team_stack_vars[team] != 4).OnlyEnforceIf(is_primary.Not())
        
        # Optimize secondary stack constraints
        is_secondary_3 = model.NewBoolVar(f"secondary_3_{team}")
        is_secondary_4 = model.NewBoolVar(f"secondary_4_{team}")
        
        model.Add(team_stack_vars[team] == 3).OnlyEnforceIf(is_secondary_3)
        model.Add(team_stack_vars[team] == 4).OnlyEnforceIf(is_secondary_4)
        model.Add(is_secondary_3 + is_secondary_4 == 1).OnlyEnforceIf(is_secondary)
        model.Add(is_secondary_3 + is_secondary_4 == 0).OnlyEnforceIf(is_secondary.Not())
        
        # A team cannot be both primary and secondary
        model.AddBoolOr([is_primary.Not(), is_secondary.Not()])
        
        # Exclude teams from primary stack usage
        if team in Config.PRIMARY_STACK_EXCLUDED_TEAMS:
            model.Add(is_primary == 0)
        
        primary_flags.append(is_primary)
        secondary_flags.append(is_secondary)
    
    # Exactly one primary stack and one secondary stack
    model.Add(sum(primary_flags) == 1)
    model.Add(sum(secondary_flags) == 1)
    
    # Optimize one-off player constraints
    if Config.ENABLE_ONE_OFF_PLAYERS and Config.ONE_OFF_PLAYERS:
        # Create variables for each player indicating if they're in a stack
        in_stack_vars = {}
        for p in valid_players:
            if not p.is_pitcher and p.id in player_vars:
                in_stack_vars[p.id] = model.NewBoolVar(f"in_stack_{p.id}")
                # Player is in a stack if their team is primary or secondary
                model.Add(in_stack_vars[p.id] == 1).OnlyEnforceIf([
                    is_primary_team[p.team],
                    is_secondary_team[p.team]
                ])
                model.Add(in_stack_vars[p.id] == 0).OnlyEnforceIf([
                    is_primary_team[p.team].Not(),
                    is_secondary_team[p.team].Not()
                ])
        
        # For each non-stack player, they must be in the one-off list
        for p in valid_players:
            if not p.is_pitcher and p.id in player_vars:
                is_one_off = p.name.split(":")[-1].strip() in one_off_players_set
                if not is_one_off:
                    # If player is not in one-off list, they must be in a stack
                    model.Add(in_stack_vars[p.id] == 1).OnlyEnforceIf(player_vars[p.id])
    
    # Optimize primary-secondary stack pairing constraints
    for primary_team, allowed_secondary_teams in Config.PRIMARY_SECONDARY_PAIRS.items():
        if primary_team in teams:
            secondary_flags_allowed = [
                is_secondary_team[team] 
                for team in allowed_secondary_teams 
                if team in teams
            ]
            
            if secondary_flags_allowed:
                # If primary_team is selected, one of the allowed secondary teams must be selected
                model.AddBoolOr([is_primary_team[primary_team].Not()] + secondary_flags_allowed)
                
                # If primary_team is selected, no other secondary teams can be selected
                for team in teams:
                    if team not in allowed_secondary_teams:
                        model.AddImplication(is_primary_team[primary_team], is_secondary_team[team].Not())
    
    # Optimize exposure constraints
    for team in teams:
        # Calculate current exposure
        current_primary_exposure = primary_stack_counts.get(team, 0) / max(1, num_generated_lineups)
        current_secondary_exposure = secondary_stack_counts.get(team, 0) / max(1, num_generated_lineups)
        
        # Add primary stack constraints
        if current_primary_exposure >= Config.MAX_PRIMARY_STACK_PCT:
            model.Add(is_primary_team[team] == 0)
        elif recent_primary_teams.get(team, 0) >= Config.RECENT_TEAMS_WINDOW:
            model.Add(is_primary_team[team] == 0)
        
        # Add secondary stack constraints
        if current_secondary_exposure >= Config.MAX_SECONDARY_STACK_PCT:
            model.Add(is_secondary_team[team] == 0)
        elif recent_secondary_teams.get(team, 0) >= Config.RECENT_TEAMS_WINDOW:
            model.Add(is_secondary_team[team] == 0)
    
    # Optimize uniqueness constraints
    for prev in used_lineups_sets:
        # Ensure at least 2 unique players compared to previous lineups
        prev_valid_players = [pid for pid in prev if pid in player_vars]
        if prev_valid_players:
            model.Add(sum(player_vars[pid] for pid in prev_valid_players) <= 6)
    
    # Add stack rules if enabled
    if Config.ENABLED_STACK_RULES:
        add_stack_rules(model, valid_players, player_vars, is_primary_team, is_secondary_team)
    
    # Set objective using projection (optimized)
    model.Maximize(sum(p.projection * player_vars[p.id] for p in valid_players))
    
    # Optimized model validation
    try:
        # Quick validation without solving
        model.Validate()
        print("✅ Model validation passed")
    except Exception as e:
        print(f"⚠️  Warning: Model validation error: {e}")
    
    return model, {
        "player_vars": player_vars,
        "assign": assign,
        "is_primary_team": is_primary_team,
        "is_secondary_team": is_secondary_team
    }

def add_stack_rules(model: cp_model.CpModel,
                   players: List[Player],
                   player_vars: Dict[int, cp_model.IntVar],
                   is_primary_team: Dict[str, cp_model.IntVar],
                   is_secondary_team: Dict[str, cp_model.IntVar]) -> None:
    """Add stack-related rules to the model with performance optimizations."""
    # Pre-compute sets for faster lookups
    avoid_pitchers_set = set()
    require_pitchers_set = set()
    
    for rule in Config.AVOID_STACK_PITCHER_PAIRS:
        avoid_pitchers_set.update(rule["pitchers"])
    
    for rule in Config.REQUIRE_STACK_PITCHER_PAIRS:
        require_pitchers_set.update(rule["pitchers"])
    
    # Optimize avoid stack-pitcher pairs
    for rule in Config.AVOID_STACK_PITCHER_PAIRS:
        for p in players:
            if p.is_pitcher and p.id in player_vars:
                pitcher_name = p.name.split(":")[-1].strip()
                if pitcher_name in rule["pitchers"]:
                    pitcher_var = player_vars[p.id]
                    
                    # For each team in the stacks list
                    for stack_team in rule["stacks"]:
                        # Get all batters from this team
                        team_batters = [p for p in players if p.team == stack_team and not p.is_pitcher and p.id in player_vars]
                        
                        # Sort by ownership and get top 5
                        top_5_owned = sorted(team_batters, key=lambda x: x.ownership, reverse=True)[:5]
                        
                        if len(top_5_owned) >= 3:  # Only apply rule if we have at least 3 players
                            # Create a variable that is true if 3 or more of the top 5 owned batters are used
                            high_owned_used = model.NewBoolVar(f"high_owned_used_{stack_team}")
                            
                            # Sum of top 5 owned batters in lineup
                            top_5_sum = sum(player_vars[p.id] for p in top_5_owned)
                            
                            # Set high_owned_used to true if 3 or more are used
                            model.Add(top_5_sum >= 3).OnlyEnforceIf(high_owned_used)
                            model.Add(top_5_sum < 3).OnlyEnforceIf(high_owned_used.Not())
                            
                            # If high owned batters are used, don't allow the pitcher
                            model.AddBoolOr([high_owned_used.Not(), pitcher_var.Not()])
    
    # Optimize required stack-pitcher pairs
    for rule in Config.REQUIRE_STACK_PITCHER_PAIRS:
        # Get the pitcher variables
        pitcher_vars = [player_vars[p.id] for p in players 
                      if p.is_pitcher and p.name.split(":")[-1].strip() in rule["pitchers"] and p.id in player_vars]
        
        if pitcher_vars:
            if not rule["secondary"]:  # If there's no secondary list
                # Create a variable that is true if any of the primary teams are used
                primary_used = model.NewBoolVar("primary_used")
                primary_vars = [is_primary_team[team] for team in rule["primary"] if team in is_primary_team]
                if primary_vars:
                    model.AddBoolOr(primary_vars).OnlyEnforceIf(primary_used)
                    model.AddBoolAnd([var.Not() for var in primary_vars]).OnlyEnforceIf(primary_used.Not())
                    
                    # If any of the primary teams are used, one of the specified pitchers must be used
                    model.AddBoolOr([
                        primary_used.Not(),
                        *pitcher_vars
                    ])
            else:
                # For each primary team in the rule
                for primary_team in rule["primary"]:
                    if primary_team in is_primary_team:
                        # For each secondary team in the rule
                        for secondary_team in rule["secondary"]:
                            if secondary_team in is_secondary_team:
                                # Create a variable that is true if this exact primary-secondary pair is used
                                exact_pair = model.NewBoolVar(f"exact_pair_{primary_team}_{secondary_team}")
                                
                                # The pair is used if both primary and secondary are selected
                                model.AddBoolAnd([
                                    is_primary_team[primary_team],
                                    is_secondary_team[secondary_team]
                                ]).OnlyEnforceIf(exact_pair)
                                
                                # If this exact pair is used, one of the specified pitchers must be used
                                model.AddBoolOr([
                                    exact_pair.Not(),
                                    *pitcher_vars
                                ])

def create_optimized_solver() -> cp_model.CpSolver:
    """Create a highly optimized OR-Tools solver configuration for maximum performance."""
    solver = cp_model.CpSolver()
    
    # Core performance optimizations
    solver.parameters.log_search_progress = False  # Disable verbose logging
    solver.parameters.num_search_workers = 8  # Use multiple workers for parallel search
    
    # Time limit
    solver.parameters.max_time_in_seconds = 30.0  # Set time limit
    
    # Presolve and preprocessing optimizations
    solver.parameters.cp_model_presolve = True  # Enable presolve for better performance
    solver.parameters.linearization_level = 2  # Aggressive linearization
    solver.parameters.interleave_search = True  # Interleave different search strategies
    
    return solver

def solve_lineup(model: cp_model.CpModel,
                players: List[Player],
                teams: List[str],
                variables: Dict) -> Optional[Lineup]:
    """Solve the lineup optimization model and return the solution if found."""
    solver = create_optimized_solver()
    
    # Solve the model
    status = solver.Solve(model)
    
    # Handle different solver statuses with more detailed information
    if status == cp_model.OPTIMAL:
        print(f"✅ Optimal solution found in {solver.WallTime():.2f} seconds")
        print(f"   Objective value: {solver.ObjectiveValue():.2f}")
    elif status == cp_model.FEASIBLE:
        print(f"⚠️  Feasible solution found in {solver.WallTime():.2f} seconds")
        print(f"   Objective value: {solver.ObjectiveValue():.2f}")
    elif status == cp_model.INFEASIBLE:
        print("❌ Model is infeasible - no solution exists")
        return None
    elif status == cp_model.MODEL_INVALID:
        print("❌ Model is invalid - check constraint definitions")
        return None
    elif status == cp_model.UNKNOWN:
        print("⚠️  Solver status unknown - may have hit time limit")
        if solver.WallTime() >= 30.0:
            print("   Time limit reached - consider increasing max_time_in_seconds")
        return None
    else:
        print(f"❌ Solver failed with status: {status}")
        return None
    
    # Add performance metrics
    print(f"   Search statistics:")
    print(f"     - Branches explored: {solver.NumBranches()}")
    print(f"     - Conflicts: {solver.NumConflicts()}")
    print(f"     - Wall time: {solver.WallTime():.2f} seconds")
    print(f"     - User time: {solver.UserTime():.2f} seconds")
    
    lineup = []
    lineup_ids = set()
    primary_stack = ""
    secondary_stack = ""
    
    # Get primary and secondary stacks
    for team in teams:
        if solver.Value(variables["is_primary_team"][team]):
            primary_stack = team
        if solver.Value(variables["is_secondary_team"][team]):
            secondary_stack = team
    
    # Get players in lineup
    for p in players:
        if solver.Value(variables["player_vars"][p.id]):
            assigned_slot = next((s for s in variables["assign"][p.id] 
                                if solver.Value(variables["assign"][p.id][s])), None)
            lineup.append({
                "Slot": assigned_slot,
                "Name": p.name,
                "Team": p.team,
                "Opponent": p.opponent,
                "Positions": ",".join(p.positions),
                "Salary": p.salary,
                "Projection": p.projection,
                "Ownership": p.ownership,
                "Id": p.id,
                "Roster Order": p.roster_order  # Add roster order to the dictionary
            })
            lineup_ids.add(p.id)
    
    return Lineup(lineup, primary_stack, secondary_stack)

def get_players_in_order(lineup: Lineup) -> List[Dict]:
    """Return players in the lineup ordered by their ID."""
    return sorted(lineup.players, key=lambda x: x["Id"])

def print_lineup(lineup: Lineup, lineup_num: int) -> None:
    """Print the lineup in a formatted way (minimal output)."""
    print(f"=== Lineup {lineup_num} — Primary Stack: {lineup.primary_stack}, Secondary Stack: {lineup.secondary_stack} ===")
    
    # FanDuel's position order
    fd_position_order = ['P', 'C/1B', '2B', '3B', 'SS', 'OF', 'OF', 'OF', 'UTIL']
    
    # Create position map for this lineup
    position_map = {}
    outfielders = []
    util_candidates = []
    
    for player in lineup.players:
        if player["Slot"] == "OF":
            outfielders.append(player)
        elif player["Slot"] == "UTIL":
            util_candidates.append(player)
        else:
            position_map[player["Slot"]] = player
    
    # Print in FanDuel's order
    for pos in fd_position_order:
        if pos == 'OF':
            if outfielders:
                player = outfielders.pop(0)
                print(f"{pos}: {player['Name']} ({player['Team']}) | Salary: {player['Salary']} | Proj: {player['Projection']}")
        elif pos == 'UTIL':
            if util_candidates:
                player = util_candidates[0]
                print(f"{pos}: {player['Name']} ({player['Team']}) | Salary: {player['Salary']} | Proj: {player['Projection']}")
        else:
            if pos in position_map:
                player = position_map[pos]
                print(f"{pos}: {player['Name']} ({player['Team']}) | Salary: {player['Salary']} | Proj: {player['Projection']}")
    
    total_salary = sum(p['Salary'] for p in lineup.players)
    total_projection = sum(p['Projection'] for p in lineup.players)
    print(f"Total Salary: ${total_salary}")
    print(f"Total Projection: {total_projection:.2f}\n")

def export_to_csv(lineups: List[Lineup], output_path: str) -> None:
    """Export lineups to a CSV file in FanDuel format."""
    # FanDuel's position order
    fd_position_order = ['P', 'C/1B', '2B', '3B', 'SS', 'OF', 'OF', 'OF', 'UTIL']
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        # Write header
        writer.writerow(['P', 'C/1B', '2B', '3B', 'SS', 'OF', 'OF', 'OF', 'UTIL'])
        
        # Write each lineup
        for lineup in lineups:
            # Create position map for this lineup
            position_map = {}
            outfielders = []
            util_candidates = []
            
            for player in lineup.players:
                if player["Slot"] == "OF":
                    outfielders.append(player)
                elif player["Slot"] == "UTIL":
                    util_candidates.append(player)
                else:
                    position_map[player["Slot"]] = player
            
            # Build row in FanDuel's order
            row = []
            for pos in fd_position_order:
                if pos == 'OF':
                    if outfielders:
                        player = outfielders.pop(0)
                        row.append(player["Id"])
                elif pos == 'UTIL':
                    if util_candidates:
                        player = util_candidates[0]
                        row.append(player["Id"])
                else:
                    if pos in position_map:
                        player = position_map[pos]
                        row.append(player["Id"])
            
            writer.writerow(row)

def monitor_performance(solver: cp_model.CpSolver, attempt: int, total_lineups: int) -> None:
    """Monitor and report solver performance metrics."""
    if attempt % 10 == 0:  # Report every 10 attempts
        print(f"\n📊 Performance Metrics (Attempt {attempt}, Lineups: {total_lineups}):")
        print(f"   - Wall time: {solver.WallTime():.2f} seconds")
        print(f"   - User time: {solver.UserTime():.2f} seconds")
        print(f"   - Branches explored: {solver.NumBranches():,}")
        print(f"   - Conflicts: {solver.NumConflicts():,}")
        print(f"   - Average time per attempt: {solver.WallTime() / max(1, attempt):.3f} seconds")
        print(f"   - Success rate: {(total_lineups / max(1, attempt)) * 100:.1f}%")

def main():
    """Main function to run the lineup optimizer with minimal output."""
    try:
        # Load and process data
        df, ro8_9_ids = load_and_clean_data(Config.DATA_FILE)
        players = create_player_objects(df)
        teams = list(set(p.team for p in players))
        
        # Validate that we have enough players for the model
        if len(players) < 9:
            raise ValueError(f"Insufficient players ({len(players)}) for lineup optimization. Need at least 9 players.")
        
        # Validate that we have at least one pitcher
        pitchers = [p for p in players if p.is_pitcher]
        if not pitchers:
            raise ValueError("No pitchers found in player pool. At least one pitcher is required.")
        
        # Initialize tracking variables
        generated_lineups = []
        used_lineups_sets = []
        primary_stack_counts = {}
        secondary_stack_counts = {}
        pitcher_counts = {}
        recent_primary_teams = {team: 0 for team in teams}
        recent_secondary_teams = {team: 0 for team in teams}
        stack_combinations = {}
        stack_type_counts = {"4-3": 0, "4-4": 0}
        attempt = 0
        
        for player in players:
            if player.is_pitcher:
                pitcher_counts[player.name] = 0
        
        # Generate lineups
        while (len(generated_lineups) < Config.NUM_LINEUPS_TO_GENERATE and 
               attempt < Config.MAX_ATTEMPTS):
            attempt += 1
            model, variables = create_lineup_model(
                players, teams, primary_stack_counts, secondary_stack_counts,
                recent_primary_teams, recent_secondary_teams, used_lineups_sets,
                ro8_9_ids, len(generated_lineups)
            )
            lineup = solve_lineup(model, players, teams, variables)
            if not lineup:
                continue
            primary_stack_counts[lineup.primary_stack] = primary_stack_counts.get(lineup.primary_stack, 0) + 1
            secondary_stack_counts[lineup.secondary_stack] = secondary_stack_counts.get(lineup.secondary_stack, 0) + 1
            stack_key = f"{lineup.primary_stack}-{lineup.secondary_stack}"
            stack_combinations[stack_key] = stack_combinations.get(stack_key, 0) + 1
            secondary_stack_size = sum(1 for p in lineup.players if p["Team"] == lineup.secondary_stack and p["Slot"] != "P")
            stack_type = "4-4" if secondary_stack_size == 4 else "4-3"
            stack_type_counts[stack_type] += 1
            for player in lineup.players:
                if player["Slot"] == "P":
                    pitcher_name = player["Name"].split(":")[-1].strip()
                    pitcher_counts[pitcher_name] = pitcher_counts.get(pitcher_name, 0) + 1
            for team in teams:
                if team == lineup.primary_stack:
                    recent_primary_teams[team] += 1
                else:
                    recent_primary_teams[team] = max(0, recent_primary_teams[team] - 1)
                if team == lineup.secondary_stack:
                    recent_secondary_teams[team] += 1
                else:
                    recent_secondary_teams[team] = max(0, recent_secondary_teams[team] - 1)
            generated_lineups.append(lineup)
            used_lineups_sets.append(set(p["Id"] for p in lineup.players))
            print_lineup(lineup, len(generated_lineups))
        print(f"Generated {len(generated_lineups)} lineups in {attempt} attempts")
        if len(generated_lineups) > 0:
            output_path = "/Users/adamsardinha/Desktop/FD_MLB_Lineups.csv"
            export_to_csv(generated_lineups, output_path)
            print(f"Exported lineups to {output_path}")
        else:
            print("No lineups were generated. Please check your configuration settings and try again.")
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main()
