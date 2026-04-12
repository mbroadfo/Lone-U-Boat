"""
Mission 2 Configuration
Mission-specific settings including hex layout, starting positions, objectives.

Mission 2: Supply Ship Attack: North East of Scotland
Two corvettes escort a merchant ship. Different terrain and starting positions
compared to Mission 1.

Hex coordinates captured via the in-game F3 Terrain Edit mode on 2026-03-14.
"""

from typing import Any


# ====================
# MISSION METADATA
# ====================

MISSION_INFO: dict[str, Any] = {
    'number': 2,
    'name': 'Supply Ship Attack: North East of Scotland',
    'description': 'Intercept and sink the supply convoy before it escapes',
    'map_image': 'assets/maps/mission_2.png',
}


# ====================
# HEX LAYOUT
# ====================

# Valid hexes are defined in board_config.VALID_HEXES (common across all missions)
VALID_HEXES = None  # Use board_config.VALID_HEXES


# ====================
# TERRAIN LAYOUT
# ====================

# Shallow water hexes (U-Boat cannot dive below Periscope depth here)
SHALLOW_HEXES = [
    (1, 7),
    (2, 7),
    (2, 8),
    (3, 8),
    (4, 8),
    (4, 9),
    (5, 8),
    (5, 9),
]

# Land hexes (impassable for all units)
LAND_HEXES = [
    (1, 8),
    (1, 9),
    (2, 9),
    (3, 9),
]


# ====================
# STARTING POSITIONS
# ====================

# U-Boat starting position
U_BOAT_START: dict[str, Any] = {
    'position': (9, 4),
    'facing': 'NORTHWEST',
    'depth': 'SURFACED',  # Initial starting depth (player can change at game start)
}

# Allied ships starting positions
# Mission 2 has TWO corvettes (vs one in Mission 1)
SHIPS_START: list[dict[str, Any]] = [
    {
        'type': 'merchant',
        'position': (1, 4),
        'facing': 'SOUTHEAST',
        'damaged': False
    },
    {
        'type': 'corvette',
        'position': (3, 2),
        'facing': 'SOUTHEAST',
        'damaged': False
    },
    {
        'type': 'corvette',
        'position': (1, 5),
        'facing': 'SOUTHEAST',
        'damaged': False
    },
]


# ====================
# MERCHANT PATHS
# ====================

MERCHANT_PATHS: list[dict[str, Any]] = [
    {
        'ship_index': 0,  # First (and only) merchant in SHIPS_START
        'waypoints': [
            (2, 4),
            (3, 4),
            (4, 4),
            (4, 5),
            (5, 5),
            (6, 5),
            (7, 5),
            (7, 6),
            (8, 6),
            (9, 6),
        ],
        'exit_hex': (9, 6),
    },
]


# ====================
# MISSION OBJECTIVES
# ====================

# Anchor position — where corvettes orbit/patrol when DL is low
ANCHOR_POSITIONS = [
    (6, 6),
]

# U-Boat exit hex and required facing (direction of the exit arrow on the map)
U_BOAT_EXIT_HEX = (6, 9)
U_BOAT_EXIT_FACING = 'SOUTH'

EXIT_POSITIONS: dict[str, dict[str, Any]] = {
    'u_boat': {
        'position': (6, 9),
        'facing': 'SOUTH',
    },
    'merchant': {
        'position': (9, 6),
        'facing': 'SOUTHEAST',
    },
}

# Victory conditions
VICTORY_CONDITIONS = {
    'primary': 'Sink at least one supply ship',
    'secondary': 'Exit the mission area in the direction of the red arrow',
    'bonus': 'Sink all enemy vessels',
}

# Mission time limit (turns, if applicable)
TIME_LIMIT = None  # None for unlimited time


# ====================
# ENEMY PATROLS
# ====================

PATROL_ROUTES = [
    # TODO: Add patrol routes when AI system is implemented
]


# ====================
# SPECIAL RULES
# ====================

SPECIAL_RULES: dict[str, Any] = {
    'detection_modifier': 0,
    'weather': 'clear',
    'time_of_day': 'day',
    'has_air_support': False,
}
