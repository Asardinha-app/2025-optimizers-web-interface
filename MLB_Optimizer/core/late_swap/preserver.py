"""
Stack Preserver for MLB Late Swap Optimizer

This module handles preserving stack integrity during swap operations.
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SwapOption:
    """A potential swap option that preserves stack integrity"""
    original_player: Dict
    replacement_player: object  # Player object
    stack_type: str  # "primary", "secondary", or "none"
    projection_change: float
    salary_change: int
    preserves_stack: bool
    priority: int

def preserve_primary_stack(
    lineup, 
    invalid_player: Dict, 
    players: List
) -> List[SwapOption]:
    """
    Generate swap options that preserve primary stack
    
    Args:
        lineup: Current lineup
        invalid_player: Player that needs to be replaced
        players: List of available players
        
    Returns:
        List of SwapOption objects
    """
    swap_options = []
    
    # Get primary stack team
    primary_stack, _ = _identify_stack_structure(lineup)
    
    if not primary_stack:
        logger.warning("No primary stack found")
        return swap_options
    
    # Check if invalid player is in primary stack
    if invalid_player["Team"] != primary_stack:
        logger.debug(f"Invalid player {invalid_player['Name']} not in primary stack {primary_stack}")
        return swap_options
    
    # Get all players in primary stack
    primary_stack_players = [p for p in lineup.players 
                           if p["Team"] == primary_stack and p["Slot"] != "P"]
    
    if len(primary_stack_players) < 4:
        logger.warning(f"Primary stack {primary_stack} has {len(primary_stack_players)} players, expected 4")
        return swap_options
    
    # Find replacement candidates from same team
    replacement_candidates = _find_team_replacement_candidates(
        invalid_player, players, primary_stack
    )
    
    for candidate in replacement_candidates:
        # Check if this swap would maintain stack integrity
        if _would_maintain_primary_stack(lineup, invalid_player, candidate):
            swap_option = SwapOption(
                original_player=invalid_player,
                replacement_player=candidate,
                stack_type="primary",
                projection_change=candidate.projection - invalid_player["Projection"],
                salary_change=candidate.salary - invalid_player["Salary"],
                preserves_stack=True,
                priority=3  # High priority for primary stack
            )
            swap_options.append(swap_option)
    
    # Sort by projection change (highest first)
    swap_options.sort(key=lambda x: x.projection_change, reverse=True)
    
    logger.info(f"Found {len(swap_options)} primary stack preservation options")
    return swap_options

def preserve_secondary_stack(
    lineup, 
    invalid_player: Dict, 
    players: List
) -> List[SwapOption]:
    """
    Generate swap options that preserve secondary stack
    
    Args:
        lineup: Current lineup
        invalid_player: Player that needs to be replaced
        players: List of available players
        
    Returns:
        List of SwapOption objects
    """
    swap_options = []
    
    # Get secondary stack team
    _, secondary_stack = _identify_stack_structure(lineup)
    
    if not secondary_stack:
        logger.warning("No secondary stack found")
        return swap_options
    
    # Check if invalid player is in secondary stack
    if invalid_player["Team"] != secondary_stack:
        logger.debug(f"Invalid player {invalid_player['Name']} not in secondary stack {secondary_stack}")
        return swap_options
    
    # Get all players in secondary stack
    secondary_stack_players = [p for p in lineup.players 
                             if p["Team"] == secondary_stack and p["Slot"] != "P"]
    
    if len(secondary_stack_players) < 3:
        logger.warning(f"Secondary stack {secondary_stack} has {len(secondary_stack_players)} players, expected 3-4")
        return swap_options
    
    # Find replacement candidates from same team
    replacement_candidates = _find_team_replacement_candidates(
        invalid_player, players, secondary_stack
    )
    
    for candidate in replacement_candidates:
        # Check if this swap would maintain stack integrity
        if _would_maintain_secondary_stack(lineup, invalid_player, candidate):
            swap_option = SwapOption(
                original_player=invalid_player,
                replacement_player=candidate,
                stack_type="secondary",
                projection_change=candidate.projection - invalid_player["Projection"],
                salary_change=candidate.salary - invalid_player["Salary"],
                preserves_stack=True,
                priority=2  # Medium priority for secondary stack
            )
            swap_options.append(swap_option)
    
    # Sort by projection change (highest first)
    swap_options.sort(key=lambda x: x.projection_change, reverse=True)
    
    logger.info(f"Found {len(swap_options)} secondary stack preservation options")
    return swap_options

def optimize_stack_swaps(
    lineup,
    swap_analyses: List,
    players: List
) -> Optional:
    """
    Optimize multiple swaps while preserving stacks
    
    Args:
        lineup: Current lineup
        swap_analyses: List of SwapAnalysis objects
        players: List of available players
        
    Returns:
        Optimized lineup or None if optimization fails
    """
    try:
        # Sort swap analyses by priority
        swap_analyses.sort(key=lambda x: x.swap_priority, reverse=True)
        
        # Apply swaps one by one, starting with highest priority
        optimized_lineup = lineup
        swaps_made = []
        
        for swap_analysis in swap_analyses:
            if swap_analysis.best_replacement:
                # Create swap option
                swap_option = SwapOption(
                    original_player={
                        "Id": swap_analysis.player_id,
                        "Name": swap_analysis.player_name,
                        "Team": swap_analysis.team,
                        "Slot": swap_analysis.position,
                        "Salary": 0,  # Will be filled from lineup
                        "Projection": 0,  # Will be filled from lineup
                        "Roster Order": swap_analysis.roster_order
                    },
                    replacement_player=swap_analysis.best_replacement,
                    stack_type=swap_analysis.stack_type,
                    projection_change=swap_analysis.best_replacement.projection,
                    salary_change=swap_analysis.best_replacement.salary,
                    preserves_stack=swap_analysis.is_in_stack,
                    priority=swap_analysis.swap_priority
                )
                
                # Apply the swap
                new_lineup = _apply_swap(optimized_lineup, swap_option)
                if new_lineup:
                    optimized_lineup = new_lineup
                    swaps_made.append(swap_option)
                    logger.info(f"Applied swap: {swap_option.original_player['Name']} -> {swap_option.replacement_player.name}")
                else:
                    logger.warning(f"Failed to apply swap for {swap_option.original_player['Name']}")
        
        if swaps_made:
            logger.info(f"Successfully applied {len(swaps_made)} swaps")
            return optimized_lineup
        else:
            logger.warning("No swaps were successfully applied")
            return None
            
    except Exception as e:
        logger.error(f"Error optimizing stack swaps: {str(e)}")
        return None

def _identify_stack_structure(lineup) -> Tuple[str, str]:
    """
    Identify primary and secondary stacks in a lineup
    
    Args:
        lineup: Lineup object to analyze
        
    Returns:
        Tuple of (primary_stack, secondary_stack)
    """
    # Count players by team (excluding pitcher)
    team_counts = {}
    for player in lineup.players:
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

def _find_team_replacement_candidates(
    invalid_player: Dict, 
    players: List, 
    team: str
) -> List:
    """
    Find replacement candidates from the same team
    
    Args:
        invalid_player: Player that needs to be replaced
        players: List of available players
        team: Team to search for candidates
        
    Returns:
        List of candidate players from the same team
    """
    candidates = []
    position = invalid_player["Slot"]
    
    # Get players from the same team that can play the position
    for player in players:
        if player.team == team:
            # Check if player can play the position
            if _can_play_position(player, position):
                # Skip if player is already in the lineup
                if not _is_player_in_lineup(player, invalid_player):
                    candidates.append(player)
    
    # Sort by projection (highest first)
    candidates.sort(key=lambda x: x.projection, reverse=True)
    
    return candidates

def _can_play_position(player, position: str) -> bool:
    """
    Check if player can play the specified position
    
    Args:
        player: Player object
        position: Position to check
        
    Returns:
        True if player can play the position
    """
    if position == "P" and player.is_pitcher:
        return True
    elif position == "C/1B" and any(pos in ["C", "1B", "C/1B"] for pos in player.positions):
        return True
    elif position == "UTIL" and not player.is_pitcher:
        return True
    elif position in player.positions:
        return True
    return False

def _is_player_in_lineup(player, invalid_player: Dict) -> bool:
    """
    Check if a player is already in the lineup (excluding the invalid player)
    
    Args:
        player: Player to check
        invalid_player: Player being replaced
        
    Returns:
        True if player is in lineup
    """
    # This is a simplified check - in practice, you'd need to check against
    # the actual lineup players
    return False

def _would_maintain_primary_stack(lineup, invalid_player: Dict, candidate) -> bool:
    """
    Check if swapping would maintain primary stack integrity
    
    Args:
        lineup: Current lineup
        invalid_player: Player being replaced
        candidate: Replacement candidate
        
    Returns:
        True if primary stack would be maintained
    """
    # Count players in primary stack after swap
    primary_stack, _ = _identify_stack_structure(lineup)
    
    if not primary_stack:
        return False
    
    # Count current primary stack players
    primary_count = len([p for p in lineup.players 
                        if p["Team"] == primary_stack and p["Slot"] != "P"])
    
    # If invalid player is in primary stack, count would decrease by 1
    if invalid_player["Team"] == primary_stack:
        primary_count -= 1
    
    # If candidate is in primary stack, count would increase by 1
    if candidate.team == primary_stack:
        primary_count += 1
    
    # Primary stack should have 4 players
    return primary_count == 4

def _would_maintain_secondary_stack(lineup, invalid_player: Dict, candidate) -> bool:
    """
    Check if swapping would maintain secondary stack integrity
    
    Args:
        lineup: Current lineup
        invalid_player: Player being replaced
        candidate: Replacement candidate
        
    Returns:
        True if secondary stack would be maintained
    """
    # Count players in secondary stack after swap
    _, secondary_stack = _identify_stack_structure(lineup)
    
    if not secondary_stack:
        return False
    
    # Count current secondary stack players
    secondary_count = len([p for p in lineup.players 
                          if p["Team"] == secondary_stack and p["Slot"] != "P"])
    
    # If invalid player is in secondary stack, count would decrease by 1
    if invalid_player["Team"] == secondary_stack:
        secondary_count -= 1
    
    # If candidate is in secondary stack, count would increase by 1
    if candidate.team == secondary_stack:
        secondary_count += 1
    
    # Secondary stack should have 3-4 players
    return 3 <= secondary_count <= 4

def _apply_swap(lineup, swap_option: SwapOption):
    """
    Apply a swap to a lineup
    
    Args:
        lineup: Current lineup
        swap_option: Swap option to apply
        
    Returns:
        New lineup with swap applied
    """
    try:
        # Create a copy of the lineup
        new_players = []
        
        for player in lineup.players:
            if player["Id"] == swap_option.original_player["Id"]:
                # Replace with new player
                new_player_data = {
                    "Slot": swap_option.original_player["Slot"],
                    "Name": swap_option.replacement_player.name,
                    "Team": swap_option.replacement_player.team,
                    "Opponent": swap_option.replacement_player.opponent,
                    "Positions": ",".join(swap_option.replacement_player.positions),
                    "Salary": swap_option.replacement_player.salary,
                    "Projection": swap_option.replacement_player.projection,
                    "Ownership": swap_option.replacement_player.ownership,
                    "Id": swap_option.replacement_player.id,
                    "Roster Order": swap_option.replacement_player.roster_order
                }
                new_players.append(new_player_data)
            else:
                new_players.append(player)
        
        # Create new lineup object
        from MLB_Optimizer import Lineup
        return Lineup(new_players, lineup.primary_stack, lineup.secondary_stack)
        
    except Exception as e:
        logger.error(f"Error applying swap: {str(e)}")
        return None 