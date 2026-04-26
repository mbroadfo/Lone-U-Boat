"""
Mission 3 Configuration
Mission-specific settings including hex layout, starting positions, objectives.

Mission 3: Special Operation: Agent Transport to Scarpa Flow, North Scotland
One destroyer and two corvettes patrol while the U-Boat delivers a German agent.
There is no merchant ship in this mission.

IMPORTANT: U-Boat must start at MEDIUM depth (mission rule).

Terrain hexes captured via the in-game F3 Terrain Edit mode.
TODO: confirm AGENT_DROP_HEX (red X) and DESTROYER start position in-game.
"""

from typing import Any


# ====================
# MISSION METADATA
# ====================

MISSION_INFO: dict[str, Any] = {
    'number': 3,
    'name': 'Special Operation: Agent Transport to Scarpa Flow, North Scotland',
    'description': 'Deliver an agent to Scarpa Flow — surface at the X hex at end of U-Boat Phase, then escape.',
    'map_image': 'assets/maps/mission_3.png',
}


# ====================
# HEX LAYOUT
# ====================

VALID_HEXES = None  # Use board_config.VALID_HEXES


# ====================
# TERRAIN LAYOUT
# ====================

# Shallow water hexes (U-Boat cannot dive below Periscope depth here)
SHALLOW_HEXES: list[tuple[int, int]] = [
    (1, 5),
    (1, 6),
    (2, 4),
    (2, 5),
    (3, 3),
    (3, 4),
    (3, 9),
    (4, 1),
    (4, 2),
    (4, 3),
    (4, 8),
    (4, 9),
    (5, 8),
    (5, 9),
    (7, 3),
    (7, 4),
    (8, 3),
    (8, 4),
    (9, 3),
    (9, 4),
]

# Land hexes (impassable for all units)
LAND_HEXES: list[tuple[int, int]] = [
    (1, 4),
    (2, 3),
    (3, 2),
    (8, 0),
    (8, 1),
    (8, 2),
    (9, 0),
    (9, 1),
    (9, 2),
]


# ====================
# STARTING POSITIONS
# ====================

# U-Boat starting position — must begin at MEDIUM depth (mission rule)
U_BOAT_START: dict[str, Any] = {
    'position': (9, 5),
    'facing': 'NORTHWEST',
    'depth': 'MEDIUM',
}

# Allied ships — no merchant in this mission
SHIPS_START: list[dict[str, Any]] = [
    {
        'type': 'destroyer',
        'position': (6, 0),
        'facing': 'SOUTH',
        'damaged': False,
    },
    {
        'type': 'corvette',
        'position': (7, 0),
        'facing': 'SOUTH',
        'damaged': False,
    },
    {
        'type': 'corvette',
        'position': (1, 9),
        'facing': 'NORTHEAST',
        'damaged': False,
    },
]


# ====================
# MERCHANT PATHS
# ====================

MERCHANT_PATHS: list[dict[str, Any]] = []  # No merchant in this mission


# ====================
# MISSION OBJECTIVES
# ====================

# Agent drop hex — U-Boat must be SURFACED here at the END of the U-Boat Phase
AGENT_DROP_HEX: tuple[int, int] = (2, 4)
AGENT_DROP_FACING = None                      # No required facing to drop the agent

# Anchor position — where escorts orbit/patrol when DL is low
ANCHOR_POSITIONS: list[tuple[int, int]] = [
    (5, 6),
]

# U-Boat exit hex and facing (direction of the red arrow on the map)
U_BOAT_EXIT_HEX: tuple[int, int] = (6, 9)
U_BOAT_EXIT_FACING = 'SOUTH'

EXIT_POSITIONS: dict[str, dict[str, Any]] = {
    'u_boat': {
        'position': (6, 9),
        'facing': 'SOUTH',
    },
    # No merchant exit in this mission
}

# Victory conditions
VICTORY_CONDITIONS: dict[str, str | None] = {
    'primary': 'Surface at the X hex at end of your U-Boat Phase to drop the agent',
    'secondary': 'Exit the mission area in the direction of the red arrow',
    'bonus': None,
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
    'has_air_support': True,      # B24 Liberators are active in this mission
    'has_merchant': False,
    'starting_depth': 'MEDIUM',   # Mission rule: U-Boat must start at Medium depth
    'agent_drop_required': True,  # Must surface at AGENT_DROP_HEX before exiting
}
