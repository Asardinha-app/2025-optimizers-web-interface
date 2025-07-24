"""
NFL Daily Fantasy Sports Lineup Optimizer
This script generates optimized lineups for NFL DFS contests using constraint programming.
"""

from typing import List, Dict, Set, Tuple, Optional
import pandas as pd
from ortools.sat.python import cp_model
import os
from dataclasses import dataclass
import numpy as np
import copy

# Import configuration files
from qb_stacks_config import get_all_qb_stacks, validate_all_qb_stacks_against_players
from player_groups_config import get_player_groups, validate_all_groups_against_players

# ===== Configuration =====
class Config:
    # File paths
    DATA_FILE = "/Users/adamsardinha/Desktop/NFL_FD.csv"
    
    # Lineup generation settings
    NUM_LINEUPS_TO_GENERATE = 300
    MAX_SALARY = 60000  # NFL salary cap is $60,000
    MIN_SALARY = 59500  # Lowered minimum salary for more flexibility
    MAX_ATTEMPTS = 1000
    
    # Roster settings
    SLOTS = {
        "QB": 1,
        "RB": 2,
        "WR": 3,
        "TE": 1,
        "FLEX": 1,  # Can only be RB
        "D": 1  # Defense position
    }
    
    # RB team limit settings
    RB_TEAM_LIMIT = {
        "enabled": True,
        "max_rbs_per_team": 1,
        "excluded_teams": ["DET"]  # Teams where multiple RBs are allowed
    }
    
    # Secondary stack settings
    ENABLE_RB_OPP_STACK = True  # Disable secondary stacks to reduce constraints
    ENABLE_WR_WR_OPP_STACK = True  # WR + WR from opponent teams
    ENABLE_RB_DEF_SAME_TEAM = True  # Disable secondary stacks to reduce constraints
    
    # Smart Randomness settings
    ENABLE_SMART_RANDOMNESS = True  # Disable smart randomness to reduce complexity
    DISTRIBUTION_TYPE = "lognormal"  # "normal" or "lognormal"
    RANDOMNESS_SEED = None  # Set to an integer for reproducible results
    RANDOMNESS_FREQUENCY = "per_lineup"  # "per_lineup" or "per_session" (once at start)
    
    # Filtering settings
    ENABLE_PERCENTILE_FILTER = True  # Enable percentile-based filtering
    PERCENTILE_THRESHOLD = 75  # Remove RB/TE/WR below this percentile
    MIN_TARGETS_FILTER = 2.5  # Remove WR/TE with targets less than this
    ENABLE_TARGETS_FILTER = True  # Enable targets filtering
    
    # Premium RB settings
    ENABLE_PREMIUM_RB_FILTER = True  # Enable premium RB filtering
    PREMIUM_RB_RUSH_PERCENTILE = 85  # Minimum rush attempts percentile for premium RBs
    PREMIUM_RB_SALARY_PERCENTILE = 82.5  # Minimum salary percentile for premium RBs
    MIN_PREMIUM_RBS = 2  # Minimum number of premium RBs required in lineup
    
    # Ownership settings
    MIN_LOW_OWNERSHIP_PLAYERS = 1  # Minimum number of players with ownership <= 5%
    LOW_OWNERSHIP_THRESHOLD = 5.0  # Ownership threshold for low ownership players
    
    ENABLE_OWNERSHIP_SUM_CONSTRAINTS = True  # Enable min/max total ownership constraints
    MIN_TOTAL_OWNERSHIP = 90.0  # Minimum total ownership percentage for lineup
    MAX_TOTAL_OWNERSHIP = 120.0  # Maximum total ownership percentage for lineup

@dataclass
class Player:
    id: int
    name: str
    positions: List[str]
    team: str
    opponent: str
    salary: int
    projection: float
    is_qb: bool
    ownership: float
    only_in_stack: bool
    rush_attempts: float = 0.0
    targets: float = 0.0
    ceiling: float = 0.0
    current_projection: float = None
    projection_floor: float = None  # 25th percentile projection
    projection_ceil: float = None  # 85th percentile projection
    std_dev: float = None  # Calculated standard deviation

    def __post_init__(self):
        self.current_projection = self.projection

@dataclass
class Lineup:
    players: List[Dict]
    primary_stack: str
    secondary_stack: str

class SmartRandomness:
    """Applies smart randomness to player projections based on exposure."""
    
    def __init__(self, players: List[Player], distribution_type: str = "lognormal", seed: Optional[int] = None):
        self.players = {p.id: p for p in players}
        self.distribution_type = distribution_type
        self.rng = None
        self.initialize_rng(seed)
    
    def initialize_rng(self, seed: Optional[int] = None):
        """Initialize the random number generator."""
        import random
        self.rng = random.Random(seed)
    
    def apply_randomness(self, player_id: int, current_projection: float) -> float:
        """Applies smart randomness to a player's projection using their floor/median/ceiling range."""
        if not Config.ENABLE_SMART_RANDOMNESS:
            return current_projection
        
        if self.rng is None:
            raise ValueError("Random number generator not initialized.")
        
        player = self.players[player_id]
        
        # If player doesn't have floor/ceiling data, return original projection
        if (player.projection_floor is None or player.projection_ceil is None or 
            player.projection_floor == player.projection_ceil):
            return current_projection
        
        # Use the player's actual projection range (floor, median, ceiling)
        floor = player.projection_floor
        median = current_projection  # This is the median/base projection
        ceiling = player.projection_ceil
        
        # Generate a random value between 0 and 1
        random_value = self.rng.random()
        
        # Use the random value to interpolate within the player's range
        if random_value < 0.33:
            # Lower third: interpolate between floor and median
            weight = random_value / 0.33
            random_projection = floor + (median - floor) * weight
        elif random_value < 0.67:
            # Middle third: interpolate between median and ceiling
            weight = (random_value - 0.33) / 0.34
            random_projection = median + (ceiling - median) * weight
        else:
            # Upper third: interpolate between median and ceiling (slightly more weight to ceiling)
            weight = (random_value - 0.67) / 0.33
            random_projection = median + (ceiling - median) * weight
        
        return round(random_projection, 2)

def load_and_clean_data(file_path: str) -> Tuple[pd.DataFrame, Set[int]]:
    """Load and clean the player data from CSV file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data file not found: {file_path}")
    
    df = pd.read_csv(file_path)
    
    # Data validation: Ensure all player IDs are unique
    if df['Id'].duplicated().any():
        num_duplicates = df['Id'].duplicated().sum()
        print(f"Warning: Found {num_duplicates} duplicate player IDs in input data. Removing duplicates and keeping the first occurrence.")
        df = df.drop_duplicates(subset=['Id'], keep='first')
    
    # Convert columns to appropriate types
    numeric_columns = ["FPPG", "Salary"]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    df["Position"] = df["Position"].astype(str)
    
    # Return empty set for ro8_9_ids since we're not using Roster Order
    ro8_9_ids = set()
    
    return df, ro8_9_ids

def create_player_objects(df: pd.DataFrame) -> List[Player]:
    """Convert DataFrame rows to Player objects."""
    players = []
    
    for _, row in df.iterrows():
        positions = row["Position"].split("/")
        name = row["Player ID + Player Name"]
        projection = round(row["FPPG"], 2)
        
        # Use Projected Ownership directly from the CSV file
        ownership = float(row.get("Projected Ownership", 0))
        
        # Get OIS flag, default to False if not present
        only_in_stack = row.get("OIS", "").upper() == "Y"
        
        # Get rush attempts for RBs, default to 0 if not present
        rush_attempts = float(row.get("Rush", 0)) if "Rush" in row and pd.notna(row.get("Rush")) else 0.0
        
        # Get targets for WR/TE/RB, default to 0 if not present
        targets = float(row.get("Targets", 0)) if "Targets" in row and pd.notna(row.get("Targets")) else 0.0
        
        # Get ceiling projection, default to projection if not present
        ceiling = float(row.get("Projection Ceil", projection)) if "Projection Ceil" in row and pd.notna(row.get("Projection Ceil")) else projection
        
        # Get projection data for smart randomness
        projection_floor = row.get("Projection Floor", projection)
        projection_ceil = row.get("Projection Ceil", projection)
        
        # Calculate standard deviation if we have floor and ceil data
        std_dev = None
        if pd.notna(projection_floor) and pd.notna(projection_ceil) and projection_floor != projection_ceil:
            # Ensure floor and ceil are positive for lognormal calculation
            if projection_floor > 0 and projection_ceil > 0:
                # Calculate std_dev using the same method as other optimizers
                if Config.DISTRIBUTION_TYPE == "normal":
                    std_dev = (projection_ceil - projection) / 1.0364
                else:  # lognormal
                    log_median = np.log(projection)
                    log_floor = np.log(projection_floor)
                    log_ceil = np.log(projection_ceil)
                    std_dev = (log_ceil - log_median) / 1.0364
                std_dev = max(std_dev, 0.1)  # Ensure minimum std_dev
        
        players.append(Player(
            id=row["Id"],
            name=name,
            positions=positions,
            team=row["Team"],
            opponent=row["Opponent"],
            salary=int(row["Salary"]),
            projection=projection,
            is_qb="QB" in positions,
            ownership=ownership,
            only_in_stack=only_in_stack,
            rush_attempts=rush_attempts,
            targets=targets,
            ceiling=ceiling,
            projection_floor=projection_floor,
            projection_ceil=projection_ceil,
            std_dev=std_dev
        ))
    return players

def add_skill_position_team_limit(model: cp_model.CpModel,
                                players: List[Player],
                                player_vars: Dict[int, cp_model.IntVar]) -> None:
    """Add constraint to limit total players from same team to 4 when QB is used, 2 otherwise."""
    # Group players by team
    players_by_team = {}
    for p in players:
        if p.team not in players_by_team:
            players_by_team[p.team] = {"qb": [], "all": []}
        if "QB" in p.positions:
            players_by_team[p.team]["qb"].append(p)
        players_by_team[p.team]["all"].append(p)  # Include all players (including DEF)
    
    # For each team
    for team, team_players in players_by_team.items():
        if not team_players["qb"]:
            continue
            
        # Create a variable that is true if QB is in lineup
        qb_in_lineup = model.NewBoolVar(f"qb_in_lineup_{team}")
        model.AddBoolOr([player_vars[qb.id] for qb in team_players["qb"]]).OnlyEnforceIf(qb_in_lineup)
        model.AddBoolAnd([player_vars[qb.id].Not() for qb in team_players["qb"]]).OnlyEnforceIf(qb_in_lineup.Not())
        
        # Sum of ALL players from this team (including DEF)
        team_sum = sum(player_vars[p.id] for p in team_players["all"])
        
        # If QB is in lineup, can have up to 4 total players (including DEF)
        # If QB is not in lineup, limit to 2 total players
        model.Add(team_sum <= 4).OnlyEnforceIf(qb_in_lineup)
        model.Add(team_sum <= 2).OnlyEnforceIf(qb_in_lineup.Not())

def add_qb_stack_constraint(model: cp_model.CpModel,
                          players: List[Player],
                          player_vars: Dict[int, cp_model.IntVar]) -> None:
    """Add constraint to require between 1 and 2 skill position players from QB's team and limit opponent team."""
    # Group players by team
    players_by_team = {}
    for p in players:
        if p.team not in players_by_team:
            players_by_team[p.team] = {"qb": [], "skill": [], "rbs": []}
        if "QB" in p.positions:
            players_by_team[p.team]["qb"].append(p)
        elif any(pos in ["RB", "WR", "TE"] for pos in p.positions):
            players_by_team[p.team]["skill"].append(p)
        if "RB" in p.positions:
            players_by_team[p.team]["rbs"].append(p)
    
    # For each team with a QB
    for team, team_players in players_by_team.items():
        if not team_players["qb"] or not team_players["skill"]:
            continue
            
        # Create a variable that is true if QB is in lineup
        qb_in_lineup = model.NewBoolVar(f"qb_in_lineup_{team}")
        model.AddBoolOr([player_vars[qb.id] for qb in team_players["qb"]]).OnlyEnforceIf(qb_in_lineup)
        model.AddBoolAnd([player_vars[qb.id].Not() for qb in team_players["qb"]]).OnlyEnforceIf(qb_in_lineup.Not())
        
        # Find the RBs with highest targets from this team
        if team_players["rbs"]:
            # Find the maximum targets among RBs on this team
            max_targets = max(rb.targets for rb in team_players["rbs"])
            # Get all RBs that have the maximum targets (allows ties)
            top_rbs = [rb for rb in team_players["rbs"] if rb.targets == max_targets]
            other_rbs = [rb for rb in team_players["rbs"] if rb.targets < max_targets]
            
            # If QB is in lineup, only allow RBs with max targets to be used
            for other_rb in other_rbs:
                model.Add(player_vars[other_rb.id] == 0).OnlyEnforceIf(qb_in_lineup)
        
        # Sum of WR/TE players from this team (for base stacking)
        wr_te_sum = sum(player_vars[p.id] for p in team_players["skill"] 
                       if any(pos in ["WR", "TE"] for pos in p.positions))
        
        # Sum of all skill players from this team (for total limit)
        skill_sum = sum(player_vars[p.id] for p in team_players["skill"])
        
        # If QB is in lineup, require at least 1 WR or TE
        model.Add(wr_te_sum >= 1).OnlyEnforceIf(qb_in_lineup)
        model.Add(skill_sum <= 2).OnlyEnforceIf(qb_in_lineup)
        # If QB is not in lineup, limit skill players to avoid partial stacks
        model.Add(skill_sum <= 2).OnlyEnforceIf(qb_in_lineup.Not())
        
        # Find opponent team's skill players
        opponent_skill_players = []
        for p in players:
            if (p.team == team_players["qb"][0].opponent and  # Check if player is from opponent team
                any(pos in ["RB", "WR", "TE"] for pos in p.positions)):  # Check if player is a skill position
                opponent_skill_players.append(p)
        
        if opponent_skill_players:
            # Sum of opponent skill players
            opponent_skill_sum = sum(player_vars[p.id] for p in opponent_skill_players)
            
            # If QB is in lineup, limit opponent skill players to 2
            model.Add(opponent_skill_sum <= 2).OnlyEnforceIf(qb_in_lineup)

def add_rb_team_limit(model: cp_model.CpModel,
                     players: List[Player],
                     player_vars: Dict[int, cp_model.IntVar]) -> None:
    """Add constraint to limit RBs from same team, with exceptions."""
    if not Config.RB_TEAM_LIMIT["enabled"]:
        return
        
    # Group RBs by team
    rbs_by_team = {}
    for p in players:
        if "RB" in p.positions and p.team not in Config.RB_TEAM_LIMIT["excluded_teams"]:
            if p.team not in rbs_by_team:
                rbs_by_team[p.team] = []
            rbs_by_team[p.team].append(p)
    
    # For each team (except excluded ones), limit number of RBs
    for team, team_rbs in rbs_by_team.items():
        if len(team_rbs) > 1:  # Only add constraint if team has multiple RBs
            rb_sum = sum(player_vars[p.id] for p in team_rbs)
            model.Add(rb_sum <= Config.RB_TEAM_LIMIT["max_rbs_per_team"])

def add_ois_constraints(model: cp_model.CpModel,
                       players: List[Player],
                       player_vars: Dict[int, cp_model.IntVar]) -> None:
    """Add constraints for players that can only be used in stacks with their QB."""
    # Group players by team
    players_by_team = {}
    for p in players:
        if p.team not in players_by_team:
            players_by_team[p.team] = {"qb": [], "ois": []}
        if "QB" in p.positions:
            players_by_team[p.team]["qb"].append(p)
        # Only apply OIS to WR and TE positions
        elif p.only_in_stack and any(pos in ["WR", "TE"] for pos in p.positions):
            players_by_team[p.team]["ois"].append(p)
    
    # For each team
    for team, team_players in players_by_team.items():
        if not team_players["qb"] or not team_players["ois"]:
            continue
            
        # Create a variable that is true if QB is in lineup
        qb_in_lineup = model.NewBoolVar(f"qb_in_lineup_{team}")
        model.AddBoolOr([player_vars[qb.id] for qb in team_players["qb"]]).OnlyEnforceIf(qb_in_lineup)
        model.AddBoolAnd([player_vars[qb.id].Not() for qb in team_players["qb"]]).OnlyEnforceIf(qb_in_lineup.Not())
        
        # For each OIS player, they can only be used if QB is in lineup
        for ois_player in team_players["ois"]:
            model.AddBoolOr([player_vars[ois_player.id].Not(), qb_in_lineup])

def add_player_group_constraints(model: cp_model.CpModel,
                               players: List[Player],
                               player_vars: Dict[int, cp_model.IntVar]) -> None:
    """Add constraints for player groups defined in the config file."""
    groups = get_player_groups()
    
    for group_config in groups:
        group_name = group_config['group_name']
        
        if group_config['type'] == 'QB_RB_Restriction':
            # Handle QB-RB same team restriction
            allowed_rbs = set(rb.strip() for rb in group_config.get('allowed_pairs', []))
            
            # Find all QBs
            qbs = [p for p in players if "QB" in p.positions]
            # Find all RBs
            rbs = [p for p in players if "RB" in p.positions]
            
            # For each QB
            for qb in qbs:
                # Find RBs from same team
                same_team_rbs = [rb for rb in rbs if rb.team == qb.team]
                
                for rb in same_team_rbs:
                    # Clean up player name for comparison
                    rb_name = rb.name.split(":")[-1].strip()
                    
                    # If RB is not in allowed pairs list, prevent QB-RB pairing
                    if rb_name not in allowed_rbs:
                        model.AddBoolOr([
                            player_vars[qb.id].Not(),  # QB not in lineup
                            player_vars[rb.id].Not()   # RB not in lineup
                        ])
            continue
        
        # Find players that match the group criteria (by name or position)
        group_players = []
        if group_config.get('players'):
            for p in players:
                if p.name.split(":")[-1].strip() in group_config['players']:
                    # Check team filter if specified
                    if group_config.get('team') and p.team != group_config['team']:
                        continue
                    # Check position filter if specified
                    if group_config.get('position') and group_config['position'] not in p.positions:
                        continue
                    group_players.append(p)
        elif group_config.get('position'):
            for p in players:
                if group_config['position'] in p.positions:
                    # Check team filter if specified
                    if group_config.get('team') and p.team != group_config['team']:
                        continue
                    group_players.append(p)
        
        if not group_players:
            continue
            
        # Sum of players from this group in the lineup
        group_sum = sum(player_vars[p.id] for p in group_players)
        
        # Apply min/max constraints based on group type
        if group_config['type'] == 'Min':
            model.Add(group_sum >= group_config['min_players'])
        elif group_config['type'] == 'Max':
            model.Add(group_sum <= group_config['max_players'])

def add_secondary_stack_constraints(model, players, player_vars, assign):
    """Add secondary stack constraints."""
    # Identify all QBs
    qbs = [p for p in players if "QB" in p.positions]
    qb_vars = {qb.id: player_vars[qb.id] for qb in qbs}

    # Map team to skill players (WR, RB, TE)
    team_skill_players = {}
    for p in players:
        if any(pos in ["WR", "RB", "TE"] for pos in p.positions):
            team_skill_players.setdefault(p.team, []).append(p)

    # Create variables to track which secondary stack type is used
    secondary_stack_vars = {}
    
    # Secondary Stack 1: RB + opponent WR (exactly one such pair, not in primary stack)
    if Config.ENABLE_RB_OPP_STACK:
        rbs = [p for p in players if "RB" in p.positions]
        rb_opp_pairs = []
        for rb in rbs:
            opp_team = rb.opponent
            opp_wrs = [p for p in players if p.team == opp_team and "WR" in p.positions]
            for wr in opp_wrs:
                rb_opp_pairs.append((rb, wr))
        if rb_opp_pairs:
            pair_vars = []
            for rb, wr in rb_opp_pairs:
                pair_var = model.NewBoolVar(f"rb_opp_pair_{rb.id}_{wr.id}")
                # For each possible QB, if that QB is in the lineup, neither rb nor wr can be in that QB's primary stack
                for qb in qbs:
                    qb_team = qb.team
                    primary_stack_ids = [p.id for p in team_skill_players.get(qb_team, [])]
                    if rb.id in primary_stack_ids or wr.id in primary_stack_ids:
                        model.Add(pair_var == 0).OnlyEnforceIf(qb_vars[qb.id])
                # Normal pair logic
                model.AddBoolAnd([player_vars[rb.id], player_vars[wr.id]]).OnlyEnforceIf(pair_var)
                model.AddBoolOr([player_vars[rb.id].Not(), player_vars[wr.id].Not()]).OnlyEnforceIf(pair_var.Not())
                pair_vars.append(pair_var)
            if pair_vars:
                secondary_stack_vars['rb_opp'] = pair_vars

    # Secondary Stack 2: WR + WR from opponent teams (exactly one such pair, not in primary stack)
    if Config.ENABLE_WR_WR_OPP_STACK:
        wrs = [p for p in players if "WR" in p.positions]
        wr_wr_opp_pairs = []
        for wr1 in wrs:
            # Find WRs from opponent teams
            opp_wrs = [p for p in players if p.team == wr1.opponent and "WR" in p.positions]
            for wr2 in opp_wrs:
                # Avoid duplicate pairs (wr1, wr2) and (wr2, wr1)
                if wr1.id < wr2.id:
                    wr_wr_opp_pairs.append((wr1, wr2))
        if wr_wr_opp_pairs:
            pair_vars = []
            for wr1, wr2 in wr_wr_opp_pairs:
                pair_var = model.NewBoolVar(f"wr_wr_opp_pair_{wr1.id}_{wr2.id}")
                # For each possible QB, if that QB is in the lineup, neither wr1 nor wr2 can be in that QB's primary stack
                for qb in qbs:
                    qb_team = qb.team
                    primary_stack_ids = [p.id for p in team_skill_players.get(qb_team, [])]
                    if wr1.id in primary_stack_ids or wr2.id in primary_stack_ids:
                        model.Add(pair_var == 0).OnlyEnforceIf(qb_vars[qb.id])
                # Normal pair logic
                model.AddBoolAnd([player_vars[wr1.id], player_vars[wr2.id]]).OnlyEnforceIf(pair_var)
                model.AddBoolOr([player_vars[wr1.id].Not(), player_vars[wr2.id].Not()]).OnlyEnforceIf(pair_var.Not())
                pair_vars.append(pair_var)
            if pair_vars:
                secondary_stack_vars['wr_wr_opp'] = pair_vars

    # Secondary Stack 3: RB + DEF from same team (exactly one such pair, not in primary stack)
    if Config.ENABLE_RB_DEF_SAME_TEAM:
        rbs = [p for p in players if "RB" in p.positions]
        defenses = [p for p in players if "D" in p.positions or "DST" in p.positions]
        rb_def_pairs = []
        for rb in rbs:
            same_team_def = [d for d in defenses if d.team == rb.team]
            for d in same_team_def:
                rb_def_pairs.append((rb, d))
        if rb_def_pairs:
            pair_vars = []
            for rb, d in rb_def_pairs:
                pair_var = model.NewBoolVar(f"rb_def_pair_{rb.id}_{d.id}")
                # For each possible QB, if that QB is in the lineup, rb cannot be in that QB's primary stack
                for qb in qbs:
                    qb_team = qb.team
                    primary_stack_ids = [p.id for p in team_skill_players.get(qb_team, [])]
                    if rb.id in primary_stack_ids:
                        model.Add(pair_var == 0).OnlyEnforceIf(qb_vars[qb.id])
                # Normal pair logic
                model.AddBoolAnd([player_vars[rb.id], player_vars[d.id]]).OnlyEnforceIf(pair_var)
                model.AddBoolOr([player_vars[rb.id].Not(), player_vars[d.id].Not()]).OnlyEnforceIf(pair_var.Not())
                pair_vars.append(pair_var)
            if pair_vars:
                secondary_stack_vars['rb_def'] = pair_vars

    # Ensure exactly one secondary stack type is used (if any are enabled)
    if secondary_stack_vars:
        # Create variables for each stack type being used
        stack_type_vars = {}
        for stack_type, pair_vars in secondary_stack_vars.items():
            stack_type_var = model.NewBoolVar(f"use_{stack_type}_stack")
            # If this stack type is used, exactly one pair from this type must be used
            model.Add(sum(pair_vars) == 1).OnlyEnforceIf(stack_type_var)
            model.Add(sum(pair_vars) == 0).OnlyEnforceIf(stack_type_var.Not())
            stack_type_vars[stack_type] = stack_type_var
        
        # Ensure exactly one stack type is used
        model.Add(sum(stack_type_vars.values()) == 1)

def add_filtering_constraints(model: cp_model.CpModel,
                            players: List[Player],
                            player_vars: Dict[int, cp_model.IntVar]) -> None:
    """Add filtering constraints for percentile-based filtering and targets."""
    
    # Team-relative percentile-based filtering for RB/TE/WR
    if Config.ENABLE_PERCENTILE_FILTER:
        # Group players by team
        players_by_team = {}
        for p in players:
            if any(pos in ["RB", "TE", "WR"] for pos in p.positions):
                if p.team not in players_by_team:
                    players_by_team[p.team] = []
                players_by_team[p.team].append(p)
        
        # For each team, calculate team-relative percentile threshold
        for team, team_players in players_by_team.items():
            if len(team_players) > 1:  # Only apply if team has multiple skill players
                # Calculate projections for this team's skill players
                team_projections = [p.projection for p in team_players]
                team_projections.sort()
                
                # Calculate the threshold value at the specified percentile for this team
                threshold_index = int(len(team_projections) * Config.PERCENTILE_THRESHOLD / 100)
                if threshold_index < len(team_projections):
                    team_threshold_value = team_projections[threshold_index]
                    
                    # Remove players from this team below the team's threshold
                    for p in team_players:
                        if p.projection < team_threshold_value:
                            model.Add(player_vars[p.id] == 0)
    
    # Targets filtering for WR/TE
    if Config.ENABLE_TARGETS_FILTER:
        for p in players:
            if any(pos in ["WR", "TE"] for pos in p.positions):
                if p.targets < Config.MIN_TARGETS_FILTER:
                    model.Add(player_vars[p.id] == 0)
    
    # Premium RB filtering
    if Config.ENABLE_PREMIUM_RB_FILTER:
        # Get all RBs
        rb_players = [p for p in players if "RB" in p.positions]
        
        if rb_players:
            # Calculate rush attempts percentiles
            rush_attempts = [p.rush_attempts for p in rb_players]
            rush_attempts.sort()
            rush_threshold_index = int(len(rush_attempts) * Config.PREMIUM_RB_RUSH_PERCENTILE / 100)
            rush_threshold = rush_attempts[rush_threshold_index] if rush_threshold_index < len(rush_attempts) else 0
            
            # Calculate salary percentiles
            salaries = [p.salary for p in rb_players]
            salaries.sort()
            salary_threshold_index = int(len(salaries) * Config.PREMIUM_RB_SALARY_PERCENTILE / 100)
            salary_threshold = salaries[salary_threshold_index] if salary_threshold_index < len(salaries) else 0
            
            # Mark premium RBs
            premium_rbs = []
            for p in rb_players:
                if p.rush_attempts >= rush_threshold and p.salary >= salary_threshold:
                    premium_rbs.append(p)
            
            # Add constraint to require minimum number of premium RBs
            if premium_rbs:
                model.Add(sum(player_vars[p.id] for p in premium_rbs) >= Config.MIN_PREMIUM_RBS)
    
    # Low ownership constraint (offensive positions only)
    offensive_players = [p for p in players if any(pos in ["QB", "RB", "WR", "TE"] for pos in p.positions)]
    low_ownership_players = [p for p in offensive_players if p.ownership <= Config.LOW_OWNERSHIP_THRESHOLD]
    if low_ownership_players:
        model.Add(sum(player_vars[p.id] for p in low_ownership_players) >= Config.MIN_LOW_OWNERSHIP_PLAYERS)
    
    # Total ownership sum constraints
    if Config.ENABLE_OWNERSHIP_SUM_CONSTRAINTS:
        # For the constraint only, scale to integer (preserve two decimal places)
        total_ownership = sum(int(round(p.ownership * 100)) * player_vars[p.id] for p in players)
        model.Add(total_ownership >= int(round(Config.MIN_TOTAL_OWNERSHIP * 100)))
        model.Add(total_ownership <= int(round(Config.MAX_TOTAL_OWNERSHIP * 100)))

def create_lineup_model(players: List[Player], 
                       teams: List[str],
                       used_lineups_sets: List[Set[int]]) -> Tuple[cp_model.CpModel, Dict]:
    """Create the CP-SAT model with all necessary constraints."""
    model = cp_model.CpModel()
    
    # Create player variables
    player_vars = {p.id: model.NewBoolVar(f"player_{p.id}") for p in players}
    assign = {}
    
    # Create assignment variables
    for p in players:
        assign[p.id] = {}
        for slot in Config.SLOTS:
            can_play = (
                (slot == "QB" and "QB" in p.positions) or
                (slot == "RB" and "RB" in p.positions) or
                (slot == "WR" and "WR" in p.positions) or
                (slot == "TE" and "TE" in p.positions) or
                (slot == "FLEX" and "RB" in p.positions) or
                (slot == "D" and ("D" in p.positions or "DST" in p.positions))
            )
            if can_play:
                assign[p.id][slot] = model.NewBoolVar(f"assign_{p.id}_{slot}")
    
    # Add roster constraints
    for slot, count in Config.SLOTS.items():
        model.Add(sum(assign[p.id][slot] for p in players if slot in assign[p.id]) == count)
    
    # Ensure we have at least one player at each position (for QB, TE, D)
    # QB position
    qb_players = [p for p in players if "QB" in p.positions]
    if qb_players:
        model.Add(sum(player_vars[p.id] for p in qb_players) >= 1)
    
    # TE position
    te_players = [p for p in players if "TE" in p.positions]
    if te_players:
        model.Add(sum(player_vars[p.id] for p in te_players) >= 1)
    
    # D position
    d_players = [p for p in players if "D" in p.positions or "DST" in p.positions]
    if d_players:
        model.Add(sum(player_vars[p.id] for p in d_players) >= 1)
    
    # Ensure each player can only be used once
    for p in players:
        model.Add(sum(assign[p.id][s] for s in assign[p.id]) <= 1)
        model.Add(sum(assign[p.id][s] for s in assign[p.id]) == player_vars[p.id])
    
    # Ensure exactly one defense is used
    defense_players = [p for p in players if "D" in p.positions or "DST" in p.positions]
    model.Add(sum(player_vars[p.id] for p in defense_players) == 1)
    
    # Add constraint to prevent defense against opposing teams
    for d in defense_players:
        for p in players:
            if not (d.team == p.opponent or p.team == d.opponent):
                continue
            model.AddBoolOr([player_vars[d.id].Not(), player_vars[p.id].Not()])
    
    # Add skill position team limit constraint
    add_skill_position_team_limit(model, players, player_vars)
    
    # Add QB stack constraint
    add_qb_stack_constraint(model, players, player_vars)
    
    # Add RB team limit constraint
    add_rb_team_limit(model, players, player_vars)
    
    # Add OIS constraints
    add_ois_constraints(model, players, player_vars)
    
    # Add player group constraints
    add_player_group_constraints(model, players, player_vars)
    
    # Add secondary stack constraints
    add_secondary_stack_constraints(model, players, player_vars, assign)
    
    # Add filtering constraints
    add_filtering_constraints(model, players, player_vars)
    
    # Add constraint for max 4 players per team
    players_by_team = {}
    for p in players:
        if p.team not in players_by_team:
            players_by_team[p.team] = []
        players_by_team[p.team].append(p)
    
    for team, team_players in players_by_team.items():
        team_sum = sum(player_vars[p.id] for p in team_players)
        model.Add(team_sum <= 4)
    
    # Add constraint for minimum 3 teams
    team_vars = {}
    for team in teams:
        team_vars[team] = model.NewBoolVar(f"team_{team}")
        team_players = [p for p in players if p.team == team]
        if team_players:
            model.AddBoolOr([player_vars[p.id] for p in team_players]).OnlyEnforceIf(team_vars[team])
            model.AddBoolAnd([player_vars[p.id].Not() for p in team_players]).OnlyEnforceIf(team_vars[team].Not())
    
    model.Add(sum(team_vars[team] for team in teams) >= 3)
    
    # Add salary constraints
    total_salary = sum(p.salary * player_vars[p.id] for p in players)
    model.Add(total_salary <= Config.MAX_SALARY)
    model.Add(total_salary >= Config.MIN_SALARY)
    
    # Add uniqueness constraints
    for prev in used_lineups_sets:
        has_enough_unique = model.NewBoolVar(f"has_enough_unique_{len(used_lineups_sets)}")
        common_players = sum(player_vars[pid] for pid in prev if pid in player_vars)
        model.Add(common_players <= 6).OnlyEnforceIf(has_enough_unique)
        model.Add(common_players > 6).OnlyEnforceIf(has_enough_unique.Not())
        model.Add(has_enough_unique == 1)
    
    # Set objective function (maximize projection)
    objective = sum(p.current_projection * player_vars[p.id] for p in players)
    model.Maximize(objective)
    
    variables = {
        "player_vars": player_vars,
        "assign": assign,
        "team_vars": team_vars
    }
    
    return model, variables

def has_duplicate_players(lineup: Lineup) -> bool:
    player_ids = [p["Id"] for p in lineup.players]
    return len(player_ids) != len(set(player_ids))

def solve_lineup(model: cp_model.CpModel,
                players: List[Player],
                teams: List[str],
                variables: Dict) -> Optional[Lineup]:
    """Solve the lineup optimization model and return the solution if found."""
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.Solve(model)
    
    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return None
    
    lineup = []
    primary_stack = ""
    secondary_stack = ""
    used_players = set()  # Track used players to prevent duplicates
    
    # Get players in lineup with their assigned positions
    for p in players:
        if solver.Value(variables["player_vars"][p.id]):
            # Find which position this player is assigned to
            assigned_slot = next((s for s in variables["assign"][p.id] 
                                if solver.Value(variables["assign"][p.id][s])), None)
            
            if assigned_slot and p.id not in used_players:
                lineup.append({
                    "Slot": assigned_slot,
                    "Name": p.name,
                    "Team": p.team,
                    "Opponent": p.opponent,
                    "Positions": ",".join(p.positions),
                    "Salary": p.salary,
                    "Projection": p.projection,
                    "Ownership": p.ownership,
                    "Rush": p.rush_attempts,
                    "Targets": p.targets,
                    "Ceiling": p.ceiling,
                    "Id": p.id
                })
                used_players.add(p.id)
    
    # Verify lineup has exactly 9 unique players
    if len(used_players) != 9:
        print(f"Warning: Expected 9 unique players, got {len(used_players)}")
        return None
    
    # Verify each position has the correct number of players
    position_counts = {}
    for player in lineup:
        position_counts[player["Slot"]] = position_counts.get(player["Slot"], 0) + 1
    
    for slot, count in Config.SLOTS.items():
        if position_counts.get(slot, 0) != count:
            print(f"Warning: Expected {count} players for {slot}, got {position_counts.get(slot, 0)}")
            return None
    
    # Final duplicate check
    temp_lineup = Lineup(lineup, primary_stack, secondary_stack)
    if has_duplicate_players(temp_lineup):
        print("Warning: Duplicate player detected in lineup, skipping.")
        return None
    
    return temp_lineup

def print_lineup(lineup: Lineup, lineup_num: int) -> None:
    """Print the lineup in a formatted way."""
    print(f"=== Lineup {lineup_num} ===")
    
    # Define FanDuel's required position order
    fd_position_order = ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX', 'D']
    
    # Create a mapping of positions to players
    position_map = {}
    rb_candidates = []
    wr_candidates = []
    flex_candidates = []
    
    # First, organize players by their assigned slots
    for player in lineup.players:
        if player["Slot"] == "RB":
            rb_candidates.append(player)
        elif player["Slot"] == "WR":
            wr_candidates.append(player)
        elif player["Slot"] == "FLEX":
            flex_candidates.append(player)
        elif player["Slot"] in ["D", "DST"]:
            position_map["D"] = player
        else:
            position_map[player["Slot"]] = player
    
    # Print players in FanDuel's order
    for pos in fd_position_order:
        if pos == 'RB':
            if rb_candidates:
                player = rb_candidates.pop(0)  # Get and remove first RB
                print(f"ID: {player['Id']} | {pos}: {player['Name']} ({player['Team']}) | Proj: {player['Projection']:.2f} | Own: {player['Ownership']:.1f}% | Rush: {player.get('Rush', 0):.1f}")
        elif pos == 'WR':
            if wr_candidates:
                player = wr_candidates.pop(0)  # Get and remove first WR
                print(f"ID: {player['Id']} | {pos}: {player['Name']} ({player['Team']}) | Proj: {player['Projection']:.2f} | Own: {player['Ownership']:.1f}%")
        elif pos == 'FLEX':
            if flex_candidates:
                player = flex_candidates[0]
                print(f"ID: {player['Id']} | {pos}: {player['Name']} ({player['Team']}) | Proj: {player['Projection']:.2f} | Own: {player['Ownership']:.1f}% | Rush: {player.get('Rush', 0):.1f}")
        elif pos == 'D':
            if 'D' in position_map:
                player = position_map['D']
                print(f"ID: {player['Id']} | {pos}: {player['Name']} ({player['Team']}) | Proj: {player['Projection']:.2f} | Own: {player['Ownership']:.1f}%")
        else:
            if pos in position_map:
                player = position_map[pos]
                print(f"ID: {player['Id']} | {pos}: {player['Name']} ({player['Team']}) | Proj: {player['Projection']:.2f} | Own: {player['Ownership']:.1f}%")
    
    # Calculate totals
    total_salary = sum(p['Salary'] for p in lineup.players)
    total_projection = sum(p['Projection'] for p in lineup.players)
    total_ownership = sum(p['Ownership'] for p in lineup.players)
    total_ceiling = sum(p['Ceiling'] for p in lineup.players)
    
    # Calculate NFL-specific statistics
    total_targets = sum(p['Targets'] for p in lineup.players if any(pos in ["WR", "TE", "RB"] for pos in p["Positions"].split(",")))
    total_rushes = sum(p['Rush'] for p in lineup.players if "RB" in p["Positions"])
    
    print(f"\nTotal Salary: ${total_salary}")
    print(f"Total Projection: {total_projection:.2f}")
    print(f"Total Ceiling: {total_ceiling:.2f}")
    print(f"Total Targets: {total_targets:.1f}")
    print(f"Total Rushes: {total_rushes:.1f}")
    print(f"Total Lineup Ownership: {total_ownership:.1f}%")
    
    # Show ownership constraints if enabled
    if Config.ENABLE_OWNERSHIP_SUM_CONSTRAINTS:
        print(f"Ownership Range: {Config.MIN_TOTAL_OWNERSHIP:.1f}% - {Config.MAX_TOTAL_OWNERSHIP:.1f}%")

def export_to_csv(lineups: List[Lineup], output_path: str) -> None:
    """Export lineups to a CSV file, matching the printout order exactly (FanDuel order)."""
    if not lineups:
        print("No lineups to export")
        return
    
    # Filter out any lineups with duplicate players before exporting
    valid_lineups = [l for l in lineups if not has_duplicate_players(l)]
    if len(valid_lineups) < len(lineups):
        print(f"Filtered out {len(lineups) - len(valid_lineups)} lineups with duplicate players.")
    if not valid_lineups:
        print("No valid lineups to export after duplicate check.")
        return
    
    # Calculate metrics for all lineups
    lineup_metrics = calculate_lineup_metrics(valid_lineups)
    
    # Sort by Average_Rank (ascending) and take top 150
    lineup_metrics.sort(key=lambda x: x["Average_Rank"])
    top_lineups = lineup_metrics[:150]  # Filter to top 150 ranked lineups
    print(f"Filtered to top {len(top_lineups)} lineups (sorted by Average_Rank)")
    
    # FanDuel slot order
    fd_order = ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'TE', 'FLEX', 'D']
    slot_names = ['QB', 'RB1', 'RB2', 'WR1', 'WR2', 'WR3', 'TE', 'FLEX', 'D']
    data = []
    skipped_due_to_duplicates = 0
    for i, lm in enumerate(top_lineups, 1):
        lineup = lm["lineup"]
        player_ids = [p["Id"] for p in lineup.players]
        if len(player_ids) != len(set(player_ids)):
            print(f"DEBUG: Skipping lineup {i} due to duplicate players: {player_ids}")
            skipped_due_to_duplicates += 1
            continue  # Skip this lineup
        # Build slot-to-player mapping (lists for multi-slot positions)
        slot_map = {slot: [] for slot in set(fd_order)}
        for player in lineup.players:
            slot = player["Slot"]
            # Normalize D/DST
            if slot in ["D", "DST"]:
                slot_map["D"].append(player)
            elif slot in slot_map:
                slot_map[slot].append(player)
        # Track used player IDs
        used_ids = set()
        row = {}
        # Fill each slot in FanDuel order, never duplicating a player
        for idx, pos in enumerate(fd_order):
            found = False
            for player in slot_map[pos]:
                if player["Id"] not in used_ids:
                    row[slot_names[idx]] = player['Name']
                    used_ids.add(player["Id"])
                    found = True
                    break
            # For FLEX, if not found, use next unused RB/WR/TE
            if not found and pos == "FLEX":
                for alt_slot in ["RB", "WR", "TE"]:
                    for player in slot_map[alt_slot]:
                        if player["Id"] not in used_ids:
                            row[slot_names[idx]] = player['Name']
                            used_ids.add(player["Id"])
                            found = True
                            break
                    if found:
                        break
            if not found:
                row[slot_names[idx]] = ""
        # Summary columns
        row["Primary_Stack"] = lineup.primary_stack
        row["Secondary_Stack"] = lineup.secondary_stack
        row["Total_Projection"] = lm["Total_Projection"]
        row["Total_Salary"] = sum(p["Salary"] for p in lineup.players)
        row["Total_Ceiling"] = lm["Total_Ceiling"]
        row["Total_Targets"] = lm["Total_Targets"]
        row["Total_Rushes"] = lm["Total_Rushes"]
        # Ownership product and sum
        row["Total_Ownership_Product"] = f'{lm["Total_Ownership_Product"]:.10f}%'
        row["Total_Ownership_Sum"] = lm["Total_Ownership_Sum"]
        # Z-scores
        row["Projection_ZScore"] = lm["Total_Projection_ZScore"]
        row["Ceiling_ZScore"] = lm["Total_Ceiling_ZScore"]
        row["Targets_ZScore"] = lm["Total_Targets_ZScore"]
        row["Rushes_ZScore"] = lm["Total_Rushes_ZScore"]
        row["Ownership_ZScore"] = lm["Total_Ownership_Product_ZScore"]
        # Rankings
        row["Projection_Rank"] = lm["Total_Projection_Rank"]
        row["Ceiling_Rank"] = lm["Total_Ceiling_Rank"]
        row["Targets_Rank"] = lm["Total_Targets_Rank"]
        row["Rushes_Rank"] = lm["Total_Rushes_Rank"]
        row["Ownership_Rank"] = lm["Total_Ownership_Product_Rank"]
        # Average Rank
        row["Average_Rank"] = lm["Average_Rank"]
        data.append(row)
    print(f"\nDEBUG: Skipped {skipped_due_to_duplicates} lineups due to duplicate players during export.")
    # Data is already sorted by Average_Rank from the lineup_metrics sorting above
    # Create DataFrame
    columns = slot_names + [
        "Primary_Stack", "Secondary_Stack", "Total_Projection", "Total_Salary",
        "Total_Ceiling", "Total_Targets", "Total_Rushes", 
        "Total_Ownership_Product", "Total_Ownership_Sum",
        "Projection_ZScore", "Ceiling_ZScore", "Targets_ZScore", "Rushes_ZScore", "Ownership_ZScore",
        "Projection_Rank", "Ceiling_Rank", "Targets_Rank", "Rushes_Rank", "Ownership_Rank",
        "Average_Rank"
    ]
    df = pd.DataFrame(data, columns=columns)
    # Export to CSV
    df.to_csv(output_path, index=False)
    print(f"Exported {len(data)} lineups to {output_path}")

def export_report(lineups: List[Lineup], players: List[Player], output_path: str) -> None:
    """Export a detailed report showing player exposures and stacking configurations."""
    if not lineups:
        print("No lineups to generate report for")
        return
    
    print(f"\nGenerating exposure report for {len(lineups)} lineups...")
    
    # Player exposure tracking
    player_exposures = {}
    for player in players:
        player_exposures[player.id] = {
            'name': player.name,
            'team': player.team,
            'positions': player.positions,
            'count': 0,
            'percentage': 0.0
        }
    
    # Stack tracking
    primary_stacks = {}
    secondary_stacks = {}
    
    # Process each lineup
    for lineup in lineups:
        # Count player exposures
        for player in lineup.players:
            player_id = player["Id"]
            if player_id in player_exposures:
                player_exposures[player_id]['count'] += 1
        
        # Track primary stacks
        if lineup.primary_stack:
            if lineup.primary_stack not in primary_stacks:
                primary_stacks[lineup.primary_stack] = 0
            primary_stacks[lineup.primary_stack] += 1
        
        # Track secondary stacks
        if lineup.secondary_stack:
            if lineup.secondary_stack not in secondary_stacks:
                secondary_stacks[lineup.secondary_stack] = 0
            secondary_stacks[lineup.secondary_stack] += 1
    
    # Calculate percentages
    total_lineups = len(lineups)
    for player_data in player_exposures.values():
        player_data['percentage'] = (player_data['count'] / total_lineups) * 100
    
    # Sort players by exposure percentage (descending) and organize by position
    sorted_players = sorted(player_exposures.values(), key=lambda x: x['percentage'], reverse=True)
    
    # Organize players by position
    players_by_position = {
        'QB': [],
        'RB': [],
        'WR': [],
        'TE': [],
        'D': []
    }
    
    for player in sorted_players:
        if player['count'] > 0:  # Only include players with exposure
            for pos in player['positions']:
                if pos in players_by_position:
                    players_by_position[pos].append(player)
                    break  # Only add to first matching position
    
    # Sort stacks by count (descending)
    sorted_primary_stacks = sorted(primary_stacks.items(), key=lambda x: x[1], reverse=True)
    sorted_secondary_stacks = sorted(secondary_stacks.items(), key=lambda x: x[1], reverse=True)
    
    # Generate report content
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("NFL DFS LINEUP EXPOSURE REPORT")
    report_lines.append("=" * 80)
    report_lines.append(f"Total Lineups Analyzed: {total_lineups}")
    report_lines.append(f"Report Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")
    
    # Player Exposures Section (organized by position)
    report_lines.append("PLAYER EXPOSURES BY POSITION")
    report_lines.append("=" * 80)
    
    for position in ['QB', 'RB', 'WR', 'TE', 'D']:
        if players_by_position[position]:
            report_lines.append(f"\n{position} POSITION")
            report_lines.append("-" * 40)
            report_lines.append(f"{'Player':<30} {'Team':<5} {'Count':<6} {'%':<6}")
            report_lines.append("-" * 40)
            
            for player in players_by_position[position]:
                report_lines.append(f"{player['name']:<30} {player['team']:<5} {player['count']:<6} {player['percentage']:<6.1f}")
    
    report_lines.append("")
    
    # Primary Stack Configurations
    report_lines.append("PRIMARY STACK CONFIGURATIONS")
    report_lines.append("-" * 40)
    report_lines.append(f"{'Stack Configuration':<30} {'Count':<6} {'%':<6}")
    report_lines.append("-" * 40)
    
    for stack, count in sorted_primary_stacks:
        percentage = (count / total_lineups) * 100
        report_lines.append(f"{stack:<30} {count:<6} {percentage:<6.1f}")
    
    report_lines.append("")
    
    # Secondary Stack Configurations
    report_lines.append("SECONDARY STACK CONFIGURATIONS")
    report_lines.append("-" * 40)
    report_lines.append(f"{'Stack Configuration':<30} {'Count':<6} {'%':<6}")
    report_lines.append("-" * 40)
    
    for stack, count in sorted_secondary_stacks:
        percentage = (count / total_lineups) * 100
        report_lines.append(f"{stack:<30} {count:<6} {percentage:<6.1f}")
    
    report_lines.append("")
    
    # Detailed Stack Analysis
    report_lines.append("DETAILED STACK ANALYSIS")
    report_lines.append("-" * 40)
    
    # Group lineups by primary stack
    stack_groups = {}
    for lineup in lineups:
        if lineup.primary_stack:
            if lineup.primary_stack not in stack_groups:
                stack_groups[lineup.primary_stack] = []
            stack_groups[lineup.primary_stack].append(lineup)
    
    for stack_name, stack_lineups in stack_groups.items():
        report_lines.append(f"\n{stack_name} Stack ({len(stack_lineups)} lineups):")
        
        # Get all players in this stack
        stack_players = {}
        for lineup in stack_lineups:
            qb = next((p for p in lineup.players if "QB" in p["Positions"]), None)
            if qb:
                qb_team = qb["Team"]
                for player in lineup.players:
                    if player["Team"] == qb_team and player["Id"] != qb["Id"]:
                        player_id = player["Id"]
                        if player_id not in stack_players:
                            stack_players[player_id] = {
                                'name': player["Name"],
                                'positions': player["Positions"],
                                'count': 0
                            }
                        stack_players[player_id]['count'] += 1
        
        # Sort stack players by count
        sorted_stack_players = sorted(stack_players.values(), key=lambda x: x['count'], reverse=True)
        
        for player in sorted_stack_players:
            percentage = (player['count'] / len(stack_lineups)) * 100
            positions_str = "/".join(player['positions'].split(","))
            report_lines.append(f"  {player['name']:<25} {positions_str:<8} {player['count']:<3} ({percentage:.1f}%)")
    
    # Write report to file
    with open(output_path, 'w') as f:
        f.write('\n'.join(report_lines))
    
    print(f"Exported exposure report to {output_path}")

def list_lineup_stacks(lineup: Lineup):
    """List the stacks found in a lineup."""
    players = lineup.players

    # Primary Stack: QB + skill players from same team
    qb = next((p for p in players if "QB" in p["Positions"]), None)
    primary_stack = []
    if qb:
        primary_stack = [p for p in players if p["Team"] == qb["Team"] and any(pos in ["WR", "RB", "TE"] for pos in p["Positions"].split(","))]
        print(f"Primary Stack (QB Stack): QB {qb['Name']} with {[p['Name'] for p in primary_stack]}")

    # Secondary Stack Detection
    secondary_stack_found = False
    
    # Check for RB + opponent WR stack
    if Config.ENABLE_RB_OPP_STACK:
        rbs = [p for p in players if "RB" in p["Positions"]]
        for rb in rbs:
            opp_wrs = [p for p in players if p["Team"] == rb["Opponent"] and "WR" in p["Positions"]]
            if opp_wrs:
                print(f"Secondary Stack (RB + Opp WR): {rb['Name']} + {[p['Name'] for p in opp_wrs]}")
                secondary_stack_found = True
                break
    
    # Check for WR + WR opponent stack
    if not secondary_stack_found and Config.ENABLE_WR_WR_OPP_STACK:
        wrs = [p for p in players if "WR" in p["Positions"]]
        for wr1 in wrs:
            opp_wrs = [p for p in players if p["Team"] == wr1["Opponent"] and "WR" in p["Positions"]]
            if opp_wrs:
                print(f"Secondary Stack (WR + WR Opponent): {wr1['Name']} + {[p['Name'] for p in opp_wrs]}")
                secondary_stack_found = True
                break
    
    # Check for RB + DEF same team stack
    if not secondary_stack_found and Config.ENABLE_RB_DEF_SAME_TEAM:
        rbs = [p for p in players if "RB" in p["Positions"]]
        for rb in rbs:
            same_team_def = [p for p in players if p["Team"] == rb["Team"] and ("D" in p["Positions"] or "DST" in p["Positions"])]
            if same_team_def:
                print(f"Secondary Stack (RB + DEF Same Team): {rb['Name']} + {[p['Name'] for p in same_team_def]}")
                secondary_stack_found = True
                break
    
    if not secondary_stack_found:
        print("No secondary stack found in this lineup.")

def identify_premium_rbs(lineup: Lineup, players: List[Player]) -> List[str]:
    """Identify premium RBs in the lineup based on rush attempts and salary percentiles."""
    if not Config.ENABLE_PREMIUM_RB_FILTER:
        return []
    
    # Get all RBs from the full player pool
    all_rbs = [p for p in players if "RB" in p.positions]
    if not all_rbs:
        return []
    
    # Calculate rush attempts percentiles
    rush_attempts = [p.rush_attempts for p in all_rbs]
    rush_attempts.sort()
    rush_threshold_index = int(len(rush_attempts) * Config.PREMIUM_RB_RUSH_PERCENTILE / 100)
    rush_threshold = rush_attempts[rush_threshold_index] if rush_threshold_index < len(rush_attempts) else 0
    
    # Calculate salary percentiles
    salaries = [p.salary for p in all_rbs]
    salaries.sort()
    salary_threshold_index = int(len(salaries) * Config.PREMIUM_RB_SALARY_PERCENTILE / 100)
    salary_threshold = salaries[salary_threshold_index] if salary_threshold_index < len(salaries) else 0
    
    # Find premium RBs in the lineup
    premium_rbs = []
    for player in lineup.players:
        if "RB" in player["Positions"]:
            # Find the corresponding player object
            player_obj = next((p for p in players if p.id == player["Id"]), None)
            if player_obj and player_obj.rush_attempts >= rush_threshold and player_obj.salary >= salary_threshold:
                premium_rbs.append(player["Name"])
    
    return premium_rbs

def identify_low_ownership_players(lineup: Lineup) -> List[str]:
    """Identify players with low ownership (<= 5%) in the lineup."""
    low_ownership_players = []
    for player in lineup.players:
        if player["Ownership"] <= Config.LOW_OWNERSHIP_THRESHOLD:
            low_ownership_players.append(f"{player['Name']} ({player['Ownership']:.1f}%)")
    return low_ownership_players

def calculate_lineup_metrics(lineups: List[Lineup]) -> List[Dict]:
    """Calculate z-scores, rankings, and average ranks for all lineups."""
    if not lineups:
        return []
    
    # Calculate metrics for each lineup
    lineup_metrics = []
    for lineup in lineups:
        total_projection = sum(p["Projection"] for p in lineup.players)
        total_ceiling = sum(p["Ceiling"] for p in lineup.players)
        total_targets = sum(p["Targets"] for p in lineup.players if any(pos in ["WR", "TE", "RB"] for pos in p["Positions"].split(",")))
        total_rushes = sum(p["Rush"] for p in lineup.players if "RB" in p["Positions"])
        # Ownership product (as decimal)
        ownership_product = 1.0
        for p in lineup.players:
            ownership_product *= max(p["Ownership"] / 100.0, 0.0001)  # Avoid zero
        # Ownership sum (for reference)
        total_ownership_sum = sum(p["Ownership"] for p in lineup.players)
        lineup_metrics.append({
            "lineup": lineup,
            "Total_Projection": total_projection,
            "Total_Ceiling": total_ceiling,
            "Total_Targets": total_targets,
            "Total_Rushes": total_rushes,
            "Total_Ownership_Product": ownership_product * 100,  # as percentage
            "Total_Ownership_Sum": total_ownership_sum
        })
    # Calculate z-scores for each metric
    metrics = ["Total_Projection", "Total_Ceiling", "Total_Targets", "Total_Rushes", "Total_Ownership_Product"]
    for metric in metrics:
        values = [lm[metric] for lm in lineup_metrics]
        mean_val = sum(values) / len(values)
        std_val = (sum((x - mean_val) ** 2 for x in values) / len(values)) ** 0.5
        if std_val == 0:
            for lm in lineup_metrics:
                lm[f"{metric}_ZScore"] = 0.0
        else:
            for lm in lineup_metrics:
                lm[f"{metric}_ZScore"] = (lm[metric] - mean_val) / std_val
    # Calculate rankings (higher is better for all except ownership product)
    for metric in metrics:
        if metric == "Total_Ownership_Product":
            # For ownership product, lower is better
            sorted_lineups = sorted(lineup_metrics, key=lambda x: x[metric])
        else:
            sorted_lineups = sorted(lineup_metrics, key=lambda x: x[metric], reverse=True)
        for i, lm in enumerate(sorted_lineups):
            lm[f"{metric}_Rank"] = i + 1
    # Calculate average rank for each lineup
    for lm in lineup_metrics:
        ranks = [lm[f"{metric}_Rank"] for metric in metrics]
        lm["Average_Rank"] = sum(ranks) / len(ranks)
    return lineup_metrics

def get_lineup_stack_types(lineup: Lineup) -> tuple[str, str]:
    players = lineup.players

    # --- Primary Stack ---
    qb = next((p for p in players if "QB" in p["Positions"]), None)
    primary_stack = ""
    if qb:
        # Find all skill positions from QB's team
        stack_positions = set()
        for p in players:
            if p["Team"] == qb["Team"] and p["Id"] != qb["Id"]:
                for pos in p["Positions"].split(","):
                    if pos in ["RB", "WR", "TE"]:
                        stack_positions.add(pos)
        if stack_positions:
            primary_stack = "QB/" + "/".join(sorted(stack_positions))
        else:
            primary_stack = "QB"

    # --- Secondary Stack ---
    secondary_stack = ""
    # RB + Opp WR
    if Config.ENABLE_RB_OPP_STACK:
        rbs = [p for p in players if "RB" in p["Positions"]]
        for rb in rbs:
            opp_wrs = [p for p in players if p["Team"] == rb["Opponent"] and "WR" in p["Positions"]]
            if opp_wrs:
                secondary_stack = "RB/Opp WR"
                break
    # WR + Opp WR
    if not secondary_stack and Config.ENABLE_WR_WR_OPP_STACK:
        wrs = [p for p in players if "WR" in p["Positions"]]
        for wr1 in wrs:
            opp_wrs = [p for p in players if p["Team"] == wr1["Opponent"] and "WR" in p["Positions"]]
            if opp_wrs:
                secondary_stack = "WR/Opp WR"
                break
    # RB + DEF
    if not secondary_stack and Config.ENABLE_RB_DEF_SAME_TEAM:
        rbs = [p for p in players if "RB" in p["Positions"]]
        for rb in rbs:
            same_team_def = [p for p in players if p["Team"] == rb["Team"] and ("D" in p["Positions"] or "DST" in p["Positions"])]
            if same_team_def:
                secondary_stack = "RB/DEF"
                break

    return primary_stack, secondary_stack

def main():
    """Main function to run the lineup optimizer."""
    try:
        # Load and process data
        df, ro8_9_ids = load_and_clean_data(Config.DATA_FILE)
        players = create_player_objects(df)
        teams = list(set(p.team for p in players))
        
        # Initialize smart randomness
        smart_randomness = None
        if Config.ENABLE_SMART_RANDOMNESS:
            smart_randomness = SmartRandomness(players, Config.DISTRIBUTION_TYPE, Config.RANDOMNESS_SEED)
            
            # Apply smart randomness once at the start if frequency is per_session
            if Config.RANDOMNESS_FREQUENCY == "per_lineup":
                for player in players:
                    if player.std_dev:
                        player.current_projection = smart_randomness.apply_randomness(player.id, player.projection)
        
        # Validate configurations against available players
        print("\n=== Configuration Validation ===")
        
        # Validate QB stacks
        qb_stack_validation = validate_all_qb_stacks_against_players(players)
        print(f"QB Stack Validation: {qb_stack_validation['valid_count']}/{qb_stack_validation['total_qbs']} valid")
        
        if qb_stack_validation['warnings']:
            print("\nQB Stack Warnings:")
            for qb, warnings in qb_stack_validation['warnings'].items():
                for warning in warnings:
                    print(f"  {warning}")
        
        if qb_stack_validation['invalid_configs']:
            print("\nQB Stack Errors:")
            for qb, errors in qb_stack_validation['invalid_configs'].items():
                for error in errors:
                    print(f"  {error}")
        
        # Validate player groups
        group_validation = validate_all_groups_against_players(players)
        print(f"\nPlayer Group Validation: {group_validation['valid_count']}/{group_validation['total_groups']} valid")
        
        if group_validation['warnings']:
            print("\nPlayer Group Warnings:")
            for group, warnings in group_validation['warnings'].items():
                for warning in warnings:
                    print(f"  {warning}")
        
        if group_validation['invalid_groups']:
            print("\nPlayer Group Errors:")
            for group, errors in group_validation['invalid_groups'].items():
                for error in errors:
                    print(f"  {error}")
        
        print("=== End Configuration Validation ===\n")
        
        # Initialize tracking variables
        generated_lineups = []
        used_lineups_sets = []
        attempt = 0
        
        # Generate lineups
        while (len(generated_lineups) < Config.NUM_LINEUPS_TO_GENERATE and 
               attempt < Config.MAX_ATTEMPTS):
            attempt += 1
            
            # Apply smart randomness to player projections if enabled
            if smart_randomness and Config.RANDOMNESS_FREQUENCY == "per_lineup":
                for player in players:
                    if player.std_dev:
                        player.current_projection = smart_randomness.apply_randomness(player.id, player.projection)
            
            # Create and solve model
            model, variables = create_lineup_model(
                players, teams, used_lineups_sets
            )
            
            lineup = solve_lineup(model, players, teams, variables)
            if not lineup:
                continue
            
            # Set stack types before appending
            primary_stack, secondary_stack = get_lineup_stack_types(lineup)
            lineup.primary_stack = primary_stack
            lineup.secondary_stack = secondary_stack
            # Deep copy lineup before appending to avoid mutation issues
            generated_lineups.append(copy.deepcopy(lineup))
            used_lineups_sets.append(set(p["Id"] for p in lineup.players))
            
            # Print lineup
            print_lineup(lineup, len(generated_lineups))
            # Print stacks
            list_lineup_stacks(lineup)
            # Print premium RBs
            premium_rbs = identify_premium_rbs(lineup, players)
            if premium_rbs:
                print(f"Premium RBs: {', '.join(premium_rbs)}")
            
            # Print low ownership players
            low_ownership_players = identify_low_ownership_players(lineup)
            if low_ownership_players:
                print(f"Low Ownership Players (≤{Config.LOW_OWNERSHIP_THRESHOLD}%): {', '.join(low_ownership_players)}")
            else:
                print(f"No players with ownership ≤{Config.LOW_OWNERSHIP_THRESHOLD}% found")
        
        print(f"\nGenerated {len(generated_lineups)} lineups in {attempt} attempts")
        
        # Export lineups
        output_path = "/Users/adamsardinha/Desktop/FD_NFL_Lineups.csv"
        export_to_csv(generated_lineups, output_path)
        print(f"\nExported lineups to {output_path}")
        
        # Calculate metrics and get top 150 lineups for report
        lineup_metrics = calculate_lineup_metrics(generated_lineups)
        lineup_metrics.sort(key=lambda x: x["Average_Rank"])
        top_150_lineups = [lm["lineup"] for lm in lineup_metrics[:150]]
        
        # Export exposure report (using only the top 150 lineups)
        report_path = "/Users/adamsardinha/Desktop/FD_NFL_Exposure_Report.txt"
        export_report(top_150_lineups, players, report_path)
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main()