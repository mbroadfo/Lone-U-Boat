"""
⚠️ LEGACY EDITOR - DEPRECATED ⚠️

This editor is deprecated. Use the in-game alignment mode instead (F2 key).

The in-game alignment mode provides the same functionality with better
integration and live preview. This file is kept for reference only.

To use alignment mode:
1. Run main.py
2. Start a mission
3. Press F2 to toggle alignment mode
4. Use arrow keys to adjust positions
5. Press P to print calibration, L to save

================================================================================

Board Editor and Alignment Tool for Lone U-Boat
Separate utility for aligning hex grids, detecting status box coordinates,
and testing mission configurations.
"""

import pygame
from typing import Optional, List, Dict, Any
import importlib
import argparse
import sys
import os

# Import board and mission configurations
from config import board_config as cfg

# Import core game models
from core.models import HexCoord, Facing, Depth, UBoat, Ship
from core.hex_grid import HexGrid
from core.assets import AssetManager
from core.conditions import ConditionFactory
from core.renderer import GameRenderer


class BoardEditor:
    """Board alignment and mission configuration tool."""
    
    def __init__(self, mission_number: int = 1, edit_mode: bool = False):
        pygame.init()
        # Create window with RESIZABLE flag (allows maximize button)
        self.screen = pygame.display.set_mode(
            (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT),
            pygame.RESIZABLE
        )
        self.is_fullscreen = False
        
        # Maximize window on Windows
        if sys.platform == 'win32':
            import ctypes
            import ctypes.wintypes
            hwnd = pygame.display.get_wm_info()['window']
            SW_MAXIMIZE = 3
            ctypes.windll.user32.ShowWindow(hwnd, SW_MAXIMIZE)
        
        # Edit mode controls whether map-altering features are enabled
        self.edit_mode = edit_mode
        
        # Load mission configuration
        self.mission_number = mission_number
        self.mission_config = self._load_mission_config(mission_number)
        
        pygame.display.set_caption(f"Lone U-Boat - EDITOR - {self.mission_config.MISSION_INFO['name']}")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Load mission map
        # Load map at a size that gives reasonable scale factor
        # Target: scale ~1.0 to 1.5 for comfortable editing
        # Since board_height will be ~900-1000, load map at ~900 height
        self.map_image = AssetManager.load_mission_map(
            self.mission_config.MISSION_INFO['map_image'],
            max_width=1200,
            max_height=900
        )
        
        # Convert mission hex coordinates to HexCoord objects
        valid_hexes = self.mission_config.VALID_HEXES if self.mission_config.VALID_HEXES else cfg.VALID_HEXES
        self.mission_hexes = {HexCoord(q, r) for q, r in valid_hexes}
        
        # Load terrain data from mission config
        self.shallow_hexes = {HexCoord(q, r) for q, r in self.mission_config.SHALLOW_HEXES}
        self.land_hexes = {HexCoord(q, r) for q, r in self.mission_config.LAND_HEXES}
        
        # Create hex grid overlay
        self.hex_grid = HexGrid(
            size=cfg.HEX_GRID['size'],
            cols=cfg.HEX_GRID['cols'],
            rows=cfg.HEX_GRID['rows'],
            offset_x=cfg.HEX_GRID['offset_x'],
            offset_y=cfg.HEX_GRID['offset_y'],
            global_offset_x=cfg.GLOBAL_BOARD_OFFSET['offset_x'],
            global_offset_y=cfg.GLOBAL_BOARD_OFFSET['offset_y']
        )
        
        # Game entities - load from mission config
        u_boat_start = self.mission_config.U_BOAT_START
        self.u_boat = UBoat(
            position=HexCoord(*u_boat_start['position']),
            facing=Facing[u_boat_start['facing']]
        )
        
        # Load ships from mission config
        self.ships: List[Ship] = []
        for ship_data in self.mission_config.SHIPS_START:
            ship = Ship(
                position=HexCoord(*ship_data['position']),
                facing=Facing[ship_data['facing']],
                ship_type=ship_data['type'],
                damaged=ship_data['damaged']
            )
            self.ships.append(ship)
        
        # Editor-specific UI state
        self.selected_hex: Optional[HexCoord] = None
        self.show_grid = True
        self.show_map = True
        self.show_terrain = True  # Editor defaults to showing terrain
        self.detection_level = 0
        
        # Grid alignment mode (only active in edit mode)
        self.alignment_mode = edit_mode
        self.dragging_grid = False
        self.drag_start = None
        self.grid_offset_start = None
        
        # Coordinate detection mode (for status boxes)
        self.coord_detect_dragging = False
        self.coord_detect_start = None
        
        # Status box markers
        self.status_boxes: Dict[str, Dict[str, Any]] = {}
        asset_manager = AssetManager(cfg)
        self.marker_images = asset_manager.load_marker_images()
        self._setup_status_boxes()
        self.show_all_markers = True  # Editor defaults to showing all markers
        
        # Fonts
        self.font, self.font_large = asset_manager.load_fonts()
        
        # Load images
        self.u_boat_images = asset_manager.load_u_boat_images()
        self.ship_images = asset_manager.load_ship_images()
        
        # Create renderer
        assets: Dict[str, Any] = {
            'u_boat_images': self.u_boat_images,
            'ship_images': self.ship_images,
            'marker_images': self.marker_images,
            'font': self.font,
            'font_large': self.font_large
        }
        self.renderer = GameRenderer(self.screen, cfg, self.hex_grid, assets)
        
        # Calculate uniform scale factor (same as game)
        # Game board height = SCREEN_HEIGHT - TOP_BAR_HEIGHT (no bottom panel)
        board_height = cfg.SCREEN_HEIGHT - cfg.TOP_BAR_HEIGHT
        original_map_width = self.map_image.get_width()
        original_map_height = self.map_image.get_height()
        self.scale = board_height / original_map_height
        
        print(f"\n=== Map Image Info ===")
        print(f"Loaded map dimensions: {original_map_width}x{original_map_height}")
        print(f"Expected (trimmed): 2204x2924")
        print(f"======================\n")
        
        # Store original values for scaling
        self.original_hex_size = self.hex_grid.size
        self.original_hex_offset_x = self.hex_grid.offset_x
        self.original_hex_offset_y = self.hex_grid.offset_y
        self.original_global_offset_x = self.hex_grid.global_offset_x
        self.original_global_offset_y = self.hex_grid.global_offset_y
        
        # User adjustments (separate for hex grid and status boxes)
        self.user_hex_adjustment_x = 0
        self.user_hex_adjustment_y = 0
        self.user_status_adjustment_x = 0
        self.user_status_adjustment_y = 0
        
        # Scale multipliers (separate for hex grid and status boxes)
        self.hex_scale_multiplier = cfg.HEX_SCALE_MULTIPLIER
        self.status_box_scale_multiplier = cfg.STATUS_BOX_SCALE_MULTIPLIER
        
        # Which adjustment mode (True = hex grid, False = status boxes)
        self.adjusting_hex_grid = True
    
    def _load_mission_config(self, mission_number: int):
        """Dynamically load mission configuration module."""
        try:
            mission_module = importlib.import_module(f'missions.mission_{mission_number}_config')
            return mission_module
        except ImportError:
            raise ValueError(f"Mission {mission_number} configuration not found")
    
    def _setup_status_boxes(self):
        """Configure status box positions and marker types from config."""
        for box_name, box_data in cfg.STATUS_BOXES.items():
            rect_tuple = box_data['rect']
            marker_type = box_data['marker']
            condition_key = box_data['condition']
            
            # Create condition using factory
            condition = ConditionFactory.create_condition_with_getter(
                condition_key,
                lambda: self.u_boat,
                lambda: self.detection_level
            )
            
            self.status_boxes[box_name] = {
                'rect': pygame.Rect(*rect_tuple),
                'marker_type': marker_type,
                'condition': condition
            }
    
    def handle_events(self):
        """Handle pygame events - editor version with all debug features."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                
                # F11: Toggle fullscreen
                elif event.key == pygame.K_F11:
                    self.is_fullscreen = not self.is_fullscreen
                    if self.is_fullscreen:
                        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                    else:
                        self.screen = pygame.display.set_mode(
                            (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT),
                            pygame.RESIZABLE
                        )
                    # Update renderer reference to new screen
                    self.renderer.screen = self.screen
                
                # Editor-specific toggles
                elif event.key == pygame.K_s:
                    # Toggle show all markers mode
                    self.show_all_markers = not self.show_all_markers
                    print(f"Status markers: {'ON' if self.show_all_markers else 'OFF'}")
                    if self.show_all_markers:
                        # Print Silent DL box location
                        silent_box = self.status_boxes.get('silent')
                        if silent_box:
                            rect = silent_box['rect']
                            adj_x = rect.x + self.renderer.global_offset_x
                            adj_y = rect.y + self.renderer.global_offset_y
                            print(f"  -> Silent DL box at screen position: ({adj_x}, {adj_y})")
                elif event.key == pygame.K_t:
                    # Toggle torpedo loading (for testing markers)
                    all_loaded = all(self.u_boat.torpedo_tubes)
                    new_state = not all_loaded
                    self.u_boat.torpedo_tubes = [new_state] * 5
                    print(f"Torpedoes: {'LOADED' if new_state else 'EMPTY'}")
                elif event.key == pygame.K_g:
                    self.show_grid = not self.show_grid
                    print(f"Hex grid: {'ON' if self.show_grid else 'OFF'}")
                    if self.show_grid:
                        # Print hex 5,5 location
                        from core.models import HexCoord
                        hex_55 = HexCoord(5, 5)
                        x, y = self.hex_grid.hex_to_pixel(hex_55)
                        print(f"  -> Hex (5,5) at screen position: ({int(x)}, {int(y)})")
                elif event.key == pygame.K_m:
                    self.show_map = not self.show_map
                    print(f"Map: {'ON' if self.show_map else 'OFF'}")
                elif event.key == pygame.K_v:
                    # Toggle terrain visualization
                    self.show_terrain = not self.show_terrain
                    print(f"Terrain overlay: {'ON' if self.show_terrain else 'OFF'}")
                elif event.key == pygame.K_p:
                    # Print current mission hexes layout
                    self._print_mission_hexes()
                elif event.key == pygame.K_o:
                    # Print current offsets
                    self._print_calibration_values()
                
                # U-Boat controls (for testing positioning)
                elif event.key == pygame.K_q:
                    self.u_boat.facing = self.u_boat.facing.rotate_counterclockwise()
                elif event.key == pygame.K_e:
                    self.u_boat.facing = self.u_boat.facing.rotate_clockwise()
                elif event.key == pygame.K_w:
                    new_pos = self.u_boat.facing.forward(self.u_boat.position)
                    if self.hex_grid.is_valid_hex(new_pos, self.mission_hexes):
                        self.u_boat.position = new_pos
                elif event.key == pygame.K_z:
                    if self.u_boat.depth != Depth.DEEP:
                        self.u_boat.depth = Depth(self.u_boat.depth.value + 1)
                        print(f"Depth changed to: {self.u_boat.depth.name}")
                elif event.key == pygame.K_x:
                    if self.u_boat.depth != Depth.SURFACED:
                        self.u_boat.depth = Depth(self.u_boat.depth.value - 1)
                        print(f"Depth changed to: {self.u_boat.depth.name}")
                
                # TAB: Toggle between hex grid and status box adjustment mode
                elif event.key == pygame.K_TAB:
                    self.adjusting_hex_grid = not self.adjusting_hex_grid
                    mode = "HEX GRID" if self.adjusting_hex_grid else "STATUS BOXES"
                    print(f"Adjustment mode: {mode}")
                
                # +/- keys for scale adjustment (only in edit mode)
                elif self.edit_mode and event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_MINUS, pygame.K_UNDERSCORE):
                    shift_pressed = pygame.key.get_mods() & pygame.KMOD_SHIFT
                    step = 0.01 if shift_pressed else 0.001
                    
                    if event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                        if self.adjusting_hex_grid:
                            self.hex_scale_multiplier += step
                        else:
                            self.status_box_scale_multiplier += step
                    elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE):
                        if self.adjusting_hex_grid:
                            self.hex_scale_multiplier = max(0.5, self.hex_scale_multiplier - step)
                        else:
                            self.status_box_scale_multiplier = max(0.5, self.status_box_scale_multiplier - step)
                    
                    self._print_calibration_values()
                
                # Arrow keys for fine adjustment (only in edit mode)
                elif self.edit_mode and event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                    shift_pressed = pygame.key.get_mods() & pygame.KMOD_SHIFT
                    step = 10 if shift_pressed else 1
                    
                    if event.key == pygame.K_LEFT:
                        if self.adjusting_hex_grid:
                            self.user_hex_adjustment_x -= step
                        else:
                            self.user_status_adjustment_x -= step
                    elif event.key == pygame.K_RIGHT:
                        if self.adjusting_hex_grid:
                            self.user_hex_adjustment_x += step
                        else:
                            self.user_status_adjustment_x += step
                    elif event.key == pygame.K_UP:
                        if self.adjusting_hex_grid:
                            self.user_hex_adjustment_y -= step
                        else:
                            self.user_status_adjustment_y -= step
                    elif event.key == pygame.K_DOWN:
                        if self.adjusting_hex_grid:
                            self.user_hex_adjustment_y += step
                        else:
                            self.user_status_adjustment_y += step
                    
                    self._print_calibration_values()
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    keys = pygame.key.get_mods()
                    mouse_pos = pygame.mouse.get_pos()
                    
                    if self.edit_mode:
                        hex_coord = self.hex_grid.pixel_to_hex(*mouse_pos)
                        
                        if keys & pygame.KMOD_SHIFT:
                            # Shift+click: Add hex to mission
                            self.mission_hexes.add(hex_coord)
                            print(f"Added hex: ({hex_coord.q}, {hex_coord.r})")
                        elif keys & pygame.KMOD_CTRL:
                            # Ctrl+click: Remove hex from mission
                            if hex_coord in self.mission_hexes:
                                self.mission_hexes.discard(hex_coord)
                                print(f"Removed hex: ({hex_coord.q}, {hex_coord.r})")
                        elif keys & pygame.KMOD_ALT:
                            # Alt+click: Start coordinate detection drag for status boxes
                            self.coord_detect_dragging = True
                            self.coord_detect_start = mouse_pos
                        else:
                            # Regular click: Start dragging grid
                            self.dragging_grid = True
                            self.drag_start = pygame.mouse.get_pos()
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    if self.dragging_grid:
                        # Commit the drag adjustment (resets drag offset)
                        self.dragging_grid = False
                        self.drag_start = None
                        self._print_calibration_values()
                    elif self.coord_detect_dragging and self.coord_detect_start:
                        # Print drag coordinates for status box detection
                        mouse_pos = pygame.mouse.get_pos()
                        x1, y1 = self.coord_detect_start
                        x2, y2 = mouse_pos
                        # Ensure top-left to bottom-right
                        left = min(x1, x2)
                        top = min(y1, y2)
                        right = max(x1, x2)
                        bottom = max(y1, y2)
                        width = right - left
                        height = bottom - top
                        
                        # Only print if drag was significant (not just a click)
                        if width > 5 and height > 5:
                            print(f"\n=== STATUS BOX COORDINATES ===")
                            print(f"Top-Left: ({left}, {top})")
                            print(f"Bottom-Right: ({right}, {bottom})")
                            print(f"Width: {width}, Height: {height}")
                            print(f"Box: ({left}, {top}, {width}, {height})")
                            print(f"==============================\n")
                        
                        self.coord_detect_dragging = False
                        self.coord_detect_start = None
            
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging_grid and self.drag_start is not None:
                    # Update user hex adjustment based on drag
                    mouse_pos = pygame.mouse.get_pos()
                    dx = mouse_pos[0] - self.drag_start[0]
                    dy = mouse_pos[1] - self.drag_start[1]
                    self.user_hex_adjustment_x = dx
                    self.user_hex_adjustment_y = dy
    
    def _print_calibration_values(self) -> None:
        """Print current calibration values for updating board_config."""
        # Calculate the base values that should go in config (without adjustment applied)
        # Because both game and editor will add adjustment when they run
        # Need to recalculate adjustment to subtract it out
        cal_board_x = cfg.CALIBRATION_MAP_POSITION['board_x']
        cal_board_y = cfg.CALIBRATION_MAP_POSITION['board_y']
        cal_board_width = cfg.CALIBRATION_MAP_POSITION['board_width']
        cal_board_height = cfg.CALIBRATION_MAP_POSITION['board_height']
        
        # Use the SCALED map dimensions that AssetManager provides
        # (not the original 2204x2924)
        scaled_map_width = self.map_image.get_width()   # 678 from AssetManager
        scaled_map_height = self.map_image.get_height() # 900 from AssetManager
        cal_scale = cal_board_height / scaled_map_height
        scaled_cal_map_width = int(scaled_map_width * cal_scale)
        cal_map_x_offset = (cal_board_width - scaled_cal_map_width) // 2
        cal_map_x = cal_board_x + cal_map_x_offset
        cal_map_y = cal_board_y
        
        board_width = cfg.SCREEN_WIDTH - cfg.LEFT_PANEL_WIDTH - cfg.RIGHT_PANEL_WIDTH
        board_x = cfg.LEFT_PANEL_WIDTH
        board_y = cfg.TOP_BAR_HEIGHT
        
        original_map_width = self.map_image.get_width()
        scaled_map_width = int(original_map_width * self.scale)
        map_x_offset = (board_width - scaled_map_width) // 2
        actual_map_x = board_x + map_x_offset
        actual_map_y = board_y
        
        adjustment_x = actual_map_x - cal_map_x
        adjustment_y = actual_map_y - cal_map_y
        
        # Calculate base config values: current - adjustment
        # Offsets are NOT scaled, so just subtract adjustment
        base_hex_offset_x = int(self.hex_grid.offset_x - adjustment_x)
        base_hex_offset_y = int(self.hex_grid.offset_y - adjustment_y)
        base_global_offset_x = int(self.renderer.global_offset_x - adjustment_x)
        base_global_offset_y = int(self.renderer.global_offset_y - adjustment_y)
        
        print(f"\n=== Calibration Values ===")
        print(f"Current grid offset (with adjustment): ({int(self.hex_grid.offset_x)}, {int(self.hex_grid.offset_y)})")
        print(f"Current global offset (with adjustment): ({int(self.renderer.global_offset_x)}, {int(self.renderer.global_offset_y)})")
        print(f"Adjustment being applied: ({adjustment_x}, {adjustment_y})")
        print(f"\nUser adjustments: Hex=({self.user_hex_adjustment_x}, {self.user_hex_adjustment_y}), Status=({self.user_status_adjustment_x}, {self.user_status_adjustment_y})")
        print(f"Scale multipliers: Hex={self.hex_scale_multiplier:.3f}x, Status={self.status_box_scale_multiplier:.3f}x")
        print(f"\n** Update board_config.py with these BASE values **")
        print(f"  HEX_GRID 'offset_x': {base_hex_offset_x}, 'offset_y': {base_hex_offset_y}")
        print(f"  GLOBAL_BOARD_OFFSET 'offset_x': {base_global_offset_x}, 'offset_y': {base_global_offset_y}")
        print(f"  HEX_SCALE_MULTIPLIER: {self.hex_scale_multiplier:.3f}")
        print(f"  STATUS_BOX_SCALE_MULTIPLIER: {self.status_box_scale_multiplier:.3f}")
        print(f"========================\n")
    
    def update(self):
        """Update editor state."""
        pass
    
    def render(self):
        """Render everything with the same layout and scaling as the game."""
        self.screen.fill((10, 15, 25))
        
        # Use same panel dimensions as game
        screen_width = self.screen.get_width()
        screen_height = self.screen.get_height()
        left_width = cfg.LEFT_PANEL_WIDTH
        right_width = cfg.RIGHT_PANEL_WIDTH
        top_height = cfg.TOP_BAR_HEIGHT
        
        board_width = screen_width - left_width - right_width
        board_height = screen_height - top_height
        board_x = left_width
        board_y = top_height
        
        # Draw top bar
        bar_rect = pygame.Rect(0, 0, screen_width, top_height)
        pygame.draw.rect(self.screen, (25, 35, 50), bar_rect)
        pygame.draw.line(self.screen, (50, 70, 100), (0, top_height-1), (screen_width, top_height-1), 2)
        
        title = f"EDITOR - Mission {self.mission_number} {'(EDIT MODE)' if self.edit_mode else '(VIEW ONLY)'}"
        title_surface = self.font.render(title, True, (200, 220, 255))
        title_rect = title_surface.get_rect(center=(screen_width // 2, top_height // 2))
        self.screen.blit(title_surface, title_rect)
        
        # Draw board area with same scaling as game
        board_rect = pygame.Rect(board_x, board_y, board_width, board_height)
        pygame.draw.rect(self.screen, (15, 20, 30), board_rect)
        
        old_clip = self.screen.get_clip()
        self.screen.set_clip(board_rect)
        
        # Scale map uniformly
        original_map_width = self.map_image.get_width()
        original_map_height = self.map_image.get_height()
        scaled_map_width = int(original_map_width * self.scale)
        scaled_map_height = int(original_map_height * self.scale)
        map_image_scaled = pygame.transform.smoothscale(
            self.map_image,
            (scaled_map_width, scaled_map_height)
        )
        
        # Center map horizontally
        map_x_offset = (board_width - scaled_map_width) // 2
        actual_map_x = board_x + map_x_offset
        actual_map_y = board_y
        
        # Calculate calibration adjustment
        cal_board_x = cfg.CALIBRATION_MAP_POSITION['board_x']
        cal_board_y = cfg.CALIBRATION_MAP_POSITION['board_y']
        cal_board_width = cfg.CALIBRATION_MAP_POSITION['board_width']
        cal_board_height = cfg.CALIBRATION_MAP_POSITION['board_height']
        
        # Calculate scale at calibration time using the SCALED map dimensions
        cal_scale = cal_board_height / original_map_height
        cal_scaled_map_width = int(original_map_width * cal_scale)
        cal_map_x_offset = (cal_board_width - cal_scaled_map_width) // 2
        cal_map_x = cal_board_x + cal_map_x_offset
        cal_map_y = cal_board_y
        
        adjustment_x = actual_map_x - cal_map_x
        adjustment_y = actual_map_y - cal_map_y
        
        # Apply scaling to hex grid size with multiplier - offsets are pre-calibrated for scaled view
        self.hex_grid.size = int(self.original_hex_size * self.scale * self.hex_scale_multiplier)
        # Offsets are NOT scaled - just add adjustment and user tweaks
        self.hex_grid.offset_x = self.original_hex_offset_x + adjustment_x + self.user_hex_adjustment_x
        self.hex_grid.offset_y = self.original_hex_offset_y + adjustment_y + self.user_hex_adjustment_y
        self.hex_grid.global_offset_x = self.original_global_offset_x + adjustment_x + self.user_hex_adjustment_x
        self.hex_grid.global_offset_y = self.original_global_offset_y + adjustment_y + self.user_hex_adjustment_y
        
        # For renderer status boxes: offsets NOT scaled, just add adjustments
        self.renderer.global_offset_x = self.original_global_offset_x + adjustment_x + self.user_status_adjustment_x
        self.renderer.global_offset_y = self.original_global_offset_y + adjustment_y + self.user_status_adjustment_y
        
        # Debug: Print rendering info once on startup
        if not hasattr(self, '_debug_printed'):
            self._debug_printed = True
            print(f"\n=== Render Debug Info ===")
            print(f"Window size: {screen_width}x{screen_height}")
            print(f"Board area: {board_width}x{board_height} at ({board_x}, {board_y})")
            print(f"Map scale: {self.scale:.3f}")
            print(f"Adjustment: ({adjustment_x}, {adjustment_y})")
            print(f"Hex grid offset: ({int(self.hex_grid.offset_x)}, {int(self.hex_grid.offset_y)})")
            print(f"Status offset: ({int(self.renderer.global_offset_x)}, {int(self.renderer.global_offset_y)})")
            print(f"Show: grid={self.show_grid}, map={self.show_map}, markers={self.show_all_markers}")
            print(f"========================\n")
        
        # Render map
        if self.show_map:
            self.screen.blit(map_image_scaled, (actual_map_x, actual_map_y))
        
        # Render hex grid
        if self.show_grid:
            self.renderer.render_hex_grid(self.mission_hexes)
        
        # Render terrain
        if self.show_terrain:
            self.renderer.render_terrain_overlay(self.shallow_hexes, self.land_hexes, self.mission_hexes)
        
        # Render status boxes with scaling and multiplier
        self.renderer.render_status_markers(self.status_boxes, show_all=self.show_all_markers, scale=self.scale * self.status_box_scale_multiplier)
        
        # Render ships with scaling
        for ship in self.ships:
            self.renderer.render_ship(ship, scale=self.scale)
        
        # Render U-boat with scaling
        self.renderer.render_u_boat(self.u_boat, scale=self.scale)
        
        # Render coordinate detection rectangle if dragging
        if self.coord_detect_dragging and self.coord_detect_start:
            self.renderer.render_drag_rectangle(self.coord_detect_start)
        
        self.screen.set_clip(old_clip)
        
        # Draw board border
        pygame.draw.rect(self.screen, (50, 70, 100), board_rect, 2)
        
        # Draw info panels (simplified for editor)
        # Left panel
        left_rect = pygame.Rect(0, top_height, left_width, board_height)
        pygame.draw.rect(self.screen, (20, 25, 35), left_rect)
        pygame.draw.line(self.screen, (50, 70, 100), (left_width-1, top_height), (left_width-1, screen_height), 2)
        
        info_y = top_height + 20
        info_text = [
            "EDITOR CONTROLS:",
            "",
            "G: Toggle Grid",
            "M: Toggle Map",
            "V: Toggle Terrain",
            "S: Toggle Markers",
            "",
            "Q/E: Rotate U-boat",
            "W: Move Forward",
            "Z/X: Change Depth",
            "",
            f"Scale: {self.scale:.3f}x",
            f"Mode: {'HEX GRID' if self.adjusting_hex_grid else 'STATUS BOXES'}",
            f"Hex Grid: ({int(self.hex_grid.offset_x)}, {int(self.hex_grid.offset_y)})",
            f"  Adjust: ({self.user_hex_adjustment_x}, {self.user_hex_adjustment_y})",
            f"  Scale: {self.hex_scale_multiplier:.3f}x",
            f"Status: ({int(self.renderer.global_offset_x)}, {int(self.renderer.global_offset_y)})",
            f"  Adjust: ({self.user_status_adjustment_x}, {self.user_status_adjustment_y})",
            f"  Scale: {self.status_box_scale_multiplier:.3f}x",
        ]
        
        if self.edit_mode:
            info_text.extend([
                "",
                "EDIT MODE:",
                "TAB: Toggle adjustment mode",
                "Arrow: Adjust offset",
                "  Shift+Arrow: 10x speed",
                "+/-: Adjust scale",
                "  Shift+/-: 10x speed",
                "Click-Drag: Move hex grid",
                "Shift+Click: Add hex",
                "Ctrl+Click: Remove hex",
                "Alt+Drag: Detect box",
                "O: Print calibration",
                "P: Print hexes"
            ])
        
        for line in info_text:
            text_surface = self.font.render(line, True, (180, 200, 220) if line else (100, 100, 100))
            self.screen.blit(text_surface, (10, info_y))
            info_y += 20
        
        # Right panel
        right_rect = pygame.Rect(left_width + board_width, top_height, right_width, board_height)
        pygame.draw.rect(self.screen, (20, 25, 35), right_rect)
        pygame.draw.line(self.screen, (50, 70, 100), (left_width + board_width, top_height), (left_width + board_width, screen_height), 2)
        
        pygame.display.flip()
    
    def _print_mission_hexes(self):
        """Print current mission hexes in code format for easy copying."""
        print("\n" + "="*60)
        print(f"MISSION_{self.mission_number}_HEXES = [")
        
        # Group by row
        hexes_by_row: Dict[int, List[HexCoord]] = {}
        for hex_coord in sorted(self.mission_hexes, key=lambda h: (h.r, h.q)):
            if hex_coord.r not in hexes_by_row:
                hexes_by_row[hex_coord.r] = []
            hexes_by_row[hex_coord.r].append(hex_coord)
        
        # Print row by row with counts
        for r in sorted(hexes_by_row.keys()):
            hexes = hexes_by_row[r]
            hex_strings = [f"({h.q}, {h.r})" for h in hexes]
            print(f"    # Row {r} - {len(hexes)} hexes")
            for i in range(0, len(hex_strings), 10):  # 10 hexes per line
                chunk = hex_strings[i:i+10]
                print(f"    {', '.join(chunk)},")
        
        print("]")
        print(f"Total hexes: {len(self.mission_hexes)}")
        print("="*60 + "\n")
    
    def run(self):
        """Main editor loop."""
        print("\n" + "="*60)
        if self.edit_mode:
            print("BOARD EDITOR MODE - EDIT MODE ENABLED")
            print("="*60)
            print("WARNING: Map editing features are active!")
            print("\nEdit Controls:")
            print("  Click-Drag: Move grid")
            print("  Arrow Keys: Fine adjustment (Shift for 10x)")
            print("  Shift+Click: Add hex")
            print("  Ctrl+Click: Remove hex")
            print("  Alt+Click-Drag: Detect status box coordinates")
            print("  P: Print hexes")
            print("  O: Print grid offset")
        else:
            print("BOARD EDITOR MODE - VIEW ONLY")
            print("="*60)
            print("(Use --edit flag to enable map editing)")
        print("\nView Controls:")
        print("  G/M/V: Toggle grid/map/terrain")
        print("  S: Toggle show all markers")
        print("  T: Toggle torpedos (test)")
        print("  Q/E: Rotate U-boat")
        print("  W: Move U-boat forward")
        print("  Z/X: Change depth")
        print("  F11: Toggle fullscreen")
        print("  ESC: Quit")
        print("="*60 + "\n")
        
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(60)
        
        pygame.quit()


def main():
    """Start the board editor."""
    parser = argparse.ArgumentParser(description='Lone U-Boat Board Editor')
    parser.add_argument('--mission', type=int, default=1, help='Mission number to edit (default: 1)')
    parser.add_argument('--edit', action='store_true', help='Enable map editing features (use with caution)')
    args = parser.parse_args()
    
    editor = BoardEditor(mission_number=args.mission, edit_mode=args.edit)
    editor.run()


if __name__ == "__main__":
    main()
