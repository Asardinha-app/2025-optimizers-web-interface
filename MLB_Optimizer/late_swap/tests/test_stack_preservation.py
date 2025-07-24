"""
Test Stack Preservation Logic

This module tests the stack preservation functionality for the Late Swap Optimizer.
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from late_swap.core.stack_preserver import (
    preserve_primary_stack,
    preserve_secondary_stack,
    SwapOption,
    _identify_stack_structure,
    _would_maintain_primary_stack,
    _would_maintain_secondary_stack
)

class TestStackPreservation(unittest.TestCase):
    """Test cases for stack preservation logic"""
    
    def setUp(self):
        """Set up test data"""
        # Create a mock lineup with a primary stack (4 players from same team)
        self.lineup = Mock()
        self.lineup.players = [
            {"Name": "Pitcher A", "Team": "TEAM1", "Slot": "P", "Salary": 8500, "Projection": 25.0},
            {"Name": "Batter A1", "Team": "TEAM2", "Slot": "C/1B", "Salary": 4000, "Projection": 12.0},
            {"Name": "Batter A2", "Team": "TEAM2", "Slot": "2B", "Salary": 3800, "Projection": 11.0},
            {"Name": "Batter A3", "Team": "TEAM2", "Slot": "3B", "Salary": 4200, "Projection": 13.0},
            {"Name": "Batter A4", "Team": "TEAM2", "Slot": "SS", "Salary": 4100, "Projection": 12.5},
            {"Name": "Batter B1", "Team": "TEAM3", "Slot": "OF", "Salary": 3500, "Projection": 10.0},
            {"Name": "Batter B2", "Team": "TEAM3", "Slot": "OF", "Salary": 3600, "Projection": 10.5},
            {"Name": "Batter B3", "Team": "TEAM3", "Slot": "OF", "Salary": 3700, "Projection": 11.0},
            {"Name": "Batter C1", "Team": "TEAM4", "Slot": "UTIL", "Salary": 3000, "Projection": 9.0},
        ]
        
        # Create mock players for testing
        self.players = [
            Mock(id=1, name="Replacement A1", team="TEAM2", positions=["C/1B"], 
                 salary=4000, projection=12.5, is_pitcher=False),
            Mock(id=2, name="Replacement A2", team="TEAM2", positions=["2B"], 
                 salary=3800, projection=11.5, is_pitcher=False),
            Mock(id=3, name="Replacement A3", team="TEAM2", positions=["3B"], 
                 salary=4200, projection=13.5, is_pitcher=False),
            Mock(id=4, name="Replacement A4", team="TEAM2", positions=["SS"], 
                 salary=4100, projection=12.8, is_pitcher=False),
        ]
        
        # Invalid player from primary stack
        self.invalid_player = {
            "Name": "Batter A1",
            "Team": "TEAM2",
            "Slot": "C/1B",
            "Salary": 4000,
            "Projection": 12.0,
            "Roster Order": 0
        }
    
    def test_identify_stack_structure(self):
        """Test stack structure identification"""
        primary, secondary = _identify_stack_structure(self.lineup)
        
        # TEAM2 should be primary stack (4 players)
        self.assertEqual(primary, "TEAM2")
        # TEAM3 should be secondary stack (3 players)
        self.assertEqual(secondary, "TEAM3")
    
    def test_preserve_primary_stack(self):
        """Test primary stack preservation"""
        options = preserve_primary_stack(self.lineup, self.invalid_player, self.players)
        
        # Should find replacement options
        self.assertGreater(len(options), 0)
        
        # All options should preserve stack
        for option in options:
            self.assertTrue(option.preserves_stack)
            self.assertEqual(option.stack_type, "primary")
            self.assertEqual(option.priority, 3)
    
    def test_would_maintain_primary_stack(self):
        """Test primary stack maintenance check"""
        candidate = self.players[0]  # Replacement A1
        
        # Should maintain primary stack (same team, same position)
        result = _would_maintain_primary_stack(self.lineup, self.invalid_player, candidate)
        self.assertTrue(result)
    
    def test_would_maintain_secondary_stack(self):
        """Test secondary stack maintenance check"""
        # Create a candidate from secondary stack team
        candidate = Mock(id=5, name="Replacement B1", team="TEAM3", positions=["OF"], 
                        salary=3500, projection=10.5, is_pitcher=False)
        
        # Create invalid player from secondary stack
        invalid_player = {
            "Name": "Batter B1",
            "Team": "TEAM3",
            "Slot": "OF",
            "Salary": 3500,
            "Projection": 10.0,
            "Roster Order": 0
        }
        
        result = _would_maintain_secondary_stack(self.lineup, invalid_player, candidate)
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main() 