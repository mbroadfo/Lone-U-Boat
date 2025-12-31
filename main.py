"""
Lone U-Boat Game - Clean Architecture
A hex-based submarine warfare game using actual mission maps.
"""

import pygame
import math
from pathlib import Path
from dataclasses import dataclass
from typing import Tuple, Optional, List
from enum import Enum
import importlib

# Import board and mission configurations
from config import board_config as cfg


class Terrain(Enum):
    """Hex terrain types."""
    LAND = 0
    SHALLOW = 1
    DEEP = 2


# ====================
# DATA CLASSES
# ====================

@dataclass
class HexCoord:
    """Axial coordinate system for hexagons."""
    q: int  # column
    r: int  # row
    
    def __hash__(self):
        return hash((self.q, self.r))
    
    def __eq__(self, other):
        return self.q == other.q and self.r == other.r
    
    def neighbors(self) -> List['HexCoord']:
        """Return all 6 neighboring hex coordinates (axial coordinates, flat-top)."""
        # Constant axial direction vectors for flat-top hexes
        directions = [
            HexCoord(0, -1),   # N
            HexCoord(1, -1),   # NE
            HexCoord(1, 0),    # SE
            HexCoord(0, 1),    # S
            HexCoord(-1, 1),   # SW
            HexCoord(-1, 0),   # NW
        ]
        return [HexCoord(self.q + d.q, self.r + d.r) for d in directions]


class Facing(Enum):
    """Six possible facing directions for units (0-5, clockwise from top)."""
    NORTH = 0
    NORTHEAST = 1
    SOUTHEAST = 2
    SOUTH = 3
    SOUTHWEST = 4
    NORTHWEST = 5
    
    def rotate_clockwise(self) -> 'Facing':
        """Rotate one hex edge clockwise."""
        return Facing((self.value + 1) % 6)
    
    def rotate_counterclockwise(self) -> 'Facing':
        """Rotate one hex edge counterclockwise."""
        return Facing((self.value - 1) % 6)
    
    def forward(self, coord: HexCoord) -> HexCoord:
        """Get the hex coordinate in front of this facing (axial coordinates)."""
        # Constant axial direction vectors for flat-top hexes
        directions = [
            HexCoord(0, -1),   # N
            HexCoord(1, -1),   # NE
            HexCoord(1, 0),    # SE
            HexCoord(0, 1),    # S
            HexCoord(-1, 1),   # SW
            HexCoord(-1, 0),   # NW
        ]
        d = directions[self.value]
        return HexCoord(coord.q + d.q, coord.r + d.r)


class Depth(Enum):
    """U-Boat depth levels."""
    SURFACED = 0
    PERISCOPE = 1
    MEDIUM = 2
    DEEP = 3


@dataclass
class UBoat:
    """The player's U-Boat."""
    position: HexCoord
    facing: Facing
    depth: Depth = Depth.SURFACED
    
    # Game state
    action_points: int = 0
    hull_damage: int = 0
    engine_damaged: bool = False
    
    # Crew (True = alive)
    captain_alive: bool = True
    engineer_alive: bool = True
    sonar_operator_alive: bool = True
    weapons_officer_alive: bool = True
    lookout_alive: bool = True
    medic_alive: bool = True
    
    # Weapons
    torpedo_tubes: List[bool] = None  # True = loaded
    deck_gun_damaged: bool = False
    flak_gun_damaged: bool = False
    
    def __post_init__(self):
        if self.torpedo_tubes is None:
            self.torpedo_tubes = [True] * 5  # 4 front + 1 rear


@dataclass
class Ship:
    """An allied ship (merchant, corvette, or destroyer)."""
    position: HexCoord
    facing: Facing
    ship_type: str  # 'merchant', 'corvette', 'destroyer'
    damaged: bool = False


# ====================
# HEX MATH
# ====================

class HexGrid:
    """Handles hex grid calculations and rendering."""
    
    def __init__(self, size: int, cols: int, rows: int, offset_x: int = 0, offset_y: int = 0):
        self.size = size
        self.cols = cols
        self.rows = rows
        self.offset_x = offset_x
        self.offset_y = offset_y
        
        # Flat-top hex math (pointy sides)
        self.width = 2 * size
        self.height = math.sqrt(3) * size
        self.horiz_spacing = self.width * 3/4
        
    def hex_to_pixel(self, coord: HexCoord) -> Tuple[float, float]:
        """Convert axial hex coordinates to pixel coordinates (flat-top hexes).
        
        Axial coordinates:
        - q axis: roughly horizontal (columns)
        - r axis: down-right diagonal
        """
        x = self.size * (3/2 * coord.q)
        y = self.size * (math.sqrt(3) * (coord.r + coord.q / 2))
        return (x + self.offset_x, y + self.offset_y)
    
    def pixel_to_hex(self, x: float, y: float) -> HexCoord:
        """Convert pixel coordinates to axial hex coordinates (flat-top hexes)."""
        # Adjust for offset
        x -= self.offset_x
        y -= self.offset_y
        
        # Inverse axial coordinate formulas
        q = (2/3 * x) / self.size
        r = (-1/3 * x + math.sqrt(3)/3 * y) / self.size
        
        # Round to nearest hex using cube coordinate rounding
        return self._round_hex(q, r)
    
    def _round_hex(self, q: float, r: float) -> HexCoord:
        """Round fractional axial coordinates to nearest integer hex using cube rounding.
        
        Converts axial (q,r) to cube (q,r,s) where s = -q-r, rounds all three,
        then fixes the component with largest rounding error to maintain q+r+s=0.
        """
        s = -q - r
        
        rq = round(q)
        rr = round(r)
        rs = round(s)
        
        q_diff = abs(rq - q)
        r_diff = abs(rr - r)
        s_diff = abs(rs - s)
        
        if q_diff > r_diff and q_diff > s_diff:
            rq = -rr - rs
        elif r_diff > s_diff:
            rr = -rq - rs
        
        return HexCoord(int(rq), int(rr))
    
    def get_hex_corners(self, coord: HexCoord) -> List[Tuple[float, float]]:
        """Get the pixel coordinates of a hex's 6 corners."""
        center_x, center_y = self.hex_to_pixel(coord)
        corners = []
        
        for i in range(6):
            angle_deg = 60 * i  # Flat-top (pointy sides)
            angle_rad = math.pi / 180 * angle_deg
            corner_x = center_x + self.size * math.cos(angle_rad)
            corner_y = center_y + self.size * math.sin(angle_rad)
            corners.append((corner_x, corner_y))
        
        return corners
    
    def is_valid_hex(self, coord: HexCoord, mission_hexes=None) -> bool:
        """Check if axial hex coordinate is valid for the mission.
        
        For missions, primarily rely on the mission_hexes set membership.
        The bounds check is kept as a quick rejection test.
        """
        # Quick rejection: basic bounds check
        if not (0 <= coord.q < self.cols and 0 <= coord.r < self.rows):
            return False
        
        # Primary validation: check mission-specific valid hexes if provided
        if mission_hexes is not None:
            return coord in mission_hexes
        
        return True


# ====================
# GAME STATE
# ====================

class Game:
    """Main game state and logic."""
    
    def __init__(self, mission_number: int = 1):
        pygame.init()
        self.screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        
        # Load mission configuration
        self.mission_number = mission_number
        self.mission_config = self._load_mission_config(mission_number)
        
        pygame.display.set_caption(f"Lone U-Boat - {self.mission_config.MISSION_INFO['name']}")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Load mission map
        self.map_image = self._load_mission_map()
        
        # Convert mission hex coordinates to HexCoord objects
        # Use VALID_HEXES from board_config unless mission overrides it
        valid_hexes = self.mission_config.VALID_HEXES if self.mission_config.VALID_HEXES else cfg.VALID_HEXES
        self.mission_hexes = {HexCoord(q, r) for q, r in valid_hexes}
        
        # Calculate map position to center it
        map_rect = self.map_image.get_rect()
        map_x = (cfg.SCREEN_WIDTH - map_rect.width) // 2
        map_y = cfg.UI['map_offset_y']
        
        # Create hex grid overlay
        self.hex_grid = HexGrid(
            size=cfg.HEX_GRID['size'],
            cols=cfg.HEX_GRID['cols'],
            rows=cfg.HEX_GRID['rows'],
            offset_x=cfg.HEX_GRID['offset_x'],
            offset_y=cfg.HEX_GRID['offset_y']
        )
        
        # Game entities - load from mission config
        u_boat_start = self.mission_config.U_BOAT_START
        self.u_boat = UBoat(
            position=HexCoord(*u_boat_start['position']),
            facing=Facing[u_boat_start['facing']]
        )
        
        self.ships: List[Ship] = []  # Mission-specific ships will be added later
        
        # UI state
        self.selected_hex: Optional[HexCoord] = None
        self.show_grid = True
        self.show_map = True
        self.detection_level = 0
        
        # Grid alignment mode
        self.alignment_mode = False
        self.dragging_grid = False
        self.drag_start = None
        self.grid_offset_start = None
        
        # Coordinate detection mode (for status boxes)
        self.coord_detect_dragging = False
        self.coord_detect_start = None
        
        # Status box markers
        self.status_boxes = {}
        self.marker_images = self._load_marker_images()
        self._setup_status_boxes()
        self.show_all_markers = False  # Toggle to show all markers for testing
        
        # Fonts
        self.font = pygame.font.Font(None, cfg.UI['font_size'])
        self.font_large = pygame.font.Font(None, cfg.UI['font_size_large'])
        
        # Load U-Boat images
        self.u_boat_images = self._load_u_boat_images()
    
    def _load_mission_config(self, mission_number: int):
        """Dynamically load mission configuration module."""
        try:
            mission_module = importlib.import_module(f'missions.mission_{mission_number}_config')
            return mission_module
        except ImportError:
            raise ValueError(f"Mission {mission_number} configuration not found")
    
    def _load_u_boat_images(self) -> dict:
        """Load U-Boat images for each depth level."""
        images = {}
        depth_files = {
            Depth.SURFACED: cfg.ASSETS['u_boat_surfaced'],
            Depth.PERISCOPE: cfg.ASSETS['u_boat_periscope'],
            Depth.MEDIUM: cfg.ASSETS['u_boat_medium'],
            Depth.DEEP: cfg.ASSETS['u_boat_deep'],
        }
        
        # Target size to fit in hex
        target_size = cfg.UI['u_boat_image_size']
        
        for depth, filepath in depth_files.items():
            path = Path(filepath)
            if path.exists():
                image = pygame.image.load(path).convert_alpha()
                # Scale down significantly to fit in hex
                original_size = max(image.get_width(), image.get_height())
                scale = target_size / original_size
                new_width = int(image.get_width() * scale)
                new_height = int(image.get_height() * scale)
                images[depth] = pygame.transform.smoothscale(image, (new_width, new_height))
            else:
                # Create placeholder if image doesn't exist
                surface = pygame.Surface((40, 40), pygame.SRCALPHA)
                pygame.draw.circle(surface, cfg.COLORS['u_boat'], (20, 20), 15)
                images[depth] = surface
        
        return images
    
    def _load_marker_images(self) -> dict:
        """Load marker images for status boxes."""
        markers = {}
        marker_files = {
            'detection': cfg.ASSETS['detection_marker'],
            'damaged': cfg.ASSETS['damaged_marker'],
            'torpedo': cfg.ASSETS['torpedo_marker']
        }
        
        for marker_type, filename in marker_files.items():
            path = Path(filename)
            if path.exists():
                markers[marker_type] = pygame.image.load(path).convert_alpha()
            else:
                # Create placeholder if image doesn't exist
                surface = pygame.Surface((20, 20), pygame.SRCALPHA)
                pygame.draw.circle(surface, (255, 255, 0), (10, 10), 8)
                markers[marker_type] = surface
        
        return markers
    
    def _setup_status_boxes(self):
        """Configure status box positions and marker types from config."""
        for box_name, box_data in cfg.STATUS_BOXES.items():
            rect_tuple = box_data['rect']
            marker_type = box_data['marker']
            condition_key = box_data['condition']
            
            # Create lambda for condition based on string key
            condition = self._create_condition_lambda(condition_key)
            
            self.status_boxes[box_name] = {
                'rect': pygame.Rect(*rect_tuple),
                'marker_type': marker_type,
                'condition': condition
            }
    
    def _create_condition_lambda(self, condition_key: str):
        """Create a lambda function for status box conditions based on config string."""
        # Detection levels
        if condition_key.startswith('detection_level_'):
            level = int(condition_key.split('_')[-1])
            return lambda: self.detection_level == level
        
        # Hull damage
        elif condition_key.startswith('hull_damage_'):
            level = int(condition_key.split('_')[-1])
            return lambda: self.u_boat.hull_damage >= level
        
        # Torpedo tubes
        elif condition_key.startswith('torpedo_tube_'):
            tube_index = int(condition_key.split('_')[-1])
            return lambda idx=tube_index: self.u_boat.torpedo_tubes[idx]
        
        # Crew (alive status - condition triggers when dead)
        elif condition_key == 'captain_dead':
            return lambda: not self.u_boat.captain_alive
        elif condition_key == 'sonar_operator_dead':
            return lambda: not self.u_boat.sonar_operator_alive
        elif condition_key == 'engineer_dead':
            return lambda: not self.u_boat.engineer_alive
        elif condition_key == 'weapons_officer_dead':
            return lambda: not self.u_boat.weapons_officer_alive
        elif condition_key == 'lookout_dead':
            return lambda: not self.u_boat.lookout_alive
        elif condition_key == 'medic_dead':
            return lambda: not self.u_boat.medic_alive
        
        # Equipment damage
        elif condition_key == 'engine_damaged':
            return lambda: self.u_boat.engine_damaged
        elif condition_key == 'flak_gun_damaged':
            return lambda: self.u_boat.flak_gun_damaged
        elif condition_key == 'deck_gun_damaged':
            return lambda: self.u_boat.deck_gun_damaged
        
        # Default: always false
        else:
            return lambda: False
    
    def _load_mission_map(self) -> pygame.Surface:
        """Load the mission map image from config."""
        map_path = Path(self.mission_config.MISSION_INFO['map_image'])
        if not map_path.exists():
            # Create placeholder if map doesn't exist
            surface = pygame.Surface((800, 600))
            surface.fill((100, 150, 200))
            return surface
        
        image = pygame.image.load(map_path)
        # Scale down if too large
        max_width = 900
        max_height = 700
        if image.get_width() > max_width or image.get_height() > max_height:
            scale = min(max_width / image.get_width(), 
                       max_height / image.get_height())
            new_size = (int(image.get_width() * scale), 
                       int(image.get_height() * scale))
            image = pygame.transform.smoothscale(image, new_size)
        
        return image
    
    def handle_events(self):
        """Handle pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_a:
                    # Toggle alignment mode
                    self.alignment_mode = not self.alignment_mode
                    self.dragging_grid = False
                elif event.key == pygame.K_s:
                    # Toggle show all markers mode
                    self.show_all_markers = not self.show_all_markers
                    status = "ON" if self.show_all_markers else "OFF"
                    print(f"Show all markers: {status}")
                elif event.key == pygame.K_t:
                    # Toggle torpedo loading (for testing markers)
                    all_loaded = all(self.u_boat.torpedo_tubes)
                    new_state = not all_loaded
                    self.u_boat.torpedo_tubes = [new_state] * 5
                    status = "LOADED" if new_state else "EMPTY"
                    print(f"All torpedos: {status}")
                elif event.key == pygame.K_g:
                    self.show_grid = not self.show_grid
                elif event.key == pygame.K_m:
                    self.show_map = not self.show_map
                elif event.key == pygame.K_q:
                    # Rotate U-boat left
                    self.u_boat.facing = self.u_boat.facing.rotate_counterclockwise()
                elif event.key == pygame.K_e:
                    # Rotate U-boat right
                    self.u_boat.facing = self.u_boat.facing.rotate_clockwise()
                elif event.key == pygame.K_w:
                    # Move U-boat forward
                    new_pos = self.u_boat.facing.forward(self.u_boat.position)
                    if self.hex_grid.is_valid_hex(new_pos, self.mission_hexes):
                        self.u_boat.position = new_pos
                elif event.key == pygame.K_z:
                    # Increase depth (go deeper)
                    if self.u_boat.depth != Depth.DEEP:
                        self.u_boat.depth = Depth(self.u_boat.depth.value + 1)
                        print(f"Depth changed to: {self.u_boat.depth.name}")
                elif event.key == pygame.K_x:
                    # Decrease depth (go shallower)
                    if self.u_boat.depth != Depth.SURFACED:
                        self.u_boat.depth = Depth(self.u_boat.depth.value - 1)
                        print(f"Depth changed to: {self.u_boat.depth.name}")
                elif event.key == pygame.K_p:
                    # Print current mission hexes layout
                    self._print_mission_hexes()
                
                # Arrow keys for fine grid adjustment in alignment mode
                elif self.alignment_mode:
                    shift_pressed = pygame.key.get_mods() & pygame.KMOD_SHIFT
                    step = 10 if shift_pressed else 1
                    
                    if event.key == pygame.K_LEFT:
                        self.hex_grid.offset_x -= step
                    elif event.key == pygame.K_RIGHT:
                        self.hex_grid.offset_x += step
                    elif event.key == pygame.K_UP:
                        self.hex_grid.offset_y -= step
                    elif event.key == pygame.K_DOWN:
                        self.hex_grid.offset_y += step
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    keys = pygame.key.get_mods()
                    mouse_pos = pygame.mouse.get_pos()
                    hex_coord = self.hex_grid.pixel_to_hex(*mouse_pos)
                    
                    if keys & pygame.KMOD_SHIFT:
                        # Shift+click: Add hex to mission
                        self.mission_hexes.add(hex_coord)
                        print(f"Added hex: {hex_coord}")
                    elif keys & pygame.KMOD_CTRL:
                        # Ctrl+click: Remove hex from mission
                        if hex_coord in self.mission_hexes:
                            self.mission_hexes.discard(hex_coord)
                            print(f"Removed hex: {hex_coord}")
                    elif self.alignment_mode:
                        # Start dragging grid
                        self.dragging_grid = True
                        self.drag_start = pygame.mouse.get_pos()
                        self.grid_offset_start = (self.hex_grid.offset_x, self.hex_grid.offset_y)
                    else:
                        # Start coordinate detection drag (for status boxes)
                        self.coord_detect_dragging = True
                        self.coord_detect_start = mouse_pos
                        # Also select hex for normal gameplay
                        if self.hex_grid.is_valid_hex(hex_coord, self.mission_hexes):
                            self.selected_hex = hex_coord
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    if self.alignment_mode:
                        self.dragging_grid = False
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
                if self.dragging_grid and self.drag_start:
                    # Update grid offset based on drag
                    mouse_pos = pygame.mouse.get_pos()
                    dx = mouse_pos[0] - self.drag_start[0]
                    dy = mouse_pos[1] - self.drag_start[1]
                    self.hex_grid.offset_x = self.grid_offset_start[0] + dx
                    self.hex_grid.offset_y = self.grid_offset_start[1] + dy
    
    def update(self):
        """Update game state."""
        pass  # Game logic will go here
    
    def render(self):
        """Render everything."""
        self.screen.fill(cfg.COLORS['background'])
        
        # Draw mission map
        if self.show_map:
            map_rect = self.map_image.get_rect()
            map_x = (cfg.SCREEN_WIDTH - map_rect.width) // 2
            map_y = 50
            self.screen.blit(self.map_image, (map_x, map_y))
        
        # Draw hex grid overlay
        if self.show_grid:
            self._render_hex_grid()
        
        # Draw ships
        for ship in self.ships:
            self._render_ship(ship)
        
        # Draw U-boat
        self._render_u_boat()
        
        # Draw selected hex
        if self.selected_hex:
            self._render_hex_highlight(self.selected_hex, cfg.COLORS['selection'])
        
        # Draw coordinate detection rectangle (visual feedback during drag)
        if self.coord_detect_dragging and self.coord_detect_start:
            self._render_drag_rectangle()
        
        # Draw status box markers
        self._render_status_markers()
        
        # Draw UI
        self._render_ui()
        
        pygame.display.flip()
    
    def _render_hex_grid(self):
        """Render hex grid overlay."""
        surface = pygame.Surface((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        
        # Only render valid mission hexes
        for coord in self.mission_hexes:
            corners = self.hex_grid.get_hex_corners(coord)
            pygame.draw.polygon(surface, cfg.COLORS['hex_grid'], corners, 1)
            
            # Add coordinate labels
            center = self.hex_grid.hex_to_pixel(coord)
            label = self.font.render(f"{coord.q},{coord.r}", True, (200, 200, 200))
            label_rect = label.get_rect(center=(int(center[0]), int(center[1])))
            surface.blit(label, label_rect)
        
        self.screen.blit(surface, (0, 0))
    
    def _render_hex_highlight(self, coord: HexCoord, color: Tuple[int, int, int, int]):
        """Highlight a specific hex."""
        surface = pygame.Surface((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        corners = self.hex_grid.get_hex_corners(coord)
        pygame.draw.polygon(surface, color, corners)
        self.screen.blit(surface, (0, 0))
    
    def _render_u_boat(self):
        """Render the U-boat using depth-specific PNG images."""
        center = self.hex_grid.hex_to_pixel(self.u_boat.position)
        
        # Get the appropriate image for current depth
        image = self.u_boat_images.get(self.u_boat.depth)
        if image is None:
            return
        
        # Rotate image based on facing (aligned with hex edges)
        angle_deg = -60 * self.u_boat.facing.value
        rotated_image = pygame.transform.rotate(image, angle_deg)
        
        # Center the rotated image
        rect = rotated_image.get_rect(center=(int(center[0]), int(center[1])))
        self.screen.blit(rotated_image, rect)
    
    def _render_ship(self, ship: Ship):
        """Render an allied ship."""
        center = self.hex_grid.hex_to_pixel(ship.position)
        
        # Draw square for ship
        size = 15
        rect = pygame.Rect(center[0] - size, center[1] - size, size * 2, size * 2)
        pygame.draw.rect(self.screen, cfg.COLORS['ship'], rect)
        
        # Draw border if damaged
        if ship.damaged:
            pygame.draw.rect(self.screen, (255, 0, 0), rect, 3)
    
    def _render_drag_rectangle(self):
        """Render drag rectangle for coordinate detection."""
        if not self.coord_detect_start:
            return
        
        mouse_pos = pygame.mouse.get_pos()
        x1, y1 = self.coord_detect_start
        x2, y2 = mouse_pos
        
        # Calculate rectangle
        left = min(x1, x2)
        top = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        
        # Draw semi-transparent rectangle
        surface = pygame.Surface((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT), pygame.SRCALPHA)
        rect = pygame.Rect(left, top, width, height)
        pygame.draw.rect(surface, (255, 255, 0, 100), rect)  # Yellow with transparency
        pygame.draw.rect(surface, (255, 255, 0, 255), rect, 2)  # Yellow border
        self.screen.blit(surface, (0, 0))
    
    def _render_status_markers(self):
        """Render status box markers based on game state."""
        for box_name, box_data in self.status_boxes.items():
            rect = box_data['rect']
            marker_type = box_data['marker_type']
            condition = box_data.get('condition', True)
            
            # In show all markers mode, always render
            if self.show_all_markers:
                should_render = True
            else:
                # Evaluate condition if it's a lambda/callable
                if callable(condition):
                    should_render = condition()
                else:
                    should_render = condition
            
            # Only render if condition is met
            if not should_render:
                continue
            
            # Get marker image
            marker_img = self.marker_images.get(marker_type)
            if marker_img is None:
                continue
            
            # Scale marker to fit box
            scaled_marker = pygame.transform.smoothscale(marker_img, (rect.width, rect.height))
            self.screen.blit(scaled_marker, rect)
    
    def _render_ui(self):
        """Render UI panels and information."""
        # Top bar
        ui_rect = pygame.Rect(0, 0, cfg.SCREEN_WIDTH, cfg.UI['top_bar_height'])
        pygame.draw.rect(self.screen, cfg.COLORS['panel_bg'], ui_rect)
        
        # Title
        title_text = f"{self.mission_config.MISSION_INFO['name']}"
        title = self.font_large.render(title_text, True, cfg.COLORS['text'])
        self.screen.blit(title, (10, 5))
        
        # Controls info
        if self.alignment_mode:
            controls = self.font.render(
                "ALIGNMENT MODE: Click-Drag | Arrows | Shift+Click-Add | Ctrl+Click-Remove | P-Print | A-Exit",
                True, (255, 255, 0)  # Yellow for alignment mode
            )
        else:
            controls = self.font.render(
                "Controls: Q/E-Rotate | W-Move | Z/X-Depth | T-Torpedos | S-Show All | G-Grid | M-Map | A-Align | ESC-Quit",
                True, cfg.COLORS['text']
            )
        self.screen.blit(controls, (10, cfg.SCREEN_HEIGHT - 30))
        
        # Show marker mode indicator
        if self.show_all_markers:
            marker_mode_text = self.font.render(
                "ALL MARKERS VISIBLE (Press S to toggle)",
                True, (255, 255, 0)
            )
            self.screen.blit(marker_mode_text, (10, cfg.SCREEN_HEIGHT - 60))
        
        # Show offset values in alignment mode
        if self.alignment_mode:
            offset_text = self.font.render(
                f"Offset X: {int(self.hex_grid.offset_x)} | Y: {int(self.hex_grid.offset_y)}",
                True, (255, 255, 0)
            )
            self.screen.blit(offset_text, (10, cfg.SCREEN_HEIGHT - 60))
        
        # Status panel (right side)
        panel_x = cfg.UI['status_panel_x']
        panel_y = cfg.UI['status_panel_y']
        
        # Depth color based on level
        depth_colors = {
            Depth.SURFACED: (255, 100, 100),    # Red (most visible)
            Depth.PERISCOPE: (255, 200, 100),   # Orange
            Depth.MEDIUM: (100, 200, 255),      # Light blue
            Depth.DEEP: (50, 100, 200),         # Dark blue (safest)
        }
        depth_color = depth_colors.get(self.u_boat.depth, cfg.COLORS['text'])
        
        status_texts = [
            (f"Position: ({self.u_boat.position.q}, {self.u_boat.position.r})", cfg.COLORS['text']),
            (f"Facing: {self.u_boat.facing.name}", cfg.COLORS['text']),
            (f"Depth: {self.u_boat.depth.name} (Z/X)", depth_color),
            (f"Detection: {self.detection_level}", cfg.COLORS['text']),
            (f"Hull Damage: {self.u_boat.hull_damage}/3", cfg.COLORS['text']),
        ]
        
        for i, (text, color) in enumerate(status_texts):
            rendered = self.font.render(text, True, color)
            self.screen.blit(rendered, (panel_x, panel_y + i * 25))
    
    def _print_mission_hexes(self):
        """Print current mission hexes in code format for easy copying."""
        print("\n" + "="*60)
        print("MISSION_1_HEXES = {")
        
        # Group by row
        hexes_by_row = {}
        for hex_coord in sorted(self.mission_hexes, key=lambda h: (h.r, h.q)):
            if hex_coord.r not in hexes_by_row:
                hexes_by_row[hex_coord.r] = []
            hexes_by_row[hex_coord.r].append(hex_coord)
        
        # Print row by row with counts
        for r in sorted(hexes_by_row.keys()):
            hexes = hexes_by_row[r]
            hex_strings = [f"HexCoord({h.q}, {h.r})" for h in hexes]
            print(f"    # Row {r} - {len(hexes)} hexes")
            print(f"    {', '.join(hex_strings)},")
        
        print("}")
        print(f"Total hexes: {len(self.mission_hexes)}")
        print("="*60 + "\n")
    
    def run(self):
        """Main game loop."""
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(60)
        
        pygame.quit()


# ====================
# MAIN ENTRY POINT
# ====================

def main():
    """Start the game."""
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
