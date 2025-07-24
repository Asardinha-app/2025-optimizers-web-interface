"""
Swap Analyzer for MLB Late Swap Optimizer

This module analyzes lineups to identify players that need to be swapped
and determines stack structures for preservation.
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SwapAnalysis:
    """Analysis of a player that needs to be swapped"""
    player_id: int
    player_name: str
    team: str
    position: str
    roster_order: int
    is_in_stack: bool
    stack_type: str  # "primary", "secondary", or "none"
    replacement_candidates: List
    best_replacement: Optional
    swap_priority: int  # Higher priority for stack players
    
    def __post_init__(self):
        """Set swap priority based on stack type"""
        if self.stack_type == "primary":
            self.swap_priority = 3
        elif self.stack_type == "secondary":
            self.swap_priority = 2
        else:
            self.swap_priority = 1

def analyze_lineup_for_swaps(lineup, players: List, config=None) -> List[SwapAnalysis]:
    """
    Analyze a lineup to identify players that need to be swapped
    
    Args:
        lineup: Lineup object to analyze
        players: List of available players
        config: Configuration object with LOCKED_TEAMS setting
        
    Returns:
        List of SwapAnalysis objects for players that need swapping
    """
    swap_analyses = []
    
    # Identify stack structure
    primary_stack, secondary_stack = identify_stack_structure(lineup)
    
    # Get locked teams from config
    locked_teams = getattr(config, 'LOCKED_TEAMS', []) if config else []
    
    # Analyze each player in the lineup
    for player_data in lineup.players:
        # Check if player is a pitcher (exclude from roster order check)
        is_pitcher = player_data["Slot"] == "P" or "P" in player_data.get("Positions", "")
        
        # Check for players that need to be swapped
        needs_swap = False
        
        # Check if batter has roster_order == 0 (out of batting order)
        if not is_pitcher and player_data["Roster Order"] == 0:
            needs_swap = True
        
        if needs_swap:
            # Check if player's team is locked (game has started)
            if player_data["Team"] in locked_teams:
                logger.info(f"Skipping player {player_data['Name']} from locked team {player_data['Team']}")
                continue
            
            # This player needs to be swapped
            swap_analysis = _create_swap_analysis(
                player_data, 
                players, 
                lineup, 
                primary_stack, 
                secondary_stack
            )
            if swap_analysis:
                swap_analyses.append(swap_analysis)
    
    # Sort by priority (stack players first)
    swap_analyses.sort(key=lambda x: x.swap_priority, reverse=True)
    
    logger.info(f"Found {len(swap_analyses)} players needing swaps")
    return swap_analyses

def should_skip_lineup(lineup, players: List) -> bool:
    """
    Check if lineup should be skipped (all batters have roster_order 1-9)
    
    Args:
        lineup: Lineup object to check
        players: List of available players
        
    Returns:
        True if lineup should be skipped
    """
    # Check if any players need to be swapped
    for player_data in lineup.players:
        # Check if player is a pitcher (exclude from roster order check)
        is_pitcher = player_data["Slot"] == "P" or "P" in player_data.get("Positions", "")
        
        # Check if batter has roster_order == 0
        if not is_pitcher and player_data["Roster Order"] == 0:
            return False  # Lineup needs processing
    
    # All players are valid
    return True

def identify_stack_structure(lineup) -> Tuple[str, str]:
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
    
    logger.debug(f"Identified stacks - Primary: {primary_stack}, Secondary: {secondary_stack}")
    return primary_stack, secondary_stack

def find_replacement_candidates(
    invalid_player: Dict, 
    players: List, 
    lineup,
    preserve_stack: bool = True
) -> List:
    """
    Find valid replacement candidates for a player
    
    Args:
        invalid_player: Player that needs to be replaced
        players: List of available players
        lineup: Current lineup
        preserve_stack: Whether to preserve stack integrity
        
    Returns:
        List of candidate players sorted by projection
    """
    candidates = []
    
    # Get player's position and team
    position = invalid_player["Slot"]
    team = invalid_player["Team"]
    
    # Find players that can play this position
    position_candidates = _get_position_candidates(position, players)
    
    for candidate in position_candidates:
        # Skip if candidate has zero or negative projection
        if candidate.projection <= 0:
            continue
        
        # Skip if candidate is already in the lineup
        if any(p["Id"] == candidate.id for p in lineup.players):
            continue
        
        # Check salary constraints
        if not _check_salary_constraints(candidate, lineup, invalid_player):
            continue
        
        # Check pitcher-opponent constraints
        if not _check_pitcher_opponent_constraints(candidate, lineup):
            continue
        
        # If preserving stack, prioritize same team players
        if preserve_stack and candidate.team == team:
            candidates.append(candidate)
        elif not preserve_stack:
            candidates.append(candidate)
    
    # Sort by projection (highest first)
    candidates.sort(key=lambda x: x.projection, reverse=True)
    
    logger.debug(f"Found {len(candidates)} replacement candidates for {invalid_player['Name']}")
    return candidates

def _create_swap_analysis(
    player_data: Dict, 
    players: List, 
    lineup, 
    primary_stack: str, 
    secondary_stack: str
) -> Optional[SwapAnalysis]:
    """
    Create a SwapAnalysis object for a player
    
    Args:
        player_data: Player data dictionary
        players: List of available players
        lineup: Current lineup
        primary_stack: Primary stack team
        secondary_stack: Secondary stack team
        
    Returns:
        SwapAnalysis object or None if invalid
    """
    try:
        # Determine stack type
        team = player_data["Team"]
        if team == primary_stack:
            stack_type = "primary"
            is_in_stack = True
        elif team == secondary_stack:
            stack_type = "secondary"
            is_in_stack = True
        else:
            stack_type = "none"
            is_in_stack = False
        
        # Find replacement candidates
        replacement_candidates = find_replacement_candidates(
            player_data, players, lineup, preserve_stack=True
        )
        
        # Select best replacement
        best_replacement = replacement_candidates[0] if replacement_candidates else None
        
        return SwapAnalysis(
            player_id=player_data["Id"],
            player_name=player_data["Name"],
            team=team,
            position=player_data["Slot"],
            roster_order=player_data["Roster Order"],
            is_in_stack=is_in_stack,
            stack_type=stack_type,
            replacement_candidates=replacement_candidates,
            best_replacement=best_replacement,
            swap_priority=0  # Will be set in __post_init__
        )
        
    except Exception as e:
        logger.error(f"Error creating swap analysis for {player_data['Name']}: {str(e)}")
        return None

def _get_position_candidates(position: str, players: List) -> List:
    """
    Get players that can play a specific position
    
    Args:
        position: Position to filter by
        players: List of available players
        
    Returns:
        List of players that can play the position
    """
    if position == "P":
        return [p for p in players if p.is_pitcher]
    elif position == "C/1B":
        return [p for p in players if any(pos in ["C", "1B", "C/1B"] for pos in p.positions)]
    elif position == "UTIL":
        return [p for p in players if not p.is_pitcher]
    else:
        return [p for p in players if position in p.positions]

def _check_salary_constraints(candidate, lineup, invalid_player: Dict) -> bool:
    """
    Check if adding the candidate would violate salary constraints
    
    Args:
        candidate: Candidate player
        lineup: Current lineup
        invalid_player: Player being replaced
        
    Returns:
        True if salary constraints are satisfied
    """
    current_salary = sum(p["Salary"] for p in lineup.players)
    salary_change = candidate.salary - invalid_player["Salary"]
    new_salary = current_salary + salary_change
    
    return new_salary <= 35000

def _check_pitcher_opponent_constraints(candidate, lineup) -> bool:
    """
    Check pitcher-opponent constraints
    
    Args:
        candidate: Candidate player
        lineup: Current lineup
        
    Returns:
        True if constraints are satisfied
    """
    # If candidate is a pitcher, check that no opponent is in lineup
    if candidate.is_pitcher:
        for player in lineup.players:
            if player["Team"] == candidate.opponent:
                return False
    
    # If candidate is a batter, check that pitcher is not their opponent
    else:
        for player in lineup.players:
            if (player["Slot"] == "P" and 
                player["Team"] == candidate.opponent):
                return False
    
    return True

def get_stack_players(lineup, stack_type: str) -> List[Dict]:
    """
    Get all players in a specific stack
    
    Args:
        lineup: Lineup object
        stack_type: "primary" or "secondary"
        
    Returns:
        List of players in the stack
    """
    primary_stack, secondary_stack = identify_stack_structure(lineup)
    
    target_team = primary_stack if stack_type == "primary" else secondary_stack
    
    if not target_team:
        return []
    
    return [p for p in lineup.players if p["Team"] == target_team and p["Slot"] != "P"]

def validate_stack_integrity(lineup, original_stack_counts: Dict[str, int]) -> bool:
    """
    Validate that stack integrity is maintained after swaps
    
    Args:
        lineup: Lineup to validate
        original_stack_counts: Original stack player counts
        
    Returns:
        True if stack integrity is maintained
    """
    primary_stack, secondary_stack = identify_stack_structure(lineup)
    
    # Check primary stack (should have 4 players)
    if primary_stack:
        primary_count = len([p for p in lineup.players 
                           if p["Team"] == primary_stack and p["Slot"] != "P"])
        if primary_count < 4:
            logger.warning(f"Primary stack {primary_stack} has {primary_count} players, expected 4")
            return False
    
    # Check secondary stack (should have 3-4 players)
    if secondary_stack:
        secondary_count = len([p for p in lineup.players 
                             if p["Team"] == secondary_stack and p["Slot"] != "P"])
        if secondary_count < 3:
            logger.warning(f"Secondary stack {secondary_stack} has {secondary_count} players, expected 3-4")
            return False
    
    return True 