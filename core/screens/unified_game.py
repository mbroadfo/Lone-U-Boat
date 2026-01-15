"""
Unified Game Screen - Single page with all game information.
Left: Mission briefing | Center: Game board | Right: Event log | Bottom: Controls
"""

import pygame
import sys
from typing import Optional, Any, List, Dict, Tuple
from ..models import Facing, Depth, Ship
from .base_screen import BaseScreen
from ..actions import (
    MoveAction, RotateAction, DepthChangeAction, RepairAction,
    DeckGunAction, FireTorpedoAction, LoadTorpedoAction
)
from ..damage.ship_damage import ShipDamageResolver
from ..damage.ship_damage import ShipDamageResolver
from ..damage.ship_damage import ShipDamageResolver


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
        self.event_log_scroll = 0  # Scroll position (0 = bottom/latest, positive = scroll up)
        self.debug_print_events = True  # Set to False to disable console event printing
        self.add_event(f"Mission {mission_number} started")
        self.add_event("Select your starting depth and facing direction")
        
        # Dice roll history
        self.dice_rolls: List[Dict[str, Any]] = []
        
        # Load mission briefing for left panel display
        self.mission_briefing: Optional[Dict[str, Any]] = None
        try:
            import json
            briefing_path = f"missions/mission_{mission_number}_briefing.json"
            with open(briefing_path, 'r', encoding='utf-8') as f:
                self.mission_briefing = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load mission briefing: {e}")
        
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
        
        # Action queue button rects for click handling
        self.undo_button_rect: Optional[pygame.Rect] = None
        self.commit_button_rect: Optional[pygame.Rect] = None
        
        # Action selection button rects
        self.action_button_rects: Dict[str, tuple[pygame.Rect, bool]] = {}
        
        # Deck gun resolution state (for interactive combat)
        self.deck_gun_resolution_state: Optional[Dict[str, Any]] = None
        self.deck_gun_roll_button_rect: Optional[pygame.Rect] = None
        
        # Torpedo resolution state (for interactive torpedo attacks)
        self.torpedo_resolution_state: Optional[Dict[str, Any]] = None
        self.torpedo_roll_button_rect: Optional[pygame.Rect] = None
        
        # Torpedo loading selection state (for interactive tube selection)
        self.load_torpedo_selection_state: Optional[Dict[str, Any]] = None
        self.tube_checkbox_rects: Dict[int, pygame.Rect] = {}  # tube_num -> checkbox rect
        self.confirm_load_button_rect: Optional[pygame.Rect] = None
        self.cancel_load_button_rect: Optional[pygame.Rect] = None
        
        # Mission rules (loaded separately if needed)
        self.mission_rules: Optional[Any] = None
        self.mission_rules_view: Optional[Any] = None
    
    def add_event(self, message: str) -> None:
        """Add an event to the log."""
        self.event_log.append(message)
        # Auto-scroll to bottom when new event added
        self.event_log_scroll = 0
        # Print to console for debugging
        if self.debug_print_events:
            print(f"[EVENT] {message}")
    
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
                    self.game.show_status_boxes = True  # Enable status boxes in edit mode
                else:
                    self.add_event("Alignment mode OFF")
                    self.game.show_status_boxes = False  # Disable status boxes when exiting edit mode
            
            # Alignment mode controls
            elif self.alignment_mode:
                self._handle_alignment_input(event)
            
            # If awaiting initial setup
            if self.awaiting_initial_setup:
                self._handle_setup_input(event)
            else:
                # Game is active - handle game keys
                if event.key == pygame.K_SPACE:
                    # Check if in U-Boat phase with uncommitted actions
                    from ..models import GamePhase
                    if self.game.turn_manager.current_phase == GamePhase.UBOAT_PHASE:
                        # If actions are queued but not committed, warn player
                        if hasattr(self.game, 'action_queue') and self.game.action_queue.actions:
                            self.add_event("⚠ Commit your actions first (press C or click Commit button)")
                        else:
                            # No uncommitted actions, can advance
                            self._advance_phase_and_update_ui()
                    else:
                        # Not in U-Boat phase, can always advance
                        self._advance_phase_and_update_ui()
                
                elif event.key == pygame.K_u:
                    # Undo last action from queue
                    if hasattr(self.game, 'action_queue') and self.game.action_queue.actions:
                        undone_action = self.game.action_queue.remove_last()
                        if undone_action:
                            action_desc = self._get_action_description(undone_action)
                            remaining = self.game.action_queue.get_remaining_ap(self.game)
                            self.add_event(f"Undone: {action_desc} (AP: {remaining}/{self.game.action_queue.max_ap})")
                    else:
                        self.add_event("Nothing to undo")
                
                elif event.key == pygame.K_c:
                    # Commit queued actions
                    current_phase = self.game.turn_manager.current_phase
                    from ..models import GamePhase
                    if current_phase == GamePhase.UBOAT_PHASE:
                        if hasattr(self.game, 'action_queue') and self.game.action_queue.actions:
                            # Execute all actions immediately (commit_all clears queue and deducts AP)
                            results = self.game.action_queue.commit_all(self.game)
                            for result in results:
                                if result.success:
                                    action_name = result.state_changes.get('action_name', 'Action')
                                    self.add_event(f"✓ {action_name}")
                                else:
                                    self.add_event(f"✗ Failed: {result.message}")
                            remaining = self.game.action_queue.get_remaining_ap(self.game)
                            self.add_event(f"Committed (AP: {remaining}/{self.game.action_queue.max_ap})")
                        else:
                            self.add_event("No actions to commit")
                    else:
                        self.add_event("Can only commit during U-Boat phase")
                
                # Display toggles (work during game)
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
                    # Status boxes only toggleable in alignment mode
                    if self.alignment_mode:
                        self.game.show_status_boxes = not self.game.show_status_boxes
                        state = "ON" if self.game.show_status_boxes else "OFF"
                        self.add_event(f"Status boxes: {state}")
                    else:
                        self.add_event(f"Status boxes: Only available in F2 Edit Mode")

        elif event.type == pygame.MOUSEWHEEL:
            # Scroll event log
            if event.y > 0:  # Scroll up
                self.event_log_scroll = min(self.event_log_scroll + 3, len(self.event_log) - 10)
            elif event.y < 0:  # Scroll down
                self.event_log_scroll = max(0, self.event_log_scroll - 3)
        
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
                
                # Check if clicking dice roll button
                if not self.awaiting_initial_setup:
                    # Only check dice button if AP hasn't been rolled
                    if (hasattr(self, 'dice_roll_button_rect') and self.dice_roll_button_rect and 
                        self.game.turn_manager.ap_tracker is None and
                        self.dice_roll_button_rect.collidepoint(mouse_pos)):
                        from ..models import GamePhase
                        if self.game.turn_manager.current_phase == GamePhase.UBOAT_PHASE:
                            # Roll dice and initialize AP tracker (without incrementing turn)
                            ap = self.game.turn_manager.roll_action_points_only(self.game.u_boat)
                            self.game.u_boat.action_points = ap
                            # Reset action queue for new turn
                            self.game.action_queue.reset_for_new_turn(ap)
                            
                            # Clear dice button rect so it doesn't interfere with action button clicks
                            self.dice_roll_button_rect = None
                            
                            # Add event log
                            if self.game.turn_manager.last_ap_roll:
                                roll_info = self.game.turn_manager.last_ap_roll
                                rolls_str = "][".join([str(r) for r in roll_info['rolls']])
                                event_msg = f"Turn {self.game.turn_manager.turn_number}: Rolled [{rolls_str}] → {roll_info['highest']}"
                                if roll_info['captain_bonus'] > 0:
                                    event_msg += f" +{roll_info['captain_bonus']} (Captain)"
                                event_msg += f" = {roll_info['total_ap']} AP"
                                self.add_event(event_msg)
                    
                    # Check if clicking action queue buttons
                    elif self.undo_button_rect and self.undo_button_rect.collidepoint(mouse_pos):
                        if hasattr(self.game, 'action_queue') and self.game.action_queue.actions:
                            undone_action = self.game.action_queue.remove_last()
                            if undone_action:
                                action_name = type(undone_action).__name__.replace('Action', '')
                                self.add_event(f"Undone: {action_name}")
                    
                    elif self.commit_button_rect and self.commit_button_rect.collidepoint(mouse_pos):
                        current_phase = self.game.turn_manager.current_phase
                        from ..models import GamePhase
                        if current_phase == GamePhase.UBOAT_PHASE:
                            if hasattr(self.game, 'action_queue') and self.game.action_queue.actions:
                                # Check if any action needs interactive resolution
                                has_deck_gun = any(isinstance(action, DeckGunAction) for action in self.game.action_queue.actions)
                                has_torpedo = any(isinstance(action, FireTorpedoAction) for action in self.game.action_queue.actions)
                                
                                if has_deck_gun:
                                    # Check if deck gun is damaged
                                    if self.game.u_boat.deck_gun_damaged:
                                        self.add_event("✗ Cannot fire deck gun - deck gun is damaged")
                                        # Remove deck gun actions from queue
                                        self.game.action_queue.actions = [
                                            a for a in self.game.action_queue.actions 
                                            if not isinstance(a, DeckGunAction)
                                        ]
                                    else:
                                        # Find the first deck gun action and start interactive resolution
                                        for i, action in enumerate(self.game.action_queue.actions):
                                            if isinstance(action, DeckGunAction):
                                                # Recalculate targets based on CURRENT u-boat position
                                                # (may have moved since action was queued)
                                                from ..los import LOSCalculator
                                                from ..hex_grid import HexGrid
                                                
                                                los_calc = LOSCalculator(self.game.land_hexes)
                                                current_targets: List[Tuple[Ship, int]] = []
                                                for ship in self.game.ships:
                                                    distance = HexGrid.hex_distance(self.game.u_boat.position, ship.position)
                                                    if 1 <= distance <= 3:
                                                        has_los, _ = los_calc.has_line_of_sight(
                                                            self.game.u_boat.position,
                                                            ship.position
                                                        )
                                                        if has_los:
                                                            current_targets.append((ship, distance))
                                                
                                                # Sort by distance (closest first)
                                                import random
                                                current_targets.sort(key=lambda ship_tuple: (ship_tuple[1], random.random()))
                                                
                                                # Store queue index for after resolution
                                                self.deck_gun_resolution_state = {
                                                    'action': action,
                                                    'action_index': i,
                                                    'targets': current_targets,  # Use recalculated targets
                                                    'current_idx': 0,
                                                    'waiting_for': 'hit',
                                                    'last_hit_roll': None,
                                                    'last_damage_roll': None,
                                                    'results': []
                                                }
                                                self.add_event("=== DECK GUN ATTACK ===")
                                                break
                                
                                elif has_torpedo:
                                    # Find first torpedo action and start interactive resolution
                                    for i, action in enumerate(self.game.action_queue.actions):
                                        if isinstance(action, FireTorpedoAction):
                                            # Execute to get targets (tubes are unloaded here)
                                            result = action.execute(self.game)
                                            
                                            # Spend AP
                                            self.game.u_boat.action_points -= result.ap_spent
                                            
                                            # Check if needs interactive resolution
                                            if result.state_changes.get('needs_interactive_resolution'):
                                                # Setup interactive resolution state
                                                self.torpedo_resolution_state = {
                                                    'action': action,
                                                    'action_index': i,
                                                    'torpedo_count': result.state_changes['torpedo_count'],
                                                    'targets': result.state_changes['targets'],  # [(ship, distance, aspect), ...]
                                                    'current_target_idx': 0,
                                                    'current_torpedo_idx': 0,
                                                    'torpedoes_available': result.state_changes['torpedo_count'],
                                                    'waiting_for': 'hit',  # 'hit', 'damage', 'continue'
                                                    'last_hit_roll': None,
                                                    'last_damage_roll': None,
                                                    'results': []  # [(torpedo_num, ship, distance, hit, damage_die), ...]
                                                }
                                                self.add_event(f"=== FIRING {self.torpedo_resolution_state['torpedo_count']} TORPEDO(ES) ===")
                                            else:
                                                # No targets, just log
                                                self.add_event(result.message)
                                            
                                            # Remove this action from queue
                                            self.game.action_queue.actions.pop(i)
                                            break
                                
                                else:
                                    # No interactive actions - execute all immediately (commit_all clears queue and deducts AP)
                                    results = self.game.action_queue.commit_all(self.game)
                                    for result in results:
                                        if result.success:
                                            action_name = result.state_changes.get('action_name', 'Action')
                                            self.add_event(f"✓ {action_name}")
                                        else:
                                            self.add_event(f"✗ Failed: {result.message}")
                                    remaining = self.game.action_queue.get_remaining_ap(self.game)
                                    self.add_event(f"Committed (AP: {remaining}/{self.game.action_queue.max_ap})")
                            else:
                                self.add_event("No actions to commit")
                        else:
                            self.add_event("Can only commit during U-Boat phase")
                    
                    # Check if clicking deck gun resolution button
                    elif self.deck_gun_resolution_state and self.deck_gun_roll_button_rect and self.deck_gun_roll_button_rect.collidepoint(mouse_pos):
                        self._handle_deck_gun_roll()
                    
                    # Check if clicking torpedo resolution button
                    elif self.torpedo_resolution_state and self.torpedo_roll_button_rect and self.torpedo_roll_button_rect.collidepoint(mouse_pos):
                        self._handle_torpedo_roll()
                    
                    # Check if clicking torpedo loading UI buttons
                    elif self.load_torpedo_selection_state:
                        self._handle_load_torpedo_clicks(mouse_pos)
                    
                    # Check if clicking action selection buttons
                    elif not self.load_torpedo_selection_state:  # Only allow if not in torpedo selection
                        for action_id, button_data in self.action_button_rects.items():
                            rect: pygame.Rect
                            is_clickable: bool
                            rect, is_clickable = button_data
                            if rect.collidepoint(mouse_pos) and is_clickable:
                                self._queue_action(action_id)
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
            self.add_event("Click 'Roll for AP' to begin your turn")
        
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
    
    def _advance_phase_and_update_ui(self):
        """Advance to next phase and update UI with phase information."""
        # Forward phase advancement to game
        self.game._advance_to_next_phase()  # type: ignore[attr-defined]
        
        # Add visual feedback
        phase_name = self.game.turn_manager.get_current_phase_name()
        self.add_event(f"→ {phase_name}")
        
        # Show phase log messages in event log
        phase_logs = self.game.turn_manager.get_phase_log(phase_name)
        for log_msg in phase_logs:
            self.add_event(f"  {log_msg}")
        
        # If we just started U-Boat phase (new turn), prompt for AP roll
        from ..models import GamePhase
        if self.game.turn_manager.current_phase == GamePhase.UBOAT_PHASE:
            if self.game.turn_manager.ap_tracker is None:
                self.add_event("Click 'Roll for AP' to begin your turn")
            elif self.game.turn_manager.last_ap_roll:
                # This shouldn't happen with new flow, but keep for safety
                roll_info = self.game.turn_manager.last_ap_roll
                rolls_str = "][".join([str(r) for r in roll_info['rolls']])
                
                event_msg = f"Turn {self.game.turn_manager.turn_number}: Rolled [{rolls_str}] → {roll_info['highest']}"
                if roll_info['captain_bonus'] > 0:
                    event_msg += f" +{roll_info['captain_bonus']} (Captain)"
                event_msg += f" = {roll_info['total_ap']} AP"
                
                self.add_event(event_msg)
    
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
            old_phase = self.game.turn_manager.current_phase if hasattr(self.game, 'turn_manager') else None
            self.game.update()
            
            # Update mission rules view if phase changed
            if hasattr(self, 'mission_rules') and self.mission_rules and hasattr(self.game, 'turn_manager'):
                new_phase = self.game.turn_manager.current_phase
                if old_phase != new_phase:
                    try:
                        sys.path.insert(0, 'missions')
                        from mission_rules_loader import create_mission_rules_view_model  # type: ignore[import-not-found]
                        # Map GamePhase enum to phase number (3->1, 4->2, etc.)
                        phase_map = {3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6}
                        current_phase_num = phase_map.get(new_phase.value, 1)
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
        turn_num = self.game.turn_manager.turn_number if hasattr(self.game, 'turn_manager') else 1
        phase_name = self.game.turn_manager.current_phase.name.replace('_', ' ') if hasattr(self.game, 'turn_manager') else 'SETUP'
        title = f"Mission {self.mission_number} - Turn {turn_num} - {phase_name}"
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
        """Draw the left panel with mission briefing (from JSON structure)."""
        panel_rect = pygame.Rect(0, y, width, height)
        pygame.draw.rect(self.screen, (20, 25, 35), panel_rect)
        pygame.draw.line(self.screen, (50, 70, 100), (width-1, y), (width-1, y+height), 2)
        
        if not self.mission_briefing:
            # Fallback if briefing couldn't load
            self.draw_text(
                "MISSION BRIEFING",
                width // 2,
                y + 15,
                self.font_medium,
                color=(200, 220, 255),
                center=True
            )
            self.draw_text(
                "Briefing could not be loaded",
                10,
                y + 50,
                self.font_small,
                color=(150, 150, 150)
            )
            return
        
        # Clear phase header rects for click detection
        self.phase_header_rects.clear()
        
        text_x = 12
        text_y = y + 10
        text_width = width - 24
        
        # === MISSION HEADER ===
        title = self.mission_briefing.get("title", "")
        self.draw_text(
            title,
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
        
        objective = self.mission_briefing.get("objective", "")
        objective_lines = self._wrap_text(objective, text_width, self.font_small)
        for line in objective_lines[:3]:  # Limit to 3 lines
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
        phases = self.mission_briefing.get("phases", [])
        current_phase = self.game.turn_manager.current_phase.value if hasattr(self.game, 'turn_manager') else 1
        
        for phase in phases:
            phase_id = phase.get("id", 0)
            phase_name = phase.get("name", "")
            header_text = phase.get("header_text", "")
            is_expanded = self.expanded_phases.get(phase_id, False)
            is_active = (phase_id == current_phase)
            sections = phase.get("sections", [])
            
            # Phase header
            header_height = 26
            header_rect = pygame.Rect(0, text_y, width, header_height)
            
            # Background color for active phase
            if is_active:
                pygame.draw.rect(self.screen, (40, 60, 90), header_rect)
            else:
                pygame.draw.rect(self.screen, (28, 33, 42), header_rect)
            
            # Store rect for click detection
            self.phase_header_rects[phase_id] = header_rect
            
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
            phase_label = f"Phase {phase_id} — {phase_name}"
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
            
            # Header text (if any)
            if is_expanded and header_text:
                self.draw_text(
                    header_text,
                    text_x + 5,
                    text_y,
                    self.font_small,
                    color=(220, 200, 100)
                )
                text_y += 18
            
            # Phase content (if expanded)
            if is_expanded and sections:
                text_y = self._draw_briefing_sections(sections, text_x, text_y, text_width, y + height)
                text_y += 8
            
            # Check if we need to stop (running out of space)
            if text_y > y + height - 150:
                break
        
        # === GLOBAL NOTES (at bottom if space available) ===
        global_notes = self.mission_briefing.get("global_notes", [])
        if global_notes and text_y < y + height - 100:
            text_y += 10
            pygame.draw.line(
                self.screen,
                (70, 90, 120),
                (text_x, text_y),
                (width - text_x, text_y),
                1
            )
            text_y += 10
            
            for note in global_notes:
                text_y = self._draw_global_note(note, text_x, text_y, text_width, width, y + height)
                if text_y > y + height - 20:
                    break
    
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
        style = section.get("style", "")
        
        # Use grid-based renderer for torpedo attack range table
        if style == "fire_torps_range":
            attack_data = {"headers": headers, "rows": rows}
            panel_rect = pygame.Rect(x, y, width, 200)
            y = self._render_attack_table(self.screen, panel_rect, attack_data, self.font_small)
            return y
        
        # Default rendering for other mini-tables
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
                    # Special handling for ship damage chart - use grid-based renderer
                    if title:
                        title_lines = self._wrap_text(title, width - 10, self.font_small)
                        for line in title_lines:
                            self.draw_text(line, x + 5, y, self.font_small, color=(220, 230, 150))
                            y += 16
                        y += 4
                    
                    # Build damage data structure for grid renderer
                    damage_data = {}
                    for ship_class in referenced_section.get("ship_classes", []):
                        ship_type = ship_class["ship_type"]
                        damage_data[ship_type] = ship_class
                    
                    # Use grid-based renderer
                    panel_rect = pygame.Rect(x, y, width, 200)
                    y = self._render_damage_chart(self.screen, panel_rect, damage_data, self.font_small)
        
        return y
    
    def _build_damage_chart_data(self, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build damage chart data structure from table rows.
        
        Args:
            rows: List of row dictionaries with "cells" representing ship damage outcomes
        
        Returns:
            Dictionary mapping ship_type to outcomes data
        """
        # If we have access to mission rules, use that
        if self.mission_rules:
            damage_section = self.mission_rules.get_section_by_id("allied_ship_damage")
            if damage_section:
                damage_data = {}
                for ship_class in damage_section.get("ship_classes", []):
                    ship_type = ship_class["ship_type"]
                    damage_data[ship_type] = ship_class
                return damage_data
        
        # Fallback: construct from rows (if provided in that format)
        # This is a simplified fallback
        damage_data = {
            "merchant": {"outcomes": []},
            "corvette": {"outcomes": []},
            "destroyer": {"outcomes": []}
        }
        return damage_data
    
    # ==================== BRIEFING GRID SYSTEM ====================
    
    class BriefingGrid:
        """
        Helper for rendering column-based layouts with consistent margins and alignment.
        Each section/table can instantiate its own grid with appropriate column widths.
        """
        
        def __init__(
            self,
            screen: pygame.Surface,
            font: pygame.font.Font,
            panel_rect: pygame.Rect,
            padding: int,
            columns: List[Tuple[str, Any]],  # List of (name, width) where width is int (px) or float (fraction)
            line_height: int = 18,
            gutter: int = 8
        ):
            """
            Initialize grid system.
            
            Args:
                screen: Pygame surface to draw on
                font: Font to use for text
                panel_rect: Full panel rectangle (x, y, width, height)
                padding: Inner padding from panel edges
                columns: List of (name, width) tuples. Width can be:
                    - int: absolute pixels
                    - float 0.0-1.0: fraction of available width
                line_height: Height per row in pixels
                gutter: Horizontal spacing between columns
            """
            self.screen = screen
            self.font = font
            self.panel_rect = panel_rect
            self.padding = padding
            self.line_height = line_height
            self.gutter = gutter
            
            # Compute usable inner rect
            self.inner_rect = pygame.Rect(
                panel_rect.x + padding,
                panel_rect.y + padding,
                panel_rect.width - 2 * padding,
                panel_rect.height - 2 * padding
            )
            
            # Parse column definitions and compute rects
            self.columns = columns
            self.col_rects = self._compute_col_rects()
            
            # Current baseline Y position
            self.current_y = self.inner_rect.y
        
        def _compute_col_rects(self) -> Dict[str, pygame.Rect]:
            """
            Compute column rectangles based on column definitions.
            
            Returns:
                Dictionary mapping column name to pygame.Rect
            """
            col_rects = {}
            available_width = self.inner_rect.width
            
            # First pass: calculate absolute widths for fractional columns
            total_fixed = 0
            total_fraction = 0.0
            
            for name, width in self.columns:
                if isinstance(width, int):
                    total_fixed += width
                else:
                    total_fraction += width
            
            # Subtract gutter space (n-1 gutters for n columns)
            available_for_fraction = available_width - total_fixed - (len(self.columns) - 1) * self.gutter
            
            # Second pass: create rects
            current_x = self.inner_rect.x
            for i, (name, width) in enumerate(self.columns):
                if isinstance(width, int):
                    col_width = width
                else:
                    col_width = int(available_for_fraction * width)
                
                col_rects[name] = pygame.Rect(
                    current_x,
                    self.current_y,
                    col_width,
                    self.line_height
                )
                
                current_x += col_width + self.gutter
            
            return col_rects
        
        def draw_cell(
            self,
            col_name: str,
            text: str,
            align: str = "left",
            color: Tuple[int, int, int] = (180, 195, 210)
        ) -> None:
            """
            Draw text in a specific column cell at the current row.
            
            Args:
                col_name: Name of the column
                text: Text to render
                align: "left", "center", or "right"
                color: RGB color tuple
            """
            if col_name not in self.col_rects:
                return
            
            rect = self.col_rects[col_name]
            text_surface = self.font.render(str(text), True, color)
            
            if align == "center":
                text_x = rect.x + (rect.width - text_surface.get_width()) // 2
            elif align == "right":
                text_x = rect.x + rect.width - text_surface.get_width()
            else:  # left
                text_x = rect.x
            
            # Update rect y position to current baseline
            text_y = self.current_y
            self.screen.blit(text_surface, (text_x, text_y))
        
        def draw_wrapped_in_col(
            self,
            col_name: str,
            text: str,
            color: Tuple[int, int, int] = (155, 170, 185),
            indent_px: int = 0,
            v_spacing: int = 2
        ) -> int:
            """
            Draw wrapped text within a column, advancing baseline for each line.
            
            Args:
                col_name: Name of the column
                text: Text to wrap and render
                color: RGB color tuple
                indent_px: Additional left indent in pixels
                v_spacing: Extra vertical spacing between lines
            
            Returns:
                Number of lines drawn
            """
            if col_name not in self.col_rects:
                return 0
            
            rect = self.col_rects[col_name]
            wrapped_lines = self._wrap_text(text, rect.width - indent_px)
            
            lines_drawn = 0
            for line in wrapped_lines:
                text_surface = self.font.render(line, True, color)
                self.screen.blit(text_surface, (rect.x + indent_px, self.current_y))
                self.current_y += self.line_height - v_spacing
                lines_drawn += 1
            
            return lines_drawn
        
        def next_row(self, extra_lines: int = 0) -> None:
            """
            Advance to next row.
            
            Args:
                extra_lines: Additional blank lines to skip (for spacing)
            """
            self.current_y += self.line_height * (1 + extra_lines)
            
            # Update all column rects to new y position
            for rect in self.col_rects.values():
                rect.y = self.current_y
        
        def _wrap_text(self, text: str, max_width: int) -> List[str]:
            """Wrap text to fit within max_width pixels."""
            words = text.split(' ')
            lines = []
            current_line = ""
            
            for word in words:
                test_line = f"{current_line} {word}".strip()
                test_surface = self.font.render(test_line, True, (255, 255, 255))
                
                if test_surface.get_width() <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            
            if current_line:
                lines.append(current_line)
            
            return lines if lines else [""]
    
    def _render_ap_table(
        self,
        surface: pygame.Surface,
        panel_rect: pygame.Rect,
        rows: List[Dict[str, Any]],
        font: pygame.font.Font
    ) -> int:
        """
        Render Action Points cost table using BriefingGrid.
        
        Args:
            surface: Surface to draw on
            panel_rect: Rectangle defining the table area (x, y, width, height)
            rows: List of row dictionaries with "cells" and optional "comment"
            font: Font to use
        
        Returns:
            Final Y position after rendering
        """
        # Create grid with 5 columns: Action (35%), Surf (16.25%), Peri (16.25%), Med (16.25%), Deep (16.25%)
        grid = self.BriefingGrid(
            surface,
            font,
            panel_rect,
            padding=5,
            columns=[
                ("action", 0.35),
                ("surf", 0.1625),
                ("peri", 0.1625),
                ("med", 0.1625),
                ("deep", 0.1625)
            ],
            line_height=18,
            gutter=4
        )
        
        # Draw headers
        grid.draw_cell("action", "Action", align="left", color=(220, 230, 150))
        grid.draw_cell("surf", "Surf", align="center", color=(220, 230, 150))
        grid.draw_cell("peri", "Peri", align="center", color=(220, 230, 150))
        grid.draw_cell("med", "Med", align="center", color=(220, 230, 150))
        grid.draw_cell("deep", "Deep", align="center", color=(220, 230, 150))
        grid.next_row()
        
        # Draw horizontal line under headers
        line_y = grid.current_y - 2
        pygame.draw.line(surface, (70, 90, 120), (panel_rect.x, line_y), (panel_rect.x + panel_rect.width, line_y), 1)
        grid.current_y += 2
        
        # Draw data rows
        for row in rows:
            cells = row.get("cells", [])
            comment = row.get("comment", "")
            
            if len(cells) >= 5:
                # Draw action name and AP costs
                grid.draw_cell("action", cells[0], align="left", color=(230, 240, 160))
                grid.draw_cell("surf", cells[1], align="center", color=(180, 195, 210))
                grid.draw_cell("peri", cells[2], align="center", color=(180, 195, 210))
                grid.draw_cell("med", cells[3], align="center", color=(180, 195, 210))
                grid.draw_cell("deep", cells[4], align="center", color=(180, 195, 210))
                grid.next_row()
                
                # Draw comment indented under action column
                if comment:
                    grid.draw_wrapped_in_col("action", comment, color=(155, 170, 185), indent_px=12, v_spacing=2)
                    grid.next_row(extra_lines=0)
        
        return grid.current_y
    
    def _render_attack_table(
        self,
        surface: pygame.Surface,
        panel_rect: pygame.Rect,
        data: Dict[str, Any],
        font: pygame.font.Font
    ) -> int:
        """
        Render torpedo attack range table using BriefingGrid.
        
        Args:
            surface: Surface to draw on
            panel_rect: Rectangle defining the table area
            data: Dictionary with "headers" and "rows"
            font: Font to use
        
        Returns:
            Final Y position after rendering
        """
        headers = data.get("headers", [])
        rows = data.get("rows", [])
        
        # Create grid with label column (30%) + 4 range columns (17.5% each)
        grid = self.BriefingGrid(
            surface,
            font,
            panel_rect,
            padding=5,
            columns=[
                ("label", 0.30),
                ("range1", 0.175),
                ("range2", 0.175),
                ("range3", 0.175),
                ("range4", 0.175)
            ],
            line_height=16,
            gutter=4
        )
        
        # Draw headers
        if len(headers) >= 5:
            grid.draw_cell("label", headers[0], align="left", color=(220, 230, 150))
            grid.draw_cell("range1", headers[1], align="center", color=(220, 230, 150))
            grid.draw_cell("range2", headers[2], align="center", color=(220, 230, 150))
            grid.draw_cell("range3", headers[3], align="center", color=(220, 230, 150))
            grid.draw_cell("range4", headers[4], align="center", color=(220, 230, 150))
            grid.next_row()
        
        # Draw rows
        for row in rows:
            if len(row) >= 5:
                grid.draw_cell("label", row[0], align="left", color=(190, 205, 220))
                grid.draw_cell("range1", row[1], align="center", color=(180, 195, 210))
                grid.draw_cell("range2", row[2], align="center", color=(180, 195, 210))
                grid.draw_cell("range3", row[3], align="center", color=(180, 195, 210))
                grid.draw_cell("range4", row[4], align="center", color=(180, 195, 210))
                grid.next_row()
        
        return grid.current_y
    
    def _render_damage_chart(
        self,
        surface: pygame.Surface,
        panel_rect: pygame.Rect,
        data: Dict[str, Any],
        font: pygame.font.Font
    ) -> int:
        """
        Render Allied Ship Damage chart using BriefingGrid.
        
        Args:
            surface: Surface to draw on
            panel_rect: Rectangle defining the table area
            data: Dictionary with ship damage data
            font: Font to use
        
        Returns:
            Final Y position after rendering
        """
        # Create grid with ship column (25%) + 3 result columns (25% each)
        grid = self.BriefingGrid(
            surface,
            font,
            panel_rect,
            padding=5,
            columns=[
                ("ship", 0.25),
                ("result1", 0.25),
                ("result2", 0.25),
                ("result3", 0.25)
            ],
            line_height=16,
            gutter=4
        )
        
        # Draw headers
        grid.draw_cell("ship", "Ship", align="left", color=(220, 230, 150))
        grid.draw_cell("result1", "1-2", align="center", color=(220, 230, 150))
        grid.draw_cell("result2", "3-4", align="center", color=(220, 230, 150))
        grid.draw_cell("result3", "5-6", align="center", color=(220, 230, 150))
        grid.next_row()
        
        # Draw rows for each ship type
        ship_types = ["merchant", "corvette", "destroyer"]
        ship_labels = ["Merchant", "Corvette", "Destroyer"]
        
        for ship_type, ship_label in zip(ship_types, ship_labels):
            ship_data = data.get(ship_type, {})
            outcomes = ship_data.get("outcomes", [])
            
            if len(outcomes) >= 3:
                grid.draw_cell("ship", ship_label, align="left", color=(200, 215, 230))
                
                # Map outcomes to columns (1-2, 3-4, 5-6)
                for i, outcome in enumerate(outcomes[:3]):
                    result_text = outcome.get("result", "")
                    col_name = f"result{i+1}"
                    
                    # Color code results
                    if "SUNK" in result_text or "CRIT" in result_text:
                        color = (255, 100, 100)
                    elif "DAMAGE" in result_text:
                        color = (255, 200, 100)
                    else:
                        color = (150, 220, 150)
                    
                    grid.draw_cell(col_name, result_text, align="center", color=color)
                
                grid.next_row()
        
        return grid.current_y
    
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
    
    def _draw_briefing_sections(
        self,
        sections: List[Dict[str, Any]],
        x: int,
        y: int,
        width: int,
        max_y: int
    ) -> int:
        """
        Draw sections from the JSON briefing structure.
        
        Args:
            sections: List of section dictionaries from JSON
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
            
            if section_type == "text_block":
                # Text block with optional styling
                text = section.get("text", "")
                style = section.get("style", "")
                
                # Special handling for intro_box (phase intro in bordered box)
                if style == "intro_box":
                    wrapped = self._wrap_text(text, width - 16, self.font_small)
                    box_height = 8 + len(wrapped) * 14
                    box_rect = pygame.Rect(x + 8, y, width - 16, box_height)
                    pygame.draw.rect(self.screen, (30, 38, 50), box_rect)
                    pygame.draw.rect(self.screen, (60, 75, 95), box_rect, 1)
                    
                    text_y = y + 4
                    for line in wrapped:
                        self.draw_text(line, x + 12, text_y, self.font_small, color=(190, 205, 220))
                        text_y += 14
                    y = text_y + 4
                
                # Special handling for action_rules_summary (bordered box with bullets)
                elif style == "action_rules_summary":
                    lines = text.split('\n')
                    
                    # Calculate box height
                    box_height = 10 + len(lines) * 15
                    box_rect = pygame.Rect(x, y, width, box_height)
                    
                    # Draw background and border
                    pygame.draw.rect(self.screen, (30, 35, 45), box_rect)
                    pygame.draw.rect(self.screen, (70, 90, 120), box_rect, 1)
                    
                    y += 6
                    for line in lines:
                        self.draw_text(
                            f"• {line}",
                            x + 8,
                            y,
                            self.font_small,
                            color=(180, 195, 210)
                        )
                        y += 15
                    y += 4
                else:
                    # Regular text block
                    # Color based on style
                    if style.startswith("phase_"):
                        color = (200, 220, 240)
                    elif style.startswith("rules_"):
                        color = (180, 195, 210)
                    else:
                        color = (170, 185, 200)
                    
                    wrapped = self._wrap_text(text, width - 10, self.font_small)
                    for line in wrapped:
                        self.draw_text(
                            line,
                            x + 5,
                            y,
                            self.font_small,
                            color=color
                        )
                        y += 16
                    y += 6
            
            elif section_type == "note":
                # Short call-out / reminder (smaller, indented)
                text = section.get("text", "")
                wrapped = self._wrap_text(text, width - 20, self.font_small)
                for line in wrapped:
                    self.draw_text(
                        f"• {line}" if line == wrapped[0] else f"  {line}",
                        x + 10,
                        y,
                        self.font_small,
                        color=(160, 175, 140)
                    )
                    y += 14
                y += 4
            
            elif section_type == "table":
                # Table rendering
                y = self._draw_briefing_table(section, x, y, width)
                y += 8
        
        return y
    
    def _draw_briefing_table(
        self,
        table: Dict[str, Any],
        x: int,
        y: int,
        width: int
    ) -> int:
        """Draw a table from the JSON briefing structure."""
        style = table.get("style", "")
        title = table.get("title", "")
        columns = table.get("columns", [])
        rows = table.get("rows", [])
        notes = table.get("notes", [])
        # header_row = table.get("header_row", "")  # Reserved for future use
        
        # Title (if present)
        if title:
            title_lines = self._wrap_text(title, width - 10, self.font_small)
            for line in title_lines:
                self.draw_text(line, x + 5, y, self.font_small, color=(220, 230, 150))
                y += 16
            y += 4
        
        # === USE GRID-BASED RENDERERS FOR SPECIFIC STYLES ===
        
        # Action Costs table (Phase 1)
        if style == "action_costs":
            panel_rect = pygame.Rect(x, y, width, 600)  # Height will be computed by renderer
            y = self._render_ap_table(self.screen, panel_rect, rows, self.font_small)
            return y + 8
        
        # Torpedo attack range sub-table
        if style == "fire_torps_range":
            panel_rect = pygame.Rect(x, y, width, 200)
            attack_data = {"headers": columns, "rows": [row if isinstance(row, list) else row.get("cells", []) for row in rows]}
            y = self._render_attack_table(self.screen, panel_rect, attack_data, self.font_small)
            return y + 8
        
        # Allied Ship Damage chart
        if style == "allied_ship_damage":
            # Need to fetch the actual damage data from mission rules
            # For now, construct it from the rows if available
            damage_data = self._build_damage_chart_data(rows)
            panel_rect = pygame.Rect(x, y, width, 200)
            y = self._render_damage_chart(self.screen, panel_rect, damage_data, self.font_small)
            return y + 8
        
        # Calculate column widths based on style
        num_cols = len(columns)
        if style == "action_table_card":
            # Card layout: Action(35%), Surf(10%), Peri(10%), Med(10%), Deep(10%)
            # Remaining 25% for spacing and comments span full width
            col_widths = [
                int(width * 0.35),  # Action
                int(width * 0.13),  # Surf
                int(width * 0.13),  # Peri
                int(width * 0.13),  # Med
                int(width * 0.13)   # Deep
            ]
        elif style == "action_table":
            # Fixed column widths: 40% for Action, 15% each for depth columns
            action_col_width = int(width * 0.40)
            depth_col_width = int((width - action_col_width) / (num_cols - 1)) if num_cols > 1 else width - action_col_width
            col_widths = [action_col_width] + [depth_col_width] * (num_cols - 1)
        elif style == "attack_table":
            # Custom widths for attack table
            col_widths = [80] + [(width - 100) // (num_cols - 1) if num_cols > 1 else 50] * (num_cols - 1)
        elif style == "damage_chart":
            # First column for ship name, others for roll results
            ship_col_width = 70
            remaining_width = width - ship_col_width - 20
            result_col_width = remaining_width // (num_cols - 1) if num_cols > 1 else remaining_width
            col_widths = [ship_col_width] + [result_col_width] * (num_cols - 1)
        elif style == "detection_table" or style == "modifier_table":
            # Two columns, roughly equal
            col_widths = [width // 2 - 10, width // 2 - 10]
        elif style == "escort_table":
            # d6 column narrow, action columns wider
            d6_col_width = 30
            action_col_width = (width - d6_col_width - 20) // (num_cols - 1) if num_cols > 1 else width - d6_col_width - 20
            col_widths = [d6_col_width] + [action_col_width] * (num_cols - 1)
        elif style == "events_table":
            # Roll column narrow, effect column wide
            col_widths = [50, width - 70]
        else:
            # Default: equal widths
            col_widths = [(width - 20) // num_cols] * num_cols
        
        # Draw column headers
        header_x = x + 5
        for i, header in enumerate(columns):
            col_width = col_widths[i] if i < len(col_widths) else 50
            # Center headers for action_table_card and action_table numeric columns
            if (style == "action_table_card" and i < 4) or (style == "action_table" and i > 0):
                # Center column headers
                header_surface = self.font_small.render(header, True, (220, 230, 150))
                header_center_x = header_x + (col_width - header_surface.get_width()) // 2
                self.screen.blit(header_surface, (header_center_x, y))
            else:
                self.draw_text(header[:20], header_x, y, self.font_small, color=(220, 230, 150))
            
            header_x += col_width
        y += 16
        
        # Draw horizontal line under headers for action_table_card
        if style == "action_table_card":
            pygame.draw.line(self.screen, (70, 90, 120), (x, y), (x + width, y), 1)
            y += 2
        
        # Draw rows
        for row in rows:
            cells = row.get("cells", [])
            row_style = row.get("style", "")
            styles = row.get("styles", [])  # Per-cell styles for damage chart
            comment = row.get("comment", "")
            
            # Calculate row height for action_table_card (need to wrap comment text)
            row_height = 18
            wrapped_comment = []
            if style == "action_table_card" and comment:
                comment_width = width - 20
                wrapped_comment = self._wrap_text(comment, comment_width, self.font_small)
                row_height = 18 + len(wrapped_comment) * 14 + 4
            
            cell_x = x + 5
            cell_y = y
            
            for i, cell in enumerate(cells):
                col_width = col_widths[i] if i < len(col_widths) else 50
                
                # Color based on row style or per-cell style
                if styles and i < len(styles):
                    cell_style = styles[i]
                    if cell_style == "result_critical":
                        color = (255, 100, 100)
                    elif cell_style == "result_warning":
                        color = (255, 200, 100)
                    elif cell_style == "result_ok":
                        color = (150, 220, 150)
                    else:
                        color = (180, 195, 210)
                elif row_style == "critical":
                    color = (255, 100, 100)
                elif row_style == "hull":
                    color = (255, 180, 100)
                elif row_style == "damage":
                    color = (255, 220, 120)
                elif row_style == "crew":
                    color = (200, 200, 255)
                else:
                    color = (180, 195, 210)
                
                # Special handling for action_table_card layout
                if style == "action_table_card":
                    # Draw row background
                    if i == 0:
                        row_bg = pygame.Rect(x + 8, y - 2, width - 16, row_height)
                        pygame.draw.rect(self.screen, (25, 32, 42), row_bg)
                        pygame.draw.rect(self.screen, (50, 62, 78), row_bg, 1)
                    
                    if i == 0:
                        # Bold action name
                        self.draw_text(str(cell), cell_x, cell_y, self.font_small, color=(230, 240, 160))
                    else:
                        # Center AP cost numbers (Surf, Peri, Med, Deep)
                        cell_surface = self.font_small.render(str(cell), True, (180, 195, 210))
                        cell_center_x = cell_x + (col_width - cell_surface.get_width()) // 2
                        self.screen.blit(cell_surface, (cell_center_x, cell_y))
                
                # For action_table: left-align action names, center numbers
                elif style == "action_table":
                    if i == 0:
                        # Left-align action name, no truncation
                        self.draw_text(str(cell), cell_x, cell_y, self.font_small, color=color)
                    else:
                        # Center numbers
                        cell_surface = self.font_small.render(str(cell), True, color)
                        cell_center_x = cell_x + (col_width - cell_surface.get_width()) // 2
                        self.screen.blit(cell_surface, (cell_center_x, cell_y))
                else:
                    # Regular cell rendering for other table types (like damage_chart)
                    max_chars = col_width // 6
                    cell_text = str(cell)[:max_chars]
                    self.draw_text(cell_text, cell_x, cell_y, self.font_small, color=color)
                
                cell_x += col_width
            
            # For action_table_card, draw comment indented under the row
            if style == "action_table_card" and comment:
                comment_y = y + 18
                for comment_line in wrapped_comment:
                    self.draw_text(
                        comment_line,
                        x + 16,
                        comment_y,
                        self.font_small,
                        color=(155, 170, 185)
                    )
                    comment_y += 14
            
            y += row_height + 6
            
            # For action_table, draw comment under the row
            if style == "action_table" and comment:
                # Wrap comment text to fit table width
                comment_wrapped = self._wrap_text(comment, width - 15, self.font_small)
                for comment_line in comment_wrapped:
                    self.draw_text(
                        comment_line,
                        x + 8,
                        y,
                        self.font_small,
                        color=(160, 175, 190)
                    )
                    y += 13
                y += 4  # Extra spacing after comment before next row
        
        # Draw notes (if present)
        if notes:
            y += 4
            for note in notes:
                wrapped = self._wrap_text(note, width - 20, self.font_small)
                for line in wrapped:
                    self.draw_text(
                        f"• {line}" if line == wrapped[0] else f"  {line}",
                        x + 10,
                        y,
                        self.font_small,
                        color=(160, 175, 140)
                    )
                    y += 14
        
        return y
    
    def _draw_global_note(
        self,
        note: Dict[str, Any],
        x: int,
        y: int,
        width: int,
        panel_width: int,
        max_y: int
    ) -> int:
        """Draw a global note block."""
        if y > max_y - 40:
            return y
        
        title = note.get("title", "")
        text_lines = note.get("text", [])
        
        # Background box
        block_height = 20 + len(text_lines) * 15
        block_rect = pygame.Rect(x - 5, y, panel_width - 2*x + 10, min(block_height, max_y - y))
        pygame.draw.rect(self.screen, (45, 50, 30), block_rect)
        pygame.draw.rect(self.screen, (120, 130, 80), block_rect, 1)
        
        # Title
        self.draw_text(title, x + 5, y + 4, self.font_small, color=(220, 230, 150))
        y += 18
        
        # Text lines
        for line in text_lines:
            if y > max_y - 15:
                break
            wrapped = self._wrap_text(line, width - 20, self.font_small)
            for wrapped_line in wrapped:
                self.draw_text(wrapped_line, x + 5, y, self.font_small, color=(190, 200, 160))
                y += 14
                if y > max_y - 15:
                    break
        
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
        
        # Render action preview (outline showing where u-boat will be after queued actions)
        if hasattr(self.game, 'action_queue') and self.game.action_queue.actions:
            self._render_action_preview()
        
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
    
    def _render_action_preview(self) -> None:
        """Render an outline showing where the u-boat will be after all queued actions."""
        # Use queued actions
        actions_to_preview = self.game.action_queue.actions
        
        if not actions_to_preview:
            return
        
        # Calculate preview state by simulating all queued actions
        # Start from either setup state or current state
        if self.awaiting_initial_setup:
            preview_position = self.game.u_boat.position
            preview_facing = self.selected_facing
            preview_depth = self.selected_depth
        else:
            preview_position = self.game.u_boat.position
            preview_facing = self.game.u_boat.facing
            preview_depth = self.game.u_boat.depth
        
        for action in actions_to_preview:
            action_type = type(action).__name__
            
            if action_type == "MoveAction":
                # Move forward in current facing
                new_position = preview_facing.forward(preview_position)
                # Validate new position is within mission hexes
                if new_position in self.game.mission_hexes:
                    preview_position = new_position
                else:
                    # Stop preview at last valid position
                    break
            elif action_type == "RotateAction":
                # Rotate left or right
                assert isinstance(action, RotateAction)
                if action.clockwise:
                    preview_facing = Facing((preview_facing.value + 1) % 6)
                else:
                    preview_facing = Facing((preview_facing.value - 1) % 6)
            elif action_type == "DepthChangeAction":
                # Change depth
                assert isinstance(action, DepthChangeAction)
                preview_depth = action.new_depth
        
        # Only draw if preview differs from current
        if (preview_position != self.game.u_boat.position or 
            preview_facing != self.game.u_boat.facing or
            preview_depth != self.game.u_boat.depth):
            
            # Get pixel position
            center = self.game.renderer.hex_grid.hex_to_pixel(preview_position)
            
            # Define rectangle size (similar to u-boat image size)
            rect_width = 50
            rect_height = 30
            
            # Rotate rectangle based on facing (add 90 degrees to align with forward direction)
            angle_deg = -60 * preview_facing.value - 90
            
            # Depth-based colors (semi-transparent)
            depth_colors = {
                Depth.SURFACED: (100, 200, 255, 180),    # Light blue
                Depth.PERISCOPE: (50, 150, 255, 180),    # Medium blue
                Depth.MEDIUM: (30, 100, 200, 180),       # Dark blue
                Depth.DEEP: (20, 50, 150, 180)           # Very dark blue
            }
            
            color = depth_colors.get(preview_depth, (100, 200, 255, 180))  # type: ignore[arg-type]
            
            # Create a surface for the rotated rectangle
            # Make it larger to accommodate rotation
            surf_size = int((rect_width + rect_height) * 1.5)
            temp_surface = pygame.Surface((surf_size, surf_size), pygame.SRCALPHA)
            
            # Draw rectangle at center of temp surface
            rect_x = (surf_size - rect_width) // 2
            rect_y = (surf_size - rect_height) // 2
            
            # Draw filled rectangle with transparency
            pygame.draw.rect(temp_surface, color, 
                           (rect_x, rect_y, rect_width, rect_height))
            
            # Draw outline (thicker, more visible)
            pygame.draw.rect(temp_surface, (255, 255, 255, 255), 
                           (rect_x, rect_y, rect_width, rect_height), 3)
            
            # Rotate the surface
            rotated_surface = pygame.transform.rotate(temp_surface, angle_deg)
            
            # Blit to screen centered on hex
            rect = rotated_surface.get_rect(center=(int(center[0]), int(center[1])))
            self.screen.blit(rotated_surface, rect)
    
    def _draw_right_panel(self, x: int, y: int, width: int, height: int) -> None:
        """Draw the right panel with dice rolls, action queue, event log, and controls."""
        panel_rect = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.screen, (20, 25, 35), panel_rect)
        pygame.draw.line(self.screen, (50, 70, 100), (x, y), (x, y+height), 2)
        
        # Split panel into four areas: dice rolls (top), action queue, event log (middle), controls (bottom)
        dice_area_height = 150
        action_queue_height = 250
        controls_area_height = 200
        queue_area_y = y + dice_area_height
        log_area_y = y + dice_area_height + action_queue_height
        log_area_height = height - dice_area_height - action_queue_height - controls_area_height
        controls_area_y = y + dice_area_height + action_queue_height + log_area_height
        
        # === DICE ROLL SECTION ===
        self.draw_text(
            "DICE ROLLS",
            x + width // 2,
            y + 15,
            self.font_medium,
            color=(255, 220, 100),
            center=True
        )
        
        dice_y = y + 45
        dice_x = x + 10
        
        # Show AP roll details if available
        if hasattr(self.game, 'turn_manager') and self.game.turn_manager.last_ap_roll:
            roll_info = self.game.turn_manager.last_ap_roll
            
            # Dice type label
            num_dice = roll_info['num_dice']
            dice_label = f"{num_dice}d6"
            if roll_info['engine_damaged']:
                dice_label += " (Engine Dmg)"
            
            self.draw_text(
                f"AP Roll [{dice_label}]:",
                dice_x,
                dice_y,
                self.font_small,
                color=(200, 200, 200)
            )
            dice_y += 20
            
            # Individual dice with colored boxes
            rolls = roll_info['rolls']
            highest = roll_info['highest']
            
            # Draw dice as small colored boxes
            box_x = dice_x + 10
            box_size = 20
            box_spacing = 5
            
            for _, roll_val in enumerate(rolls):
                box_rect = pygame.Rect(box_x, dice_y, box_size, box_size)
                
                # Highlight highest die
                if roll_val == highest:
                    box_color = (100, 200, 100)  # Green for highest
                    text_color = (255, 255, 255)
                else:
                    box_color = (60, 60, 80)
                    text_color = (180, 180, 180)
                
                pygame.draw.rect(self.screen, box_color, box_rect)
                pygame.draw.rect(self.screen, (150, 150, 150), box_rect, 1)
                
                # Draw die value centered
                self.draw_text(
                    str(roll_val),
                    box_rect.centerx,
                    box_rect.centery,
                    self.font_small,
                    color=text_color,
                    center=True
                )
                
                box_x += box_size + box_spacing
            
            dice_y += 30
            
            # Result breakdown
            result_text = f"Highest: {highest}"
            if roll_info['captain_bonus'] > 0:
                result_text += f" +{roll_info['captain_bonus']} (Captain)"
            result_text += f" = {roll_info['total_ap']} AP"
            
            self.draw_text(
                result_text,
                dice_x,
                dice_y,
                self.font_small,
                color=(100, 255, 150)
            )
            dice_y += 25
        
        # Show other combat rolls (last 3)
        visible_rolls = self.dice_rolls[-3:] if self.dice_rolls else []
        if visible_rolls:
            for roll_info in visible_rolls:
                action = roll_info.get('action', 'Unknown')
                dice = roll_info.get('dice', '?')
                result = roll_info.get('result', '?')
                
                roll_text = f"{action}: [{dice}] = {result}"
                self.draw_text(roll_text, dice_x, dice_y, self.font_small, color=(255, 255, 150))
                dice_y += 18
        elif not (hasattr(self.game, 'turn_manager') and self.game.turn_manager.last_ap_roll):
            self.draw_text("No rolls yet", dice_x, dice_y, self.font_small, color=(120, 120, 120))
        
        # Separator line
        pygame.draw.line(
            self.screen,
            (50, 70, 100),
            (x, queue_area_y),
            (x + width, queue_area_y),
            2
        )
        
        # === ACTION QUEUE SECTION ===
        self._draw_action_queue(x, queue_area_y, width, action_queue_height)
        
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
        
        # Calculate how many events to show based on scroll position
        # scroll = 0 means show latest (bottom), scroll > 0 means show older events
        total_events = len(self.event_log)
        if self.event_log_scroll == 0:
            # Show latest events (scrolled to bottom)
            visible_events = self.event_log[-40:]
        else:
            # Show older events based on scroll position
            end_idx = total_events - self.event_log_scroll
            start_idx = max(0, end_idx - 40)
            visible_events = self.event_log[start_idx:end_idx]
        
        # Show scroll indicator if not at bottom
        if self.event_log_scroll > 0:
            scroll_text = f"[Scrolled up {self.event_log_scroll} events - Use mouse wheel to scroll]"
            self.draw_text(scroll_text, x + width // 2, log_y - 20, self.font_small, 
                          color=(255, 200, 100), center=True)
        
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
    
    def _draw_action_queue(self, x: int, y: int, width: int, height: int) -> None:
        """Draw the action queue with queued actions, AP, and Undo/Commit buttons."""
        self.draw_text(
            "ACTION QUEUE",
            x + width // 2,
            y + 15,
            self.font_medium,
            color=(100, 255, 150),
            center=True
        )
        
        # Show remaining AP
        if hasattr(self.game, 'action_queue'):
            remaining_ap = self.game.action_queue.get_remaining_ap(self.game)
            total_ap = self.game.action_queue.max_ap
            
            ap_text = f"AP: {remaining_ap}/{total_ap}"
            ap_color = (100, 255, 100) if remaining_ap > 0 else (150, 150, 150)
            self.draw_text(
                ap_text,
                x + width // 2,
                y + 40,
                self.font_medium,
                color=ap_color,
                center=True
            )
            
            # Show queued actions
            queue_y = y + 70
            queue_x = x + 10
            
            if self.game.action_queue.actions:
                for idx, action in enumerate(self.game.action_queue.actions, 1):
                    # Action description
                    action_name = self._get_action_description(action)
                    action_cost = action.get_cost(self.game.u_boat)
                    
                    action_text = f"{idx}. {action_name} ({action_cost} AP)"
                    self.draw_text(
                        action_text,
                        queue_x,
                        queue_y,
                        self.font_small,
                        color=(220, 240, 255)
                    )
                    queue_y += 20
                    
                    # Stop if we run out of space
                    if queue_y > y + height - 80:
                        break
            else:
                self.draw_text(
                    "No actions queued",
                    queue_x,
                    queue_y,
                    self.font_small,
                    color=(120, 120, 120)
                )
            
            # Buttons at bottom - only show if NOT in deck gun resolution
            if not self.deck_gun_resolution_state:
                button_y = y + height - 55
                button_width = (width - 30) // 2
                button_height = 40
                
                # Undo button (left)
                undo_rect = pygame.Rect(x + 10, button_y, button_width, button_height)
                undo_color = (100, 50, 50) if self.game.action_queue.actions else (40, 40, 40)
                pygame.draw.rect(self.screen, undo_color, undo_rect)
                pygame.draw.rect(self.screen, (150, 100, 100), undo_rect, 2)
                self.draw_text(
                    "UNDO (U)",
                    undo_rect.centerx,
                    undo_rect.centery,
                    self.font_small,
                    color=(255, 200, 200) if self.game.action_queue.actions else (100, 100, 100),
                    center=True
                )
                
                # Commit button (right)
                commit_rect = pygame.Rect(x + 20 + button_width, button_y, button_width, button_height)
                commit_color = (50, 100, 50) if self.game.action_queue.actions else (40, 40, 40)
                pygame.draw.rect(self.screen, commit_color, commit_rect)
                pygame.draw.rect(self.screen, (100, 150, 100), commit_rect, 2)
                self.draw_text(
                    "COMMIT (C)",
                    commit_rect.centerx,
                    commit_rect.centery,
                    self.font_small,
                    color=(200, 255, 200) if self.game.action_queue.actions else (100, 100, 100),
                    center=True
                )
                
                self.undo_button_rect = undo_rect
                self.commit_button_rect = commit_rect
            else:
                self.undo_button_rect = None
                self.commit_button_rect = None
        else:
            self.draw_text(
                "Action queue not initialized",
                x + width // 2,
                y + height // 2,
                self.font_small,
                color=(120, 120, 120),
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
        """Draw action selection buttons."""
        self.draw_text(
            "ACTIONS",
            x + width // 2,
            y + 10,
            self.font_small,
            color=(255, 220, 100),
            center=True
        )
        
        # Check if we need to roll dice first
        from ..models import GamePhase
        if (self.game.turn_manager.current_phase == GamePhase.UBOAT_PHASE and 
            self.game.turn_manager.ap_tracker is None):
            self._draw_dice_roll_button(x, y + 35, width)
            return
        
        # Check if in deck gun resolution mode
        if self.deck_gun_resolution_state:
            self._draw_deck_gun_resolution(x, y + 35, width)
            return
        
        # Check if in torpedo resolution mode
        if self.torpedo_resolution_state:
            self._draw_torpedo_resolution(x, y + 35, width)
            return
        
        # Check if in torpedo loading selection mode
        if self.load_torpedo_selection_state:
            self._draw_torpedo_loading_selection(x, y + 35, width)
            return
        
        # Clear button rects
        self.action_button_rects.clear()
        
        button_y = y + 35
        button_x = x + 10
        button_width = width - 20
        button_height = 25
        button_spacing = 3
        
        u_boat = self.game.u_boat
        
        # Calculate torpedo states
        loaded_tubes = sum(1 for tube in u_boat.torpedo_tubes if tube)
        empty_tubes = len(u_boat.torpedo_tubes) - loaded_tubes
        
        # Get action cost lookup
        from ..action_costs import ActionCostLookup
        cost_lookup = ActionCostLookup(self.game.mission_rules)
        
        # Define action buttons with cost info
        # Format: (label, action_id, enabled, action_name_for_cost)
        actions: list[tuple[str, str, bool, str]] = [
            ("MOVE FORWARD", "move", u_boat.depth != Depth.DEEP, "MOVE"),
            ("ROTATE LEFT", "rotate_l", True, "TURN"),
            ("ROTATE RIGHT", "rotate_r", True, "TURN"),
            ("DIVE", "dive", u_boat.depth != Depth.DEEP, "CHANGE DEPTH"),
            ("SURFACE", "surface", u_boat.depth != Depth.SURFACED, "CHANGE DEPTH"),
            ("REPAIR", "repair", u_boat.engine_damaged or u_boat.deck_gun_damaged or u_boat.flak_gun_damaged, "REPAIR"),
            ("FIRE DECK GUN", "deck_gun", self._has_valid_deck_gun_targets(), "FIRE DECK GUN"),
            ("LOAD TORPEDOES", "load_torp", empty_tubes > 0, "LOAD TORPS"),
        ]
        
        # Add individual torpedo tube fire buttons
        can_fire_depth = u_boat.depth == Depth.SURFACED or u_boat.depth == Depth.PERISCOPE
        for tube_num in range(1, 6):
            tube_idx = tube_num - 1
            is_loaded = u_boat.torpedo_tubes[tube_idx]
            # TODO: Add tube damaged check when damage system implemented
            is_damaged = False  # u_boat.torpedo_tubes_damaged[tube_idx]
            tube_type = "Front" if tube_num <= 4 else "Rear"
            
            if is_loaded and not is_damaged:
                status = "Loaded"
            elif is_damaged:
                status = "Damaged"
            else:
                status = "Empty"
            
            label = f"FIRE TUBE {tube_num} ({tube_type}): {status}"
            enabled = is_loaded and not is_damaged and can_fire_depth
            actions.append((label, f"fire_torp_{tube_num}", enabled, "FIRE TORPS"))
        
        for label, action_id, enabled, action_name in actions:
            rect = pygame.Rect(button_x, button_y, button_width, button_height)
            
            # Get action cost
            cost = cost_lookup.get_cost(action_name, u_boat.depth)
            
            # Build label with cost
            if cost is not None:
                full_label = f"{label} - {cost} AP"
            elif enabled:
                full_label = label  # No cost info available
            else:
                full_label = f"{label} - N/A"
            
            # Check if button is clickable (enabled AND enough AP)
            can_afford = cost is not None and cost <= u_boat.action_points
            is_clickable = enabled and can_afford
            
            # Store rect AND clickable state
            self.action_button_rects[action_id] = (rect, is_clickable)
            
            # Check hover state
            mouse_pos = pygame.mouse.get_pos()
            is_hover = rect.collidepoint(mouse_pos)
            
            # Button color based on availability and hover
            if is_clickable:
                if is_hover:
                    color = (80, 110, 140)  # Lighter on hover
                    border_color = (120, 180, 230)
                else:
                    color = (60, 80, 100)
                    border_color = (100, 150, 200)
                text_color = (200, 220, 255)
            elif enabled:
                # Enabled but not enough AP
                color = (80, 80, 60)
                border_color = (120, 120, 80)
                text_color = (180, 180, 140)
            else:
                color = (40, 40, 40)
                border_color = (80, 80, 80)
                text_color = (100, 100, 100)
            
            pygame.draw.rect(self.screen, color, rect)
            pygame.draw.rect(self.screen, border_color, rect, 1)
            self.draw_text(full_label, rect.centerx, rect.centery, self.font_small, 
                          color=text_color, center=True)
            
            button_y += button_height + button_spacing
        
        # Info section: Depth cost modifiers
        info_y = button_y + 10
        
        # Show current depth and its effect on costs
        depth_name = u_boat.depth.name
        self.draw_text(
            f"At {depth_name}:",
            x + width // 2,
            info_y,
            self.font_small,
            color=(150, 170, 200),
            center=True
        )
        info_y += 18
        
        # Show cost for common actions at this depth vs surfaced
        surfaced_move = cost_lookup.get_cost("MOVE", Depth.SURFACED)
        current_move = cost_lookup.get_cost("MOVE", u_boat.depth)
        surfaced_turn = cost_lookup.get_cost("TURN", Depth.SURFACED)
        current_turn = cost_lookup.get_cost("TURN", u_boat.depth)
        
        if surfaced_move and current_move:
            move_diff = current_move - surfaced_move
            move_text = f"Move: {current_move} AP"
            if move_diff > 0:
                move_text += f" (+{move_diff})"
            self.draw_text(
                move_text,
                x + 10,
                info_y,
                self.font_small,
                color=(180, 180, 180)
            )
        
        if surfaced_turn and current_turn:
            turn_diff = current_turn - surfaced_turn
            turn_text = f"Turn: {current_turn} AP"
            if turn_diff > 0:
                turn_text += f" (+{turn_diff})"
            self.draw_text(
                turn_text,
                x + 10,
                info_y + 15,
                self.font_small,
                color=(180, 180, 180)
            )
        
        # Add SPACE bar hint at bottom of action panel
        from ..models import GamePhase
        phase_hint_y = y + height - 60
        
        # Draw separator line
        pygame.draw.line(
            self.screen,
            (80, 80, 80),
            (x + 10, phase_hint_y - 10),
            (x + width - 10, phase_hint_y - 10),
            1
        )
        
        # Show current phase and SPACE hint
        current_phase_name = self.game.turn_manager.get_current_phase_name()
        self.draw_text(
            f"Current: {current_phase_name}",
            x + width // 2,
            phase_hint_y,
            self.font_small,
            color=(200, 200, 150),
            center=True
        )
        
        # SPACE bar hint
        self.draw_text(
            "Press SPACE to advance phase",
            x + width // 2,
            phase_hint_y + 20,
            self.font_small,
            color=(100, 255, 100),
            center=True
        )
    
    def _get_action_description(self, action: Any) -> str:
        """Get descriptive name for an action."""
        action_type = type(action).__name__
        
        if action_type == "RotateAction":
            return "Rotate Left" if not action.clockwise else "Rotate Right"
        elif action_type == "DepthChangeAction":
            depth_names = {0: "Surfaced", 1: "Periscope", 2: "Medium", 3: "Deep"}
            target_name = depth_names.get(action.new_depth.value, "Unknown")
            return f"Depth → {target_name}"
        elif action_type == "MoveAction":
            return "Move Forward"
        elif action_type == "RepairAction":
            return f"Repair {action.repair_target.replace('_', ' ').title()}"
        elif action_type == "DeckGunAction":
            return "Fire Deck Gun"
        elif action_type == "LoadTorpedoAction":
            return "Load Torpedo"
        elif action_type == "FireTorpedoAction":
            return "Fire Torpedo"
        else:
            return action_type.replace('Action', '')
    
    def _has_valid_deck_gun_targets(self) -> bool:
        """Check if any ships are in LOS and range 1-3 for deck gun."""
        u_boat = self.game.u_boat
        
        # Must be surfaced
        if u_boat.depth != Depth.SURFACED:
            return False
        
        # Deck gun must not be damaged
        if u_boat.deck_gun_damaged:
            return False
        
        # Check if any ship is in range 1-3 with LOS
        from ..hex_grid import HexGrid
        from ..los import LOSCalculator
        
        los_calc = LOSCalculator(self.game.land_hexes)
        
        for ship in self.game.ships:
            distance = HexGrid.hex_distance(u_boat.position, ship.position)
            if 1 <= distance <= 3:
                has_los, _ = los_calc.has_line_of_sight(
                    u_boat.position,
                    ship.position
                )
                if has_los:
                    return True
        
        return False
    
    def _draw_dice_roll_button(self, x: int, y: int, width: int) -> None:
        """Draw the dice roll button."""
        button_width = width - 40
        button_height = 60
        button_x = x + 20
        button_y = y + 20
        
        # Store button rect for click detection
        self.dice_roll_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        
        # Draw button background
        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.dice_roll_button_rect.collidepoint(mouse_pos)
        button_color = (80, 120, 80) if is_hover else (60, 100, 60)
        border_color = (120, 200, 120) if is_hover else (100, 170, 100)
        
        pygame.draw.rect(self.screen, button_color, self.dice_roll_button_rect)
        pygame.draw.rect(self.screen, border_color, self.dice_roll_button_rect, 3)
        
        # Draw button text
        text1 = "CLICK TO"
        text2 = "ROLL DICE"
        self.draw_text(text1, self.dice_roll_button_rect.centerx, self.dice_roll_button_rect.centery - 12,
                      self.font_medium, color=(255, 255, 255), center=True)
        self.draw_text(text2, self.dice_roll_button_rect.centerx, self.dice_roll_button_rect.centery + 12,
                      self.font_medium, color=(255, 255, 255), center=True)
    
    def _draw_deck_gun_resolution(self, x: int, y: int, width: int) -> None:
        """Draw the interactive deck gun resolution UI."""
        state = self.deck_gun_resolution_state
        if not state:
            return
        
        current_idx = state['current_idx']
        targets = state['targets']
        
        # Check if all targets resolved
        if current_idx >= len(targets):
            # All done - automatically finish without showing summary
            self._finish_deck_gun_resolution()
            return
        
        ship, distance = targets[current_idx]
        waiting_for = state['waiting_for']
        
        # Draw target info
        info_y = y
        self.draw_text(
            f"TARGET: {ship.ship_type.upper()} at range {distance}",
            x + width // 2,
            info_y,
            self.font_small,
            color=(255, 220, 100),
            center=True
        )
        info_y += 20
        
        self.draw_text(
            f"({current_idx + 1} of {len(targets)} ships)",
            x + width // 2,
            info_y,
            self.font_small,
            color=(180, 180, 180),
            center=True
        )
        info_y += 25
        
        # Initialize defaults
        button_color = (60, 80, 100)
        border_color = (100, 140, 180)
        button_text1 = "CLICK"
        button_text2 = "BUTTON"
        
        # Show what we're waiting for
        if waiting_for == 'hit':
            # Show hit target number
            hit_target = "7+" if distance <= 2 else "8+"
            self.draw_text(
                f"Need {hit_target} on 2d6 to hit",
                x + width // 2,
                info_y,
                self.font_small,
                color=(200, 200, 200),
                center=True
            )
            info_y += 25
            
            button_text1 = "CLICK TO"
            button_text2 = "ROLL FOR HIT"
            button_color = (100, 60, 60)
            border_color = (180, 100, 100)
        
        elif waiting_for == 'damage':
            # Show last hit roll
            hit_roll = state['last_hit_roll']
            self.draw_text(
                f"HIT! Rolled {hit_roll['total']}",
                x + width // 2,
                info_y,
                self.font_small,
                color=(100, 255, 100),
                center=True
            )
            info_y += 25
            
            button_text1 = "CLICK TO"
            button_text2 = "ROLL DAMAGE"
            button_color = (100, 80, 60)
            border_color = (180, 140, 100)
        
        elif waiting_for == 'continue':
            # Show result based on whether we hit and rolled damage
            if state['last_damage_roll']:
                # We hit and rolled damage
                hit_roll = state['last_hit_roll']
                self.draw_text(
                    f"HIT! Rolled {hit_roll['total']}",
                    x + width // 2,
                    info_y,
                    self.font_small,
                    color=(100, 255, 100),
                    center=True
                )
                info_y += 25
                
                damage_roll = state['last_damage_roll']
                self.draw_text(
                    f"Damage: {damage_roll['description']}",
                    x + width // 2,
                    info_y,
                    self.font_small,
                    color=(255, 200, 100),
                    center=True
                )
                info_y += 20
            else:
                # We missed
                hit_roll = state['last_hit_roll']
                self.draw_text(
                    f"MISS! Rolled {hit_roll['total']}",
                    x + width // 2,
                    info_y,
                    self.font_small,
                    color=(255, 100, 100),
                    center=True
                )
                info_y += 25
            
            button_text1 = "CONTINUE TO"
            button_text2 = "NEXT TARGET"
            button_color = (60, 80, 100)
            border_color = (100, 140, 180)
        
        # Draw button
        button_width = width - 40
        button_height = 60
        button_x = x + 20
        button_y = info_y + 10
        
        self.deck_gun_roll_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        
        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.deck_gun_roll_button_rect.collidepoint(mouse_pos)
        
        if is_hover:
            button_color = tuple(min(c + 30, 255) for c in button_color)
            border_color = tuple(min(c + 30, 255) for c in border_color)
        
        pygame.draw.rect(self.screen, button_color, self.deck_gun_roll_button_rect)
        pygame.draw.rect(self.screen, border_color, self.deck_gun_roll_button_rect, 3)
        
        self.draw_text(
            button_text1,
            self.deck_gun_roll_button_rect.centerx,
            self.deck_gun_roll_button_rect.centery - 12,
            self.font_medium,
            color=(255, 255, 255),
            center=True
        )
        self.draw_text(
            button_text2,
            self.deck_gun_roll_button_rect.centerx,
            self.deck_gun_roll_button_rect.centery + 12,
            self.font_medium,
            color=(255, 255, 255),
            center=True
        )
    
    def _draw_deck_gun_summary(self, x: int, y: int, width: int, state: Dict[str, Any]) -> None:
        """Draw summary after all targets resolved."""
        results = state['results']
        
        info_y = y
        self.draw_text(
            "DECK GUN COMPLETE",
            x + width // 2,
            info_y,
            self.font_medium,
            color=(100, 255, 100),
            center=True
        )
        info_y += 30
        
        # Count hits
        hits = sum(1 for _, _, hit, _ in results if hit)
        self.draw_text(
            f"{hits} hit(s) out of {len(results)} target(s)",
            x + width // 2,
            info_y,
            self.font_small,
            color=(200, 200, 200),
            center=True
        )
        info_y += 30
        
        # Finish button
        button_width = width - 40
        button_height = 50
        button_x = x + 20
        button_y = info_y + 10
        
        self.deck_gun_roll_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        
        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.deck_gun_roll_button_rect.collidepoint(mouse_pos)
        button_color = (80, 120, 80) if is_hover else (60, 100, 60)
        border_color = (120, 200, 120) if is_hover else (100, 170, 100)
        
        pygame.draw.rect(self.screen, button_color, self.deck_gun_roll_button_rect)
        pygame.draw.rect(self.screen, border_color, self.deck_gun_roll_button_rect, 3)
        
        self.draw_text(
            "FINISH",
            self.deck_gun_roll_button_rect.centerx,
            self.deck_gun_roll_button_rect.centery,
            self.font_medium,
            color=(255, 255, 255),
            center=True
        )
    
    def _draw_torpedo_loading_selection(self, x: int, y: int, width: int) -> None:
        """Draw torpedo tube selection UI for loading."""
        state = self.load_torpedo_selection_state
        if not state:
            return
        
        self.tube_checkbox_rects.clear()
        
        u_boat = state['u_boat']
        selected_tubes = state['selected_tubes']
        max_tubes = state['max_tubes']
        
        # Title
        info_y = y
        self.draw_text(
            "LOAD TORPEDOES",
            x + width // 2,
            info_y,
            self.font_medium,
            color=(100, 200, 255),
            center=True
        )
        info_y += 30
        
        # Info text
        cost = state['cost_lookup'].get_cost("LOAD TORPS", u_boat.depth)
        cost_text = f"Cost: {cost} AP" if cost is not None else "Cost: N/A"
        self.draw_text(
            f"Select up to {max_tubes} tube(s) | {cost_text}",
            x + width // 2,
            info_y,
            self.font_small,
            color=(180, 180, 180),
            center=True
        )
        info_y += 25
        
        # Tube checkboxes
        checkbox_size = 20
        label_x = x + 20
        checkbox_x = x + width - 40
        
        for tube_num in range(1, 6):
            tube_idx = tube_num - 1  # 0-based index
            is_loaded = u_boat.torpedo_tubes[tube_idx]
            is_selected = tube_num in selected_tubes
            is_available = not is_loaded
            
            # Tube label
            tube_type = "Front" if tube_num <= 4 else "Rear"
            if is_loaded:
                status = "Loaded"
                status_color = (100, 255, 100)
            elif is_selected:
                status = "Selected"
                status_color = (255, 220, 100)
            else:
                status = "Empty"
                status_color = (150, 150, 150)
            
            label_text = f"Tube {tube_num} ({tube_type})"
            self.draw_text(
                label_text,
                label_x,
                info_y + checkbox_size // 2,
                self.font_small,
                color=(200, 200, 200)
            )
            
            self.draw_text(
                status,
                label_x + 120,
                info_y + checkbox_size // 2,
                self.font_small,
                color=status_color
            )
            
            # Checkbox
            checkbox_rect = pygame.Rect(checkbox_x, info_y, checkbox_size, checkbox_size)
            self.tube_checkbox_rects[tube_num] = checkbox_rect
            
            # Checkbox appearance
            if is_available:
                if is_selected:
                    pygame.draw.rect(self.screen, (100, 200, 255), checkbox_rect)
                    pygame.draw.rect(self.screen, (150, 220, 255), checkbox_rect, 2)
                    # Draw checkmark
                    pygame.draw.line(self.screen, (255, 255, 255),
                                   (checkbox_rect.left + 4, checkbox_rect.centery),
                                   (checkbox_rect.centerx, checkbox_rect.bottom - 4), 2)
                    pygame.draw.line(self.screen, (255, 255, 255),
                                   (checkbox_rect.centerx, checkbox_rect.bottom - 4),
                                   (checkbox_rect.right - 4, checkbox_rect.top + 4), 2)
                else:
                    pygame.draw.rect(self.screen, (60, 60, 60), checkbox_rect)
                    pygame.draw.rect(self.screen, (120, 120, 120), checkbox_rect, 2)
            else:
                # Disabled (already loaded)
                pygame.draw.rect(self.screen, (40, 40, 40), checkbox_rect)
                pygame.draw.rect(self.screen, (80, 80, 80), checkbox_rect, 1)
            
            info_y += checkbox_size + 8
        
        # Confirm and Cancel buttons
        info_y += 10
        button_height = 35
        button_width = (width - 50) // 2
        
        # Confirm button
        confirm_x = x + 15
        self.confirm_load_button_rect = pygame.Rect(confirm_x, info_y, button_width, button_height)
        
        can_confirm = len(selected_tubes) > 0
        if can_confirm:
            confirm_color = (60, 120, 60)
            confirm_border = (100, 200, 100)
            confirm_text_color = (200, 255, 200)
        else:
            confirm_color = (40, 40, 40)
            confirm_border = (80, 80, 80)
            confirm_text_color = (100, 100, 100)
        
        pygame.draw.rect(self.screen, confirm_color, self.confirm_load_button_rect)
        pygame.draw.rect(self.screen, confirm_border, self.confirm_load_button_rect, 2)
        self.draw_text(
            "CONFIRM",
            self.confirm_load_button_rect.centerx,
            self.confirm_load_button_rect.centery,
            self.font_small,
            color=confirm_text_color,
            center=True
        )
        
        # Cancel button
        cancel_x = confirm_x + button_width + 20
        self.cancel_load_button_rect = pygame.Rect(cancel_x, info_y, button_width, button_height)
        
        cancel_color = (80, 60, 60)
        cancel_border = (150, 100, 100)
        cancel_text_color = (255, 200, 200)
        
        pygame.draw.rect(self.screen, cancel_color, self.cancel_load_button_rect)
        pygame.draw.rect(self.screen, cancel_border, self.cancel_load_button_rect, 2)
        self.draw_text(
            "CANCEL",
            self.cancel_load_button_rect.centerx,
            self.cancel_load_button_rect.centery,
            self.font_small,
            color=cancel_text_color,
            center=True
        )
    
    def _handle_deck_gun_roll(self) -> None:
        """Handle clicking the deck gun resolution button."""
        state = self.deck_gun_resolution_state
        if not state:
            return
        
        current_idx = state['current_idx']
        targets = state['targets']
        
        # Check if all targets resolved - finish button
        if current_idx >= len(targets):
            self._finish_deck_gun_resolution()
            return
        
        ship, distance = targets[current_idx]
        waiting_for = state['waiting_for']
        
        if waiting_for == 'hit':
            # Roll for hit
            from ..combat_resolver import CombatResolver
            resolver = CombatResolver(self.game.turn_manager.dice, self.game.mission_rules)
            
            hit, roll_total, description = resolver.resolve_deck_gun_attack(distance)
            
            state['last_hit_roll'] = {
                'total': roll_total,
                'hit': hit,
                'description': description
            }
            
            if hit:
                # Need to roll damage
                state['waiting_for'] = 'damage'
                self.add_event(f"Targeting {ship.ship_type} at range {distance}: HIT! (Rolled {roll_total})")
            else:
                # Miss - check if this is the last target
                state['results'].append((ship, distance, False, None))
                self.add_event(f"Targeting {ship.ship_type} at range {distance}: MISS (Rolled {roll_total})")
                
                # If this was the last target, finish automatically
                if current_idx + 1 >= len(targets):
                    self._finish_deck_gun_resolution()
                else:
                    # More targets remain - show continue button
                    state['waiting_for'] = 'continue'
        
        elif waiting_for == 'damage':
            # Roll for damage
            from ..combat_resolver import CombatResolver
            resolver = CombatResolver(self.game.turn_manager.dice, self.game.mission_rules)
            
            # Roll 1d6 for damage
            damage_die = resolver.dice.roll_1d6()
            
            # Determine damage result
            if damage_die <= 3:
                damage_desc = f"Rolled {damage_die}: No damage"
            elif damage_die <= 5:
                damage_desc = f"Rolled {damage_die}: 1 damage point"
            else:
                damage_desc = f"Rolled {damage_die}: 2 damage points"
            
            state['last_damage_roll'] = {
                'die': damage_die,
                'description': damage_desc
            }
            
            state['results'].append((ship, distance, True, damage_die))
            self.add_event(f"  Damage roll: {damage_desc}")
            
            # If this was the last target, finish automatically
            if current_idx + 1 >= len(targets):
                self._finish_deck_gun_resolution()
            else:
                # More targets remain - show continue button
                state['waiting_for'] = 'continue'
        
        elif waiting_for == 'continue':
            # Move to next target
            state['current_idx'] += 1
            state['waiting_for'] = 'hit'
            state['last_hit_roll'] = None
            state['last_damage_roll'] = None
            
            # If that was the last target, automatically finish
            if state['current_idx'] >= len(targets):
                self._finish_deck_gun_resolution()
    
    def _finish_deck_gun_resolution(self) -> None:
        """Finish deck gun resolution and continue with queue commit."""
        state = self.deck_gun_resolution_state
        if not state:
            return
        
        results = state['results']
        hits = sum(1 for _, _, hit, _ in results if hit)
        
        # Get the action from state
        action = state.get('action')
        action_index = state.get('action_index', 0)
        
        # Apply deck gun results
        if action:
            # Import ship damage resolver
            from ..damage import ShipDamageResolver
            damage_resolver = ShipDamageResolver(self.game.turn_manager.dice, self.game.mission_rules)
            
            # Build message from results and apply damage
            result_msgs: list[str] = []
            
            # Process each target sequentially, removing sunk ships immediately
            for ship, distance, hit, _ in results:
                # Skip if ship was already sunk by a previous attack in this volley
                if ship not in self.game.ships:
                    continue
                
                if hit:
                    # Apply proper damage using ShipDamageResolver
                    damage_result = damage_resolver.apply_damage(ship, "deck_gun")
                    
                    # Log the damage result
                    if damage_result.is_now_sunk:
                        result_msgs.append(
                            f"HIT {ship.ship_type} at range {distance} - {damage_result.description} - SUNK!"
                        )
                        # Remove ship immediately
                        if ship in self.game.ships:
                            self.game.ships.remove(ship)
                            self.add_event(f"💀 {ship.ship_type.title()} SUNK and removed from map")
                    elif damage_result.effect == "damaged":
                        # Apply damage marker immediately
                        ship.damaged = True
                        result_msgs.append(
                            f"HIT {ship.ship_type} at range {distance} - DAMAGED (roll: {damage_result.roll})"
                        )
                        self.add_event(f"💥 {ship.ship_type.title()} DAMAGED")
                        # Render immediately to show damage marker
                        self.render()
                        pygame.display.flip()
                    else:  # no_effect
                        result_msgs.append(
                            f"HIT {ship.ship_type} at range {distance} - No effect (roll: {damage_result.roll})"
                        )
                else:
                    result_msgs.append(f"MISS {ship.ship_type} at range {distance}")
            
            message = f"Deck gun fired at {len(results)} ship(s): {hits} hit(s). " + "; ".join(result_msgs)
            
            # Set detection level to 3 if any hits
            if hits > 0:
                message += " (DL set to 3)"
                self.game.detection_level = 3
            
            # Get cost
            cost = action.get_cost(self.game.u_boat)
            
            # Manually apply the action result
            self.game.u_boat.action_points -= cost
            
            # Log result
            self.add_event(f"✓ Deck Gun: {message}")
            
            # Remove this action from queue
            if action_index < len(self.game.action_queue.actions):
                self.game.action_queue.actions.pop(action_index)
        
        # Clear resolution state
        self.deck_gun_resolution_state = None
        self.deck_gun_roll_button_rect = None
        
        # Execute all non-deck-gun actions before next deck gun
        # This ensures moves/rotates happen before we recalculate targets
        # AND updates the u-boat position visually on screen
        non_deck_gun_actions = [a for a in self.game.action_queue.actions if not isinstance(a, DeckGunAction)]
        if non_deck_gun_actions:
            for action in non_deck_gun_actions:
                result = action.execute(self.game)
                if result.success:
                    action_name = result.state_changes.get('action_name', type(action).__name__.replace('Action', ''))
                    self.add_event(f"✓ {action_name}")
                    self.game.u_boat.action_points -= result.ap_spent
                    
                    # Apply state changes immediately for visual feedback
                    if 'new_position' in result.state_changes:
                        self.game.u_boat.position = result.state_changes['new_position']
                    if 'new_facing' in result.state_changes:
                        self.game.u_boat.facing = result.state_changes['new_facing']
                    if 'new_depth' in result.state_changes:
                        self.game.u_boat.depth = result.state_changes['new_depth']
                else:
                    self.add_event(f"✗ Action failed: {result.message}")
            # Remove executed actions from queue
            self.game.action_queue.actions = [a for a in self.game.action_queue.actions if isinstance(a, DeckGunAction)]
        
        # Check if there are more deck gun actions in the remaining queue
        remaining_deck_guns = [i for i, a in enumerate(self.game.action_queue.actions) if isinstance(a, DeckGunAction)]
        
        if remaining_deck_guns:
            # Start interactive resolution for the next deck gun
            next_idx = remaining_deck_guns[0]
            next_action = self.game.action_queue.actions[next_idx]
            
            # Recalculate targets based on CURRENT u-boat position
            from ..los import LOSCalculator
            from ..hex_grid import HexGrid
            
            los_calc = LOSCalculator(self.game.land_hexes)
            current_targets: List[Tuple[Ship, int]] = []
            for ship in self.game.ships:
                distance = HexGrid.hex_distance(self.game.u_boat.position, ship.position)
                if 1 <= distance <= 3:
                    has_los, _ = los_calc.has_line_of_sight(
                        self.game.u_boat.position,
                        ship.position
                    )
                    if has_los:
                        current_targets.append((ship, distance))
            
            # Sort by distance (closest first)
            import random
            current_targets.sort(key=lambda ship_tuple: (ship_tuple[1], random.random()))
            
            self.deck_gun_resolution_state = {
                'action': next_action,
                'action_index': next_idx,
                'targets': current_targets,  # Use recalculated targets
                'current_idx': 0,
                'waiting_for': 'hit',
                'last_hit_roll': None,
                'last_damage_roll': None,
                'results': []
            }
            self.add_event("=== DECK GUN ATTACK ===")
        else:
            # All deck gun actions resolved - clear queue
            self.game.action_queue.clear()
    
    def _draw_torpedo_resolution(self, x: int, y: int, width: int) -> None:
        """Draw the interactive torpedo resolution UI."""
        state = self.torpedo_resolution_state
        if not state:
            return
        
        current_target_idx = state['current_target_idx']
        targets = state['targets']  # [(ship, distance, aspect), ...]
        torpedoes_available = state['torpedoes_available']
        current_torpedo_idx = state['current_torpedo_idx']
        waiting_for = state['waiting_for']
        
        # Check if all torpedoes fired or all targets exhausted
        if torpedoes_available <= 0 or current_target_idx >= len(targets):
            # All done - finish resolution
            self._finish_torpedo_resolution()
            return
        
        ship, distance, aspect = targets[current_target_idx]
        
        # Draw header
        info_y = y
        self.draw_text(
            f"TORPEDO #{current_torpedo_idx + 1} of {state['torpedo_count']}",
            x + width // 2,
            info_y,
            self.font_small,
            color=(255, 220, 100),
            center=True
        )
        info_y += 20
        
        # Draw target info
        self.draw_text(
            f"TARGET: {ship.ship_type.upper()}",
            x + width // 2,
            info_y,
            self.font_small,
            color=(200, 200, 200),
            center=True
        )
        info_y += 20
        
        self.draw_text(
            f"Range {distance}, {aspect.replace('_', '/')} aspect",
            x + width // 2,
            info_y,
            self.font_small,
            color=(180, 180, 180),
            center=True
        )
        info_y += 20
        
        self.draw_text(
            f"({current_target_idx + 1} of {len(targets)} ships)",
            x + width // 2,
            info_y,
            self.font_small,
            color=(150, 150, 150),
            center=True
        )
        info_y += 25
        
        # Button defaults
        button_color = (60, 80, 100)
        border_color = (100, 140, 180)
        button_text1 = "CLICK"
        button_text2 = "BUTTON"
        
        # Show what we're waiting for
        if waiting_for == 'hit':
            # Get hit target from action
            action = state['action']
            hit_target = action.get_torpedo_hit_target(distance, aspect)
            
            self.draw_text(
                f"Need {hit_target}+ on 1d6 to hit",
                x + width // 2,
                info_y,
                self.font_small,
                color=(200, 200, 200),
                center=True
            )
            info_y += 25
            
            button_text1 = "CLICK TO"
            button_text2 = "ROLL FOR HIT"
            button_color = (100, 60, 60)
            border_color = (180, 100, 100)
        
        elif waiting_for == 'damage':
            # Show last hit roll
            hit_roll = state['last_hit_roll']
            self.draw_text(
                f"HIT! Rolled {hit_roll}",
                x + width // 2,
                info_y,
                self.font_small,
                color=(100, 255, 100),
                center=True
            )
            info_y += 25
            
            button_text1 = "CLICK TO"
            button_text2 = "ROLL DAMAGE"
            button_color = (100, 80, 60)
            border_color = (180, 140, 100)
        
        elif waiting_for == 'continue':
            # Show result
            if state['last_damage_roll']:
                # Hit
                hit_roll = state['last_hit_roll']
                self.draw_text(
                    f"HIT! Rolled {hit_roll}",
                    x + width // 2,
                    info_y,
                    self.font_small,
                    color=(100, 255, 100),
                    center=True
                )
                info_y += 20
                
                damage_roll = state['last_damage_roll']
                self.draw_text(
                    f"Damage: {damage_roll['description']}",
                    x + width // 2,
                    info_y,
                    self.font_small,
                    color=(255, 200, 100),
                    center=True
                )
                info_y += 20
            else:
                # Miss
                hit_roll = state['last_hit_roll']
                self.draw_text(
                    f"MISS! Rolled {hit_roll}",
                    x + width // 2,
                    info_y,
                    self.font_small,
                    color=(255, 100, 100),
                    center=True
                )
                info_y += 20
                
                # Check if more torpedoes remaining
                if torpedoes_available > 1:
                    self.draw_text(
                        "Torpedo continues to next ship...",
                        x + width // 2,
                        info_y,
                        self.font_small,
                        color=(200, 200, 100),
                        center=True
                    )
                    info_y += 20
            
            button_text1 = "CONTINUE"
            button_text2 = "NEXT"
            button_color = (60, 80, 100)
            border_color = (100, 140, 180)
        
        # Draw button
        button_width = width - 40
        button_height = 60
        button_x = x + 20
        button_y = info_y + 10
        
        self.torpedo_roll_button_rect = pygame.Rect(button_x, button_y, button_width, button_height)
        
        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.torpedo_roll_button_rect.collidepoint(mouse_pos)
        
        if is_hover:
            button_color = tuple(min(c + 30, 255) for c in button_color)
            border_color = tuple(min(c + 30, 255) for c in border_color)
        
        pygame.draw.rect(self.screen, button_color, self.torpedo_roll_button_rect)
        pygame.draw.rect(self.screen, border_color, self.torpedo_roll_button_rect, 3)
        
        self.draw_text(
            button_text1,
            self.torpedo_roll_button_rect.centerx,
            self.torpedo_roll_button_rect.centery - 12,
            self.font_medium,
            color=(255, 255, 255),
            center=True
        )
        self.draw_text(
            button_text2,
            self.torpedo_roll_button_rect.centerx,
            self.torpedo_roll_button_rect.centery + 12,
            self.font_medium,
            color=(255, 255, 255),
            center=True
        )
    
    def _handle_torpedo_roll(self) -> None:
        """Handle clicking the torpedo resolution button."""
        state = self.torpedo_resolution_state
        if not state:
            return
        
        current_target_idx = state['current_target_idx']
        targets = state['targets']
        torpedoes_available = state['torpedoes_available']
        waiting_for = state['waiting_for']
        
        # Check if finished
        if torpedoes_available <= 0 or current_target_idx >= len(targets):
            self._finish_torpedo_resolution()
            return
        
        ship, distance, aspect = targets[current_target_idx]
        current_torpedo_idx = state['current_torpedo_idx']
        
        if waiting_for == 'hit':
            # Roll for hit (1d6)
            roll = self.game.turn_manager.dice.roll_1d6()
            
            # Get hit target from action
            action = state['action']
            hit_target = action.get_torpedo_hit_target(distance, aspect)
            
            hit = (roll >= hit_target)
            
            state['last_hit_roll'] = roll
            
            if hit:
                # Need to roll damage
                state['waiting_for'] = 'damage'
                self.add_event(f"Torpedo #{current_torpedo_idx + 1} vs {ship.ship_type} (range {distance}, {aspect}): HIT! (Rolled {roll}, needed {hit_target}+)")
            else:
                # Miss - torpedo continues
                state['results'].append((current_torpedo_idx + 1, ship, distance, False, None))
                self.add_event(f"Torpedo #{current_torpedo_idx + 1} vs {ship.ship_type} (range {distance}, {aspect}): MISS (Rolled {roll}, needed {hit_target}+)")
                
                # Don't consume this torpedo - it continues to next ship
                state['waiting_for'] = 'continue'
        
        elif waiting_for == 'damage':
            # Roll for damage using ShipDamageResolver
            from ..damage import ShipDamageResolver
            damage_resolver = ShipDamageResolver(self.game.turn_manager.dice, self.game.mission_rules)
            
            damage_result = damage_resolver.apply_damage(ship, "torpedo")
            
            state['last_damage_roll'] = {
                'die': damage_result.roll,
                'description': damage_result.description
            }
            
            # Store result
            state['results'].append((current_torpedo_idx + 1, ship, distance, True, damage_result.roll))
            
            # Log result
            if damage_result.is_now_sunk:
                self.add_event(f"  Damage: {damage_result.description} - {ship.ship_type.upper()} SUNK!")
                # Remove ship
                if ship in self.game.ships:
                    self.game.ships.remove(ship)
            elif damage_result.effect == "damaged":
                self.add_event(f"  Damage: DAMAGED (roll: {damage_result.roll})")
            else:
                self.add_event(f"  Damage: No effect (roll: {damage_result.roll})")
            
            # This torpedo is consumed
            state['torpedoes_available'] -= 1
            state['current_torpedo_idx'] += 1
            
            state['waiting_for'] = 'continue'
        
        elif waiting_for == 'continue':
            # Move to next target or next torpedo
            state['last_hit_roll'] = None
            state['last_damage_roll'] = None
            
            # If last action was a miss and we have more targets, continue same torpedo
            if state['torpedoes_available'] > 0 and current_target_idx + 1 < len(targets):
                # Continue torpedo to next ship
                state['current_target_idx'] += 1
                state['waiting_for'] = 'hit'
            elif state['torpedoes_available'] > 0:
                # No more targets, finish
                self._finish_torpedo_resolution()
            else:
                # All torpedoes fired, finish
                self._finish_torpedo_resolution()
    
    def _finish_torpedo_resolution(self) -> None:
        """Finish torpedo resolution and calculate detection level changes."""
        state = self.torpedo_resolution_state
        if not state:
            return
        
        results = state['results']
        torpedo_count = state['torpedo_count']
        
        # Count hits
        hits = sum(1 for _, _, _, hit, _ in results if hit)
        
        # Calculate DL increase (max +2 total per salvo)
        dl_increase = 0
        if torpedo_count == 3:
            dl_increase += 1  # Noise from firing 3 torpedoes
        dl_increase += hits  # +1 DL per hit
        dl_increase = min(dl_increase, 2)  # Enforce max +2 total
        
        # Apply DL increase
        if dl_increase > 0:
            self.game.detection_level = min(self.game.detection_level + dl_increase, 5)
            self.add_event(f"Detection Level +{dl_increase} (now {self.game.detection_level})")
        
        # Summary
        self.add_event(f"=== TORPEDO ATTACK COMPLETE: {hits}/{torpedo_count} hits ===")
        
        # Clear resolution state
        self.torpedo_resolution_state = None
        self.torpedo_roll_button_rect = None
        
        # Execute remaining non-torpedo actions
        non_torpedo_actions = [a for a in self.game.action_queue.actions if not isinstance(a, FireTorpedoAction)]
        if non_torpedo_actions:
            for action in non_torpedo_actions:
                result = action.execute(self.game)
                if result.success:
                    action_name = result.state_changes.get('action_name', type(action).__name__.replace('Action', ''))
                    self.add_event(f"✓ {action_name}")
                    self.game.u_boat.action_points -= result.ap_spent
            
            # Remove from queue
            self.game.action_queue.actions = [a for a in self.game.action_queue.actions if isinstance(a, FireTorpedoAction)]
        
        # Check if more torpedoes in queue
        next_torpedo = next((a for a in self.game.action_queue.actions if isinstance(a, FireTorpedoAction)), None)
        if next_torpedo:
            # Execute next torpedo action
            next_idx = self.game.action_queue.actions.index(next_torpedo)
            result = next_torpedo.execute(self.game)
            self.game.u_boat.action_points -= result.ap_spent
            
            if result.state_changes.get('needs_interactive_resolution'):
                # Setup next torpedo resolution
                self.torpedo_resolution_state = {
                    'action': next_torpedo,
                    'action_index': next_idx,
                    'torpedo_count': result.state_changes['torpedo_count'],
                    'targets': result.state_changes['targets'],
                    'current_target_idx': 0,
                    'current_torpedo_idx': 0,
                    'torpedoes_available': result.state_changes['torpedo_count'],
                    'waiting_for': 'hit',
                    'last_hit_roll': None,
                    'last_damage_roll': None,
                    'results': []
                }
                self.add_event(f"=== FIRING {self.torpedo_resolution_state['torpedo_count']} TORPEDO(ES) ===")
            else:
                self.add_event(result.message)
            
            # Remove from queue
            self.game.action_queue.actions.pop(next_idx)
        else:
            # All torpedoes resolved - clear queue
            self.game.action_queue.clear()
    
    def _handle_load_torpedo_clicks(self, mouse_pos: Tuple[int, int]) -> None:
        """Handle clicks on torpedo loading UI elements."""
        state = self.load_torpedo_selection_state
        if not state:
            return
        
        # Check tube checkbox clicks
        for tube_num, rect in self.tube_checkbox_rects.items():
            if rect.collidepoint(mouse_pos):
                # Toggle tube selection
                if tube_num in state['selected_tubes']:
                    state['selected_tubes'].remove(tube_num)
                    self.add_event(f"Deselected Tube {tube_num}")
                else:
                    # Check if we can add more
                    if len(state['selected_tubes']) < state['max_tubes']:
                        # Check if tube is available (not already loaded)
                        u_boat = state['u_boat']
                        if not u_boat.torpedo_tubes[tube_num - 1]:  # Convert to 0-based
                            state['selected_tubes'].append(tube_num)
                            self.add_event(f"Selected Tube {tube_num}")
                        else:
                            self.add_event(f"Tube {tube_num} is already loaded")
                    else:
                        max_tubes = state['max_tubes']
                        self.add_event(f"Can only load {max_tubes} tube(s) per action")
                return
        
        # Check Confirm button click
        if self.confirm_load_button_rect and self.confirm_load_button_rect.collidepoint(mouse_pos):
            if len(state['selected_tubes']) > 0:
                # Queue the load action
                from ..torpedo_validator import TorpedoValidator
                tube_indices = state['selected_tubes']
                cost_lookup = state['cost_lookup']
                
                action = LoadTorpedoAction(
                    tube_indices=tube_indices,
                    cost_lookup=cost_lookup,
                    validator=TorpedoValidator()
                )
                
                success, message = self.game.action_queue.add_action(action, self.game)
                if success:
                    self.add_event(f"Queued: Load Tubes {', '.join(str(t) for t in tube_indices)}")
                else:
                    self.add_event(f"✗ Failed: {message}")
                
                # Close selection UI
                self.load_torpedo_selection_state = None
            else:
                self.add_event("Select at least one tube to load")
            return
        
        # Check Cancel button click
        if self.cancel_load_button_rect and self.cancel_load_button_rect.collidepoint(mouse_pos):
            self.load_torpedo_selection_state = None
            self.add_event("Cancelled torpedo loading")
            return
    
    def _queue_action(self, action_id: str) -> None:
        """Queue an action based on action ID."""
        from ..models import GamePhase
        from ..action_costs import ActionCostLookup
        from ..movement_validator import MovementValidator
        from ..depth_validator import DepthValidator
        from ..repair_validator import RepairValidator
        
        # Only queue during U-Boat phase
        if self.game.turn_manager.current_phase != GamePhase.UBOAT_PHASE:
            self.add_event("Can only queue actions during U-Boat Phase")
            return
        
        u_boat = self.game.u_boat
        cost_lookup = ActionCostLookup(self.game.mission_rules)
        
        # Calculate current state after all queued actions
        # This is needed so rotations affect subsequent moves
        preview_position = u_boat.position
        preview_facing = u_boat.facing
        preview_depth = u_boat.depth
        
        for queued_action in self.game.action_queue.actions:
            action_type = type(queued_action).__name__
            if action_type == "MoveAction":
                # Simply use the target hex from the queued action
                assert isinstance(queued_action, MoveAction)
                preview_position = queued_action.target_hex
            elif action_type == "RotateAction":
                assert isinstance(queued_action, RotateAction)
                if queued_action.clockwise:
                    preview_facing = Facing((preview_facing.value + 1) % 6)
                else:
                    preview_facing = Facing((preview_facing.value - 1) % 6)
            elif action_type == "DepthChangeAction":
                assert isinstance(queued_action, DepthChangeAction)
                preview_depth = queued_action.new_depth
        
        action = None
        
        try:
            if action_id == "move":
                # Calculate target hex based on preview facing (after queued rotations)
                target_hex = preview_facing.forward(preview_position)  # type: ignore[arg-type]
                validator = MovementValidator(self.game.land_hexes, self.game.shallow_hexes, self.game.mission_hexes)
                action = MoveAction(target_hex, cost_lookup, validator)
                
            elif action_id == "rotate_l":
                action = RotateAction(clockwise=False, cost_lookup=cost_lookup)
                
            elif action_id == "rotate_r":
                action = RotateAction(clockwise=True, cost_lookup=cost_lookup)
                
            elif action_id == "dive":
                target_depth = Depth(u_boat.depth.value + 1) if u_boat.depth.value < 3 else u_boat.depth
                validator = DepthValidator(self.game.shallow_hexes)
                action = DepthChangeAction(target_depth, cost_lookup, validator)
                
            elif action_id == "surface":
                target_depth = Depth(u_boat.depth.value - 1) if u_boat.depth.value > 0 else u_boat.depth
                validator = DepthValidator(self.game.shallow_hexes)
                action = DepthChangeAction(target_depth, cost_lookup, validator)
                
            elif action_id == "repair":
                # For now, just pick first damaged system
                validator = RepairValidator()
                if u_boat.engine_damaged:
                    action = RepairAction("Engine", cost_lookup, validator)
                elif u_boat.deck_gun_damaged:
                    action = RepairAction("Deck Gun", cost_lookup, validator)
                elif u_boat.flak_gun_damaged:
                    action = RepairAction("Flak Gun", cost_lookup, validator)
                elif not all(u_boat.torpedo_tubes):
                    action = RepairAction("Torpedo Tubes", cost_lookup, validator)
                else:
                    self.add_event("No damaged systems to repair")
                    return
                    
            elif action_id == "deck_gun":
                # Queue deck gun action - interactive resolution happens on commit
                from ..los import LOSCalculator
                from ..hex_grid import HexGrid
                
                los_calc = LOSCalculator(self.game.land_hexes)
                
                # Find all valid targets (in range 1-3 with LOS)
                valid_targets: List[Tuple[Ship, int]] = []
                for ship in self.game.ships:
                    distance = HexGrid.hex_distance(u_boat.position, ship.position)
                    if 1 <= distance <= 3:
                        has_los, _ = los_calc.has_line_of_sight(
                            u_boat.position,
                            ship.position
                        )
                        if has_los:
                            valid_targets.append((ship, distance))
                
                if not valid_targets:
                    self.add_event("No ships in range for deck gun")
                    return
                
                # Sort by distance (closest first), then randomly for ties
                import random
                valid_targets.sort(key=lambda ship_tuple: (ship_tuple[1], random.random()))
                
                # Create action with targets stored for later interactive resolution
                from ..combat_resolver import CombatResolver
                ship_damage_resolver = ShipDamageResolver(self.game.turn_manager.dice, self.game.mission_rules)
                action = DeckGunAction(
                    targets=valid_targets,
                    cost_lookup=cost_lookup,
                    los_calculator=los_calc,
                    combat_resolver=CombatResolver(self.game.turn_manager.dice, self.game.mission_rules),
                    ship_damage=ship_damage_resolver
                )
                # Store targets for interactive resolution during commit
                action._interactive_targets = valid_targets  # type: ignore[attr-defined]
                
            elif action_id == "load_torp":
                # Open interactive tube selection UI
                max_tubes = 2 if u_boat.weapons_officer_alive else 1
                self.load_torpedo_selection_state = {
                    'selected_tubes': [],
                    'max_tubes': max_tubes,
                    'u_boat': u_boat,
                    'cost_lookup': cost_lookup
                }
                self.add_event(f"Select up to {max_tubes} tube(s) to load")
                return  # Don't queue yet - wait for user to select tubes
                
            elif action_id.startswith("fire_torp_"):
                # Fire individual torpedo tube
                tube_num = int(action_id.split("_")[-1])  # Extract tube number (1-5)
                
                from ..torpedo_validator import TorpedoValidator
                from ..los import LOSCalculator
                from ..combat_resolver import CombatResolver
                
                # Determine fire direction based on tube
                if tube_num <= 4:
                    # Front tubes fire forward
                    fire_direction = u_boat.facing
                else:
                    # Rear tube fires backward
                    fire_direction = Facing((u_boat.facing.value + 3) % 6)
                
                los_calc = LOSCalculator(self.game.land_hexes)
                
                action = FireTorpedoAction(
                    tube_indices=[tube_num],  # Fire single tube (1-based)
                    fire_direction=fire_direction,
                    cost_lookup=cost_lookup,
                    validator=TorpedoValidator(),
                    los_calculator=los_calc,
                    combat_resolver=CombatResolver(self.game.turn_manager.dice, self.game.mission_rules)
                )
            
            # Add action to queue
            if action:
                # Temporarily set u_boat to preview state for validation
                original_position = u_boat.position
                original_facing = u_boat.facing
                original_depth = u_boat.depth
                
                u_boat.position = preview_position
                u_boat.facing = preview_facing
                u_boat.depth = preview_depth
                
                success, message = self.game.action_queue.add_action(action, self.game)
                
                # Restore original state
                u_boat.position = original_position
                u_boat.facing = original_facing
                u_boat.depth = original_depth
                
                if success:
                    remaining = self.game.action_queue.get_remaining_ap(self.game)
                    action_desc = self._get_action_description(action)
                    self.add_event(f"Queued: {action_desc} (AP: {remaining}/{self.game.action_queue.max_ap})")
                else:
                    remaining = self.game.action_queue.get_remaining_ap(self.game)
                    self.add_event(f"Cannot queue: {message} (AP: {remaining}/{self.game.action_queue.max_ap})")
                    
        except Exception as e:
            import traceback
            self.add_event(f"Error queuing action: {e}")
            print(f"Full error: {traceback.format_exc()}")
