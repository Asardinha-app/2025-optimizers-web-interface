"""
Multi-Swap Optimizer for MLB Late Swap Optimizer

This module implements sophisticated multi-swap optimization algorithms that can handle
complex scenarios where multiple players need to be swapped simultaneously while
preserving stack integrity and meeting all constraints.
"""

import logging
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from copy import deepcopy
from ortools.sat.python import cp_model

logger = logging.getLogger(__name__)

@dataclass
class MultiSwapSolution:
    """A solution for multi-swap optimization"""
    swaps: List[Dict]
    total_projection_change: float
    total_salary_change: int
    preserves_all_stacks: bool
    constraint_violations: List[str]
    is_optimal: bool

class MultiSwapOptimizer:
    """Advanced multi-swap optimization using OR-Tools"""
    
    def __init__(self, config=None):
        self.config = config or type('Config', (), {
            'MAX_SALARY': 35000,
            'PRESERVE_STACKS': True,
            'LOCKED_TEAMS': [],
            'MAX_SWAP_ATTEMPTS': 100
        })()
    
    def optimize_multi_swaps(
        self,
        lineup,
        invalid_players: List[Dict],
        players: List
    ) -> Optional[MultiSwapSolution]:
        """
        Optimize multiple swaps simultaneously using constraint programming
        
        Args:
            lineup: Original lineup
            invalid_players: List of players that need to be swapped
            players: Available player pool
            
        Returns:
            MultiSwapSolution or None if optimization fails
        """
        if not invalid_players:
            return None
        
        try:
            # Create constraint programming model
            model = cp_model.CpModel()
            
            # Create variables for each potential swap
            swap_vars = {}
            swap_data = {}
            
            for i, invalid_player in enumerate(invalid_players):
                # Find all valid replacement candidates
                candidates = self._find_all_candidates(invalid_player, players)
                
                if not candidates:
                    logger.warning(f"No valid candidates found for {invalid_player['Name']}")
                    continue
                
                for j, candidate in enumerate(candidates):
                    var_name = f"swap_{i}_{j}"
                    swap_vars[var_name] = model.NewBoolVar(var_name)
                    swap_data[var_name] = {
                        'invalid_player': invalid_player,
                        'candidate': candidate,
                        'projection_change': candidate.projection - invalid_player["Projection"],
                        'salary_change': candidate.salary - invalid_player["Salary"]
                    }
            
            if not swap_vars:
                logger.warning("No valid swap variables created")
                return None
            
            # Constraint 1: Each invalid player must be swapped exactly once
            for i, invalid_player in enumerate(invalid_players):
                player_swaps = [var for var_name, var in swap_vars.items() 
                              if var_name.startswith(f"swap_{i}_")]
                if player_swaps:
                    model.Add(sum(player_swaps) == 1)
            
            # Constraint 2: Salary cap must be maintained
            total_salary_change = sum(
                swap_data[var_name]['salary_change'] * var
                for var_name, var in swap_vars.items()
            )
            current_salary = sum(player["Salary"] for player in lineup.players)
            model.Add(current_salary + total_salary_change <= self.config.MAX_SALARY)
            
            # Constraint 3: Stack preservation constraints
            self._add_stack_preservation_constraints(model, swap_vars, swap_data, lineup)
            
            # Constraint 4: Position constraints
            self._add_position_constraints(model, swap_vars, swap_data, lineup)
            
            # Constraint 5: No duplicate players
            self._add_no_duplicate_constraints(model, swap_vars, swap_data)
            
            # Objective: Maximize projection improvement
            objective = sum(
                swap_data[var_name]['projection_change'] * var
                for var_name, var in swap_vars.items()
            )
            model.Maximize(objective)
            
            # Solve the model
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = 30.0
            status = solver.Solve(model)
            
            if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                logger.warning(f"Multi-swap optimization failed with status: {status}")
                logger.warning(f"Status meaning: {solver.StatusName(status)}")
                
                # Provide detailed debugging information
                logger.warning(f"Current salary: ${current_salary}")
                logger.warning(f"Salary cap: ${self.config.MAX_SALARY}")
                logger.warning(f"Invalid players: {len(invalid_players)}")
                for i, player in enumerate(invalid_players):
                    candidates = self._find_all_candidates(player, players)
                    logger.warning(f"  Player {i+1}: {player['Name']} - {len(candidates)} candidates")
                
                return None
            
            # Extract solution
            swaps = []
            for var_name, var in swap_vars.items():
                if solver.Value(var) == 1:
                    data = swap_data[var_name]
                    swaps.append({
                        'original_player': data['invalid_player'],
                        'replacement_player': data['candidate'],
                        'projection_change': data['projection_change'],
                        'salary_change': data['salary_change']
                    })
            
            if not swaps:
                logger.warning("No swaps found in solution")
                return None
            
            # Calculate totals
            total_projection_change = sum(swap['projection_change'] for swap in swaps)
            total_salary_change = sum(swap['salary_change'] for swap in swaps)
            
            # Check constraint violations
            violations = self._check_constraint_violations(swaps, lineup)
            
            # Check stack preservation
            preserves_all_stacks = self._check_stack_preservation(swaps, lineup)
            
            return MultiSwapSolution(
                swaps=swaps,
                total_projection_change=total_projection_change,
                total_salary_change=total_salary_change,
                preserves_all_stacks=preserves_all_stacks,
                constraint_violations=violations,
                is_optimal=(status == cp_model.OPTIMAL)
            )
            
        except Exception as e:
            logger.error(f"Error in multi-swap optimization: {str(e)}")
            return None
    
    def _find_all_candidates(self, invalid_player: Dict, players: List) -> List:
        """Enhanced candidate finding with better filtering and performance optimizations"""
        candidates = []
        current_salary = invalid_player["Salary"]
        current_projection = invalid_player["Projection"]
        position = invalid_player["Slot"]
        
        # Get current lineup player IDs to avoid duplicates - cache this
        current_player_ids = set(p["Id"] for p in invalid_player.get("lineup_players", []))
        
        # Pre-filter players by position to reduce loop iterations
        position_eligible_players = [
            p for p in players 
            if self._can_play_position(p, position) and p.id not in current_player_ids
        ]
        
        # Sort by projection for early termination
        position_eligible_players.sort(key=lambda p: p.projection, reverse=True)
        
        for player in position_eligible_players[:25]:  # Reduced from 50 to 25 for better performance
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
            if len(candidates) >= 15:  # Reduced from 20 to 15 for better performance
                break
        
        return candidates
    
    def _creates_pitcher_opponent_conflict(self, candidate, invalid_player: Dict) -> bool:
        """Check if adding the candidate would create a pitcher-opponent conflict"""
        try:
            # Get the pitcher from the lineup
            pitcher = None
            for player in invalid_player.get("lineup_players", []):
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
    
    def _add_stack_preservation_constraints(
        self,
        model: cp_model.CpModel,
        swap_vars: Dict,
        swap_data: Dict,
        lineup
    ):
        """Add constraints to preserve stack integrity"""
        # Identify stack structure
        primary_stack, secondary_stack = self._identify_stack_structure(lineup)
        
        if primary_stack:
            # Count current primary stack players
            current_primary_count = sum(
                1 for player in lineup.players
                if player["Team"] == primary_stack and player["Slot"] != "P"
            )
            
            # Count primary stack players being swapped out
            primary_swaps_out = sum(
                var for var_name, var in swap_vars.items()
                if (swap_data[var_name]['invalid_player']["Team"] == primary_stack and
                    swap_data[var_name]['candidate'].team != primary_stack)
            )
            
            # Count primary stack players being swapped in
            primary_swaps_in = sum(
                var for var_name, var in swap_vars.items()
                if (swap_data[var_name]['invalid_player']["Team"] != primary_stack and
                    swap_data[var_name]['candidate'].team == primary_stack)
            )
            
            # Primary stack should maintain 4 players
            model.Add(current_primary_count - primary_swaps_out + primary_swaps_in == 4)
        
        if secondary_stack:
            # Count current secondary stack players
            current_secondary_count = sum(
                1 for player in lineup.players
                if player["Team"] == secondary_stack and player["Slot"] != "P"
            )
            
            # Count secondary stack players being swapped out
            secondary_swaps_out = sum(
                var for var_name, var in swap_vars.items()
                if (swap_data[var_name]['invalid_player']["Team"] == secondary_stack and
                    swap_data[var_name]['candidate'].team != secondary_stack)
            )
            
            # Count secondary stack players being swapped in
            secondary_swaps_in = sum(
                var for var_name, var in swap_vars.items()
                if (swap_data[var_name]['invalid_player']["Team"] != secondary_stack and
                    swap_data[var_name]['candidate'].team == secondary_stack)
            )
            
            # Secondary stack should maintain 3-4 players
            model.Add(current_secondary_count - secondary_swaps_out + secondary_swaps_in >= 3)
            model.Add(current_secondary_count - secondary_swaps_out + secondary_swaps_in <= 4)
    
    def _add_position_constraints(
        self,
        model: cp_model.CpModel,
        swap_vars: Dict,
        swap_data: Dict,
        lineup
    ):
        """Add constraints to maintain position requirements"""
        # Count current positions
        position_counts = {}
        for player in lineup.players:
            slot = player["Slot"]
            position_counts[slot] = position_counts.get(slot, 0) + 1
        
        # For each position, ensure the count remains correct
        for position, required_count in {"P": 1, "C/1B": 1, "2B": 1, "3B": 1, "SS": 1, "OF": 3, "UTIL": 1}.items():
            # Count players being swapped out of this position
            swaps_out = sum(
                var for var_name, var in swap_vars.items()
                if swap_data[var_name]['invalid_player']["Slot"] == position
            )
            
            # Count players being swapped into this position
            swaps_in = sum(
                var for var_name, var in swap_vars.items()
                if self._can_play_position(swap_data[var_name]['candidate'], position)
            )
            
            # Position count should remain the same
            current_count = position_counts.get(position, 0)
            model.Add(current_count - swaps_out + swaps_in == required_count)
    
    def _add_no_duplicate_constraints(
        self,
        model: cp_model.CpModel,
        swap_vars: Dict,
        swap_data: Dict
    ):
        """Add constraints to prevent duplicate players"""
        # Group swaps by candidate player
        candidate_groups = {}
        for var_name, var in swap_vars.items():
            candidate_id = swap_data[var_name]['candidate'].id
            if candidate_id not in candidate_groups:
                candidate_groups[candidate_id] = []
            candidate_groups[candidate_id].append(var)
        
        # Each candidate can only be used once
        for candidate_id, vars_list in candidate_groups.items():
            if len(vars_list) > 1:
                model.Add(sum(vars_list) <= 1)
    
    def _check_stack_preservation(self, swaps: List[Dict], lineup) -> bool:
        """Check if swaps preserve all stacks"""
        # Create a copy of the lineup and apply swaps
        test_lineup = deepcopy(lineup)
        
        for swap in swaps:
            # Find and replace the player
            for i, player in enumerate(test_lineup.players):
                if player["Id"] == swap['original_player']["Id"]:
                    test_lineup.players[i]["Team"] = swap['replacement_player'].team
                    break
        
        # Check stack structure
        primary_stack, secondary_stack = self._identify_stack_structure(test_lineup)
        
        # Count players in each stack
        team_counts = {}
        for player in test_lineup.players:
            if player["Slot"] != "P":
                team = player["Team"]
                team_counts[team] = team_counts.get(team, 0) + 1
        
        # Check if we have proper stacks
        has_primary = any(count == 4 for count in team_counts.values())
        has_secondary = any(count in [3, 4] for count in team_counts.values())
        
        return has_primary and has_secondary
    
    def _check_constraint_violations(self, swaps: List[Dict], lineup) -> List[str]:
        """Check for constraint violations in the swaps"""
        violations = []
        
        # Check salary cap
        total_salary = sum(player["Salary"] for player in lineup.players)
        salary_change = sum(swap['salary_change'] for swap in swaps)
        if total_salary + salary_change > self.config.MAX_SALARY:
            violations.append(f"Salary cap exceeded: ${total_salary + salary_change}")
        
        # Check for duplicate players
        replacement_ids = [swap['replacement_player'].id for swap in swaps]
        if len(replacement_ids) != len(set(replacement_ids)):
            violations.append("Duplicate players in swaps")
        
        return violations
    
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
    
    def _is_player_in_lineup(self, player, invalid_player: Dict) -> bool:
        """Check if player is already in the lineup"""
        return player.id == invalid_player["Id"]
    
    def _check_salary_constraints(self, candidate, invalid_player: Dict) -> bool:
        """Check if adding the candidate would violate salary constraints"""
        salary_change = candidate.salary - invalid_player["Salary"]
        return salary_change <= 0  # Can't increase salary in late swap
    
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
    
    def apply_multi_swap_solution(self, lineup, solution: MultiSwapSolution) -> Optional:
        """Apply a multi-swap solution to a lineup"""
        try:
            # Create a copy of the lineup
            new_lineup = deepcopy(lineup)
            
            # Apply all swaps
            for swap in solution.swaps:
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
            
            logger.info(f"Applied {len(solution.swaps)} swaps with total projection change: {solution.total_projection_change:.2f}")
            return new_lineup
            
        except Exception as e:
            logger.error(f"Error applying multi-swap solution: {str(e)}")
            return None 