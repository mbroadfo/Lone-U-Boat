"""
Core game state and logic for Lone U-Boat.
Contains the main Game class with gameplay loop (no editor features).
"""

import pygame
import importlib
from typing import Optional, List, Any, Dict

from config import board_config as cfg
from config.board_layout_config import load_mission_layout, MissionLayoutConfig
from .models import HexCoord, Facing, Depth, UBoat, Ship, GamePhase
from .hex_grid import HexGrid
from .assets import AssetManager
from .conditions import ConditionFactory
from .renderer import GameRenderer
from .board_layout import BoardLayoutRuntime


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
        
        # Game phase tracking
        self.current_phase = GamePhase.UBOAT_PHASE
        self.turn_number = 1
        
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
        
        # Gameplay UI state
        self.selected_hex: Optional[HexCoord] = None
        self.show_grid = False  # Game defaults to grid off
        self.show_map = True
        self.show_terrain = False  # Terrain off during normal gameplay
        self.show_status_boxes = True  # Status boxes and torpedoes visible by default
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
        """Handle pygame events - gameplay controls only."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                
                # Display toggles
                elif event.key == pygame.K_g:
                    self.show_grid = not self.show_grid
                elif event.key == pygame.K_m:
                    self.show_map = not self.show_map
                
                # U-Boat controls
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
                elif event.key == pygame.K_x:
                    # Decrease depth (go shallower)
                    if self.u_boat.depth != Depth.SURFACED:
                        self.u_boat.depth = Depth(self.u_boat.depth.value - 1)
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    mouse_pos = pygame.mouse.get_pos()
                    hex_coord = self.hex_grid.pixel_to_hex(*mouse_pos)
                    
                    # Select hex for gameplay
                    if self.hex_grid.is_valid_hex(hex_coord, self.mission_hexes):
                        self.selected_hex = hex_coord
    
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
