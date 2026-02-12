"""
B-24 Turn Action - Interactive AI system.

Handles B-24 aircraft turning toward U-boat (only at DL 2-3).
B-24s turn in 60° increments (one facing change), same as escorts.
"""

from typing import Tuple, Any, Optional, Dict
from .base_ai_action import AIAction, ActionResult
from core.models import Aircraft, UBoat, HexCoord, Facing


class B24TurnAction(AIAction):
    """Action for B-24 turning toward U-boat."""
    
    def __init__(self, aircraft_index: int, detection_level: int):
        """Initialize B-24 turn action.
        
        Args:
            aircraft_index: Index of aircraft in game_state.aircraft_list
            detection_level: Current detection level (0-3)
        """
        super().__init__(entity_index=aircraft_index)
        self._aircraft_index = aircraft_index
        self._detection_level = detection_level
        self._turn_direction: Optional[str] = None
        self._new_facing: Optional[Facing] = None
    
    @property
    def triggers_animation(self) -> bool:
        """Turn triggers animation."""
        return True
    
    @property
    def requires_player_input(self) -> bool:
        """Turning may require dice roll for random turns."""
        return False
    
    def get_entity(self, game_state: Any) -> Optional[Aircraft]:
        """Get the B-24 aircraft."""
        if hasattr(game_state, 'aircraft_list') and 0 <= self._aircraft_index < len(game_state.aircraft_list):
            return game_state.aircraft_list[self._aircraft_index]
        return None
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for UI."""
        aircraft = self.get_entity(game_state)
        return {
            'type': 'b24_turn',
            'aircraft_index': self._aircraft_index,
            'detection_level': self._detection_level,
            'current_facing': aircraft.facing if aircraft else None,
            'turn_direction': self._turn_direction,
            'new_facing': self._new_facing
        }
    
    @property
    def aircraft_index(self) -> int:
        """Get the aircraft index."""
        return self._aircraft_index
    
    @property
    def detection_level(self) -> int:
        """Get the detection level."""
        return self._detection_level
    
    @property
    def turn_direction(self) -> Optional[str]:
        """Direction aircraft turned ('clockwise', 'counterclockwise', or None)."""
        return self._turn_direction
    
    @property
    def new_facing(self) -> Optional[Facing]:
        """New facing after turn."""
        return self._new_facing
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """Validate that aircraft can turn.
        
        Args:
            game_state: Current game state with aircraft_list, u_boat
        
        Returns:
            Tuple of (can_turn, reason)
        """
        # Check detection level
        if self._detection_level < 2:
            return (False, f"Detection level {self._detection_level} < 2, B-24 cannot turn")
        
        # Check aircraft exists
        if not hasattr(game_state, 'aircraft_list'):
            return (False, "No aircraft list in game state")
        
        if self._aircraft_index >= len(game_state.aircraft_list):
            return (False, f"Aircraft index {self._aircraft_index} out of range")
        
        # Check U-boat exists
        if not hasattr(game_state, 'u_boat'):
            return (False, "No U-boat in game state")
        
        return (True, f"B-24 at DL {self._detection_level} can attempt turn")
    
    def execute(self, game_state: Any) -> ActionResult:
        """Execute B-24 turn toward U-boat.
        
        Turn logic (same as original B-24 AI):
        - If same hex as U-boat and facing off-map: turn randomly
        - If facing U-boat directly: no turn
        - If facing away from U-boat: turn randomly
        - Otherwise: turn toward U-boat
        
        Args:
            game_state: Current game state (modified in place)
        
        Returns:
            ActionResult with turn details
        """
        aircraft: Aircraft = game_state.aircraft_list[self._aircraft_index]
        u_boat: UBoat = game_state.u_boat
        hex_grid = game_state.hex_grid
        dice = getattr(game_state, 'dice_roller', None)
        mission_hexes: Optional[set[HexCoord]] = getattr(hex_grid, 'mission_hexes', None)
        
        # Check if same hex as U-boat
        if aircraft.position == u_boat.position:
            forward_hex = aircraft.facing.forward(aircraft.position)
            if not hex_grid.is_valid_hex(forward_hex, mission_hexes):
                # Turn randomly
                if dice and dice.roll_1d6() <= 3:
                    aircraft.facing = aircraft.facing.rotate_clockwise()
                    self._turn_direction = "clockwise"
                    self._new_facing = aircraft.facing
                    return ActionResult(
                        success=True,
                        message="B-24 turned clockwise (same hex, facing off-map)",
                        ap_spent=0,
                        state_changes={}
                    )
                else:
                    aircraft.facing = aircraft.facing.rotate_counterclockwise()
                    self._turn_direction = "counterclockwise"
                    self._new_facing = aircraft.facing
                    return ActionResult(
                        success=True,
                        message="B-24 turned counterclockwise (same hex, facing off-map)",
                        ap_spent=0,
                        state_changes={}
                    )
            else:
                self._turn_direction = None
                return ActionResult(
                    success=True,
                    message="B-24 no turn (same hex, not facing off-map)",
                    ap_spent=0,
                    state_changes={}
                )
        
        # Check if facing U-boat directly
        if self._is_facing_target(aircraft.position, aircraft.facing, u_boat.position, hex_grid, mission_hexes):
            self._turn_direction = None
            return ActionResult(
                success=True,
                message="B-24 no turn (facing U-boat directly)",
                ap_spent=0,
                state_changes={}
            )
        
        # Check if facing away from U-boat
        if self._is_facing_away(aircraft.position, aircraft.facing, u_boat.position, hex_grid, mission_hexes):
            # Turn randomly
            if dice and dice.roll_1d6() <= 3:
                aircraft.facing = aircraft.facing.rotate_clockwise()
                self._turn_direction = "clockwise"
                self._new_facing = aircraft.facing
                return ActionResult(
                    success=True,
                    message="B-24 turned clockwise (facing away)",
                    ap_spent=0,
                    state_changes={}
                )
            else:
                aircraft.facing = aircraft.facing.rotate_counterclockwise()
                self._turn_direction = "counterclockwise"
                self._new_facing = aircraft.facing
                return ActionResult(
                    success=True,
                    message="B-24 turned counterclockwise (facing away)",
                    ap_spent=0,
                    state_changes={}
                )
        
        # Turn toward U-boat
        turn_dir = self._calculate_turn_direction(aircraft.position, aircraft.facing, u_boat.position)
        
        if turn_dir == "clockwise":
            aircraft.facing = aircraft.facing.rotate_clockwise()
            self._turn_direction = "clockwise"
            self._new_facing = aircraft.facing
            return ActionResult(
                success=True,
                message="B-24 turned clockwise toward U-boat",
                ap_spent=0,
                state_changes={}
            )
        elif turn_dir == "counterclockwise":
            aircraft.facing = aircraft.facing.rotate_counterclockwise()
            self._turn_direction = "counterclockwise"
            self._new_facing = aircraft.facing
            return ActionResult(
                success=True,
                message="B-24 turned counterclockwise toward U-boat",
                ap_spent=0,
                state_changes={}
            )
        else:
            self._turn_direction = None
            return ActionResult(
                success=True,
                message="B-24 no turn needed",
                ap_spent=0,
                state_changes={}
            )
    
    def execute_with_animation(self, game_state: Any) -> ActionResult:
        """Execute with animation trigger.
        
        Future enhancement: Add turn animation
        
        Args:
            game_state: Current game state
        
        Returns:
            ActionResult from execute()
        """
        return self.execute(game_state)
    
    def _is_facing_target(self, pos: HexCoord, facing: Facing, target: HexCoord, 
                         hex_grid: Any, mission_hexes: Optional[set[HexCoord]]) -> bool:
        """Check if facing directly toward target."""
        current = pos
        for _ in range(20):  # Arbitrary max distance
            current = facing.forward(current)
            if current == target:
                return True
            if not hex_grid.is_valid_hex(current, mission_hexes):
                return False
        return False
    
    def _is_facing_away(self, pos: HexCoord, facing: Facing, target: HexCoord,
                       hex_grid: Any, mission_hexes: Optional[set[HexCoord]]) -> bool:
        """Check if facing directly away from target."""
        opposite_facing = Facing((facing.value + 3) % 6)
        return self._is_facing_target(pos, opposite_facing, target, hex_grid, mission_hexes)
    
    def _calculate_turn_direction(self, pos: HexCoord, facing: Facing, target: HexCoord) -> str:
        """Calculate which direction to turn to face target.
        
        Returns:
            'clockwise', 'counterclockwise', or 'none'
        """
        # Calculate angle to target
        dq = target.q - pos.q
        dr = target.r - pos.r
        
        # Convert to facing
        target_direction = self._coords_to_facing(dq, dr)
        if target_direction is None:
            return 'none'
        
        # Calculate angular difference
        current = facing.value
        target_val = target_direction.value
        
        # Shortest rotation direction
        diff = (target_val - current + 6) % 6
        
        if diff == 0:
            return 'none'
        elif diff <= 3:
            return 'clockwise'
        else:
            return 'counterclockwise'
    
    def _coords_to_facing(self, dq: int, dr: int) -> Optional[Facing]:
        """Convert coordinate difference to facing direction."""
        if dq == 0 and dr < 0:
            return Facing.NORTH
        elif dq > 0 and dr < 0:
            return Facing.NORTHEAST
        elif dq > 0 and dr >= 0:
            return Facing.SOUTHEAST
        elif dq == 0 and dr > 0:
            return Facing.SOUTH
        elif dq < 0 and dr > 0:
            return Facing.SOUTHWEST
        elif dq < 0 and dr <= 0:
            return Facing.NORTHWEST
        return None
