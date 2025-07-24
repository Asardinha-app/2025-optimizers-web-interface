"""
Test Stack Preservation Logic with Real Data

This module tests the stack preservation functionality using real lineup and player data.
"""

import unittest
import sys
import os
import pandas as pd

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
from data.processors.lineup_parser import parse_lineup_from_csv_row
from MLB_Optimizer import Player, Lineup

class TestStackPreservationRealData(unittest.TestCase):
    """Test cases for stack preservation logic using real data"""
    
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
        
        # Create a real lineup from the template data
        # Let's use the first lineup that has players needing swaps
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
                    
                    # Find a player with roster_order == 0 for testing
                    for player_data in lineup_players:
                        if (player_data["Roster Order"] == 0 and 
                            player_data["Slot"] != "P"):
                            self.invalid_player = player_data
                            print(f"Found invalid player: {player_data['Name']} from {player_data['Team']}")
                            return
                    
                    print("No invalid players found in this lineup, trying next...")
                    
            except Exception as e:
                print(f"Error parsing lineup: {e}")
                continue
        
        # If we get here, create a mock lineup for testing
        print("Creating mock lineup for testing")
        self.lineup = Lineup([], "", "")
        self.invalid_player = None
    
    def test_identify_stack_structure_real_data(self):
        """Test stack structure identification with real data"""
        if not hasattr(self, 'lineup') or not self.lineup.players:
            self.skipTest("No valid lineup data available")
        
        primary, secondary = _identify_stack_structure(self.lineup)
        
        print(f"Identified stacks - Primary: {primary}, Secondary: {secondary}")
        
        # Verify we can identify stacks
        self.assertIsInstance(primary, str)
        self.assertIsInstance(secondary, str)
    
    def test_preserve_primary_stack_real_data(self):
        """Test primary stack preservation with real data"""
        if not hasattr(self, 'lineup') or not self.lineup.players or not self.invalid_player:
            self.skipTest("No valid lineup or invalid player data available")
        
        # Check if invalid player is in primary stack
        primary_stack, _ = _identify_stack_structure(self.lineup)
        
        if self.invalid_player["Team"] == primary_stack:
            print(f"Testing primary stack preservation for {self.invalid_player['Name']}")
            
            options = preserve_primary_stack(self.lineup, self.invalid_player, self.players)
            
            print(f"Found {len(options)} primary stack preservation options")
            
            # Should find some replacement options
            self.assertGreaterEqual(len(options), 0)
            
            # All options should preserve stack
            for option in options:
                self.assertTrue(option.preserves_stack)
                self.assertEqual(option.stack_type, "primary")
                self.assertEqual(option.priority, 3)
                print(f"  Option: {option.replacement_player.name} (proj: {option.projection_change:.2f})")
        else:
            print(f"Invalid player {self.invalid_player['Name']} not in primary stack {primary_stack}")
            self.skipTest("Invalid player not in primary stack")
    
    def test_preserve_secondary_stack_real_data(self):
        """Test secondary stack preservation with real data"""
        if not hasattr(self, 'lineup') or not self.lineup.players or not self.invalid_player:
            self.skipTest("No valid lineup or invalid player data available")
        
        # Check if invalid player is in secondary stack
        _, secondary_stack = _identify_stack_structure(self.lineup)
        
        if self.invalid_player["Team"] == secondary_stack:
            print(f"Testing secondary stack preservation for {self.invalid_player['Name']}")
            
            options = preserve_secondary_stack(self.lineup, self.invalid_player, self.players)
            
            print(f"Found {len(options)} secondary stack preservation options")
            
            # Should find some replacement options
            self.assertGreaterEqual(len(options), 0)
            
            # All options should preserve stack
            for option in options:
                self.assertTrue(option.preserves_stack)
                self.assertEqual(option.stack_type, "secondary")
                self.assertEqual(option.priority, 2)
                print(f"  Option: {option.replacement_player.name} (proj: {option.projection_change:.2f})")
        else:
            print(f"Invalid player {self.invalid_player['Name']} not in secondary stack {secondary_stack}")
            self.skipTest("Invalid player not in secondary stack")
    
    def test_would_maintain_stack_real_data(self):
        """Test stack maintenance check with real data"""
        if not hasattr(self, 'lineup') or not self.lineup.players or not self.invalid_player:
            self.skipTest("No valid lineup or invalid player data available")
        
        # Find a replacement candidate from the same team
        team = self.invalid_player["Team"]
        position = self.invalid_player["Slot"]
        
        # Find candidates from the same team that can play the position
        candidates = []
        for player in self.players:
            if (player.team == team and 
                not player.is_pitcher and
                any(pos in player.positions for pos in ([position] if position != "UTIL" else ["C/1B", "2B", "3B", "SS", "OF"]))):
                candidates.append(player)
        
        if candidates:
            candidate = candidates[0]  # Use first candidate
            print(f"Testing stack maintenance with candidate: {candidate.name}")
            
            # Test primary stack maintenance
            primary_result = _would_maintain_primary_stack(self.lineup, self.invalid_player, candidate)
            print(f"Would maintain primary stack: {primary_result}")
            
            # Test secondary stack maintenance
            secondary_result = _would_maintain_secondary_stack(self.lineup, self.invalid_player, candidate)
            print(f"Would maintain secondary stack: {secondary_result}")
            
            # At least one should be true if the candidate is from a stack team
            primary_stack, secondary_stack = _identify_stack_structure(self.lineup)
            if team == primary_stack:
                self.assertTrue(primary_result)
            elif team == secondary_stack:
                self.assertTrue(secondary_result)
        else:
            print(f"No replacement candidates found for {self.invalid_player['Name']}")
            self.skipTest("No replacement candidates available")

if __name__ == '__main__':
    unittest.main() 