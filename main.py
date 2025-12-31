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


class Terrain(Enum):
    """Hex terrain types."""
    LAND = 0
    SHALLOW = 1
    DEEP = 2


# ====================
# CONSTANTS & CONFIG
# ====================

SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 900

# Colors
COLOR_HEX_GRID = (100, 100, 100, 128)  # Semi-transparent gray
COLOR_HEX_HIGHLIGHT = (255, 255, 0, 200)  # Yellow highlight
COLOR_U_BOAT = (255, 0, 0)  # Red
COLOR_SHIP = (0, 0, 255)  # Blue
COLOR_SELECTION = (0, 255, 0, 150)  # Green selection
COLOR_VALID_MOVE = (0, 255, 0, 100)  # Green for valid moves
COLOR_PANEL_BG = (40, 40, 40)
COLOR_TEXT = (255, 255, 255)

# Hex grid configuration
HEX_SIZE = 32  # Radius of hexagon
HEX_COLS = 11  # Maximum columns (0-10)
HEX_ROWS = 12  # Rows 0-11


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
        """Return all 6 neighboring hex coordinates (offset coordinates, flat-top)."""
        # Neighbors depend on whether column is even or odd
        parity = self.q & 1  # 0 for even, 1 for odd
        
        if parity == 0:  # Even column
            directions = [
                HexCoord(1, -1), HexCoord(1, 0),    # NE, SE
                HexCoord(0, 1),                      # S
                HexCoord(-1, 0), HexCoord(-1, -1),  # SW, NW
                HexCoord(0, -1)                      # N
            ]
        else:  # Odd column
            directions = [
                HexCoord(1, 0), HexCoord(1, 1),     # NE, SE
                HexCoord(0, 1),                      # S
                HexCoord(-1, 1), HexCoord(-1, 0),   # SW, NW
                HexCoord(0, -1)                      # N
            ]
        return [HexCoord(self.q + d.q, self.r + d.r) for d in directions]


# Mission 1 valid hex coordinates - 67 total hexes
# Pattern: 1,3,5,7,9,9,9,8,7,5,3,1
MISSION_1_HEXES = {
    # Row 0 - 1 hex
    HexCoord(5, 0),
    # Row 1 - 3 hexes
    HexCoord(4, 1), HexCoord(5, 1), HexCoord(6, 1),
    # Row 2 - 5 hexes
    HexCoord(3, 2), HexCoord(4, 2), HexCoord(5, 2), HexCoord(6, 2), HexCoord(7, 2),
    # Row 3 - 7 hexes
    HexCoord(2, 3), HexCoord(3, 3), HexCoord(4, 3), HexCoord(5, 3), HexCoord(6, 3), HexCoord(7, 3), HexCoord(8, 3),
    # Row 4 - 9 hexes (widest)
    HexCoord(1, 4), HexCoord(2, 4), HexCoord(3, 4), HexCoord(4, 4), HexCoord(5, 4), HexCoord(6, 4), HexCoord(7, 4), HexCoord(8, 4), HexCoord(9, 4),
    # Row 5 - 9 hexes
    HexCoord(1, 5), HexCoord(2, 5), HexCoord(3, 5), HexCoord(4, 5), HexCoord(5, 5), HexCoord(6, 5), HexCoord(7, 5), HexCoord(8, 5), HexCoord(9, 5),
    # Row 6 - 9 hexes
    HexCoord(1, 6), HexCoord(2, 6), HexCoord(3, 6), HexCoord(4, 6), HexCoord(5, 6), HexCoord(6, 6), HexCoord(7, 6), HexCoord(8, 6), HexCoord(9, 6),
    # Row 7 - 8 hexes
    HexCoord(2, 7), HexCoord(3, 7), HexCoord(4, 7), HexCoord(5, 7), HexCoord(6, 7), HexCoord(7, 7), HexCoord(8, 7), HexCoord(9, 7),
    # Row 8 - 7 hexes
    HexCoord(3, 8), HexCoord(4, 8), HexCoord(5, 8), HexCoord(6, 8), HexCoord(7, 8), HexCoord(8, 8), HexCoord(9, 8),
    # Row 9 - 5 hexes
    HexCoord(4, 9), HexCoord(5, 9), HexCoord(6, 9), HexCoord(7, 9), HexCoord(8, 9),
    # Row 10 - 3 hexes
    HexCoord(5, 10), HexCoord(6, 10), HexCoord(7, 10),
    # Row 11 - 1 hex (bottom)
    HexCoord(6, 11),
}


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
        """Get the hex coordinate in front of this facing (offset coordinates)."""
        parity = coord.q & 1  # 0 for even, 1 for odd
        
        if parity == 0:  # Even column
            directions = [
                HexCoord(0, -1),   # N
                HexCoord(1, -1),   # NE
                HexCoord(1, 0),    # SE
                HexCoord(0, 1),    # S
                HexCoord(-1, 0),   # SW
                HexCoord(-1, -1),  # NW
            ]
        else:  # Odd column
            directions = [
                HexCoord(0, -1),   # N
                HexCoord(1, 0),    # NE
                HexCoord(1, 1),    # SE
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
        """Convert hex coordinates to pixel coordinates (flat-top with horizontal rows)."""
        # Offset coordinates: odd columns (q) shift down by half hex height
        x = self.size * 3/2 * coord.q
        y = self.size * math.sqrt(3) * (coord.r + 0.5 * (coord.q & 1))
        return (x + self.offset_x, y + self.offset_y)
    
    def pixel_to_hex(self, x: float, y: float) -> HexCoord:
        """Convert pixel coordinates to hex coordinates (flat-top offset)."""
        # Adjust for offset
        x -= self.offset_x
        y -= self.offset_y
        
        # Convert to fractional offset coordinates
        q = (2.0 / 3.0 * x) / self.size
        r = (y - self.size * math.sqrt(3) / 2 * (int(q) & 1)) / (self.size * math.sqrt(3))
        
        # Round to nearest hex
        return HexCoord(round(q), round(r))
    
    def _round_hex(self, q: float, r: float) -> HexCoord:
        """Round fractional hex coordinates to nearest integer hex."""
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
        
        return HexCoord(rq, rr)
    
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
        """Check if hex coordinate is within grid bounds and valid for the mission."""
        # Check basic bounds
        if not (0 <= coord.q < self.cols and 0 <= coord.r < self.rows):
            return False
        
        # Check mission-specific valid hexes if provided
        if mission_hexes is not None:
            return coord in mission_hexes
        
        return True


# ====================
# GAME STATE
# ====================

class Game:
    """Main game state and logic."""
    
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Lone U-Boat - Mission 1")
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Load mission map
        self.map_image = self._load_mission_map(1)
        self.mission_hexes = MISSION_1_HEXES  # Valid hexes for this mission
        
        # Calculate map position to center it
        map_rect = self.map_image.get_rect()
        map_x = (SCREEN_WIDTH - map_rect.width) // 2
        map_y = 50  # Leave space at top for UI
        
        # Create hex grid overlay
        self.hex_grid = HexGrid(
            size=HEX_SIZE,
            cols=HEX_COLS,
            rows=HEX_ROWS,
            offset_x=505,  # Aligned with Mission 1 map
            offset_y=12
        )
        
        # Game entities
        self.u_boat = UBoat(
            position=HexCoord(6, 11),  # Starting position - bottom center
            facing=Facing.NORTH
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
        
        # Fonts
        self.font = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 36)
    
    def _load_mission_map(self, mission_num: int) -> pygame.Surface:
        """Load the mission map image."""
        map_path = Path(f"assets/maps/mission_{mission_num}.png")
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
                    if self.alignment_mode:
                        # Start dragging grid
                        self.dragging_grid = True
                        self.drag_start = pygame.mouse.get_pos()
                        self.grid_offset_start = (self.hex_grid.offset_x, self.hex_grid.offset_y)
                    else:
                        # Select hex
                        mouse_pos = pygame.mouse.get_pos()
                        hex_coord = self.hex_grid.pixel_to_hex(*mouse_pos)
                        if self.hex_grid.is_valid_hex(hex_coord, self.mission_hexes):
                            self.selected_hex = hex_coord
            
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.dragging_grid = False
            
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
        self.screen.fill((20, 20, 30))
        
        # Draw mission map
        if self.show_map:
            map_rect = self.map_image.get_rect()
            map_x = (SCREEN_WIDTH - map_rect.width) // 2
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
            self._render_hex_highlight(self.selected_hex, COLOR_SELECTION)
        
        # Draw UI
        self._render_ui()
        
        pygame.display.flip()
    
    def _render_hex_grid(self):
        """Render hex grid overlay."""
        surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        
        # Only render valid mission hexes
        for coord in self.mission_hexes:
            corners = self.hex_grid.get_hex_corners(coord)
            pygame.draw.polygon(surface, COLOR_HEX_GRID, corners, 1)
            
            # Add coordinate labels
            center = self.hex_grid.hex_to_pixel(coord)
            label = self.font.render(f"{coord.q},{coord.r}", True, (200, 200, 200))
            label_rect = label.get_rect(center=(int(center[0]), int(center[1])))
            surface.blit(label, label_rect)
        
        self.screen.blit(surface, (0, 0))
    
    def _render_hex_highlight(self, coord: HexCoord, color: Tuple[int, int, int, int]):
        """Highlight a specific hex."""
        surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        corners = self.hex_grid.get_hex_corners(coord)
        pygame.draw.polygon(surface, color, corners)
        self.screen.blit(surface, (0, 0))
    
    def _render_u_boat(self):
        """Render the U-boat."""
        center = self.hex_grid.hex_to_pixel(self.u_boat.position)
        
        # Draw circle for U-boat
        pygame.draw.circle(self.screen, COLOR_U_BOAT, 
                          (int(center[0]), int(center[1])), 20)
        
        # Draw facing indicator (triangle)
        angle_deg = 60 * self.u_boat.facing.value - 90  # Adjust for facing
        angle_rad = math.radians(angle_deg)
        tip_x = center[0] + 30 * math.cos(angle_rad)
        tip_y = center[1] + 30 * math.sin(angle_rad)
        
        left_angle = angle_rad + math.radians(140)
        left_x = center[0] + 15 * math.cos(left_angle)
        left_y = center[1] + 15 * math.sin(left_angle)
        
        right_angle = angle_rad - math.radians(140)
        right_x = center[0] + 15 * math.cos(right_angle)
        right_y = center[1] + 15 * math.sin(right_angle)
        
        pygame.draw.polygon(self.screen, (255, 255, 255),
                          [(tip_x, tip_y), (left_x, left_y), (right_x, right_y)])
    
    def _render_ship(self, ship: Ship):
        """Render an allied ship."""
        center = self.hex_grid.hex_to_pixel(ship.position)
        
        # Draw square for ship
        size = 15
        rect = pygame.Rect(center[0] - size, center[1] - size, size * 2, size * 2)
        pygame.draw.rect(self.screen, COLOR_SHIP, rect)
        
        # Draw border if damaged
        if ship.damaged:
            pygame.draw.rect(self.screen, (255, 0, 0), rect, 3)
    
    def _render_ui(self):
        """Render UI panels and information."""
        # Top bar
        ui_rect = pygame.Rect(0, 0, SCREEN_WIDTH, 40)
        pygame.draw.rect(self.screen, COLOR_PANEL_BG, ui_rect)
        
        # Title
        title = self.font_large.render("Mission 1: Supply Ship Attack", True, COLOR_TEXT)
        self.screen.blit(title, (10, 5))
        
        # Controls info
        if self.alignment_mode:
            controls = self.font.render(
                "ALIGNMENT MODE: Click-Drag to move | Arrows to nudge (Shift=10px) | A-Exit",
                True, (255, 255, 0)  # Yellow for alignment mode
            )
        else:
            controls = self.font.render(
                "Controls: Q/E-Rotate | W-Move | G-Toggle Grid | M-Toggle Map | A-Align Mode | ESC-Quit",
                True, COLOR_TEXT
            )
        self.screen.blit(controls, (10, SCREEN_HEIGHT - 30))
        
        # Show offset values in alignment mode
        if self.alignment_mode:
            offset_text = self.font.render(
                f"Offset X: {int(self.hex_grid.offset_x)} | Y: {int(self.hex_grid.offset_y)}",
                True, (255, 255, 0)
            )
            self.screen.blit(offset_text, (10, SCREEN_HEIGHT - 60))
        
        # Status panel (right side)
        panel_x = SCREEN_WIDTH - 250
        panel_y = 50
        
        status_texts = [
            f"Position: ({self.u_boat.position.q}, {self.u_boat.position.r})",
            f"Facing: {self.u_boat.facing.name}",
            f"Depth: {self.u_boat.depth.name}",
            f"Detection: {self.detection_level}",
            f"Hull Damage: {self.u_boat.hull_damage}/3",
        ]
        
        for i, text in enumerate(status_texts):
            rendered = self.font.render(text, True, COLOR_TEXT)
            self.screen.blit(rendered, (panel_x, panel_y + i * 25))
    
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
