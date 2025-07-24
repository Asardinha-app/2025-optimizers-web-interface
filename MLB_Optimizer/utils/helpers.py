#!/usr/bin/env python3
"""
Simple Lineup Parser for MLB Late Swap Optimizer

This is a clean, simple parser that avoids all state persistence issues.
"""

import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

def parse_lineup_simple(
    lineup_data: Dict, 
    player_pool: List, 
    fd_position_order: List[str]
) -> Optional[Tuple[List[Dict], str, str]]:
    """
    Simple lineup parser that avoids state persistence issues
    Optimized for performance with minimal logging
    """
    # Only log errors and warnings
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Extract player IDs from CSV columns
        player_ids = []
        
        # Handle OF positions specially - get all OF columns (OF, OF.1, OF.2)
        of_columns = []
        for col in lineup_data.keys():
            if col == 'OF' or col.startswith('OF.'):
                of_columns.append(col)
        
        of_index = 0
        
        for pos in fd_position_order:
            if pos == 'OF':
                # Handle multiple OF columns (OF, OF.1, OF.2)
                if of_index < len(of_columns):
                    of_col = of_columns[of_index]
                    player_id = lineup_data[of_col]
                    if player_id and str(player_id).strip():
                        player_ids.append(str(player_id).strip())
                    else:
                        logger.warning(f"Missing player ID for position {of_col}")
                        return None
                    of_index += 1
                else:
                    logger.warning(f"Not enough OF columns for position {pos}")
                    return None
            elif pos in lineup_data:
                player_id = lineup_data[pos]
                if player_id and str(player_id).strip():
                    player_ids.append(str(player_id).strip())
                else:
                    logger.warning(f"Missing player ID for position {pos}")
                    return None
        
        if len(player_ids) != 9:
            logger.warning(f"Invalid lineup - expected 9 players, got {len(player_ids)}")
            return None
        
        # Create a lookup dictionary for faster player finding
        # Handle both full ID format (118836-52142) and numeric ID format
        player_lookup = {}
        for p in player_pool:
            # Store both the full ID and the numeric part
            player_lookup[str(p.id)] = p
            # Also store the numeric part after the dash if it exists
            if '-' in str(p.id):
                numeric_part = str(p.id).split('-')[-1]
                player_lookup[numeric_part] = p
        
        # Create player objects for the lineup
        lineup_players = []
        for i, player_id in enumerate(player_ids):
            # Try to find player by full ID first, then by numeric part
            player = None
            if player_id in player_lookup:
                player = player_lookup[player_id]
            else:
                # Try to extract numeric part from the ID
                try:
                    if '-' in player_id:
                        numeric_part = player_id.split('-')[-1]
                        if numeric_part in player_lookup:
                            player = player_lookup[numeric_part]
                except:
                    pass
            
            if not player:
                logger.warning(f"Player ID {player_id} not found in player pool")
                return None
            
            # Create player dict for lineup
            player_dict = {
                "Id": player.id,
                "Name": player.name,
                "Team": player.team,
                "Position": player.positions[0] if player.positions else "UNK",
                "Salary": player.salary,
                "Projection": player.projection,
                "Roster Order": player.roster_order,
                "Slot": fd_position_order[i]
            }
            
            lineup_players.append(player_dict)
        
        # Identify stacks (simplified for performance)
        primary_stack = None
        secondary_stack = None
        
        # Count players by team
        team_counts = {}
        for player in lineup_players:
            team = player["Team"]
            team_counts[team] = team_counts.get(team, 0) + 1
        
        # Find primary stack (team with most players)
        if team_counts:
            primary_stack = max(team_counts.items(), key=lambda x: x[1])[0]
        
        # Find secondary stack (team with second most players, if any)
        if len(team_counts) > 1:
            sorted_teams = sorted(team_counts.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_teams) > 1 and sorted_teams[1][1] >= 2:
                secondary_stack = sorted_teams[1][0]
        
        return lineup_players, primary_stack, secondary_stack
        
    except Exception as e:
        logger.error(f"Error in simple lineup parser: {str(e)}")
        return None

def assign_slot_simple(player, expected_slot: str, existing_players: List[Dict]) -> Optional[str]:
    """
    Simple slot assignment that tries the expected slot first
    
    Args:
        player: Player object
        expected_slot: Expected slot based on position order
        existing_players: List of already assigned players
        
    Returns:
        Slot name or None if no valid slot available
    """
    # Count existing players by slot
    slot_counts = {}
    for p in existing_players:
        slot = p["Slot"]
        slot_counts[slot] = slot_counts.get(slot, 0) + 1
    
    slot_limits = {
        "P": 1, "C/1B": 1, "2B": 1, "3B": 1, "SS": 1, "OF": 3, "UTIL": 1
    }
    
    # Try expected slot first
    if can_play_position_simple(player, expected_slot):
        current_count = slot_counts.get(expected_slot, 0)
        max_count = slot_limits.get(expected_slot, 1)
        if current_count < max_count:
            return expected_slot
    
    # Try alternative slots
    for slot, max_count in slot_limits.items():
        current_count = slot_counts.get(slot, 0)
        if current_count < max_count and can_play_position_simple(player, slot):
            return slot
    
    return None

def can_play_position_simple(player, slot: str) -> bool:
    """
    Simple position matching with strict pitcher/position player separation
    
    Args:
        player: Player object
        slot: Position slot
        
    Returns:
        True if player can play the position
    """
    # Pitcher slot - only pitchers can play P
    if slot == "P":
        return player.is_pitcher
    
    # Non-pitcher slots - only non-pitchers can play these
    if player.is_pitcher:
        return False
    
    # C/1B slot - accept C, 1B, or C/1B
    if slot == "C/1B":
        return any(pos in ["C", "1B", "C/1B"] for pos in player.positions)
    
    # UTIL slot - any non-pitcher can play UTIL
    if slot == "UTIL":
        return True
    
    # Specific position slots - must have that position
    if slot in player.positions:
        return True
    
    return False

def identify_stacks_simple(lineup_players: List[Dict]) -> Tuple[str, str]:
    """
    Simple stack identification
    
    Args:
        lineup_players: List of player dictionaries
        
    Returns:
        Tuple of (primary_stack, secondary_stack)
    """
    # Count players by team (excluding pitcher)
    team_counts = {}
    for player in lineup_players:
        if player["Slot"] != "P":  # Exclude pitcher
            team = player["Team"]
            team_counts[team] = team_counts.get(team, 0) + 1
    
    # Find teams with most players
    sorted_teams = sorted(team_counts.items(), key=lambda x: x[1], reverse=True)
    
    primary_stack = sorted_teams[0][0] if sorted_teams else ""
    secondary_stack = sorted_teams[1][0] if len(sorted_teams) > 1 else ""
    
    return primary_stack, secondary_stack 