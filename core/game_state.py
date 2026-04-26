"""
Core game state and logic for Lone U-Boat.
Contains the main Game class with gameplay loop (no editor features).
"""

import pygame
import importlib
from typing import Optional, List, Any, Dict, Tuple

from config import board_config as cfg
from config.board_layout_config import load_mission_layout
from .models import HexCoord, Facing, Depth, UBoat, Ship, Aircraft, GamePhase
from .hex_grid import HexGrid
from .assets import AssetManager
from .conditions import ConditionFactory
from .renderer import GameRenderer
from .board_layout import BoardLayoutRuntime
from .turn_manager import TurnManager
from .actions.action_history import ActionHistory
from .actions.action_queue import ActionQueue  # Phase 2A: Keep for complex actions temporarily
from .actions.ai import AIActionQueue
from .ai_action_generators import (
    generate_merchant_actions,
    generate_detection_actions,
    generate_escort_actions,
    generate_b24_actions
)
from .merchant_ai import MerchantAI
from .detection_ai import DetectionAI
from .escort_ai import EscortAI
from .b24_ai import B24AI
from .event_system import EventSystem
from missions.mission_rules_loader import load_mission_rules


class Game:
    """Main game state and gameplay logic (editor features removed)."""
    
    animation_manager: Any  # Type hint for animation manager (set externally)
    
    def __init__(
        self,
        mission_number: int = 1,
        initial_depth: Optional[Depth] = None,
        initial_facing: Optional[Facing] = None,
        screen: Optional[pygame.Surface] = None
    ):
        pygame.init()
        if screen is None:
            self.screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        else:
            self.screen = screen
        
        # Load mission configuration
        self.mission_number = mission_number
        self.mission_config = self._load_mission_config(mission_number)
        
        pygame.display.set_caption(f"Lone U-Boat - {self.mission_config.MISSION_INFO['name']}")
        self.clock = pygame.time.Clock()
        self.running = True
        self.defeat_reason = None  # Track reason for defeat (None, 'destroyed', 'merchant_escaped')
        
        # Track entities destroyed this phase for visual feedback
        self.destroyed_this_phase: List[Dict[str, Any]] = []
        
        # AI action queue for interactive mode (solitaire gameplay)
        self.current_ai_queue: Optional[AIActionQueue] = None
        self.current_ai_queue_phase: Optional[str] = None  # Track which phase the queue belongs to
        self.last_escort_roll: Optional[Dict[str, Any]] = None  # Last escort dice roll for right-panel display
        
        # Load mission rules from JSON
        self.mission_rules = load_mission_rules(mission_number)
        
        # Initialize turn manager
        self.turn_manager = TurnManager(self.mission_rules)
        
        # Make dice roller accessible on game_state for AI actions
        self.dice_roller = self.turn_manager.dice
        
        # Initialize merchant AI
        self.merchant_ai = MerchantAI(
            mission_config=self.mission_config,
            mission_rules=self.mission_rules,
            dice_roller=self.turn_manager.dice
        )
        
        # Initialize detection AI
        self.detection_ai = DetectionAI(
            mission_rules=self.mission_rules,
            dice_roller=self.turn_manager.dice
        )
        
        # Initialize escort AI
        anchor_hex_tuple = (self.mission_config.ANCHOR_POSITIONS[0] 
                           if hasattr(self.mission_config, 'ANCHOR_POSITIONS') 
                           and self.mission_config.ANCHOR_POSITIONS
                           else (10, 10))  # Default anchor
        self.escort_ai = EscortAI(
            mission_rules=self.mission_rules,
            dice_roller=self.turn_manager.dice,
            anchor_hex=HexCoord(*anchor_hex_tuple)
        )
        
        # Initialize B-24 AI
        self.b24_ai = B24AI(
            dice_roller=self.turn_manager.dice,
            hex_grid=None,  # type: ignore[arg-type]
            mission_rules=self.mission_rules  # type: ignore[arg-type]
        )
        
        # Initialize Event System
        self.event_system = EventSystem(
            mission_rules=self.mission_rules,  # type: ignore[arg-type]
            dice_roller=self.turn_manager.dice,
            game_state=self  # Pass self for condition checking
        )
        
        # Next screen for transitions (back to menu, etc.)
        self.next_screen: Optional[str] = None
        self.next_screen_data: Dict[str, Any] = {}
        
        # Load mission map (scaled to reasonable size for rendering)
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
        
        # Load and create board layout engine for resolution-independent positioning
        try:
            layout_cfg = load_mission_layout(mission_number)
        except FileNotFoundError:
            # Fall back to legacy calibration if layout file doesn't exist
            print(f"Warning: No layout file for mission {mission_number}, using legacy calibration")
            from config.board_layout_config import MapCalibration, HexGridCalibration, StatusBoxCalibration, MissionLayoutConfig
            # Convert legacy config to new format
            layout_cfg = MissionLayoutConfig(
                map_calib=MapCalibration(width=678, height=900),
                hex_grid_calib=HexGridCalibration(
                    hex_size=cfg.HEX_GRID['size'] * cfg.HEX_SCALE_MULTIPLIER,  # type: ignore[attr-defined]
                    origin_in_map=(cfg.HEX_GRID['offset_x'] + cfg.GLOBAL_BOARD_OFFSET['offset_x'],  # type: ignore[attr-defined]
                                   cfg.HEX_GRID['offset_y'] + cfg.GLOBAL_BOARD_OFFSET['offset_y'])  # type: ignore[attr-defined]
                ),
                status_calib=StatusBoxCalibration(
                    boxes_in_map={name: (data['rect'][0] * cfg.STATUS_BOX_SCALE_MULTIPLIER,  # type: ignore[attr-defined]
                                        data['rect'][1] * cfg.STATUS_BOX_SCALE_MULTIPLIER,  # type: ignore[attr-defined]
                                        data['rect'][2] * cfg.STATUS_BOX_SCALE_MULTIPLIER,  # type: ignore[attr-defined]
                                        data['rect'][3] * cfg.STATUS_BOX_SCALE_MULTIPLIER)  # type: ignore[attr-defined]
                                 for name, data in cfg.STATUS_BOXES.items()}
                )
            )
        
        self.layout = BoardLayoutRuntime(
            screen_size=(self.screen.get_width(), self.screen.get_height()),
            layout_cfg=layout_cfg,
            ui_cfg=cfg.UI  # type: ignore[arg-type]
        )
        
        # Create hex grid overlay with runtime-computed offsets
        self.hex_grid = HexGrid(
            size=int(self.layout.hex_size),
            cols=cfg.HEX_GRID['cols'],
            rows=cfg.HEX_GRID['rows'],
            offset_x=self.layout.hex_origin_screen[0],
            offset_y=self.layout.hex_origin_screen[1],
            global_offset_x=0,  # No longer needed, handled by layout
            global_offset_y=0
        )
        
        # Set hex_grid for AI systems that need it
        self.b24_ai.hex_grid = self.hex_grid
        self.escort_ai.hex_grid = self.hex_grid  # type: ignore[attr-defined]
        
        # Game entities - load from mission config
        u_boat_start = self.mission_config.U_BOAT_START
        
        # Use provided initial settings or defaults from mission config
        initial_position = HexCoord(*u_boat_start['position'])
        initial_facing_value = initial_facing if initial_facing else Facing[u_boat_start['facing']]
        initial_depth_value = initial_depth if initial_depth else Depth[u_boat_start.get('depth', 'SURFACED')]
        
        self.u_boat = UBoat(
            position=initial_position,
            facing=initial_facing_value,
            depth=initial_depth_value
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
        
        # Aircraft (B-24s spawned via End Turn Events)
        self.aircraft: List[Aircraft] = []
        
        # Gameplay UI state
        self.selected_hex: Optional[HexCoord] = None
        self.show_grid = False  # Game defaults to grid off
        self.show_map = True
        self.show_terrain = False  # Terrain off during normal gameplay
        self.show_status_boxes = False  # Status boxes only in F2 edit mode
        self.detection_level = 0
        
        # Status box markers
        self.status_boxes: Dict[str, Dict[str, Any]] = {}
        asset_manager = AssetManager(cfg)
        self.marker_images = asset_manager.load_marker_images()
        self._setup_status_boxes()
        self.show_all_markers = False  # Markers based on game state only
        
        # Fonts
        self.font, self.font_large = asset_manager.load_fonts()
        
        # Load images
        self.u_boat_images = asset_manager.load_u_boat_images()
        self.ship_images = asset_manager.load_ship_images()
        
        # Create renderer with layout engine
        assets: Dict[str, Any] = {
            'u_boat_images': self.u_boat_images,
            'ship_images': self.ship_images,
            'marker_images': self.marker_images,
            'font': self.font,
            'font_large': self.font_large
        }
        self.renderer = GameRenderer(self.screen, cfg, self.hex_grid, assets, self.layout)
        
        # Initialize turn manager but don't roll dice yet - player must click
        self.turn_manager.turn_number = 1
        self.turn_manager.current_phase = GamePhase.UBOAT_PHASE
        self.turn_manager.ap_tracker = None  # No AP rolled yet
        
        # Apply depth detection modifier at turn start
        self.detection_level = self.turn_manager.apply_depth_detection_modifier(
            self.detection_level, 
            self.u_boat.depth
        )
        self.u_boat.action_points = 0  # Will be set after dice roll
        
        # Initialize action history for immediate execution with undo
        self.action_history = ActionHistory()
        self.turn_manager.action_history = self.action_history  # Connect to TurnManager
        
        # Phase 2A: Keep action_queue for complex actions (torpedoes, repair, deck gun) temporarily
        self.action_queue = ActionQueue()
        
        self.selected_target: Optional[Ship] = None  # For combat actions
    
    def _load_mission_config(self, mission_number: int) -> Any:
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
    
    def update_screen_size(self, new_size: tuple[int, int]) -> None:
        """Update layout when screen size changes.
        
        Args:
            new_size: New screen size (width, height)
        """
        self.layout.recompute(new_size)
        # Update hex grid with new computed values
        self.hex_grid.size = int(self.layout.hex_size)  # type: ignore[assignment]
        self.hex_grid.offset_x, self.hex_grid.offset_y = self.layout.hex_origin_screen
        # Update renderer's layout reference
        self.renderer.update_layout(self.layout)
    
    def update_board_region(self, board_rect: pygame.Rect) -> None:
        """Update layout for a specific board region.
        
        This allows the screen to define where the board area is,
        and the layout engine handles all positioning within that area.
        
        Args:
            board_rect: The board area in screen coordinates
        """
        self.layout.recompute_for_board(board_rect)
        # Update hex grid with new computed values
        self.hex_grid.size = int(self.layout.hex_size)  # type: ignore[assignment]
        self.hex_grid.offset_x, self.hex_grid.offset_y = self.layout.hex_origin_screen
        # Update renderer's layout reference
        self.renderer.update_layout(self.layout)
    
    def handle_events(self):
        """Handle pygame events - gameplay controls and phase advancement."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                
                # Phase advancement
                elif event.key == pygame.K_SPACE:
                    self._advance_to_next_phase()
                
                # Display toggles
                elif event.key == pygame.K_g:
                    self.show_grid = not self.show_grid
                elif event.key == pygame.K_m:
                    self.show_map = not self.show_map
                elif event.key == pygame.K_v:
                    self.show_terrain = not self.show_terrain
                elif event.key == pygame.K_s:
                    self.show_status_boxes = not self.show_status_boxes
                
                # TODO Phase 3: U-Boat action controls will go here
                # Actions will cost AP and be validated before execution
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    mouse_pos = pygame.mouse.get_pos()
                    hex_coord = self.hex_grid.pixel_to_hex(*mouse_pos)
                    
                    # Select hex for gameplay
                    if self.hex_grid.is_valid_hex(hex_coord, self.mission_hexes):
                        self.selected_hex = hex_coord
    
    def _advance_to_next_phase(self):
        """Advance to next phase, executing phase-specific logic."""
        current_phase = self.turn_manager.current_phase
        
        # Execute phase end logic for current phase
        if current_phase == GamePhase.UBOAT_PHASE:
            self._end_uboat_phase()
        
        # Stop if game ended during phase cleanup
        if not self.running:
            return
        
        # Cleanup destroyed entities before phase change
        self._cleanup_destroyed_entities()
        
        # Advance to next phase
        _, turn_wrapped = self.turn_manager.advance_phase()
        
        # If wrapped to new turn, start it
        if turn_wrapped:
            self._start_new_turn()
            return
        
        # Execute phase start logic for new phase
        new_phase = self.turn_manager.current_phase
        if new_phase == GamePhase.MERCHANT_PHASE:
            self._execute_merchant_phase()
        elif new_phase == GamePhase.DETECTION_PHASE:
            self._execute_detection_phase()
        elif new_phase == GamePhase.ESCORT_PHASE:
            self._execute_escort_phase()
        elif new_phase == GamePhase.B24_PHASE:
            self._execute_b24_phase()
        elif new_phase == GamePhase.END_TURN_EVENTS:
            self._execute_end_turn_events()
        elif new_phase == GamePhase.END_TURN_PHASE:
            self._execute_end_turn_phase()
    
    def _end_uboat_phase(self):
        """Clean up U-Boat phase - clear action history (no undo across phases)."""
        # Clear action history when phase ends (can't undo across phases)
        self.action_history.clear()
        self.turn_manager.clear_action_history()
        
        # Phase 2A: Clear action_queue for complex actions
        self.action_queue.clear()
        
        # TODO Phase 2: Remove old action_queue logic
        # Old queue-based logic commented out for Phase 1
        # if self.action_queue and self.action_queue.actions:
        #     results = self.action_queue.commit_all(self)
        #     for result in results:
        #         if result.success:
        #             action_name = result.state_changes.get('action_name', 'Action')
        #             self.turn_manager.add_phase_log("U-Boat Phase", 
        #                 f"✓ {action_name}: {result.message}")
        #         else:
        #             self.turn_manager.add_phase_log("U-Boat Phase", 
        #                 f"✗ Action failed: {result.message}")
    
    def _execute_merchant_phase(self):
        """Execute merchant phase - generate action queue for player to execute."""
        # Generate actions for player to execute
        self.current_ai_queue = generate_merchant_actions(self)
        self.current_ai_queue_phase = "Merchant Phase"
        
        # Log phase start
        merchant_count = sum(1 for ship in self.ships if ship.ship_type == 'merchant')
        if merchant_count == 0:
            self.turn_manager.add_phase_log("Merchant Phase", "No merchants on map")
            self.current_ai_queue = None  # Skip to next phase immediately
            self.current_ai_queue_phase = None
            return
        
        # If queue is empty even with merchants present, log it
        if self.current_ai_queue.total_count() == 0:
            self.turn_manager.add_phase_log("Merchant Phase", 
                                           f"{merchant_count} merchant(s) - no actions needed")
            self.current_ai_queue = None  # Skip to next phase immediately
            self.current_ai_queue_phase = None
            return
        
        self.turn_manager.add_phase_log("Merchant Phase", 
                                       f"{merchant_count} merchant(s) - {self.current_ai_queue.total_count()} actions queued")
    
    def _trigger_merchant_escape_defeat(self, merchant_count: int):
        """Trigger defeat when merchant(s) escape."""
        self.defeat_reason = 'merchant_escaped'
        print(f"\n{'='*60}")
        print("MISSION FAILED - MERCHANT ESCAPED!")
        print(f"{'='*60}")
        print(f"Reason: {merchant_count} merchant ship(s) reached exit hex")
        print(f"Mission Objective: Destroy all merchants before they escape")
        print(f"Turn: {self.turn_manager.turn_number}")
        print(f"Final Position: {self.u_boat.position}")
        print(f"Hull Damage: {self.u_boat.hull_damage}/4")
        print(f"{'='*60}\n")
        self.running = False
    
    def _execute_detection_phase(self):
        """Execute detection phase - generate action queue for player to execute."""
        # Skip detection if already at maximum
        if self.detection_level >= 3:
            self.turn_manager.add_phase_log("Detection Phase", 
                                           "Detection already at maximum - no checks needed")
            return
        
        # Generate actions for player to execute
        self.current_ai_queue = generate_detection_actions(self)
        self.current_ai_queue_phase = "Detection Phase"
        
        # Log phase start
        action_count = self.current_ai_queue.total_count()
        if action_count == 0:
            self.turn_manager.add_phase_log("Detection Phase", "No detection checks")
            self.current_ai_queue = None  # Skip to next phase immediately
            self.current_ai_queue_phase = None
            return
        
        self.turn_manager.add_phase_log("Detection Phase",
                                       f"{action_count} detection check(s) queued")
    
    def _execute_escort_phase(self):
        """Execute escort phase - generate action queue for player to execute."""
        # Generate actions for player to execute
        self.current_ai_queue = generate_escort_actions(self)
        self.current_ai_queue_phase = "Escort Phase"
        
        # Log phase start
        escort_count = sum(1 for ship in self.ships if ship.ship_type in ['corvette', 'destroyer'])
        if escort_count == 0:
            self.turn_manager.add_phase_log("Escort Phase", "No escorts on map")
            self.current_ai_queue = None  # Skip to next phase immediately
            self.current_ai_queue_phase = None
            return
        
        self.turn_manager.add_phase_log("Escort Phase",
                                       f"{escort_count} escort(s) - {self.current_ai_queue.total_count()} actions queued")
    
    def _execute_b24_phase(self):
        """Execute B-24 phase - generate action queue for player to execute."""
        # Generate actions for player to execute
        self.current_ai_queue = generate_b24_actions(self)
        self.current_ai_queue_phase = "B24 Aircraft Phase"
        
        # Log phase start
        if not self.aircraft:
            self.turn_manager.add_phase_log("B24 Aircraft Phase", "No aircraft on map")
            self.current_ai_queue = None  # Skip to next phase immediately
            self.current_ai_queue_phase = None
            return
        
        self.turn_manager.add_phase_log("B24 Aircraft Phase",
                                       f"{len(self.aircraft)} aircraft - {self.current_ai_queue.total_count()} actions queued")
    
    def _execute_end_turn_events(self):
        """Execute end-of-turn events (Phase 6)."""
        self.turn_manager.add_phase_log("End Turn Events", f"Checking for turn {self.turn_manager.turn_number} events...")
        
        result = self.event_system.execute_end_turn_events(
            self.turn_manager.turn_number
        )
        
        # Add spawned ships
        for ship in result.spawned_ships:
            self.ships.append(ship)
        
        # Add spawned aircraft
        for aircraft in result.spawned_aircraft:
            self.aircraft.append(aircraft)
        
        # Handle special effects
        for effect in result.special_effects:
            self._apply_special_effect(effect)
        
        # Log messages
        if result.messages:
            for msg in result.messages:
                self.turn_manager.add_phase_log("End Turn Events", msg)
        else:
            msg = "No events this turn"
            self.turn_manager.add_phase_log("End Turn Events", msg)
    
    def _apply_special_effect(self, effect: str):
        """Apply special event effects to game state.
        
        Args:
            effect: Effect identifier string
        """
        if effect == "rerun_detection_phase":
            # Re-run detection phase
            self.turn_manager.add_phase_log("End Turn Events", "  Re-running Detection Phase...")
            self._execute_detection_phase()
        
        elif effect == "set_detection_level_1":
            # Set DL to 1
            if self.detection_level == 0:
                print(f"[DL] Event 'set_detection_level_1': DL 0 -> 1")
                self.detection_level = 1
                self.turn_manager.add_phase_log("End Turn Events", "  Detection Level set to 1")
        
        elif effect == "hull_damage_1_force_medium":
            # Add 1 hull damage and force to medium depth
            self.u_boat.hull_damage += 1
            self.turn_manager.add_phase_log("End Turn Events", f"  +1 Hull Damage (now {self.u_boat.hull_damage})")
            if self.u_boat.depth == Depth.DEEP:
                self.u_boat.depth = Depth.MEDIUM
                self.turn_manager.add_phase_log("End Turn Events", "  U-Boat forced to Medium depth")
        
        elif effect == "reduce_detection_level_1":
            # Reduce DL by 1
            if self.detection_level > 0:
                self.detection_level -= 1
                self.turn_manager.add_phase_log("End Turn Events", f"  Detection Level reduced to {self.detection_level}")
    
    def _execute_end_turn_phase(self):
        """Clean up turn and prepare for next."""
        msg = f"Turn {self.turn_manager.turn_number} complete"
        self.turn_manager.add_phase_log("End Turn Phase", msg)
        self.turn_manager.add_phase_log("End Turn Phase", f"U-Boat: {self.u_boat.position}, {self.u_boat.depth.name}, Hull:{self.u_boat.hull_damage}/{self.escort_ai.damage_resolver.max_hull_damage}")
        self.turn_manager.add_phase_log("End Turn Phase", f"Ships: {len(self.ships)} remaining, Detection Level: {self.detection_level}")
        
        # Check victory/defeat conditions
        self._check_game_over_conditions()
    
    def _start_new_turn(self):
        """Start a new turn - reset state and wait for player to roll AP."""
        # Log turn separator
        print("[TURN] " + "-" * 60)
        print(f"[TURN] Turn {self.turn_manager.turn_number + 1} Beginning")
        print("[TURN] " + "-" * 60)
        
        # Apply depth detection modifier before rolling AP
        self.detection_level = self.turn_manager.apply_depth_detection_modifier(
            self.detection_level,
            self.u_boat.depth
        )
        
        # Increment turn and reset to U-Boat phase, waiting for AP roll
        self.turn_manager.turn_number += 1
        self.turn_manager.current_phase = GamePhase.UBOAT_PHASE
        self.turn_manager.ap_tracker = None  # Player must click to roll
        self.turn_manager.phase_logs.clear()
        self.turn_manager.depth_changed_this_turn = False
        self.last_escort_roll = None
        
        # Reset AP to 0 until player rolls
        self.u_boat.action_points = 0
        
        # Clear action history for new turn
        if hasattr(self, 'action_history'):
            self.action_history.clear()
        else:
            self.action_history = ActionHistory()
            self.turn_manager.action_history = self.action_history
        self.selected_target = None
    
    
    def can_exit_map(self, preview_position: Optional[HexCoord] = None, 
                     preview_facing: Optional[Facing] = None) -> tuple[bool, str]:
        """
        Check if U-boat can exit the map.
        
        Args:
            preview_position: Optional preview position (after queued actions)
            preview_facing: Optional preview facing (after queued actions)
        
        Requirements:
        1. U-boat ON the exit hex
        2. Facing the correct direction
        3. Has available movement points (AP > 0)
        4. All merchants sunk
        
        Returns:
            (can_exit, reason_if_not)
        """
        # Check if config has exit hex defined
        if not hasattr(self.mission_config, 'U_BOAT_EXIT_HEX'):
            return False, "No exit hex defined"
        
        exit_hex = HexCoord(*self.mission_config.U_BOAT_EXIT_HEX)
        exit_facing = Facing[self.mission_config.U_BOAT_EXIT_FACING]
        
        # Use preview state if provided, otherwise use actual state
        check_position = preview_position if preview_position is not None else self.u_boat.position
        check_facing = preview_facing if preview_facing is not None else self.u_boat.facing
        
        # 1. Check if ON exit hex
        if check_position != exit_hex:
            return False, f"Not on exit hex (currently at {check_position}, need {exit_hex})"
        
        # 2. Check facing
        if check_facing != exit_facing:
            return False, f"Wrong facing (currently {check_facing.name}, need {exit_facing.name})"
        
        # 3. Check AP - need remaining AP > 0
        remaining_ap = self.turn_manager.remaining_ap if hasattr(self.turn_manager, 'remaining_ap') else 0
        if remaining_ap <= 0:
            return False, "No movement points remaining"
        
        # 4. Check all merchants sunk (exclude destroyed merchants that are still visible)
        # Count only merchants that are NOT in the destroyed_this_phase list
        alive_merchant_count = 0
        for ship in self.ships:
            if ship.ship_type == "merchant":
                # Check if this merchant is in destroyed_this_phase
                is_destroyed = False
                for destroyed in self.destroyed_this_phase:
                    if destroyed.get('position') == ship.position and destroyed.get('type') == 'merchant':
                        is_destroyed = True
                        break
                
                if not is_destroyed:
                    alive_merchant_count += 1
        
        if alive_merchant_count > 0:
            return False, f"{alive_merchant_count} merchant(s) still alive"
        
        return True, "Can exit"
    
    def record_destroyed_entity(self, entity_type: str, position: HexCoord, name: str) -> None:
        """
        Record an entity destroyed this phase for visual feedback.
        
        Args:
            entity_type: Type of entity ('corvette', 'destroyer', 'merchant', 'b24')
            position: Last known position of entity
            name: Display name for overlay (e.g., 'CORVETTE', 'MERCHANT')
        """
        self.destroyed_this_phase.append({
            'type': entity_type,
            'position': position,
            'name': name
        })
    
    def _cleanup_destroyed_entities(self) -> None:
        """Remove destroyed entities from game lists and clear tracking (called on phase advance)."""
        # Remove ships marked for destruction
        for destroyed in self.destroyed_this_phase:
            if destroyed['type'] in ['corvette', 'destroyer', 'merchant']:
                # Find and remove from ships list
                self.ships = [s for s in self.ships if s.position != destroyed['position']]
            elif destroyed['type'] == 'b24':
                # Find and remove from aircraft list
                self.aircraft = [a for a in self.aircraft if a.position != destroyed['position']]
        
        # Clear the destroyed list for next phase
        self.destroyed_this_phase.clear()
    
    def _check_game_over_conditions(self):
        """Check if the game is over (victory or defeat)."""
        # Check U-boat destruction (defeat)
        is_destroyed, reason = self.escort_ai.damage_resolver.check_destruction(self.u_boat)
        if is_destroyed:
            self.defeat_reason = 'destroyed'
            # Don't print the banner here — the UI adds the triggering die/event
            # to the event log AFTER execute_next_ai_action() returns, so printing
            # here would make the banner appear before the [EVENT] that caused it.
            # The banner is printed by the UI (unified_game._print_game_over_banner)
            # after add_event() to guarantee correct ordering.
            self.running = False
            return
        
        # Note: Victory is now triggered by EXIT MAP button, not automatic
        # This ensures all exit conditions are met: position, facing, AP, and merchants sunk
    
    # ========== INTERACTIVE AI MODE METHODS (Strangler Fig Pattern) ==========
    
    
    def execute_next_ai_action(self) -> Tuple[bool, Optional[str]]:
        """Execute next action in current AI queue (called from UI).
        
        Returns:
            Tuple of (has_more, result_message):
            - has_more: True if more actions remain, False if queue exhausted
            - result_message: The action result message to display, or None
        """
        if not self.current_ai_queue or self.current_ai_queue.is_exhausted():
            return (False, None)
        
        # Execute current action
        result = self.current_ai_queue.execute_current(self)
        
        # Store result message for return
        result_message = None
        if result and result.success:
            result_message = result.message
            # NOTE: Do NOT add to phase_log here.  The UI shows results live via
            # add_event() as each action is executed, so storing them in phase_log
            # would cause duplicates and out-of-order display.
        
        # Check if U-boat was destroyed by this action
        self._check_game_over_conditions()
        if not self.running:
            # Game over - clear queue and return False
            self.current_ai_queue = None
            return (False, result_message)
        
        # Advance to next action
        has_more = self.current_ai_queue.next()
        
        # If queue exhausted, clear it and allow phase advance
        if not has_more:
            self.current_ai_queue = None
            self.current_ai_queue_phase = None
        
        return (has_more, result_message)
    
    def get_current_ai_action_preview(self) -> Optional[Dict[str, Any]]:
        """Get preview data for current AI action (for UI display).
        
        Returns:
            Preview data dict with action_name and details for UI display,
            or None if no action queued
        """
        if not self.current_ai_queue or self.current_ai_queue.is_exhausted():
            return None
        
        action = self.current_ai_queue.current_action()
        if not action:
            return None
        
        # Get technical preview data (for rendering, not for UI text)
        preview_data = action.get_preview_data(self)
        
        # Add user-friendly data for UI display
        action_name = action.__class__.__name__.replace('Action', '').replace('_', ' ')
        details = action.get_description() if hasattr(action, 'get_description') else "AI action"
        
        # Also add entity description if available
        if hasattr(action, 'get_entity_description'):
            try:
                entity_desc = action.get_entity_description(self)
                details = f"{entity_desc}: {details}"
            except:
                pass  # If entity lookup fails, just use basic description
        
        return {
            'action_name': action_name,
            'details': details,
            'preview_data': preview_data  # Technical data for rendering
        }
    
    def has_pending_ai_actions(self) -> bool:
        """Check if there are pending AI actions to execute.
        
        Returns:
            True if player must execute AI actions before advancing phase
        """
        return (self.current_ai_queue is not None 
                and not self.current_ai_queue.is_exhausted())
    
    # ========== END INTERACTIVE AI MODE METHODS ==========
    
    def trigger_victory(self):
        """Trigger victory when exiting via EXIT MAP button."""
        print(f"\n{'='*60}")
        print("MISSION SUCCESS!")
        print(f"{'='*60}")
        print(f"All merchant ships destroyed!")
        print(f"U-boat escaped via exit hex!")
        print(f"Turn: {self.turn_manager.turn_number}")
        print(f"Final Position: {self.u_boat.position}")
        print(f"Hull Damage: {self.u_boat.hull_damage}/{self.escort_ai.damage_resolver.max_hull_damage}")
        print(f"{'='*60}\n")
        self.running = False
    
    def update(self):
        """Update game state - NPC AI and game rules will go here."""
        pass  # Future: NPC ship movement, detection, combat resolution
    
    def render(self):
        """Render everything using the GameRenderer."""
        self.renderer.render_frame(self)
    
    def run(self):
        """Main game loop."""
        while self.running:
            self.handle_events()
            self.update()
            self.render()
            self.clock.tick(60)
        
        pygame.quit()
