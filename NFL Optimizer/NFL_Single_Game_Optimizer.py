"""
NFL Single Game Daily Fantasy Sports Lineup Optimizer
This script generates optimized lineups for NFL single-game DFS contests using constraint programming.
"""

from typing import List, Dict, Set, Tuple, Optional
import pandas as pd
from ortools.sat.python import cp_model
import os
from dataclasses import dataclass
from pathlib import Path
import csv
import random
import numpy as np
import copy

# ===== Configuration =====
class Config:
    # File paths
    DATA_FILE = "/Users/adamsardinha/Desktop/NFL_Single_Game_FD.csv"
    
    # Lineup generation settings
    NUM_LINEUPS_TO_GENERATE = 1000
    MAX_SALARY = 60000  # FanDuel single-game salary cap
    MIN_SALARY = 57000  # Minimum salary to ensure quality lineups
    MAX_ATTEMPTS = 1000
    MIN_PLAYER_PROJECTION = 3  # Minimum fantasy points projection for players
    
    # Stack rules
    ENABLED_STACK_RULES = False
    
    # Roster settings for FanDuel NFL single-game contests
    SLOTS = {
        "MVP": 1,    # 1.5x points and salary
        "UTIL": 5    # 1x points
    }
    
    # Exposure settings
    RECENT_PLAYERS_WINDOW = 5  # Number of recent lineups to track for each player
    MIN_PLAYER_EXPOSURE = 0.05  # Minimum exposure for each player
    
    # MVP eligibility settings
    MVP_ELIGIBLE_PLAYERS = [
        # Add your MVP eligible players here
        # Example: "Patrick Mahomes", "Josh Allen", "Lamar Jackson"
    ]
    
    # Smart Randomness settings
    ENABLE_SMART_RANDOMNESS = True  # Enable smart randomness
    DISTRIBUTION_TYPE = "lognormal"  # "normal" or "lognormal"
    RANDOMNESS_SEED = None  # Set to an integer for reproducible results
    RANDOMNESS_FREQUENCY = "per_lineup"  # "per_lineup" or "per_session" (once at start)
    
    # ===== MVP Stacking Configuration =====
    ENABLE_MVP_STACKING = True  # Master toggle for MVP-specific stacking rules
    
    # QB MVP Stacking Rules
    MVP_QB_REQUIRE_WR_TE = True  # If QB is MVP, require at least one WR/TE from same team
    MVP_QB_MIN_WR_TE = 1  # If QB is MVP, minimum WR/TE from same team (set to 0 to disable)
    
    # RB MVP Stacking Rules
    MVP_RB_REQUIRE_QB = True  # If RB is MVP, require QB from same team
    MVP_RB_MAX_WR_TE = 2  # If RB is MVP, maximum WR/TE from same team (set to -1 to disable)
    
    # WR MVP Stacking Rules
    MVP_WR_REQUIRE_QB = True  # If WR is MVP, require QB from same team
    MVP_WR_MAX_SAME_TEAM_WR_TE = 1  # If WR is MVP, maximum WR/TE from same team (set to -1 to disable)
    MVP_WR_MIN_OPP_WR_TE = 1  # If WR is MVP, minimum WR/TE from opponent team (set to 0 to disable)
    
    # TE MVP Stacking Rules
    MVP_TE_REQUIRE_QB = True  # If TE is MVP, require QB from same team
    MVP_TE_REQUIRE_EXACT_WR = 1  # If TE is MVP, require exactly this many WR from same team (set to -1 to disable)
    
    # Defense MVP Stacking Rules
    MVP_D_REQUIRE_TEAMMATES = 3  # If D is MVP, require at least this many teammates (set to 0 to disable)
    
    # Group constraints
    GROUP_CONSTRAINTS = [
        # Example QB-WR stacks
        # {
        #     "name": "KC Stack",
        #     "players": ["Patrick Mahomes", "Travis Kelce", "Rashee Rice"],
        #     "min": 2,  # Minimum number of players from this group
        #     "max": 3   # Maximum number of players from this group
        # },
    ]
    
    # Conditional constraints
    CONDITIONAL_CONSTRAINTS = [
        # Example: If QB is MVP, then include at least one WR from same team
        # {
        #     "if_player": "Patrick Mahomes",
        #     "if_position": "MVP",
        #     "then_team": "KC",
        #     "min_team_players": 1
        # },
    ]

@dataclass
class Player:
    id: int
    name: str
    positions: List[str]
    team: str
    opponent: str
    salary: int
    mvp_salary: int
    projection: float
    ownership: float
    mvp_ownership: float
    starter: str = "0"  # Add starter attribute, default to "0"
    current_projection: float = None  # Current adjusted projection
    projection_floor: float = None  # 25th percentile projection
    projection_ceil: float = None  # 85th percentile projection
    std_dev: float = None  # Calculated standard deviation

    def __post_init__(self):
        self.current_projection = self.projection  # Initialize current projection

class PlayerProjectionTracker:
    def __init__(self):
        self.original_projections: Dict[int, float] = {}  # Stores original projections
        
    def initialize_player(self, player: Player):
        """Initialize tracking for a new player."""
        if player.id not in self.original_projections:
            self.original_projections[player.id] = player.projection
            player.current_projection = player.projection
    
    def update_projection(self, player: Player, used_in_lineup: bool):
        """Update a player's projection based on usage."""
        self.initialize_player(player)
        
        # For now, just maintain the original projection
        # This can be extended later if needed
        player.current_projection = player.projection

@dataclass
class Lineup:
    players: List[Dict]
    
    @property
    def lineup(self):
        """Convert our players to LineupPlayer objects expected by FanDuelCSVLineupExporter."""
        # Define FanDuel's required position order for NFL single-game contests
        fd_position_order = ['MVP', 'UTIL', 'UTIL', 'UTIL', 'UTIL', 'UTIL']
        
        # Create a mapping of positions to players
        position_map = {}
        util_candidates = []
        
        for player in self.players:
            if player["Slot"] == "UTIL":
                util_candidates.append(player)
            else:
                position_map[player["Slot"]] = player
        
        # Build ordered list according to FanDuel's sequence
        ordered_players = []
        for pos in fd_position_order:
            if pos == 'UTIL':
                if util_candidates:
                    player = util_candidates.pop(0)
                    ordered_players.append(player)
            else:
                if pos in position_map:
                    ordered_players.append(position_map[pos])
        
        return ordered_players

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

def load_and_clean_data(file_path: str) -> pd.DataFrame:
    """Load and clean the player data from CSV file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Data file not found: {file_path}")
    
    df = pd.read_csv(file_path)
    
    # Convert columns to appropriate types
    numeric_columns = ["FPPG", "Salary", "MVP 1.5x Salary", "Projected Ownership", "MVP Ownership"]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    df["Position"] = df["Position"].astype(str)
    
    return df

def create_player_objects(df: pd.DataFrame) -> List[Player]:
    """Convert DataFrame rows to Player objects."""
    players = []
    for _, row in df.iterrows():
        positions = row["Position"].split("/")
        name = f"{row['First Name']} {row['Last Name']}"
        
        # Filter out players with projection under minimum threshold
        projection = round(row["FPPG"], 2)
        if projection < Config.MIN_PLAYER_PROJECTION:
            continue
        

        
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
            mvp_salary=int(row["MVP 1.5x Salary"]),
            projection=projection,
            ownership=float(row.get("Projected Ownership", 0)),
            mvp_ownership=float(row.get("MVP Ownership", 0)),
            starter=str(row.get("Starter", "0")),  # Read Starter column
            projection_floor=projection_floor,
            projection_ceil=projection_ceil,
            std_dev=std_dev
        ))
    return players

def add_mvp_stacking_constraints(model: cp_model.CpModel,
                                players: List[Player],
                                player_vars: Dict[int, cp_model.IntVar],
                                assign: Dict[int, Dict[str, cp_model.IntVar]]) -> None:
    """Add MVP-specific stacking constraints."""
    
    # Find all QBs
    qbs = [p for p in players if "QB" in p.positions]
    
    # For each QB, if they are MVP, require WR/TE from same team (if enabled)
    if Config.MVP_QB_REQUIRE_WR_TE and Config.MVP_QB_MIN_WR_TE > 0:
        for qb in qbs:
            # Find WR/TE players from the same team as this QB
            same_team_wr_te = [p for p in players 
                              if p.team == qb.team and 
                              p.id != qb.id and 
                              any(pos in ["WR", "TE"] for pos in p.positions)]
            
            if same_team_wr_te:
                # If this QB is MVP, require minimum WR/TE from same team
                qb_mvp_var = assign[qb.id]["MVP"]
                
                # Sum of WR/TE players from same team
                wr_te_sum = sum(player_vars[p.id] for p in same_team_wr_te)
                
                # If QB is MVP, require minimum WR/TE from same team
                model.Add(wr_te_sum >= Config.MVP_QB_MIN_WR_TE).OnlyEnforceIf(qb_mvp_var)
    
    # For each RB, if they are MVP, require QB from same team and limit WR/TE
    if Config.MVP_RB_REQUIRE_QB:
        rbs = [p for p in players if "RB" in p.positions]
        for rb in rbs:
            # Find QB from the same team as this RB
            same_team_qb = [p for p in players 
                           if p.team == rb.team and 
                           p.id != rb.id and 
                           "QB" in p.positions]
            
            # Find WR/TE players from the same team as this RB
            same_team_wr_te = [p for p in players 
                              if p.team == rb.team and 
                              p.id != rb.id and 
                              any(pos in ["WR", "TE"] for pos in p.positions)]
            
            if same_team_qb:
                # If this RB is MVP, require QB from same team
                rb_mvp_var = assign[rb.id]["MVP"]
                qb_var = player_vars[same_team_qb[0].id]
                
                # If RB is MVP, require QB from same team
                model.Add(qb_var >= 1).OnlyEnforceIf(rb_mvp_var)
                
                # If RB is MVP, limit WR/TE from same team to maximum (if enabled)
                if same_team_wr_te and Config.MVP_RB_MAX_WR_TE >= 0:
                    wr_te_sum = sum(player_vars[p.id] for p in same_team_wr_te)
                    model.Add(wr_te_sum <= Config.MVP_RB_MAX_WR_TE).OnlyEnforceIf(rb_mvp_var)
    
    # For each WR, if they are MVP, require QB from same team and limit WR/TE
    if Config.MVP_WR_REQUIRE_QB:
        wrs = [p for p in players if "WR" in p.positions]
        for wr in wrs:
            # Find QB from the same team as this WR
            same_team_qb = [p for p in players 
                           if p.team == wr.team and 
                           p.id != wr.id and 
                           "QB" in p.positions]
            
            # Find WR/TE players from the same team as this WR (excluding the WR itself)
            same_team_wr_te = [p for p in players 
                              if p.team == wr.team and 
                              p.id != wr.id and 
                              any(pos in ["WR", "TE"] for pos in p.positions)]
            
            # Find WR/TE players from the opponent team
            opp_team_wr_te = [p for p in players 
                             if p.team == wr.opponent and 
                             any(pos in ["WR", "TE"] for pos in p.positions)]
            
            if same_team_qb:
                # If this WR is MVP, require QB from same team
                wr_mvp_var = assign[wr.id]["MVP"]
                qb_var = player_vars[same_team_qb[0].id]
                
                # If WR is MVP, require QB from same team
                model.Add(qb_var >= 1).OnlyEnforceIf(wr_mvp_var)
                
                # If WR is MVP, limit WR/TE from same team to maximum (if enabled)
                if same_team_wr_te and Config.MVP_WR_MAX_SAME_TEAM_WR_TE >= 0:
                    same_team_wr_te_sum = sum(player_vars[p.id] for p in same_team_wr_te)
                    model.Add(same_team_wr_te_sum <= Config.MVP_WR_MAX_SAME_TEAM_WR_TE).OnlyEnforceIf(wr_mvp_var)
                
                # If WR is MVP, require minimum WR/TE from opponent team (if enabled)
                if opp_team_wr_te and Config.MVP_WR_MIN_OPP_WR_TE > 0:
                    opp_team_wr_te_sum = sum(player_vars[p.id] for p in opp_team_wr_te)
                    model.Add(opp_team_wr_te_sum >= Config.MVP_WR_MIN_OPP_WR_TE).OnlyEnforceIf(wr_mvp_var)
    
    # For each TE, if they are MVP, require QB from same team and exactly one WR
    if Config.MVP_TE_REQUIRE_QB:
        tes = [p for p in players if "TE" in p.positions]
        for te in tes:
            # Find QB from the same team as this TE
            same_team_qb = [p for p in players 
                           if p.team == te.team and 
                           p.id != te.id and 
                           "QB" in p.positions]
            
            # Find WR players from the same team as this TE (excluding the TE itself)
            same_team_wr = [p for p in players 
                           if p.team == te.team and 
                           p.id != te.id and 
                           "WR" in p.positions]
            
            if same_team_qb:
                # If this TE is MVP, require QB from same team
                te_mvp_var = assign[te.id]["MVP"]
                qb_var = player_vars[same_team_qb[0].id]
                
                # If TE is MVP, require QB from same team
                model.Add(qb_var >= 1).OnlyEnforceIf(te_mvp_var)
                
                # If TE is MVP, require exactly specified number of WR from same team (if enabled)
                if same_team_wr and Config.MVP_TE_REQUIRE_EXACT_WR >= 0:
                    same_team_wr_sum = sum(player_vars[p.id] for p in same_team_wr)
                    model.Add(same_team_wr_sum == Config.MVP_TE_REQUIRE_EXACT_WR).OnlyEnforceIf(te_mvp_var)
    
    # For each Defense, if they are MVP, require minimum teammates (if enabled)
    if Config.MVP_D_REQUIRE_TEAMMATES > 0:
        defenses = [p for p in players if "D" in p.positions or "DST" in p.positions]
        for defense in defenses:
            # Find all teammates (excluding the defense itself)
            teammates = [p for p in players 
                       if p.team == defense.team and 
                       p.id != defense.id]
            
            if teammates:
                # If this Defense is MVP, require at least the specified number of teammates
                defense_mvp_var = assign[defense.id]["MVP"]
                teammates_sum = sum(player_vars[p.id] for p in teammates)
                
                # If Defense is MVP, require at least the minimum number of teammates
                model.Add(teammates_sum >= Config.MVP_D_REQUIRE_TEAMMATES).OnlyEnforceIf(defense_mvp_var)

def print_mvp_stacking_info(lineup: Lineup) -> None:
    """Print information about MVP stacking in the lineup."""
    mvp_player = next((p for p in lineup.players if p["Slot"] == "MVP"), None)
    
    if not mvp_player:
        return
    
    mvp_name = mvp_player["Name"]
    mvp_team = mvp_player["Team"]
    mvp_positions = mvp_player["Positions"].split(",")
    
    print(f"\nMVP Stacking Analysis:")
    print(f"  MVP: {mvp_name} ({mvp_team}) - {', '.join(mvp_positions)}")
    
    # Check if MVP is a QB
    if "QB" in mvp_positions:
        # Find WR/TE from same team
        same_team_wr_te = [p for p in lineup.players 
                          if p["Team"] == mvp_team and 
                          p["Id"] != mvp_player["Id"] and 
                          any(pos in ["WR", "TE"] for pos in p["Positions"].split(","))]
        
        if Config.MVP_QB_REQUIRE_WR_TE and Config.MVP_QB_MIN_WR_TE > 0:
            if same_team_wr_te:
                wr_te_count = len(same_team_wr_te)
                min_required = Config.MVP_QB_MIN_WR_TE
                if wr_te_count >= min_required:
                    print(f"  ✅ QB MVP Stack: {wr_te_count}/{min_required} WR/TE from same team")
                    for player in same_team_wr_te:
                        positions = player["Positions"].split(",")
                        print(f"    - {player['Name']} ({', '.join(positions)})")
                else:
                    print(f"  ⚠️  QB MVP Stack: {wr_te_count}/{min_required} WR/TE from same team (constraint violation!)")
            else:
                min_required = Config.MVP_QB_MIN_WR_TE
                print(f"  ⚠️  QB MVP Stack: 0/{min_required} WR/TE from same team (constraint violation!)")
        else:
            if same_team_wr_te:
                print(f"  ℹ️  QB MVP Stack: {len(same_team_wr_te)} WR/TE from same team (rule disabled)")
                for player in same_team_wr_te:
                    positions = player["Positions"].split(",")
                    print(f"    - {player['Name']} ({', '.join(positions)})")
            else:
                print(f"  ℹ️  QB MVP Stack: No WR/TE from same team (rule disabled)")
    
    # Check if MVP is an RB
    elif "RB" in mvp_positions:
        # Find QB from same team
        same_team_qb = [p for p in lineup.players 
                       if p["Team"] == mvp_team and 
                       p["Id"] != mvp_player["Id"] and 
                       "QB" in p["Positions"].split(",")]
        
        # Find WR/TE from same team
        same_team_wr_te = [p for p in lineup.players 
                          if p["Team"] == mvp_team and 
                          p["Id"] != mvp_player["Id"] and 
                          any(pos in ["WR", "TE"] for pos in p["Positions"].split(","))]
        
        if same_team_qb:
            print(f"  ✅ RB MVP Stack: QB from same team")
            for player in same_team_qb:
                positions = player["Positions"].split(",")
                print(f"    - {player['Name']} ({', '.join(positions)})")
        else:
            print(f"  ⚠️  RB MVP Stack: No QB from same team (constraint violation!)")
        
        if same_team_wr_te and Config.MVP_RB_MAX_WR_TE >= 0:
            wr_te_count = len(same_team_wr_te)
            max_allowed = Config.MVP_RB_MAX_WR_TE
            if wr_te_count <= max_allowed:
                print(f"  ✅ RB MVP Stack: {wr_te_count}/{max_allowed} WR/TE from same team")
                for player in same_team_wr_te:
                    positions = player["Positions"].split(",")
                    print(f"    - {player['Name']} ({', '.join(positions)})")
            else:
                print(f"  ⚠️  RB MVP Stack: {wr_te_count}/{max_allowed} WR/TE from same team (constraint violation!)")
        elif same_team_wr_te:
            print(f"  ℹ️  RB MVP Stack: {len(same_team_wr_te)} WR/TE from same team (rule disabled)")
            for player in same_team_wr_te:
                positions = player["Positions"].split(",")
                print(f"    - {player['Name']} ({', '.join(positions)})")
        else:
            print(f"  ℹ️  RB MVP Stack: No WR/TE from same team")
    
    # Check if MVP is a WR
    elif "WR" in mvp_positions:
        # Find QB from same team
        same_team_qb = [p for p in lineup.players 
                       if p["Team"] == mvp_team and 
                       p["Id"] != mvp_player["Id"] and 
                       "QB" in p["Positions"].split(",")]
        
        # Find WR/TE from same team (excluding the WR MVP itself)
        same_team_wr_te = [p for p in lineup.players 
                          if p["Team"] == mvp_team and 
                          p["Id"] != mvp_player["Id"] and 
                          any(pos in ["WR", "TE"] for pos in p["Positions"].split(","))]
        
        # Find WR/TE from opponent team
        opp_team_wr_te = [p for p in lineup.players 
                         if p["Team"] == mvp_player["Opponent"] and 
                         any(pos in ["WR", "TE"] for pos in p["Positions"].split(","))]
        
        if same_team_qb:
            print(f"  ✅ WR MVP Stack: QB from same team")
            for player in same_team_qb:
                positions = player["Positions"].split(",")
                print(f"    - {player['Name']} ({', '.join(positions)})")
        else:
            print(f"  ⚠️  WR MVP Stack: No QB from same team (constraint violation!)")
        
        if same_team_wr_te and Config.MVP_WR_MAX_SAME_TEAM_WR_TE >= 0:
            same_team_count = len(same_team_wr_te)
            max_allowed = Config.MVP_WR_MAX_SAME_TEAM_WR_TE
            if same_team_count <= max_allowed:
                print(f"  ✅ WR MVP Stack: {same_team_count}/{max_allowed} WR/TE from same team")
                for player in same_team_wr_te:
                    positions = player["Positions"].split(",")
                    print(f"    - {player['Name']} ({', '.join(positions)})")
            else:
                print(f"  ⚠️  WR MVP Stack: {same_team_count}/{max_allowed} WR/TE from same team (constraint violation!)")
        elif same_team_wr_te:
            print(f"  ℹ️  WR MVP Stack: {len(same_team_wr_te)} WR/TE from same team (rule disabled)")
            for player in same_team_wr_te:
                positions = player["Positions"].split(",")
                print(f"    - {player['Name']} ({', '.join(positions)})")
        else:
            print(f"  ℹ️  WR MVP Stack: No WR/TE from same team")
        
        if opp_team_wr_te and Config.MVP_WR_MIN_OPP_WR_TE > 0:
            opp_count = len(opp_team_wr_te)
            min_required = Config.MVP_WR_MIN_OPP_WR_TE
            if opp_count >= min_required:
                print(f"  ✅ WR MVP Stack: {opp_count}/{min_required} WR/TE from opponent team")
                for player in opp_team_wr_te:
                    positions = player["Positions"].split(",")
                    print(f"    - {player['Name']} ({', '.join(positions)})")
            else:
                print(f"  ⚠️  WR MVP Stack: {opp_count}/{min_required} WR/TE from opponent team (constraint violation!)")
        elif opp_team_wr_te:
            print(f"  ℹ️  WR MVP Stack: {len(opp_team_wr_te)} WR/TE from opponent team (rule disabled)")
            for player in opp_team_wr_te:
                positions = player["Positions"].split(",")
                print(f"    - {player['Name']} ({', '.join(positions)})")
        else:
            print(f"  ℹ️  WR MVP Stack: No WR/TE from opponent team")
    
    # Check if MVP is a TE
    elif "TE" in mvp_positions:
        # Find QB from same team
        same_team_qb = [p for p in lineup.players 
                       if p["Team"] == mvp_team and 
                       p["Id"] != mvp_player["Id"] and 
                       "QB" in p["Positions"].split(",")]
        
        # Find WR from same team (excluding the TE MVP itself)
        same_team_wr = [p for p in lineup.players 
                       if p["Team"] == mvp_team and 
                       p["Id"] != mvp_player["Id"] and 
                       "WR" in p["Positions"].split(",")]
        
        if same_team_qb:
            print(f"  ✅ TE MVP Stack: QB from same team")
            for player in same_team_qb:
                positions = player["Positions"].split(",")
                print(f"    - {player['Name']} ({', '.join(positions)})")
        else:
            print(f"  ⚠️  TE MVP Stack: No QB from same team (constraint violation!)")
        
        if same_team_wr and Config.MVP_TE_REQUIRE_EXACT_WR >= 0:
            wr_count = len(same_team_wr)
            exact_required = Config.MVP_TE_REQUIRE_EXACT_WR
            if wr_count == exact_required:
                print(f"  ✅ TE MVP Stack: {wr_count}/{exact_required} WR from same team (exact)")
                for player in same_team_wr:
                    positions = player["Positions"].split(",")
                    print(f"    - {player['Name']} ({', '.join(positions)})")
            elif wr_count > exact_required:
                print(f"  ⚠️  TE MVP Stack: {wr_count}/{exact_required} WR from same team (too many)")
                for player in same_team_wr:
                    positions = player["Positions"].split(",")
                    print(f"    - {player['Name']} ({', '.join(positions)})")
            else:
                print(f"  ⚠️  TE MVP Stack: {wr_count}/{exact_required} WR from same team (not enough)")
                for player in same_team_wr:
                    positions = player["Positions"].split(",")
                    print(f"    - {player['Name']} ({', '.join(positions)})")
        elif same_team_wr:
            print(f"  ℹ️  TE MVP Stack: {len(same_team_wr)} WR from same team (rule disabled)")
            for player in same_team_wr:
                positions = player["Positions"].split(",")
                print(f"    - {player['Name']} ({', '.join(positions)})")
        else:
            if Config.MVP_TE_REQUIRE_EXACT_WR >= 0:
                exact_required = Config.MVP_TE_REQUIRE_EXACT_WR
                print(f"  ⚠️  TE MVP Stack: 0/{exact_required} WR from same team (constraint violation!)")
            else:
                print(f"  ℹ️  TE MVP Stack: No WR from same team (rule disabled)")
    
    # Check if MVP is a Defense
    elif "D" in mvp_positions or "DST" in mvp_positions:
        # Find all teammates (excluding the defense itself)
        teammates = [p for p in lineup.players 
                    if p["Team"] == mvp_team and 
                    p["Id"] != mvp_player["Id"]]
        
        if teammates and Config.MVP_D_REQUIRE_TEAMMATES > 0:
            teammate_count = len(teammates)
            min_required = Config.MVP_D_REQUIRE_TEAMMATES
            if teammate_count >= min_required:
                print(f"  ✅ D MVP Stack: {teammate_count}/{min_required} teammates")
                for player in teammates:
                    positions = player["Positions"].split(",")
                    print(f"    - {player['Name']} ({', '.join(positions)})")
            else:
                print(f"  ⚠️  D MVP Stack: {teammate_count}/{min_required} teammates (constraint violation!)")
                for player in teammates:
                    positions = player["Positions"].split(",")
                    print(f"    - {player['Name']} ({', '.join(positions)})")
        elif teammates:
            print(f"  ℹ️  D MVP Stack: {len(teammates)} teammates (rule disabled)")
            for player in teammates:
                positions = player["Positions"].split(",")
                print(f"    - {player['Name']} ({', '.join(positions)})")
        else:
            if Config.MVP_D_REQUIRE_TEAMMATES > 0:
                min_required = Config.MVP_D_REQUIRE_TEAMMATES
                print(f"  ⚠️  D MVP Stack: 0/{min_required} teammates (constraint violation!)")
            else:
                print(f"  ℹ️  D MVP Stack: No teammates (rule disabled)")
    
    else:
        print(f"  ℹ️  Non-QB/RB/WR/TE/D MVP: {mvp_name}")

def create_lineup_model(players: List[Player], 
                       teams: List[str],
                       used_lineups_sets: List[Set[int]],
                       num_generated_lineups: int) -> Tuple[cp_model.CpModel, Dict]:
    """Create the constraint programming model for lineup optimization."""
    model = cp_model.CpModel()
    
    # Create player variables
    player_vars = {p.id: model.NewBoolVar(f"player_{p.id}") for p in players}
    assign = {}
    
    # Create assignment variables
    for p in players:
        assign[p.id] = {}
        for slot in Config.SLOTS:
            assign[p.id][slot] = model.NewBoolVar(f"assign_{p.id}_{slot}")
    
    # Add group constraints
    for group in Config.GROUP_CONSTRAINTS:
        group_player_ids = [p.id for p in players if p.name in group["players"]]
        if group_player_ids:
            # Add minimum constraint
            if "min" in group:
                model.Add(sum(player_vars[pid] for pid in group_player_ids) >= group["min"])
            # Add maximum constraint
            if "max" in group:
                model.Add(sum(player_vars[pid] for pid in group_player_ids) <= group["max"])
    
    # Add MVP-specific stacking rules
    if Config.ENABLE_MVP_STACKING:
        add_mvp_stacking_constraints(model, players, player_vars, assign)
    
    # Add conditional constraints
    for constraint in Config.CONDITIONAL_CONSTRAINTS:
        if_player_id = next((p.id for p in players if p.name == constraint["if_player"]), None)
        
        if if_player_id:
            # Create boolean variable for the if_position
            if_position = assign[if_player_id][constraint["if_position"]]
            
            # Handle player-to-player constraints
            if "then_player" in constraint:
                then_player_id = next((p.id for p in players if p.name == constraint["then_player"]), None)
                if then_player_id:
                    then_position = assign[then_player_id][constraint["then_position"]]
                    model.Add(if_position <= then_position)
            
            # Handle team stacking constraints
            if "then_team" in constraint:
                if "team_players" in constraint:
                    # Use specific players from the team
                    team_players = [p.id for p in players if p.name in constraint["team_players"]]
                else:
                    # Use all players from the team
                    team_players = [p.id for p in players if p.team == constraint["then_team"]]
                
                if team_players:
                    # Create a boolean variable for each team player
                    team_player_vars = [player_vars[pid] for pid in team_players]
                    # Add constraint: if if_position is True, then sum of team players must be >= min_team_players
                    model.Add(sum(team_player_vars) >= constraint["min_team_players"]).OnlyEnforceIf(if_position)
            
            # Handle multiple player conditional constraints
            if "then_players" in constraint:
                # Create a list to store all the player variables for group constraints
                group_player_vars = []
                
                for then_player in constraint["then_players"]:
                    then_player_id = next((p.id for p in players if p.name == then_player["name"]), None)
                    if then_player_id:
                        then_position = assign[then_player_id][then_player["position"]]
                        group_player_vars.append(then_position)
                        
                        # Add individual min/max constraints if specified
                        if "min" in then_player and then_player["min"] > 0:
                            model.Add(then_position >= then_player["min"]).OnlyEnforceIf(if_position)
                        
                        if "max" in then_player:
                            model.Add(then_position <= then_player["max"]).OnlyEnforceIf(if_position)
                
                # Handle group min/max constraints if specified
                if "group_min" in constraint and group_player_vars:
                    model.Add(sum(group_player_vars) >= constraint["group_min"]).OnlyEnforceIf(if_position)
                
                if "group_max" in constraint and group_player_vars:
                    model.Add(sum(group_player_vars) <= constraint["group_max"]).OnlyEnforceIf(if_position)
    
    # Add roster constraints
    for slot, count in Config.SLOTS.items():
        model.Add(sum(assign[p.id][slot] for p in players) == count)
    
    for p in players:
        model.Add(sum(assign[p.id][s] for s in assign[p.id]) <= 1)
        model.Add(sum(assign[p.id][s] for s in assign[p.id]) == player_vars[p.id])
    
    # MVP eligibility constraint
    if Config.MVP_ELIGIBLE_PLAYERS:  # Only apply constraint if list is not empty
        for p in players:
            player_name = p.name.split(":")[-1].strip()
            if player_name not in Config.MVP_ELIGIBLE_PLAYERS:
                model.Add(assign[p.id]["MVP"] == 0)
    
    # Total players constraint
    model.Add(sum(player_vars[p.id] for p in players) == 6)  # 6 players in NFL single-game lineup (1 MVP + 5 UTIL)
    
    # Salary constraints using appropriate salary for each slot
    mvp_salary = sum(p.mvp_salary * assign[p.id]["MVP"] for p in players)  # Use mvp_salary
    util_salary = sum(p.salary * assign[p.id]["UTIL"] for p in players)  # UTIL salary is normal
    total_salary = mvp_salary + util_salary
    
    model.Add(total_salary <= Config.MAX_SALARY)
    model.Add(total_salary >= Config.MIN_SALARY)
    
    # Team constraints - maximum 5 players per team
    for team in teams:
        team_players = [p for p in players if p.team == team]
        model.Add(sum(player_vars[p.id] for p in team_players) <= 5)
    
    # Onslaught constraint: If 5 players are from the same team, MVP must be from that team
    for team in teams:
        team_players = [p for p in players if p.team == team]
        if len(team_players) >= 5:  # Only add constraint if team has at least 5 players
            # Create a variable that is true if exactly 5 players from this team are in lineup
            team_count = sum(player_vars[p.id] for p in team_players)
            five_team_players = model.NewBoolVar(f"five_team_players_{team}")
            
            # five_team_players is true if team_count == 5
            model.Add(team_count == 5).OnlyEnforceIf(five_team_players)
            model.Add(team_count != 5).OnlyEnforceIf(five_team_players.Not())
            
            # If five_team_players is true, then MVP must be from this team
            team_mvp_players = [p for p in team_players]
            if team_mvp_players:
                # Sum of MVP assignments for this team's players
                team_mvp_sum = sum(assign[p.id]["MVP"] for p in team_mvp_players)
                # If five players from this team, require MVP to be from this team
                model.Add(team_mvp_sum >= 1).OnlyEnforceIf(five_team_players)
            
            # If five_team_players is true, then QB from this team must be included (MVP or UTIL)
            team_qbs = [p for p in team_players if "QB" in p.positions]
            if team_qbs:
                # Sum of all QB assignments for this team's QBs (MVP + UTIL)
                team_qb_sum = sum(player_vars[p.id] for p in team_qbs)
                # If five players from this team, require QB to be included
                model.Add(team_qb_sum >= 1).OnlyEnforceIf(five_team_players)
    
    # Add uniqueness constraints
    for prev in used_lineups_sets:
        # Ensure at least 1 unique player compared to previous lineups
        model.Add(sum(player_vars[pid] for pid in prev if pid in player_vars) <= 5)
    
    # Set objective using current_projection with appropriate multipliers
    mvp_projection = sum(p.current_projection * 1.5 * assign[p.id]["MVP"] for p in players)  # MVP gets 1.5x points
    util_projection = sum(p.current_projection * assign[p.id]["UTIL"] for p in players)  # UTIL gets normal points
    total_projection = mvp_projection + util_projection
    
    model.Maximize(total_projection)
    
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
                "MVP Ownership": p.mvp_ownership,
                "Projection Floor": p.projection_floor,
                "Projection Ceil": p.projection_ceil,
                "Id": p.id
            })
    
    return Lineup(lineup)

def print_lineup(lineup: Lineup, lineup_num: int, show_current_projections: bool = False) -> None:
    """Print the lineup in a formatted way."""
    print(f"=== Lineup {lineup_num} ===")
    
    # Sort players by slot order
    slot_order = {"MVP": 0, "UTIL": 1}
    sorted_players = sorted(lineup.players, key=lambda x: slot_order[x["Slot"]])
    
    for player in sorted_players:
        if player["Slot"] == "MVP":
            mvp_proj = player['current_projection'] * 1.5
            proj_str = f" | Proj: {mvp_proj:.2f} (1.5x points, Base: {player['current_projection']:.2f})"
            salary_str = f"${int(player.get('mvp_salary', player['Salary'] * 1.5))} (1.5x salary)"
        else:
            proj_str = f" | Proj: {player['current_projection']:.2f}"
            salary_str = f"${player['Salary']}"
        print(f"{player['Slot']}: {player['Name']} ({player['Team']}) | Salary: {salary_str}{proj_str}")
    
    # Calculate total salary using appropriate salary for each slot
    total_salary = sum(
        (player.get('mvp_salary', player['Salary'] * 1.5) if player['Slot'] == 'MVP'
         else player['Salary']) for player in lineup.players
    )
    total_original_projection = sum(
        p['Projection'] * (1.5 if p['Slot'] == 'MVP' else 1) 
        for p in lineup.players
    )
    total_current_projection = sum(
        p['current_projection'] * (1.5 if p['Slot'] == 'MVP' else 1) 
        for p in lineup.players
    )
    
    print(f"\nTotal Salary: ${total_salary}")
    print(f"Total Original Projection: {total_original_projection:.2f}")
    if show_current_projections:
        print(f"Total Current Projection: {total_current_projection:.2f}")
    
    # Print MVP stacking information
    print_mvp_stacking_info(lineup)

def calculate_lineup_metrics(lineups: List[Lineup]) -> List[Dict]:
    """Calculate z-scores, rankings, and average ranks for all lineups."""
    if not lineups:
        return []
    
    # Calculate metrics for each lineup
    lineup_metrics = []
    for lineup in lineups:
        # Calculate projections with MVP multiplier
        total_projection = sum(
            p["Projection"] * (1.5 if p["Slot"] == "MVP" else 1) 
            for p in lineup.players
        )
        
        # Calculate ceiling with MVP multiplier
        total_ceiling = sum(
            p.get("Projection Ceil", p["Projection"]) * (1.5 if p["Slot"] == "MVP" else 1) 
            for p in lineup.players
        )
        
        # Calculate ownership product considering MVP ownership for MVP slot
        ownership_product = 1.0
        for p in lineup.players:
            if p["Slot"] == "MVP":
                # Use MVP ownership for MVP slot (data is already in percentage form)
                ownership_value = p.get("MVP Ownership", p["Ownership"])  # No division by 100
            else:
                # Use regular ownership for UTIL slots (data is already in percentage form)
                ownership_value = p["Ownership"]  # No division by 100
            ownership_product *= max(ownership_value, 0.0001)  # Avoid zero
        
        # Ownership sum (for reference)
        total_ownership_sum = sum(
            (p.get("MVP Ownership", p["Ownership"]) if p["Slot"] == "MVP" else p["Ownership"])
            for p in lineup.players
        )
        
        lineup_metrics.append({
            "lineup": lineup,
            "Total_Projection": total_projection,
            "Total_Ceiling": total_ceiling,
            "Total_Ownership_Product": ownership_product * 100,  # as percentage
            "Total_Ownership_Sum": total_ownership_sum
        })
    
    # Calculate z-scores for each metric
    metrics = ["Total_Projection", "Total_Ceiling", "Total_Ownership_Product"]
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

def export_to_csv(lineups: List[Lineup], output_path: str) -> None:
    """Export lineups to a CSV file with detailed metrics and sorting."""
    if not lineups:
        print("No lineups to export")
        return
    
    # Calculate metrics for all lineups
    lineup_metrics = calculate_lineup_metrics(lineups)
    
    # Sort by Average_Rank (ascending) and take top 150
    lineup_metrics.sort(key=lambda x: x["Average_Rank"])
    top_lineups = lineup_metrics[:150]  # Filter to top 150 ranked lineups
    print(f"Filtered to top {len(top_lineups)} lineups (sorted by Average_Rank)")
    
    # FanDuel slot order for single-game contests
    fd_order = ['MVP', 'UTIL', 'UTIL', 'UTIL', 'UTIL', 'UTIL']
    slot_names = ['MVP', 'UTIL1', 'UTIL2', 'UTIL3', 'UTIL4', 'UTIL5']
    
    data = []
    for i, lm in enumerate(top_lineups, 1):
        lineup = lm["lineup"]
        
        # Build slot-to-player mapping
        slot_map = {slot: [] for slot in set(fd_order)}
        for player in lineup.players:
            slot = player["Slot"]
            if slot in slot_map:
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
            if not found:
                row[slot_names[idx]] = ""
        
        # Summary columns
        row["Total_Projection"] = lm["Total_Projection"]
        row["Total_Salary"] = sum(
            (player.get('mvp_salary', player['Salary'] * 1.5) if player['Slot'] == 'MVP'
             else player['Salary']) for player in lineup.players
        )
        row["Total_Ceiling"] = lm["Total_Ceiling"]
        
        # Ownership product and sum
        row["Total_Ownership_Product"] = f'{lm["Total_Ownership_Product"]:.10f}%'
        row["Total_Ownership_Sum"] = lm["Total_Ownership_Sum"]
        
        # Z-scores
        row["Projection_ZScore"] = lm["Total_Projection_ZScore"]
        row["Ceiling_ZScore"] = lm["Total_Ceiling_ZScore"]
        row["Ownership_ZScore"] = lm["Total_Ownership_Product_ZScore"]
        
        # Rankings
        row["Projection_Rank"] = lm["Total_Projection_Rank"]
        row["Ceiling_Rank"] = lm["Total_Ceiling_Rank"]
        row["Ownership_Rank"] = lm["Total_Ownership_Product_Rank"]
        
        # Average Rank
        row["Average_Rank"] = lm["Average_Rank"]
        
        data.append(row)
    
    # Create DataFrame
    columns = slot_names + [
        "Total_Projection", "Total_Salary",
        "Total_Ceiling", 
        "Total_Ownership_Product", "Total_Ownership_Sum",
        "Projection_ZScore", "Ceiling_ZScore", "Ownership_ZScore",
        "Projection_Rank", "Ceiling_Rank", "Ownership_Rank",
        "Average_Rank"
    ]
    
    df = pd.DataFrame(data, columns=columns)
    
    # Export to CSV
    df.to_csv(output_path, index=False)
    print(f"Exported {len(data)} lineups to {output_path}")

def main():
    """Main function to run the lineup optimizer."""
    try:
        # Load and process data
        df = load_and_clean_data(Config.DATA_FILE)
        players = create_player_objects(df)
        teams = list(set(p.team for p in players))
        
        # Initialize smart randomness
        smart_randomness = None
        if Config.ENABLE_SMART_RANDOMNESS:
            smart_randomness = SmartRandomness(players, Config.DISTRIBUTION_TYPE, Config.RANDOMNESS_SEED)
            
            # Apply smart randomness once at the start if frequency is per_session
            if Config.RANDOMNESS_FREQUENCY == "per_session":
                for player in players:
                    if player.std_dev:
                        player.current_projection = smart_randomness.apply_randomness(player.id, player.projection)
        
        # Initialize tracking variables
        generated_lineups = []
        used_lineups_sets = []
        player_counts = {}  # Track player exposure
        projection_tracker = PlayerProjectionTracker()
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
                for player in players:
                    if player.std_dev:
                        player.current_projection = smart_randomness.apply_randomness(player.id, player.projection)
            
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
        
        # Export lineups with detailed metrics and sorting
        output_path = "/Users/adamsardinha/Desktop/FD_NFL_Single_Game_Lineups.csv"
        export_to_csv(generated_lineups, output_path)
        print(f"\nExported lineups to {output_path}")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main() 