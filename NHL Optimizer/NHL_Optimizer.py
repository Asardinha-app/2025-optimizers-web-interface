"""
NHL Daily Fantasy Sports Lineup Optimizer
This script generates optimized lineups for NHL DFS contests using constraint programming.
"""

from typing import List, Dict, Set, Tuple, Optional
import pandas as pd
from ortools.sat.python import cp_model
import os
from dataclasses import dataclass
import numpy as np

# ===== Configuration =====
class Config:
    DATA_FILE = "/Users/adamsardinha/Desktop/NHL_FD.csv"
    NUM_LINEUPS = 300
    MAX_SALARY = 55000
    MAX_ATTEMPTS = 300
    MAX_PRIMARY_STACK_PCT = 0.1 # 20% max exposure for Primary stack (with goalie)
    MAX_SECONDARY_STACK_PCT = 0.085  # 15% max exposure for Secondary stack (without goalie)
    # Set to True to allow goalies to be paired with skaters from their opponent team
    # Useful for short slates where you want to maximize goalie correlation
    ALLOW_GOALIE_VS_OPPONENT = False
    
    # Roster settings for FanDuel NHL (UTIL can be C or W)
    SLOTS = {
        "C": 2,
        "W": 2,
        "D": 2,
        "G": 1,
        "UTIL": 2
    }
    
    # Exposure settings
    RECENT_TEAMS_WINDOW = 5  # Number of recent lineups to track for each team

@dataclass
class Player:
    id: str
    name: str
    position: str
    team: str
    opponent: str
    salary: int
    projection: float
    roster_order: int
    is_goalie: bool = False
    shatt: float = 0.0
    ceiling: float = 0.0
    projected_ownership: float = 0.0
    
    def __post_init__(self):
        self.is_goalie = "G" in self.position

@dataclass
class Lineup:
    players: List[Player]
    primary_stack: str  # Team:RO format - includes goalie
    secondary_stack: str  # Team:RO format - no goalie
    total_salary: int
    total_projection: float
    
    def __post_init__(self):
        self.total_salary = sum(p.salary for p in self.players)
        self.total_projection = sum(p.projection for p in self.players)

def load_data(file_path: str) -> pd.DataFrame:
    """Load and clean the player data."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data file not found: {file_path}")
    df = pd.read_csv(file_path)
    # Convert numeric columns
    df["Salary"] = pd.to_numeric(df["Salary"], errors="coerce")
    df["FPPG"] = pd.to_numeric(df["FPPG"], errors="coerce")
    df["Roster Order"] = pd.to_numeric(df["Roster Order"], errors="coerce")
    return df

def filter_players(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all player filters."""
    skaters = df[
        df["Position"].str.contains("C|W|D", na=False) &
        (df["Roster Order"] >= 1) & (df["Roster Order"] <= 4)
    ]
    if "pp_line" in skaters.columns:
        dmen = skaters["Position"].str.contains("D", na=False)
        pp_zero = skaters["pp_line"] == 0
        skaters = skaters[~(dmen & pp_zero)]
    if "Goalie" in df.columns:
        goalies = df[
            df["Position"].str.contains("G", na=False) &
            df["Goalie"].astype(str).str.contains("Confirmed|Expected", case=False, na=False)
        ]
    else:
        goalies = df[0:0]
    filtered = pd.concat([skaters, goalies], ignore_index=True)
    filtered = filtered[filtered["FPPG"] > -1]
    filtered = filtered[~((filtered["Position"].str.contains("G", na=False)) & (filtered["FPPG"] == 0))]
    return filtered

def create_players(df: pd.DataFrame) -> List[Player]:
    """Convert DataFrame to Player objects."""
    players = []
    
    for _, row in df.iterrows():
        player = Player(
            id=str(row["Id"]),
            name=row["Player ID + Player Name"].split(":")[-1].strip(),
            position=row["Position"],
            team=row["Team"],
            opponent=row["Opponent"],
            salary=int(row["Salary"]),
            projection=float(row["FPPG"]),
            roster_order=int(row["Roster Order"]) if pd.notna(row["Roster Order"]) else 0,
            shatt=float(row["shatt"]) if "shatt" in row and pd.notna(row["shatt"]) else 0.0,
            ceiling=float(row["Projection Ceil"]) if "Projection Ceil" in row and pd.notna(row["Projection Ceil"]) else 0.0,
            projected_ownership=float(row["Projected Ownership"]) if "Projected Ownership" in row and pd.notna(row["Projected Ownership"]) else 0.0
        )
        players.append(player)
    
    return players

def get_lines(players: List[Player]) -> Dict[str, List[Player]]:
    """Get all available lines (Team:RO format) with 3+ C/W players."""
    lines = {}
    
    for player in players:
        if not player.is_goalie and player.roster_order > 0:
            if "C" in player.position or "W" in player.position:
                line_key = f"{player.team}:{player.roster_order}"
                if line_key not in lines:
                    lines[line_key] = []
                lines[line_key].append(player)
    
    # Only keep lines with 3+ C/W players
    valid_lines = {k: v for k, v in lines.items() if len(v) >= 3}
    return valid_lines

def print_valid_stack_combinations(players, lines):
    pass  # Remove diagnostic output

def create_lineup_model(players: List[Player], 
                       lines: Dict[str, List[Player]],
                       teams: List[str],
                       primary_stack_counts: Dict[str, int],
                       secondary_stack_counts: Dict[str, int],
                       primary_stack_last_used: Dict[str, int],
                       secondary_stack_last_used: Dict[str, int],
                       recent_primary_teams: Dict[str, int],
                       recent_secondary_teams: Dict[str, int],
                       used_lineups_sets: List[Set[str]],
                       num_generated_lineups: int) -> Tuple[cp_model.CpModel, Dict]:
    """Create the constraint programming model for lineup optimization."""
    model = cp_model.CpModel()
    
    # Create player variables
    player_vars = {p.id: model.NewBoolVar(f"player_{p.id}") for p in players}
    
    # === CORE ROSTER CONSTRAINTS ===
    # Total players
    model.Add(sum(player_vars[p.id] for p in players) == 9)
    
    # Salary cap
    model.Add(sum(p.salary * player_vars[p.id] for p in players) <= Config.MAX_SALARY)
    
    # Position constraints
    centers = [p for p in players if "C" in p.position]
    wings = [p for p in players if "W" in p.position]
    defensemen = [p for p in players if "D" in p.position]
    goalies = [p for p in players if p.is_goalie]
    
    # Exactly 2 centers, 2 wings, 2 defensemen, 1 goalie, 2 UTIL (C or W)
    model.Add(sum(player_vars[p.id] for p in centers) >= 2)  # At least 2 centers
    model.Add(sum(player_vars[p.id] for p in wings) >= 2)    # At least 2 wings
    model.Add(sum(player_vars[p.id] for p in defensemen) == 2)  # Exactly 2 defensemen
    model.Add(sum(player_vars[p.id] for p in goalies) == 1)  # Exactly 1 goalie
    
    # UTIL slots: total C+W must be 6 (2C + 2W + 2UTIL)
    model.Add(sum(player_vars[p.id] for p in centers + wings) == 6)
    
    # === TEAM CONSTRAINTS ===
    # Max 4 players per team
    for team in teams:
        model.Add(sum(player_vars[p.id] for p in players if p.team == team) <= 4)
    
    # At least 3 unique teams
    team_used_vars = {t: model.NewBoolVar(f"team_used_{t}") for t in teams}
    for team in teams:
        model.Add(sum(player_vars[p.id] for p in players if p.team == team) >= 1).OnlyEnforceIf(team_used_vars[team])
        model.Add(sum(player_vars[p.id] for p in players if p.team == team) == 0).OnlyEnforceIf(team_used_vars[team].Not())
    model.Add(sum(team_used_vars.values()) >= 3)
    
    # === PRIMARY STACK CONSTRAINTS ===
    # Create primary stack variables for each line that has a goalie
    primary_line_stack_vars = {}
    for line_key, line_players in lines.items():
        team = line_key.split(":")[0]
        c_w_players = [p for p in line_players if ("C" in p.position or "W" in p.position)]
        team_goalies = [p for p in players if p.is_goalie and p.team == team]
        
        # Only create primary stack variables for lines with 3+ C/W players and available goalies
        if len(c_w_players) >= 3 and team_goalies:
            var = model.NewBoolVar(f"primary_stack_{line_key}")
            primary_line_stack_vars[line_key] = var
            
            # If this line is primary, exactly 3 C/W must be selected from this line
            model.Add(sum(player_vars[p.id] for p in c_w_players) == 3).OnlyEnforceIf(var)
            
            # Exactly 1 goalie from this team if this line is primary
            model.Add(sum(player_vars[g.id] for g in team_goalies) == 1).OnlyEnforceIf(var)
    
    # Exactly one primary stack
    if primary_line_stack_vars:
        model.Add(sum(primary_line_stack_vars.values()) == 1)
    
    # === SECONDARY STACK CONSTRAINTS ===
    # Create secondary stack variables for each line
    secondary_line_stack_vars = {}
    for line_key, line_players in lines.items():
        team = line_key.split(":")[0]
        c_w_players = [p for p in line_players if ("C" in p.position or "W" in p.position)]
        if len(c_w_players) == 3:
            var = model.NewBoolVar(f"secondary_stack_{line_key}")
            secondary_line_stack_vars[line_key] = var
            
            # If this line is secondary, exactly 3 C/W must be selected
            model.Add(sum(player_vars[p.id] for p in c_w_players) == 3).OnlyEnforceIf(var)
            
            # No goalie from this team if this line is secondary
            team_goalies = [p for p in players if p.is_goalie and p.team == team]
            if team_goalies:
                model.Add(sum(player_vars[g.id] for g in team_goalies) == 0).OnlyEnforceIf(var)
    
    # Exactly one secondary stack
    if secondary_line_stack_vars:
        model.Add(sum(secondary_line_stack_vars.values()) == 1)
    
    # Secondary stack must be from different team than primary stack
    for line_key in secondary_line_stack_vars:
        team = line_key.split(":")[0]
        for primary_line_key in primary_line_stack_vars:
            primary_team = primary_line_key.split(":")[0]
            if team == primary_team:
                model.AddImplication(primary_line_stack_vars[primary_line_key], secondary_line_stack_vars[line_key].Not())
    
    # === EXPOSURE CONSTRAINTS ===
    # Primary stack exposure - AFTER EACH strategy
    for line_key in lines:
        if line_key in primary_stack_last_used:
            current_count = primary_stack_counts.get(line_key, 0)
            # Calculate the exposure percentage: count / total lineups generated
            if num_generated_lineups > 0:
                exposure_pct = current_count / num_generated_lineups
                # Block this line as primary if exposure is still above threshold
                if exposure_pct >= Config.MAX_PRIMARY_STACK_PCT:
                    if line_key in primary_line_stack_vars:
                        model.Add(primary_line_stack_vars[line_key] == 0)
    
    # Secondary stack exposure - AFTER EACH strategy
    for line_key in lines:
        if line_key in secondary_stack_last_used:
            current_count = secondary_stack_counts.get(line_key, 0)
            # Calculate the exposure percentage: count / total lineups generated
            if num_generated_lineups > 0:
                exposure_pct = current_count / num_generated_lineups
                # Block this line as secondary if exposure is still above threshold
                if exposure_pct >= Config.MAX_SECONDARY_STACK_PCT:
                    if line_key in secondary_line_stack_vars:
                        model.Add(secondary_line_stack_vars[line_key] == 0)
    
    # === UNIQUENESS CONSTRAINT ===
    if used_lineups_sets:
        for prev_lineup_set in used_lineups_sets:
            overlap_count = sum(player_vars[p.id] for p in players if p.id in prev_lineup_set)
            model.Add(overlap_count <= 6)
    
    # === OBJECTIVE ===
    model.Maximize(sum(p.projection * player_vars[p.id] for p in players))
    
    return model, {
        "player_vars": player_vars,
        "primary_line_stack_vars": primary_line_stack_vars,
        "secondary_line_stack_vars": secondary_line_stack_vars
    }

def solve_lineup(model: cp_model.CpModel,
                players: List[Player],
                lines: Dict[str, List[Player]],
                teams: List[str],
                variables: Dict) -> Optional[Lineup]:
    """Solve the lineup optimization model and return the solution if found."""
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    if status == cp_model.INFEASIBLE:
        print("Model is infeasible - no solution exists")
    elif status == cp_model.MODEL_INVALID:
        print("Model is invalid")
    elif status == cp_model.UNKNOWN:
        print("Solver could not determine feasibility")
    
    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return None
    
    # Extract selected players
    selected_players = []
    for p in players:
        if solver.Value(variables["player_vars"][p.id]):
            selected_players.append(p)
    
    # Find primary and secondary stacks as line keys
    primary_stack_line_key = None
    secondary_stack_line_key = None

    # Identify primary stack using the primary stack variables
    if "primary_line_stack_vars" in variables:
        for line_key, var in variables["primary_line_stack_vars"].items():
            if solver.Value(var):
                primary_stack_line_key = line_key
                break
    
    # If primary stack not found via variables, fallback to goalie's team
    if not primary_stack_line_key:
        goalie = [p for p in selected_players if p.is_goalie][0] if any(p.is_goalie for p in selected_players) else None
        goalie_team = goalie.team if goalie else None
        if goalie_team:
            primary_stack_line_key = f"{goalie_team}:team"
        else:
            primary_stack_line_key = None

    # Identify secondary stack by finding 3 C/W from a different line
    if "secondary_line_stack_vars" in variables:
        for line_key, var in variables["secondary_line_stack_vars"].items():
            if solver.Value(var):
                secondary_stack_line_key = line_key
                break
    
    # If secondary stack not found via variables, try to identify it manually
    if not secondary_stack_line_key:
        for line_key, line_players in lines.items():
            if line_key != primary_stack_line_key:  # Different from primary
                c_w_players = [p for p in line_players if ("C" in p.position or "W" in p.position)]
                if len(c_w_players) >= 3:
                    # Check if exactly 3 C/W players from this line are in the selected lineup
                    line_players_in_lineup = [p for p in selected_players if p.id in [lp.id for lp in c_w_players]]
                    if len(line_players_in_lineup) == 3:
                        secondary_stack_line_key = line_key
                        break
    
    # Calculate totals for Lineup constructor
    total_salary = sum(p.salary for p in selected_players)
    total_projection = sum(p.projection for p in selected_players)
    
    return Lineup(selected_players, primary_stack_line_key, secondary_stack_line_key, total_salary, total_projection)

def print_lineup(lineup: Lineup, lineup_num: int):
    """Print a single lineup."""
    print(f"\n=== Lineup {lineup_num} ===")
    print(f"Total Salary: ${lineup.total_salary:,}")
    print(f"Total Projection: {lineup.total_projection:.2f}")
    
    # Get teams and lines for highlighting
    primary_team = lineup.primary_stack.split(":")[0] if lineup.primary_stack else ""
    primary_line = lineup.primary_stack.split(":")[1] if lineup.primary_stack and ":" in lineup.primary_stack else None
    secondary_team = lineup.secondary_stack.split(":")[0] if lineup.secondary_stack else ""
    secondary_line = lineup.secondary_stack.split(":")[1] if lineup.secondary_stack and ":" in lineup.secondary_stack else None
    
    # Identify primary stack players (3 C/W from same line + goalie)
    primary_cw_players = []
    goalie = [p for p in lineup.players if p.is_goalie][0] if any(p.is_goalie for p in lineup.players) else None
    goalie_team = goalie.team if goalie else None
    
    if primary_line and primary_line != "team":
        # Find 3 C/W players from the specific line
        for p in lineup.players:
            if (p.team == primary_team and 
                not p.is_goalie and 
                ("C" in p.position or "W" in p.position) and
                p.roster_order == int(primary_line)):
                primary_cw_players.append(p)
                if len(primary_cw_players) == 3:
                    break
    else:
        # Fallback: get all C/W from goalie's team (should be exactly 3)
        if goalie_team:
            primary_cw_players = [p for p in lineup.players 
                                 if p.team == goalie_team and 
                                 not p.is_goalie and 
                                 ("C" in p.position or "W" in p.position)]
            # Take only the first 3 if more than 3
            primary_cw_players = primary_cw_players[:3]
        else:
            # Fallback to primary_team if goalie not found
            primary_cw_players = [p for p in lineup.players 
                                 if p.team == primary_team and 
                                 not p.is_goalie and 
                                 ("C" in p.position or "W" in p.position)]
            # Take only the first 3 if more than 3
            primary_cw_players = primary_cw_players[:3]
    
    # Identify secondary stack players (3 C/W from different line)
    secondary_cw_players = []
    if secondary_line and secondary_line != "team":
        # Find 3 C/W players from the specific line
        for p in lineup.players:
            if (p.team == secondary_team and 
                not p.is_goalie and 
                ("C" in p.position or "W" in p.position) and
                p.roster_order == int(secondary_line)):
                secondary_cw_players.append(p)
                if len(secondary_cw_players) == 3:
                    break
    else:
        # Fallback: get C/W from secondary team (should be exactly 3)
        secondary_cw_players = [p for p in lineup.players 
                               if p.team == secondary_team and 
                               not p.is_goalie and 
                               ("C" in p.position or "W" in p.position)]
        # Take only the first 3 if more than 3
        secondary_cw_players = secondary_cw_players[:3]
    
    # Get goalie and defensemen
    goalie = [p for p in lineup.players if p.is_goalie][0] if any(p.is_goalie for p in lineup.players) else None
    defensemen = [p for p in lineup.players if "D" in p.position]
    
    # Print in correct order: C, C, W, W, D, D, UTIL, UTIL, G
    print(f"\nLINEUP ORDER (C, C, W, W, D, D, UTIL, UTIL, G):")
    print("-" * 50)
    
    # Get all C, W, and UTIL players
    centers = [p for p in lineup.players if "C" in p.position]
    wings = [p for p in lineup.players if "W" in p.position]
    util_candidates = [p for p in lineup.players if ("C" in p.position or "W" in p.position)]
    
    # Remove players already assigned to C and W slots
    used_players = set()
    
    # C1, C2
    for i, center in enumerate(centers[:2], 1):
        print(f"  C{i}: {center.name} ({center.team}) - ${center.salary:,} - {center.projection:.2f}")
        used_players.add(center.id)
    
    # W1, W2
    for i, wing in enumerate(wings[:2], 1):
        print(f"  W{i}: {wing.name} ({wing.team}) - ${wing.salary:,} - {wing.projection:.2f}")
        used_players.add(wing.id)
    
    # D1, D2
    for i, dman in enumerate(defensemen[:2], 1):
        print(f"  D{i}: {dman.name} ({dman.team}) - ${dman.salary:,} - {dman.projection:.2f}")
    
    # UTIL1, UTIL2 (remaining C or W not already used)
    remaining_util = [p for p in util_candidates if p.id not in used_players]
    for i, util in enumerate(remaining_util[:2], 1):
        print(f"  UTIL{i}: {util.name} ({util.team}) - ${util.salary:,} - {util.projection:.2f}")
    
    # G
    if goalie:
        print(f"  G: {goalie.name} ({goalie.team}) - ${goalie.salary:,} - {goalie.projection:.2f}")
    
    # Print stack breakdown
    print(f"\nPRIMARY STACK: {lineup.primary_stack} (3 C/W + goalie)")
    print("-" * 50)
    for player in primary_cw_players:
        print(f"  {player.position}: {player.name} - ${player.salary:,} - {player.projection:.2f}")
    if goalie:
        print(f"  G: {goalie.name} - ${goalie.salary:,} - {goalie.projection:.2f}")
    
    if secondary_cw_players:
        print(f"\nSECONDARY STACK: {lineup.secondary_stack} (3 C/W)")
        print("-" * 50)
        for player in secondary_cw_players:
            print(f"  {player.position}: {player.name} - ${player.salary:,} - {player.projection:.2f}")
    
    print(f"\nSTACK BREAKDOWN:")
    print(f"  Primary Stack: {len(primary_cw_players)} C/W + 1 goalie = {len(primary_cw_players) + 1} players")
    print(f"  Secondary Stack: {len(secondary_cw_players)} C/W = {len(secondary_cw_players)} players")
    print(f"  Defensemen: {len(defensemen)} players")
    print(f"  Total: {len(lineup.players)} players")

def export_lineups(lineups: List[Lineup], output_path: str):
    """Export lineups to CSV in the requested format."""
    if not lineups:
        print("No lineups to export")
        return
    
    # Slot order: C, C, W, W, D, D, UTIL, UTIL, G
    slot_names = ["C1", "C2", "W1", "W2", "D1", "D2", "UTIL1", "UTIL2", "G"]
    data = []
    
    for i, lineup in enumerate(lineups, 1):
        # Assign players to slots
        centers = [p for p in lineup.players if "C" in p.position]
        wings = [p for p in lineup.players if "W" in p.position]
        defensemen = [p for p in lineup.players if "D" in p.position]
        goalies = [p for p in lineup.players if p.is_goalie]
        
        # Sort by projection for better assignment
        centers.sort(key=lambda p: p.projection, reverse=True)
        wings.sort(key=lambda p: p.projection, reverse=True)
        defensemen.sort(key=lambda p: p.projection, reverse=True)
        goalies.sort(key=lambda p: p.projection, reverse=True)
        
        used_ids = set()
        row = {"Lineup": i}
        
        # C1, C2
        if len(centers) > 0:
            row["C1"] = centers[0].id + ": " + centers[0].name
            used_ids.add(centers[0].id)
        else:
            row["C1"] = ""
            
        if len(centers) > 1:
            row["C2"] = centers[1].id + ": " + centers[1].name
            used_ids.add(centers[1].id)
        else:
            row["C2"] = ""
            
        # W1, W2
        if len(wings) > 0:
            row["W1"] = wings[0].id + ": " + wings[0].name
            used_ids.add(wings[0].id)
        else:
            row["W1"] = ""
            
        if len(wings) > 1:
            row["W2"] = wings[1].id + ": " + wings[1].name
            used_ids.add(wings[1].id)
        else:
            row["W2"] = ""
            
        # D1, D2
        if len(defensemen) > 0:
            row["D1"] = defensemen[0].id + ": " + defensemen[0].name
            used_ids.add(defensemen[0].id)
        else:
            row["D1"] = ""
            
        if len(defensemen) > 1:
            row["D2"] = defensemen[1].id + ": " + defensemen[1].name
            used_ids.add(defensemen[1].id)
        else:
            row["D2"] = ""
            
        # UTIL1, UTIL2 (remaining C or W not already used)
        util_candidates = [p for p in lineup.players if ("C" in p.position or "W" in p.position) and p.id not in used_ids]
        util_candidates.sort(key=lambda p: p.projection, reverse=True)
        
        if len(util_candidates) > 0:
            row["UTIL1"] = util_candidates[0].id + ": " + util_candidates[0].name
            used_ids.add(util_candidates[0].id)
        else:
            row["UTIL1"] = ""
            
        if len(util_candidates) > 1:
            row["UTIL2"] = util_candidates[1].id + ": " + util_candidates[1].name
            used_ids.add(util_candidates[1].id)
        else:
            row["UTIL2"] = ""
            
        # G
        if len(goalies) > 0:
            row["G"] = goalies[0].id + ": " + goalies[0].name
        else:
            row["G"] = ""
            
        # Summary columns
        row["Primary_Stack"] = lineup.primary_stack
        row["Secondary_Stack"] = lineup.secondary_stack
        row["Total_Projection"] = lineup.total_projection
        row["Total_Salary"] = lineup.total_salary
        row["Total Ceiling"] = sum(p.ceiling for p in lineup.players)
        row["Total Shots"] = sum(p.shatt for p in lineup.players)
        product_ownership = 1.0
        for p in lineup.players:
            product_ownership *= p.projected_ownership if p.projected_ownership else 1.0
        row["Product Ownership"] = product_ownership
        data.append(row)
    # Create DataFrame
    columns = ["Lineup"] + slot_names + [
        "Primary_Stack", "Secondary_Stack", "Total_Projection", "Total_Salary",
        "Total Ceiling", "Total Shots", "Product Ownership"
    ]
    df = pd.DataFrame(data, columns=columns)
    # Add rankings
    df["Projection Rank"] = df["Total_Projection"].rank(ascending=False, method="min")
    df["Ceiling Rank"] = df["Total Ceiling"].rank(ascending=False, method="min")
    df["Shots Rank"] = df["Total Shots"].rank(ascending=False, method="min")
    df["Ownership Rank"] = df["Product Ownership"].rank(ascending=True, method="min")
    df["Average"] = df[["Projection Rank", "Ceiling Rank", "Shots Rank", "Ownership Rank"]].mean(axis=1)
    # Add standardized columns
    for col, zcol, invert in [
        ("Total_Projection", "Projection Z", False),
        ("Total Ceiling", "Ceiling Z", False),
        ("Total Shots", "Shots Z", False),
        ("Product Ownership", "Ownership Z", True)
    ]:
        mean = df[col].mean()
        std = df[col].std(ddof=0)
        if std == 0:
            df[zcol] = 0.0
        else:
            z = (df[col] - mean) / std
            if invert:
                z = -z
            df[zcol] = z
    # Sort by average rank
    df = df.sort_values("Average", ascending=True).reset_index(drop=True)
    # Reorder columns
    columns += ["Projection Rank", "Ceiling Rank", "Shots Rank", "Ownership Rank", "Average",
                "Projection Z", "Ceiling Z", "Shots Z", "Ownership Z"]
    df = df[columns]
    df.to_csv(output_path, index=False)
    print(f"Exported {len(lineups)} lineups to {output_path}")

def main():
    """Main function."""
    print("NHL DFS Lineup Optimizer")
    print("=" * 50)
    
    # Print configuration
    print(f"Configuration:")
    print(f"  Allow Goalie vs Opponent: {Config.ALLOW_GOALIE_VS_OPPONENT}")
    print(f"  Max Primary Stack Exposure: {Config.MAX_PRIMARY_STACK_PCT*100:.1f}%")
    print(f"  Max Secondary Stack Exposure: {Config.MAX_SECONDARY_STACK_PCT*100:.1f}%")
    print()
    
    # Load and process data
    print("Loading data...")
    df = load_data(Config.DATA_FILE)
    df = filter_players(df)
    players = create_players(df)
    
    # Get lines
    lines = get_lines(players)
    if len(lines) < 2:
        print("ERROR: Need at least 2 valid lines to create lineups")
        return
    
    teams = list(set(p.team for p in players))
    
    # Debug: Check goalie availability by team
    goalies_by_team = {}
    for p in players:
        if p.is_goalie:
            if p.team not in goalies_by_team:
                goalies_by_team[p.team] = []
            goalies_by_team[p.team].append(p)
    
    print(f"Goalie availability by team:")
    for team in sorted(teams):
        goalie_count = len(goalies_by_team.get(team, []))
        print(f"  {team}: {goalie_count} goalies")
    
    # Check which lines can be primary stacks (have goalies)
    primary_capable_lines = []
    for line_key in lines:
        team = line_key.split(":")[0]
        if team in goalies_by_team and len(goalies_by_team[team]) > 0:
            primary_capable_lines.append(line_key)
    
    print(f"Lines that can be primary stacks: {len(primary_capable_lines)} out of {len(lines)}")
    
    # Initialize tracking variables
    generated_lineups = []
    used_lineups_sets = []
    primary_stack_counts = {}
    secondary_stack_counts = {}
    # Track when each line was last used for AFTER EACH strategy
    primary_stack_last_used = {}
    secondary_stack_last_used = {}
    recent_primary_teams = {team: 0 for team in teams}
    recent_secondary_teams = {team: 0 for team in teams}
    attempt = 0
    
    # Generate lineups
    while (len(generated_lineups) < Config.NUM_LINEUPS and 
           attempt < Config.MAX_ATTEMPTS):
        attempt += 1
        

        
        # Create and solve model
        model, variables = create_lineup_model(
            players, lines, teams, primary_stack_counts, secondary_stack_counts,
            primary_stack_last_used, secondary_stack_last_used,
            recent_primary_teams, recent_secondary_teams, used_lineups_sets, len(generated_lineups)
        )
        
        lineup = solve_lineup(model, players, lines, teams, variables)
        if not lineup:
            continue
        
        # Update tracking variables AFTER generating the lineup
        current_lineup_number = len(generated_lineups) + 1
        
        if lineup.primary_stack:
            # Track primary stack usage
            primary_stack_counts[lineup.primary_stack] = primary_stack_counts.get(lineup.primary_stack, 0) + 1
            # Track when this line was last used as primary
            primary_stack_last_used[lineup.primary_stack] = current_lineup_number
        
        # For secondary, use the secondary_stack (which is a line key)
        if lineup.secondary_stack:
            secondary_stack_counts[lineup.secondary_stack] = secondary_stack_counts.get(lineup.secondary_stack, 0) + 1
            # Track when this line was last used as secondary
            secondary_stack_last_used[lineup.secondary_stack] = current_lineup_number
        
        # Update recent teams tracking
        primary_team = lineup.primary_stack.split(":")[0] if lineup.primary_stack else ""
        secondary_team = lineup.secondary_stack.split(":")[0] if lineup.secondary_stack else ""
        
        for team in teams:
            if team == primary_team:
                recent_primary_teams[team] += 1
            else:
                recent_primary_teams[team] = max(0, recent_primary_teams[team] - 1)
            if team == secondary_team:
                recent_secondary_teams[team] += 1
            else:
                recent_secondary_teams[team] = max(0, recent_secondary_teams[team] - 1)
        
        generated_lineups.append(lineup)
        used_lineups_sets.append(set(p.id for p in lineup.players))
        

        
        # Print lineup
        print_lineup(lineup, len(generated_lineups))
    
    print(f"\nGenerated {len(generated_lineups)} lineups in {attempt} attempts")
    
    if generated_lineups:
        # Export to CSV
        export_lineups(generated_lineups, "/Users/adamsardinha/Desktop/nhl_lineups.csv")
        
        # Print final exposure summary
        print(f"\nFinal Exposure Summary:")
        print("Primary Stacks:")
        for stack, count in sorted(primary_stack_counts.items(), key=lambda x: x[1], reverse=True):
            pct = count / len(generated_lineups) * 100
            print(f"  {stack}: {count} ({pct:.1f}%)")
        print("Secondary Stacks:")
        for stack, count in sorted(secondary_stack_counts.items(), key=lambda x: x[1], reverse=True):
            pct = count / len(generated_lineups) * 100
            print(f"  {stack}: {count} ({pct:.1f}%)")
    else:
        print("\nNo lineups were generated. This could be due to:")
        print("1. Too restrictive exposure limits")
        print("2. Conflicting constraints (goalie enforcement + diversity)")
        print("3. Insufficient player pool")
        print("4. Uniqueness constraints making the model infeasible")
        print("\nPlease check your configuration settings and try again.")

if __name__ == "__main__":
    main() 