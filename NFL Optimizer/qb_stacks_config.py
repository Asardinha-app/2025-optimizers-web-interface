"""
QB Stacks Configuration for NFL Optimizer

This module provides QB-specific stack configurations for the NFL optimizer.
QB stacks pair a quarterback with multiple skill position players (WR, RB, TE) 
from the same team for optimal correlation.

CONFIGURATION STRUCTURE:
- exactly_players: Exact number of skill players required (0 = use global minimum of 2)
- players: List of specific skill players to include in the stack

VALIDATION RULES:
- exactly_players must be 0 or >= 2 (global minimum)
- exactly_players must be <= 4 (global team limit)
- All player names must exist in the CSV data
"""

from typing import List, Dict, Optional

# QB Stack Configurations
QB_STACKS = {
    "Patrick Mahomes": {
        "exactly_players": 0,
        "players": [
            "Travis Kelce",
            "Isiah Pacheco", 
            "Rashee Rice",
            "Marquez Valdes-Scantling"
        ]
    },
    
    "Josh Allen": {
        "exactly_players": 0,
        "players": [
            "Stefon Diggs",
            "Gabe Davis",
            "Dalton Kincaid",
            "James Cook"
        ]
    },
    
    "Jalen Hurts": {
        "exactly_players": 0,
        "players": [
            "A.J. Brown",
            "DeVonta Smith",
            "D'Andre Swift",
            "Dallas Goedert"
        ]
    },
    
    "Joe Burrow": {
        "exactly_players": 0,
        "players": [
            "Ja'Marr Chase",
            "Tee Higgins",
            "Tyler Boyd",
            "Joe Mixon"
        ]
    },
    
    "Lamar Jackson": {
        "exactly_players": 0,
        "players": [
            "Mark Andrews",
            "Zay Flowers",
            "Gus Edwards",
            "Odell Beckham Jr."
        ]
    }
}

# Default configuration for QBs not specifically defined
DEFAULT_STACK = {
    "exactly_players": 0,
    "players": []
}


def get_qb_stack_config(qb_name: str) -> Dict:
    """Get stack configuration for a specific QB."""
    return QB_STACKS.get(qb_name, DEFAULT_STACK)


def get_all_qb_stacks() -> Dict:
    """Get all QB stack configurations."""
    return QB_STACKS.copy()


def validate_qb_stack_config(qb_name: str, config: Dict) -> List[str]:
    """Validate a QB stack configuration."""
    errors = []
    
    # Check required fields
    required_fields = ["exactly_players", "players"]
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
    
    # Check data types
    if "exactly_players" in config and not isinstance(config["exactly_players"], int):
        errors.append("exactly_players must be an integer")
    
    if "players" in config and not isinstance(config["players"], list):
        errors.append("players must be a list")
    
    # Validate exactly_players constraints
    if "exactly_players" in config:
        if config["exactly_players"] > 0 and config["exactly_players"] < 2:
            errors.append("exactly_players must be 0 or >= 2 to satisfy global minimum")
        if config["exactly_players"] > 4:
            errors.append("exactly_players must be <= 4 to satisfy global team limit")
    
    return errors


def validate_qb_stack_against_players(qb_name: str, config: Dict, available_players: List) -> Dict:
    """Validate QB stack configuration against available player pool."""
    results = {
        "is_valid": True,
        "missing_players": [],
        "found_players": [],
        "warnings": [],
        "errors": []
    }
    
    # Get available player names
    available_names = {p.name.split(":")[-1].strip() for p in available_players}
    
    # Check each player in the stack configuration
    for player_name in config.get('players', []):
        if player_name in available_names:
            results["found_players"].append(player_name)
        else:
            results["missing_players"].append(player_name)
    
    # Generate warnings and errors
    if results["missing_players"]:
        results["warnings"].append(f"QB {qb_name}: Missing players in stack: {results['missing_players']}")
        
        if len(results["found_players"]) == 0:
            results["errors"].append(f"QB {qb_name}: All stack players are missing from player pool")
            results["is_valid"] = False
        elif len(results["missing_players"]) > len(results["found_players"]):
            results["warnings"].append(f"QB {qb_name}: Most stack players are missing - stack may be ineffective")
    
    # Check exactly_players requirement
    if config.get('exactly_players', 0) > 0:
        if len(results["found_players"]) < config['exactly_players']:
            results["errors"].append(f"QB {qb_name}: Not enough available players ({len(results['found_players'])}) for exactly_players requirement ({config['exactly_players']})")
            results["is_valid"] = False
    
    return results


def validate_all_qb_stacks() -> Dict[str, List[str]]:
    """Validate all QB stack configurations."""
    validation_results = {}
    
    for qb_name, config in QB_STACKS.items():
        errors = validate_qb_stack_config(qb_name, config)
        validation_results[qb_name] = errors
    
    # Validate default stack
    errors = validate_qb_stack_config("DEFAULT", DEFAULT_STACK)
    validation_results["DEFAULT"] = errors
    
    return validation_results


def validate_all_qb_stacks_against_players(available_players: List) -> Dict:
    """Validate all QB stack configurations against the player pool."""
    results = {
        "valid_configs": [],
        "invalid_configs": {},
        "warnings": {},
        "missing_players_summary": {},
        "total_qbs": len(QB_STACKS),
        "valid_count": 0,
        "invalid_count": 0
    }
    
    for qb_name, config in QB_STACKS.items():
        validation = validate_qb_stack_against_players(qb_name, config, available_players)
        
        if validation["is_valid"]:
            results["valid_configs"].append(qb_name)
            results["valid_count"] += 1
        else:
            results["invalid_configs"][qb_name] = validation["errors"]
            results["invalid_count"] += 1
        
        if validation["warnings"]:
            results["warnings"][qb_name] = validation["warnings"]
        
        if validation["missing_players"]:
            results["missing_players_summary"][qb_name] = validation["missing_players"]
    
    return results


def get_qb_stack_config_with_validation(qb_name: str, available_players: Optional[List] = None) -> Dict:
    """Get QB stack configuration with optional validation against player pool."""
    config = get_qb_stack_config(qb_name)
    
    if available_players is not None:
        validation = validate_qb_stack_against_players(qb_name, config, available_players)
        if not validation["is_valid"]:
            print(f"Warning: QB stack configuration for {qb_name} has validation errors")
    
    return config


def print_qb_stack_config(qb_name: Optional[str] = None):
    """Print QB stack configuration(s)."""
    if qb_name:
        if qb_name in QB_STACKS:
            config = QB_STACKS[qb_name]
            print(f"\nQB Stack Configuration for {qb_name}:")
            print(f"  Exactly Players: {config['exactly_players']}")
            print(f"  Players: {config['players']}")
        else:
            print(f"No configuration found for QB: {qb_name}")
    else:
        print("\nAll QB Stack Configurations:")
        for qb_name, config in QB_STACKS.items():
            print(f"\n{qb_name}:")
            print(f"  Exactly Players: {config['exactly_players']}")
            print(f"  Players: {config['players']}")


if __name__ == "__main__":
    # Test the configuration
    print("Testing QB Stack Configuration...")
    print_qb_stack_config()
    
    # Validate configurations
    validation_results = validate_all_qb_stacks()
    print(f"\nValidation Results:")
    for qb_name, errors in validation_results.items():
        if errors:
            print(f"  {qb_name}: {errors}")
        else:
            print(f"  {qb_name}: Valid") 