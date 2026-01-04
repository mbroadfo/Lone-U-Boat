"""
Board Configuration
Contains all game board settings that are constant across all missions.

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
CRITICAL: DO NOT TOUCH CALIBRATION CONSTANTS
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

The following values are FROZEN CALIBRATION CONSTANTS that were hand-tuned to
align the hex grid and status box markers perfectly with the mission map image:

- CALIBRATION_MAP_POSITION (board_x, board_y, board_width)
- GLOBAL_BOARD_OFFSET (offset_x, offset_y)
- HEX_GRID['offset_x'] and HEX_GRID['offset_y']
- All STATUS_BOXES rect values

These values must NOT be derived from or updated based on:
- LEFT_PANEL_WIDTH
- RIGHT_PANEL_WIDTH
- GAME_BOARD_WIDTH
- Any other layout variables

They represent "where the map was positioned when we calibrated the overlays",
and the rendering code uses them to compute adjustment offsets.

When changing UI layout:
✅ You MAY adjust: LEFT_PANEL_WIDTH, RIGHT_PANEL_WIDTH, font sizes, spacing
✅ You MAY modify: left panel rendering logic in UnifiedGame._draw_left_panel
❌ You MUST NOT change: Any calibration constants listed above

Only change calibration values during an explicit "re-calibration session" with
visual verification and user approval.
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
"""

from typing import TypedDict


# ====================
# TYPE DEFINITIONS
# ====================

class StatusBoxConfig(TypedDict):
    """Type definition for status box configuration."""
    rect: tuple[int, int, int, int]
    marker: str
    condition: str


class HexGridConfig(TypedDict):
    """Type definition for hex grid configuration."""
    size: int
    cols: int
    rows: int
    offset_x: int
    offset_y: int


class UIConfig(TypedDict):
    """Type definition for UI configuration."""
    top_bar_height: int
    map_offset_y: int
    status_panel_x: int
    status_panel_y: int
    font_size: int
    font_size_large: int
    u_boat_image_size: int


# ====================
# SCREEN CONFIGURATION
# ====================

# Base window size (windowed mode)
SCREEN_WIDTH = 1600
SCREEN_HEIGHT = 900

# Panel layout for unified game screen
LEFT_PANEL_WIDTH = 750      # Mission rules panel (rulebook-style)
RIGHT_PANEL_WIDTH = 250      # Event log/commentary
BOTTOM_PANEL_HEIGHT = 0      # No bottom panel (controls moved to right panel)
TOP_BAR_HEIGHT = 40         # Title and game info

# Calculated game board area
GAME_BOARD_WIDTH = SCREEN_WIDTH - LEFT_PANEL_WIDTH - RIGHT_PANEL_WIDTH
GAME_BOARD_HEIGHT = SCREEN_HEIGHT - TOP_BAR_HEIGHT - BOTTOM_PANEL_HEIGHT


# ====================
# COLOR PALETTE
# ====================

COLORS: dict[str, tuple[int, int, int] | tuple[int, int, int, int]] = {
    'hex_grid': (100, 100, 100, 128),       # Semi-transparent gray
    'hex_highlight': (255, 255, 0, 200),    # Yellow highlight
    'ship': (0, 0, 255),                    # Blue - for rendering enemy ships
    'selection': (0, 255, 0, 150),          # Green selection
    'valid_move': (0, 255, 0, 100),         # Green for valid moves
    'panel_bg': (40, 40, 40),               # Dark gray
    'text': (255, 255, 255),                # White
    'background': (20, 20, 30),             # Dark blue-gray
}


# ====================
# HEX GRID CONFIGURATION
# ====================

# These offsets were calibrated at 1600x900 window size with unified game layout
# where the map is positioned at (LEFT_PANEL_WIDTH + map_x_offset, TOP_BAR_HEIGHT)
# For the map to stay aligned at different window sizes, we need to store:
# - The base map position used during calibration
# - The hex grid offset relative to that map position

# Legacy calibration constants - DEPRECATED
# These are no longer used. All calibration is now stored in mission_X_layout.json
# and handled by the BoardLayoutRuntime engine.

HEX_GRID: HexGridConfig = {
    'size': 32,         # Radius of hexagon
    'cols': 11,         # Maximum columns (0-10)
    'rows': 12,         # Rows 0-11
    'offset_x': 733,      # Horizontal offset from calibration board position
    'offset_y': -33,      # Vertical offset from calibration board position
}


# ====================
# HEX LAYOUT (Common across all missions)
# ====================

# Valid hex coordinates - 74 total hexes (axial coordinates)
# Pattern: 5,6,7,8,9,9,9,8,7,6 hexes per row
# Format: (q, r) where q=column, r=row
VALID_HEXES: list[tuple[int, int]] = [
    # Row 0 - 5 hexes
    (5, 0), (6, 0), (7, 0), (8, 0), (9, 0),
    # Row 1 - 6 hexes
    (4, 1), (5, 1), (6, 1), (7, 1), (8, 1), (9, 1),
    # Row 2 - 7 hexes
    (3, 2), (4, 2), (5, 2), (6, 2), (7, 2), (8, 2), (9, 2),
    # Row 3 - 8 hexes
    (2, 3), (3, 3), (4, 3), (5, 3), (6, 3), (7, 3), (8, 3), (9, 3),
    # Row 4 - 9 hexes (widest)
    (1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4), (7, 4), (8, 4), (9, 4),
    # Row 5 - 9 hexes
    (1, 5), (2, 5), (3, 5), (4, 5), (5, 5), (6, 5), (7, 5), (8, 5), (9, 5),
    # Row 6 - 9 hexes
    (1, 6), (2, 6), (3, 6), (4, 6), (5, 6), (6, 6), (7, 6), (8, 6), (9, 6),
    # Row 7 - 8 hexes
    (1, 7), (2, 7), (3, 7), (4, 7), (5, 7), (6, 7), (7, 7), (8, 7),
    # Row 8 - 7 hexes
    (1, 8), (2, 8), (3, 8), (4, 8), (5, 8), (6, 8), (7, 8),
    # Row 9 - 6 hexes
    (1, 9), (2, 9), (3, 9), (4, 9), (5, 9), (6, 9),
]


# ====================
# STATUS BOX MARKERS
# ====================

# Status box marker types and conditions.
# NOTE: The 'rect' field is DEPRECATED - positions now come from missions/mission_X_layout.json
# The rects below are kept only for reference and are NOT used for positioning.
# Each entry: 'name': {'rect': (DEPRECATED), 'marker': 'type', 'condition': 'condition_key'}
STATUS_BOXES: dict[str, StatusBoxConfig] = {
    # Detection Levels
    'detection_silent': {
        'rect': (475, 89, 29, 29),
        'marker': 'detection',
        'condition': 'detection_level_0'
    },
    'detection_aware': {
        'rect': (509, 90, 29, 28),
        'marker': 'detection',
        'condition': 'detection_level_1'
    },
    'detection_traced': {
        'rect': (544, 90, 29, 26),
        'marker': 'detection',
        'condition': 'detection_level_2'
    },
    'detection_locked': {
        'rect': (578, 89, 28, 26),
        'marker': 'detection',
        'condition': 'detection_level_3'
    },
    
    # Hull Damage
    'hull_damage_1': {
        'rect': (475, 132, 29, 25),
        'marker': 'damaged',
        'condition': 'hull_damage_1'
    },
    'hull_damage_2': {
        'rect': (509, 133, 29, 25),
        'marker': 'damaged',
        'condition': 'hull_damage_2'
    },
    'hull_damage_3': {
        'rect': (544, 133, 28, 23),
        'marker': 'damaged',
        'condition': 'hull_damage_3'
    },
    
    # Torpedo Tubes
    'torpedo_tube_1': {
        'rect': (781, 112, 28, 28),
        'marker': 'torpedo',
        'condition': 'torpedo_tube_0'
    },
    'torpedo_tube_2': {
        'rect': (817, 114, 28, 27),
        'marker': 'torpedo',
        'condition': 'torpedo_tube_1'
    },
    'torpedo_tube_3': {
        'rect': (852, 114, 26, 26),
        'marker': 'torpedo',
        'condition': 'torpedo_tube_2'
    },
    'torpedo_tube_4': {
        'rect': (885, 113, 26, 27),
        'marker': 'torpedo',
        'condition': 'torpedo_tube_3'
    },
    'torpedo_tube_5': {
        'rect': (886, 166, 27, 25),
        'marker': 'torpedo',
        'condition': 'torpedo_tube_4'
    },
    
    # Crew
    'captain_damaged': {
        'rect': (515, 576, 27, 25),
        'marker': 'damaged',
        'condition': 'captain_dead'
    },
    'sonar_operator_damaged': {
        'rect': (514, 615, 29, 26),
        'marker': 'damaged',
        'condition': 'sonar_operator_dead'
    },
    'engineer_damaged': {
        'rect': (515, 655, 27, 26),
        'marker': 'damaged',
        'condition': 'engineer_dead'
    },
    'weapons_officer_damaged': {
        'rect': (592, 614, 30, 27),
        'marker': 'damaged',
        'condition': 'weapons_officer_dead'
    },
    'lookout_damaged': {
        'rect': (594, 656, 26, 24),
        'marker': 'damaged',
        'condition': 'lookout_dead'
    },
    'medic_damaged': {
        'rect': (662, 655, 27, 28),
        'marker': 'damaged',
        'condition': 'medic_dead'
    },
    
    # Equipment
    'engine_damaged': {
        'rect': (782, 657, 27, 27),
        'marker': 'damaged',
        'condition': 'engine_damaged'
    },
    'flak_gun_damaged': {
        'rect': (886, 622, 29, 26),
        'marker': 'damaged',
        'condition': 'flak_gun_damaged'
    },
    'deck_gun_damaged': {
        'rect': (886, 655, 29, 27),
        'marker': 'damaged',
        'condition': 'deck_gun_damaged'
    },
}


# ====================
# ASSET PATHS
# ====================

ASSETS: dict[str, str] = {
    'detection_marker': 'assets/Detection.png',
    'damaged_marker': 'assets/Damaged.png',
    'torpedo_marker': 'assets/Torpedo.png',
    'u_boat_surfaced': 'assets/UB-Surfaced.png',
    'u_boat_periscope': 'assets/UB-Periscope.png',
    'u_boat_medium': 'assets/UB-Medium.png',
    'u_boat_deep': 'assets/UB-Deep.png',
    'merchant': 'assets/Merchant.png',
    'merchant_damaged': 'assets/Merchant-Damaged.png',
    'corvette': 'assets/Corvette.png',
    'corvette_damaged': 'assets/Corvette-Damaged.png',
    'destroyer': 'assets/Destroyer.png',
    'destroyer_damaged': 'assets/Destroyer-Damaged.png',
}


# ====================
# UI CONFIGURATION
# ====================

UI: UIConfig = {
    'top_bar_height': 40,
    'map_offset_y': 50,
    'status_panel_x': SCREEN_WIDTH - 250,
    'status_panel_y': 50,
    'font_size': 24,
    'font_size_large': 36,
    'u_boat_image_size': 50,  # Target size for U-boat images in hex
}
