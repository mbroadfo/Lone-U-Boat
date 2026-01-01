"""
Unified Game Screen - Single page with all game information.
Left: Mission briefing | Center: Game board | Right: Event log | Bottom: Controls
"""

import pygame
from typing import Optional, Any, List
from ..models import Facing, Depth
from .base_screen import BaseScreen


class UnifiedGameScreen(BaseScreen):
    """
    Unified game screen with all information visible.
    Replaces separate briefing, setup, and game screens.
    """
    
    def __init__(
        self,
        screen_manager: Any,
        config: Any,
        mission_number: int = 1,
        game_instance: Optional[Any] = None
    ):
        """
        Initialize the unified game screen.
        
        Args:
            screen_manager: Reference to ScreenManager
            config: Board configuration
            mission_number: Mission to play
            game_instance: Existing Game instance or None to create new
        """
        super().__init__(screen_manager, config)
        self.mission_number = mission_number
        
        # Import here to avoid circular dependency
        if game_instance is None:
            from ..game_state import Game
            self.game = Game(
                mission_number=mission_number,
                initial_depth=None,  # Will be set by player
                initial_facing=None,
                screen=self.screen  # Pass existing screen to avoid creating new display
            )
        else:
            self.game = game_instance
        
        # UI state
        self.awaiting_initial_setup = True  # Player needs to choose depth/facing
        self.selected_depth = Depth.SURFACED
        self.selected_facing = Facing.NORTH
        
        # Event log for play-by-play commentary
        self.event_log: List[str] = []
        self.add_event(f"Mission {mission_number} started")
        self.add_event("Select your starting depth and facing direction")
        
        # Load mission text for left panel
        self.mission_text = self._load_mission_text()
        
        # Panel scroll positions
        self.left_panel_scroll = 0
        self.right_panel_scroll = 0
    
    def _load_mission_text(self) -> str:
        """Load mission description from file."""
        mission_file = f'missions/M{self.mission_number}.txt'
        try:
            with open(mission_file, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return f"Mission {self.mission_number}"
    
    def add_event(self, message: str) -> None:
        """Add an event to the log."""
        self.event_log.append(message)
        # Auto-scroll to bottom
        self.right_panel_scroll = max(0, len(self.event_log) * 20 - 500)
    
    def handle_events(self, event: pygame.event.Event) -> None:
        """Handle all game events."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Return to main menu
                self.transition_to('menu')
            
            elif event.key == pygame.K_F11:
                # Toggle fullscreen via screen manager
                self.screen_manager.toggle_fullscreen()
                mode = "fullscreen" if self.screen_manager.fullscreen else "windowed"
                self.add_event(f"Switched to {mode} mode (F11 to toggle)")
            
            # If awaiting initial setup
            if self.awaiting_initial_setup:
                self._handle_setup_input(event)
            else:
                # Game is active - handle gameplay events
                # We'll integrate game events here in Phase 2
                pass
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.awaiting_initial_setup:
                # Handle setup clicks
                pass  # Will implement click handling
            else:
                # Handle game clicks
                pass
    
    def _handle_setup_input(self, event: pygame.event.Event) -> None:
        """Handle input during initial setup phase."""
        if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            # Confirm setup
            self.game.u_boat.depth = self.selected_depth
            self.game.u_boat.facing = self.selected_facing
            self.awaiting_initial_setup = False
            self.add_event(f"U-Boat positioned at {self.selected_depth.name}, facing {self.selected_facing.name}")
            self.add_event("Turn 1 - U-Boat Phase")
        
        # Depth selection
        elif event.key == pygame.K_1:
            self.selected_depth = Depth.SURFACED
        elif event.key == pygame.K_2:
            self.selected_depth = Depth.PERISCOPE
        elif event.key == pygame.K_3:
            self.selected_depth = Depth.MEDIUM
        elif event.key == pygame.K_4:
            self.selected_depth = Depth.DEEP
        
        # Facing selection
        elif event.key == pygame.K_q:
            self.selected_facing = self.selected_facing.rotate_counterclockwise()
        elif event.key == pygame.K_e:
            self.selected_facing = self.selected_facing.rotate_clockwise()
        elif event.key == pygame.K_w:
            self.selected_facing = Facing.NORTH
        elif event.key == pygame.K_s:
            self.selected_facing = Facing.SOUTH
        elif event.key == pygame.K_a:
            self.selected_facing = Facing.NORTHWEST
        elif event.key == pygame.K_d:
            self.selected_facing = Facing.NORTHEAST
    
    def update_screen(self, screen: pygame.Surface) -> None:
        """Update screen reference when display mode changes."""
        super().update_screen(screen)
        # Propagate to game components
        self.game.screen = screen
        self.game.renderer.screen = screen
    
    def update(self) -> None:
        """Update game state."""
        if not self.awaiting_initial_setup:
            self.game.update()
    
    def render(self) -> None:
        """Render the unified game screen."""
        # Clear screen
        self.screen.fill((10, 15, 25))
        
        # Get current screen dimensions (may change in fullscreen)
        screen_width = self.screen.get_width()
        screen_height = self.screen.get_height()
        
        # Calculate panel dimensions based on screen size
        left_width = self.config.LEFT_PANEL_WIDTH
        right_width = self.config.RIGHT_PANEL_WIDTH
        bottom_height = self.config.BOTTOM_PANEL_HEIGHT
        top_height = self.config.TOP_BAR_HEIGHT
        
        board_width = screen_width - left_width - right_width
        board_height = screen_height - top_height - bottom_height
        
        # Draw top bar
        self._draw_top_bar(screen_width, top_height)
        
        # Draw left panel (mission briefing)
        self._draw_left_panel(left_width, top_height, board_height + bottom_height)
        
        # Draw center (game board)
        self._draw_game_board(left_width, top_height, board_width, board_height)
        
        # Draw right panel (event log)
        self._draw_right_panel(left_width + board_width, top_height, right_width, board_height + bottom_height)
        
        # Draw bottom panel (controls)
        self._draw_bottom_panel(left_width, top_height + board_height, board_width, bottom_height)
        
        pygame.display.flip()
    
    def _draw_top_bar(self, width: int, height: int) -> None:
        """Draw the top title bar."""
        bar_rect = pygame.Rect(0, 0, width, height)
        pygame.draw.rect(self.screen, (25, 35, 50), bar_rect)
        pygame.draw.line(self.screen, (50, 70, 100), (0, height-1), (width, height-1), 2)
        
        # Title
        title = f"Mission {self.mission_number} - Turn {self.game.turn_number} - {self.game.current_phase.name.replace('_', ' ')}"
        self.draw_text(
            title,
            width // 2,
            height // 2,
            self.font_medium,
            color=(200, 220, 255),
            center=True
        )
        
        # Fullscreen hint
        self.draw_text(
            "F11: Fullscreen",
            width - 120,
            height // 2,
            self.font_small,
            color=(150, 170, 200),
            center=True
        )
        
        # ESC hint
        self.draw_text(
            "ESC: Menu",
            20,
            height // 2,
            self.font_small,
            color=(150, 170, 200)
        )
    
    def _draw_left_panel(self, width: int, y: int, height: int) -> None:
        """Draw the left panel with mission briefing."""
        panel_rect = pygame.Rect(0, y, width, height)
        pygame.draw.rect(self.screen, (20, 25, 35), panel_rect)
        pygame.draw.line(self.screen, (50, 70, 100), (width-1, y), (width-1, y+height), 2)
        
        # Header
        self.draw_text(
            "MISSION BRIEF",
            width // 2,
            y + 15,
            self.font_medium,
            color=(200, 220, 255),
            center=True
        )
        
        # Mission text (scrollable)
        text_y = y + 50
        text_x = 10
        text_width = width - 20
        
        lines = self.mission_text.split('\n')
        for line in lines[:30]:  # Show first 30 lines
            if not line.strip():
                text_y += 10
                continue
            
            # Word wrap
            words = line.split()
            current_line = ""
            for word in words:
                test_line = current_line + word + " "
                if self.font_small.size(test_line)[0] > text_width:
                    if current_line:
                        self.draw_text(current_line.strip(), text_x, text_y, self.font_small, color=(180, 190, 210))
                        text_y += 18
                    current_line = word + " "
                else:
                    current_line = test_line
            
            if current_line.strip():
                self.draw_text(current_line.strip(), text_x, text_y, self.font_small, color=(180, 190, 210))
                text_y += 18
            
            # Stop if running out of space
            if text_y > y + height - 20:
                break
    
    def _draw_game_board(self, x: int, y: int, width: int, height: int) -> None:
        """Draw the central game board."""
        board_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (15, 20, 30), board_rect)
        
        # Create a subsurface for the game to render to
        board_surface = self.screen.subsurface(board_rect)
        
        # Temporarily adjust game renderer for this viewport
        old_screen = self.game.screen
        self.game.screen = board_surface
        self.game.renderer.screen = board_surface
        
        # Render game (but only the essentials)
        if self.game.show_map and self.game.map_image:
            board_surface.blit(self.game.map_image, (0, 0))
        
        if self.game.show_grid:
            self.game.renderer.render_hex_grid(self.game.mission_hexes)
        
        if self.game.show_terrain:
            self.game.renderer.render_terrain_overlay(
                self.game.shallow_hexes, 
                self.game.land_hexes, 
                self.game.mission_hexes
            )
        
        # Render ships
        for ship in self.game.ships:
            self.game.renderer.render_ship(ship)
        
        # Render U-boat (use selected values if in setup)
        if self.awaiting_initial_setup:
            # Show preview with selected depth/facing
            temp_boat = self.game.u_boat
            temp_boat.depth = self.selected_depth
            temp_boat.facing = self.selected_facing
            self.game.renderer.render_u_boat(temp_boat)
        else:
            self.game.renderer.render_u_boat(self.game.u_boat)
        
        # Restore original screen
        self.game.screen = old_screen
        self.game.renderer.screen = old_screen
        
        # Draw border
        pygame.draw.rect(self.screen, (50, 70, 100), board_rect, 2)
    
    def _draw_right_panel(self, x: int, y: int, width: int, height: int) -> None:
        """Draw the right panel with event log."""
        panel_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (20, 25, 35), panel_rect)
        pygame.draw.line(self.screen, (50, 70, 100), (x, y), (x, y+height), 2)
        
        # Header
        self.draw_text(
            "EVENT LOG",
            x + width // 2,
            y + 15,
            self.font_medium,
            color=(200, 220, 255),
            center=True
        )
        
        # Event log entries
        log_y = y + 50
        log_x = x + 10
        log_width = width - 20
        
        # Show last N events that fit
        visible_events = self.event_log[-40:]  # Last 40 events
        for event_text in visible_events:
            # Word wrap
            words = event_text.split()
            current_line = ""
            for word in words:
                test_line = current_line + word + " "
                if self.font_small.size(test_line)[0] > log_width:
                    if current_line:
                        self.draw_text(current_line.strip(), log_x, log_y, self.font_small, color=(200, 210, 230))
                        log_y += 18
                    current_line = word + " "
                else:
                    current_line = test_line
            
            if current_line.strip():
                self.draw_text(current_line.strip(), log_x, log_y, self.font_small, color=(200, 210, 230))
                log_y += 18
            
            # Add small gap between events
            log_y += 5
            
            if log_y > y + height - 20:
                break
    
    def _draw_bottom_panel(self, x: int, y: int, width: int, height: int) -> None:
        """Draw the bottom control panel."""
        panel_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (25, 35, 50), panel_rect)
        pygame.draw.line(self.screen, (50, 70, 100), (x, y), (x+width, y), 2)
        
        if self.awaiting_initial_setup:
            self._draw_setup_controls(x, y, width, height)
        else:
            self._draw_game_controls(x, y, width, height)
    
    def _draw_setup_controls(self, x: int, y: int, width: int, height: int) -> None:
        """Draw initial setup controls."""
        self.draw_text(
            "INITIAL SETUP",
            x + width // 2,
            y + 15,
            self.font_large,
            color=(220, 220, 255),
            center=True
        )
        
        # Depth selection
        depth_y = y + 50
        self.draw_text(
            f"Depth [1-4]: {self.selected_depth.name}",
            x + 20,
            depth_y,
            self.font_medium,
            color=(200, 220, 255)
        )
        
        # Facing selection
        facing_y = y + 80
        self.draw_text(
            f"Facing [Q/E]: {self.selected_facing.name}",
            x + 20,
            facing_y,
            self.font_medium,
            color=(200, 220, 255)
        )
        
        # Confirm button hint
        self.draw_text(
            "Press ENTER to begin",
            x + width - 200,
            y + height // 2,
            self.font_medium,
            color=(100, 255, 100),
            center=True
        )
    
    def _draw_game_controls(self, x: int, y: int, width: int, height: int) -> None:
        """Draw normal game controls."""
        self.draw_text(
            "CONTROLS",
            x + width // 2,
            y + 15,
            self.font_large,
            color=(220, 220, 255),
            center=True
        )
        
        # Basic controls
        controls_y = y + 50
        control_x = x + 20
        
        controls = [
            "Q/E: Rotate | W: Move Forward | Z/X: Change Depth",
            "G: Toggle Grid | M: Toggle Map | V: Toggle Terrain"
        ]
        
        for control_text in controls:
            self.draw_text(
                control_text,
                control_x,
                controls_y,
                self.font_small,
                color=(180, 200, 220)
            )
            controls_y += 25
