"""
Swap data models for MLB Late Swap Optimizer
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from .player import Player


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
    replacement_candidates: List[Player]
    best_replacement: Optional[Player]
    swap_priority: int  # Higher priority for stack players
    
    def __post_init__(self):
        """Set swap priority based on stack type"""
        if self.stack_type == "primary":
            self.swap_priority = 3
        elif self.stack_type == "secondary":
            self.swap_priority = 2
        else:
            self.swap_priority = 1


@dataclass
class LateSwapLineup:
    """Enhanced lineup class for late swap operations"""
    original_lineup: 'Lineup'
    swapped_lineup: Optional['Lineup']
    swaps_made: List[Dict]  # Track what was swapped
    is_valid: bool
    total_projection_change: float
    primary_stack_preserved: bool
    secondary_stack_preserved: bool
    skipped_reason: Optional[str] = None
    
    def __post_init__(self):
        """Calculate projection change if swapped lineup exists"""
        if self.swapped_lineup:
            original_projection = sum(p["Projection"] for p in self.original_lineup.players)
            swapped_projection = sum(p["Projection"] for p in self.swapped_lineup.players)
            self.total_projection_change = swapped_projection - original_projection
        else:
            self.total_projection_change = 0.0 