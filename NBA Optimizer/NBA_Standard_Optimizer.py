"""
NBA Standard Daily Fantasy Sports Lineup Optimizer
This script generates optimized lineups for NBA standard DFS contests using constraint programming.
"""

from typing import List, Dict, Set, Tuple, Optional
import pandas as pd
from ortools.sat.python import cp_model
import os
from dataclasses import dataclass
from pathlib import Path
import csv
import numpy as np

# ===== Configuration =====
class Config:
    # File paths
    DATA_FILE = "/Users/adamsardinha/Desktop/NBA_Standard_FD.csv"
    
    # Lineup generation settings
    NUM_LINEUPS_TO_GENERATE = 500
    TOP_LINEUPS_TO_EXPORT = 150  # Number of top ranked lineups to export
    MAX_SALARY = 60000  # FanDuel standard salary cap
    MIN_SALARY = 59500  # Minimum salary to ensure quality lineups
    MAX_ATTEMPTS = 500
    
    # Minimum projection to include a player in the pool
    MIN_PROJECTION = 12
    
    # Value filtering (points per dollar * 1000)
    ENABLE_VALUE_FILTER = True
    MIN_VALUE = 4.5  # Minimum value threshold (points per dollar * 1000)
    
    # Stack rules
    ENABLED_STACK_RULES = False
    MAX_PLAYERS_PER_TEAM = 4  # Maximum players from one team
        
    # Roster settings for FanDuel NBA classic contests
    SLOTS = {
        "PG": 2,
        "SG": 2,
        "SF": 2,
        "PF": 2,
        "C": 1
    }
    
    # Players to exclude from lineups
    EXCLUDED_PLAYERS = [
        # Add players to exclude here
    ]
    
    # Players that must be in every lineup
    CORE_PLAYERS = [
        "Jalen Brunson","Jrue Holiday","Jaylen Brown","Al Horford","Mitchell Robinson","Payton Pritchard","Derrick White","Julius Randle"
    ]
    
    # Minimum number of core players that must be used in each lineup
    MIN_CORE_PLAYERS = 6
    
    # Filler players for each position (if not a core player, only these can fill the slot)
    FILLER_PLAYERS = {
        # "PG": ["Jrue Holiday","Payton Pritchard","Derrick White","Jalen Brunson","Mike Conley"],
        # "SG": ["Anthony Edwards","Mikal Bridges","Donte DiVincenzo","Buddy Hield","Brandin Podziemski"],
        # "SF": ["Jaylen Brown","Jaden McDaniels","OG Anunoby","Nickeil Alexander-Walker","Sam Hauser"],
        # "PF": ["Julius Randle","Josh Hart","Jonathan Kuminga","Jimmy Butler","Naz Reid"],
        # "C": ["Al Horford","Karl-Anthony Towns","Kristaps Porzingis","Draymond Green","Mitchell Robinson"]
        # # ...
    }
    
    # Teams to exclude from stacking
    EXCLUDED_TEAMS = [
        # Add teams to exclude from stacking here
    ]
    
    # Smart Randomness settings
    ENABLE_SMART_RANDOMNESS = True  # Toggle smart randomness feature
    DISTRIBUTION_TYPE = "lognormal"  # "normal" or "lognormal"
    RANDOMNESS_SEED = None  # Set to an integer for reproducible results
    RANDOMNESS_FREQUENCY = "per_lineup"  # "per_lineup" or "per_session" (once at start)

    # ===== Advanced Percentile-Based Player Filtering =====
    ENABLE_ADVANCED_FILTERS = True  # Master switch for advanced filters

    # Rule 1: Avoid high bust + high ownership
    ENABLE_AVOID_HIGH_BUST_HIGH_OWN = True
    BUST_PERCENTILE_THRESHOLD = 0.8      # Top 20% bust
    OWNERSHIP_PERCENTILE_THRESHOLD = 0.8 # Top 20% ownership

    # Rule 2: Find high boom + low ownership
    ENABLE_FIND_HIGH_BOOM_LOW_OWN = True
    BOOM_PERCENTILE_THRESHOLD = 0.8      # Top 20% boom
    LOW_OWNERSHIP_PERCENTILE_THRESHOLD = 0.2 # Bottom 20% ownership

class PlayerProjectionTracker:
    """Tracks player projection history and provides statistics."""
    
    def __init__(self):
        self.player_history = {}
        self.current_iteration = 0
    
    def initialize_player(self, player):
        """Initialize tracking for a new player."""
        if player.name not in self.player_history:
            self.player_history[player.name] = {
                'projections': [],
                'current_projection': player.projection,
                'original_projection': player.projection
            }
    
    def update_player_projection(self, player):
        """Update the current projection for a player."""
        if player.name in self.player_history:
            self.player_history[player.name]['current_projection'] = player.current_projection
            self.player_history[player.name]['projections'].append(player.current_projection)
    
    def get_player_stats(self, player_name):
        """Get statistics for a specific player."""
        if player_name in self.player_history:
            history = self.player_history[player_name]
            projections = history['projections']
            if projections:
                return {
                    'mean': np.mean(projections),
                    'std': np.std(projections),
                    'min': np.min(projections),
                    'max': np.max(projections),
                    'count': len(projections)
                }
        return None

@dataclass
class Player:
    id: int
    name: str
    positions: List[str]
    team: str
    opponent: str
    salary: int
    projection: float
    ownership: float
    ceiling: float = 0.0  # Add ceiling field
    projection_floor: float = None  # 25th percentile projection
    projection_ceil: float = None  # 85th percentile projection
    std_dev: float = None  # Calculated standard deviation
    boom_probability: float = 0.0 # Probability of being a boom player
    bust_probability: float = 0.0 # Probability of being a bust player
    boom_probability_percentile: float = 0.0 # Percentile rank for boom probability
    bust_probability_percentile: float = 0.0 # Percentile rank for bust probability
    value: float = 0.0  # Value (points per dollar * 1000)

    def __post_init__(self):
        self.current_projection = self.projection  # Initialize current projection

class SmartRandomness:
    """Handles smart randomness for player projections using distribution data."""
    
    def __init__(self, distribution_type: str = "normal", seed: int = None):
        self.distribution_type = distribution_type
        self.rng = np.random.RandomState(seed) if seed is not None else np.random.RandomState()
        
    def calculate_std_dev(self, median: float, floor: float, ceil: float) -> float:
        """Calculate standard deviation from percentile data.
        
        For normal distribution:
        - 25th percentile = median - 0.6745 * std_dev
        - 85th percentile = median + 1.0364 * std_dev
        
        For lognormal distribution, we use the log-transformed values.
        """
        if self.distribution_type == "normal":
            # For normal distribution, use both percentiles to calculate std_dev
            # 25th percentile = median - 0.6745 * std_dev
            # 85th percentile = median + 1.0364 * std_dev
            # Calculate std_dev from both sides and average them for better accuracy
            std_dev_from_floor = (median - floor) / 0.6745
            std_dev_from_ceil = (ceil - median) / 1.0364
            std_dev = (std_dev_from_floor + std_dev_from_ceil) / 2
        else:  # lognormal
            # For lognormal, we need to work with log-transformed values
            log_median = np.log(median)
            log_floor = np.log(floor)
            log_ceil = np.log(ceil)
            
            # Calculate std_dev of the log-transformed distribution using both percentiles
            std_dev_from_floor = (log_median - log_floor) / 0.6745
            std_dev_from_ceil = (log_ceil - log_median) / 1.0364
            std_dev = (std_dev_from_floor + std_dev_from_ceil) / 2
            
        return max(std_dev, 0.1)  # Ensure minimum std_dev to avoid division by zero
    
    def generate_random_projection(self, player: Player) -> float:
        """Generate a random projection based on the player's distribution."""
        if not player.std_dev:
            return player.projection
        
        if self.distribution_type == "normal":
            # Generate random value from normal distribution using full std_dev
            random_factor = self.rng.normal(0, 1)
            adjusted_projection = player.projection + (random_factor * player.std_dev)
            
        else:  # lognormal
            # Generate random value from lognormal distribution using full std_dev
            log_median = np.log(player.projection)
            random_factor = self.rng.normal(0, 1)
            log_adjusted = log_median + (random_factor * player.std_dev)
            adjusted_projection = np.exp(log_adjusted)
        
        # Ensure the projection stays within reasonable bounds
        min_projection = max(player.projection_floor * 0.5, 0.1) if player.projection_floor else 0.1
        max_projection = player.projection_ceil if player.projection_ceil else player.projection * 1.5
        
        return np.clip(adjusted_projection, min_projection, max_projection)
    
    def apply_smart_randomness(self, players: List[Player]) -> None:
        """Apply smart randomness to all players' current projections."""
        for player in players:
            if player.std_dev:
                player.current_projection = self.generate_random_projection(player)



@dataclass
class Lineup:
    players: List[Dict]
    
    @property
    def lineup(self):
        """Convert our players to the correct FanDuel NBA classic order."""
        fd_position_order = ['PG', 'PG', 'SG', 'SG', 'SF', 'SF', 'PF', 'PF', 'C']
        # Create a mapping of positions to players
        position_map = {pos: [] for pos in ['PG', 'SG', 'SF', 'PF', 'C']}
        for player in self.players:
            position_map[player["Slot"]].append(player)
        ordered_players = []
        for pos in fd_position_order:
            if position_map[pos]:
                ordered_players.append(position_map[pos].pop(0))
        return ordered_players

def load_and_clean_data(file_path: str) -> pd.DataFrame:
    """Load and clean the player data from CSV file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data file not found: {file_path}")
    
    df = pd.read_csv(file_path)
    
    # Convert columns to appropriate types
    numeric_columns = ["FPPG", "Salary"]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # Add ceiling column if it doesn't exist
    if "Projection Ceil" not in df.columns:
        df["Projection Ceil"] = df["FPPG"] * 1.2  # Default ceiling as 120% of projection
    
    df["Position"] = df["Position"].astype(str)
    
    return df

def create_player_objects(df: pd.DataFrame) -> List[Player]:
    """Convert DataFrame rows to Player objects."""
    players = []
    
    # Initialize smart randomness for std_dev calculations
    smart_randomness = SmartRandomness(
        distribution_type=Config.DISTRIBUTION_TYPE,
        seed=Config.RANDOMNESS_SEED
    )
    
    for _, row in df.iterrows():
        positions = row["Position"].split("/")
        name = f"{row['First Name']} {row['Last Name']}"
        
        # Filter out players with projection under MIN_PROJECTION
        projection = round(row["FPPG"], 2)
        if projection < Config.MIN_PROJECTION:
            continue
        
        # Calculate value (points per dollar * 1000) and filter if enabled
        value = (projection / row["Salary"]) * 1000
        if Config.ENABLE_VALUE_FILTER and value < Config.MIN_VALUE:
            continue
        
        # Get projection data
        projection_floor = row.get("Projection Floor", projection)
        projection_ceil = row.get("Projection Ceil", projection)
        
        # Calculate standard deviation if we have floor and ceil data
        std_dev = None
        if pd.notna(projection_floor) and pd.notna(projection_ceil) and projection_floor != projection_ceil:
            std_dev = smart_randomness.calculate_std_dev(projection, projection_floor, projection_ceil)
        
        # Get ceiling value (use projection_ceil if available, otherwise 120% of projection)
        ceiling = projection_ceil if pd.notna(projection_ceil) else projection * 1.2
        
        # Get boom and bust probabilities
        boom = row.get("Boom Probability", 0)
        bust = row.get("Bust Probability", 0)
        
        players.append(Player(
            id=row["Id"],
            name=name,
            positions=positions,
            team=row["Team"],
            opponent=row["Opponent"],
            salary=int(row["Salary"]),
            projection=projection,
            ownership=float(row.get("Projected Ownership", 0)),
            ceiling=ceiling,
            projection_floor=projection_floor,
            projection_ceil=projection_ceil,
            std_dev=std_dev,
            boom_probability=boom,
            bust_probability=bust,
            value=value
        ))
    
    # Assign percentiles for boom and bust
    if players:
        boom_values = np.array([p.boom_probability for p in players])
        bust_values = np.array([p.bust_probability for p in players])
        for p in players:
            p.boom_probability_percentile = np.sum(boom_values <= p.boom_probability) / len(boom_values)
            p.bust_probability_percentile = np.sum(bust_values <= p.bust_probability) / len(bust_values)
    
    return players

def create_lineup_model(players: List[Player], 
                       teams: List[str],
                       used_lineups_sets: List[Set[int]],
                       num_generated_lineups: int) -> Tuple[cp_model.CpModel, Dict]:
    """Create the constraint programming model for lineup optimization."""
    model = cp_model.CpModel()
    
    # Create player variables
    player_vars = {p.id: model.NewBoolVar(f"player_{p.id}") for p in players}
    assign = {}
    
    # Create assignment variables with FILLER/CORE logic
    for p in players:
        assign[p.id] = {}
        for slot in Config.SLOTS:
            player_name = p.name.split(":")[-1].strip()
            # If FILLER_PLAYERS is empty for all positions, allow any eligible player
            if not any(Config.FILLER_PLAYERS.values()):
                can_play = slot in p.positions
            else:
                is_core = player_name in Config.CORE_PLAYERS
                is_filler = player_name in Config.FILLER_PLAYERS.get(slot, [])
                can_play = slot in p.positions and (is_core or is_filler)
            if can_play:
                assign[p.id][slot] = model.NewBoolVar(f"assign_{p.id}_{slot}")
    
    # Add roster constraints
    for slot, count in Config.SLOTS.items():
        model.Add(sum(assign[p.id][slot] for p in players if slot in assign[p.id]) == count)
    
    for p in players:
        model.Add(sum(assign[p.id][s] for s in assign[p.id]) <= 1)
        model.Add(sum(assign[p.id][s] for s in assign[p.id]) == player_vars[p.id])
    
    # Exclude specific players
    for p in players:
        if p.name.split(":")[-1].strip() in Config.EXCLUDED_PLAYERS:
            model.Add(player_vars[p.id] == 0)
    
    # Core players: must use at least MIN_CORE_PLAYERS (only if CORE_PLAYERS is not empty)
    if Config.CORE_PLAYERS:  # Only apply constraint if CORE_PLAYERS list is not empty
        core_player_vars = []
        for p in players:
            if p.name.split(":")[-1].strip() in Config.CORE_PLAYERS:
                core_player_vars.append(player_vars[p.id])
        if core_player_vars:
            model.Add(sum(core_player_vars) >= Config.MIN_CORE_PLAYERS)
    
    # Total players constraint
    model.Add(sum(player_vars[p.id] for p in players) == 9)  # 9 players in classic lineup
    
    # Salary constraints
    model.Add(sum(p.salary * player_vars[p.id] for p in players) <= Config.MAX_SALARY)
    model.Add(sum(p.salary * player_vars[p.id] for p in players) >= Config.MIN_SALARY)
    
    # Team constraints (max 4 per team)
    for team in teams:
        if team not in Config.EXCLUDED_TEAMS:
            team_players = [p for p in players if p.team == team]
            model.Add(sum(player_vars[p.id] for p in team_players) <= Config.MAX_PLAYERS_PER_TEAM)
    
    # At least 3 unique teams in the lineup
    team_used_vars = {}
    for team in teams:
        team_players = [p for p in players if p.team == team]
        team_used = model.NewBoolVar(f"team_used_{team}")
        # If any player from this team is used, team_used is 1
        model.AddMaxEquality(team_used, [player_vars[p.id] for p in team_players])
        team_used_vars[team] = team_used
    model.Add(sum(team_used_vars[team] for team in teams) >= 3)
    
    # Uniqueness constraint: ensure at least 1 unique player between lineups
    for prev in used_lineups_sets:
        # Count how many players are in common with this previous lineup
        common_players = sum(player_vars[pid] for pid in prev if pid in player_vars)
        
        # Force at least 1 unique player (max 8 common players)
        model.Add(common_players <= 8)
    
    # Advanced Percentile-Based Constraints
    if Config.ENABLE_ADVANCED_FILTERS:
        # At least 2 BOOM players
        if Config.ENABLE_FIND_HIGH_BOOM_LOW_OWN:
            boom_player_vars = [player_vars[p.id] for p in players if hasattr(p, 'boom_probability_percentile') and p.boom_probability_percentile >= Config.BOOM_PERCENTILE_THRESHOLD]
            if boom_player_vars:
                model.Add(sum(boom_player_vars) >= 2)
        # At most 1 BUST player
        if Config.ENABLE_AVOID_HIGH_BUST_HIGH_OWN:
            bust_player_vars = [player_vars[p.id] for p in players if hasattr(p, 'bust_probability_percentile') and p.bust_probability_percentile >= Config.BUST_PERCENTILE_THRESHOLD]
            if bust_player_vars:
                model.Add(sum(bust_player_vars) <= 1)
    
    # Set objective using current_projection
    model.Maximize(sum(p.current_projection * player_vars[p.id] for p in players))
    
    return model, {
        "player_vars": player_vars,
        "assign": assign
    }

def solve_lineup(model: cp_model.CpModel,
                players: List[Player],
                teams: List[str],
                variables: Dict) -> Optional[Lineup]:
    """Solve the lineup optimization model and return the solution if found."""
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return None
    
    lineup = []
    
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
                "current_projection": p.current_projection,
                "Ownership": p.ownership,
                "Ceiling": p.ceiling,
                "Value": p.value,
                "Id": p.id
            })
    
    return Lineup(lineup)

def print_lineup(lineup: Lineup, lineup_num: int, show_current_projections: bool = False) -> None:
    """Print the lineup in a formatted way."""
    print(f"=== Lineup {lineup_num} ===")
    
    # Sort players by slot order
    slot_order = {"PG": 0, "SG": 1, "SF": 2, "PF": 3, "C": 4}
    sorted_players = sorted(lineup.players, key=lambda x: slot_order[x["Slot"]])
    
    for player in sorted_players:
        player_name = player['Name'].split(":")[-1].strip()
        is_core = player_name in Config.CORE_PLAYERS
        core_indicator = " [CORE]" if is_core else ""
        proj_str = f" | Proj: {player['current_projection']:.2f}"
        if show_current_projections and player['current_projection'] != player['Projection']:
            proj_str += f" (Original: {player['Projection']:.2f})"
            # Show if this is due to smart randomness
            if Config.ENABLE_SMART_RANDOMNESS and abs(player['current_projection'] - player['Projection']) > 0.01:
                proj_str += " [Smart Random]"
        ceiling_str = f" | Ceiling: {player['Ceiling']:.2f}"
        ownership_str = f" | Own: {player['Ownership']:.1%}" if player['Ownership'] > 0 else ""
        value_str = f" | Value: {player['Value']:.2f}" if 'Value' in player else ""
        print(f"{player['Slot']}: {player['Name']}{core_indicator} ({player['Team']}) | Salary: ${player['Salary']}{proj_str}{ceiling_str}{ownership_str}{value_str}")
    
    total_salary = sum(p['Salary'] for p in lineup.players)
    total_original_projection = sum(p['Projection'] for p in lineup.players)
    total_current_projection = sum(p['current_projection'] for p in lineup.players)
    total_ceiling = sum(p['Ceiling'] for p in lineup.players)
    
    # Calculate product of ownership
    product_ownership = 1.0
    for p in lineup.players:
        ownership = p['Ownership'] if p['Ownership'] else 1.0
        product_ownership *= ownership
    
    print(f"\nTotal Salary: ${total_salary}")
    print(f"Total Original Projection: {total_original_projection:.2f}")
    if show_current_projections:
        print(f"Total Current Projection: {total_current_projection:.2f}")
    print(f"Total Ceiling: {total_ceiling:.2f}")
    print(f"Product Ownership: {product_ownership:.6f}")

def export_lineups(lineups: List[Lineup], output_path: str) -> None:
    """Export lineups to CSV in the requested format similar to NHL optimizer."""
    if not lineups:
        print("No lineups to export")
        return
    
    slot_names = ["PG1", "PG2", "SG1", "SG2", "SF1", "SF2", "PF1", "PF2", "C"]
    data = []
    
    for i, lineup in enumerate(lineups, 1):
        # Assign players to slots
        point_guards = [p for p in lineup.players if p["Slot"] == "PG"]
        shooting_guards = [p for p in lineup.players if p["Slot"] == "SG"]
        small_forwards = [p for p in lineup.players if p["Slot"] == "SF"]
        power_forwards = [p for p in lineup.players if p["Slot"] == "PF"]
        centers = [p for p in lineup.players if p["Slot"] == "C"]
        
        # Sort by projection for better assignment
        point_guards.sort(key=lambda p: p["current_projection"], reverse=True)
        shooting_guards.sort(key=lambda p: p["current_projection"], reverse=True)
        small_forwards.sort(key=lambda p: p["current_projection"], reverse=True)
        power_forwards.sort(key=lambda p: p["current_projection"], reverse=True)
        centers.sort(key=lambda p: p["current_projection"], reverse=True)
        
        row = {"Lineup": i}
        
        # Assign to slots with both ID and Name
        slot_assignments = {
            "PG1": f"{point_guards[0]['Id']}: {point_guards[0]['Name']}" if len(point_guards) > 0 else "",
            "PG2": f"{point_guards[1]['Id']}: {point_guards[1]['Name']}" if len(point_guards) > 1 else "",
            "SG1": f"{shooting_guards[0]['Id']}: {shooting_guards[0]['Name']}" if len(shooting_guards) > 0 else "",
            "SG2": f"{shooting_guards[1]['Id']}: {shooting_guards[1]['Name']}" if len(shooting_guards) > 1 else "",
            "SF1": f"{small_forwards[0]['Id']}: {small_forwards[0]['Name']}" if len(small_forwards) > 0 else "",
            "SF2": f"{small_forwards[1]['Id']}: {small_forwards[1]['Name']}" if len(small_forwards) > 1 else "",
            "PF1": f"{power_forwards[0]['Id']}: {power_forwards[0]['Name']}" if len(power_forwards) > 0 else "",
            "PF2": f"{power_forwards[1]['Id']}: {power_forwards[1]['Name']}" if len(power_forwards) > 1 else "",
            "C": f"{centers[0]['Id']}: {centers[0]['Name']}" if len(centers) > 0 else ""
        }
        
        for slot in slot_names:
            row[slot] = slot_assignments[slot]
        
        # Summary columns
        row["Total_Projection"] = sum(p["Projection"] for p in lineup.players)
        row["Total_Salary"] = sum(p["Salary"] for p in lineup.players)
        row["Total_Ceiling"] = sum(p["Ceiling"] for p in lineup.players)
        
        # Calculate product of ownership
        product_ownership = 1.0
        for p in lineup.players:
            ownership = p["Ownership"] if p["Ownership"] else 1.0
            product_ownership *= ownership
        row["Product_Ownership"] = product_ownership
        
        data.append(row)
    
    # Create DataFrame
    columns = ["Lineup"] + slot_names + [
        "Total_Projection", "Total_Salary", "Total_Ceiling", "Product_Ownership"
    ]
    df = pd.DataFrame(data, columns=columns)
    
    # Add rankings
    df["Projection_Rank"] = df["Total_Projection"].rank(ascending=False, method="min")
    df["Ceiling_Rank"] = df["Total_Ceiling"].rank(ascending=False, method="min")
    df["Ownership_Rank"] = df["Product_Ownership"].rank(ascending=True, method="min")
    df["Average"] = df[["Projection_Rank", "Ceiling_Rank", "Ownership_Rank"]].mean(axis=1)
    
    # Add standardized columns
    for col, zcol, invert in [
        ("Total_Projection", "Projection_Z", False),
        ("Total_Ceiling", "Ceiling_Z", False),
        ("Product_Ownership", "Ownership_Z", True)
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
    
    # Sort by average rank and filter top 150
    df = df.sort_values("Average", ascending=True).reset_index(drop=True)
    df = df.head(Config.TOP_LINEUPS_TO_EXPORT)  # Filter to top 150 lineups
    
    # Reorder columns
    columns += ["Projection_Rank", "Ceiling_Rank", "Ownership_Rank", "Average",
                "Projection_Z", "Ceiling_Z", "Ownership_Z"]
    df = df[columns]
    
    df.to_csv(output_path, index=False)
    print(f"Exported top {Config.TOP_LINEUPS_TO_EXPORT} lineups to {output_path}")

def main():
    """Main function to run the lineup optimizer."""
    try:
        # Load and process data
        df = load_and_clean_data(Config.DATA_FILE)
        original_count = len(df)
        players = create_player_objects(df)
        filtered_count = len(players)
        teams = list(set(p.team for p in players))
        
        # Print filtering statistics
        print(f"Data loaded: {original_count} total players")
        print(f"After filtering: {filtered_count} players")
        if Config.ENABLE_VALUE_FILTER:
            print(f"Value filter applied: minimum value = {Config.MIN_VALUE}")
        print(f"Teams in pool: {len(teams)}")
        print()
        
        # Initialize tracking variables
        generated_lineups = []
        used_lineups_sets = []
        player_counts = {}  # Track player exposure
        projection_tracker = PlayerProjectionTracker()
        
        # Initialize smart randomness
        smart_randomness = None
        if Config.ENABLE_SMART_RANDOMNESS:
            smart_randomness = SmartRandomness(
                distribution_type=Config.DISTRIBUTION_TYPE,
                seed=Config.RANDOMNESS_SEED
            )
            
            # Apply smart randomness once at the start if frequency is per_session
            if Config.RANDOMNESS_FREQUENCY == "per_session":
                smart_randomness.apply_smart_randomness(players)
        
        attempt = 0
        
        # Initialize projections for all players
        for player in players:
            projection_tracker.initialize_player(player)
            player_counts[player.name] = 0  # Initialize player counts
        
        # Generate lineups
        while (len(generated_lineups) < Config.NUM_LINEUPS_TO_GENERATE and 
               attempt < Config.MAX_ATTEMPTS):
            attempt += 1
            
            # Apply smart randomness to player projections if enabled
            if smart_randomness and Config.RANDOMNESS_FREQUENCY == "per_lineup":
                smart_randomness.apply_smart_randomness(players)
            
            # Create and solve model
            model, variables = create_lineup_model(
                players, teams, used_lineups_sets, len(generated_lineups)
            )
            
            lineup = solve_lineup(model, players, teams, variables)
            if not lineup:
                continue
            
            # Update player counts
            for player in lineup.players:
                player_name = player["Name"].split(":")[-1].strip()
                player_counts[player_name] = player_counts.get(player_name, 0) + 1
            
            generated_lineups.append(lineup)
            used_lineups_sets.append(set(p["Id"] for p in lineup.players))
            
            # Print lineup
            print_lineup(lineup, len(generated_lineups))
            
            # Print exposure statistics
            if len(generated_lineups) % 10 == 0:
                print("\nCurrent Exposure Statistics:")
                print("Player Exposure:")
                for player, count in sorted(player_counts.items(), key=lambda x: x[1], reverse=True):
                    if count > 0:  # Only show players that were used
                        exposure = count / len(generated_lineups)
                        print(f"{player}: {count} ({exposure:.1%})")
                print()
        
        print(f"\nGenerated {len(generated_lineups)} lineups in {attempt} attempts")
        
        # Print final exposure statistics
        print("\nFinal Exposure Statistics:")
        print("Player Exposure:")
        for player, count in sorted(player_counts.items(), key=lambda x: x[1], reverse=True):
            if count > 0:  # Only show players that were used
                exposure = count / len(generated_lineups)
                print(f"{player}: {count} ({exposure:.1%})")
        
        # Export lineups
        output_path = "/Users/adamsardinha/Desktop/FD_NBA_Standard_Lineups.csv"
        export_lineups(generated_lineups, output_path)
        print(f"\nGenerated {len(generated_lineups)} total lineups, exported top {Config.TOP_LINEUPS_TO_EXPORT} ranked lineups to {output_path}")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main() 