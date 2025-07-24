"""
NBA Single Game Daily Fantasy Sports Lineup Optimizer
This script generates optimized lineups for NBA single-game DFS contests using constraint programming.
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
    DATA_FILE = "/Users/adamsardinha/Desktop/NBA_Single_Game_FD.csv"
    
    # Lineup generation settings
    NUM_LINEUPS_TO_GENERATE = 1000
    MAX_SALARY = 60000  # FanDuel single-game salary cap
    MIN_SALARY = 57000  # Minimum salary to ensure quality lineups
    MAX_ATTEMPTS = 1000
    MIN_PLAYER_PROJECTION = 8.0  # Minimum fantasy points projection for players
    
    # Stack rules
    ENABLED_STACK_RULES = False
    MAX_PLAYERS_PER_TEAM = 5  # Maximum players from one team
    

    
    # Roster settings for FanDuel single-game contests
    SLOTS = {
        "MVP": 1,    # 1.5x points and salary
        "UTIL": 5    # 1x points
    }
    
    # Exposure settings
    RECENT_PLAYERS_WINDOW = 5  # Number of recent lineups to track for each player
    MIN_PLAYER_EXPOSURE = 0.05  # Minimum exposure for each player
    
    # MVP eligibility settings
    MVP_ELIGIBLE_PLAYERS = [
"Tyrese Haliburton",
"Andrew Nembhard",
"Aaron Nesmith",
"Pascal Siakam",
"Myles Turner",
"Shai Gilgeous-Alexander",
"Luguentz Dort",
"Jalen Williams",
"Chet Holmgren",
    ]
    
    # Group constraints
    GROUP_CONSTRAINTS = [

        # {
        #     "name": "OKC Cheap Stack",
        #     "players": ["Cason Wallace", "Aaron Wiggins","Jaylin Williams"],
        #     "min": 0,  # Minimum number of players from this group
        #     "max": 1   # Maximum number of players from this group
        # },
        # {
        #     "name": "OKC Core Stack",
        #     "players": ["Jalen Williams", "Chet Holmgren", "Isaiah Hartenstein","Alex Caruso","Shai Gilgeous-Alexander"],
        #     "min": 2,  # Minimum number of players from this group
        #     # "max": 1   # Maximum number of players from this group
        # },
        
    ]
    
    # Conditional constraints
    CONDITIONAL_CONSTRAINTS = [

       
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

    def __post_init__(self):
        self.current_projection = self.projection  # Initialize current projection



@dataclass
class Lineup:
    players: List[Dict]
    
    @property
    def lineup(self):
        """Convert our players to LineupPlayer objects expected by FanDuelCSVLineupExporter."""
        # Define FanDuel's required position order for single-game contests
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
        
        # Check if this player has bounce or boost settings
        bounce = Config.BOUNCE_SETTINGS.get(name.split(":")[-1].strip(), 0.0)
        boost = Config.BOOST_SETTINGS.get(name.split(":")[-1].strip(), 0.0)
        
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
            bounce=bounce,
            boost=boost
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
    model.Add(sum(player_vars[p.id] for p in players) == 6)  # 6 players in single-game lineup (1 MVP + 5 UTIL)
    
    # Salary constraints using mvp_salary for MVPs
    mvp_salary = sum(p.mvp_salary * assign[p.id]["MVP"] for p in players)  # Use mvp_salary
    util_salary = sum(p.salary * assign[p.id]["UTIL"] for p in players)  # UTIL salary is normal
    total_salary = mvp_salary + util_salary
    
    model.Add(total_salary <= Config.MAX_SALARY)
    model.Add(total_salary >= Config.MIN_SALARY)
    
    # Team constraints
    for team in teams:
        team_players = [p for p in players if p.team == team]
        model.Add(sum(player_vars[p.id] for p in team_players) <= Config.MAX_PLAYERS_PER_TEAM)
    
    # Add uniqueness constraints
    for prev in used_lineups_sets:
        # Ensure at least 1 unique player compared to previous lineups
        model.Add(sum(player_vars[pid] for pid in prev if pid in player_vars) <= 5)
    
    # Set objective using current_projection with MVP multiplier
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
    
    # Calculate total salary using mvp_salary for MVPs
    total_salary = sum((player.get('mvp_salary', player['Salary'] * 1.5) if player['Slot'] == 'MVP' else player['Salary']) for player in lineup.players)
    total_original_projection = sum(p['Projection'] * (1.5 if p['Slot'] == 'MVP' else 1) for p in lineup.players)
    total_current_projection = sum(p['current_projection'] * (1.5 if p['Slot'] == 'MVP' else 1) for p in lineup.players)
    
    print(f"\nTotal Salary: ${total_salary}")
    print(f"Total Original Projection: {total_original_projection:.2f}")
    if show_current_projections:
        print(f"Total Current Projection: {total_current_projection:.2f}")

def export_to_csv(lineups: List[Lineup], output_path: str) -> None:
    """Export lineups to a CSV file in FanDuel format."""
    # FanDuel's position order for single-game contests
    fd_position_order = ['MVP', 'UTIL', 'UTIL', 'UTIL', 'UTIL', 'UTIL']
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        # Write header
        writer.writerow(fd_position_order)
        
        # Write each lineup
        for lineup in lineups:
            # Create position map for this lineup
            position_map = {}
            util_candidates = []
            
            for player in lineup.players:
                if player["Slot"] == "UTIL":
                    util_candidates.append(player)
                else:
                    position_map[player["Slot"]] = player
            
            # Build row in FanDuel's order
            row = []
            for pos in fd_position_order:
                if pos == 'UTIL':
                    if util_candidates:
                        player = util_candidates.pop(0)
                        row.append(player["Id"])
                else:
                    if pos in position_map:
                        player = position_map[pos]
                        row.append(player["Id"])
            
            writer.writerow(row)

def main():
    """Main function to run the lineup optimizer."""
    try:
        # Load and process data
        df = load_and_clean_data(Config.DATA_FILE)
        players = create_player_objects(df)
        teams = list(set(p.team for p in players))
        
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
        output_path = "/Users/adamsardinha/Desktop/FD_NBA_Single_Game_Lineups_Raw.csv"
        export_to_csv(generated_lineups, output_path)
        print(f"\nExported lineups to {output_path}")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main() 