"""
Unified Game Screen - Single page with all game information.
Left: Mission briefing | Center: Game board | Right: Event log | Bottom: Controls
"""

import pygame
import sys
from typing import Optional, Any, List, Dict
from ..models import Facing, Depth, GamePhase
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
        
        # Dice roll history
        self.dice_rolls: List[Dict[str, Any]] = []
        
        # Load mission rules for left panel display
        self.mission_rules: Any = None
        self.mission_rules_view: Any = None
        try:
            sys.path.insert(0, 'missions')
            from mission_rules_loader import load_mission_rules, create_mission_rules_view_model  # type: ignore[import-not-found]
            self.mission_rules = load_mission_rules(mission_number)
            self.mission_rules_view = create_mission_rules_view_model(self.mission_rules, 1)
        except Exception as e:
            print(f"Warning: Could not load mission rules: {e}")
        
        # Mission Rules panel state
        self.expanded_phases = {1: True, 2: False, 3: False, 4: False, 5: False, 6: False}  # Phase 1 expanded by default
        self.phase_header_rects = {}  # Store clickable regions for phase headers
        
        # Panel scroll positions
        self.left_panel_scroll = 0
        self.right_panel_scroll = 0
    
    def add_event(self, message: str) -> None:
        """Add an event to the log."""
        self.event_log.append(message)
        # Auto-scroll to bottom
        self.right_panel_scroll = max(0, len(self.event_log) * 20 - 500)
    
    def add_dice_roll(self, action: str, dice: str, result: str) -> None:
        """Add a dice roll to the history."""
        self.dice_rolls.append({
            'action': action,
            'dice': dice,
            'result': result
        })
        # Also add to event log
        self.add_event(f"{action}: Rolled {dice} = {result}")
    
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
            
            # Toggle display options (work in both setup and game modes)
            elif event.key == pygame.K_g:
                self.game.show_grid = not self.game.show_grid
                state = "ON" if self.game.show_grid else "OFF"
                self.add_event(f"Hex grid: {state}")
            
            elif event.key == pygame.K_m:
                self.game.show_map = not self.game.show_map
                state = "ON" if self.game.show_map else "OFF"
                self.add_event(f"Map display: {state}")
            
            elif event.key == pygame.K_v:
                self.game.show_terrain = not self.game.show_terrain
                state = "ON" if self.game.show_terrain else "OFF"
                self.add_event(f"Terrain overlay: {state}")
            
            elif event.key == pygame.K_s:
                self.game.show_status_boxes = not self.game.show_status_boxes
                state = "ON" if self.game.show_status_boxes else "OFF"
                self.add_event(f"Status boxes: {state}")
            
            # If awaiting initial setup
            if self.awaiting_initial_setup:
                self._handle_setup_input(event)
            else:
                # Game is active - handle gameplay events
                # We'll integrate game events here in Phase 2
                pass
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                mouse_pos = event.pos
                
                # Check if clicking on a phase header in left panel
                for phase_num, rect in self.phase_header_rects.items():
                    if rect.collidepoint(mouse_pos):
                        # Toggle expansion
                        self.expanded_phases[phase_num] = not self.expanded_phases[phase_num]
                        break
                
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
            old_phase = self.game.current_phase
            self.game.update()
            
            # Update mission rules view if phase changed
            if self.mission_rules and old_phase != self.game.current_phase:
                try:
                    sys.path.insert(0, 'missions')
                    from mission_rules_loader import create_mission_rules_view_model  # type: ignore[import-not-found]
                    # Map GamePhase enum to phase number (3->1, 4->2, etc.)
                    phase_map = {3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6}
                    current_phase_num = phase_map.get(self.game.current_phase.value, 1)
                    self.mission_rules_view = create_mission_rules_view_model(self.mission_rules, current_phase_num)
                    
                    # Auto-expand the current phase
                    for phase_num in range(1, 7):
                        self.expanded_phases[phase_num] = (phase_num == current_phase_num)
                except Exception as e:
                    print(f"Warning: Could not update mission rules view: {e}")
    
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
        """Draw the left panel with mission rules."""
        panel_rect = pygame.Rect(0, y, width, height)
        pygame.draw.rect(self.screen, (20, 25, 35), panel_rect)
        pygame.draw.line(self.screen, (50, 70, 100), (width-1, y), (width-1, y+height), 2)
        
        if not self.mission_rules_view:
            # Fallback if rules couldn't load
            self.draw_text(
                "MISSION RULES",
                width // 2,
                y + 15,
                self.font_medium,
                color=(200, 220, 255),
                center=True
            )
            self.draw_text(
                "Rules could not be loaded",
                10,
                y + 50,
                self.font_small,
                color=(150, 150, 150)
            )
            return
        
        # Clear phase header rects for click detection
        self.phase_header_rects.clear()
        
        mission_info = self.mission_rules_view["mission_info"]
        phases = self.mission_rules_view["phases"]
        
        text_x = 10
        text_y = y + 10
        text_width = width - 20
        
        # === MISSION HEADER ===
        # Mission title
        title_text = f"MISSION {mission_info['number']}"
        self.draw_text(
            title_text,
            width // 2,
            text_y,
            self.font_medium,
            color=(255, 220, 100),
            center=True
        )
        text_y += 25
        
        # Mission name
        name_lines = self._wrap_text(mission_info['title'], text_width, self.font_small)
        for line in name_lines:
            self.draw_text(
                line,
                width // 2,
                text_y,
                self.font_small,
                color=(200, 220, 255),
                center=True
            )
            text_y += 16
        
        text_y += 5
        
        # Objective
        self.draw_text(
            "OBJECTIVE:",
            text_x,
            text_y,
            self.font_small,
            color=(180, 200, 220)
        )
        text_y += 18
        
        objective_lines = self._wrap_text(mission_info['objective'], text_width, self.font_small)
        for line in objective_lines[:3]:  # Limit to 3 lines to save space
            self.draw_text(
                line,
                text_x,
                text_y,
                self.font_small,
                color=(160, 180, 200)
            )
            text_y += 16
        
        # Divider
        text_y += 5
        pygame.draw.line(
            self.screen,
            (70, 90, 120),
            (text_x, text_y),
            (width - text_x, text_y),
            1
        )
        text_y += 10
        
        # === PHASE SECTIONS ===
        for phase_data in phases:
            phase_num = phase_data["phase_number"]
            phase_name = phase_data["phase_name"]
            is_active = phase_data["is_active"]
            is_expanded = self.expanded_phases.get(phase_num, False)
            sections = phase_data["sections"]
            
            # Phase header
            header_height = 22
            header_rect = pygame.Rect(0, text_y, width, header_height)
            
            # Background color for active phase
            if is_active:
                pygame.draw.rect(self.screen, (40, 60, 90), header_rect)
            else:
                pygame.draw.rect(self.screen, (25, 30, 40), header_rect)
            
            # Store rect for click detection
            self.phase_header_rects[phase_num] = header_rect
            
            # Expand/collapse indicator
            indicator = "▼" if is_expanded else "▶"
            self.draw_text(
                indicator,
                text_x,
                text_y + 3,
                self.font_small,
                color=(180, 200, 220)
            )
            
            # Phase name
            phase_label = f"Phase {phase_num} - {phase_name}"
            label_color = (255, 255, 150) if is_active else (180, 200, 220)
            self.draw_text(
                phase_label,
                text_x + 20,
                text_y + 3,
                self.font_small,
                color=label_color
            )
            
            # Border
            border_color = (100, 140, 180) if is_active else (50, 70, 100)
            pygame.draw.rect(self.screen, border_color, header_rect, 1)
            
            text_y += header_height + 2
            
            # Phase content (if expanded)
            if is_expanded and sections:
                content_y = text_y
                
                for section in sections:
                    section_title = section.get("title", "")
                    section_type = section.get("type", "bullets")
                    content = section.get("content", [])
                    
                    # Section title
                    self.draw_text(
                        section_title,
                        text_x + 5,
                        content_y,
                        self.font_small,
                        color=(200, 220, 150)
                    )
                    content_y += 16
                    
                    # Section content
                    if section_type == "bullets":
                        for line in content[:8]:  # Limit bullets to avoid overflow
                            # Wrap long lines
                            wrapped = self._wrap_text(f"• {line}", text_width - 10, self.font_small)
                            for wrapped_line in wrapped[:2]:  # Max 2 lines per bullet
                                self.draw_text(
                                    wrapped_line,
                                    text_x + 10,
                                    content_y,
                                    self.font_small,
                                    color=(170, 185, 200)
                                )
                                content_y += 14
                    
                    elif section_type == "table":
                        # Table headers
                        headers = section.get("headers", [])
                        rows = section.get("rows", [])
                        
                        # Calculate column widths
                        col_width = (text_width - 80) // len(headers) if headers else 30
                        
                        # Header row
                        header_x = text_x + 80
                        for header in headers:
                            self.draw_text(
                                header,
                                header_x,
                                content_y,
                                self.font_small,
                                color=(200, 220, 150)
                            )
                            header_x += col_width
                        content_y += 14
                        
                        # Table rows
                        for row in rows[:6]:  # Limit rows
                            # Action name
                            action_name = row.get("action", "")
                            self.draw_text(
                                action_name[:10],  # Truncate if needed
                                text_x + 10,
                                content_y,
                                self.font_small,
                                color=(170, 185, 200)
                            )
                            
                            # Costs
                            costs_x = text_x + 80
                            for cost in row.get("costs", []):
                                self.draw_text(
                                    cost,
                                    costs_x,
                                    content_y,
                                    self.font_small,
                                    color=(170, 185, 200)
                                )
                                costs_x += col_width
                            content_y += 14
                    
                    content_y += 5  # Gap between sections
                    
                    # Check if we're running out of space
                    if content_y > y + height - 30:
                        break
                
                text_y = content_y + 5
            
            # Check if we need to stop (running out of space)
            if text_y > y + height - 30:
                break
    
    def _wrap_text(self, text: str, max_width: int, font: pygame.font.Font) -> List[str]:
        """
        Wrap text to fit within max_width.
        
        Args:
            text: Text to wrap
            max_width: Maximum width in pixels
            font: Font to use for measuring
            
        Returns:
            List of wrapped lines
        """
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + word + " "
            if font.size(test_line)[0] > max_width:
                if current_line:
                    lines.append(current_line.strip())
                    current_line = word + " "
                else:
                    # Single word is too long
                    lines.append(word)
                    current_line = ""
            else:
                current_line = test_line
        
        if current_line.strip():
            lines.append(current_line.strip())
        
        return lines
    
    def _draw_game_board(self, x: int, y: int, width: int, height: int) -> None:
        """Draw the central game board."""
        board_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (15, 20, 30), board_rect)
        
        # Render directly to main screen (not subsurface) to preserve alignment
        old_clip = self.screen.get_clip()
        self.screen.set_clip(board_rect)
        
        # Calculate map position (centered horizontally in board area)
        map_x_offset = 0
        if self.game.map_image:
            map_x_offset = (width - self.game.map_image.get_width()) // 2
        
        # Actual map position on screen
        actual_map_x = x + map_x_offset
        actual_map_y = y
        
        # Calculate offset adjustment: difference between actual position and calibration position
        # Calibration was done with map at a specific board position
        cal_board_x = self.config.CALIBRATION_MAP_POSITION['board_x']
        cal_board_y = self.config.CALIBRATION_MAP_POSITION['board_y']
        cal_board_width = self.config.CALIBRATION_MAP_POSITION['board_width']
        
        if self.game.map_image:
            cal_map_x_offset = (cal_board_width - self.game.map_image.get_width()) // 2
        else:
            cal_map_x_offset = 0
            
        cal_map_x = cal_board_x + cal_map_x_offset
        cal_map_y = cal_board_y
        
        # Adjust hex grid and renderer for current vs calibration position
        adjustment_x = actual_map_x - cal_map_x
        adjustment_y = actual_map_y - cal_map_y
        
        # Temporarily adjust global offsets for this render
        original_global_x = self.game.hex_grid.global_offset_x
        original_global_y = self.game.hex_grid.global_offset_y
        original_renderer_x = self.game.renderer.global_offset_x
        original_renderer_y = self.game.renderer.global_offset_y
        
        self.game.hex_grid.global_offset_x = original_global_x + adjustment_x
        self.game.hex_grid.global_offset_y = original_global_y + adjustment_y
        self.game.renderer.global_offset_x = original_renderer_x + adjustment_x
        self.game.renderer.global_offset_y = original_renderer_y + adjustment_y
        
        # Render game at board position, center map horizontally
        if self.game.show_map and self.game.map_image:
            self.screen.blit(self.game.map_image, (actual_map_x, actual_map_y))
        
        if self.game.show_grid:
            self.game.renderer.render_hex_grid(self.game.mission_hexes)
        
        if self.game.show_terrain:
            self.game.renderer.render_terrain_overlay(
                self.game.shallow_hexes, 
                self.game.land_hexes, 
                self.game.mission_hexes
            )
        
        # Render status boxes and torpedoes (if enabled)
        if self.game.show_status_boxes:
            self.game.renderer.render_status_markers(self.game.status_boxes, show_all=True)
        
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
        
        # Restore original offsets
        self.game.hex_grid.global_offset_x = original_global_x
        self.game.hex_grid.global_offset_y = original_global_y
        self.game.renderer.global_offset_x = original_renderer_x
        self.game.renderer.global_offset_y = original_renderer_y
        
        # Restore clip region
        self.screen.set_clip(old_clip)
        
        # Draw border
        pygame.draw.rect(self.screen, (50, 70, 100), board_rect, 2)
    
    def _draw_right_panel(self, x: int, y: int, width: int, height: int) -> None:
        """Draw the right panel with dice rolls and event log."""
        panel_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (20, 25, 35), panel_rect)
        pygame.draw.line(self.screen, (50, 70, 100), (x, y), (x, y+height), 2)
        
        # Split panel into dice area and event log
        dice_area_height = 150
        log_area_y = y + dice_area_height
        
        # === DICE ROLL SECTION ===
        self.draw_text(
            "DICE ROLLS",
            x + width // 2,
            y + 15,
            self.font_medium,
            color=(255, 220, 100),
            center=True
        )
        
        # Show last 5 dice rolls
        dice_y = y + 45
        dice_x = x + 10
        
        visible_rolls = self.dice_rolls[-5:] if self.dice_rolls else []
        if visible_rolls:
            for roll_info in visible_rolls:
                action = roll_info.get('action', 'Unknown')
                dice = roll_info.get('dice', '?')
                result = roll_info.get('result', '?')
                
                roll_text = f"{action}: [{dice}] = {result}"
                self.draw_text(roll_text, dice_x, dice_y, self.font_small, color=(255, 255, 150))
                dice_y += 20
        else:
            self.draw_text("No rolls yet", dice_x, dice_y, self.font_small, color=(120, 120, 120))
        
        # Separator line
        pygame.draw.line(
            self.screen,
            (50, 70, 100),
            (x, log_area_y),
            (x + width, log_area_y),
            2
        )
        
        # === EVENT LOG SECTION ===
        self.draw_text(
            "EVENT LOG",
            x + width // 2,
            log_area_y + 15,
            self.font_medium,
            color=(200, 220, 255),
            center=True
        )
        
        # Event log entries
        log_y = log_area_y + 50
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
            "G: Toggle Grid | M: Toggle Map | V: Toggle Terrain",
            "S: Toggle Status/Torps"
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
