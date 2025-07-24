"""
Player data model for MLB Optimizer
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Player:
    id: int
    name: str
    positions: List[str]
    team: str
    opponent: str
    salary: int
    projection: float
    is_pitcher: bool
    ownership: float
    roster_order: int = 0  # Added for consecutive order constraints

    def __post_init__(self):
        self.current_projection = self.projection  # Initialize current projection 