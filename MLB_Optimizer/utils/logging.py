"""
Swap Logger for MLB Late Swap Optimizer

This module handles logging for swap operations, validation results, and performance metrics.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

def setup_logger(log_level: int, log_file: str) -> logging.Logger:
    """
    Set up logging configuration
    
    Args:
        log_level: Logging level (e.g., logging.INFO)
        log_file: Path to log file
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger('mlb_late_swap')
    logger.setLevel(log_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

def log_swap_operation(
    logger: logging.Logger,
    lineup_index: int,
    original_player: Dict,
    replacement_player: Dict,
    swap_reason: str,
    stack_preserved: bool = True
) -> None:
    """
    Log a swap operation
    
    Args:
        logger: Logger instance
        lineup_index: Index of the lineup being processed
        original_player: Original player data
        replacement_player: Replacement player data
        swap_reason: Reason for the swap
        stack_preserved: Whether the stack was preserved
    """
    logger.info(
        f"Lineup {lineup_index}: SWAP - "
        f"{original_player['Name']} ({original_player['Team']}) -> "
        f"{replacement_player['Name']} ({replacement_player['Team']}) - "
        f"Reason: {swap_reason} - "
        f"Stack Preserved: {stack_preserved}"
    )
    
    # Log projection change
    projection_change = replacement_player['Projection'] - original_player['Projection']
    logger.info(
        f"Lineup {lineup_index}: Projection change: "
        f"{original_player['Projection']:.2f} -> {replacement_player['Projection']:.2f} "
        f"({projection_change:+.2f})"
    )

def log_lineup_validation(
    logger: logging.Logger,
    lineup_index: int,
    is_valid: bool,
    validation_errors: List[str] = None
) -> None:
    """
    Log lineup validation results
    
    Args:
        logger: Logger instance
        lineup_index: Index of the lineup being validated
        is_valid: Whether the lineup is valid
        validation_errors: List of validation errors
    """
    if is_valid:
        logger.info(f"Lineup {lineup_index}: VALID - All constraints satisfied")
    else:
        logger.warning(f"Lineup {lineup_index}: INVALID - Constraint violations detected")
        if validation_errors:
            for error in validation_errors:
                logger.warning(f"Lineup {lineup_index}: {error}")

def log_stack_analysis(
    logger: logging.Logger,
    lineup_index: int,
    primary_stack: str,
    secondary_stack: str,
    stack_players: Dict[str, List[Dict]]
) -> None:
    """
    Log stack analysis results
    
    Args:
        logger: Logger instance
        lineup_index: Index of the lineup being analyzed
        primary_stack: Primary stack team
        secondary_stack: Secondary stack team
        stack_players: Dictionary of players by stack type
    """
    logger.info(f"Lineup {lineup_index}: Stack Analysis")
    logger.info(f"  Primary Stack: {primary_stack} ({len(stack_players.get('primary', []))} players)")
    logger.info(f"  Secondary Stack: {secondary_stack} ({len(stack_players.get('secondary', []))} players)")
    
    for stack_type, players in stack_players.items():
        if players:
            logger.info(f"  {stack_type.title()} Stack Players:")
            for player in players:
                logger.info(f"    {player['Name']} ({player['Team']}) - Proj: {player['Projection']:.2f}")

def log_skip_reason(
    logger: logging.Logger,
    lineup_index: int,
    reason: str
) -> None:
    """
    Log why a lineup was skipped
    
    Args:
        logger: Logger instance
        lineup_index: Index of the lineup being skipped
        reason: Reason for skipping
    """
    logger.info(f"Lineup {lineup_index}: SKIPPED - {reason}")

def log_performance_metrics(
    logger: logging.Logger,
    total_lineups: int,
    processed_lineups: int,
    valid_lineups: int,
    skipped_lineups: int,
    total_projection_change: float,
    processing_time: float
) -> None:
    """
    Log performance metrics
    
    Args:
        logger: Logger instance
        total_lineups: Total number of lineups
        processed_lineups: Number of processed lineups
        valid_lineups: Number of valid lineups
        skipped_lineups: Number of skipped lineups
        total_projection_change: Total projection change across all lineups
        processing_time: Total processing time in seconds
    """
    logger.info("=== Performance Summary ===")
    logger.info(f"Total Lineups: {total_lineups}")
    logger.info(f"Processed Lineups: {processed_lineups}")
    logger.info(f"Valid Lineups: {valid_lineups}")
    logger.info(f"Skipped Lineups: {skipped_lineups}")
    logger.info(f"Success Rate: {(valid_lineups / max(1, total_lineups)) * 100:.1f}%")
    logger.info(f"Average Projection Change: {total_projection_change / max(1, processed_lineups):.2f}")
    logger.info(f"Processing Time: {processing_time:.2f} seconds")
    logger.info(f"Average Time per Lineup: {processing_time / max(1, total_lineups):.3f} seconds")

def log_error(
    logger: logging.Logger,
    error_type: str,
    error_message: str,
    lineup_index: Optional[int] = None,
    additional_info: Dict = None
) -> None:
    """
    Log an error with context
    
    Args:
        logger: Logger instance
        error_type: Type of error
        error_message: Error message
        lineup_index: Index of the lineup where error occurred
        additional_info: Additional error information
    """
    context = f"Lineup {lineup_index}" if lineup_index else "General"
    logger.error(f"{context}: {error_type} - {error_message}")
    
    if additional_info:
        for key, value in additional_info.items():
            logger.error(f"  {key}: {value}")

def log_constraint_violation(
    logger: logging.Logger,
    lineup_index: int,
    constraint_type: str,
    constraint_details: str,
    severity: str = "WARNING"
) -> None:
    """
    Log a constraint violation
    
    Args:
        logger: Logger instance
        lineup_index: Index of the lineup
        constraint_type: Type of constraint violated
        constraint_details: Details about the violation
        severity: Severity level (WARNING, ERROR)
    """
    if severity.upper() == "ERROR":
        logger.error(f"Lineup {lineup_index}: Constraint Violation - {constraint_type}: {constraint_details}")
    else:
        logger.warning(f"Lineup {lineup_index}: Constraint Violation - {constraint_type}: {constraint_details}")

def log_stack_preservation_attempt(
    logger: logging.Logger,
    lineup_index: int,
    stack_type: str,
    team: str,
    success: bool,
    details: str = ""
) -> None:
    """
    Log stack preservation attempt
    
    Args:
        logger: Logger instance
        lineup_index: Index of the lineup
        stack_type: Type of stack (primary/secondary)
        team: Team name
        success: Whether preservation was successful
        details: Additional details
    """
    status = "SUCCESS" if success else "FAILED"
    logger.info(f"Lineup {lineup_index}: {stack_type.title()} Stack Preservation ({team}) - {status}")
    if details:
        logger.info(f"Lineup {lineup_index}: {details}")

def create_summary_report(
    processed_lineups: List,
    output_file: str = None
) -> str:
    """
    Create a summary report of the processing results
    
    Args:
        processed_lineups: List of processed lineup objects
        output_file: Optional file path to save the report
        
    Returns:
        Summary report as string
    """
    total_lineups = len(processed_lineups)
    valid_lineups = sum(1 for l in processed_lineups if l.is_valid)
    skipped_lineups = sum(1 for l in processed_lineups if l.skipped_reason)
    swapped_lineups = sum(1 for l in processed_lineups if l.swapped_lineup and l.swapped_lineup != l.original_lineup)
    
    total_projection_change = sum(l.total_projection_change for l in processed_lineups)
    avg_projection_change = total_projection_change / max(1, total_lineups)
    
    report = f"""
MLB Late Swap Optimizer - Summary Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Processing Results:
- Total Lineups: {total_lineups}
- Valid Lineups: {valid_lineups}
- Skipped Lineups: {skipped_lineups}
- Swapped Lineups: {swapped_lineups}
- Success Rate: {(valid_lineups / max(1, total_lineups)) * 100:.1f}%

Projection Changes:
- Total Projection Change: {total_projection_change:+.2f}
- Average Projection Change: {avg_projection_change:+.2f}

Stack Preservation:
- Primary Stacks Preserved: {sum(1 for l in processed_lineups if l.primary_stack_preserved)}
- Secondary Stacks Preserved: {sum(1 for l in processed_lineups if l.secondary_stack_preserved)}

Skipped Lineups:
"""
    
    # Add details about skipped lineups
    skip_reasons = {}
    for lineup in processed_lineups:
        if lineup.skipped_reason:
            reason = lineup.skipped_reason
            skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
    
    for reason, count in skip_reasons.items():
        report += f"- {reason}: {count} lineups\n"
    
    if output_file:
        with open(output_file, 'w') as f:
            f.write(report)
    
    return report 