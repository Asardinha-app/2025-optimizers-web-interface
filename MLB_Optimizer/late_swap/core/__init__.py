"""
Core components for MLB Late Swap Optimizer

This module contains the core logic for analyzing lineups, preserving stacks,
validating constraints, and optimizing swaps.
"""

from .swap_analyzer import SwapAnalysis, analyze_lineup_for_swaps, should_skip_lineup
from .stack_preserver import preserve_primary_stack, preserve_secondary_stack
from .constraint_validator import validate_lineup_constraints, validate_salary_cap
from .swap_optimizer import optimize_swaps, create_swap_optimization_model

__all__ = [
    "SwapAnalysis",
    "analyze_lineup_for_swaps", 
    "should_skip_lineup",
    "preserve_primary_stack",
    "preserve_secondary_stack",
    "validate_lineup_constraints",
    "validate_salary_cap",
    "optimize_swaps",
    "create_swap_optimization_model"
] 