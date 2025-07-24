"""
Lineup data model for MLB Optimizer
"""

from dataclasses import dataclass
from typing import List, Dict


@dataclass
class Lineup:
    players: List[Dict]
    primary_stack: str
    secondary_stack: str 