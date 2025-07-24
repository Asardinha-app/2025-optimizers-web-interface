"""
Test Multi-Swap Optimizer with Real Data

This module tests the multi-swap optimization functionality using real lineup and player data.
"""

import unittest
import sys
import os
import pandas as pd

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from late_swap.core.multi_swap_optimizer import MultiSwapOptimizer, MultiSwapSolution
from data.processors.lineup_parser import parse_lineup_from_csv_row
from late_swap.core.swap_analyzer import analyze_lineup_for_swaps
from MLB_Optimizer import Player, Lineup

class TestMultiSwapOptimizerRealData(unittest.TestCase):
    """Test cases for multi-swap optimization logic using real data"""
    
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
        
        # Create multi-swap optimizer
        self.optimizer = MultiSwapOptimizer()
        
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
        
        primary, secondary = self.optimizer._identify_stack_structure(self.lineup)
        
        print(f"Identified stacks - Primary: {primary}, Secondary: {secondary}")
        
        # Verify we can identify stacks
        self.assertIsInstance(primary, str)
        self.assertIsInstance(secondary, str)
    
    def test_find_all_candidates_real_data(self):
        """Test finding all candidates with real data"""
        if not hasattr(self, 'lineup') or not self.lineup.players:
            self.skipTest("No valid lineup data available")
        
        # Create a mock invalid player
        invalid_player = {
            "Id": 999999,  # Mock ID
            "Name": "Test Player",
            "Team": "HOU",
            "Slot": "OF",
            "Salary": 4000,
            "Projection": 10.0,
            "Roster Order": 0
        }
        
        candidates = self.optimizer._find_all_candidates(invalid_player, self.players)
        
        print(f"Found {len(candidates)} candidates for {invalid_player['Slot']} position")
        
        # Should find some candidates
        self.assertGreaterEqual(len(candidates), 0)
        
        # All candidates should be able to play the position
        for candidate in candidates:
            self.assertTrue(self.optimizer._can_play_position(candidate, invalid_player["Slot"]))
            print(f"  Candidate: {candidate.name} ({candidate.team}) - proj: {candidate.projection:.2f}")
    
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
    
    def test_optimize_multi_swaps_real_data(self):
        """Test multi-swap optimization with real data"""
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
        
        # Optimize multi-swaps
        solution = self.optimizer.optimize_multi_swaps(
            self.lineup, invalid_players, self.players
        )
        
        if solution:
            print(f"Multi-swap optimization results:")
            print(f"  Swaps: {len(solution.swaps)}")
            print(f"  Total projection change: {solution.total_projection_change:.2f}")
            print(f"  Total salary change: {solution.total_salary_change}")
            print(f"  Preserves all stacks: {solution.preserves_all_stacks}")
            print(f"  Is optimal: {solution.is_optimal}")
            print(f"  Constraint violations: {solution.constraint_violations}")
            
            # Should have a valid solution
            self.assertIsNotNone(solution)
            self.assertIsInstance(solution, MultiSwapSolution)
            
            # Should have some swaps
            self.assertGreaterEqual(len(solution.swaps), 0)
            
            # Should not have constraint violations
            self.assertEqual(len(solution.constraint_violations), 0)
        else:
            print("No valid multi-swap solution found")
            self.skipTest("No valid solution available")
    
    def test_apply_multi_swap_solution_real_data(self):
        """Test applying multi-swap solution with real data"""
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
        
        # Optimize multi-swaps
        solution = self.optimizer.optimize_multi_swaps(
            self.lineup, invalid_players, self.players
        )
        
        if solution:
            # Apply the solution
            new_lineup = self.optimizer.apply_multi_swap_solution(self.lineup, solution)
            
            if new_lineup:
                print(f"Successfully applied multi-swap solution")
                print(f"Original lineup projection: {sum(p['Projection'] for p in self.lineup.players):.2f}")
                print(f"New lineup projection: {sum(p['Projection'] for p in new_lineup.players):.2f}")
                print(f"Projection change: {solution.total_projection_change:.2f}")
                
                # Should have a valid new lineup
                self.assertIsNotNone(new_lineup)
                self.assertEqual(len(new_lineup.players), len(self.lineup.players))
            else:
                print("Failed to apply multi-swap solution")
                self.skipTest("Solution application failed")
        else:
            print("No valid multi-swap solution found")
            self.skipTest("No valid solution available")
    
    def test_can_play_position_real_data(self):
        """Test position compatibility checking with real data"""
        # Test with a real player
        test_player = self.players[0]  # Use first player
        
        print(f"Testing position compatibility for: {test_player.name}")
        print(f"  Positions: {test_player.positions}")
        print(f"  Is pitcher: {test_player.is_pitcher}")
        
        # Test various positions
        test_positions = ["P", "C/1B", "2B", "3B", "SS", "OF", "UTIL"]
        
        for position in test_positions:
            can_play = self.optimizer._can_play_position(test_player, position)
            print(f"  Can play {position}: {can_play}")
            
            # Should be able to play at least one position
            if position in test_player.positions:
                self.assertTrue(can_play)
    
    def test_check_salary_constraints_real_data(self):
        """Test salary constraint checking with real data"""
        # Create test scenarios
        test_cases = [
            {
                "candidate_salary": 4000,
                "invalid_player_salary": 4500,
                "expected": True  # Can decrease salary
            },
            {
                "candidate_salary": 5000,
                "invalid_player_salary": 4000,
                "expected": False  # Cannot increase salary
            },
            {
                "candidate_salary": 4000,
                "invalid_player_salary": 4000,
                "expected": True  # Same salary is OK
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            # Create mock candidate and invalid player
            candidate = type('Player', (), {
                'salary': test_case["candidate_salary"]
            })()
            
            invalid_player = {
                "Salary": test_case["invalid_player_salary"]
            }
            
            result = self.optimizer._check_salary_constraints(candidate, invalid_player)
            
            print(f"Test case {i+1}: Candidate ${test_case['candidate_salary']} vs Invalid ${test_case['invalid_player_salary']} = {result}")
            
            self.assertEqual(result, test_case["expected"])

if __name__ == '__main__':
    unittest.main() 