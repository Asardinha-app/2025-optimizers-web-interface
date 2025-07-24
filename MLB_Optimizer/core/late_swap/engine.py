"""
Late Swap Engine for MLB Late Swap Optimizer

This module integrates all Phase 3 components to provide a comprehensive late swap solution.
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from copy import deepcopy

from .advanced_preserver import AdvancedStackPreserver, StackSwapPlan
from .multi_optimizer import MultiSwapOptimizer, MultiSwapSolution
from .analyzer import analyze_lineup_for_swaps
from .validator import validate_lineup_constraints, validate_swap_constraints
from data.processors.lineup_parser import parse_lineup_from_csv_row

logger = logging.getLogger(__name__)

@dataclass
class LateSwapResult:
    """Result of a late swap operation"""
    original_lineup: object
    optimized_lineup: Optional[object]
    swaps_made: List[Dict]
    total_projection_change: float
    total_salary_change: int
    preserves_all_stacks: bool
    constraint_violations: List[str]
    optimization_method: str  # "multi_swap", "stack_preservation", or "simple"
    is_successful: bool
    error_message: Optional[str] = None

class LateSwapEngine:
    """Main late swap engine that integrates all optimization components"""
    
    def __init__(self, config=None):
        self.config = config or type('Config', (), {
            'MAX_SALARY': 35000,
            'PRESERVE_STACKS': True,
            'LOCKED_TEAMS': [],
            'MAX_SWAP_ATTEMPTS': 100,
            'PREFER_MULTI_SWAP': True,
            'PREFER_STACK_PRESERVATION': True
        })()
        
        # Initialize components
        self.stack_preserver = AdvancedStackPreserver(config)
        self.multi_swap_optimizer = MultiSwapOptimizer(config)
    
    def optimize_lineup(
        self,
        lineup,
        players: List
    ) -> LateSwapResult:
        """
        Optimize a lineup using late swap logic
        
        Args:
            lineup: Current lineup to optimize
            players: List of available players
            
        Returns:
            LateSwapResult with optimization results
        """
        try:
            # Validate input lineup
            if not hasattr(lineup, 'players') or not lineup.players:
                return LateSwapResult(
                    original_lineup=lineup,
                    optimized_lineup=None,
                    swaps_made=[],
                    total_projection_change=0.0,
                    total_salary_change=0,
                    preserves_all_stacks=False,
                    constraint_violations=["Invalid lineup structure"],
                    optimization_method="none",
                    is_successful=False,
                    error_message="Lineup has no players"
                )
            
            # Analyze lineup for players needing swaps
            swap_analyses = analyze_lineup_for_swaps(lineup, players, self.config)
            
            if not swap_analyses:
                logger.info("No players need swapping in this lineup")
                return LateSwapResult(
                    original_lineup=lineup,
                    optimized_lineup=lineup,
                    swaps_made=[],
                    total_projection_change=0.0,
                    total_salary_change=0,
                    preserves_all_stacks=True,
                    constraint_violations=[],
                    optimization_method="none",
                    is_successful=True
                )
            
            logger.info(f"Found {len(swap_analyses)} players needing swaps")
            
            # Extract invalid players
            invalid_players = []
            for analysis in swap_analyses:
                # Find the player in the lineup to get full data
                for player in lineup.players:
                    if player["Id"] == analysis.player_id:
                        invalid_players.append(player)
                        break
            
            if not invalid_players:
                logger.warning("Could not find invalid players in lineup")
                return LateSwapResult(
                    original_lineup=lineup,
                    optimized_lineup=None,
                    swaps_made=[],
                    total_projection_change=0.0,
                    total_salary_change=0,
                    preserves_all_stacks=False,
                    constraint_violations=["Could not identify invalid players"],
                    optimization_method="none",
                    is_successful=False,
                    error_message="Could not find invalid players in lineup"
                )
            
            # Try multi-swap optimization first (if enabled)
            if self.config.PREFER_MULTI_SWAP:
                result = self._try_multi_swap_optimization(lineup, invalid_players, players)
                if result and result.is_successful:
                    logger.info("Successfully used multi-swap optimization")
                    return result
                elif result:
                    logger.warning(f"Multi-swap optimization failed: {result.error_message}")
            
            # Try stack preservation optimization
            if self.config.PREFER_STACK_PRESERVATION:
                result = self._try_stack_preservation_optimization(lineup, invalid_players, players)
                if result and result.is_successful:
                    logger.info("Successfully used stack preservation optimization")
                    return result
                elif result:
                    logger.warning(f"Stack preservation optimization failed: {result.error_message}")
            
            # Try simple optimization as fallback
            result = self._try_simple_optimization(lineup, invalid_players, players)
            if result and result.is_successful:
                logger.info("Successfully used simple optimization")
                return result
            elif result:
                logger.warning(f"Simple optimization failed: {result.error_message}")
            
            # All optimization methods failed
            logger.error("All optimization methods failed")
            return LateSwapResult(
                original_lineup=lineup,
                optimized_lineup=None,
                swaps_made=[],
                total_projection_change=0.0,
                total_salary_change=0,
                preserves_all_stacks=False,
                constraint_violations=["All optimization methods failed"],
                optimization_method="none",
                is_successful=False,
                error_message="All optimization methods failed"
            )
            
        except Exception as e:
            logger.error(f"Error in optimize_lineup: {str(e)}")
            return LateSwapResult(
                original_lineup=lineup,
                optimized_lineup=None,
                swaps_made=[],
                total_projection_change=0.0,
                total_salary_change=0,
                preserves_all_stacks=False,
                constraint_violations=[f"Exception: {str(e)}"],
                optimization_method="none",
                is_successful=False,
                error_message=f"Exception in optimize_lineup: {str(e)}"
            )
    
    def _try_multi_swap_optimization(
        self,
        lineup,
        invalid_players: List[Dict],
        players: List
    ) -> Optional[LateSwapResult]:
        """Try multi-swap optimization"""
        try:
            solution = self.multi_swap_optimizer.optimize_multi_swaps(
                lineup, invalid_players, players
            )
            
            if solution and solution.swaps:
                # Apply the solution
                optimized_lineup = self.multi_swap_optimizer.apply_multi_swap_solution(
                    lineup, solution
                )
                
                if optimized_lineup:
                    # Validate the result
                    is_valid = validate_lineup_constraints(optimized_lineup, self.config)
                    
                    return LateSwapResult(
                        original_lineup=lineup,
                        optimized_lineup=optimized_lineup,
                        swaps_made=solution.swaps,
                        total_projection_change=solution.total_projection_change,
                        total_salary_change=solution.total_salary_change,
                        preserves_all_stacks=solution.preserves_all_stacks,
                        constraint_violations=solution.constraint_violations,
                        optimization_method="multi_swap",
                        is_successful=is_valid and len(solution.constraint_violations) == 0
                    )
            
            return None
            
        except Exception as e:
            logger.warning(f"Multi-swap optimization failed: {str(e)}")
            return None
    
    def _try_stack_preservation_optimization(
        self,
        lineup,
        invalid_players: List[Dict],
        players: List
    ) -> Optional[LateSwapResult]:
        """Try advanced stack preservation optimization"""
        try:
            swap_plan = self.stack_preserver.create_comprehensive_swap_plan(
                lineup, invalid_players, players
            )
            
            if swap_plan and (swap_plan.primary_stack_swaps or 
                             swap_plan.secondary_stack_swaps or 
                             swap_plan.one_off_swaps):
                
                # Apply the swap plan
                optimized_lineup = self.stack_preserver.apply_swap_plan(lineup, swap_plan)
                
                if optimized_lineup:
                    # Validate the result
                    is_valid = validate_lineup_constraints(optimized_lineup, self.config)
                    
                    # Convert swaps to standard format
                    swaps_made = []
                    for swap in (swap_plan.primary_stack_swaps + 
                               swap_plan.secondary_stack_swaps + 
                               swap_plan.one_off_swaps):
                        swaps_made.append({
                            'original_player': swap['original_player'],
                            'replacement_player': swap['replacement_player'],
                            'projection_change': swap['projection_change'],
                            'salary_change': swap['salary_change']
                        })
                    
                    return LateSwapResult(
                        original_lineup=lineup,
                        optimized_lineup=optimized_lineup,
                        swaps_made=swaps_made,
                        total_projection_change=swap_plan.total_projection_change,
                        total_salary_change=swap_plan.total_salary_change,
                        preserves_all_stacks=swap_plan.preserves_all_stacks,
                        constraint_violations=[],
                        optimization_method="stack_preservation",
                        is_successful=is_valid
                    )
            
            return None
            
        except Exception as e:
            logger.warning(f"Stack preservation optimization failed: {str(e)}")
            return None
    
    def _try_simple_optimization(
        self,
        lineup,
        invalid_players: List[Dict],
        players: List
    ) -> Optional[LateSwapResult]:
        """Try simple optimization with stack preservation"""
        try:
            optimized_lineup = deepcopy(lineup)
            swaps_made = []
            total_projection_change = 0.0
            total_salary_change = 0
            
            # First, handle the invalid players (Roster Order 0)
            for invalid_player in invalid_players:
                # Find best replacement
                candidates = self._find_simple_replacement(invalid_player, players, optimized_lineup)
                
                if candidates:
                    best_candidate = candidates[0]  # Already sorted by projection
                    
                    # Apply the swap
                    for i, player in enumerate(optimized_lineup.players):
                        if player["Id"] == invalid_player["Id"]:
                            # Calculate changes
                            projection_change = best_candidate.projection - player["Projection"]
                            salary_change = best_candidate.salary - player["Salary"]
                            
                            # Update player
                            optimized_lineup.players[i] = {
                                "Id": best_candidate.id,
                                "Name": best_candidate.name,
                                "Team": best_candidate.team,
                                "Slot": player["Slot"],
                                "Salary": best_candidate.salary,
                                "Projection": best_candidate.projection,
                                "Roster Order": best_candidate.roster_order,
                                "Positions": ",".join(best_candidate.positions)
                            }
                            
                            swaps_made.append({
                                'original_player': player,
                                'replacement_player': best_candidate,
                                'projection_change': projection_change,
                                'salary_change': salary_change
                            })
                            
                            total_projection_change += projection_change
                            total_salary_change += salary_change
                            break
            
            # After handling invalid players, check if we need additional swaps to maintain stack structure
            if swaps_made:
                # Validate the result
                is_valid = validate_lineup_constraints(optimized_lineup, self.config)
                
                if not is_valid:
                    # Try to fix stack structure with additional swaps
                    logger.info("Stack structure disrupted, attempting additional swaps to maintain 4-3 structure")
                    additional_swaps = self._fix_stack_structure(optimized_lineup, players)
                    
                    if additional_swaps:
                        swaps_made.extend(additional_swaps)
                        # Recalculate totals
                        total_projection_change = sum(swap['projection_change'] for swap in swaps_made)
                        total_salary_change = sum(swap['salary_change'] for swap in swaps_made)
                        
                        # Re-validate
                        is_valid = validate_lineup_constraints(optimized_lineup, self.config)
                
                return LateSwapResult(
                    original_lineup=lineup,
                    optimized_lineup=optimized_lineup,
                    swaps_made=swaps_made,
                    total_projection_change=total_projection_change,
                    total_salary_change=total_salary_change,
                    preserves_all_stacks=is_valid,
                    constraint_violations=[],
                    optimization_method="simple_with_stack_fix",
                    is_successful=is_valid
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"Simple optimization failed: {str(e)}")
            return None
    
    def _find_simple_replacement(self, invalid_player: Dict, players: List, lineup) -> List:
        """Enhanced simple replacement candidate finding with performance optimizations"""
        candidates = []
        position = invalid_player["Slot"]
        current_salary = invalid_player["Salary"]
        current_projection = invalid_player["Projection"]
        
        # Get current lineup player IDs to avoid duplicates - cache this
        current_player_ids = set(p["Id"] for p in lineup.players)
        
        # Pre-filter players by position to reduce loop iterations
        position_eligible_players = [
            p for p in players 
            if self._can_play_position(p, position) and p.id not in current_player_ids
        ]
        
        # Sort by projection for early termination
        position_eligible_players.sort(key=lambda p: p.projection, reverse=True)
        
        for player in position_eligible_players[:20]:  # Reduced from 30 to 20 for better performance
            # Skip if already in lineup (redundant check but safe)
            if player.id in current_player_ids:
                continue
            
            # Enhanced projection filtering - only consider significant improvements
            if player.projection <= current_projection + 0.5:  # Require at least 0.5 point improvement
                continue
            
            # Enhanced salary constraints - only allow reasonable increases
            salary_diff = player.salary - current_salary
            if salary_diff > 500:  # Limit salary increase to $500
                continue
            
            # Check team conflicts - avoid adding players from same team as invalid player
            if player.team == invalid_player["Team"]:
                continue
            
            # Check roster order conflicts - avoid players with roster order 0
            if player.roster_order == 0:
                continue
            
            # Additional filtering: avoid players from locked teams
            if player.team in self.config.LOCKED_TEAMS:
                continue
            
            candidates.append(player)
            
            # Early termination if we have enough good candidates
            if len(candidates) >= 10:  # Reduced from 15 to 10 for better performance
                break
        
        return candidates
    
    def _creates_pitcher_opponent_conflict(self, candidate, invalid_player: Dict, lineup) -> bool:
        """Check if adding the candidate would create a pitcher-opponent conflict"""
        try:
            # Get the pitcher from the lineup
            pitcher = None
            for player in lineup.players:
                if player["Slot"] == "P":
                    pitcher = player
                    break
            
            if not pitcher:
                return False
            
            # Check if candidate is on the same team as the pitcher's opponent
            if hasattr(candidate, 'team') and hasattr(pitcher, 'Opponent'):
                return candidate.team == pitcher.get("Opponent")
            
            return False
        except Exception:
            return False
    
    def _can_play_position(self, player, position: str) -> bool:
        """Enhanced position matching with more flexible rules"""
        
        # Pitcher slot
        if position == "P" and player.is_pitcher:
            return True
        
        # C/1B slot - accept C, 1B, or C/1B
        elif position == "C/1B":
            return any(pos in ["C", "1B", "C/1B"] for pos in player.positions)
        
        # UTIL slot - accept any non-pitcher
        elif position == "UTIL" and not player.is_pitcher:
            return True
        
        # Specific position slots
        elif position in player.positions:
            return True
        
        # Additional flexibility for common position combinations
        elif position == "2B" and "2B" in player.positions:
            return True
        elif position == "3B" and "3B" in player.positions:
            return True
        elif position == "SS" and "SS" in player.positions:
            return True
        elif position == "OF" and "OF" in player.positions:
            return True
        
        return False
    
    def _check_salary_constraints(self, candidate, invalid_player: Dict) -> bool:
        """Check if adding the candidate would violate salary constraints"""
        # For late swap, we need to be more careful about salary increases
        # Calculate the salary change
        salary_change = candidate.salary - invalid_player["Salary"]
        
        # If this would increase salary significantly, be more restrictive
        if salary_change > 500:  # Don't allow salary increases over $500
            return False
        
        return True
    
    def _fix_stack_structure(self, lineup, players: List) -> List[Dict]:
        """
        Fix stack structure by swapping additional players to maintain 4-3 stack
        
        Args:
            lineup: Current lineup
            players: Available players
            
        Returns:
            List of additional swaps made
        """
        additional_swaps = []
        
        # Analyze current stack structure
        team_counts = {}
        for player in lineup.players:
            if player["Slot"] != "P":
                team = player["Team"]
                team_counts[team] = team_counts.get(team, 0) + 1
        
        # Find teams with 4 players (primary stack)
        primary_stacks = [team for team, count in team_counts.items() if count == 4]
        
        # Find teams with 3 players (secondary stack)
        secondary_stacks = [team for team, count in team_counts.items() if count == 3]
        
        # If we have more than 1 primary stack, need to reduce one
        if len(primary_stacks) > 1:
            # Keep the first primary stack, reduce others
            for team in primary_stacks[1:]:
                swap_result = self._reduce_stack(team, lineup, players)
                if swap_result:
                    additional_swaps.append(swap_result)
        
        # If we have no primary stack, need to build one
        elif len(primary_stacks) == 0:
            # Find a team with 3 players and add one more
            if secondary_stacks:
                team_to_expand = secondary_stacks[0]
                swap_result = self._expand_stack(team_to_expand, lineup, players)
                if swap_result:
                    additional_swaps.append(swap_result)
        
        # If we have no secondary stack, need to build one
        if len(secondary_stacks) == 0:
            # Find a team with 2 players and add one more
            teams_with_2 = [team for team, count in team_counts.items() if count == 2]
            if teams_with_2:
                team_to_expand = teams_with_2[0]
                swap_result = self._expand_stack(team_to_expand, lineup, players)
                if swap_result:
                    additional_swaps.append(swap_result)
        
        return additional_swaps
    
    def _reduce_stack(self, team: str, lineup, players: List) -> Optional[Dict]:
        """Reduce a stack by swapping out one player"""
        # Find a player from this team to swap out
        team_players = [p for p in lineup.players if p["Team"] == team and p["Slot"] != "P"]
        
        if not team_players:
            return None
        
        # Find the player with the lowest projection to swap out
        player_to_swap = min(team_players, key=lambda p: p["Projection"])
        
        # Find a replacement from a different team
        candidates = []
        current_player_ids = [p["Id"] for p in lineup.players]
        
        for player in players:
            if (not player.is_pitcher and
                player.projection > 0 and
                player.team != team and
                self._can_play_position(player, player_to_swap["Slot"]) and
                player.id != player_to_swap["Id"] and
                player.id not in current_player_ids):  # Ensure player is not already in lineup
                
                # Check salary constraints
                if self._check_salary_constraints(player, player_to_swap):
                    candidates.append(player)
        
        if candidates:
            best_candidate = max(candidates, key=lambda p: p.projection)
            
            # Apply the swap
            for i, player in enumerate(lineup.players):
                if player["Id"] == player_to_swap["Id"]:
                    projection_change = best_candidate.projection - player["Projection"]
                    salary_change = best_candidate.salary - player["Salary"]
                    
                    lineup.players[i] = {
                        "Id": best_candidate.id,
                        "Name": best_candidate.name,
                        "Team": best_candidate.team,
                        "Slot": player["Slot"],
                        "Salary": best_candidate.salary,
                        "Projection": best_candidate.projection,
                        "Roster Order": best_candidate.roster_order,
                        "Positions": ",".join(best_candidate.positions)
                    }
                    
                    return {
                        'original_player': player,
                        'replacement_player': best_candidate,
                        'projection_change': projection_change,
                        'salary_change': salary_change
                    }
        
        return None
    
    def _expand_stack(self, team: str, lineup, players: List) -> Optional[Dict]:
        """Expand a stack by swapping in one player from the same team"""
        # Find a player from a different team to swap out
        other_teams_players = [p for p in lineup.players if p["Team"] != team and p["Slot"] != "P"]
        
        if not other_teams_players:
            return None
        
        # Find the player with the lowest projection to swap out
        player_to_swap = min(other_teams_players, key=lambda p: p["Projection"])
        
        # Find a replacement from the target team
        candidates = []
        current_player_ids = [p["Id"] for p in lineup.players]
        
        for player in players:
            if (not player.is_pitcher and
                player.projection > 0 and
                player.team == team and
                self._can_play_position(player, player_to_swap["Slot"]) and
                player.id != player_to_swap["Id"] and
                player.id not in current_player_ids):  # Ensure player is not already in lineup
                
                # Check salary constraints
                if self._check_salary_constraints(player, player_to_swap):
                    candidates.append(player)
        
        if candidates:
            best_candidate = max(candidates, key=lambda p: p.projection)
            
            # Apply the swap
            for i, player in enumerate(lineup.players):
                if player["Id"] == player_to_swap["Id"]:
                    projection_change = best_candidate.projection - player["Projection"]
                    salary_change = best_candidate.salary - player["Salary"]
                    
                    lineup.players[i] = {
                        "Id": best_candidate.id,
                        "Name": best_candidate.name,
                        "Team": best_candidate.team,
                        "Slot": player["Slot"],
                        "Salary": best_candidate.salary,
                        "Projection": best_candidate.projection,
                        "Roster Order": best_candidate.roster_order,
                        "Positions": ",".join(best_candidate.positions)
                    }
                    
                    return {
                        'original_player': player,
                        'replacement_player': best_candidate,
                        'projection_change': projection_change,
                        'salary_change': salary_change
                    }
        
        return None
    
    def validate_swap_result(self, result: LateSwapResult) -> bool:
        """Validate a late swap result"""
        if not result.is_successful:
            return False
        
        if not result.optimized_lineup:
            return False
        
        # Check all constraints
        return validate_lineup_constraints(result.optimized_lineup, self.config)
    
    def get_optimization_summary(self, result: LateSwapResult) -> Dict:
        """Get a summary of the optimization result"""
        return {
            "successful": result.is_successful,
            "optimization_method": result.optimization_method,
            "swaps_made": len(result.swaps_made),
            "projection_change": result.total_projection_change,
            "salary_change": result.total_salary_change,
            "preserves_stacks": result.preserves_all_stacks,
            "constraint_violations": len(result.constraint_violations),
            "error_message": result.error_message
        } 