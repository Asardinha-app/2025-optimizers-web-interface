"""
MLB Late Swap Optimizer Package

This package provides functionality for optimizing MLB DFS lineups when players
are out of the batting order (roster_order == 0) while preserving stack integrity
and maintaining all original MLB Optimizer constraints.
"""

__version__ = "1.0.0"
__author__ = "MLB Optimizer Team"

from .core.swap_analyzer import SwapAnalysis
from .core.constraint_validator import validate_lineup_constraints

__all__ = [
    "SwapAnalysis",
    "validate_lineup_constraints"
] 