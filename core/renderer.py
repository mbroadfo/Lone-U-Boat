"""
Game renderer - handles all pygame drawing operations.
Separated from game logic for cleaner architecture.
"""

import pygame
import math
from typing import Tuple, Set, Dict, Any, TYPE_CHECKING, Optional, List

from .models import HexCoord, UBoat, Ship, Facing, Depth

if TYPE_CHECKING:
    from .hex_grid import HexGrid
    from .board_layout import BoardLayoutRuntime


class GameRenderer:
    """Handles all rendering operations for the game."""
    
    def __init__(self, screen: pygame.Surface, config: Any, hex_grid: 'HexGrid', 
                 assets: Dict[str, Any], layout: Optional['BoardLayoutRuntime'] = None):
        """Initialize renderer with dependencies.
        
        Args:
            screen: Pygame display surface
            config: Configuration module (board_config)
            hex_grid: HexGrid instance for coordinate conversions
            assets: Dict containing loaded assets (images, fonts)
            layout: Optional BoardLayoutRuntime for resolution-independent positioning
        """
        self.screen = screen
        self.config = config
        self.hex_grid = hex_grid
        self.layout = layout
        
        # Unpack assets
        self.u_boat_images: Dict[Depth, pygame.Surface] = assets['u_boat_images']
        self.ship_images: Dict[str, pygame.Surface] = assets['ship_images']
        self.marker_images: Dict[str, pygame.Surface] = assets['marker_images']
        self.font: pygame.font.Font = assets['font']
        self.font_large: pygame.font.Font = assets['font_large']
    
    def update_layout(self, layout: 'BoardLayoutRuntime') -> None:
        """Update the layout engine (called after window resize).
        
        Args:
            layout: New BoardLayoutRuntime instance
        """
        self.layout = layout
    
    def render_frame(self, game_state: Any) -> None:
        """Render a complete frame.
        
        Args:
            game_state: Game instance with all state needed for rendering
        """
        self.screen.fill(self.config.COLORS['background'])
        
        # Draw mission map
        if game_state.show_map:
            self.render_map(game_state.map_image)
        
        # Draw hex grid overlay
        if game_state.show_grid:
            self.render_hex_grid(game_state.mission_hexes)
        
        # Draw terrain visualization (test mode)
        if game_state.show_terrain:
            self.render_terrain_overlay(
                game_state.shallow_hexes,
                game_state.land_hexes,
                game_state.mission_hexes
            )
            self.render_mission_markers(game_state.mission_config)
        
        # Draw ships
        for ship in game_state.ships:
            self.render_ship(ship)
        
        # Draw aircraft
        if hasattr(game_state, 'aircraft'):
            for aircraft in game_state.aircraft:
                self.render_aircraft(aircraft)
        
        # Draw U-boat
        self.render_u_boat(game_state.u_boat)
        
        # Draw selected hex
        if game_state.selected_hex:
            self.render_hex_highlight(game_state.selected_hex, self.config.COLORS['selection'])
        
        # Draw coordinate detection rectangle (editor mode)
        if hasattr(game_state, 'coord_detect_dragging') and game_state.coord_detect_dragging:
            if hasattr(game_state, 'coord_detect_start') and game_state.coord_detect_start:
                self.render_drag_rectangle(game_state.coord_detect_start)
        
        # Draw status box markers
        self.render_status_markers(
            game_state.status_boxes,
            game_state.show_all_markers if hasattr(game_state, 'show_all_markers') else False
        )
        
        # Draw UI
        self.render_ui(game_state)
        
        # Draw phase log overlay (for non-U-Boat phases)
        if hasattr(game_state, 'turn_manager'):
            self.render_phase_log(game_state)
        
        pygame.display.flip()
    
    def render_map(self, map_image: pygame.Surface) -> None:
        """Render the mission map background."""
        if self.layout:
            # Use layout engine for positioning and scaling
            rect = self.layout.board_rects.map_rect
            scaled = pygame.transform.smoothscale(map_image, (rect.width, rect.height))
            self.screen.blit(scaled, rect.topleft)
        else:
            # Legacy fallback
            map_rect = map_image.get_rect()
            map_x = (self.config.SCREEN_WIDTH - map_rect.width) // 2
            map_y = 50
            self.screen.blit(map_image, (map_x, map_y))
    
    def render_hex_grid(self, mission_hexes: Set[HexCoord]) -> None:
        """Render hex grid overlay with coordinates."""
        surface = pygame.Surface((self.config.SCREEN_WIDTH, self.config.SCREEN_HEIGHT), pygame.SRCALPHA)
        
        # Only render valid mission hexes
        for coord in mission_hexes:
            corners = self.hex_grid.get_hex_corners(coord)
            pygame.draw.polygon(surface, self.config.COLORS['hex_grid'], corners, 1)
            
            # Add coordinate labels
            center = self.hex_grid.hex_to_pixel(coord)
            label = self.font.render(f"{coord.q},{coord.r}", True, (200, 200, 200))
            label_rect = label.get_rect(center=(int(center[0]), int(center[1])))
            surface.blit(label, label_rect)
        
        self.screen.blit(surface, (0, 0))
    
    def render_terrain_overlay(self, shallow_hexes: Set[HexCoord], 
                               land_hexes: Set[HexCoord],
                               mission_hexes: Set[HexCoord]) -> None:
        """Render terrain type overlays for testing/visualization."""
        surface = pygame.Surface((self.config.SCREEN_WIDTH, self.config.SCREEN_HEIGHT), pygame.SRCALPHA)
        
        # Render shallow hexes (light blue)
        for coord in shallow_hexes:
            if coord in mission_hexes:
                corners = self.hex_grid.get_hex_corners(coord)
                pygame.draw.polygon(surface, (100, 200, 255, 100), corners)  # Light blue
                pygame.draw.polygon(surface, (100, 200, 255, 200), corners, 2)  # Border
        
        # Render land hexes (brown/tan)
        for coord in land_hexes:
            if coord in mission_hexes:
                corners = self.hex_grid.get_hex_corners(coord)
                pygame.draw.polygon(surface, (139, 90, 43, 150), corners)  # Brown
                pygame.draw.polygon(surface, (139, 90, 43, 255), corners, 3)  # Border
        
        self.screen.blit(surface, (0, 0))
    
    def render_mission_markers(self, mission_config: Any) -> None:
        """Render anchor and exit point markers for testing."""
        # Render anchor position (green circle)
        for anchor_coord in mission_config.ANCHOR_POSITIONS:
            hex_coord = HexCoord(*anchor_coord)
            center = self.hex_grid.hex_to_pixel(hex_coord)
            pygame.draw.circle(self.screen, (0, 255, 0), (int(center[0]), int(center[1])), 10)
            pygame.draw.circle(self.screen, (255, 255, 255), (int(center[0]), int(center[1])), 10, 2)
            # Label
            label = self.font.render("ANCHOR", True, (255, 255, 255))
            label_rect = label.get_rect(center=(int(center[0]), int(center[1]) - 20))
            self.screen.blit(label, label_rect)
        
        # Render U-Boat exit (yellow arrow)
        if 'u_boat' in mission_config.EXIT_POSITIONS:
            exit_data = mission_config.EXIT_POSITIONS['u_boat']
            hex_coord = HexCoord(*exit_data['position'])
            center = self.hex_grid.hex_to_pixel(hex_coord)
            # Draw directional arrow
            facing = Facing[exit_data['facing']]
            self.draw_exit_arrow(center, facing, (255, 255, 0))
            # Label
            label = self.font.render("U-EXIT", True, (255, 255, 255))
            label_rect = label.get_rect(center=(int(center[0]), int(center[1]) + 25))
            self.screen.blit(label, label_rect)
        
        # Render Merchant exit (red arrow)
        if 'merchant' in mission_config.EXIT_POSITIONS:
            exit_data = mission_config.EXIT_POSITIONS['merchant']
            hex_coord = HexCoord(*exit_data['position'])
            center = self.hex_grid.hex_to_pixel(hex_coord)
            # Draw directional arrow
            facing = Facing[exit_data['facing']]
            self.draw_exit_arrow(center, facing, (255, 0, 0))
            # Label
            label = self.font.render("M-EXIT", True, (255, 255, 255))
            label_rect = label.get_rect(center=(int(center[0]), int(center[1]) + 25))
            self.screen.blit(label, label_rect)
    
    def draw_exit_arrow(self, center: Tuple[float, float], facing: Facing, color: Tuple[int, int, int]) -> None:
        """Draw an arrow pointing in the exit direction."""
        # Arrow parameters
        arrow_length = 25
        arrow_width = 8
        
        # Calculate arrow direction based on facing (in degrees)
        # Rotate 90 degrees counter-clockwise to align with hex grid
        angle_deg = 60 * facing.value - 90
        angle_rad = math.radians(angle_deg)
        
        # Calculate arrow tip position
        tip_x = center[0] + arrow_length * math.cos(angle_rad)
        tip_y = center[1] + arrow_length * math.sin(angle_rad)
        
        # Calculate arrow base positions (perpendicular to direction)
        perp_angle = angle_rad + math.pi / 2
        base1_x = center[0] + arrow_width * math.cos(perp_angle)
        base1_y = center[1] + arrow_width * math.sin(perp_angle)
        base2_x = center[0] - arrow_width * math.cos(perp_angle)
        base2_y = center[1] - arrow_width * math.sin(perp_angle)
        
        # Draw arrow as triangle
        arrow_points = [
            (int(tip_x), int(tip_y)),
            (int(base1_x), int(base1_y)),
            (int(base2_x), int(base2_y))
        ]
        pygame.draw.polygon(self.screen, color, arrow_points)
        pygame.draw.polygon(self.screen, (0, 0, 0), arrow_points, 2)
    
    def render_hex_highlight(self, coord: HexCoord, color: Tuple[int, int, int] | Tuple[int, int, int, int]) -> None:
        """Highlight a specific hex."""
        surface = pygame.Surface((self.config.SCREEN_WIDTH, self.config.SCREEN_HEIGHT), pygame.SRCALPHA)
        corners = self.hex_grid.get_hex_corners(coord)
        # Ensure color has alpha channel
        if len(color) == 3:
            color_with_alpha = (*color, 255)
        else:
            color_with_alpha = color
        pygame.draw.polygon(surface, color_with_alpha, corners)
        self.screen.blit(surface, (0, 0))
    
    def render_u_boat(self, u_boat: UBoat, animated_pos: Optional[Tuple[float, float]] = None, 
                      animated_angle: Optional[float] = None) -> None:
        """Render the U-boat using depth-specific PNG images.
        
        Args:
            u_boat: UBoat instance to render
            animated_pos: Optional animated position as (q, r) floats for interpolation
            animated_angle: Optional animated angle in degrees for rotation
        """
        # Use animated position if provided, otherwise use actual position
        if animated_pos:
            center = self.hex_grid.hex_to_pixel_float(animated_pos[0], animated_pos[1])
        else:
            center = self.hex_grid.hex_to_pixel(u_boat.position)
        
        # Get the appropriate image for current depth
        image = self.u_boat_images.get(u_boat.depth)
        if image is None:
            return
        
        # Use animated angle if provided, otherwise use actual facing
        if animated_angle is not None:
            angle_deg = -animated_angle  # Negative for pygame rotation
        else:
            angle_deg = -60 * u_boat.facing.value
        
        rotated_image = pygame.transform.rotate(image, angle_deg)
        
        # Center the rotated image
        rect = rotated_image.get_rect(center=(int(center[0]), int(center[1])))
        self.screen.blit(rotated_image, rect)
        
        # If U-boat is destroyed, overlay destroyed icon
        if u_boat.hull_damage >= 4:
            destroyed_image = self.marker_images.get('destroyed')
            if destroyed_image:
                # Scale destroyed icon to fit inside hex (about 80% of hex size)
                target_size = int(self.hex_grid.size * 1.6)  # diameter = size * 2, use 80%
                scaled_destroyed = pygame.transform.scale(destroyed_image, (target_size, target_size))
                destroyed_rect = scaled_destroyed.get_rect(center=(int(center[0]), int(center[1])))
                self.screen.blit(scaled_destroyed, destroyed_rect)
    
    def render_ship(self, ship: Ship, destroyed_list: Optional[List[Dict[str, Any]]] = None,
                    animated_pos: Optional[Tuple[float, float]] = None,
                    animated_angle: Optional[float] = None) -> None:
        """Render an allied ship using PNG images.
        
        Args:
            ship: Ship instance to render
            destroyed_list: Optional list of destroyed entities this phase
            animated_pos: Optional animated position as (q, r) floats for interpolation
            animated_angle: Optional animated angle in degrees for rotation
        """
        # Use animated position if provided, otherwise use actual position
        if animated_pos:
            center = self.hex_grid.hex_to_pixel_float(animated_pos[0], animated_pos[1])
        else:
            center = self.hex_grid.hex_to_pixel(ship.position)
        
        # Get the appropriate image
        image_key = f"{ship.ship_type}_damaged" if ship.damaged else ship.ship_type
        image = self.ship_images.get(image_key)
        
        if image is None:
            # Fallback to colored square
            size = 15
            rect = pygame.Rect(center[0] - size, center[1] - size, size * 2, size * 2)
            pygame.draw.rect(self.screen, self.config.COLORS['ship'], rect)
            if ship.damaged:
                pygame.draw.rect(self.screen, (255, 0, 0), rect, 3)
            return
        
        # Use animated angle if provided, otherwise use actual facing
        if animated_angle is not None:
            angle_deg = -animated_angle  # Negative for pygame rotation
        else:
            angle_deg = -60 * ship.facing.value
        
        rotated_image = pygame.transform.rotate(image, angle_deg)
        
        # Center the rotated image
        rect = rotated_image.get_rect(center=(int(center[0]), int(center[1])))
        self.screen.blit(rotated_image, rect)
        
        # If ship is destroyed (check destroyed_list), overlay destroyed icon
        is_destroyed = False
        if destroyed_list:
            for destroyed in destroyed_list:
                if destroyed.get('position') == ship.position and destroyed.get('type') in ['merchant', 'corvette', 'destroyer']:
                    is_destroyed = True
                    break
        
        if is_destroyed:
            destroyed_image = self.marker_images.get('destroyed')
            if destroyed_image:
                # Scale destroyed icon to fit inside hex (about 80% of hex size)
                target_size = int(self.hex_grid.size * 1.6)  # diameter = size * 2, use 80%
                scaled_destroyed = pygame.transform.scale(destroyed_image, (target_size, target_size))
                destroyed_rect = scaled_destroyed.get_rect(center=(int(center[0]), int(center[1])))
                self.screen.blit(scaled_destroyed, destroyed_rect)
    
    def render_aircraft(self, aircraft: 'Aircraft', destroyed_list: Optional[List[Dict[str, Any]]] = None,
                       animated_pos: Optional[Tuple[float, float]] = None,
                       animated_angle: Optional[float] = None) -> None:
        """Render aircraft (B-24) using PNG image.
        
        Args:
            aircraft: Aircraft instance to render
            destroyed_list: Optional list of destroyed entities this phase
            animated_pos: Optional animated position as (q, r) floats for interpolation
            animated_angle: Optional animated angle in degrees for rotation
        """
        from .models import Aircraft
        
        # Use animated position if provided, otherwise use actual position
        if animated_pos:
            center = self.hex_grid.hex_to_pixel_float(animated_pos[0], animated_pos[1])
        else:
            center = self.hex_grid.hex_to_pixel(aircraft.position)
        
        # Get B-24 image
        image = self.ship_images.get('b24')
        
        if image is None:
            # Fallback to colored triangle
            size = 20
            points = [
                (center[0], center[1] - size),
                (center[0] - size, center[1] + size),
                (center[0] + size, center[1] + size)
            ]
            pygame.draw.polygon(self.screen, (100, 100, 255), points)
            return
        
        # Use animated angle if provided, otherwise use actual facing
        if animated_angle is not None:
            angle_deg = -animated_angle  # Negative for pygame rotation
        else:
            angle_deg = -60 * aircraft.facing.value
        
        rotated_image = pygame.transform.rotate(image, angle_deg)
        
        # Center the rotated image
        rect = rotated_image.get_rect(center=(int(center[0]), int(center[1])))
        self.screen.blit(rotated_image, rect)
        
        # If aircraft is destroyed (check destroyed_list), overlay destroyed icon
        is_destroyed = False
        if destroyed_list:
            for destroyed in destroyed_list:
                if destroyed.get('position') == aircraft.position and destroyed.get('type') == 'b24':
                    is_destroyed = True
                    break
        
        if is_destroyed:
            destroyed_image = self.marker_images.get('destroyed')
            if destroyed_image:
                # Scale destroyed icon to fit inside hex (about 80% of hex size)
                target_size = int(self.hex_grid.size * 1.6)  # diameter = size * 2, use 80%
                scaled_destroyed = pygame.transform.scale(destroyed_image, (target_size, target_size))
                destroyed_rect = scaled_destroyed.get_rect(center=(int(center[0]), int(center[1])))
                self.screen.blit(scaled_destroyed, destroyed_rect)
    
    def render_drag_rectangle(self, start_pos: Tuple[int, int]) -> None:
        """Render drag rectangle for coordinate detection (editor mode)."""
        mouse_pos = pygame.mouse.get_pos()
        x1, y1 = start_pos
        x2, y2 = mouse_pos
        
        # Calculate rectangle
        left = min(x1, x2)
        top = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        
        # Draw semi-transparent rectangle
        surface = pygame.Surface((self.config.SCREEN_WIDTH, self.config.SCREEN_HEIGHT), pygame.SRCALPHA)
        rect = pygame.Rect(left, top, width, height)
        pygame.draw.rect(surface, (255, 255, 0, 100), rect)  # Yellow with transparency
        pygame.draw.rect(surface, (255, 255, 0, 255), rect, 2)  # Yellow border
        self.screen.blit(surface, (0, 0))
    
    def render_status_markers(self, status_boxes: Dict[str, Dict[str, Any]], show_all: bool = False, scale: float = 1.0) -> None:
        """Render status box markers based on game state.
        
        Args:
            status_boxes: Dictionary of status box configurations
            show_all: If True, render all markers regardless of conditions
            scale: Legacy parameter, ignored when using layout engine
        """
        for _box_name, box_data in status_boxes.items():
            marker_type = box_data['marker_type']
            condition = box_data.get('condition', True)
            
            # In show all markers mode, always render
            if show_all:
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
            
            # Use layout engine if available, otherwise fall back to legacy scaling
            if self.layout and _box_name in self.layout.status_box_rects:
                adjusted_rect = self.layout.status_box_rects[_box_name]
            else:
                # Legacy fallback
                rect = box_data['rect']
                adjusted_rect = pygame.Rect(
                    int(rect[0] * scale) + self.global_offset_x,
                    int(rect[1] * scale) + self.global_offset_y,
                    int(rect[2] * scale),
                    int(rect[3] * scale)
                )
            
            # Get marker image
            marker_img = self.marker_images.get(marker_type)
            if marker_img is None:
                continue
            
            # Scale marker to fit box
            scaled_marker = pygame.transform.smoothscale(marker_img, (adjusted_rect.width, adjusted_rect.height))
            self.screen.blit(scaled_marker, adjusted_rect)
    
    def render_ui(self, game_state: Any) -> None:
        """Render UI panels and information."""
        # Top bar with turn info
        ui_rect = pygame.Rect(0, 0, self.config.SCREEN_WIDTH, self.config.UI['top_bar_height'])
        pygame.draw.rect(self.screen, self.config.COLORS['panel_bg'], ui_rect)
        
        # Title
        title_text = f"{game_state.mission_config.MISSION_INFO['name']}"
        title = self.font_large.render(title_text, True, self.config.COLORS['text'])
        self.screen.blit(title, (10, 5))
        
        # Turn info (if turn manager exists)
        if hasattr(game_state, 'turn_manager'):
            self.render_turn_info(game_state)
        
        # Controls info
        if hasattr(game_state, 'alignment_mode') and game_state.alignment_mode:
            controls = self.font.render(
                "EDIT MODE: Click-Drag | Arrows | Shift+Click-Add | Ctrl+Click-Remove | P-Print | ESC-Quit",
                True, (255, 255, 0)  # Yellow for edit mode
            )
        else:
            controls = self.font.render(
                "SPACE-Next Phase | G-Grid | M-Map | V-Terrain | S-Status | F2-Align | ESC-Quit",
                True, self.config.COLORS['text']
            )
        self.screen.blit(controls, (10, self.config.SCREEN_HEIGHT - 30))
        
        # Stack additional info text vertically (starting from bottom up)
        info_y_position = self.config.SCREEN_HEIGHT - 60
        
        # Show marker mode indicator
        if hasattr(game_state, 'show_all_markers') and game_state.show_all_markers:
            marker_mode_text = self.font.render(
                "ALL MARKERS VISIBLE (Press S to toggle)",
                True, (255, 255, 0)
            )
            self.screen.blit(marker_mode_text, (10, info_y_position))
            info_y_position -= 30  # Move up for next line
        
        # Show offset values in alignment mode
        if hasattr(game_state, 'alignment_mode') and game_state.alignment_mode:
            offset_text = self.font.render(
                f"Offset X: {int(self.hex_grid.offset_x)} | Y: {int(self.hex_grid.offset_y)}",
                True, (255, 255, 0)
            )
            self.screen.blit(offset_text, (10, info_y_position))
        
        # Status panel (right side)
        panel_x = self.config.UI['status_panel_x']
        panel_y = self.config.UI['status_panel_y']
        
        status_texts = [
            (f"Position: ({game_state.u_boat.position.q}, {game_state.u_boat.position.r})", self.config.COLORS['text']),
            (f"Facing: {game_state.u_boat.facing.name}", self.config.COLORS['text']),
        ]
        
        for i, (text, color) in enumerate(status_texts):
            rendered = self.font.render(text, True, color)
            self.screen.blit(rendered, (panel_x, panel_y + i * 25))    
    def render_alignment_highlights(self, alignment_target: str, selected_status_box: str | None) -> None:
        """Render visual highlights for alignment mode.
        
        Args:
            alignment_target: Current alignment target ('grid' or 'status_boxes')
            selected_status_box: Name of selected status box, if any
        """
        if not self.layout:
            return
        
        # Highlight selected status box
        if alignment_target == 'status_boxes' and selected_status_box and selected_status_box in self.layout.status_box_rects:
            rect = self.layout.status_box_rects[selected_status_box]
            # Draw yellow border around selected box
            pygame.draw.rect(self.screen, (255, 255, 0), rect, 3)
            # Draw corner handles
            handle_size = 6
            for corner in [(rect.left, rect.top), (rect.right, rect.top), 
                          (rect.left, rect.bottom), (rect.right, rect.bottom)]:
                handle_rect = pygame.Rect(corner[0] - handle_size//2, corner[1] - handle_size//2, 
                                         handle_size, handle_size)
                pygame.draw.rect(self.screen, (255, 255, 0), handle_rect)
        
        # Draw all status box outlines in alignment mode
        if alignment_target == 'status_boxes':
            for name, rect in self.layout.status_box_rects.items():
                if name != selected_status_box:
                    # Draw cyan outline for unselected boxes
                    pygame.draw.rect(self.screen, (0, 255, 255, 128), rect, 1)
    
    def render_debug_overlay(self, layout: 'BoardLayoutRuntime', selected_status_box: str | None) -> None:
        """Render debug information overlay for alignment mode.
        
        Args:
            layout: Current layout runtime
            selected_status_box: Name of selected status box, if any
        """
        if not layout:
            return
        
        # Semi-transparent background panel positioned on the board area
        panel_width = 220
        panel_height = 140
        # Position halfway between map edge and right side
        map_rect = layout.board_rects.map_rect
        panel_x = map_rect.right + 10
        panel_y = map_rect.top + 10
        
        surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(surface, (0, 0, 0, 200), (0, 0, panel_width, panel_height))
        pygame.draw.rect(surface, (100, 150, 200), (0, 0, panel_width, panel_height), 2)
        
        # Debug info text
        info_lines = [
            f"Screen: {layout.screen_w}x{layout.screen_h}",
            f"Scale: {layout.scale:.3f}x",
            f"Hex Size: {layout.hex_size:.1f}",
            f"Hex Origin: ({int(layout.hex_origin_screen[0])}, {int(layout.hex_origin_screen[1])})",
            f"Map Rect: {layout.board_rects.map_rect.topleft}",
        ]
        
        if selected_status_box and selected_status_box in layout.status_box_rects:
            rect = layout.status_box_rects[selected_status_box]
            info_lines.append(f"Selected: {selected_status_box}")
            info_lines.append(f"  Pos: ({rect.x}, {rect.y})")
            info_lines.append(f"  Size: {rect.width}x{rect.height}")
        
        y_offset = 10
        for line in info_lines:
            text = self.font.render(line, True, (255, 255, 255))
            surface.blit(text, (10, y_offset))
            y_offset += 20
        
        self.screen.blit(surface, (panel_x, panel_y))
    
    def render_turn_info(self, game_state: Any) -> None:
        """Render turn number, phase, and AP counter in top-right."""
        turn_mgr = game_state.turn_manager
        
        # Build info string
        phase_name = turn_mgr.get_current_phase_name()
        turn_text = f"Turn {turn_mgr.turn_number}"
        
        # AP info (only show in U-Boat phase)
        if turn_mgr.ap_tracker and turn_mgr.current_phase.name == 'UBOAT_PHASE':
            ap_text = f"AP: {turn_mgr.ap_tracker.remaining()}/{turn_mgr.ap_tracker.total_ap}"
        else:
            ap_text = ""
        
        # Render text right-aligned
        x_right = self.config.SCREEN_WIDTH - 20
        y_pos = 8
        
        # Turn number
        turn_surface = self.font_large.render(turn_text, True, self.config.COLORS['text'])
        turn_rect = turn_surface.get_rect()
        turn_rect.topright = (x_right, y_pos)
        self.screen.blit(turn_surface, turn_rect)
        
        # Phase name
        phase_color = self._get_phase_color(turn_mgr.current_phase)
        phase_surface = self.font.render(phase_name, True, phase_color)
        phase_rect = phase_surface.get_rect()
        phase_rect.topright = (x_right, y_pos + 30)
        self.screen.blit(phase_surface, phase_rect)
        
        # AP counter
        if ap_text:
            ap_surface = self.font.render(ap_text, True, (100, 255, 100))
            ap_rect = ap_surface.get_rect()
            ap_rect.topright = (x_right, y_pos + 52)
            self.screen.blit(ap_surface, ap_rect)
    
    def _get_phase_color(self, phase) -> Tuple[int, int, int]:
        """Get color for phase display."""
        from .models import GamePhase
        
        colors = {
            GamePhase.UBOAT_PHASE: (100, 255, 100),  # Green (player active)
            GamePhase.MERCHANT_PHASE: (200, 200, 100),  # Yellow
            GamePhase.DETECTION_PHASE: (255, 150, 100),  # Orange
            GamePhase.ESCORT_PHASE: (255, 100, 100),  # Red (enemy active)
            GamePhase.B24_PHASE: (150, 150, 255),  # Blue
            GamePhase.END_TURN_PHASE: (150, 150, 150),  # Gray
        }
        return colors.get(phase, (255, 255, 255))
    
    def render_phase_log(self, game_state: Any) -> None:
        """Render phase execution log (for non-U-Boat phases)."""
        turn_mgr = game_state.turn_manager
        phase_name = turn_mgr.get_current_phase_name()
        
        # Only show log for non-U-Boat phases
        if turn_mgr.current_phase.name == 'UBOAT_PHASE':
            return
        
        log_entries = turn_mgr.get_phase_log(phase_name)
        if not log_entries:
            return
        
        # Create log panel (center of screen)
        panel_width = 500
        panel_height = min(300, 50 + len(log_entries) * 25)
        panel_x = (self.config.SCREEN_WIDTH - panel_width) // 2
        panel_y = (self.config.SCREEN_HEIGHT - panel_height) // 2
        
        # Background
        surface = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(surface, (0, 0, 0, 230), (0, 0, panel_width, panel_height))
        pygame.draw.rect(surface, self._get_phase_color(turn_mgr.current_phase), 
                        (0, 0, panel_width, panel_height), 3)
        
        # Title
        title = self.font_large.render(phase_name, True, (255, 255, 255))
        surface.blit(title, (10, 10))
        
        # Log entries
        y_offset = 45
        for entry in log_entries:
            text = self.font.render(f"• {entry}", True, (220, 220, 220))
            surface.blit(text, (15, y_offset))
            y_offset += 25
        
        # Continue prompt
        prompt = self.font.render("[SPACE] Continue", True, (255, 255, 100))
        prompt_rect = prompt.get_rect()
        prompt_rect.bottomright = (panel_width - 15, panel_height - 10)
        surface.blit(prompt, prompt_rect)
        
        self.screen.blit(surface, (panel_x, panel_y))