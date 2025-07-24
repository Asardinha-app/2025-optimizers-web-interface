"""
CSV Handler for MLB Late Swap Optimizer

This module handles reading and writing CSV files in FanDuel template format.
"""

import csv
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

def load_template_lineups(file_path: str) -> List[Dict]:
    """
    Load lineups from FanDuel template CSV using pandas to handle duplicate column names
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        List of dictionaries containing lineup data
        
    Raises:
        FileNotFoundError: If the CSV file doesn't exist
        ValueError: If the CSV format is invalid
    """
    try:
        import pandas as pd
        
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Template file not found: {file_path}")
        
                # Use pandas to handle duplicate column names properly
        df = pd.read_csv(file_path)
        logger.info(f"Loaded CSV with columns: {list(df.columns)}")
        
        lineups = []
        
        # Validate required columns - handle multiple OF columns
        required_columns = ['P', 'C/1B', '2B', '3B', 'SS', 'UTIL']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        # Check for OF columns (can be OF, OF.1, OF.2 or similar)
        of_columns = [col for col in df.columns if col.startswith('OF')]
        if not of_columns:
            missing_columns.append('OF')
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Process each row
        for row_num, (index, row) in enumerate(df.iterrows(), start=2):  # Start at 2 to account for header
                try:
                    # Check if this is a blank row (no entry_id) - stop reading here
                    # Look for entry_id in various formats
                    entry_id = row.get('entry_id') or row.get('Entry ID') or row.get('Entry_ID')
                    if not entry_id or pd.isna(entry_id) or not str(entry_id).strip():
                        logger.info(f"Stopping at row {row_num} - blank row detected (end of lineup entries)")
                        break
                    
                    # Convert pandas Series to dict
                    row_dict = row.to_dict()
                    
                    # Validate that this row has lineup data
                    if _is_valid_lineup_row(row_dict):
                        lineups.append(row_dict)
                    else:
                        logger.warning(f"Skipping row {row_num} - no valid lineup data")
                        # Debug: Print the row to see what's wrong
                        logger.debug(f"Row {row_num} data: {row_dict}")
                        
                except Exception as e:
                    logger.warning(f"Error processing row {row_num}: {str(e)}")
                    continue
        
        logger.info(f"Successfully loaded {len(lineups)} lineups from {file_path}")
        return lineups
        
    except Exception as e:
        logger.error(f"Error loading template lineups: {str(e)}")
        raise

def export_swapped_lineups(lineups: List, output_path: str) -> None:
    """
    Export swapped lineups to CSV in FanDuel format
    
    Args:
        lineups: List of LateSwapLineup objects
        output_path: Path to output CSV file
        
    Raises:
        ValueError: If no valid lineups to export
    """
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Filter valid lineups
        valid_lineups = []
        for lineup in lineups:
            if hasattr(lineup, 'swapped_lineup') and lineup.swapped_lineup:
                valid_lineups.append(lineup.swapped_lineup)
            elif hasattr(lineup, 'original_lineup'):
                # If no swap was made, use original lineup
                valid_lineups.append(lineup.original_lineup)
        
        if not valid_lineups:
            raise ValueError("No valid lineups to export")
        
        # FanDuel position order
        fd_position_order = ['P', 'C/1B', '2B', '3B', 'SS', 'OF', 'OF', 'OF', 'UTIL']
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(fd_position_order)
            
            # Write each lineup
            for lineup in valid_lineups:
                row = _create_lineup_row(lineup, fd_position_order)
                if row:
                    writer.writerow(row)
        
        logger.info(f"Successfully exported {len(valid_lineups)} lineups to {output_path}")
        
    except Exception as e:
        logger.error(f"Error exporting lineups: {str(e)}")
        raise

def validate_csv_format(csv_data: List[Dict]) -> bool:
    """
    Validate CSV has required columns and format
    
    Args:
        csv_data: List of dictionaries containing CSV data
        
    Returns:
        True if format is valid, False otherwise
    """
    if not csv_data:
        logger.warning("CSV data is empty")
        return False
    
    # Check required columns
    required_columns = ['P', 'C/1B', '2B', '3B', 'SS', 'OF', 'UTIL']
    sample_row = csv_data[0]
    
    missing_columns = [col for col in required_columns if col not in sample_row]
    if missing_columns:
        logger.error(f"Missing required columns: {missing_columns}")
        return False
    
    # Check that at least one row has valid lineup data
    has_valid_lineup = False
    for row in csv_data:
        if _is_valid_lineup_row(row):
            has_valid_lineup = True
            break
    
    if not has_valid_lineup:
        logger.error("No valid lineup data found in CSV")
        return False
    
    logger.info("CSV format validation passed")
    return True

def _is_valid_lineup_row(row: Dict) -> bool:
    """
    Check if a CSV row contains valid lineup data
    
    Args:
        row: Dictionary representing a CSV row
        
    Returns:
        True if row contains valid lineup data
    """
    # Check if any of the position columns have data
    position_columns = ['P', 'C/1B', '2B', '3B', 'SS', 'OF', 'UTIL']
    
    for col in position_columns:
        if col in row and row[col] and str(row[col]).strip():
            return True
    
    return False

def _create_lineup_row(lineup, fd_position_order: List[str]) -> Optional[List]:
    """
    Create a CSV row from a lineup object
    
    Args:
        lineup: Lineup object
        fd_position_order: List of positions in FanDuel order
        
    Returns:
        List of player IDs in FanDuel order, or None if invalid
    """
    try:
        # Create position map for this lineup
        position_map = {}
        outfielders = []
        util_candidates = []
        
        for player in lineup.players:
            if player["Slot"] == "OF":
                outfielders.append(player)
            elif player["Slot"] == "UTIL":
                util_candidates.append(player)
            else:
                position_map[player["Slot"]] = player
        
        # Build row in FanDuel order
        row = []
        for pos in fd_position_order:
            if pos == 'OF':
                if outfielders:
                    player = outfielders.pop(0)
                    player_id_with_nickname = _format_player_id_with_nickname(player)
                    row.append(player_id_with_nickname)
                else:
                    row.append("")  # Empty cell for missing OF
            elif pos == 'UTIL':
                if util_candidates:
                    player = util_candidates[0]
                    player_id_with_nickname = _format_player_id_with_nickname(player)
                    row.append(player_id_with_nickname)
                else:
                    row.append("")  # Empty cell for missing UTIL
            else:
                if pos in position_map:
                    player = position_map[pos]
                    player_id_with_nickname = _format_player_id_with_nickname(player)
                    row.append(player_id_with_nickname)
                else:
                    row.append("")  # Empty cell for missing position
        
        return row
        
    except Exception as e:
        logger.error(f"Error creating lineup row: {str(e)}")
        return None

def _format_player_id_with_nickname(player: Dict) -> str:
    """
    Format player ID with nickname as "Id:Nickname"
    
    Args:
        player: Player dictionary containing Id and Name
        
    Returns:
        Formatted string "Id:Nickname"
    """
    try:
        player_id = player["Id"]
        player_name = player["Name"]
        
        # Extract nickname from player name
        # Player name format is typically "Player ID + Player Name" or just "Player Name"
        # We want to extract just the nickname part
        if ":" in player_name:
            # Format: "118836-198625:Player Name"
            nickname = player_name.split(":", 1)[1].strip()
        else:
            # Format: "Player Name" - use the full name as nickname
            nickname = player_name.strip()
        
        # Return formatted string
        return f"{player_id}:{nickname}"
        
    except Exception as e:
        logger.error(f"Error formatting player ID with nickname: {str(e)}")
        # Fallback to just the ID if there's an error
        return str(player.get("Id", ""))

def create_sample_template(output_path: str, num_lineups: int = 5) -> None:
    """
    Create a sample FanDuel template CSV for testing
    
    Args:
        output_path: Path to output the sample template
        num_lineups: Number of sample lineups to create
    """
    try:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Sample player IDs (these would be replaced with real IDs)
        sample_player_ids = {
            'P': [1001, 1002, 1003, 1004, 1005],
            'C/1B': [2001, 2002, 2003, 2004, 2005],
            '2B': [3001, 3002, 3003, 3004, 3005],
            '3B': [4001, 4002, 4003, 4004, 4005],
            'SS': [5001, 5002, 5003, 5004, 5005],
            'OF': [6001, 6002, 6003, 6004, 6005, 6006, 6007, 6008, 6009],
            'UTIL': [7001, 7002, 7003, 7004, 7005]
        }
        
        fd_position_order = ['P', 'C/1B', '2B', '3B', 'SS', 'OF', 'OF', 'OF', 'UTIL']
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow(fd_position_order)
            
            # Write sample lineups
            for i in range(num_lineups):
                row = []
                for pos in fd_position_order:
                    if pos == 'OF':
                        # Add one outfielder per OF position
                        player_id = sample_player_ids['OF'][(i + len(row)) % len(sample_player_ids['OF'])]
                        row.append(player_id)
                    else:
                        player_id = sample_player_ids[pos][i % len(sample_player_ids[pos])]
                        row.append(player_id)
                
                writer.writerow(row)
        
        logger.info(f"Created sample template with {num_lineups} lineups at {output_path}")
        
    except Exception as e:
        logger.error(f"Error creating sample template: {str(e)}")
        raise 