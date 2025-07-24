"""
College Football Standard Daily Fantasy Sports Lineup Optimizer
This script generates optimized lineups for College Football standard DFS contests using constraint programming.
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
    DATA_FILE = "/Users/adamsardinha/Desktop/CFB_Standard_FD.csv"
    
    # Lineup generation settings
    NUM_LINEUPS_TO_GENERATE = 500
    MAX_SALARY = 60000  # FanDuel standard salary cap
    MIN_SALARY = 59000  # Minimum salary to ensure quality lineups
    MAX_ATTEMPTS = 500
    
    # Minimum projection to include a player in the pool
    MIN_PROJECTION = 8
    
    # Team stacking rules
    MAX_PLAYERS_PER_TEAM = 4  # Maximum players from one team
    

    
    # Roster settings for FanDuel College Football classic contests
    SLOTS = {
        "QB": 1,
        "RB": 2,
        "WR": 3,
        "SUPER_FLEX": 1
    }
    
    # Stacking settings
    MIN_QB_WR_STACK = 1  # Minimum WRs to stack with QB
    MAX_QB_WR_STACK = 2  # Maximum WRs to stack with QB
    
    # Stars-and-scrubs settings
    ENABLE_STARS_AND_SCRUBS = True  # Enable stars-and-scrubs strategy
    MIN_PREMIUM_RB_COUNT = 1  # Minimum number of premium RBs to include
    MAX_PREMIUM_RB_COUNT = 2  # Maximum number of premium RBs to include
    PREMIUM_RB_PERCENTILE = 75  # Top 25% of RBs by salary are premium
    CHEAP_WR_PERCENTILE = 25  # Bottom 25% of WRs by salary are cheap
    MIN_CHEAP_WR_COUNT = 1  # Minimum number of cheap WRs to include
    MAX_CHEAP_WR_COUNT = 2  # Maximum number of cheap WRs to include
    
    # Players to exclude from lineups
    EXCLUDED_PLAYERS = [
        # Add players to exclude here
    ]
    
    
    # Teams to exclude from stacking
    EXCLUDED_TEAMS = [
        # Add teams to exclude from stacking here
    ]

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
    ceiling: float = 0.0  # Ceiling projection for the player

    def __post_init__(self):
        self.current_projection = self.projection  # Initialize current projection



@dataclass
class Lineup:
    players: List[Dict]
    
    @property
    def lineup(self):
        """Convert our players to the correct FanDuel College Football order."""
        fd_position_order = ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'SUPER_FLEX']
        # Create a mapping of positions to players
        position_map = {pos: [] for pos in ['QB', 'RB', 'WR', 'SUPER_FLEX']}
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
    
    # Handle ceiling column if it exists
    if "Ceiling" in df.columns:
        df["Ceiling"] = pd.to_numeric(df["Ceiling"], errors="coerce")
    
    df["Position"] = df["Position"].astype(str)
    
    return df

def create_player_objects(df: pd.DataFrame) -> List[Player]:
    """Convert DataFrame rows to Player objects."""
    players = []
    for _, row in df.iterrows():
        positions = row["Position"].split("/")
        name = f"{row['First Name']} {row['Last Name']}"
        
        # Filter out players with projection under MIN_PROJECTION
        projection = round(row["FPPG"], 2)
        if projection < Config.MIN_PROJECTION:
            continue
        
        # Get ceiling projection (default to 1.5x projection if not available)
        ceiling = float(row.get("Ceiling", projection * 1.5))
        
        players.append(Player(
            id=row["Id"],
            name=name,
            positions=positions,
            team=row["Team"],
            opponent=row["Opponent"],
            salary=int(row["Salary"]),
            projection=projection,
            ownership=float(row.get("Projected Ownership", 0)),
            ceiling=ceiling
        ))
    return players

def calculate_percentile_thresholds(players: List[Player]) -> Dict[str, float]:
    """Calculate dynamic salary thresholds based on percentiles."""
    thresholds = {}
    
    # Calculate RB salary percentiles
    rb_salaries = [p.salary for p in players if "RB" in p.positions]
    if rb_salaries:
        rb_salaries.sort()
        premium_index = int(len(rb_salaries) * Config.PREMIUM_RB_PERCENTILE / 100)
        thresholds['premium_rb'] = rb_salaries[premium_index]
    
    # Calculate WR salary percentiles
    wr_salaries = [p.salary for p in players if "WR" in p.positions]
    if wr_salaries:
        wr_salaries.sort()
        cheap_index = int(len(wr_salaries) * Config.CHEAP_WR_PERCENTILE / 100)
        thresholds['cheap_wr'] = wr_salaries[cheap_index]
    
    return thresholds

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
            # Super FLEX can only be filled by QBs
            if slot == "SUPER_FLEX":
                can_play = "QB" in p.positions
            else:
                can_play = slot in p.positions
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
    

    
    # Total players constraint
    model.Add(sum(player_vars[p.id] for p in players) == 7)  # 7 players in CFB lineup
    
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
    
    # QB stacking constraints - ensure each QB is paired with 1-2 WRs from their team
    for team in teams:
        if team not in Config.EXCLUDED_TEAMS:
            team_qbs = [p for p in players if p.team == team and "QB" in p.positions]
            team_wrs = [p for p in players if p.team == team and "WR" in p.positions]
            
            # For each QB on this team, ensure they stack with 1-2 WRs from same team
            for qb in team_qbs:
                # Count how many WRs from same team are used with this QB
                qb_wr_stack_count = sum(player_vars[wr.id] for wr in team_wrs)
                
                # If this QB is used (in either QB slot or Super FLEX), ensure 1-2 WRs from same team are also used
                model.Add(qb_wr_stack_count >= Config.MIN_QB_WR_STACK).OnlyEnforceIf(player_vars[qb.id])
                model.Add(qb_wr_stack_count <= Config.MAX_QB_WR_STACK).OnlyEnforceIf(player_vars[qb.id])
    
    # Ensure we have exactly 2 QBs total (1 in QB slot + 1 in Super FLEX)
    qb_players = [p for p in players if "QB" in p.positions]
    total_qbs = sum(player_vars[p.id] for p in qb_players)
    model.Add(total_qbs == 2)
    
    # Max 2 WRs per team constraint
    for team in teams:
        if team not in Config.EXCLUDED_TEAMS:
            team_wrs = [p for p in players if p.team == team and "WR" in p.positions]
            team_wr_count = sum(player_vars[p.id] for p in team_wrs)
            model.Add(team_wr_count <= 2)
    
    # Stars-and-scrubs constraints
    if Config.ENABLE_STARS_AND_SCRUBS:
        # Calculate dynamic thresholds based on percentiles
        thresholds = calculate_percentile_thresholds(players)
        
        # Define premium RBs and cheap WRs using dynamic thresholds
        premium_rbs = [p for p in players if "RB" in p.positions and p.salary >= thresholds.get('premium_rb', 0)]
        cheap_wrs = [p for p in players if "WR" in p.positions and p.salary <= thresholds.get('cheap_wr', float('inf'))]
        
        # Count premium RBs and cheap WRs in lineup
        premium_rb_count = sum(player_vars[p.id] for p in premium_rbs)
        cheap_wr_count = sum(player_vars[p.id] for p in cheap_wrs)
        
        # Ensure minimum and maximum premium RBs
        model.Add(premium_rb_count >= Config.MIN_PREMIUM_RB_COUNT)
        model.Add(premium_rb_count <= Config.MAX_PREMIUM_RB_COUNT)
        
        # Ensure minimum and maximum cheap WRs
        model.Add(cheap_wr_count >= Config.MIN_CHEAP_WR_COUNT)
        model.Add(cheap_wr_count <= Config.MAX_CHEAP_WR_COUNT)
    
    # Uniqueness constraint: ensure at least 3 unique players between lineups
    for prev in used_lineups_sets:
        # Count how many players are in common with this previous lineup
        common_players = sum(player_vars[pid] for pid in prev if pid in player_vars)
        
        # Ensure at least 3 unique players (7 total - 4 common = 3 unique minimum)
        model.Add(common_players <= 4)
    
    # Set objective using projection
    model.Maximize(sum(p.projection * player_vars[p.id] for p in players))
    
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
                "Ceiling": p.ceiling,
                "Ownership": p.ownership,
                "Id": p.id
            })
    
    return Lineup(lineup)

def print_lineup(lineup: Lineup, lineup_num: int, players: List[Player] = None) -> None:
    """Print the lineup in a formatted way."""
    print(f"=== Lineup {lineup_num} ===")
    
    # Sort players by slot order
    slot_order = {"QB": 0, "RB": 1, "WR": 2, "SUPER_FLEX": 3}
    sorted_players = sorted(lineup.players, key=lambda x: slot_order[x["Slot"]])
    
    for player in sorted_players:
        player_name = player['Name'].split(":")[-1].strip()
        proj_str = f" | Proj: {player['Projection']:.2f}"
        
        # Add stars-and-scrubs indicators
        if Config.ENABLE_STARS_AND_SCRUBS:
            # Calculate thresholds for display
            thresholds = calculate_percentile_thresholds(players)
            if player['Slot'] == 'RB' and player['Salary'] >= thresholds.get('premium_rb', 0):
                proj_str += " [PREMIUM]"
            elif player['Slot'] == 'WR' and player['Salary'] <= thresholds.get('cheap_wr', float('inf')):
                proj_str += " [CHEAP]"
        
        print(f"{player['Slot']}: {player['Name']} ({player['Team']}) | Salary: ${player['Salary']}{proj_str}")
    
    total_salary = sum(p['Salary'] for p in lineup.players)
    total_projection = sum(p['Projection'] for p in lineup.players)
    print(f"\nTotal Salary: ${total_salary}")
    print(f"Total Projection: {total_projection:.2f}")

def calculate_lineup_metrics(lineup: Lineup) -> Dict[str, float]:
    """Calculate metrics for a lineup."""
    projection_sum = sum(p['Projection'] for p in lineup.players)
    ceiling_sum = sum(p['Ceiling'] for p in lineup.players)
    
    # Calculate product of ownership (ownership is already in percentage form)
    ownership_product = 1.0
    for p in lineup.players:
        ownership_decimal = p['Ownership'] / 100.0 if p['Ownership'] > 0 else 0.01  # Convert percentage to decimal
        ownership_product *= ownership_decimal
    
    return {
        'projection_sum': projection_sum,
        'ceiling_sum': ceiling_sum,
        'ownership_product': ownership_product
    }

def rank_lineups(lineups: List[Lineup]) -> List[Tuple[Lineup, Dict]]:
    """Rank lineups based on multiple metrics and return top 150."""
    lineup_metrics = []
    
    for lineup in lineups:
        metrics = calculate_lineup_metrics(lineup)
        lineup_metrics.append((lineup, metrics))
    
    # Sort by projection sum (highest first)
    projection_ranked = sorted(lineup_metrics, key=lambda x: x[1]['projection_sum'], reverse=True)
    
    # Sort by ceiling sum (highest first)
    ceiling_ranked = sorted(lineup_metrics, key=lambda x: x[1]['ceiling_sum'], reverse=True)
    
    # Sort by ownership product (lowest first - lower is better)
    ownership_ranked = sorted(lineup_metrics, key=lambda x: x[1]['ownership_product'])
    
    # Create ranking dictionaries
    projection_ranks = {lineup: rank for rank, (lineup, _) in enumerate(projection_ranked, 1)}
    ceiling_ranks = {lineup: rank for rank, (lineup, _) in enumerate(ceiling_ranked, 1)}
    ownership_ranks = {lineup: rank for rank, (lineup, _) in enumerate(ownership_ranked, 1)}
    
    # Calculate average rank for each lineup
    ranked_lineups = []
    for lineup, metrics in lineup_metrics:
        avg_rank = (projection_ranks[lineup] + ceiling_ranks[lineup] + ownership_ranks[lineup]) / 3
        ranked_lineups.append((lineup, metrics, avg_rank))
    
    # Sort by average rank (lowest first)
    ranked_lineups.sort(key=lambda x: x[2])
    
    # Return top 150 lineups
    return ranked_lineups[:150]

def export_to_csv(lineups: List[Lineup], output_path: str) -> None:
    """Export lineups to a CSV file in FanDuel format with metrics and rankings."""
    # Rank lineups and get top 150
    ranked_lineups = rank_lineups(lineups)
    
    fd_position_order = ['QB', 'RB', 'RB', 'WR', 'WR', 'WR', 'SUPER_FLEX']
    
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Write header with metrics
        header = fd_position_order + ['Projection_Sum', 'Ceiling_Sum', 'Ownership_Product', 'Avg_Rank']
        writer.writerow(header)
        
        for lineup, metrics, avg_rank in ranked_lineups:
            position_map = {pos: [] for pos in ['QB', 'RB', 'WR', 'SUPER_FLEX']}
            for player in lineup.players:
                position_map[player["Slot"]].append(player)
            
            row = []
            for pos in fd_position_order:
                if position_map[pos]:
                    row.append(position_map[pos].pop(0)["Id"])
            
            # Add metrics
            row.extend([
                round(metrics['projection_sum'], 2),
                round(metrics['ceiling_sum'], 2),
                round(metrics['ownership_product'], 6),
                round(avg_rank, 2)
            ])
            
            writer.writerow(row)
    
    print(f"Exported top 150 ranked lineups to {output_path}")
    print(f"Metrics included: Projection Sum, Ceiling Sum, Ownership Product, Average Rank")

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
            print_lineup(lineup, len(generated_lineups), players=players)
            
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
        
        # Calculate and display ranking statistics
        print("\nRanking Statistics:")
        ranked_lineups = rank_lineups(generated_lineups)
        if ranked_lineups:
            top_lineup, top_metrics, top_rank = ranked_lineups[0]
            print(f"Top Lineup - Projection Sum: {top_metrics['projection_sum']:.2f}, "
                  f"Ceiling Sum: {top_metrics['ceiling_sum']:.2f}, "
                  f"Ownership Product: {top_metrics['ownership_product']:.6f}, "
                  f"Average Rank: {top_rank:.2f}")
        
        # Export top 150 ranked lineups
        output_path = "/Users/adamsardinha/Desktop/FD_CFB_Standard_Lineups.csv"
        export_to_csv(generated_lineups, output_path)
        print(f"\nGenerated {len(generated_lineups)} total lineups, exported top 150 ranked lineups to {output_path}")
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main() 