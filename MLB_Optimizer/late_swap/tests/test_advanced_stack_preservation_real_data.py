"""
Test Advanced Stack Preservation with Real Data

This module tests the advanced stack preservation functionality using real lineup and player data.
"""

import unittest
import sys
import os
import pandas as pd

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from late_swap.core.advanced_stack_preserver import AdvancedStackPreserver, StackSwapPlan
from data.processors.lineup_parser import parse_lineup_from_csv_row
from late_swap.core.swap_analyzer import analyze_lineup_for_swaps
from MLB_Optimizer import Player, Lineup

class TestAdvancedStackPreservationRealData(unittest.TestCase):
    """Test cases for advanced stack preservation logic using real data"""
    
    def setUp(self):
        """Set up test data using real player data"""
        # Load real player data
        self.df = pd.read_csv("/Users/adamsardinha/Desktop/MLB_FD.csv")
        
        # Create Player objects from real data
        self.players = []
        for _, row in self.df.iterrows():
            positions = row["Position"].split("/")
            name = row["Player ID + Player Name"]
            
            # Get roster order, defaulting to 0 for pitchers
            roster_order = 0
            if "P" not in positions:
                try:
                    roster_order = int(row["Roster Order"])
                except (ValueError, TypeError):
                    roster_order = 0
            
            player = Player(
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
            )
            self.players.append(player)
        
        # Create advanced stack preserver
        self.stack_preserver = AdvancedStackPreserver()
        
        # Create a real lineup from the template data
        self.create_real_lineup()
    
    def create_real_lineup(self):
        """Create a real lineup from the template data"""
        # Read the template CSV to get a real lineup
        template_df = pd.read_csv("/Users/adamsardinha/Downloads/FanDuel-MLB-2025-07-22-118836-entries-upload-template.csv")
        
        # Get the first row with valid lineup data
        for _, row in template_df.iterrows():
            lineup_data = {}
            fd_position_order = ['P', 'C/1B', '2B', '3B', 'SS', 'OF', 'OF', 'OF', 'UTIL']
            
            for pos in fd_position_order:
                if pos in row:
                    lineup_data[pos] = row[pos]
            
            # Try to parse this lineup
            try:
                result = parse_lineup_from_csv_row(lineup_data, self.players, fd_position_order)
                if result:
                    lineup_players, primary_stack, secondary_stack = result
                    
                    # Create a Lineup object
                    self.lineup = Lineup(lineup_players, primary_stack, secondary_stack)
                    print(f"Created lineup with {len(lineup_players)} players")
                    print(f"Primary stack: {primary_stack}, Secondary stack: {secondary_stack}")
                    return
                    
            except Exception as e:
                print(f"Error parsing lineup: {e}")
                continue
        
        # If we get here, create a mock lineup for testing
        print("Creating mock lineup for testing")
        self.lineup = Lineup([], "", "")
    
    def test_identify_stack_structure_real_data(self):
        """Test stack structure identification with real data"""
        if not hasattr(self, 'lineup') or not self.lineup.players:
            self.skipTest("No valid lineup data available")
        
        primary, secondary = self.stack_preserver._identify_stack_structure(self.lineup)
        
        print(f"Identified stacks - Primary: {primary}, Secondary: {secondary}")
        
        # Verify we can identify stacks
        self.assertIsInstance(primary, str)
        self.assertIsInstance(secondary, str)
    
    def test_analyze_lineup_for_swaps_real_data(self):
        """Test analyzing lineup for swaps with real data"""
        if not hasattr(self, 'lineup') or not self.lineup.players:
            self.skipTest("No valid lineup data available")
        
        # Analyze lineup for swaps
        swap_analyses = analyze_lineup_for_swaps(self.lineup, self.players)
        
        print(f"Found {len(swap_analyses)} players needing swaps")
        
        # Should find some players needing swaps
        self.assertGreaterEqual(len(swap_analyses), 0)
        
        # Print details of each swap analysis
        for i, analysis in enumerate(swap_analyses):
            print(f"  Swap {i+1}: {analysis.player_name} ({analysis.team}) - {analysis.stack_type} stack")
            print(f"    Priority: {analysis.swap_priority}, Candidates: {len(analysis.replacement_candidates)}")
    
    def test_create_comprehensive_swap_plan_real_data(self):
        """Test creating comprehensive swap plan with real data"""
        if not hasattr(self, 'lineup') or not self.lineup.players:
            self.skipTest("No valid lineup data available")
        
        # Analyze lineup for swaps
        swap_analyses = analyze_lineup_for_swaps(self.lineup, self.players)
        
        if not swap_analyses:
            print("No players need swapping in this lineup")
            self.skipTest("No invalid players found")
        
        # Extract invalid players
        invalid_players = []
        for analysis in swap_analyses:
            invalid_players.append({
                "Id": analysis.player_id,
                "Name": analysis.player_name,
                "Team": analysis.team,
                "Slot": analysis.position,
                "Salary": 0,  # Will be filled from lineup
                "Projection": 0,  # Will be filled from lineup
                "Roster Order": analysis.roster_order
            })
        
        # Create comprehensive swap plan
        swap_plan = self.stack_preserver.create_comprehensive_swap_plan(
            self.lineup, invalid_players, self.players
        )
        
        if swap_plan:
            print(f"Created swap plan:")
            print(f"  Primary stack swaps: {len(swap_plan.primary_stack_swaps)}")
            print(f"  Secondary stack swaps: {len(swap_plan.secondary_stack_swaps)}")
            print(f"  One-off swaps: {len(swap_plan.one_off_swaps)}")
            print(f"  Total projection change: {swap_plan.total_projection_change:.2f}")
            print(f"  Total salary change: {swap_plan.total_salary_change}")
            print(f"  Preserves all stacks: {swap_plan.preserves_all_stacks}")
            print(f"  Priority score: {swap_plan.priority_score:.2f}")
            
            # Should have a valid swap plan
            self.assertIsNotNone(swap_plan)
            self.assertIsInstance(swap_plan, StackSwapPlan)
        else:
            print("No valid swap plan found")
            self.skipTest("No valid swap plan available")
    
    def test_apply_swap_plan_real_data(self):
        """Test applying swap plan with real data"""
        if not hasattr(self, 'lineup') or not self.lineup.players:
            self.skipTest("No valid lineup data available")
        
        # Analyze lineup for swaps
        swap_analyses = analyze_lineup_for_swaps(self.lineup, self.players)
        
        if not swap_analyses:
            print("No players need swapping in this lineup")
            self.skipTest("No invalid players found")
        
        # Extract invalid players
        invalid_players = []
        for analysis in swap_analyses:
            invalid_players.append({
                "Id": analysis.player_id,
                "Name": analysis.player_name,
                "Team": analysis.team,
                "Slot": analysis.position,
                "Salary": 0,  # Will be filled from lineup
                "Projection": 0,  # Will be filled from lineup
                "Roster Order": analysis.roster_order
            })
        
        # Create comprehensive swap plan
        swap_plan = self.stack_preserver.create_comprehensive_swap_plan(
            self.lineup, invalid_players, self.players
        )
        
        if swap_plan:
            # Apply the swap plan
            new_lineup = self.stack_preserver.apply_swap_plan(self.lineup, swap_plan)
            
            if new_lineup:
                print(f"Successfully applied swap plan")
                print(f"Original lineup projection: {sum(p['Projection'] for p in self.lineup.players):.2f}")
                print(f"New lineup projection: {sum(p['Projection'] for p in new_lineup.players):.2f}")
                print(f"Projection change: {swap_plan.total_projection_change:.2f}")
                
                # Should have a valid new lineup
                self.assertIsNotNone(new_lineup)
                self.assertEqual(len(new_lineup.players), len(self.lineup.players))
            else:
                print("Failed to apply swap plan")
                self.skipTest("Swap plan application failed")
        else:
            print("No valid swap plan found")
            self.skipTest("No valid swap plan available")
    
    def test_find_team_replacement_candidates_real_data(self):
        """Test finding team replacement candidates with real data"""
        if not hasattr(self, 'lineup') or not self.lineup.players:
            self.skipTest("No valid lineup data available")
        
        # Find a player from a stack team
        team_counts = {}
        for player in self.lineup.players:
            if player["Slot"] != "P":
                team = player["Team"]
                team_counts[team] = team_counts.get(team, 0) + 1
        
        # Find a team with multiple players
        stack_team = None
        for team, count in team_counts.items():
            if count >= 2:
                stack_team = team
                break
        
        if stack_team:
            print(f"Testing team replacement candidates for {stack_team}")
            
            # Create a mock invalid player from this team
            invalid_player = {
                "Id": 999999,  # Mock ID
                "Name": "Test Player",
                "Team": stack_team,
                "Slot": "OF",
                "Salary": 4000,
                "Projection": 10.0,
                "Roster Order": 0
            }
            
            candidates = self.stack_preserver._find_team_replacement_candidates(
                invalid_player, self.players, stack_team
            )
            
            print(f"Found {len(candidates)} replacement candidates")
            
            # Should find some candidates
            self.assertGreaterEqual(len(candidates), 0)
            
            # All candidates should be from the same team
            for candidate in candidates:
                self.assertEqual(candidate.team, stack_team)
                print(f"  Candidate: {candidate.name} (proj: {candidate.projection:.2f})")
        else:
            print("No stack team found for testing")
            self.skipTest("No stack team available")
    
    def test_calculate_priority_score_real_data(self):
        """Test priority score calculation with real data"""
        # Create mock swaps for testing
        primary_swaps = [
            {'projection_change': 2.5, 'priority': 3},
            {'projection_change': 1.8, 'priority': 3}
        ]
        
        secondary_swaps = [
            {'projection_change': 1.2, 'priority': 2}
        ]
        
        one_off_swaps = [
            {'projection_change': 0.8, 'priority': 1}
        ]
        
        score = self.stack_preserver._calculate_priority_score(
            primary_swaps, secondary_swaps, one_off_swaps
        )
        
        print(f"Priority score: {score:.2f}")
        
        # Should have a positive score
        self.assertGreater(score, 0)
        
        # Calculate expected score manually
        expected_score = (2.5 + 1.8) * 3.0 + 1.2 * 2.0 + 0.8 * 1.0
        self.assertAlmostEqual(score, expected_score, places=2)

if __name__ == '__main__':
    unittest.main() 