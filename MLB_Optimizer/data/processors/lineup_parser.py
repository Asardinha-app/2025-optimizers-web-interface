"""
Lineup Parser for MLB Late Swap Optimizer

This module handles parsing lineup data from CSV format and creating lineup objects.
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ParsedPlayer:
    """Parsed player data from CSV"""
    id: int
    name: str
    team: str
    opponent: str
    positions: List[str]
    salary: int
    projection: float
    ownership: float
    roster_order: int
    is_pitcher: bool
    slot: Optional[str] = None

def parse_lineup_from_csv_row(
    lineup_data: Dict, 
    player_pool: List, 
    fd_position_order: List[str]
) -> Optional[Tuple[List[Dict], str, str]]:
    """
    Parse lineup from CSV row data
    
    Args:
        lineup_data: Dictionary containing CSV row data or list-based format
        player_pool: List of available players
        fd_position_order: FanDuel position order
        
    Returns:
        Tuple of (lineup_players, primary_stack, secondary_stack) or None if invalid
    """
    try:
        # Extract player IDs from CSV columns
        player_ids = []
        
        # Handle different data formats
        if 'players' in lineup_data:
            # List-based format from main optimizer
            player_ids = lineup_data['players']
        else:
            # Dictionary format from CSV handler
            # Create a mapping for OF positions
            of_columns = [col for col in lineup_data.keys() if col.startswith('OF')]
            of_index = 0
            
            for pos in fd_position_order:
                if pos == 'OF':
                    # Handle multiple OF columns (OF, OF.1, OF.2, etc.)
                    if of_index < len(of_columns):
                        of_col = of_columns[of_index]
                        player_id = lineup_data[of_col]
                        if player_id and str(player_id).strip():
                            try:
                                # Handle FanDuel format: "118836-198625" -> use the full ID
                                player_id_str = str(player_id).strip()
                                if '-' in player_id_str:
                                    # Use the full contest ID + player ID format
                                    player_ids.append(player_id_str)
                                else:
                                    player_ids.append(player_id_str)
                            except ValueError:
                                logger.warning(f"Invalid player ID for position {of_col}: {player_id}")
                                return None
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
                        try:
                            # Handle FanDuel format: "118836-198625" -> use the full ID
                            player_id_str = str(player_id).strip()
                            if '-' in player_id_str:
                                # Use the full contest ID + player ID format
                                player_ids.append(player_id_str)
                            else:
                                player_ids.append(player_id_str)
                        except ValueError:
                            logger.warning(f"Invalid player ID for position {pos}: {player_id}")
                            return None
                    else:
                        logger.warning(f"Missing player ID for position {pos}")
                        return None
        
        if len(player_ids) != 9:
            logger.warning(f"Invalid lineup - expected 9 players, got {len(player_ids)}")
            return None
        
        # Create player objects for this lineup - ensure clean state
        lineup_players = []
        seen_player_ids = set()  # Track seen player IDs to prevent duplicates
        duplicate_positions = []  # Track which positions have duplicates
        
        # Debug: log the start of parsing
        logger.debug(f"Starting to parse lineup with {len(player_ids)} player IDs")
        logger.debug(f"Initial lineup_players length: {len(lineup_players)}")
        
        # Ensure we start with a completely clean state
        if len(lineup_players) != 0:
            logger.warning(f"Lineup players list not empty at start: {len(lineup_players)} players")
            lineup_players = []  # Force reset
        
        for i, player_id in enumerate(player_ids):
            # Extract the ID part (before the colon if present)
            # Template format: "118836-198625:Yoshinobu Yamamoto"
            # We need just: "118836-198625"
            if ':' in player_id:
                player_id = player_id.split(':')[0]
            
            # Extract numeric ID from the full ID string with better error handling
            try:
                if '-' in player_id:
                    # Format: "118836-198625" -> extract "198625"
                    numeric_id = int(player_id.split('-')[-1])
                else:
                    # Format: "198625" -> use directly
                    numeric_id = int(player_id)
            except ValueError:
                logger.warning(f"Invalid player ID format: {player_id}")
                return None
            
            # Check for duplicate players in this lineup
            if numeric_id in seen_player_ids:
                position = fd_position_order[i]
                logger.warning(f"Duplicate player ID in lineup: {numeric_id} at position {position}")
                duplicate_positions.append((position, numeric_id))
                # Continue processing to identify all duplicates
            seen_player_ids.add(numeric_id)
            
            # Find player by numeric ID
            player = next((p for p in player_pool if p.id == numeric_id), None)
            
            if not player:
                logger.warning(f"Player ID {player_id} (numeric: {numeric_id}) not found in player pool")
                return None
            
            # Determine slot assignment - be more flexible about position matching
            logger.debug(f"Trying to assign slot for player {player.name} (positions: {player.positions})")
            logger.debug(f"Current lineup_players length: {len(lineup_players)}")
            slot = _determine_slot_flexible(player, lineup_players)
            if not slot:
                logger.warning(f"Could not assign any slot for player {player.name} (positions: {player.positions})")
                # Debug: print more details
                logger.warning(f"Player ID: {player.id}, Team: {player.team}")
                logger.warning(f"Existing lineup players: {len(lineup_players)}")
                return None
            
            lineup_players.append({
                "Slot": slot,
                "Name": player.name,
                "Team": player.team,
                "Opponent": player.opponent,
                "Positions": ",".join(player.positions),
                "Salary": player.salary,
                "Projection": player.projection,
                "Ownership": player.ownership,
                "Id": player.id,
                "Roster Order": player.roster_order
            })
        
        # If we found duplicates, provide detailed error information
        if duplicate_positions:
            logger.warning("Lineup contains duplicate players:")
            for position, player_id in duplicate_positions:
                logger.warning(f"  Position {position}: Player ID {player_id}")
            logger.warning("This lineup cannot be processed due to duplicate players")
            return None
        
        # Identify primary and secondary stacks
        primary_stack, secondary_stack = _identify_stacks(lineup_players)
        
        return lineup_players, primary_stack, secondary_stack
        
    except Exception as e:
        logger.error(f"Error parsing lineup: {str(e)}")
        return None

def create_lineup_from_players(
    players: List[Dict], 
    primary_stack: str, 
    secondary_stack: str
) -> 'Lineup':
    """
    Create a Lineup object from parsed players
    
    Args:
        players: List of player dictionaries
        primary_stack: Primary stack team
        secondary_stack: Secondary stack team
        
    Returns:
        Lineup object
    """
    from MLB_Optimizer import Lineup
    return Lineup(players, primary_stack, secondary_stack)

def _determine_slot_flexible(
    player, 
    existing_players: List[Dict]
) -> Optional[str]:
    """
    Flexible slot assignment that tries to find the best available slot
    
    Args:
        player: Player object
        existing_players: List of already assigned players
        
    Returns:
        Slot name or None if no valid slot available
    """
    # Create a fresh copy of existing players to avoid any reference issues
    existing_players_copy = existing_players.copy() if existing_players else []
    
    # Count existing players by slot
    slot_counts = {}
    for p in existing_players_copy:
        slot = p["Slot"]
        slot_counts[slot] = slot_counts.get(slot, 0) + 1
    
    slot_limits = {
        "P": 1, "C/1B": 1, "2B": 1, "3B": 1, "SS": 1, "OF": 3, "UTIL": 1
    }
    
    # Try to assign to the most specific position first
    priority_slots = []
    
    # Add specific position slots first
    for pos in player.positions:
        if pos == "P":
            priority_slots.append("P")
        elif pos in ["C", "1B"]:
            priority_slots.append("C/1B")
        elif pos == "2B":
            priority_slots.append("2B")
        elif pos == "3B":
            priority_slots.append("3B")
        elif pos == "SS":
            priority_slots.append("SS")
        elif pos == "OF":
            priority_slots.append("OF")
    
    # Add UTIL as fallback for non-pitchers
    if not player.is_pitcher:
        priority_slots.append("UTIL")
    
    # Try each priority slot
    for slot in priority_slots:
        current_count = slot_counts.get(slot, 0)
        max_count = slot_limits.get(slot, 1)
        
        if current_count < max_count:
            return slot
    
    # If no priority slots work, try any available slot
    for slot, max_count in slot_limits.items():
        current_count = slot_counts.get(slot, 0)
        if current_count < max_count:
            # Check if player can play this position
            if _can_play_position(player, slot):
                return slot
    
    # If we still can't find a slot, try the most flexible approach
    if not player.is_pitcher:
        # For non-pitchers, try UTIL as last resort
        if slot_counts.get("UTIL", 0) < 1:
            return "UTIL"
    
    # Debug: log what happened
    logger.warning(f"Could not assign slot for {player.name} (positions: {player.positions})")
    logger.warning(f"Priority slots tried: {priority_slots}")
    logger.warning(f"Slot counts: {slot_counts}")
    logger.warning(f"Player is pitcher: {player.is_pitcher}")
    logger.warning(f"Existing players count: {len(existing_players_copy)}")
    
    return None

def _determine_slot_for_position(
    player, 
    expected_slot: str, 
    existing_players: List[Dict]
) -> Optional[str]:
    """
    Determine slot assignment for a specific expected position
    
    Args:
        player: Player object
        expected_slot: Expected slot based on position order
        existing_players: List of already assigned players
        
    Returns:
        Slot name or None if no valid slot available
    """
    # Check if player can play the expected slot
    if _can_play_position(player, expected_slot):
        # Check if the slot is available
        slot_counts = {}
        for p in existing_players:
            slot = p["Slot"]
            slot_counts[slot] = slot_counts.get(slot, 0) + 1
        
        slot_limits = {
            "P": 1, "C/1B": 1, "2B": 1, "3B": 1, "SS": 1, "OF": 3, "UTIL": 1
        }
        
        current_count = slot_counts.get(expected_slot, 0)
        max_count = slot_limits.get(expected_slot, 1)
        
        if current_count < max_count:
            return expected_slot
    
    # If expected slot doesn't work, try alternative slots
    return _determine_slot(player, existing_players, ["P", "C/1B", "2B", "3B", "SS", "OF", "OF", "OF", "UTIL"])

def _determine_slot(
    player, 
    existing_players: List[Dict], 
    fd_position_order: List[str]
) -> Optional[str]:
    """
    Enhanced slot assignment with better position handling
    
    Args:
        player: Player object
        existing_players: List of already assigned players
        fd_position_order: FanDuel position order
        
    Returns:
        Slot name or None if no valid slot available
    """
    if player.is_pitcher:
        return "P"
    
    # Count existing players by slot
    slot_counts = {}
    for p in existing_players:
        slot = p["Slot"]
        slot_counts[slot] = slot_counts.get(slot, 0) + 1
    
    # Check available slots with enhanced position matching
    slot_limits = {
        "P": 1, "C/1B": 1, "2B": 1, "3B": 1, "SS": 1, "OF": 3, "UTIL": 1
    }
    
    for slot, max_count in slot_limits.items():
        current_count = slot_counts.get(slot, 0)
        if current_count < max_count:
            # Enhanced position matching
            if _can_play_position(player, slot):
                return slot
    
    # Fallback: try UTIL for any non-pitcher
    if not player.is_pitcher and slot_counts.get("UTIL", 0) < 1:
        return "UTIL"
    
    return None

def _can_play_position(player, slot: str) -> bool:
    """
    Enhanced position matching with more flexible rules
    
    Args:
        player: Player object
        slot: Position slot
        
    Returns:
        True if player can play the position
    """
    # Pitcher slot
    if slot == "P" and player.is_pitcher:
        return True
    
    # C/1B slot - accept C, 1B, or C/1B
    elif slot == "C/1B":
        return any(pos in ["C", "1B", "C/1B"] for pos in player.positions)
    
    # UTIL slot - accept any non-pitcher
    elif slot == "UTIL" and not player.is_pitcher:
        return True
    
    # Specific position slots
    elif slot in player.positions:
        return True
    
    # Additional flexibility for common position combinations
    elif slot == "2B" and "2B" in player.positions:
        return True
    elif slot == "3B" and "3B" in player.positions:
        return True
    elif slot == "SS" and "SS" in player.positions:
        return True
    elif slot == "OF" and "OF" in player.positions:
        return True
    
    return False

def _identify_stacks(lineup_players: List[Dict]) -> Tuple[str, str]:
    """
    Identify primary and secondary stacks in a lineup
    
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
    
    # Find teams with 4 players (primary stack)
    primary_stack = ""
    secondary_stack = ""
    
    for team, count in team_counts.items():
        if count == 4:
            if not primary_stack:
                primary_stack = team
            elif not secondary_stack:
                secondary_stack = team
        elif count == 3:
            if not secondary_stack:
                secondary_stack = team
    
    # If no 4-player team found, look for 3-player teams
    if not primary_stack:
        for team, count in team_counts.items():
            if count == 3:
                if not primary_stack:
                    primary_stack = team
                elif not secondary_stack:
                    secondary_stack = team
    
    return primary_stack, secondary_stack

def validate_lineup_structure(lineup_players: List[Dict]) -> bool:
    """
    Validate that lineup has correct structure
    
    Args:
        lineup_players: List of player dictionaries
        
    Returns:
        True if lineup structure is valid
    """
    if len(lineup_players) != 9:
        logger.warning(f"Invalid lineup size: {len(lineup_players)}")
        return False
    
    # Check position requirements
    slot_counts = {}
    for player in lineup_players:
        slot = player["Slot"]
        slot_counts[slot] = slot_counts.get(slot, 0) + 1
    
    required_slots = {
        "P": 1, "C/1B": 1, "2B": 1, "3B": 1, "SS": 1, "OF": 3, "UTIL": 1
    }
    
    for slot, required_count in required_slots.items():
        actual_count = slot_counts.get(slot, 0)
        if actual_count != required_count:
            logger.warning(f"Invalid {slot} count: {actual_count}, expected {required_count}")
            return False
    
    # Check salary cap
    total_salary = sum(player["Salary"] for player in lineup_players)
    if total_salary > 35000:
        logger.warning(f"Salary cap exceeded: ${total_salary}")
        return False
    
    return True

def extract_player_by_id(player_id: int, player_pool: List) -> Optional:
    """
    Extract player from player pool by ID
    
    Args:
        player_id: Player ID to find
        player_pool: List of available players
        
    Returns:
        Player object or None if not found
    """
    return next((p for p in player_pool if p.id == player_id), None)

def get_team_players(team: str, player_pool: List, exclude_pitchers: bool = True) -> List:
    """
    Get all players from a specific team
    
    Args:
        team: Team name
        player_pool: List of available players
        exclude_pitchers: Whether to exclude pitchers
        
    Returns:
        List of players from the team
    """
    players = [p for p in player_pool if p.team == team]
    if exclude_pitchers:
        players = [p for p in players if not p.is_pitcher]
    return players

def get_position_players(position: str, player_pool: List) -> List:
    """
    Get all players that can play a specific position
    
    Args:
        position: Position to filter by
        player_pool: List of available players
        
    Returns:
        List of players that can play the position
    """
    if position == "P":
        return [p for p in player_pool if p.is_pitcher]
    elif position == "C/1B":
        return [p for p in player_pool if any(pos in ["C", "1B", "C/1B"] for pos in p.positions)]
    elif position == "UTIL":
        return [p for p in player_pool if not p.is_pitcher]
    else:
        return [p for p in player_pool if position in p.positions]

def _determine_slot_from_position(player_index: int, fd_position_order: List[str]) -> Optional[str]:
    """
    Determine slot based on position in lineup
    
    Args:
        player_index: Index of player in lineup (0-8)
        fd_position_order: FanDuel position order
        
    Returns:
        Slot name or None if invalid
    """
    if player_index < len(fd_position_order):
        return fd_position_order[player_index]
    return None 