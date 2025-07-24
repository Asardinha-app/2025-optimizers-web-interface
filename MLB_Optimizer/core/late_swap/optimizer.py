"""
MLB Late Swap Optimizer
This script optimizes MLB DFS lineups when players are out of the batting order
while preserving stack integrity and maintaining all original MLB Optimizer constraints.
"""

from typing import List, Dict, Set, Tuple, Optional
import pandas as pd
from dataclasses import dataclass
from pathlib import Path
import csv
import logging
from datetime import datetime

# Import from original MLB Optimizer
from core.optimizer import Config as MLBConfig, Player, Lineup

# Import late swap components
from .analyzer import SwapAnalysis, analyze_lineup_for_swaps, should_skip_lineup
from data.processors.csv_handler import load_template_lineups, export_swapped_lineups
from utils.logging import setup_logger
from .engine import LateSwapEngine

# ===== Configuration =====
class LateSwapConfig:
    """Configuration for the Late Swap Optimizer"""
    
    # File paths
    TEMPLATE_FILE_PATH = "/Users/adamsardinha/Downloads/FanDuel-MLB-2025-07-22-118836-entries-upload-template.csv"  # Real FanDuel template
    DATA_FILE = "/Users/adamsardinha/Desktop/MLB_FD.csv"  # Current player pool
    OUTPUT_FILE_PATH = "/Users/adamsardinha/Desktop/FD_MLB_Late_Swap_Lineups.csv"
    
    # Swap settings
    MAX_SWAP_ATTEMPTS = 100
    PRESERVE_STACKS = True
    MAINTAIN_SALARY_CAP = True
    SKIP_INVALID_LINEUPS = True  # Skip if no valid swaps possible
    PREFER_MULTI_SWAP = True
    PREFER_STACK_PRESERVATION = True
    
    # Data filtering settings
    FILTER_ROSTER_ORDER_ZERO = False  # Keep all players in pool, treat Roster Order 0 as constraint
    
    # Locked Teams - Teams whose games have started (players cannot be swapped out)
    LOCKED_TEAMS = [
        # Add teams here manually when their games start
        # Example: "NYY", "BOS", "LAD", etc.
    ]
    
    # Inherit all constraints from MLB_Optimizer.py
    MAX_SALARY = 35000
    SLOTS = {
        "P": 1, "C/1B": 1, "2B": 1, "3B": 1, "SS": 1, "OF": 3, "UTIL": 1
    }
    
    # FanDuel position order for CSV output
    FD_POSITION_ORDER = ['P', 'C/1B', '2B', '3B', 'SS', 'OF', 'OF', 'OF', 'UTIL']
    
    # Logging settings
    LOG_LEVEL = logging.INFO  # Changed from DEBUG to INFO for better performance
    LOG_FILE = f"logs/late_swap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Import data models
from ..models.player import Player
from ..models.lineup import Lineup
from ..models.swap import SwapAnalysis, LateSwapLineup

class LateSwapOptimizer:
    """Main class for late swap optimization"""
    
    def __init__(self, config: LateSwapConfig = None):
        """Initialize the late swap optimizer"""
        self.config = config or LateSwapConfig()
        self.logger = setup_logger(self.config.LOG_LEVEL, self.config.LOG_FILE)
        self.players = []
        self.lineups = []
        self.processed_lineups = []
        
    def load_data(self) -> bool:
        """Load player pool and template lineups"""
        try:
            # Load player pool from MLB_FD.csv
            df = pd.read_csv(self.config.DATA_FILE)
            self.logger.info(f"Loaded raw data: {len(df)} total players")

            # Create player objects (no filtering - Roster Order 0 handled as constraint)
            self.players = self._create_player_objects(df)
            self.logger.info(f"Player pool: {len(self.players)} available players")

            # Load template lineups
            self.lineups = load_template_lineups(self.config.TEMPLATE_FILE_PATH)
            self.logger.info(f"Loaded {len(self.lineups)} lineups from template")

            return True

        except Exception as e:
            self.logger.error(f"Error loading data: {str(e)}")
            return False
    
    def _create_player_objects(self, df: pd.DataFrame) -> List[Player]:
        """Convert DataFrame rows to Player objects"""
        players = []
        seen_ids = set()  # Track seen IDs to prevent duplicates
        filtered_count = 0

        for idx, row in df.iterrows():
            try:
                positions = row["Position"].split("/")
                name = row["Player ID + Player Name"]

                # Get roster order, defaulting to 0 for pitchers
                roster_order = 0
                if "P" not in positions:
                    try:
                        roster_order = int(row["Roster Order"])
                    except (ValueError, TypeError):
                        self.logger.warning(f"Invalid roster order for {name}: {row['Roster Order']}")
                        roster_order = 0

                # Extract numeric ID from the full ID string with better error handling
                full_id = row["Id"]
                try:
                    # Handle different ID formats
                    if isinstance(full_id, str):
                        if '-' in full_id:
                            # Format: "118836-52859" -> extract "52859"
                            numeric_id = int(full_id.split('-')[-1])
                        else:
                            # Format: "52859" -> use directly
                            numeric_id = int(full_id)
                    else:
                        # Handle numeric IDs directly
                        numeric_id = int(full_id)
                except (ValueError, IndexError, TypeError) as e:
                    self.logger.warning(f"Could not extract numeric ID from {full_id}: {e}")
                    continue

                # Check for duplicate IDs
                if numeric_id in seen_ids:
                    self.logger.warning(f"Duplicate player ID found: {numeric_id} ({name}) - skipping")
                    continue
                seen_ids.add(numeric_id)

                # Validate required fields
                if pd.isna(row["Salary"]) or pd.isna(row["FPPG"]):
                    self.logger.warning(f"Missing salary or projection for {name} - skipping")
                    continue

                # Create player object
                player = Player(
                    id=numeric_id,
                    name=name,
                    positions=positions,
                    team=row["Team"],
                    opponent=row["Opponent"],
                    salary=int(row["Salary"]),
                    projection=round(row["FPPG"], 2),
                    is_pitcher="P" in positions,
                    ownership=float(row.get("Projected Ownership", 0)),
                    roster_order=roster_order
                )
                
                players.append(player)

            except Exception as e:
                self.logger.warning(f"Error processing row {idx}: {e}")
                continue

        self.logger.info(f"Loaded {len(players)} total players (including Roster Order 0 players)")
        self.logger.info(f"Unique player IDs: {len(seen_ids)}")
        return players
    
    def process_lineups(self) -> List[LateSwapLineup]:
        """Process all lineups for late swap optimization"""
        self.logger.info("Starting lineup processing...")
        
        swapped_lineups_count = 0
        skipped_lineups_count = 0
        duplicate_lineups_count = 0
        failed_lineups_count = 0
        
        for i, lineup_data in enumerate(self.lineups):
            # Parse lineup from CSV data
            lineup = self._parse_lineup_from_csv(lineup_data)
            if not lineup:
                # Check if this was due to duplicates
                if "duplicate" in str(lineup_data).lower():
                    duplicate_lineups_count += 1
                    self.logger.warning(f"Lineup {i+1} skipped due to duplicate players")
                else:
                    failed_lineups_count += 1
                    self.logger.warning(f"Failed to parse lineup {i+1} (likely contains players with Roster Order 0)")
                continue
            
            # Check if lineup should be skipped
            if should_skip_lineup(lineup, self.players):
                skipped_lineups_count += 1
                processed_lineup = LateSwapLineup(
                    original_lineup=lineup,
                    swapped_lineup=None,
                    swaps_made=[],
                    is_valid=True,
                    total_projection_change=0.0,
                    primary_stack_preserved=True,
                    secondary_stack_preserved=True,
                    skipped_reason="All batters have valid roster orders (1-9)"
                )
                self.processed_lineups.append(processed_lineup)
                continue
            
            # Analyze lineup for swaps
            swap_analyses = analyze_lineup_for_swaps(lineup, self.players, self.config)
            
            if not swap_analyses:
                skipped_lineups_count += 1
                processed_lineup = LateSwapLineup(
                    original_lineup=lineup,
                    swapped_lineup=None,  # No swap was made
                    swaps_made=[],
                    is_valid=True,
                    total_projection_change=0.0,
                    primary_stack_preserved=True,
                    secondary_stack_preserved=True,
                    skipped_reason="No swaps needed - all players have valid roster orders"
                )
                self.processed_lineups.append(processed_lineup)
                continue
            
            # Lineup has players that need swapping - perform optimization
            swapped_lineups_count += 1
            
            # Perform actual swap optimization
            engine = LateSwapEngine(self.config)
            swap_result = engine.optimize_lineup(lineup, self.players)
            
            if swap_result.is_successful and swap_result.optimized_lineup:
                # Create swapped lineup
                swapped_lineup = swap_result.optimized_lineup
                
                # Calculate projection change
                original_projection = sum(p["Projection"] for p in lineup.players)
                swapped_projection = sum(p["Projection"] for p in swapped_lineup.players)
                projection_change = swapped_projection - original_projection
                
                # Create processed lineup with actual swaps
                processed_lineup = LateSwapLineup(
                    original_lineup=lineup,
                    swapped_lineup=swapped_lineup,
                    swaps_made=swap_result.swaps_made,
                    is_valid=True,
                    total_projection_change=projection_change,
                    primary_stack_preserved=swap_result.preserves_all_stacks,
                    secondary_stack_preserved=swap_result.preserves_all_stacks,
                    skipped_reason=None
                )
                
                # Log successful swaps (only for lineups with actual swaps)
                self.logger.info(f"Lineup {i+1}: {len(swap_result.swaps_made)} swaps made, projection change: {projection_change:.2f}")
                
            else:
                # Swap failed - create processed lineup with error
                processed_lineup = LateSwapLineup(
                    original_lineup=lineup,
                    swapped_lineup=None,
                    swaps_made=[],
                    is_valid=False,
                    total_projection_change=0.0,
                    primary_stack_preserved=False,
                    secondary_stack_preserved=False,
                    skipped_reason=f"Swap optimization failed: {swap_result.error_message}"
                )
                
                self.logger.warning(f"Lineup {i+1}: Swap optimization failed - {swap_result.error_message}")
            
            self.processed_lineups.append(processed_lineup)
        
        # Summary at the end
        self.logger.info(f"\n=== PROCESSING SUMMARY ===")
        self.logger.info(f"Total lineups processed: {len(self.processed_lineups)}")
        self.logger.info(f"Lineups with swaps needed: {swapped_lineups_count}")
        self.logger.info(f"Lineups skipped (no swaps needed): {skipped_lineups_count}")
        self.logger.info(f"Lineups with duplicates (skipped): {duplicate_lineups_count}")
        self.logger.info(f"Lineups with parsing errors: {failed_lineups_count}")
        
        # Update the processed lineups to have proper skipped_reason for valid lineups
        for lineup in self.processed_lineups:
            if lineup.swapped_lineup is None and lineup.is_valid and not lineup.skipped_reason:
                lineup.skipped_reason = "No swaps needed - all players have valid roster orders"
        
        return self.processed_lineups
    
    def _parse_lineup_from_csv(self, lineup_data: Dict) -> Optional[Lineup]:
        """Parse lineup from CSV row data using simple parser"""
        try:
            # Import the simple parser
            try:
                from utils.helpers import parse_lineup_simple
            except Exception as e:
                self.logger.error(f"Failed to import parse_lineup_simple: {e}")
                return None
            
            # Create a clean copy of the lineup data
            clean_lineup_data = {}
            for key, value in lineup_data.items():
                if key not in ['Entry ID', 'Contest Entry ID', 'Entry Name']:
                    clean_lineup_data[key] = value
            
            # Call the simple parser
            try:
                lineup_result = parse_lineup_simple(
                    clean_lineup_data,
                    self.players, 
                    self.config.FD_POSITION_ORDER
                )
            except Exception as e:
                self.logger.error(f"Failed to call parse_lineup_simple: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                return None
            if not lineup_result:
                self.logger.warning("Failed to parse lineup using simple parser")
                return None
            
            # Unpack the result
            lineup_players, primary_stack, secondary_stack = lineup_result
            
            # Validate the parsed lineup
            if len(lineup_players) != 9:
                self.logger.warning(f"Invalid lineup - expected 9 players, got {len(lineup_players)}")
                return None
            
            # Create Lineup object
            from MLB_Optimizer import Lineup
            return Lineup(lineup_players, primary_stack, secondary_stack)
            
        except Exception as e:
            self.logger.error(f"Error parsing lineup: {str(e)}")
            return None
    

    
    def export_results(self) -> bool:
        """Export processed lineups to CSV"""
        try:
            export_swapped_lineups(self.processed_lineups, self.config.OUTPUT_FILE_PATH)
            self.logger.info(f"Exported results to {self.config.OUTPUT_FILE_PATH}")
            return True
        except Exception as e:
            self.logger.error(f"Error exporting results: {str(e)}")
            return False
    
    def run(self) -> bool:
        """Run the complete late swap optimization process"""
        self.logger.info("Starting MLB Late Swap Optimizer")
        
        # Load data
        if not self.load_data():
            return False
        
        # Process lineups
        processed_lineups = self.process_lineups()
        
        # Export results
        if not self.export_results():
            return False
        
        # Generate summary
        self._generate_summary(processed_lineups)
        
        self.logger.info("MLB Late Swap Optimizer completed successfully")
        return True
    
    def _generate_summary(self, processed_lineups: List[LateSwapLineup]):
        """Generate a summary of the processing results"""
        total_lineups = len(processed_lineups)
        swapped_lineups = [l for l in processed_lineups if l.swapped_lineup is not None]
        
        skipped_lineups = [l for l in processed_lineups if l.skipped_reason and ("no swaps needed" in l.skipped_reason.lower() or "all batters have valid roster orders" in l.skipped_reason.lower())]
        failed_lineups = [l for l in processed_lineups if l.skipped_reason and "no swaps needed" not in l.skipped_reason.lower() and "all batters have valid roster orders" not in l.skipped_reason.lower()]
        
        self.logger.info(f"\n=== FINAL SUMMARY ===")
        self.logger.info(f"Total lineups processed: {total_lineups}")
        self.logger.info(f"Lineups with successful swaps: {len(swapped_lineups)}")
        self.logger.info(f"Lineups skipped (no swaps needed): {len(skipped_lineups)}")
        self.logger.info(f"Lineups with failed swaps: {len(failed_lineups)}")
        
        if swapped_lineups:
            total_projection_change = sum(l.total_projection_change for l in swapped_lineups)
            avg_projection_change = total_projection_change / len(swapped_lineups)
            self.logger.info(f"Total projection improvement: {total_projection_change:.2f}")
            self.logger.info(f"Average projection change per swapped lineup: {avg_projection_change:.2f}")
        elif len(skipped_lineups) == total_lineups:
            self.logger.info("No lineups required swaps - all lineups are valid")
        else:
            self.logger.info("Some lineups had issues that prevented swaps")

def main():
    """Main function to run the late swap optimizer"""
    optimizer = LateSwapOptimizer()
    success = optimizer.run()
    
    if success:
        print("✅ Late Swap Optimizer completed successfully")
    else:
        print("❌ Late Swap Optimizer failed")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 