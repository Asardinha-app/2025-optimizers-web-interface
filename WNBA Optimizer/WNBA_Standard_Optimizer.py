"""
WNBA Standard Daily Fantasy Sports Lineup Optimizer
This script generates optimized lineups for WNBA standard DFS contests using constraint programming.
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
    DATA_FILE = "/Users/adamsardinha/Desktop/WNBA_Standard_FD.csv"
    
    # Lineup generation settings
    NUM_LINEUPS_TO_GENERATE = 500
    TOP_LINEUPS_TO_EXPORT = 143  # Number of top ranked lineups to export
    MAX_SALARY = 40000  # FanDuel WNBA standard salary cap
    MIN_SALARY = 39200  # Minimum salary to ensure quality lineups
    MAX_ATTEMPTS = 500
    
    # Minimum projection to include a player in the pool
    MIN_PROJECTION = 10  # Lower threshold for WNBA
    
    # Stack rules
    ENABLED_STACK_RULES = False
    MAX_PLAYERS_PER_TEAM = 4  # Maximum players from one team
    
    # Roster settings for FanDuel WNBA classic contests (7 players)
    SLOTS = {
        "G": 3,   # Guard (PG/SG)
        "F": 4    # Forward (SF/PF/C)
    }
    
    # Players to exclude from lineups
    EXCLUDED_PLAYERS = [
        # Add players to exclude here
    ]
    
    # Players that must be in every lineup
    CORE_PLAYERS = [
        # Add core WNBA players here
        # Example: "Breanna Stewart", "A'ja Wilson", "Elena Delle Donne"
    ]
    
    # Minimum number of core players that must be used in each lineup
    MIN_CORE_PLAYERS = 3  # Lower requirement for WNBA due to smaller player pool
    
    # Filler players for each position (if not a core player, only these can fill the slot)
    FILLER_PLAYERS = {
        # "G": ["Courtney Vandersloot", "Diana Taurasi", "Chelsea Gray"],
        # "F": ["Breanna Stewart", "A'ja Wilson", "Elena Delle Donne"]
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
    current_projection: float = None  # Current adjusted projection
    projection_floor: float = None  # 25th percentile projection
    projection_ceil: float = None  # 85th percentile projection
    std_dev: float = None  # Calculated standard deviation

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

class PlayerProjectionTracker:
    def __init__(self):
        self.original_projections: Dict[int, float] = {}  # Stores original projections
        
    def initialize_player(self, player: Player):
        """Initialize tracking for a new player."""
        if player.id not in self.original_projections:
            self.original_projections[player.id] = player.projection
            player.current_projection = player.projection
    
    def update_projection(self, player: Player, used_in_lineup: bool):
        """Update a player's projection - simplified without bounce/boost."""
        self.initialize_player(player)
        # Keep current projection as original projection
        player.current_projection = player.projection

@dataclass
class Lineup:
    players: List[Dict]
    
    @property
    def lineup(self):
        """Convert our players to the correct FanDuel WNBA classic order."""
        fd_position_order = ['G', 'G', 'G', 'F', 'F', 'F', 'F']
        # Create a mapping of positions to players
        position_map = {pos: [] for pos in ['G', 'F']}
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
        player_id_name = row["Player ID + Player Name"]  # Use the combined column
        
        # Filter out players with projection under MIN_PROJECTION
        projection = round(row["FPPG"], 2)
        if projection < Config.MIN_PROJECTION:
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
        

        
        players.append(Player(
            id=row["Id"],
            name=player_id_name,  # Use the combined ID + Name
            positions=positions,
            team=row["Team"],
            opponent=row["Opponent"],
            salary=int(row["Salary"]),
            projection=projection,
            ownership=float(row.get("Projected Ownership", 0)),
            ceiling=ceiling,
            projection_floor=projection_floor,
            projection_ceil=projection_ceil,
            std_dev=std_dev
        ))
    

    
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
            # Determine if player can play this slot
            if slot == "G":
                can_play = "G" in p.positions
            elif slot == "F":
                can_play = "F" in p.positions
            else:
                can_play = False
            
            # Apply FILLER_PLAYERS restriction if configured
            if any(Config.FILLER_PLAYERS.values()):
                player_name = p.name.split(":")[-1].strip()
                is_core = player_name in Config.CORE_PLAYERS
                is_filler = player_name in Config.FILLER_PLAYERS.get(slot, [])
                can_play = can_play and (is_core or is_filler)
            
            if can_play:
                assign[p.id][slot] = model.NewBoolVar(f"assign_{p.id}_{slot}")
    
    # Add roster constraints
    for slot, count in Config.SLOTS.items():
        available_players = sum(1 for p in players if slot in assign[p.id])
        print(f"Slot {slot}: {available_players} players available, need {count}")
        model.Add(sum(assign[p.id][slot] for p in players if slot in assign[p.id]) == count)
    
    for p in players:
        model.Add(sum(assign[p.id][s] for s in assign[p.id]) <= 1)
        model.Add(sum(assign[p.id][s] for s in assign[p.id]) == player_vars[p.id])
    
    # Exclude specific players
    for p in players:
        if p.name.split(":")[-1].strip() in Config.EXCLUDED_PLAYERS:
            model.Add(player_vars[p.id] == 0)
    
    # Core players: must use at least MIN_CORE_PLAYERS
    core_player_vars = []
    for p in players:
        if p.name.split(":")[-1].strip() in Config.CORE_PLAYERS:
            core_player_vars.append(player_vars[p.id])
    if core_player_vars:
        model.Add(sum(core_player_vars) >= Config.MIN_CORE_PLAYERS)
    else:
        # If no core players are defined, skip this constraint
        print("No core players defined, skipping core player constraint")
    
    # Total players constraint
    model.Add(sum(player_vars[p.id] for p in players) == 7)  # 7 players in WNBA classic lineup
    
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
        
        # Force at least 1 unique player (max 6 common players for 7-player lineups)
        model.Add(common_players <= 6)
    

    
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
        print(f"Solver status: {status}")
        if status == cp_model.INFEASIBLE:
            print("Model is infeasible - constraints cannot be satisfied")
        elif status == cp_model.MODEL_INVALID:
            print("Model is invalid")
        elif status == cp_model.UNKNOWN:
            print("Solver could not determine feasibility")
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
                "Id": p.id
            })
    
    return Lineup(lineup)

def print_lineup(lineup: Lineup, lineup_num: int, show_current_projections: bool = False) -> None:
    """Print the lineup in a formatted way."""
    print(f"=== Lineup {lineup_num} ===")
    
    # Sort players by slot order
    slot_order = {"G": 0, "F": 1}
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
        ownership_str = f" | Own: {player['Ownership']:.1f}%" if player['Ownership'] > 0 else ""
        print(f"{player['Slot']}: {player['Name']}{core_indicator} ({player['Team']}) | Salary: ${player['Salary']}{proj_str}{ceiling_str}{ownership_str}")
    
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
    
    slot_names = ["G1", "G2", "G3", "F1", "F2", "F3", "F4"]
    data = []
    
    for i, lineup in enumerate(lineups, 1):
        # Assign players to slots
        guards = [p for p in lineup.players if p["Slot"] == "G"]
        forwards = [p for p in lineup.players if p["Slot"] == "F"]
        
        # Sort by projection for better assignment
        guards.sort(key=lambda p: p["current_projection"], reverse=True)
        forwards.sort(key=lambda p: p["current_projection"], reverse=True)
        
        row = {}
        
        # Assign to slots
        slot_assignments = {
            "G1": guards[0]["Name"] if len(guards) > 0 else "",
            "G2": guards[1]["Name"] if len(guards) > 1 else "",
            "G3": guards[2]["Name"] if len(guards) > 2 else "",
            "F1": forwards[0]["Name"] if len(forwards) > 0 else "",
            "F2": forwards[1]["Name"] if len(forwards) > 1 else "",
            "F3": forwards[2]["Name"] if len(forwards) > 2 else "",
            "F4": forwards[3]["Name"] if len(forwards) > 3 else ""
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
    columns = slot_names + [
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
        ("Product_Ownership", "Ownership_Z", True)  # Invert so lower ownership gets positive Z-score
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
        print(f"Loading data from: {Config.DATA_FILE}")
        df = load_and_clean_data(Config.DATA_FILE)
        print(f"Loaded {len(df)} players from CSV")
        
        players = create_player_objects(df)
        print(f"Created {len(players)} player objects after filtering")
        
        teams = list(set(p.team for p in players))
        print(f"Found {len(teams)} teams: {teams}")
        
        # Debug: Check player distribution by position
        g_players = [p for p in players if "G" in p.positions]
        f_players = [p for p in players if "F" in p.positions]
        print(f"Guard players (G): {len(g_players)}")
        print(f"Forward players (F): {len(f_players)}")
        
        # Debug: Show first few players and their positions
        print("\nFirst 5 players and their positions:")
        for i, p in enumerate(players[:5]):
            print(f"  {p.name}: {p.positions} (Salary: ${p.salary}, Proj: {p.projection})")
        
        # Check salary distribution
        total_salary = sum(p.salary for p in players)
        avg_salary = total_salary / len(players) if players else 0
        print(f"Average salary: ${avg_salary:.0f}")
        print(f"Salary range: ${min(p.salary for p in players)} - ${max(p.salary for p in players)}")
        
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
            
            # Update player projections based on bounce
            lineup_player_ids = set(p["Id"] for p in lineup.players)
            for player in players:
                projection_tracker.update_projection(
                    player, 
                    used_in_lineup=(player.id in lineup_player_ids)
                )
            
            generated_lineups.append(lineup)
            used_lineups_sets.append(lineup_player_ids)
            
            # Print lineup with both original and current projections
            print_lineup(lineup, len(generated_lineups), show_current_projections=True)
            
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
        output_path = "/Users/adamsardinha/Desktop/FD_WNBA_Standard_Lineups.csv"
        export_lineups(generated_lineups, output_path)
        print(f"\nGenerated {len(generated_lineups)} total lineups, exported top {Config.TOP_LINEUPS_TO_EXPORT} ranked lineups to {output_path}")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main() 