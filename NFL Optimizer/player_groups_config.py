"""
Player Groups Configuration for NFL Optimizer

This module defines player group configurations that create constraints for how players
can be combined in lineups. Groups can enforce minimum/maximum player counts and create
conditional relationships.

Configuration Structure:
- group_name: Unique identifier for the group
- type: "Min", "Max", or "QB_RB_Restriction"
- min_players/max_players: Player count constraints
- players: List of player names in the group
- team: Team abbreviation filter (optional)
- position: Position filter (optional)
- conditional_players: Players that trigger conditional logic (optional)
- conditional_logic: Relationship type (ANY, ALL, XOR, NAND, NOR, AT_LEAST_1, etc.)
"""

from typing import List, Dict, Optional, Any

# Player Groups Configuration
PLAYER_GROUPS = [
    # Example configurations (commented out by default)
    # {
    #     "group_name": "PHI_WR_Duo",
    #     "type": "Min",
    #     "min_players": 1,
    #     "max_players": 1,
    #     "players": ["A.J. Brown", "DeVonta Smith"],
    #     "team": "PHI",
    #     "position": "WR"
    # },
    # {
    #     "group_name": "KC_Team_Stack",
    #     "type": "Min",
    #     "min_players": 3,
    #     "max_players": 4,
    #     "players": ["Travis Kelce", "Isiah Pacheco", "Rashee Rice", "Marquez Valdes-Scantling"],
    #     "team": "KC",
    #     "conditional_players": ["Patrick Mahomes"],
    #     "conditional_logic": "ANY"
    # }
]


def get_player_groups() -> list:
    """Get all player group configurations."""
    return PLAYER_GROUPS.copy()


def get_group_by_name(group_name: str) -> Optional[Dict[str, Any]]:
    """Get a specific player group by name."""
    for group in PLAYER_GROUPS:
        if group["group_name"] == group_name:
            return group.copy()
    return None


def get_groups_by_team(team: str) -> list:
    """Get all player groups for a specific team."""
    return [group.copy() for group in PLAYER_GROUPS if group.get("team") == team]


def get_groups_by_position(position: str) -> list:
    """Get all player groups for a specific position."""
    return [group.copy() for group in PLAYER_GROUPS if group.get("position") == position]


def get_groups_by_type(group_type: str) -> list:
    """Get all player groups of a specific type."""
    return [group.copy() for group in PLAYER_GROUPS if group.get("type") == group_type]


def get_groups_with_conditionals() -> list:
    """Get all player groups that have conditional logic."""
    return [group.copy() for group in PLAYER_GROUPS if group.get("conditional_players")]


def validate_group(group_config: Dict[str, Any]) -> None:
    """Validate a player group configuration."""
    required_fields = ["group_name", "type"]
    for field in required_fields:
        if field not in group_config:
            raise ValueError(f"Missing required field: {field}")
    
    if group_config["type"] not in ["Min", "Max", "QB_RB_Restriction"]:
        raise ValueError(f"Invalid group type: {group_config['type']}")
    
    if group_config["type"] in ["Min", "Max"]:
        if "min_players" not in group_config and "max_players" not in group_config:
            raise ValueError(f"Min/Max groups must have min_players or max_players")
    
    if group_config["type"] == "QB_RB_Restriction":
        if "allowed_pairs" not in group_config:
            raise ValueError("QB_RB_Restriction groups must have allowed_pairs")


def validate_all_groups() -> Dict[str, Any]:
    """Validate all player group configurations."""
    results = {
        "valid_groups": [],
        "invalid_groups": {},
        "total_groups": len(PLAYER_GROUPS),
        "valid_count": 0,
        "invalid_count": 0
    }
    
    for group in PLAYER_GROUPS:
        try:
            validate_group(group)
            results["valid_groups"].append(group["group_name"])
            results["valid_count"] += 1
        except ValueError as e:
            results["invalid_groups"][group["group_name"]] = [str(e)]
            results["invalid_count"] += 1
    
    return results


def validate_group_against_players(group_config: Dict[str, Any], available_players: List) -> Dict[str, Any]:
    """Validate a player group configuration against the available player pool."""
    results = {
        "is_valid": True,
        "missing_players": [],
        "found_players": [],
        "warnings": [],
        "errors": []
    }
    
    # Get available player names
    available_names = {p.name.split(":")[-1].strip() for p in available_players}
    
    # Check players in the group
    if group_config.get('players'):
        for player_name in group_config['players']:
            if player_name in available_names:
                results["found_players"].append(player_name)
            else:
                results["missing_players"].append(player_name)
    
    # Check conditional players
    if group_config.get('conditional_players'):
        for player_name in group_config['conditional_players']:
            if player_name not in available_names:
                results["warnings"].append(f"Conditional player '{player_name}' not found in player pool")
    
    # Generate warnings and errors
    if results["missing_players"]:
        results["warnings"].append(f"Group '{group_config['group_name']}': Missing players: {results['missing_players']}")
        
        if len(results["found_players"]) == 0:
            results["errors"].append(f"Group '{group_config['group_name']}': All group players are missing from player pool")
            results["is_valid"] = False
    
    # Check min/max constraints
    if group_config["type"] in ["Min", "Max"]:
        if group_config["type"] == "Min" and "min_players" in group_config:
            if len(results["found_players"]) < group_config["min_players"]:
                results["errors"].append(f"Group '{group_config['group_name']}': Not enough available players ({len(results['found_players'])}) for min_players requirement ({group_config['min_players']})")
                results["is_valid"] = False
        
        elif group_config["type"] == "Max" and "max_players" in group_config:
            if len(results["found_players"]) > group_config["max_players"]:
                results["warnings"].append(f"Group '{group_config['group_name']}': More available players ({len(results['found_players'])}) than max_players limit ({group_config['max_players']})")
    
    return results


def validate_all_groups_against_players(available_players: List) -> Dict[str, Any]:
    """Validate all player group configurations against the player pool."""
    results = {
        "valid_groups": [],
        "invalid_groups": {},
        "warnings": {},
        "missing_players_summary": {},
        "total_groups": len(PLAYER_GROUPS),
        "valid_count": 0,
        "invalid_count": 0
    }
    
    for group in PLAYER_GROUPS:
        validation = validate_group_against_players(group, available_players)
        
        if validation["is_valid"]:
            results["valid_groups"].append(group["group_name"])
            results["valid_count"] += 1
        else:
            results["invalid_groups"][group["group_name"]] = validation["errors"]
            results["invalid_count"] += 1
        
        if validation["warnings"]:
            results["warnings"][group["group_name"]] = validation["warnings"]
        
        if validation["missing_players"]:
            results["missing_players_summary"][group["group_name"]] = validation["missing_players"]
    
    return results


def get_group_by_name_with_validation(group_name: str, available_players: List = None) -> Optional[Dict[str, Any]]:
    """Get a specific player group by name with optional validation."""
    group = get_group_by_name(group_name)
    
    if group and available_players is not None:
        validation = validate_group_against_players(group, available_players)
        if not validation["is_valid"]:
            print(f"Warning: Player group '{group_name}' has validation errors")
    
    return group


def print_group_config(group_name: Optional[str] = None) -> None:
    """Print player group configuration(s)."""
    if group_name:
        group = get_group_by_name(group_name)
        if group:
            print(f"\nPlayer Group Configuration for '{group_name}':")
            print(f"  Type: {group['type']}")
            if 'min_players' in group:
                print(f"  Min Players: {group['min_players']}")
            if 'max_players' in group:
                print(f"  Max Players: {group['max_players']}")
            if 'players' in group:
                print(f"  Players: {group['players']}")
            if 'team' in group:
                print(f"  Team: {group['team']}")
            if 'position' in group:
                print(f"  Position: {group['position']}")
            if 'conditional_players' in group:
                print(f"  Conditional Players: {group['conditional_players']}")
            if 'conditional_logic' in group:
                print(f"  Conditional Logic: {group['conditional_logic']}")
        else:
            print(f"No configuration found for group: {group_name}")
    else:
        print("\nAll Player Group Configurations:")
        for group in PLAYER_GROUPS:
            print(f"\n{group['group_name']}:")
            print(f"  Type: {group['type']}")
            if 'min_players' in group:
                print(f"  Min Players: {group['min_players']}")
            if 'max_players' in group:
                print(f"  Max Players: {group['max_players']}")
            if 'players' in group:
                print(f"  Players: {group['players']}")
            if 'team' in group:
                print(f"  Team: {group['team']}")
            if 'position' in group:
                print(f"  Position: {group['position']}")


if __name__ == "__main__":
    # Test the configuration
    print("Testing Player Group Configuration...")
    print_group_config()
    
    # Validate configurations
    validation_results = validate_all_groups()
    print(f"\nValidation Results:")
    for group_name, errors in validation_results.get("invalid_groups", {}).items():
        print(f"  {group_name}: {errors}")
    
    print(f"Valid groups: {validation_results['valid_count']}/{validation_results['total_groups']}") 