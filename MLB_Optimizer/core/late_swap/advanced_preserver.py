"""
Advanced Stack Preserver for MLB Late Swap Optimizer

This module implements sophisticated stack preservation algorithms for complex swap scenarios.
"""

import logging
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from copy import deepcopy

logger = logging.getLogger(__name__)

@dataclass
class StackSwapPlan:
    """A comprehensive plan for preserving stacks during swaps"""
    primary_stack_swaps: List[Dict]
    secondary_stack_swaps: List[Dict]
    one_off_swaps: List[Dict]
    total_projection_change: float
    total_salary_change: int
    preserves_all_stacks: bool
    priority_score: float

class AdvancedStackPreserver:
    """Advanced stack preservation with sophisticated algorithms"""
    
    def __init__(self, config=None):
        self.config = config or type('Config', (), {
            'MAX_SALARY': 35000,
            'PRESERVE_STACKS': True,
            'LOCKED_TEAMS': []
        })()
    
    def create_comprehensive_swap_plan(
        self,
        lineup,
        invalid_players: List[Dict],
        players: List
    ) -> Optional[StackSwapPlan]:
        """
        Create a comprehensive swap plan that preserves all stacks
        
        Args:
            lineup: Current lineup
            invalid_players: List of players that need to be swapped
            players: List of available players
            
        Returns:
            StackSwapPlan or None if no valid plan found
        """
        try:
            # Identify stack structure
            primary_stack, secondary_stack = self._identify_stack_structure(lineup)
            
            # Categorize invalid players
            primary_stack_players = []
            secondary_stack_players = []
            one_off_players = []
            
            for player in invalid_players:
                if player["Team"] == primary_stack:
                    primary_stack_players.append(player)
                elif player["Team"] == secondary_stack:
                    secondary_stack_players.append(player)
                else:
                    one_off_players.append(player)
            
            # Create swap plans for each category
            primary_swaps = self._plan_primary_stack_swaps(
                lineup, primary_stack_players, players, primary_stack
            )
            
            secondary_swaps = self._plan_secondary_stack_swaps(
                lineup, secondary_stack_players, players, secondary_stack
            )
            
            one_off_swaps = self._plan_one_off_swaps(
                lineup, one_off_players, players
            )
            
            # Calculate total changes
            total_projection_change = (
                sum(swap.get('projection_change', 0) for swap in primary_swaps) +
                sum(swap.get('projection_change', 0) for swap in secondary_swaps) +
                sum(swap.get('projection_change', 0) for swap in one_off_swaps)
            )
            
            total_salary_change = (
                sum(swap.get('salary_change', 0) for swap in primary_swaps) +
                sum(swap.get('salary_change', 0) for swap in secondary_swaps) +
                sum(swap.get('salary_change', 0) for swap in one_off_swaps)
            )
            
            # Check if plan preserves all stacks
            preserves_all_stacks = (
                len(primary_swaps) == len(primary_stack_players) and
                len(secondary_swaps) == len(secondary_stack_players)
            )
            
            # Calculate priority score
            priority_score = self._calculate_priority_score(
                primary_swaps, secondary_swaps, one_off_swaps
            )
            
            return StackSwapPlan(
                primary_stack_swaps=primary_swaps,
                secondary_stack_swaps=secondary_swaps,
                one_off_swaps=one_off_swaps,
                total_projection_change=total_projection_change,
                total_salary_change=total_salary_change,
                preserves_all_stacks=preserves_all_stacks,
                priority_score=priority_score
            )
            
        except Exception as e:
            logger.error(f"Error creating comprehensive swap plan: {str(e)}")
            return None
    
    def _plan_primary_stack_swaps(
        self,
        lineup,
        invalid_players: List[Dict],
        players: List,
        primary_stack: str
    ) -> List[Dict]:
        """Plan swaps for primary stack players"""
        swaps = []
        
        for invalid_player in invalid_players:
            # Find best replacement from same team
            candidates = self._find_team_replacement_candidates(
                invalid_player, players, primary_stack
            )
            
            if candidates:
                best_candidate = candidates[0]  # Already sorted by projection
                
                swap = {
                    'original_player': invalid_player,
                    'replacement_player': best_candidate,
                    'projection_change': best_candidate.projection - invalid_player["Projection"],
                    'salary_change': best_candidate.salary - invalid_player["Salary"],
                    'stack_type': 'primary',
                    'priority': 3
                }
                swaps.append(swap)
        
        return swaps
    
    def _plan_secondary_stack_swaps(
        self,
        lineup,
        invalid_players: List[Dict],
        players: List,
        secondary_stack: str
    ) -> List[Dict]:
        """Plan swaps for secondary stack players"""
        swaps = []
        
        for invalid_player in invalid_players:
            # Find best replacement from same team
            candidates = self._find_team_replacement_candidates(
                invalid_player, players, secondary_stack
            )
            
            if candidates:
                best_candidate = candidates[0]  # Already sorted by projection
                
                swap = {
                    'original_player': invalid_player,
                    'replacement_player': best_candidate,
                    'projection_change': best_candidate.projection - invalid_player["Projection"],
                    'salary_change': best_candidate.salary - invalid_player["Salary"],
                    'stack_type': 'secondary',
                    'priority': 2
                }
                swaps.append(swap)
        
        return swaps
    
    def _plan_one_off_swaps(
        self,
        lineup,
        invalid_players: List[Dict],
        players: List
    ) -> List[Dict]:
        """Plan swaps for one-off players"""
        swaps = []
        
        for invalid_player in invalid_players:
            # Find best replacement from any team
            candidates = self._find_position_replacement_candidates(
                invalid_player, players
            )
            
            if candidates:
                best_candidate = candidates[0]  # Already sorted by projection
                
                swap = {
                    'original_player': invalid_player,
                    'replacement_player': best_candidate,
                    'projection_change': best_candidate.projection - invalid_player["Projection"],
                    'salary_change': best_candidate.salary - invalid_player["Salary"],
                    'stack_type': 'none',
                    'priority': 1
                }
                swaps.append(swap)
        
        return swaps
    
    def _find_team_replacement_candidates(
        self,
        invalid_player: Dict,
        players: List,
        team: str
    ) -> List:
        """Find replacement candidates from the same team"""
        candidates = []
        position = invalid_player["Slot"]
        
        for player in players:
            if (player.team == team and
                not player.is_pitcher and
                player.projection > 0 and  # Only consider players with positive projections
                self._can_play_position(player, position) and
                not self._is_player_in_lineup(player, invalid_player)):
                
                # Check salary constraints
                if self._check_salary_constraints(player, invalid_player):
                    candidates.append(player)
        
        # Sort by projection (highest first)
        candidates.sort(key=lambda x: x.projection, reverse=True)
        return candidates
    
    def _find_position_replacement_candidates(
        self,
        invalid_player: Dict,
        players: List
    ) -> List:
        """Find replacement candidates for the same position"""
        candidates = []
        position = invalid_player["Slot"]
        
        for player in players:
            if (not player.is_pitcher and
                player.projection > 0 and  # Only consider players with positive projections
                self._can_play_position(player, position) and
                not self._is_player_in_lineup(player, invalid_player)):
                
                # Check salary constraints
                if self._check_salary_constraints(player, invalid_player):
                    candidates.append(player)
        
        # Sort by projection (highest first)
        candidates.sort(key=lambda x: x.projection, reverse=True)
        return candidates
    
    def _can_play_position(self, player, position: str) -> bool:
        """Check if player can play the specified position"""
        if position == "P":
            return player.is_pitcher
        elif position == "C/1B":
            return any(pos in ["C", "1B", "C/1B"] for pos in player.positions)
        elif position == "UTIL":
            return not player.is_pitcher
        else:
            return position in player.positions
    
    def _is_player_in_lineup(self, player, invalid_player: Dict) -> bool:
        """Check if player is already in the lineup"""
        return player.id == invalid_player["Id"]
    
    def _check_salary_constraints(self, candidate, invalid_player: Dict) -> bool:
        """Check if adding the candidate would violate salary constraints"""
        salary_change = candidate.salary - invalid_player["Salary"]
        return salary_change <= 0  # Can't increase salary in late swap
    
    def _calculate_priority_score(
        self,
        primary_swaps: List[Dict],
        secondary_swaps: List[Dict],
        one_off_swaps: List[Dict]
    ) -> float:
        """Calculate priority score for the swap plan"""
        score = 0.0
        
        # Primary stack swaps get highest priority
        for swap in primary_swaps:
            score += swap.get('projection_change', 0) * 3.0
        
        # Secondary stack swaps get medium priority
        for swap in secondary_swaps:
            score += swap.get('projection_change', 0) * 2.0
        
        # One-off swaps get lowest priority
        for swap in one_off_swaps:
            score += swap.get('projection_change', 0) * 1.0
        
        return score
    
    def _identify_stack_structure(self, lineup) -> Tuple[str, str]:
        """Identify primary and secondary stacks in a lineup"""
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
    
    def apply_swap_plan(self, lineup, swap_plan: StackSwapPlan) -> Optional:
        """Apply a comprehensive swap plan to a lineup"""
        try:
            # Create a copy of the lineup
            new_lineup = deepcopy(lineup)
            
            # Apply all swaps
            all_swaps = (
                swap_plan.primary_stack_swaps +
                swap_plan.secondary_stack_swaps +
                swap_plan.one_off_swaps
            )
            
            for swap in all_swaps:
                # Find and replace the player
                for i, player in enumerate(new_lineup.players):
                    if player["Id"] == swap['original_player']["Id"]:
                        # Update player data
                        new_lineup.players[i] = {
                            "Id": swap['replacement_player'].id,
                            "Name": swap['replacement_player'].name,
                            "Team": swap['replacement_player'].team,
                            "Slot": swap['original_player']["Slot"],
                            "Salary": swap['replacement_player'].salary,
                            "Projection": swap['replacement_player'].projection,
                            "Roster Order": swap['replacement_player'].roster_order,
                            "Positions": ",".join(swap['replacement_player'].positions)
                        }
                        break
            
            logger.info(f"Applied {len(all_swaps)} swaps with total projection change: {swap_plan.total_projection_change:.2f}")
            return new_lineup
            
        except Exception as e:
            logger.error(f"Error applying swap plan: {str(e)}")
            return None 