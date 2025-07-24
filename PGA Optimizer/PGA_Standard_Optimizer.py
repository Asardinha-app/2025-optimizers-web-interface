"""
PGA Standard Daily Fantasy Sports Lineup Optimizer
This script generates optimized lineups for PGA standard DFS contests using constraint programming.

Features:
- Wave Stacking: When enabled, ensures at least 5 golfers from a specific wave (Early/Late or Late/Early)
- Top-3 Ownership Limit: Maximum 2 players from the top 3 owned players
- Lineup Diversity: Ensures at least 3 different players between lineups
- Salary Optimization: Optimizes for maximum projection within salary constraints
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
    DATA_FILE = "/Users/adamsardinha/Desktop/GOLF_FD.csv"
    
    # Lineup generation settings
    NUM_LINEUPS_TO_GENERATE = 1000
    MAX_SALARY = 60000  # FanDuel standard salary cap
    MIN_SALARY = 59000  # Minimum salary to ensure quality lineups
    MAX_ATTEMPTS = 1000
    
    # Minimum projection to include a player in the pool
    MIN_PROJECTION = 1  # Adjust based on your scoring system
    
    # Roster settings for FanDuel PGA classic contests
    SLOTS = {
        "G": 6  # Need 6 golfers
    }
    
    # Players to exclude from lineups
    EXCLUDED_PLAYERS = [
        # Add players to exclude here
    ]
    
    # Wave Stacking Configuration
    ENABLE_WAVE_STACKING = True  # Set to True to enable wave stacking
    MIN_WAVE_PLAYERS = 5  # Minimum number of players from the same wave (Early/Late or Late/Early)
    TARGET_WAVE = "Early/Late"  # Specify which wave to stack: "Early/Late", "Late/Early", or None for any wave

@dataclass
class Player:
    id: int
    name: str
    positions: List[str]
    salary: int
    projection: float
    ownership: float
    wave: str = None  # Wave information (Early/Late or Late/Early)
    current_projection: float = None  # Current adjusted projection
    is_top_owned: bool = False  # Flag for top-3 owned players

    def __post_init__(self):
        self.current_projection = self.projection  # Initialize current projection

class PlayerProjectionTracker:
    def __init__(self):
        self.player_history: Dict[int, List[bool]] = {}  # Tracks player usage in recent lineups
        self.original_projections: Dict[int, float] = {}  # Stores original projections
        
    def initialize_player(self, player: Player):
        """Initialize tracking for a new player."""
        if player.id not in self.player_history:
            self.player_history[player.id] = []
            self.original_projections[player.id] = player.projection
            player.current_projection = player.projection
    
    def update_projection(self, player: Player, used_in_lineup: bool):
        """Update a player's projection based on usage."""
        self.initialize_player(player)
        
        # Keep history limited to recent lineups
        if len(self.player_history[player.id]) > 10:  # Keep last 10 lineups of history
            self.player_history[player.id].pop(0)
        
        self.player_history[player.id].append(used_in_lineup)

@dataclass
class Lineup:
    players: List[Dict]
    
    @property
    def lineup(self):
        """Convert our players to the correct FanDuel PGA order."""
        return sorted(self.players, key=lambda x: (-x["current_projection"], x["Name"]))

def load_and_clean_data(file_path: str) -> pd.DataFrame:
    """Load and clean the player data from CSV file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data file not found: {file_path}")
    
    df = pd.read_csv(file_path)
    
    # Convert columns to appropriate types
    numeric_columns = ["FPPG", "Salary"]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    df["Position"] = df["Position"].astype(str)
    
    # Handle Wave column if it exists
    if "Wave" in df.columns:
        df["Wave"] = df["Wave"].astype(str)
    else:
        # If Wave column doesn't exist, create a default one
        df["Wave"] = "Unknown"
    
    return df

def create_player_objects(df: pd.DataFrame) -> List[Player]:
    """Convert DataFrame rows to Player objects."""
    players = []
    for _, row in df.iterrows():
        name = f"{row['First Name']} {row['Last Name']}"
        
        # Filter out players with projection under MIN_PROJECTION
        projection = round(row["FPPG"], 2)
        if projection < Config.MIN_PROJECTION:
            continue
        
        # Convert ownership to decimal if it's a percentage
        ownership = float(row.get("Projected Ownership", 0))
        # Ownership values are already in decimal format (e.g., 40.06 = 40.06%)
        # No need to divide by 100 since they're not percentages
        
        # Get wave information
        wave = row.get("Wave", "Unknown")
        
        players.append(Player(
            id=row["Id"],
            name=name,
            positions=["G"],  # All players are golfers
            salary=int(row["Salary"]),
            projection=projection,
            ownership=ownership,
            wave=wave
        ))
    
    # Sort players by ownership and mark top 3
    players.sort(key=lambda x: x.ownership, reverse=True)
    for i, player in enumerate(players):
        player.is_top_owned = i < 3
    
    return players

def create_lineup_model(players: List[Player], 
                       used_lineups_sets: List[Set[int]],
                       num_generated_lineups: int) -> Tuple[cp_model.CpModel, Dict]:
    """Create the constraint programming model for lineup optimization."""
    model = cp_model.CpModel()
    
    # Create player variables
    player_vars = {p.id: model.NewBoolVar(f"player_{p.id}") for p in players}
    
    # Total players constraint (need exactly 6 golfers)
    model.Add(sum(player_vars[p.id] for p in players) == 6)
    
    # Salary constraints
    model.Add(sum(p.salary * player_vars[p.id] for p in players) <= Config.MAX_SALARY)
    model.Add(sum(p.salary * player_vars[p.id] for p in players) >= Config.MIN_SALARY)
    
    # Exclude specific players
    for p in players:
        if p.name.split(":")[-1].strip() in Config.EXCLUDED_PLAYERS:
            model.Add(player_vars[p.id] == 0)
    
    # Identify the top 3 owned players from the entire pool
    sorted_by_ownership = sorted(players, key=lambda x: x.ownership, reverse=True)
    top_3_owned_ids = {p.id for p in sorted_by_ownership[:3]}
    
    # Constraint: maximum 2 players from top 3 owned
    top_3_vars = [player_vars[p_id] for p_id in top_3_owned_ids]
    model.Add(sum(top_3_vars) <= 2)
    
    # Wave Stacking Constraints (if enabled)
    if Config.ENABLE_WAVE_STACKING:
        # Get unique waves in the player pool
        waves = list(set(p.wave for p in players if p.wave and p.wave != "Unknown"))
        
        if waves:
            # Create variables for each wave to track how many players are selected from each wave
            wave_vars = {}
            for wave in waves:
                wave_players = [p for p in players if p.wave == wave]
                wave_vars[wave] = sum(player_vars[p.id] for p in wave_players)
            
            if Config.TARGET_WAVE and Config.TARGET_WAVE in waves:
                # Stack specific target wave
                target_wave_players = [p for p in players if p.wave == Config.TARGET_WAVE]
                target_wave_var = sum(player_vars[p.id] for p in target_wave_players)
                model.Add(target_wave_var >= Config.MIN_WAVE_PLAYERS)
            else:
                # Constraint: At least MIN_WAVE_PLAYERS from one of the waves
                # We need to ensure that at least one wave has MIN_WAVE_PLAYERS or more
                wave_constraints = []
                for wave, wave_var in wave_vars.items():
                    # Create a boolean variable that is 1 if this wave has enough players
                    wave_sufficient = model.NewBoolVar(f"wave_sufficient_{wave}")
                    model.Add(wave_var >= Config.MIN_WAVE_PLAYERS).OnlyEnforceIf(wave_sufficient)
                    model.Add(wave_var < Config.MIN_WAVE_PLAYERS).OnlyEnforceIf(wave_sufficient.Not())
                    wave_constraints.append(wave_sufficient)
                
                # At least one wave must be sufficient
                model.Add(sum(wave_constraints) >= 1)
    
    # Uniqueness constraint: ensure at least 3 different players between lineups
    for prev in used_lineups_sets:
        # Create a variable for each previous lineup to track if this lineup is different enough
        is_different = model.NewBoolVar(f"is_different_{len(used_lineups_sets)}")
        
        # Count how many players are in common with this previous lineup
        common_players = sum(player_vars[pid] for pid in prev if pid in player_vars)
        
        # We want at most 3 players in common (meaning at least 3 different)
        # Since we have 6 total players, if we have at most 3 in common,
        # that guarantees at least 3 different players
        model.Add(common_players <= 3).OnlyEnforceIf(is_different)
        model.Add(common_players > 3).OnlyEnforceIf(is_different.Not())
        
        # Force this lineup to be different enough from all previous lineups
        model.Add(is_different == 1)
    
    # Set objective using current_projection
    model.Maximize(sum(p.current_projection * player_vars[p.id] for p in players))
    
    return model, {
        "player_vars": player_vars,
        "top_3_owned_ids": top_3_owned_ids
    }

def solve_lineup(model: cp_model.CpModel,
                players: List[Player],
                variables: Dict) -> Optional[Lineup]:
    """Solve the lineup optimization model and return the solution if found."""
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        return None
    
    lineup = []
    top_3_owned_ids = variables["top_3_owned_ids"]
    
    # Get players in lineup
    for p in players:
        if solver.Value(variables["player_vars"][p.id]):
            lineup.append({
                "Name": p.name,
                "Salary": p.salary,
                "Projection": p.projection,
                "current_projection": p.current_projection,
                "Ownership": p.ownership,
                "Id": p.id,
                "is_top_3": p.id in top_3_owned_ids,
                "wave": p.wave
            })
    
    return Lineup(lineup)

def print_lineup(lineup: Lineup, lineup_num: int, show_current_projections: bool = False) -> None:
    """Print the lineup in a formatted way."""
    print(f"=== Lineup {lineup_num} ===")
    
    # Sort players by projection
    sorted_players = sorted(lineup.players, key=lambda x: (-x["current_projection"], x["Name"]))
    
    # Count how many top-3 owned players are in the lineup
    top_3_count = sum(1 for p in lineup.players if p["is_top_3"])
    
    # Count players by wave
    wave_counts = {}
    for player in lineup.players:
        wave = player.get("wave", "Unknown")
        wave_counts[wave] = wave_counts.get(wave, 0) + 1
    
    for player in sorted_players:
        player_name = player['Name'].split(":")[-1].strip()
        proj_str = f" | Proj: {player['current_projection']:.2f}"
        if show_current_projections and player['current_projection'] != player['Projection']:
            proj_str += f" (Original: {player['Projection']:.2f})"
        ownership_str = f" | Own: {player['Ownership']:.1f}%"
        wave_str = f" | Wave: {player.get('wave', 'Unknown')}"
        
        # Mark as top 3 based on the flag we set during solve
        top_owned_indicator = " [TOP 3 OWNED]" if player["is_top_3"] else ""
            
        print(f"G: {player['Name']} | Salary: ${player['Salary']}{proj_str}{ownership_str}{wave_str}{top_owned_indicator}")
    
    total_salary = sum(p['Salary'] for p in lineup.players)
    total_original_projection = sum(p['Projection'] for p in lineup.players)
    total_current_projection = sum(p['current_projection'] for p in lineup.players)
    avg_ownership = sum(p['Ownership'] for p in lineup.players) / len(lineup.players)
    print(f"\nTotal Salary: ${total_salary}")
    print(f"Total Original Projection: {total_original_projection:.2f}")
    print(f"Total Current Projection: {total_current_projection:.2f}")
    print(f"Average Ownership: {avg_ownership:.1f}%")
    print(f"Number of Top-3 Owned Players: {top_3_count}")
    
    # Print wave distribution
    if Config.ENABLE_WAVE_STACKING:
        print("Wave Distribution:")
        for wave, count in sorted(wave_counts.items()):
            target_indicator = " (TARGET)" if wave == Config.TARGET_WAVE else ""
            print(f"  {wave}: {count} players{target_indicator}")

def export_to_csv(lineups: List[Lineup], output_path: str) -> None:
    """Export lineups to a CSV file in FanDuel format."""
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['G', 'G', 'G', 'G', 'G', 'G'])  # Header row with 6 golfer slots
        for lineup in lineups:
            # Sort by projection and get IDs
            sorted_players = sorted(lineup.players, key=lambda x: (-x["current_projection"], x["Name"]))
            row = [player["Id"] for player in sorted_players]
            writer.writerow(row)

def main():
    """Main function to run the lineup optimizer."""
    try:
        # Load and process data
        df = load_and_clean_data(Config.DATA_FILE)
        players = create_player_objects(df)
        
        # Debug: Show top 3 owned players
        sorted_by_ownership = sorted(players, key=lambda x: x.ownership, reverse=True)
        print("Top 3 owned players in the pool:")
        for i, player in enumerate(sorted_by_ownership[:3]):
            print(f"{i+1}. {player.name}: {player.ownership:.1f}%")
        print()
        
        # Debug: Show wave information if wave stacking is enabled
        if Config.ENABLE_WAVE_STACKING:
            waves = list(set(p.wave for p in players if p.wave and p.wave != "Unknown"))
            print(f"Wave Stacking Enabled - Minimum {Config.MIN_WAVE_PLAYERS} players per wave")
            if Config.TARGET_WAVE:
                print(f"Target Wave: {Config.TARGET_WAVE}")
            else:
                print("Target Wave: Any wave (will stack whichever wave has the best projection)")
            print("Available waves in the pool:")
            for wave in waves:
                wave_players = [p for p in players if p.wave == wave]
                print(f"  {wave}: {len(wave_players)} players")
            print()
        
        # Initialize tracking variables
        generated_lineups = []
        used_lineups_sets = []
        player_counts = {}  # Track player exposure
        attempt = 0
        
        # Initialize player counts
        for player in players:
            player_counts[player.name] = 0  # Initialize player counts
        
        # Generate lineups
        while (len(generated_lineups) < Config.NUM_LINEUPS_TO_GENERATE and 
               attempt < Config.MAX_ATTEMPTS):
            attempt += 1
            
            # Create and solve model
            model, variables = create_lineup_model(
                players, used_lineups_sets, len(generated_lineups)
            )
            
            lineup = solve_lineup(model, players, variables)
            if not lineup:
                continue
            
            # Update player counts
            for player in lineup.players:
                player_name = player["Name"]
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
        output_path = "/Users/adamsardinha/Desktop/FD_PGA_Standard_Lineups.csv"
        export_to_csv(generated_lineups, output_path)
        print(f"\nExported lineups to {output_path}")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main() 