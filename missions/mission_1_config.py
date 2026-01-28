"""
Mission 1 Configuration
Mission-specific settings including hex layout, starting positions, objectives.
"""

from typing import Any


# ====================
# MISSION METADATA
# ====================

MISSION_INFO: dict[str, Any] = {
    'number': 1,
    'name': 'Supply Ship Attack',
    'description': 'Intercept and sink the supply convoy',
    'map_image': 'assets/maps/mission_1.png',
}


# ====================
# HEX LAYOUT
# ====================

# Valid hexes are defined in board_config.VALID_HEXES (common across all missions)
# Mission-specific hex modifications can be added here if needed
VALID_HEXES = None  # Use board_config.VALID_HEXES


# ====================
# TERRAIN LAYOUT
# ====================

# Shallow water hexes (ships cannot enter these)
# All hexes not listed here or in LAND_HEXES are considered DEEP water
SHALLOW_HEXES = [
    (1, 8), (2, 8), (3, 8), (4, 8), (4, 9),
    (9, 1), (8, 2), (8, 3), (8, 4), (8, 5), (9, 5),
]

# Land hexes (impassable)
LAND_HEXES = [
    (4, 3), (5, 4),
    (1, 9), (2, 9), (3, 9),
    (9, 2), (9, 3), (9, 4),
]


# ====================
# STARTING POSITIONS
# ====================

# U-Boat starting position
U_BOAT_START: dict[str, Any] = {
    'position': (9, 0),  # Top right hex
    'facing': 'SOUTH',   # Initial facing direction (player can change at game start)
    'depth': 'SURFACED', # Initial starting depth (player can change at game start)
}

# Allied ships starting positions
SHIPS_START: list[dict[str, Any]] = [
    {
        'type': 'merchant',
        'position': (1, 4),
        'facing': 'SOUTH',  # Facing from (1,4) toward (1,5)
        'damaged': False
    },
    {
        'type': 'corvette',
        'position': (2, 3),
        'facing': 'SOUTH',  # Facing from (2,3) toward (2,4)
        'damaged': False
    },
]


# ====================
# MERCHANT PATHS
# ====================

# Predefined paths for merchant ships (waypoints they follow)
MERCHANT_PATHS: list[dict[str, Any]] = [
    {
        'ship_index': 0,  # First merchant in SHIPS_START
        'waypoints': [
            (1, 4),  # Start
            (1, 5),
            (1, 6),
            (1, 7),
            (2, 7),  # Turn east
            (3, 7),
            (4, 7),
            (5, 7),
            (6, 7),
            (6, 8),  # Turn south
            (6, 9),
            (6, 10), # Exit
        ],
        'exit_hex': (6, 10),
    },
]


# ====================
# MISSION OBJECTIVES
# ====================

# Anchor positions (if mission involves anchoring)
ANCHOR_POSITIONS = [
    (6, 6),  # Central anchor position
]

# Exit positions (hexes where units can exit mission)
# U-boat exit: Must be ON this hex, facing this direction, with AP > 0, all merchants sunk
U_BOAT_EXIT_HEX = (1, 7)
U_BOAT_EXIT_FACING = 'SOUTHWEST'  # Must be facing toward (0,8) to exit

EXIT_POSITIONS: dict[str, dict[str, Any]] = {
    'u_boat': {
        'position': (1, 7),
        'facing': 'SOUTHWEST',  # Facing toward (0,8) - exit after sinking merchant(s)
    },
    'merchant': {
        'position': (6, 9),
        'facing': 'SOUTH',  # Facing toward (6,10) - merchant escape route
    },
}

# Victory conditions
VICTORY_CONDITIONS = {
    'primary': 'Sink at least one supply ship',
    'secondary': 'Exit the mission area undetected',
    'bonus': 'Sink all enemy vessels',
}

# Mission time limit (turns, if applicable)
TIME_LIMIT = None  # None for unlimited time


# ====================
# ENEMY PATROLS
# ====================

# Enemy patrol routes (for destroyers/corvettes)
PATROL_ROUTES = [
    # TODO: Add patrol routes when AI system is implemented
    # Format: {'ship_id': 0, 'waypoints': [(q1, r1), (q2, r2), ...]}
]


# ====================
# SPECIAL RULES
# ====================

# Mission-specific rules or modifiers
SPECIAL_RULES: dict[str, Any] = {
    'detection_modifier': 0,     # Modifier to detection rolls
    'weather': 'clear',          # Weather conditions (clear, fog, storm)
    'time_of_day': 'day',        # day/night affects visibility
    'has_air_support': False,    # Are there enemy aircraft?
}
