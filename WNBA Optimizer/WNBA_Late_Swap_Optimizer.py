"""
WNBA Late Swap Optimizer
This script handles late swap optimization for WNBA DFS lineups, following the same logic as WNBA_Standard_Optimizer.py.
"""

from typing import List, Dict, Set, Optional, Tuple
import pandas as pd
from dataclasses import dataclass
from pathlib import Path
import csv
import os
from ortools.sat.python import cp_model
import numpy as np

class WNBA_LateSwapConfig:
    # File paths
    INPUT_LINEUP_FILE = "/Users/adamsardinha/Downloads/FanDuel-WNBA-2025-07-22-118733-entries-upload-template.csv"
    DATA_FILE = "/Users/adamsardinha/Desktop/WNBA_Standard_FD.csv"  # Same as WNBA_Standard_Optimizer
    OUTPUT_FILE = "/Users/adamsardinha/Desktop/FD_WNBA_Standard_Lineups_Swapped.csv"
    
    # Locked teams (teams whose games have started)
    LOCKED_TEAMS = {
"WAS", "LA","IND",'NY',"CHI","MIN"
    }
    
    # WNBA-specific settings (matching WNBA_Standard_Optimizer)
    MAX_SALARY = 40000  # FanDuel WNBA standard salary cap
    MIN_SALARY = 39200  # Minimum salary to ensure quality lineups
    MIN_PROJECTION = 10  # Minimum projection to include a player in the pool
    
    # Roster settings for FanDuel WNBA classic contests (7 players)
    SLOTS = {
        "G": 3,   # Guard (PG/SG)
        "F": 4    # Forward (SF/PF/C)
    }
    
    # Players to exclude from lineups
    EXCLUDED_PLAYERS = [
        # Add players to exclude here
    ]
    
    # Players that must be in every lineup (core players)
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
    
    # Stack rules
    ENABLED_STACK_RULES = False
    MAX_PLAYERS_PER_TEAM = 4  # Maximum players from one team
    
    # Smart Randomness settings
    ENABLE_SMART_RANDOMNESS = True  # Toggle smart randomness feature
    DISTRIBUTION_TYPE = "lognormal"  # "normal" or "lognormal"
    RANDOMNESS_SEED = None  # Set to an integer for reproducible results
    RANDOMNESS_FREQUENCY = "per_lineup"  # "per_lineup" or "per_session" (once at start)

@dataclass
class Player:
    id: str
    name: str
    positions: List[str]
    team: str
    opponent: str
    salary: int
    projection: float
    ownership: float
    current_projection: float = None  # Current adjusted projection
    is_locked: bool = False  # Whether player is locked (game started)
    status: str = ""  # Player status (OUT, QUESTIONABLE, etc.)
    projection_floor: float = None  # 25th percentile projection
    projection_ceil: float = None  # 85th percentile projection
    std_dev: float = None  # Calculated standard deviation
    
    def __post_init__(self):
        self.current_projection = self.projection  # Initialize current projection
    
    @property
    def can_be_swapped(self) -> bool:
        """Determine if player can be swapped based on team lock status."""
        return not self.is_locked and self.team not in WNBA_LateSwapConfig.LOCKED_TEAMS
    
    @property
    def is_core_player(self) -> bool:
        """Check if player is a core player."""
        player_name = self.name.split(":")[-1].strip()
        return player_name in WNBA_LateSwapConfig.CORE_PLAYERS
    
    @property
    def is_filler_player(self) -> bool:
        """Check if player is a filler player for any position."""
        player_name = self.name.split(":")[-1].strip()
        for position_players in WNBA_LateSwapConfig.FILLER_PLAYERS.values():
            if player_name in position_players:
                return True
        return False

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
        self.original_projections: Dict[str, float] = {}  # Stores original projections
        
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
    players: List[Player]
    total_salary: int
    total_projection: float
    
    @property
    def locked_players(self) -> List[Player]:
        """Get list of players that cannot be swapped."""
        return [p for p in self.players if not p.can_be_swapped]
    
    @property
    def swappable_players(self) -> List[Player]:
        """Get list of players that can be swapped."""
        return [p for p in self.players if p.can_be_swapped]
    
    @property
    def core_players(self) -> List[Player]:
        """Get list of core players in the lineup."""
        return [p for p in self.players if p.is_core_player]
    
    @property
    def core_player_count(self) -> int:
        """Get count of core players in the lineup."""
        return len(self.core_players)
    
    @property
    def has_out_players(self) -> bool:
        """Check if lineup contains any players marked as out."""
        for player in self.players:
            if player.status == "OUT":
                return True
        return False
    
    @property
    def out_players(self) -> List[Player]:
        """Get list of players marked as out."""
        return [p for p in self.players if p.status == "OUT"]
    
    @property
    def has_duplicate_players(self) -> bool:
        """Check if lineup contains duplicate players."""
        player_ids = [p.id for p in self.players]
        return len(player_ids) != len(set(player_ids))
    
    def get_duplicate_players(self) -> List[Player]:
        """Get list of duplicate players in the lineup."""
        player_ids = [p.id for p in self.players]
        seen_ids = set()
        duplicates = []
        for player in self.players:
            if player.id in seen_ids:
                duplicates.append(player)
            else:
                seen_ids.add(player.id)
        return duplicates

class WNBALateSwapOptimizer:
    def __init__(self):
        self.config = WNBA_LateSwapConfig()
        self.original_lineups: List[Lineup] = []
        self.available_players: Dict[str, Player] = {}  # id -> Player mapping
        self.player_data: pd.DataFrame = None
        self.projection_tracker = PlayerProjectionTracker()
        self.swapped_lineups: List[Lineup] = []
        self.unswappable_lineups: List[Tuple[int, Lineup]] = []  # [(index, lineup), ...]
        self.skipped_no_change_lineups: List[Tuple[int, Lineup]] = []  # [(index, lineup), ...] - no projection change
        self.zero_removal_swaps: List[Tuple[int, Lineup]] = []  # [(index, lineup), ...] - removed all 0-projection players
        self.zero_reduction_swaps: List[Tuple[int, Lineup]] = []  # [(index, lineup), ...] - reduced 0-projection players
        self.smart_randomness = SmartRandomness(
            distribution_type=self.config.DISTRIBUTION_TYPE,
            seed=self.config.RANDOMNESS_SEED
        )
    
    def load_player_data(self) -> None:
        """Load player data from CSV file."""
        print(f"Loading player data from: {self.config.DATA_FILE}")
        df = pd.read_csv(self.config.DATA_FILE)
        print(f"Data file has {len(df)} rows")
        
        for idx, row in df.iterrows():
            positions = str(row["Position"]).split("/")
            player_id_name = row["Player ID + Player Name"]  # Use the combined column
            
            print(f"Processing row {idx+1}: {player_id_name}")
            
            # Extract player ID from the combined column (format: "ID-Name")
            try:
                # Split by the first colon to separate ID from name
                parts = player_id_name.split(":", 1)
                if len(parts) >= 2:
                    player_id = parts[0]  # Full ID (e.g., "118729-82992")
                    player_name = parts[1]     # Second part is the name
                else:
                    # Fallback: try to extract ID from the original "Id" column
                    player_id = str(row["Id"])
                    player_name = player_id_name
            except (ValueError, KeyError) as e:
                print(f"Warning: Could not parse player ID from '{player_id_name}'. Error: {e}. Skipping player.")
                continue
            
            # Get projection and status
            projection = round(row["FPPG"], 2)
            status = row.get("Status", "")
            
            print(f"  Projection: {projection}, Status: {status}")
            
            # If player is OUT, set projection to 0
            if status == "OUT":
                projection = 0
            
            # Filter out players with projection under MIN_PROJECTION (but include OUT players with 0 projection)
            if projection < self.config.MIN_PROJECTION and projection != 0:
                print(f"  Skipping due to low projection ({projection} < {self.config.MIN_PROJECTION})")
                continue
            
            # Get projection data
            projection_floor = row.get("Projection Floor", projection)
            projection_ceil = row.get("Projection Ceil", projection)
            
            # Calculate standard deviation if we have floor and ceil data
            std_dev = None
            if pd.notna(projection_floor) and pd.notna(projection_ceil) and projection_floor != projection_ceil:
                std_dev = self.smart_randomness.calculate_std_dev(projection, projection_floor, projection_ceil)
            
            player = Player(
                id=player_id,
                name=player_id_name,  # Keep the full combined string for consistency
                positions=positions,
                team=row["Team"],
                opponent=row["Opponent"],
                salary=int(row["Salary"]),
                projection=projection,
                ownership=float(row.get("Projected Ownership", 0)),
                is_locked=row["Team"] in self.config.LOCKED_TEAMS,
                status=status,
                projection_floor=projection_floor,
                projection_ceil=projection_ceil,
                std_dev=std_dev
            )
            self.available_players[player.id] = player
            self.projection_tracker.initialize_player(player)
            print(f"  Added player: {player.name} (ID: {player_id})")
        
        print(f"Loaded {len(self.available_players)} players from data file")
        print("Sample players loaded:")
        for i, (player_id, player) in enumerate(list(self.available_players.items())[:5]):
            print(f"  {player_id}: {player.name}")
    
    def load_original_lineups(self) -> None:
        """Load original lineups from CSV file."""
        with open(self.config.INPUT_LINEUP_FILE, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)
            
            # Find the lineup columns: start with first 'G' column and end with last 'F' column
            g_indices = [i for i, col in enumerate(header) if col == 'G']
            f_indices = [i for i, col in enumerate(header) if col == 'F']
            
            if not g_indices or not f_indices:
                raise ValueError("Could not find 'G' or 'F' columns in input lineup file header.")
            
            start_idx = min(g_indices)  # First 'G' column
            end_idx = max(f_indices)    # Last 'F' column
            
            slot_headers = header[start_idx:end_idx+1]  # inclusive of last 'F'
            print(f"Reading lineup columns from index {start_idx} to {end_idx}: {slot_headers}")
            
            # Build a lookup for player ID + Player Name to Player object
            player_name_map = {p.name: p for p in self.available_players.values()}
            
            print(f"Available players in lookup: {len(player_name_map)}")
            print("Sample available players:")
            for i, (name, player) in enumerate(list(player_name_map.items())[:5]):
                print(f"  '{name}' -> {player.name}")
            
            for row_num, row in enumerate(reader, start=2):
                lineup = []
                for slot, player_name in zip(slot_headers, row[start_idx:end_idx+1]):
                    player_name = str(player_name).strip()
                    if not player_name:
                        continue
                    player = player_name_map.get(player_name)
                    if not player:
                        print(f"Warning: Player '{player_name}' not found in player pool (row {row_num}).")
                        # Show what's available for debugging
                        if row_num <= 3:  # Only show for first few rows
                            print(f"  Available players with similar names:")
                            for available_name in player_name_map.keys():
                                if player_name.lower() in available_name.lower() or available_name.lower() in player_name.lower():
                                    print(f"    '{available_name}'")
                        continue
                    lineup.append(player)
                
                if lineup:
                    lineup_obj = Lineup(
                        players=lineup,
                        total_salary=sum(p.salary for p in lineup),
                        total_projection=sum(p.projection for p in lineup)
                    )
                    
                    # Validate original lineup doesn't have duplicates
                    if lineup_obj.has_duplicate_players:
                        print(f"WARNING: Original lineup {len(self.original_lineups)+1} contains duplicate players!")
                        duplicates = lineup_obj.get_duplicate_players()
                        for dup in duplicates:
                            print(f"  Duplicate: {dup.name} (ID: {dup.id})")
                        # Skip this lineup
                        continue
                    
                    self.original_lineups.append(lineup_obj)
    
    def create_swap_model(self, original_lineup: Lineup, available_players: List[Player]) -> Tuple[cp_model.CpModel, Dict]:
        """Create the constraint programming model for swap optimization."""
        model = cp_model.CpModel()
        
        # Get locked players from original lineup that must be preserved
        locked_players = original_lineup.locked_players
        locked_player_ids = {p.id for p in locked_players}
        
        # Create player variables for available players
        player_vars = {p.id: model.NewBoolVar(f"player_{p.id}") for p in available_players}
        assign = {}
        
        # Create assignment variables with FILLER/CORE logic
        for p in available_players:
            assign[p.id] = {}
            for slot in self.config.SLOTS:
                player_name = p.name.split(":")[-1].strip()
                # Determine if player can play this slot
                if slot == "G":
                    can_play = "G" in p.positions
                elif slot == "F":
                    can_play = "F" in p.positions
                else:
                    can_play = False
                
                # Apply FILLER_PLAYERS restriction if configured
                if any(self.config.FILLER_PLAYERS.values()):
                    is_core = player_name in self.config.CORE_PLAYERS
                    is_filler = player_name in self.config.FILLER_PLAYERS.get(slot, [])
                    can_play = can_play and (is_core or is_filler)
                
                if can_play:
                    assign[p.id][slot] = model.NewBoolVar(f"assign_{p.id}_{slot}")
        
        # CRITICAL: Force locked players to be included in the lineup
        for locked_player in locked_players:
            if locked_player.id in player_vars:
                model.Add(player_vars[locked_player.id] == 1)
        
        # Add roster constraints
        for slot, count in self.config.SLOTS.items():
            model.Add(sum(assign[p.id][slot] for p in available_players if slot in assign[p.id]) == count)
        
        for p in available_players:
            model.Add(sum(assign[p.id][s] for s in assign[p.id]) <= 1)
            model.Add(sum(assign[p.id][s] for s in assign[p.id]) == player_vars[p.id])
        
        # Exclude specific players (but not locked players)
        for p in available_players:
            if p.name.split(":")[-1].strip() in self.config.EXCLUDED_PLAYERS and p.id not in locked_player_ids:
                model.Add(player_vars[p.id] == 0)
        
        # Core players: must use at least MIN_CORE_PLAYERS (skip if no core players defined)
        core_player_vars = []
        for p in available_players:
            if p.name.split(":")[-1].strip() in self.config.CORE_PLAYERS:
                core_player_vars.append(player_vars[p.id])
        if core_player_vars and self.config.CORE_PLAYERS:
            model.Add(sum(core_player_vars) >= self.config.MIN_CORE_PLAYERS)
        
        # Total players constraint
        model.Add(sum(player_vars[p.id] for p in available_players) == 7)  # 7 players in WNBA classic lineup
        
        # Salary constraints
        model.Add(sum(p.salary * player_vars[p.id] for p in available_players) <= self.config.MAX_SALARY)
        model.Add(sum(p.salary * player_vars[p.id] for p in available_players) >= self.config.MIN_SALARY)
        
        # Team constraints (max 4 per team)
        teams = list(set(p.team for p in available_players))
        for team in teams:
            if team not in self.config.EXCLUDED_TEAMS:
                team_players = [p for p in available_players if p.team == team]
                model.Add(sum(player_vars[p.id] for p in team_players) <= self.config.MAX_PLAYERS_PER_TEAM)
        
        # At least 3 unique teams in the lineup
        team_used_vars = {}
        for team in teams:
            team_players = [p for p in available_players if p.team == team]
            team_used = model.NewBoolVar(f"team_used_{team}")
            # If any player from this team is used, team_used is 1
            model.AddMaxEquality(team_used, [player_vars[p.id] for p in team_players])
            team_used_vars[team] = team_used
        model.Add(sum(team_used_vars[team] for team in teams) >= 3)
        
        # Uniqueness constraint: ensure at least 1 unique player between lineups
        # For late swap, we enforce uniqueness against previously generated lineups
        for prev_lineup in self.swapped_lineups:
            # Count how many players are in common with this previous lineup
            common_players = sum(player_vars[pid] for pid in [p.id for p in prev_lineup.players] if pid in player_vars)
            # Force at least 1 unique player (max 6 common players for 7-player lineups)
            model.Add(common_players <= 6)
        
        # Set objective to maximize total lineup projection
        model.Maximize(sum(p.current_projection * player_vars[p.id] for p in available_players))
        
        return model, {
            "player_vars": player_vars,
            "assign": assign
        }
    
    def solve_swap(self, model: cp_model.CpModel, available_players: List[Player], variables: Dict) -> Optional[List[Player]]:
        """Solve the swap optimization model and return the solution if found."""
        solver = cp_model.CpSolver()
        status = solver.Solve(model)
        
        if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            return None
        
        swapped_players = []
        
        # Get players in lineup
        for p in available_players:
            if solver.Value(variables["player_vars"][p.id]):
                swapped_players.append(p)
        
        # Validate that no player appears more than once
        player_ids = [p.id for p in swapped_players]
        if len(player_ids) != len(set(player_ids)):
            print(f"ERROR: Duplicate players found in solution!")
            print(f"Player IDs: {player_ids}")
            print(f"Unique IDs: {list(set(player_ids))}")
            return None
        
        return swapped_players
    
    def optimize_swaps(self, lineup: Lineup) -> Tuple[Optional[Lineup], str]:
        """Optimize swaps for a given lineup. Returns (lineup, reason)."""
        # Get locked players that must be preserved
        locked_players = lineup.locked_players
        
        # Get available players for optimization (only swappable players + locked players from original lineup)
        # Note: We include OUT players in available_players since they have 0 projection and can be swapped
        available_players = [
            p for p in self.available_players.values()
            if p.current_projection >= 0 and (p.can_be_swapped or p.id in [lp.id for lp in locked_players])
        ]
        
        # Ensure all locked players are in available_players
        for locked_player in locked_players:
            if locked_player.id not in [p.id for p in available_players]:
                print(f"WARNING: Locked player {locked_player.name} not in available players - adding")
                available_players.append(locked_player)
        
        # Check if original lineup has players with 0 projections that need to be swapped
        zero_projection_players = [p for p in lineup.players if p.current_projection == 0 and p.can_be_swapped]
        
        if zero_projection_players:
            print(f"Found {len(zero_projection_players)} players with 0 projections that need to be swapped:")
            for player in zero_projection_players:
                status_info = f" [OUT]" if player.status == "OUT" else ""
                print(f"  - {player.name} ({player.team}) - {player.positions[0]}{status_info}")
            
            # Prioritize swapping out players with 0 projections
            # The model will naturally prefer higher-projection players, which will replace 0-projection players
            print("Prioritizing replacement of 0-projection players...")
        
        # Create and solve model
        model, variables = self.create_swap_model(lineup, available_players)
        swapped_players = self.solve_swap(model, available_players, variables)
        
        if swapped_players:
            # Ensure all locked players from original lineup are included
            locked_players = lineup.locked_players
            locked_player_ids = {p.id for p in locked_players}
            swapped_player_ids = {p.id for p in swapped_players}
            
            # Check if all locked players are in the solution
            missing_locked_players = [p for p in locked_players if p.id not in swapped_player_ids]
            if missing_locked_players:
                print(f"ERROR: Missing locked players in solution: {[p.name for p in missing_locked_players]}")
                return None
            
            # Update projections for swapped players
            for player in available_players:
                self.projection_tracker.update_projection(
                    player, 
                    used_in_lineup=(player.id in swapped_player_ids)
                )
            
            # Apply smart randomness if enabled
            if self.config.ENABLE_SMART_RANDOMNESS:
                self.smart_randomness.apply_smart_randomness(swapped_players)
            
            # Create new lineup
            new_lineup = Lineup(
                players=swapped_players,
                total_salary=sum(p.salary for p in swapped_players),
                total_projection=sum(p.current_projection for p in swapped_players)
            )
            
            # Check if the original lineup has 0-projection players that need to be swapped
            original_zero_projection_players = [p for p in lineup.players if p.current_projection == 0 and p.can_be_swapped]
            new_zero_projection_players = [p for p in swapped_players if p.current_projection == 0 and p.can_be_swapped]
            
            # Priority 1: If we successfully removed 0-projection players, accept the swap
            if original_zero_projection_players and not new_zero_projection_players:
                print(f"Successfully removed {len(original_zero_projection_players)} 0-projection players - accepting swap")
                print(f"Original projection: {lineup.total_projection:.2f} (with {len(original_zero_projection_players)} zero-projection players)")
                print(f"New projection: {new_lineup.total_projection:.2f} (with {len(new_zero_projection_players)} zero-projection players)")
                return new_lineup, "improved_zero_removal"
            
            # Priority 2: If we reduced the number of 0-projection players, accept the swap
            elif len(new_zero_projection_players) < len(original_zero_projection_players):
                print(f"Reduced 0-projection players from {len(original_zero_projection_players)} to {len(new_zero_projection_players)} - accepting swap")
                print(f"Original projection: {lineup.total_projection:.2f}")
                print(f"New projection: {new_lineup.total_projection:.2f}")
                return new_lineup, "improved_zero_reduction"
            
            # Priority 3: Standard projection improvement logic
            elif new_lineup.total_projection > lineup.total_projection:
                return new_lineup, "improved"
            elif new_lineup.total_projection == lineup.total_projection:
                print(f"New lineup projection ({new_lineup.total_projection:.2f}) same as original ({lineup.total_projection:.2f}) - skipping")
                return None, "no_change"
            else:
                print(f"New lineup projection ({new_lineup.total_projection:.2f}) not better than original ({lineup.total_projection:.2f}) - keeping original")
                return None, "worse"
        
        return None, "no_solution"
    
    def is_lineup_swappable(self, lineup: Lineup) -> bool:
        """Check if lineup can be swapped (has swappable players)."""
        return len(lineup.swappable_players) > 0
    
    def is_lineup_optimal(self, lineup: Lineup) -> bool:
        """Check if lineup is already optimal (no out players, no 0-projection players, no swappable players)."""
        # Check if lineup has any out players (these should be swapped)
        if lineup.has_out_players:
            return False
        
        # Check if lineup has any swappable players with 0 projections
        zero_projection_swappable = [p for p in lineup.players if p.current_projection == 0 and p.can_be_swapped]
        if zero_projection_swappable:
            return False
        
        # Check if there are any swappable players at all
        if not lineup.swappable_players:
            return True
        
        # If lineup has swappable players, we should try to optimize
        # Note: This method is mainly used for analysis, but we always attempt optimization
        # when there are swappable players regardless of this result
        return False
    
    def analyze_lineup_swappability(self, lineup: Lineup) -> Dict:
        """Analyze lineup swappability and provide detailed information."""
        locked_count = len(lineup.locked_players)
        swappable_count = len(lineup.swappable_players)
        out_count = len(lineup.out_players)
        core_count = lineup.core_player_count
        zero_projection_count = len([p for p in lineup.players if p.current_projection == 0 and p.can_be_swapped])
        
        return {
            "locked_players": locked_count,
            "swappable_players": swappable_count,
            "out_players": out_count,
            "core_players": core_count,
            "zero_projection_players": zero_projection_count,
            "can_swap": self.is_lineup_swappable(lineup),
            "is_optimal": self.is_lineup_optimal(lineup),
            "has_out_players": lineup.has_out_players,
            "has_zero_projection_players": zero_projection_count > 0
        }
    
    def process_all_lineups(self) -> List[Lineup]:
        """Process all lineups and attempt swaps."""
        print(f"Processing {len(self.original_lineups)} lineups...")
        
        for i, original_lineup in enumerate(self.original_lineups):
            print(f"\n=== Processing Lineup {i+1} ===")
            
            # Analyze lineup
            analysis = self.analyze_lineup_swappability(original_lineup)
            print(f"Locked players: {analysis['locked_players']}")
            print(f"Swappable players: {analysis['swappable_players']}")
            print(f"Out players: {analysis['out_players']}")
            print(f"Core players: {analysis['core_players']}")
            print(f"Zero projection players: {analysis['zero_projection_players']}")
            print(f"Lineup optimal: {analysis['is_optimal']}")
            
            # Always attempt optimization if there are swappable players
            # (This will try to improve projection even if lineup looks "good")
            if not analysis['can_swap']:
                print("Lineup cannot be swapped (no swappable players)")
                self.unswappable_lineups.append((i, original_lineup))
                self.swapped_lineups.append(original_lineup)
                continue
            
            # Always try to maximize projection when there are swappable players
            print("Attempting to maximize lineup projection...")
            
            if analysis['has_out_players']:
                print("Lineup contains out players - will attempt replacement")
            
            if analysis['has_zero_projection_players']:
                print("Lineup contains players with 0 projections - will attempt replacement")
            
            # Attempt swap
            result = self.optimize_swaps(original_lineup)
            if result is None:
                print("No valid swap solution found - keeping original lineup")
                self.swapped_lineups.append(original_lineup)
                continue
            
            swapped_lineup, reason = result
            
            if reason in ["improved", "improved_zero_removal", "improved_zero_reduction"]:
                if reason == "improved":
                    print("Swap successful!")
                    print(f"Original projection: {original_lineup.total_projection:.2f}")
                    print(f"New projection: {swapped_lineup.total_projection:.2f}")
                    print(f"Projection change: {swapped_lineup.total_projection - original_lineup.total_projection:+.2f}")
                elif reason == "improved_zero_removal":
                    print("Swap successful - removed all 0-projection players!")
                    self.zero_removal_swaps.append((i, swapped_lineup))
                elif reason == "improved_zero_reduction":
                    print("Swap successful - reduced 0-projection players!")
                    self.zero_reduction_swaps.append((i, swapped_lineup))
                
                # Validate no duplicate players
                if swapped_lineup.has_duplicate_players:
                    print(f"ERROR: Lineup {i+1} contains duplicate players!")
                    duplicates = swapped_lineup.get_duplicate_players()
                    for dup in duplicates:
                        print(f"  Duplicate: {dup.name} (ID: {dup.id})")
                    # Skip this lineup and keep original
                    self.swapped_lineups.append(original_lineup)
                    continue
                
                # Show players swapped in and out
                self.print_swap_details(original_lineup, swapped_lineup)
                
                self.swapped_lineups.append(swapped_lineup)
            elif reason == "no_change":
                print("Skipping lineup due to no projection change")
                self.skipped_no_change_lineups.append((i, original_lineup))
                self.swapped_lineups.append(original_lineup)
            elif reason == "worse":
                print("Swap failed - keeping original lineup")
                self.swapped_lineups.append(original_lineup)
            else:  # no_solution
                print("No valid swap solution found - keeping original lineup")
                self.swapped_lineups.append(original_lineup)
        
        return self.swapped_lineups
    
    def print_lineup(self, lineup: Lineup, lineup_num: int, is_swapped: bool = False) -> None:
        """Print the lineup in a formatted way."""
        status = "SWAPPED" if is_swapped else "ORIGINAL"
        print(f"=== Lineup {lineup_num} ({status}) ===")
        
        # Sort players by slot order
        slot_order = {"G": 0, "F": 1}
        sorted_players = sorted(lineup.players, key=lambda x: slot_order.get(x.positions[0], 5))
        
        for player in sorted_players:
            player_name = player.name.split(":")[-1].strip()
            is_core = player.is_core_player
            core_indicator = " [CORE]" if is_core else ""
            locked_indicator = " [LOCKED]" if not player.can_be_swapped else ""
            out_indicator = " [OUT]" if player.status == "OUT" else ""
            
            # For OUT players, show projection as 0
            if player.status == "OUT":
                proj_str = " | Proj: 0.00 [OUT]"
            else:
                proj_str = f" | Proj: {player.current_projection:.2f}"
                if player.current_projection != player.projection:
                    proj_str += f" (Original: {player.projection:.2f})"
                    # Show if this is due to smart randomness
                    if self.config.ENABLE_SMART_RANDOMNESS and abs(player.current_projection - player.projection) > 0.01:
                        proj_str += " [Smart Random]"
            
            print(f"{player.positions[0]}: {player.name}{core_indicator}{locked_indicator}{out_indicator} ({player.team}) | Salary: ${player.salary}{proj_str}")
        
        print(f"\nTotal Salary: ${lineup.total_salary}")
        print(f"Total Projection: {lineup.total_projection:.2f}")
    
    def export_lineups(self, lineups: List[Lineup]) -> None:
        """Export lineups to a CSV file in FanDuel WNBA format."""
        fd_position_order = ['G', 'G', 'G', 'F', 'F', 'F', 'F']
        with open(self.config.OUTPUT_FILE, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(fd_position_order)
            for lineup in lineups:
                position_map = {pos: [] for pos in ['G', 'F']}
                for player in lineup.players:
                    # Find the first position that matches the slot
                    for pos in player.positions:
                        if pos in position_map:
                            position_map[pos].append(player)
                            break
                row = []
                for pos in fd_position_order:
                    if position_map[pos]:
                        row.append(position_map[pos].pop(0).id)
                writer.writerow(row)
    
    def print_summary(self) -> None:
        """Print summary of swap results."""
        total_lineups = len(self.original_lineups)
        swapped_count = len([l for l in self.swapped_lineups if l != self.original_lineups[self.swapped_lineups.index(l)]])
        unswappable_count = len(self.unswappable_lineups)
        skipped_no_change_count = len(self.skipped_no_change_lineups)
        zero_removal_count = len(self.zero_removal_swaps)
        zero_reduction_count = len(self.zero_reduction_swaps)
        
        print(f"\n=== SWAP SUMMARY ===")
        print(f"Total lineups: {total_lineups}")
        print(f"Successfully swapped: {swapped_count}")
        print(f"  - Zero-projection removal: {zero_removal_count}")
        print(f"  - Zero-projection reduction: {zero_reduction_count}")
        print(f"  - Standard improvement: {swapped_count - zero_removal_count - zero_reduction_count}")
        print(f"Skipped (no projection change): {skipped_no_change_count}")
        print(f"Unswappable: {unswappable_count}")
        
        if total_lineups > 0:
            print(f"Success rate: {swapped_count/total_lineups:.1%}")
        else:
            print("Success rate: N/A (no lineups processed)")
        
        if self.skipped_no_change_lineups:
            print(f"\nSkipped lineups (no projection change): {[i+1 for i, _ in self.skipped_no_change_lineups]}")
        
        if self.unswappable_lineups:
            print(f"\nUnswappable lineups: {[i+1 for i, _ in self.unswappable_lineups]}")
        
        if self.zero_removal_swaps:
            print(f"\nZero-projection removal lineups: {[i+1 for i, _ in self.zero_removal_swaps]}")
        
        if self.zero_reduction_swaps:
            print(f"\nZero-projection reduction lineups: {[i+1 for i, _ in self.zero_reduction_swaps]}")
    
    def print_swap_details(self, original_lineup: Lineup, new_lineup: Lineup) -> None:
        """Print details of players swapped in and out."""
        original_players = set(p.id for p in original_lineup.players)
        new_players = set(p.id for p in new_lineup.players)
        
        # Find players swapped out (in original but not in new)
        swapped_out = [p for p in original_lineup.players if p.id not in new_players]
        
        # Find players swapped in (in new but not in original)
        swapped_in = [p for p in new_lineup.players if p.id not in original_players]
        
        if swapped_out or swapped_in:
            print("\nSwap Details:")
            
            if swapped_out:
                print("Players Swapped OUT:")
                for player in swapped_out:
                    player_name = player.name.split(":")[-1].strip()
                    if player.status == "OUT":
                        proj_str = "Proj: 0.00 [OUT]"
                    else:
                        proj_str = f"Proj: {player.current_projection:.2f}"
                        if player.current_projection != player.projection:
                            proj_str += f" (Original: {player.projection:.2f})"
                            if self.config.ENABLE_SMART_RANDOMNESS and abs(player.current_projection - player.projection) > 0.01:
                                proj_str += " [Smart Random]"
                    print(f"  - {player_name} ({player.team}) - {player.positions[0]} | {proj_str} | Salary: ${player.salary}")
            
            if swapped_in:
                print("Players Swapped IN:")
                for player in swapped_in:
                    player_name = player.name.split(":")[-1].strip()
                    if player.status == "OUT":
                        proj_str = "Proj: 0.00 [OUT]"
                    else:
                        proj_str = f"Proj: {player.current_projection:.2f}"
                        if player.current_projection != player.projection:
                            proj_str += f" (Original: {player.projection:.2f})"
                            if self.config.ENABLE_SMART_RANDOMNESS and abs(player.current_projection - player.projection) > 0.01:
                                proj_str += " [Smart Random]"
                    print(f"  + {player_name} ({player.team}) - {player.positions[0]} | {proj_str} | Salary: ${player.salary}")
            
            # Show projection and salary changes
            total_proj_change = new_lineup.total_projection - original_lineup.total_projection
            total_salary_change = new_lineup.total_salary - original_lineup.total_salary
            
            print(f"\nTotal Changes:")
            print(f"  Projection: {original_lineup.total_projection:.2f} → {new_lineup.total_projection:.2f} ({total_proj_change:+.2f})")
            print(f"  Salary: ${original_lineup.total_salary:,} → ${new_lineup.total_salary:,} ({total_salary_change:+,})")
        else:
            print("No players were swapped (lineup composition unchanged)")

def main():
    """Main function to run the WNBA late swap optimizer."""
    try:
        optimizer = WNBALateSwapOptimizer()
        
        # Load data
        print("Loading player data...")
        optimizer.load_player_data()
        print(f"Loaded {len(optimizer.available_players)} players")
        
        print("Loading original lineups...")
        optimizer.load_original_lineups()
        print(f"Loaded {len(optimizer.original_lineups)} lineups")
        
        # Process lineups
        swapped_lineups = optimizer.process_all_lineups()
        
        # Print summary
        optimizer.print_summary()
        
        # Export results
        optimizer.export_lineups(swapped_lineups)
        print(f"\nExported swapped lineups to {optimizer.config.OUTPUT_FILE}")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main() 