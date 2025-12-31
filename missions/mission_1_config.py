"""
Mission 1 Configuration
Mission-specific settings including hex layout, starting positions, objectives.
"""

from dataclasses import dataclass
from typing import Set, List, Tuple


# ====================
# MISSION METADATA
# ====================

MISSION_INFO = {
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
    # TODO: Add shallow water hex coordinates when terrain system is implemented
]

# Land hexes (impassable)
LAND_HEXES = [
    # TODO: Add land hex coordinates when terrain system is implemented
]


# ====================
# STARTING POSITIONS
# ====================

# U-Boat starting position
U_BOAT_START = {
    'position': (9, 0),  # Top right hex
    'facing': 'NORTH',   # Facing direction (NORTH, NORTHEAST, SOUTHEAST, SOUTH, SOUTHWEST, NORTHWEST)
    'depth': 'SURFACED', # Starting depth (SURFACED, PERISCOPE, MEDIUM, DEEP)
}

# Allied ships starting positions
SHIPS_START = [
    # TODO: Add ship configurations when ship system is implemented
    # Format: {'type': 'merchant', 'position': (q, r), 'facing': 'SOUTH', 'damaged': False}
]


# ====================
# MISSION OBJECTIVES
# ====================

# Anchor positions (if mission involves anchoring)
ANCHOR_POSITIONS = [
    # TODO: Add anchor hex coordinates when anchor system is implemented
]

# Exit positions (hexes where U-Boat can exit mission)
EXIT_POSITIONS = [
    # TODO: Add exit hex coordinates when exit system is implemented
    # Likely along the edges of the map
]

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
SPECIAL_RULES = {
    'detection_modifier': 0,     # Modifier to detection rolls
    'weather': 'clear',          # Weather conditions (clear, fog, storm)
    'time_of_day': 'day',        # day/night affects visibility
    'has_air_support': False,    # Are there enemy aircraft?
}
