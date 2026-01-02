"""
Board Editor and Alignment Tool for Lone U-Boat
Separate utility for aligning hex grids, detecting status box coordinates,
and testing mission configurations.
"""

import pygame
from typing import Optional, List, Dict, Any
import importlib
import argparse

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
        self.screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        
        # Edit mode controls whether map-altering features are enabled
        self.edit_mode = edit_mode
        
        # Load mission configuration
        self.mission_number = mission_number
        self.mission_config = self._load_mission_config(mission_number)
        
        pygame.display.set_caption(f"Lone U-Boat - EDITOR - {self.mission_config.MISSION_INFO['name']}")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Load mission map
        self.map_image = AssetManager.load_mission_map(self.mission_config.MISSION_INFO['map_image'])
        
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
                
                # Editor-specific toggles
                elif event.key == pygame.K_s:
                    # Toggle show all markers mode
                    self.show_all_markers = not self.show_all_markers
                elif event.key == pygame.K_t:
                    # Toggle torpedo loading (for testing markers)
                    all_loaded = all(self.u_boat.torpedo_tubes)
                    new_state = not all_loaded
                    self.u_boat.torpedo_tubes = [new_state] * 5
                elif event.key == pygame.K_g:
                    self.show_grid = not self.show_grid
                elif event.key == pygame.K_m:
                    self.show_map = not self.show_map
                elif event.key == pygame.K_v:
                    # Toggle terrain visualization
                    self.show_terrain = not self.show_terrain
                elif event.key == pygame.K_p:
                    # Print current mission hexes layout
                    self._print_mission_hexes()
                elif event.key == pygame.K_o:
                    # Print current grid offset values
                    print(f"\n=== GRID OFFSET ===")
                    print(f"offset_x: {int(self.hex_grid.offset_x)}")
                    print(f"offset_y: {int(self.hex_grid.offset_y)}")
                    print(f"===================\n")
                
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
                
                # Arrow keys for fine grid adjustment (only in edit mode)
                # Now adjusts GLOBAL offset which moves both grid and status boxes together
                elif self.edit_mode and event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                    shift_pressed = pygame.key.get_mods() & pygame.KMOD_SHIFT
                    step = 10 if shift_pressed else 1
                    
                    if event.key == pygame.K_LEFT:
                        self.hex_grid.global_offset_x -= step
                        self.renderer.global_offset_x -= step
                    elif event.key == pygame.K_RIGHT:
                        self.hex_grid.global_offset_x += step
                        self.renderer.global_offset_x += step
                    elif event.key == pygame.K_UP:
                        self.hex_grid.global_offset_y -= step
                        self.renderer.global_offset_y -= step
                    elif event.key == pygame.K_DOWN:
                        self.hex_grid.global_offset_y += step
                        self.renderer.global_offset_y += step
                    
                    print(f"Global board offset: ({int(self.hex_grid.global_offset_x)}, {int(self.hex_grid.global_offset_y)})")
                    print(f"  -> Update board_config.py GLOBAL_BOARD_OFFSET to: {{'offset_x': {int(self.hex_grid.global_offset_x)}, 'offset_y': {int(self.hex_grid.global_offset_y)}}}")
            
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
                            self.grid_offset_start = (self.hex_grid.offset_x, self.hex_grid.offset_y)
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    if self.dragging_grid:
                        self.dragging_grid = False
                        print(f"Grid offset: ({int(self.hex_grid.offset_x)}, {int(self.hex_grid.offset_y)})")
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
                if self.dragging_grid and self.drag_start is not None and self.grid_offset_start is not None:
                    # Update grid offset based on drag
                    mouse_pos = pygame.mouse.get_pos()
                    dx = mouse_pos[0] - self.drag_start[0]
                    dy = mouse_pos[1] - self.drag_start[1]
                    self.hex_grid.offset_x = self.grid_offset_start[0] + dx
                    self.hex_grid.offset_y = self.grid_offset_start[1] + dy
    
    def update(self):
        """Update editor state."""
        pass
    
    def render(self):
        """Render everything using the GameRenderer."""
        self.renderer.render_frame(self)
    
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
