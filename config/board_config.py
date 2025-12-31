"""
Board Configuration
Contains all game board settings that are constant across all missions.
"""

import pygame

# ====================
# SCREEN CONFIGURATION
# ====================

SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 900


# ====================
# COLOR PALETTE
# ====================

COLORS = {
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

HEX_GRID = {
    'size': 32,         # Radius of hexagon
    'cols': 11,         # Maximum columns (0-10)
    'rows': 12,         # Rows 0-11
    'offset_x': 457,    # Horizontal offset to align with map
    'offset_y': -15,    # Vertical offset to align with map
}


# ====================
# HEX LAYOUT (Common across all missions)
# ====================

# Valid hex coordinates - 74 total hexes (axial coordinates)
# Pattern: 5,6,7,8,9,9,9,8,7,6 hexes per row
# Format: (q, r) where q=column, r=row
VALID_HEXES = [
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

# Status box positions and their marker types
# Each entry: 'name': {'rect': (x, y, width, height), 'marker': 'type', 'condition': 'condition_key'}
STATUS_BOXES = {
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

ASSETS = {
    'detection_marker': 'assets/Detection.png',
    'damaged_marker': 'assets/Damaged.png',
    'torpedo_marker': 'assets/Torpedo.png',
    'u_boat_surfaced': 'assets/UB-Surfaced.png',
    'u_boat_periscope': 'assets/UB-Periscope.png',
    'u_boat_medium': 'assets/UB-Medium.png',
    'u_boat_deep': 'assets/UB-Deep.png',
}


# ====================
# UI CONFIGURATION
# ====================

UI = {
    'top_bar_height': 40,
    'map_offset_y': 50,
    'status_panel_x': SCREEN_WIDTH - 250,
    'status_panel_y': 50,
    'font_size': 24,
    'font_size_large': 36,
    'u_boat_image_size': 50,  # Target size for U-boat images in hex
}
