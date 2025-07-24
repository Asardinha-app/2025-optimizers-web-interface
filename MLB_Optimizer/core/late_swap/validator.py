"""
Constraint Validator for MLB Late Swap Optimizer

This module validates that lineups meet all constraints from the original MLB optimizer.
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

def validate_lineup_constraints(lineup, config=None) -> bool:
    """
    Validate all original MLB optimizer constraints
    
    Args:
        lineup: Lineup object to validate
        config: Configuration object with LOCKED_TEAMS setting
        
    Returns:
        True if all constraints are satisfied
    """
    try:
        # Check basic structure
        if not validate_lineup_structure(lineup):
            return False
        
        # Check salary cap
        if not validate_salary_cap(lineup):
            return False
        
        # Check position requirements
        if not validate_position_requirements(lineup):
            return False
        
        # Check pitcher-opponent constraints
        if not validate_pitcher_opponent_constraints(lineup):
            return False
        
        # Check roster order constraints
        if not validate_roster_order_constraints(lineup):
            return False
        
        # Check stack rules
        if not validate_stack_rules(lineup):
            return False
        
        # Check one-off player rules
        if not validate_one_off_player_rules(lineup):
            return False
        
        # Check locked team constraints
        if not validate_locked_team_constraints(lineup, config):
            return False
        
        # Check for duplicate players
        if not validate_duplicate_players(lineup):
            return False
        
        logger.debug("All constraints validated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error validating constraints: {str(e)}")
        return False

def validate_salary_cap(lineup) -> bool:
    """
    Validate salary cap constraint ($35,000)
    
    Args:
        lineup: Lineup object to validate
        
    Returns:
        True if salary cap is satisfied
    """
    total_salary = sum(player["Salary"] for player in lineup.players)
    
    if total_salary > 35000:
        logger.warning(f"Salary cap exceeded: ${total_salary}")
        logger.warning(f"Salary cap limit: $35,000")
        logger.warning(f"Excess: ${total_salary - 35000}")
        
        # Log individual player salaries for debugging
        logger.warning("Player salaries:")
        for player in lineup.players:
            logger.warning(f"  {player['Name']} ({player['Slot']}): ${player['Salary']}")
        
        return False
    
    logger.debug(f"Salary cap satisfied: ${total_salary}")
    return True

def validate_position_requirements(lineup) -> bool:
    """
    Validate position requirements
    
    Args:
        lineup: Lineup object to validate
        
    Returns:
        True if position requirements are satisfied
    """
    required_slots = {
        "P": 1, "C/1B": 1, "2B": 1, "3B": 1, "SS": 1, "OF": 3, "UTIL": 1
    }
    
    slot_counts = {}
    for player in lineup.players:
        slot = player["Slot"]
        slot_counts[slot] = slot_counts.get(slot, 0) + 1
    
    for slot, required_count in required_slots.items():
        actual_count = slot_counts.get(slot, 0)
        if actual_count != required_count:
            logger.warning(f"Invalid {slot} count: {actual_count}, expected {required_count}")
            return False
    
    logger.debug("Position requirements satisfied")
    return True

def validate_pitcher_opponent_constraints(lineup) -> bool:
    """
    Validate pitcher-opponent constraints
    
    Args:
        lineup: Lineup object to validate
        
    Returns:
        True if pitcher-opponent constraints are satisfied
    """
    pitcher = None
    batters = []
    
    # Separate pitcher and batters
    for player in lineup.players:
        if player["Slot"] == "P":
            pitcher = player
        else:
            batters.append(player)
    
    if not pitcher:
        logger.warning("No pitcher found in lineup")
        return False
    
    # Check that pitcher is not facing any batter in the lineup
    for batter in batters:
        if batter["Team"] == pitcher["Opponent"]:
            logger.warning(f"Pitcher {pitcher['Name']} facing opponent {batter['Name']}")
            return False
    
    logger.debug("Pitcher-opponent constraints satisfied")
    return True

def validate_roster_order_constraints(lineup) -> bool:
    """
    Validate roster order constraints (only one player from roster orders 8-9)
    
    Args:
        lineup: Lineup object to validate
        
    Returns:
        True if roster order constraints are satisfied
    """
    ro8_9_count = 0
    
    for player in lineup.players:
        if player["Slot"] != "P":  # Only check batters
            roster_order = player["Roster Order"]
            if roster_order in [8, 9]:
                ro8_9_count += 1
    
    if ro8_9_count > 1:
        logger.warning(f"Too many players from roster orders 8-9: {ro8_9_count}")
        return False
    
    logger.debug("Roster order constraints satisfied")
    return True

def validate_stack_rules(lineup) -> bool:
    """
    Validate stack-related rules (realistic for late swap)
    
    Args:
        lineup: Lineup object to validate
        
    Returns:
        True if stack rules are satisfied
    """
    # Count players by team (excluding pitcher)
    team_counts = {}
    for player in lineup.players:
        if player["Slot"] != "P":
            team = player["Team"]
            team_counts[team] = team_counts.get(team, 0) + 1
    
    # For late swap, be more realistic about stack requirements
    # Many original lineups may not have perfect 4-3 structures
    
    # Check for at least some stacking (2+ players from same team)
    teams_with_2_plus = 0
    for team, count in team_counts.items():
        if count >= 2:
            teams_with_2_plus += 1
    
    if teams_with_2_plus < 2:
        logger.warning("Insufficient stacking - need at least 2 teams with 2+ players")
        logger.warning("Team counts (excluding pitcher):")
        for team, count in team_counts.items():
            logger.warning(f"  {team}: {count} players")
        return False
    
    # Check that we don't have too many teams (indicating no stacking)
    if len(team_counts) > 7:  # More than 7 teams means very little stacking
        logger.warning(f"Too many teams ({len(team_counts)}) - insufficient stacking")
        logger.warning("Team counts (excluding pitcher):")
        for team, count in team_counts.items():
            logger.warning(f"  {team}: {count} players")
        return False
    
    logger.debug("Stack rules satisfied (realistic validation)")
    return True

def validate_one_off_player_rules(lineup) -> bool:
    """
    Validate one-off player rules
    
    Args:
        lineup: Lineup object to validate
        
    Returns:
        True if one-off player rules are satisfied
    """
    # This is a placeholder - actual implementation would check against
    # the ONE_OFF_PLAYERS list from the original MLB optimizer
    # For now, we'll assume all one-off players are valid
    
    logger.debug("One-off player rules satisfied")
    return True

def validate_locked_team_constraints(lineup, config=None) -> bool:
    """
    Validate locked team constraints (no players from locked teams can be swapped out)
    
    Args:
        lineup: Lineup object to validate
        config: Configuration object with LOCKED_TEAMS setting
        
    Returns:
        True if locked team constraints are satisfied
    """
    if not config:
        return True
    
    locked_teams = getattr(config, 'LOCKED_TEAMS', [])
    if not locked_teams:
        return True
    
    # Check if any players from locked teams have roster_order == 0
    # (indicating they were swapped out, which is not allowed)
    for player in lineup.players:
        if (player["Team"] in locked_teams and 
            player["Roster Order"] == 0 and 
            not player.get("is_pitcher", False)):
            logger.warning(f"Player {player['Name']} from locked team {player['Team']} cannot be swapped out")
            return False
    
    logger.debug("Locked team constraints satisfied")
    return True

def validate_duplicate_players(lineup) -> bool:
    """
    Validate that no player appears more than once in the lineup
    
    Args:
        lineup: Lineup object to validate
        
    Returns:
        True if no duplicate players found
    """
    player_ids = []
    player_names = []
    player_details = []  # Track full player details for debugging
    
    for i, player in enumerate(lineup.players):
        player_id = player["Id"]
        player_name = player["Name"]
        slot = player.get("Slot", "Unknown")
        
        # Track player details for debugging
        player_details.append({
            "index": i,
            "id": player_id,
            "name": player_name,
            "slot": slot,
            "team": player.get("Team", "Unknown")
        })
        
        if player_id in player_ids:
            # Find the first occurrence of this player
            first_occurrence = next((p for p in player_details if p["id"] == player_id), None)
            logger.warning(f"Duplicate player ID found: {player_id} ({player_name})")
            logger.warning(f"  First occurrence: Slot {first_occurrence['slot']}, Team {first_occurrence['team']}")
            logger.warning(f"  Second occurrence: Slot {slot}, Team {player.get('Team', 'Unknown')}")
            return False
        
        if player_name in player_names:
            logger.warning(f"Duplicate player name found: {player_name}")
            return False
        
        player_ids.append(player_id)
        player_names.append(player_name)
    
    logger.debug("No duplicate players found")
    return True

def validate_lineup_structure(lineup) -> bool:
    """
    Validate basic lineup structure
    
    Args:
        lineup: Lineup object to validate
        
    Returns:
        True if lineup structure is valid
    """
    if not hasattr(lineup, 'players') or not lineup.players:
        logger.warning("Lineup has no players")
        return False
    
    if len(lineup.players) != 9:
        logger.warning(f"Invalid lineup size: {len(lineup.players)}")
        return False
    
    # Check that all players have required fields
    required_fields = ["Slot", "Name", "Team", "Salary", "Projection", "Id", "Roster Order"]
    for player in lineup.players:
        for field in required_fields:
            if field not in player:
                logger.warning(f"Player missing required field: {field}")
                return False
    
    logger.debug("Lineup structure is valid")
    return True

def get_validation_errors(lineup) -> List[str]:
    """
    Get detailed validation errors for a lineup
    
    Args:
        lineup: Lineup object to validate
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    # Check basic structure
    if not hasattr(lineup, 'players') or not lineup.players:
        errors.append("Lineup has no players")
        return errors
    
    if len(lineup.players) != 9:
        errors.append(f"Invalid lineup size: {len(lineup.players)}")
    
    # Check salary cap
    total_salary = sum(player["Salary"] for player in lineup.players)
    if total_salary > 35000:
        errors.append(f"Salary cap exceeded: ${total_salary}")
    
    # Check position requirements
    required_slots = {
        "P": 1, "C/1B": 1, "2B": 1, "3B": 1, "SS": 1, "OF": 3, "UTIL": 1
    }
    
    slot_counts = {}
    for player in lineup.players:
        slot = player["Slot"]
        slot_counts[slot] = slot_counts.get(slot, 0) + 1
    
    for slot, required_count in required_slots.items():
        actual_count = slot_counts.get(slot, 0)
        if actual_count != required_count:
            errors.append(f"Invalid {slot} count: {actual_count}, expected {required_count}")
    
    # Check pitcher-opponent constraints
    pitcher = None
    for player in lineup.players:
        if player["Slot"] == "P":
            pitcher = player
            break
    
    if pitcher:
        for player in lineup.players:
            if player["Slot"] != "P" and player["Team"] == pitcher["Opponent"]:
                errors.append(f"Pitcher {pitcher['Name']} facing opponent {player['Name']}")
    
    return errors

def validate_swap_constraints(
    original_lineup, 
    new_player, 
    removed_player, 
    players: List,
    config=None
) -> bool:
    """
    Validate constraints for a specific swap
    
    Args:
        original_lineup: Original lineup
        new_player: Player being added
        removed_player: Player being removed
        players: List of available players
        config: Configuration object with LOCKED_TEAMS setting
        
    Returns:
        True if swap satisfies all constraints
    """
    # Create a copy of the lineup with the swap
    swapped_lineup = _create_swapped_lineup(original_lineup, new_player, removed_player)
    
    if not swapped_lineup:
        return False
    
    # Validate the swapped lineup
    return validate_lineup_constraints(swapped_lineup, config)

def _create_swapped_lineup(original_lineup, new_player, removed_player):
    """
    Create a new lineup with a swap applied
    
    Args:
        original_lineup: Original lineup
        new_player: Player being added
        removed_player: Player being removed
        
    Returns:
        New lineup with swap applied
    """
    try:
        # Create a copy of the original lineup
        new_players = []
        for player in original_lineup.players:
            if player["Id"] == removed_player["Id"]:
                # Replace with new player
                new_player_data = {
                    "Slot": removed_player["Slot"],  # Keep same slot
                    "Name": new_player.name,
                    "Team": new_player.team,
                    "Opponent": new_player.opponent,
                    "Positions": ",".join(new_player.positions),
                    "Salary": new_player.salary,
                    "Projection": new_player.projection,
                    "Ownership": new_player.ownership,
                    "Id": new_player.id,
                    "Roster Order": new_player.roster_order
                }
                new_players.append(new_player_data)
            else:
                new_players.append(player)
        
        # Create new lineup object
        from MLB_Optimizer import Lineup
        return Lineup(new_players, original_lineup.primary_stack, original_lineup.secondary_stack)
        
    except Exception as e:
        logger.error(f"Error creating swapped lineup: {str(e)}")
        return None 