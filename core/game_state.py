"""
Core game state and logic for Lone U-Boat.
Contains the main Game class with gameplay loop (no editor features).
"""

import pygame
import importlib
from typing import Optional, List, Any, Dict

from config import board_config as cfg
from config.board_layout_config import load_mission_layout, MissionLayoutConfig
from .models import HexCoord, Facing, Depth, UBoat, Ship, Aircraft, GamePhase
from .hex_grid import HexGrid
from .assets import AssetManager
from .conditions import ConditionFactory
from .renderer import GameRenderer
from .board_layout import BoardLayoutRuntime
from .turn_manager import TurnManager
from .actions import ActionQueue
from .merchant_ai import MerchantAI
from .detection_ai import DetectionAI
from .escort_ai import EscortAI
from .b24_ai import B24AI
from .event_system import EventSystem
from missions.mission_rules_loader import MissionRules, load_mission_rules


class Game:
    """Main game state and gameplay logic (editor features removed)."""
    
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
        
        # Load mission rules from JSON
        self.mission_rules = load_mission_rules(mission_number)
        
        # Initialize turn manager
        self.turn_manager = TurnManager(self.mission_rules)
        
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
            hex_grid=None,  # Will be set after hex_grid initialization
            mission_rules=self.mission_rules
        )
        
        # Initialize Event System
        self.event_system = EventSystem(
            mission_rules=self.mission_rules,
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
                    hex_size=cfg.HEX_GRID['size'] * cfg.HEX_SCALE_MULTIPLIER,
                    origin_in_map=(cfg.HEX_GRID['offset_x'] + cfg.GLOBAL_BOARD_OFFSET['offset_x'], 
                                   cfg.HEX_GRID['offset_y'] + cfg.GLOBAL_BOARD_OFFSET['offset_y'])
                ),
                status_calib=StatusBoxCalibration(
                    boxes_in_map={name: (data['rect'][0] * cfg.STATUS_BOX_SCALE_MULTIPLIER,
                                        data['rect'][1] * cfg.STATUS_BOX_SCALE_MULTIPLIER,
                                        data['rect'][2] * cfg.STATUS_BOX_SCALE_MULTIPLIER,
                                        data['rect'][3] * cfg.STATUS_BOX_SCALE_MULTIPLIER)
                                 for name, data in cfg.STATUS_BOXES.items()}
                )
            )
        
        self.layout = BoardLayoutRuntime(
            screen_size=(self.screen.get_width(), self.screen.get_height()),
            layout_cfg=layout_cfg,
            ui_cfg=cfg.UI
        )
        
        # Create hex grid overlay with runtime-computed offsets
        self.hex_grid = HexGrid(
            size=self.layout.hex_size,
            cols=cfg.HEX_GRID['cols'],
            rows=cfg.HEX_GRID['rows'],
            offset_x=self.layout.hex_origin_screen[0],
            offset_y=self.layout.hex_origin_screen[1],
            global_offset_x=0,  # No longer needed, handled by layout
            global_offset_y=0
        )
        
        # Set hex_grid for AI systems that need it
        self.b24_ai.hex_grid = self.hex_grid
        self.escort_ai.hex_grid = self.hex_grid
        
        # Game entities - load from mission config
        u_boat_start = self.mission_config.U_BOAT_START
        
        # Use provided initial settings or defaults from mission config
        initial_position = HexCoord(*u_boat_start['position'])
        initial_facing_value = initial_facing if initial_facing else Facing[u_boat_start['facing']]
        initial_depth_value = initial_depth if initial_depth else Depth.SURFACED
        
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
        
        # Initialize action queue with 0 AP until dice are rolled
        self.action_queue = ActionQueue(max_ap=0)
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
        self.hex_grid.size = self.layout.hex_size
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
        self.hex_grid.size = self.layout.hex_size
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
        
        # Execute phase end logic
        if current_phase == GamePhase.UBOAT_PHASE:
            self._end_uboat_phase()
        elif current_phase == GamePhase.MERCHANT_PHASE:
            self._execute_merchant_phase()
        elif current_phase == GamePhase.DETECTION_PHASE:
            self._execute_detection_phase()
        elif current_phase == GamePhase.ESCORT_PHASE:
            self._execute_escort_phase()
        elif current_phase == GamePhase.B24_PHASE:
            self._execute_b24_phase()
        elif current_phase == GamePhase.END_TURN_EVENTS:
            self._execute_end_turn_events()
        elif current_phase == GamePhase.END_TURN_PHASE:
            self._execute_end_turn_phase()
        
        # Advance phase
        new_phase, turn_wrapped = self.turn_manager.advance_phase()
        
        # If wrapped to new turn, start it
        if turn_wrapped:
            self._start_new_turn()
    
    def _end_uboat_phase(self):
        """Clean up U-Boat phase - commit queued actions if not already animated."""
        # Check if actions were already executed via animation
        # If queue is empty, actions were already animated
        if self.action_queue and self.action_queue.actions:
            # Actions not yet executed - do it now (for SPACE key advancement)
            self.turn_manager.add_phase_log("U-Boat Phase", 
                f"Committing {len(self.action_queue.actions)} queued action(s)...")
            
            # commit_all now clears the queue and deducts AP internally
            results = self.action_queue.commit_all(self)
            
            # Log each action result
            for result in results:
                if result.success:
                    action_name = result.state_changes.get('action_name', 'Action')
                    self.turn_manager.add_phase_log("U-Boat Phase", 
                        f"✓ {action_name}: {result.message}")
                else:
                    self.turn_manager.add_phase_log("U-Boat Phase", 
                        f"✗ Action failed: {result.message}")
        else:
            self.turn_manager.add_phase_log("U-Boat Phase", 
                "Actions already executed")
        
        # Log remaining AP
        remaining = self.action_queue.get_remaining_ap(self)
        if remaining > 0:
            self.turn_manager.add_phase_log("U-Boat Phase",
                f"Ended with {remaining} AP remaining")
    
    def _execute_merchant_phase(self):
        """Execute merchant ship movements."""
        self.turn_manager.add_phase_log("Merchant Phase", "Merchant ships acting...")
        print("[EVENT] Merchant Phase: Executing merchant movements...")
        
        # Execute merchant AI
        messages = self.merchant_ai.execute_merchant_phase(self.ships)
        
        # Log all merchant movements
        for message in messages:
            self.turn_manager.add_phase_log("Merchant Phase", message)
            print(f"[EVENT] {message}")
        
        # Check if any merchants have exited
        exited = self.merchant_ai.check_merchant_exit(self.ships)
        if exited:
            msg = f"{len(exited)} merchant(s) exited map"
            self.turn_manager.add_phase_log("Merchant Phase", msg)
            print(f"[EVENT] {msg}")
    
    def _execute_detection_phase(self):
        """Calculate detection level changes."""
        self.turn_manager.add_phase_log("Detection Phase", "Calculating detection...")
        print(f"[EVENT] Detection Phase: Current DL={self.detection_level}")
        
        # Execute detection AI
        new_detection_level, messages = self.detection_ai.execute_detection_phase(
            ships=self.ships,
            u_boat=self.u_boat,
            current_detection_level=self.detection_level,
            land_hexes=self.land_hexes,
            hex_grid=self.hex_grid
        )
        
        # Log all detection messages
        for message in messages:
            self.turn_manager.add_phase_log("Detection Phase", message)
            print(f"[EVENT] {message}")
        
        # Update detection level
        if new_detection_level != self.detection_level:
            print(f"[EVENT] Detection Level: {self.detection_level} -> {new_detection_level}")
        self.detection_level = new_detection_level
    
    def _execute_escort_phase(self):
        """Execute escort ship behaviors."""
        self.turn_manager.add_phase_log("Escort Phase", "Escorts acting...")
        print(f"[EVENT] Escort Phase: DL={self.detection_level}")
        
        # Execute escort AI
        new_detection_level, messages = self.escort_ai.execute_escort_phase(
            ships=self.ships,
            u_boat=self.u_boat,
            detection_level=self.detection_level,
            land_hexes=self.land_hexes,
            hex_grid=self.hex_grid,
            mission_hexes=self.mission_hexes
        )
        
        # Log all escort action messages
        for message in messages:
            self.turn_manager.add_phase_log("Escort Phase", message)
            print(f"[EVENT] {message}")
        
        # Update detection level (can be increased by FIRE action or forced dive)
        if new_detection_level != self.detection_level:
            print(f"[EVENT] Detection Level changed: {self.detection_level} -> {new_detection_level}")
        self.detection_level = new_detection_level
    
    def _execute_b24_phase(self):
        """Execute B24 aircraft phase."""
        if not self.aircraft:
            msg = "No aircraft on map"
            self.turn_manager.add_phase_log("B24 Phase", msg)
            print(f"[EVENT] {msg}")
            return
        
        print(f"[EVENT] B-24 Phase: {len(self.aircraft)} aircraft active")
        
        # Execute B-24 phase
        messages, new_dl = self.b24_ai.execute_b24_phase(
            aircraft_list=self.aircraft,  # Modified in place (aircraft removed if off map)
            u_boat=self.u_boat,
            detection_level=self.detection_level
        )
        
        # Log all messages
        for msg in messages:
            self.turn_manager.add_phase_log("B24 Phase", msg)
            print(f"[EVENT] {msg}")
        
        # Update detection level
        if new_dl > self.detection_level:
            self.detection_level = new_dl
            msg = f"Detection Level increased to {new_dl}"
            self.turn_manager.add_phase_log("B24 Phase", msg)
            print(f"[EVENT] {msg}")
    
    def _execute_end_turn_events(self):
        """Execute end-of-turn events (Phase 6)."""
        print(f"[EVENT] End Turn Events: Checking for turn {self.turn_manager.turn_number} events...")
        
        result = self.event_system.execute_end_turn_events(
            self.turn_manager.turn_number
        )
        
        # Add spawned ships
        for ship in result.spawned_ships:
            self.ships.append(ship)
            msg = f"Spawned {ship.ship_type} at {ship.position}"
            self.turn_manager.add_phase_log("End Turn Events", msg)
            print(f"[EVENT] {msg}")
        
        # Add spawned aircraft
        for aircraft in result.spawned_aircraft:
            self.aircraft.append(aircraft)
            msg = f"Spawned {aircraft.aircraft_type} at {aircraft.position}"
            self.turn_manager.add_phase_log("End Turn Events", msg)
            print(f"[EVENT] {msg}")
        
        # Handle special effects
        for effect in result.special_effects:
            self._apply_special_effect(effect)
        
        # Log messages
        if result.messages:
            for msg in result.messages:
                self.turn_manager.add_phase_log("End Turn Events", msg)
                print(f"[EVENT] {msg}")
        else:
            msg = "No events this turn"
            self.turn_manager.add_phase_log("End Turn Events", msg)
            print(f"[EVENT] {msg}")
    
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
        print(f"[EVENT] {msg}")
        print(f"[EVENT] U-Boat: {self.u_boat.position}, {self.u_boat.depth.name}, Hull:{self.u_boat.hull_damage}/3")
        print(f"[EVENT] Ships: {len(self.ships)} remaining, Detection Level: {self.detection_level}")
        
        # TODO Phase 6: Check victory/defeat conditions
    
    def _start_new_turn(self):
        """Start a new turn - reset state and wait for player to roll AP."""
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
        
        # Reset AP to 0 until player rolls
        self.u_boat.action_points = 0
        
        # Reset action queue for new turn (0 AP until dice are rolled)
        if hasattr(self, 'action_queue'):
            self.action_queue.reset_for_new_turn(0)
        else:
            self.action_queue = ActionQueue(max_ap=0)
        self.selected_target = None
    
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
