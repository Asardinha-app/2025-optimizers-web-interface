"""
Swap Optimizer for MLB Late Swap Optimizer

This module uses OR-Tools to optimize swaps while preserving constraints.
"""

import logging
from typing import List, Dict, Optional, Tuple
from ortools.sat.python import cp_model

logger = logging.getLogger(__name__)

def create_swap_optimization_model(
    original_lineup,
    swap_analyses: List,
    players: List
) -> Tuple[cp_model.CpModel, Dict]:
    """
    Create optimization model for swaps
    
    Args:
        original_lineup: Original lineup
        swap_analyses: List of SwapAnalysis objects
        players: List of available players
        
    Returns:
        Tuple of (model, variables)
    """
    model = cp_model.CpModel()
    
    # Create variables for each possible swap
    swap_vars = {}
    for i, swap_analysis in enumerate(swap_analyses):
        for j, candidate in enumerate(swap_analysis.replacement_candidates):
            var_name = f"swap_{i}_{j}"
            swap_vars[(i, j)] = model.NewBoolVar(var_name)
    
    # Add constraints
    _add_swap_constraints(model, swap_vars, swap_analyses, original_lineup)
    
    # Set objective: maximize total projection
    objective_terms = []
    for i, swap_analysis in enumerate(swap_analyses):
        for j, candidate in enumerate(swap_analysis.replacement_candidates):
            projection_change = candidate.projection - swap_analysis.replacement_candidates[0].projection
            objective_terms.append(projection_change * swap_vars[(i, j)])
    
    model.Maximize(sum(objective_terms))
    
    return model, {"swap_vars": swap_vars}

def optimize_swaps(
    original_lineup,
    swap_analyses: List,
    players: List
) -> Optional:
    """
    Optimize swaps using OR-Tools
    
    Args:
        original_lineup: Original lineup
        swap_analyses: List of SwapAnalysis objects
        players: List of available players
        
    Returns:
        Optimized lineup or None if optimization fails
    """
    try:
        if not swap_analyses:
            logger.info("No swaps to optimize")
            return original_lineup
        
        # Create optimization model
        model, variables = create_swap_optimization_model(
            original_lineup, swap_analyses, players
        )
        
        # Create solver
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0
        solver.parameters.log_search_progress = False
        
        # Solve the model
        status = solver.Solve(model)
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            logger.info(f"Swap optimization successful - Status: {status}")
            
            # Apply the optimal swaps
            optimized_lineup = _apply_optimal_swaps(
                original_lineup, swap_analyses, variables, solver
            )
            
            if optimized_lineup:
                logger.info("Successfully created optimized lineup")
                return optimized_lineup
            else:
                logger.warning("Failed to apply optimal swaps")
                return None
        else:
            logger.warning(f"Swap optimization failed - Status: {status}")
            return None
            
    except Exception as e:
        logger.error(f"Error in swap optimization: {str(e)}")
        return None

def _add_swap_constraints(
    model: cp_model.CpModel,
    swap_vars: Dict,
    swap_analyses: List,
    original_lineup
) -> None:
    """
    Add constraints to the optimization model
    
    Args:
        model: OR-Tools model
        swap_vars: Dictionary of swap variables
        swap_analyses: List of SwapAnalysis objects
        original_lineup: Original lineup
    """
    # Constraint 1: At most one swap per player
    for i, swap_analysis in enumerate(swap_analyses):
        swap_vars_for_player = [
            swap_vars[(i, j)] for j in range(len(swap_analysis.replacement_candidates))
        ]
        model.Add(sum(swap_vars_for_player) <= 1)
    
    # Constraint 2: Salary cap
    current_salary = sum(player["Salary"] for player in original_lineup.players)
    salary_change_terms = []
    
    for i, swap_analysis in enumerate(swap_analyses):
        for j, candidate in enumerate(swap_analysis.replacement_candidates):
            original_player = next(
                p for p in original_lineup.players if p["Id"] == swap_analysis.player_id
            )
            salary_change = candidate.salary - original_player["Salary"]
            salary_change_terms.append(salary_change * swap_vars[(i, j)])
    
    model.Add(current_salary + sum(salary_change_terms) <= 35000)
    
    # Constraint 3: Stack preservation
    _add_stack_preservation_constraints(model, swap_vars, swap_analyses, original_lineup)

def _add_stack_preservation_constraints(
    model: cp_model.CpModel,
    swap_vars: Dict,
    swap_analyses: List,
    original_lineup
) -> None:
    """
    Add stack preservation constraints
    
    Args:
        model: OR-Tools model
        swap_vars: Dictionary of swap variables
        swap_analyses: List of SwapAnalysis objects
        original_lineup: Original lineup
    """
    # Identify primary and secondary stacks
    primary_stack, secondary_stack = _identify_stack_structure(original_lineup)
    
    if primary_stack:
        # Primary stack must have exactly 4 players
        primary_stack_terms = []
        for i, swap_analysis in enumerate(swap_analyses):
            if swap_analysis.team == primary_stack:
                for j, candidate in enumerate(swap_analysis.replacement_candidates):
                    if candidate.team == primary_stack:
                        primary_stack_terms.append(swap_vars[(i, j)])
        
        # Count current primary stack players
        current_primary_count = len([
            p for p in original_lineup.players 
            if p["Team"] == primary_stack and p["Slot"] != "P"
        ])
        
        # After swaps, primary stack should have 4 players
        model.Add(current_primary_count + sum(primary_stack_terms) == 4)
    
    if secondary_stack:
        # Secondary stack must have 3-4 players
        secondary_stack_terms = []
        for i, swap_analysis in enumerate(swap_analyses):
            if swap_analysis.team == secondary_stack:
                for j, candidate in enumerate(swap_analysis.replacement_candidates):
                    if candidate.team == secondary_stack:
                        secondary_stack_terms.append(swap_vars[(i, j)])
        
        # Count current secondary stack players
        current_secondary_count = len([
            p for p in original_lineup.players 
            if p["Team"] == secondary_stack and p["Slot"] != "P"
        ])
        
        # After swaps, secondary stack should have 3-4 players
        model.Add(current_secondary_count + sum(secondary_stack_terms) >= 3)
        model.Add(current_secondary_count + sum(secondary_stack_terms) <= 4)

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

def _apply_optimal_swaps(
    original_lineup,
    swap_analyses: List,
    variables: Dict,
    solver: cp_model.CpSolver
):
    """
    Apply the optimal swaps found by the solver
    
    Args:
        original_lineup: Original lineup
        swap_analyses: List of SwapAnalysis objects
        variables: Dictionary of variables
        solver: OR-Tools solver
        
    Returns:
        Optimized lineup or None if failed
    """
    try:
        # Create a copy of the original lineup
        new_players = list(original_lineup.players)
        
        # Apply each swap that was selected
        for i, swap_analysis in enumerate(swap_analyses):
            for j, candidate in enumerate(swap_analysis.replacement_candidates):
                var_key = (i, j)
                if var_key in variables["swap_vars"]:
                    if solver.Value(variables["swap_vars"][var_key]):
                        # Find the player to replace
                        for k, player in enumerate(new_players):
                            if player["Id"] == swap_analysis.player_id:
                                # Replace the player
                                new_players[k] = {
                                    "Slot": player["Slot"],
                                    "Name": candidate.name,
                                    "Team": candidate.team,
                                    "Opponent": candidate.opponent,
                                    "Positions": ",".join(candidate.positions),
                                    "Salary": candidate.salary,
                                    "Projection": candidate.projection,
                                    "Ownership": candidate.ownership,
                                    "Id": candidate.id,
                                    "Roster Order": candidate.roster_order
                                }
                                logger.info(f"Applied swap: {player['Name']} -> {candidate.name}")
                                break
        
        # Create new lineup object
        from MLB_Optimizer import Lineup
        return Lineup(new_players, original_lineup.primary_stack, original_lineup.secondary_stack)
        
    except Exception as e:
        logger.error(f"Error applying optimal swaps: {str(e)}")
        return None

def create_simple_swap_model(
    original_lineup,
    swap_analyses: List
) -> Optional:
    """
    Create a simple swap model without OR-Tools (fallback)
    
    Args:
        original_lineup: Original lineup
        swap_analyses: List of SwapAnalysis objects
        
    Returns:
        Optimized lineup or None if failed
    """
    try:
        # Sort by priority and apply swaps sequentially
        swap_analyses.sort(key=lambda x: x.swap_priority, reverse=True)
        
        optimized_lineup = original_lineup
        swaps_applied = []
        
        for swap_analysis in swap_analyses:
            if swap_analysis.best_replacement:
                # Check if this swap would be valid
                if _is_swap_valid(optimized_lineup, swap_analysis):
                    optimized_lineup = _apply_simple_swap(optimized_lineup, swap_analysis)
                    if optimized_lineup:
                        swaps_applied.append(swap_analysis)
                        logger.info(f"Applied simple swap: {swap_analysis.player_name} -> {swap_analysis.best_replacement.name}")
                    else:
                        logger.warning(f"Failed to apply simple swap for {swap_analysis.player_name}")
        
        if swaps_applied:
            logger.info(f"Applied {len(swaps_applied)} simple swaps")
            return optimized_lineup
        else:
            logger.warning("No simple swaps were applied")
            return None
            
    except Exception as e:
        logger.error(f"Error in simple swap model: {str(e)}")
        return None

def _is_swap_valid(lineup, swap_analysis) -> bool:
    """
    Check if a swap would be valid
    
    Args:
        lineup: Current lineup
        swap_analysis: SwapAnalysis object
        
    Returns:
        True if swap is valid
    """
    # Check salary constraints
    current_salary = sum(player["Salary"] for player in lineup.players)
    original_player = next(
        p for p in lineup.players if p["Id"] == swap_analysis.player_id
    )
    salary_change = swap_analysis.best_replacement.salary - original_player["Salary"]
    new_salary = current_salary + salary_change
    
    if new_salary > 35000:
        return False
    
    # Check pitcher-opponent constraints
    if swap_analysis.best_replacement.is_pitcher:
        for player in lineup.players:
            if player["Team"] == swap_analysis.best_replacement.opponent:
                return False
    else:
        for player in lineup.players:
            if (player["Slot"] == "P" and 
                player["Team"] == swap_analysis.best_replacement.opponent):
                return False
    
    return True

def _apply_simple_swap(lineup, swap_analysis):
    """
    Apply a simple swap to a lineup
    
    Args:
        lineup: Current lineup
        swap_analysis: SwapAnalysis object
        
    Returns:
        New lineup with swap applied
    """
    try:
        new_players = []
        
        for player in lineup.players:
            if player["Id"] == swap_analysis.player_id:
                # Replace with new player
                new_player_data = {
                    "Slot": player["Slot"],
                    "Name": swap_analysis.best_replacement.name,
                    "Team": swap_analysis.best_replacement.team,
                    "Opponent": swap_analysis.best_replacement.opponent,
                    "Positions": ",".join(swap_analysis.best_replacement.positions),
                    "Salary": swap_analysis.best_replacement.salary,
                    "Projection": swap_analysis.best_replacement.projection,
                    "Ownership": swap_analysis.best_replacement.ownership,
                    "Id": swap_analysis.best_replacement.id,
                    "Roster Order": swap_analysis.best_replacement.roster_order
                }
                new_players.append(new_player_data)
            else:
                new_players.append(player)
        
        # Create new lineup object
        from MLB_Optimizer import Lineup
        return Lineup(new_players, lineup.primary_stack, lineup.secondary_stack)
        
    except Exception as e:
        logger.error(f"Error applying simple swap: {str(e)}")
        return None 