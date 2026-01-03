"""
Unified Game Screen - Single page with all game information.
Left: Mission briefing | Center: Game board | Right: Event log | Bottom: Controls
"""

import pygame
import sys
from typing import Optional, Any, List, Dict
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
        
        # Dice roll history
        self.dice_rolls: List[Dict[str, Any]] = []
        
        # Load mission rules for left panel display
        self.mission_rules: Any = None
        self.mission_rules_view: Any = None
        try:
            sys.path.insert(0, 'missions')
            from mission_rules_loader import load_mission_rules, create_mission_rules_view_model  # type: ignore[import-not-found]
            self.mission_rules = load_mission_rules(mission_number)
            self.mission_rules_view = create_mission_rules_view_model(self.mission_rules, 1)  # type: ignore[reportUnknownMemberType]
        except Exception as e:
            print(f"Warning: Could not load mission rules: {e}")
        
        # Mission Rules panel state
        self.expanded_phases = {1: True, 2: False, 3: False, 4: False, 5: False, 6: False}  # Phase 1 expanded by default
        self.phase_header_rects: Dict[int, pygame.Rect] = {}  # Store clickable regions for phase headers
        
        # Panel scroll positions
        self.left_panel_scroll = 0
        self.right_panel_scroll = 0
        
        # Alignment mode (for editor functionality)
        self.alignment_mode = False
        self.alignment_target = 'grid'  # 'grid' or 'status_boxes'
        self.selected_status_box: Optional[str] = None
        
        # Cache board rect to avoid recomputing layout every frame
        self.cached_board_rect: Optional[pygame.Rect] = None
    
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
            
            elif event.key == pygame.K_F2:
                # Toggle alignment mode (editor)
                self.alignment_mode = not self.alignment_mode
                if self.alignment_mode:
                    self.add_event("ALIGNMENT MODE: Use arrow keys to adjust grid/boxes")
                    self.add_event("Tab: Switch grid/status | Click: Select box | P: Print | L: Save")
                    self.game.show_grid = True
                    self.game.show_map = True
                else:
                    self.add_event("Alignment mode OFF")
            
            # Alignment mode controls
            elif self.alignment_mode:
                self._handle_alignment_input(event)
            
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
                
                # Handle alignment mode clicks
                if self.alignment_mode:
                    self.handle_mouse_click_alignment(mouse_pos)
                
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
    
    def _handle_alignment_input(self, event: pygame.event.Event) -> None:
        """Handle input during alignment mode (editor)."""
        # Check modifiers
        shift_pressed = pygame.key.get_mods() & pygame.KMOD_SHIFT
        delta_map = 10.0 if shift_pressed else 1.0  # Movement delta in map pixels
        
        if event.key == pygame.K_TAB:
            # Switch between grid and status box alignment
            self.alignment_target = 'status_boxes' if self.alignment_target == 'grid' else 'grid'
            if self.alignment_target == 'status_boxes':
                self.add_event("Status boxes mode: Arrow keys move ALL boxes")
                self.add_event("+/- scales ALL boxes together")
            else:
                self.add_event(f"Alignment target: {self.alignment_target}")
        
        elif event.key == pygame.K_p:
            # Print current calibration
            self._print_calibration()
        
        elif event.key == pygame.K_l:
            # Save current calibration
            self._save_calibration()
        
        # +/- keys for scaling
        elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_MINUS, pygame.K_UNDERSCORE):
            layout_cfg = self.game.layout.cfg
            
            if self.alignment_target == 'grid':
                # Scale hex grid - use absolute increment
                scale_step = 0.5 if shift_pressed else 0.1
                current_size = layout_cfg.hex_grid_calib.hex_size
                
                if event.key in (pygame.K_EQUALS, pygame.K_PLUS):
                    new_size = current_size + scale_step
                else:  # minus/underscore
                    new_size = max(5.0, current_size - scale_step)
                
                layout_cfg.hex_grid_calib.hex_size = new_size
                self.add_event(f"Hex size: {new_size:.1f}")
            
            elif self.alignment_target == 'status_boxes':
                # Scale ALL status boxes together - including positions and dimensions
                # Use smaller multiplier for fine control: 1% or 5% per press
                scale_percent = 0.05 if shift_pressed else 0.01
                boxes = layout_cfg.status_calib.boxes_in_map
                
                # Find the center point of all boxes to scale from
                if boxes:
                    min_x = min(x for x, _, _, _ in boxes.values())
                    min_y = min(y for _, y, _, _ in boxes.values())
                    max_x = max(x + w for x, _, w, _ in boxes.values())
                    max_y = max(y + h for _, y, _, h in boxes.values())
                    center_x = (min_x + max_x) / 2
                    center_y = (min_y + max_y) / 2
                    
                    scale_multiplier = 1.0 + scale_percent if event.key in (pygame.K_EQUALS, pygame.K_PLUS) else 1.0 - scale_percent
                    
                    # Apply scale to ALL boxes - both position and size
                    for box_name in boxes:
                        x, y, w, h = boxes[box_name]
                        # Scale position relative to center
                        new_x = center_x + (x - center_x) * scale_multiplier
                        new_y = center_y + (y - center_y) * scale_multiplier
                        # Scale dimensions
                        new_w = max(5.0, w * scale_multiplier)
                        new_h = max(5.0, h * scale_multiplier)
                        boxes[box_name] = (new_x, new_y, new_w, new_h)
                    
                    percent_change = (scale_multiplier - 1.0) * 100
                    self.add_event(f"All status boxes scaled by {percent_change:+.1f}%")
            
            # Invalidate cache and recompute
            self.cached_board_rect = None
            self.game.layout.recompute((self.screen.get_width(), self.screen.get_height()))
            self.game.hex_grid.size = int(self.game.layout.hex_size)
            self.game.hex_grid.offset_x, self.game.hex_grid.offset_y = self.game.layout.hex_origin_screen
        
        # Arrow key adjustments
        elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
            if self.alignment_target == 'grid':
                # Adjust hex grid origin
                layout_cfg = self.game.layout.cfg
                origin_x, origin_y = layout_cfg.hex_grid_calib.origin_in_map
                
                if event.key == pygame.K_LEFT:
                    origin_x -= delta_map
                elif event.key == pygame.K_RIGHT:
                    origin_x += delta_map
                elif event.key == pygame.K_UP:
                    origin_y -= delta_map
                elif event.key == pygame.K_DOWN:
                    origin_y += delta_map
                
                # Update calibration
                layout_cfg.hex_grid_calib.origin_in_map = (origin_x, origin_y)
                # Invalidate cache and recompute layout
                self.cached_board_rect = None
                self.game.layout.recompute((self.screen.get_width(), self.screen.get_height()))
                self.game.hex_grid.size = int(self.game.layout.hex_size)
                self.game.hex_grid.offset_x, self.game.hex_grid.offset_y = self.game.layout.hex_origin_screen
                
                self.add_event(f"Grid origin: ({origin_x:.1f}, {origin_y:.1f})")
            
            elif self.alignment_target == 'status_boxes':
                # Move ALL status boxes together
                layout_cfg = self.game.layout.cfg
                boxes = layout_cfg.status_calib.boxes_in_map
                
                offset_x = 0.0
                offset_y = 0.0
                
                if event.key == pygame.K_LEFT:
                    offset_x = -delta_map
                elif event.key == pygame.K_RIGHT:
                    offset_x = delta_map
                elif event.key == pygame.K_UP:
                    offset_y = -delta_map
                elif event.key == pygame.K_DOWN:
                    offset_y = delta_map
                
                # Apply offset to ALL boxes
                for box_name in boxes:
                    x, y, w, h = boxes[box_name]
                    boxes[box_name] = (x + offset_x, y + offset_y, w, h)
                
                # Invalidate cache and recompute layout
                self.cached_board_rect = None
                self.game.layout.recompute((self.screen.get_width(), self.screen.get_height()))
                
                self.add_event(f"All status boxes moved by ({offset_x:.1f}, {offset_y:.1f})")
    
    def _print_calibration(self) -> None:
        """Print current calibration to console."""
        layout_cfg = self.game.layout.cfg
        print("\n" + "="*60)
        print("CURRENT CALIBRATION")
        print("="*60)
        print(f"\nMap Size: {layout_cfg.map_calib.width}x{layout_cfg.map_calib.height}")
        print(f"\nHex Grid:")
        print(f"  Size: {layout_cfg.hex_grid_calib.hex_size}")
        print(f"  Origin: {layout_cfg.hex_grid_calib.origin_in_map}")
        print(f"\nStatus Boxes:")
        for name, rect in sorted(layout_cfg.status_calib.boxes_in_map.items()):
            print(f"  {name}: {rect}")
        print("="*60 + "\n")
        self.add_event("Calibration printed to console")
    
    def _save_calibration(self) -> None:
        """Save current calibration to JSON file."""
        from config.board_layout_config import save_mission_layout
        layout_cfg = self.game.layout.cfg
        save_mission_layout(self.mission_number, layout_cfg)
        self.add_event(f"Calibration saved to mission_{self.mission_number}_layout.json")
    
    def handle_mouse_click_alignment(self, pos: tuple[int, int]) -> None:
        """Handle mouse click in alignment mode to select status boxes."""
        if self.alignment_target == 'status_boxes':
            hit_box = self.game.layout.hit_test_status_box(pos)
            if hit_box:
                self.selected_status_box = hit_box
                self.add_event(f"Selected: {hit_box}")
            else:
                self.selected_status_box = None
                self.add_event("No status box selected")
    
    def update_screen(self, screen: pygame.Surface) -> None:
        """Update screen reference when display mode changes."""
        super().update_screen(screen)
        # Propagate to game components
        self.game.screen = screen
        self.game.renderer.screen = screen
        # Invalidate cached board rect so layout recomputes
        self.cached_board_rect = None
        # Update layout for new screen size
        new_size = (screen.get_width(), screen.get_height())
        self.game.update_screen_size(new_size)
    
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
        top_height = self.config.TOP_BAR_HEIGHT
        bottom_padding = 80  # Extra padding to ensure bottom hexes have room to render completely
        
        board_width = screen_width - left_width - right_width
        board_height = screen_height - top_height - bottom_padding
        
        # Draw top bar
        self._draw_top_bar(screen_width, top_height)
        
        # Draw left panel (mission rules)
        self._draw_left_panel(left_width, top_height, board_height)
        
        # Draw center (game board) - now extends to bottom
        self._draw_game_board(left_width, top_height, board_width, board_height)
        
        # Draw right panel (event log + controls)
        self._draw_right_panel(left_width + board_width, top_height, right_width, board_height)
        
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
        """Draw the left panel with mission rules (rulebook-style layout)."""
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
        reminder_block = self.mission_rules_view.get("reminder_block")
        
        text_x = 12
        text_y = y + 10
        text_width = width - 24
        
        # === MISSION HEADER ===
        title_text = f"MISSION {mission_info['number']}: {mission_info['title']}"
        self.draw_text(
            title_text,
            width // 2,
            text_y,
            self.font_medium,
            color=(255, 220, 100),
            center=True
        )
        text_y += 28
        
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
        for line in objective_lines[:2]:  # Limit to 2 lines
            self.draw_text(
                line,
                text_x,
                text_y,
                self.font_small,
                color=(160, 180, 200)
            )
            text_y += 16
        
        # Divider
        text_y += 8
        pygame.draw.line(
            self.screen,
            (70, 90, 120),
            (text_x, text_y),
            (width - text_x, text_y),
            1
        )
        text_y += 12
        
        # === PHASE SECTIONS ===
        for phase_data in phases:
            phase_num = phase_data["phase_number"]
            phase_name = phase_data["phase_name"]
            is_active = phase_data["is_active"]
            is_expanded = self.expanded_phases.get(phase_num, False)
            sections = phase_data["sections"]
            
            # Phase header
            header_height = 26
            header_rect = pygame.Rect(0, text_y, width, header_height)
            
            # Background color for active phase
            if is_active:
                pygame.draw.rect(self.screen, (40, 60, 90), header_rect)
            else:
                pygame.draw.rect(self.screen, (28, 33, 42), header_rect)
            
            # Store rect for click detection
            self.phase_header_rects[phase_num] = header_rect
            
            # Expand/collapse indicator
            indicator = "▼" if is_expanded else "▶"
            self.draw_text(
                indicator,
                text_x,
                text_y + 5,
                self.font_small,
                color=(180, 200, 220)
            )
            
            # Phase name
            phase_label = f"Phase {phase_num} — {phase_name}"
            label_color = (255, 255, 150) if is_active else (180, 200, 220)
            self.draw_text(
                phase_label,
                text_x + 20,
                text_y + 5,
                self.font_small,
                color=label_color
            )
            
            # Border
            border_color = (100, 140, 180) if is_active else (50, 70, 100)
            pygame.draw.rect(self.screen, border_color, header_rect, 1)
            
            text_y += header_height + 3
            
            # Phase content (if expanded)
            if is_expanded and sections:
                text_y = self._draw_sections(sections, text_x, text_y, text_width, y + height)
                text_y += 8
            
            # Check if we need to stop (running out of space)
            if text_y > y + height - 100:
                break
        
        # === REMINDER BLOCK (after all phases) ===
        if reminder_block and text_y < y + height - 60:
            text_y = self._draw_reminder_block(reminder_block, text_x, text_y, text_width, width)
    
    def _draw_sections(self, sections: List[Dict[str, Any]], x: int, y: int, width: int, max_y: int) -> int:
        """
        Draw content sections, returning the final y position.
        
        Args:
            sections: List of section dictionaries
            x: Left margin x position
            y: Starting y position
            width: Available width
            max_y: Maximum y position (stop rendering if exceeded)
        
        Returns:
            Final y position after rendering
        """
        for section in sections:
            if y > max_y - 30:
                break
            
            section_type = section.get("type", "")
            
            if section_type == "compact_line":
                # Single line, no bullet, smaller font
                content = section.get("content", "")
                wrapped = self._wrap_text(content, width - 10, self.font_small)
                for line in wrapped[:1]:  # Only first line
                    self.draw_text(
                        line,
                        x + 5,
                        y,
                        self.font_small,
                        color=(200, 220, 240)
                    )
                    y += 18
                y += 4
            
            elif section_type == "inline_text_block":
                # Multiple lines, no bullets, compact spacing
                lines = section.get("lines", [])
                for line in lines:
                    wrapped = self._wrap_text(line, width - 10, self.font_small)
                    for wrapped_line in wrapped:
                        self.draw_text(
                            wrapped_line,
                            x + 5,
                            y,
                            self.font_small,
                            color=(180, 195, 210)
                        )
                        y += 16
                y += 6
            
            elif section_type == "table":
                # Standard table with headers and rows
                y = self._draw_table(section, x, y, width)
                y += 8
            
            elif section_type == "mini_table":
                # Smaller table (detection thresholds, etc.)
                y = self._draw_mini_table(section, x, y, width)
                y += 6
            
            elif section_type == "result_table":
                # Results table with styling
                y = self._draw_result_table(section, x, y, width)
                y += 8
            
            elif section_type == "result_table_ref":
                # Reference to shared table
                y = self._draw_result_table_ref(section, x, y, width)
                y += 8
        
        return y
    
    def _draw_table(self, section: Dict[str, Any], x: int, y: int, width: int) -> int:
        """Draw a standard action table with nested children."""
        headers = section.get("headers", [])
        rows = section.get("rows", [])
        style = section.get("style", "")
        
        # Column widths
        col_width = (width - 20) // max(len(headers) + 1, 2)  # Default for all styles
        action_col_width = col_width
        cost_col_width = col_width
        d6_col_width = 30
        
        if style == "action_costs":
            action_col_width = 120
            cost_col_width = (width - action_col_width - 20) // len(headers)
        elif style == "escort_actions":
            d6_col_width = 30
            action_col_width = (width - d6_col_width - 20) // 2
        
        # Headers (bold effect by drawing twice with offset)
        header_x = x + 5
        if style == "action_costs":
            self.draw_text("Action", header_x, y, self.font_small, color=(220, 230, 150))
            header_x += action_col_width
        elif style == "escort_actions":
            self.draw_text("d6", header_x, y, self.font_small, color=(220, 230, 150))
            header_x += d6_col_width
        
        for header in headers:
            self.draw_text(header, header_x, y, self.font_small, color=(220, 230, 150))
            if style == "action_costs":
                header_x += cost_col_width
            elif style == "escort_actions":
                header_x += action_col_width
            else:
                header_x += col_width
        y += 16
        
        # Rows
        for row in rows:
            cells = row.get("cells", [])
            children = row.get("children", [])
            
            # Draw cells
            cell_x = x + 5
            for i, cell in enumerate(cells):
                if style == "action_costs":
                    if i == 0:
                        # Action name
                        self.draw_text(cell[:14], cell_x, y, self.font_small, color=(180, 195, 210))
                        cell_x += action_col_width
                    else:
                        # Cost value
                        self.draw_text(str(cell), cell_x, y, self.font_small, color=(180, 195, 210))
                        cell_x += cost_col_width
                elif style == "escort_actions":
                    if i == 0:
                        # d6 roll
                        self.draw_text(cell, cell_x, y, self.font_small, color=(180, 195, 210))
                        cell_x += d6_col_width
                    else:
                        # Action description (truncate if needed)
                        self.draw_text(cell[:28], cell_x, y, self.font_small, color=(180, 195, 210))
                        cell_x += action_col_width
                else:
                    self.draw_text(str(cell), cell_x, y, self.font_small, color=(180, 195, 210))
                    cell_x += col_width
            y += 15
            
            # Draw children (indented)
            if children:
                for child in children:
                    y = self._draw_child_content(child, x + 15, y, width - 15)
        
        return y
    
    def _draw_child_content(self, child: Dict[str, Any], x: int, y: int, width: int) -> int:
        """Draw nested child content (mini_table, inline_text_block)."""
        child_type = child.get("type", "")
        
        if child_type == "mini_table":
            y = self._draw_mini_table(child, x, y, width)
            y += 4
        elif child_type == "inline_text_block":
            lines = child.get("lines", [])
            for line in lines:
                wrapped = self._wrap_text(line, width - 10, self.font_small)
                for wrapped_line in wrapped:
                    self.draw_text(
                        wrapped_line,
                        x + 5,
                        y,
                        self.font_small,
                        color=(160, 175, 190)
                    )
                    y += 14
            y += 4
        
        return y
    
    def _draw_mini_table(self, section: Dict[str, Any], x: int, y: int, width: int) -> int:
        """Draw a compact mini-table."""
        headers = section.get("headers", [])
        rows = section.get("rows", [])
        
        # Calculate column widths
        num_cols = len(headers)
        col_width = (width - 20) // num_cols if num_cols > 0 else 50
        
        # Headers
        header_x = x + 5
        for header in headers:
            self.draw_text(header[:12], header_x, y, self.font_small, color=(200, 215, 230))
            header_x += col_width
        y += 14
        
        # Rows
        for row in rows:
            cell_x = x + 5
            for cell in row:
                self.draw_text(str(cell)[:12], cell_x, y, self.font_small, color=(170, 185, 200))
                cell_x += col_width
            y += 13
        
        return y
    
    def _draw_result_table(self, section: Dict[str, Any], x: int, y: int, width: int) -> int:
        """Draw a result table with title."""
        title = section.get("title", "")
        headers = section.get("headers", [])
        rows = section.get("rows", [])
        
        # Title
        if title:
            title_lines = self._wrap_text(title, width - 10, self.font_small)
            for line in title_lines:
                self.draw_text(line, x + 5, y, self.font_small, color=(220, 230, 150))
                y += 16
            y += 4
        
        # Headers
        num_cols = len(headers)
        col_width = (width - 20) // num_cols if num_cols > 0 else 50
        
        header_x = x + 5
        for header in headers:
            self.draw_text(header[:15], header_x, y, self.font_small, color=(200, 215, 230))
            header_x += col_width
        y += 14
        
        # Rows
        for row in rows:
            cell_x = x + 5
            for i, cell in enumerate(row):
                # Truncate long text
                cell_text = str(cell)[:20] if i < 2 else str(cell)[:35]
                self.draw_text(cell_text, cell_x, y, self.font_small, color=(170, 185, 200))
                cell_x += col_width
            y += 13
        
        return y
    
    def _draw_result_table_ref(self, section: Dict[str, Any], x: int, y: int, width: int) -> int:
        """Draw a table referenced from shared rules."""
        ref_id = section.get("ref", "")
        title = section.get("title", "")
        
        # Look up the referenced section
        if self.mission_rules:
            referenced_section = self.mission_rules.get_section_by_id(ref_id)
            if referenced_section:
                # Convert to result_table format and draw
                if ref_id == "allied_ship_damage":
                    # Special handling for ship damage chart
                    if title:
                        title_lines = self._wrap_text(title, width - 10, self.font_small)
                        for line in title_lines:
                            self.draw_text(line, x + 5, y, self.font_small, color=(220, 230, 150))
                            y += 16
                        y += 4
                    
                    # Draw each ship type
                    for ship_class in referenced_section.get("ship_classes", []):
                        ship_type = ship_class["ship_type"].capitalize()
                        self.draw_text(f"{ship_type}:", x + 5, y, self.font_small, color=(200, 215, 230))
                        y += 14
                        
                        for outcome in ship_class["outcomes"][:4]:  # Limit to 4 outcomes
                            roll_text = f"{outcome['roll_min']}"
                            if outcome['roll_max'] != outcome['roll_min']:
                                roll_text = f"{outcome['roll_min']}-{outcome['roll_max']}"
                            result_text = f"{roll_text}: {outcome['result']} - {outcome.get('description', '')[:30]}"
                            
                            wrapped = self._wrap_text(result_text, width - 20, self.font_small)
                            for line in wrapped[:1]:
                                self.draw_text(line, x + 10, y, self.font_small, color=(170, 185, 200))
                                y += 13
                        y += 6
        
        return y
    
    def _draw_reminder_block(self, reminder: Dict[str, Any], x: int, y: int, width: int, panel_width: int) -> int:
        """Draw the reminder block with special styling."""
        title = reminder.get("title", "")
        lines = reminder.get("lines", [])
        
        # Background box
        block_height = 20 + len(lines) * 15
        block_rect = pygame.Rect(x - 5, y, panel_width - 2*x + 10, block_height)
        pygame.draw.rect(self.screen, (45, 50, 30), block_rect)
        pygame.draw.rect(self.screen, (120, 130, 80), block_rect, 1)
        
        # Title
        self.draw_text(title, x + 5, y + 4, self.font_small, color=(220, 230, 150))
        y += 18
        
        # Lines
        for line in lines:
            wrapped = self._wrap_text(line, width - 20, self.font_small)
            for wrapped_line in wrapped:
                self.draw_text(wrapped_line, x + 5, y, self.font_small, color=(190, 200, 160))
                y += 14
        
        return y + 5
    
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
        lines: List[str] = []
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
        """Draw the central game board.
        
        Now much simpler: just define the board area and let the layout engine
        handle all positioning and scaling.
        """
        board_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (15, 20, 30), board_rect)
        
        # Update layout only if board region changed
        if self.cached_board_rect != board_rect:
            self.game.update_board_region(board_rect)
            self.cached_board_rect = board_rect
        
        # Set clip region with extra padding to allow hex overhang at edges
        # Hexes can extend ~40 pixels beyond their center point
        hex_overhang = 60
        clip_rect = pygame.Rect(
            board_rect.x - hex_overhang,
            board_rect.y - hex_overhang,
            board_rect.width + 2 * hex_overhang,
            board_rect.height + 2 * hex_overhang
        )
        old_clip = self.screen.get_clip()
        self.screen.set_clip(clip_rect)
        
        # Render map
        if self.game.show_map and self.game.map_image:
            self.game.renderer.render_map(self.game.map_image)
        
        # Render hex grid
        if self.game.show_grid:
            self.game.renderer.render_hex_grid(self.game.mission_hexes)
        
        # Render terrain overlay
        if self.game.show_terrain:
            self.game.renderer.render_terrain_overlay(
                self.game.shallow_hexes,
                self.game.land_hexes,
                self.game.mission_hexes
            )
        
        # Render status boxes
        if self.game.show_status_boxes:
            self.game.renderer.render_status_markers(
                self.game.status_boxes,
                show_all=True
            )
        
        # Render ships
        for ship in self.game.ships:
            self.game.renderer.render_ship(ship)
        
        # Render U-boat
        if self.awaiting_initial_setup:
            # Render preview with selected depth/facing
            temp_boat = self.game.u_boat
            temp_boat.depth = self.selected_depth
            temp_boat.facing = self.selected_facing
            self.game.renderer.render_u_boat(temp_boat)
        else:
            self.game.renderer.render_u_boat(self.game.u_boat)
        
        # Render alignment mode highlights
        if self.alignment_mode:
            self.game.renderer.render_alignment_highlights(
                self.alignment_target,
                self.selected_status_box
            )
        
        # Render debug overlay if in alignment mode
        if self.alignment_mode:
            self.game.renderer.render_debug_overlay(
                self.game.layout,
                self.selected_status_box
            )
        
        # Restore clip region
        self.screen.set_clip(old_clip)
        
        # Draw border
        pygame.draw.rect(self.screen, (50, 70, 100), board_rect, 2)
    
    def _draw_right_panel(self, x: int, y: int, width: int, height: int) -> None:
        """Draw the right panel with dice rolls, event log, and controls."""
        panel_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (20, 25, 35), panel_rect)
        pygame.draw.line(self.screen, (50, 70, 100), (x, y), (x, y+height), 2)
        
        # Split panel into three areas: dice rolls (top), event log (middle), controls (bottom)
        dice_area_height = 150
        controls_area_height = 200
        log_area_y = y + dice_area_height
        log_area_height = height - dice_area_height - controls_area_height
        controls_area_y = y + dice_area_height + log_area_height
        
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
        log_max_y = controls_area_y - 10  # Stop before controls area
        
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
            
            if log_y > log_max_y:
                break
        
        # Separator line before controls
        pygame.draw.line(
            self.screen,
            (50, 70, 100),
            (x, controls_area_y),
            (x + width, controls_area_y),
            2
        )
        
        # === CONTROLS/SETUP SECTION ===
        if self.awaiting_initial_setup:
            self._draw_setup_controls(x, controls_area_y, width, controls_area_height)
        else:
            self._draw_game_controls(x, controls_area_y, width, controls_area_height)
    
    def _draw_bottom_panel(self, x: int, y: int, width: int, height: int) -> None:
        """Draw the bottom panel (currently empty - controls moved to right panel)."""
        panel_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (25, 35, 50), panel_rect)
        pygame.draw.line(self.screen, (50, 70, 100), (x, y), (x+width, y), 2)
    
    def _draw_setup_controls(self, x: int, y: int, width: int, height: int) -> None:
        """Draw initial setup controls (now in right panel)."""
        self.draw_text(
            "INITIAL SETUP",
            x + width // 2,
            y + 10,
            self.font_medium,
            color=(220, 220, 255),
            center=True
        )
        
        # Depth selection
        depth_y = y + 40
        self.draw_text(
            f"Depth [1-4]:",
            x + 10,
            depth_y,
            self.font_small,
            color=(180, 200, 220)
        )
        self.draw_text(
            self.selected_depth.name,
            x + 10,
            depth_y + 20,
            self.font_small,
            color=(255, 255, 150)
        )
        
        # Facing selection
        facing_y = y + 90
        self.draw_text(
            f"Facing [Q/E]:",
            x + 10,
            facing_y,
            self.font_small,
            color=(180, 200, 220)
        )
        self.draw_text(
            self.selected_facing.name,
            x + 10,
            facing_y + 20,
            self.font_small,
            color=(255, 255, 150)
        )
        
        # Confirm button hint
        self.draw_text(
            "Press ENTER",
            x + width // 2,
            y + 150,
            self.font_small,
            color=(100, 255, 100),
            center=True
        )
        self.draw_text(
            "to begin",
            x + width // 2,
            y + 170,
            self.font_small,
            color=(100, 255, 100),
            center=True
        )
    
    def _draw_game_controls(self, x: int, y: int, width: int, height: int) -> None:
        """Draw normal game controls (now in right panel)."""
        self.draw_text(
            "CONTROLS",
            x + width // 2,
            y + 10,
            self.font_medium,
            color=(220, 220, 255),
            center=True
        )
        
        # Basic controls - compact layout for narrow panel
        controls_y = y + 40
        control_x = x + 10
        
        controls = [
            "Q/E: Rotate",
            "W: Move Forward",
            "Z/X: Change Depth",
            "",
            "G: Toggle Grid",
            "M: Toggle Map",
            "V: Toggle Terrain",
            "S: Status/Torps"
        ]
        
        for control_text in controls:
            if control_text:  # Skip empty lines for spacing
                self.draw_text(
                    control_text,
                    control_x,
                    controls_y,
                    self.font_small,
                    color=(180, 200, 220)
                )
            controls_y += 20
