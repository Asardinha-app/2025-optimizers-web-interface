"""
Test Projection Filtering for Late Swap Optimizer

This module tests that the late swap optimizer correctly filters out players
with projections <= 0, only considering players with positive projections.
"""

import unittest
import sys
import os
import pandas as pd

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from late_swap.core.swap_analyzer import find_replacement_candidates
from late_swap.core.advanced_stack_preserver import AdvancedStackPreserver
from late_swap.core.multi_swap_optimizer import MultiSwapOptimizer
from late_swap.core.late_swap_engine import LateSwapEngine
from MLB_Optimizer import Player, Lineup

class TestProjectionFiltering(unittest.TestCase):
    """Test cases for projection filtering functionality"""
    
    def setUp(self):
        """Set up test data with players having different projections"""
        # Create test players with various projections
        self.players = [
            Player(id=1, name="Player A", positions=["OF"], team="TEAM1", opponent="TEAM2", 
                   salary=4000, projection=12.5, is_pitcher=False, ownership=0.1, roster_order=1),
            Player(id=2, name="Player B", positions=["OF"], team="TEAM1", opponent="TEAM2", 
                   salary=3800, projection=0.0, is_pitcher=False, ownership=0.05, roster_order=2),
            Player(id=3, name="Player C", positions=["OF"], team="TEAM1", opponent="TEAM2", 
                   salary=4200, projection=-1.5, is_pitcher=False, ownership=0.02, roster_order=3),
            Player(id=4, name="Player D", positions=["OF"], team="TEAM2", opponent="TEAM1", 
                   salary=4100, projection=15.2, is_pitcher=False, ownership=0.15, roster_order=4),
            Player(id=5, name="Player E", positions=["OF"], team="TEAM2", opponent="TEAM1", 
                   salary=3900, projection=0.0, is_pitcher=False, ownership=0.08, roster_order=5),
            Player(id=6, name="Player F", positions=["OF"], team="TEAM3", opponent="TEAM4", 
                   salary=4300, projection=8.7, is_pitcher=False, ownership=0.12, roster_order=6),
        ]
        
        # Create a test lineup
        self.lineup = Lineup([
            {"Id": 999, "Name": "Invalid Player", "Team": "TEAM1", "Slot": "OF", 
             "Salary": 4000, "Projection": 10.0, "Roster Order": 0}
        ], "TEAM1", "TEAM2")
    
    def test_swap_analyzer_projection_filtering(self):
        """Test that swap analyzer filters out players with projections <= 0"""
        invalid_player = {
            "Id": 999,
            "Name": "Invalid Player",
            "Team": "TEAM1",
            "Slot": "OF",
            "Salary": 4000,
            "Projection": 10.0,
            "Roster Order": 0
        }
        
        candidates = find_replacement_candidates(invalid_player, self.players, self.lineup)
        
        print(f"Found {len(candidates)} candidates after projection filtering")
        
        # Should only find players with positive projections
        self.assertGreater(len(candidates), 0)
        
        for candidate in candidates:
            print(f"  Candidate: {candidate.name} - projection: {candidate.projection}")
            self.assertGreater(candidate.projection, 0)
        
        # Should not include players with zero or negative projections
        zero_projection_players = [p for p in candidates if p.projection <= 0]
        self.assertEqual(len(zero_projection_players), 0)
    
    def test_advanced_stack_preserver_projection_filtering(self):
        """Test that advanced stack preserver filters out players with projections <= 0"""
        stack_preserver = AdvancedStackPreserver()
        
        invalid_player = {
            "Id": 999,
            "Name": "Invalid Player",
            "Team": "TEAM1",
            "Slot": "OF",
            "Salary": 4000,
            "Projection": 10.0,
            "Roster Order": 0
        }
        
        # Test team replacement candidates
        candidates = stack_preserver._find_team_replacement_candidates(
            invalid_player, self.players, "TEAM1"
        )
        
        print(f"Found {len(candidates)} team candidates after projection filtering")
        
        # Should only find players with positive projections
        for candidate in candidates:
            print(f"  Team candidate: {candidate.name} - projection: {candidate.projection}")
            self.assertGreater(candidate.projection, 0)
        
        # Test position replacement candidates
        candidates = stack_preserver._find_position_replacement_candidates(
            invalid_player, self.players
        )
        
        print(f"Found {len(candidates)} position candidates after projection filtering")
        
        # Should only find players with positive projections
        for candidate in candidates:
            print(f"  Position candidate: {candidate.name} - projection: {candidate.projection}")
            self.assertGreater(candidate.projection, 0)
    
    def test_multi_swap_optimizer_projection_filtering(self):
        """Test that multi-swap optimizer filters out players with projections <= 0"""
        optimizer = MultiSwapOptimizer()
        
        invalid_player = {
            "Id": 999,
            "Name": "Invalid Player",
            "Team": "TEAM1",
            "Slot": "OF",
            "Salary": 4000,
            "Projection": 10.0,
            "Roster Order": 0
        }
        
        candidates = optimizer._find_all_candidates(invalid_player, self.players)
        
        print(f"Found {len(candidates)} multi-swap candidates after projection filtering")
        
        # Should only find players with positive projections
        for candidate in candidates:
            print(f"  Multi-swap candidate: {candidate.name} - projection: {candidate.projection}")
            self.assertGreater(candidate.projection, 0)
    
    def test_late_swap_engine_projection_filtering(self):
        """Test that late swap engine filters out players with projections <= 0"""
        engine = LateSwapEngine()
        
        invalid_player = {
            "Id": 999,
            "Name": "Invalid Player",
            "Team": "TEAM1",
            "Slot": "OF",
            "Salary": 4000,
            "Projection": 10.0,
            "Roster Order": 0
        }
        
        candidates = engine._find_simple_replacement(invalid_player, self.players)
        
        print(f"Found {len(candidates)} simple replacement candidates after projection filtering")
        
        # Should only find players with positive projections
        for candidate in candidates:
            print(f"  Simple replacement candidate: {candidate.name} - projection: {candidate.projection}")
            self.assertGreater(candidate.projection, 0)
    
    def test_projection_distribution(self):
        """Test the distribution of projections in the test data"""
        positive_projections = [p for p in self.players if p.projection > 0]
        zero_projections = [p for p in self.players if p.projection == 0]
        negative_projections = [p for p in self.players if p.projection < 0]
        
        print(f"Projection distribution in test data:")
        print(f"  Positive projections: {len(positive_projections)}")
        print(f"  Zero projections: {len(zero_projections)}")
        print(f"  Negative projections: {len(negative_projections)}")
        
        # Should have a mix of projections for testing
        self.assertGreater(len(positive_projections), 0)
        self.assertGreater(len(zero_projections), 0)
        self.assertGreater(len(negative_projections), 0)
        
        # Print details of each category
        for player in positive_projections:
            print(f"    Positive: {player.name} - {player.projection}")
        for player in zero_projections:
            print(f"    Zero: {player.name} - {player.projection}")
        for player in negative_projections:
            print(f"    Negative: {player.name} - {player.projection}")

if __name__ == '__main__':
    unittest.main() 