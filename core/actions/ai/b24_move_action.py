"""
B-24 Move Action - Interactive AI system.

Handles B-24 aircraft movement (2 hexes forward) with map boundary validation.
"""

from typing import Tuple, Optional, Any, Dict
from .base_ai_action import AIAction, ActionResult
from core.models import Aircraft, HexCoord


class B24MoveAction(AIAction):
    """Action for B-24 moving 2 hexes forward."""
    
    def __init__(self, aircraft_index: int):
        """Initialize B-24 move action.
        
        Args:
            aircraft_index: Index of aircraft in game_state.aircraft_list
        """
        super().__init__(entity_index=aircraft_index)
        self._aircraft_index = aircraft_index
        self._off_map = False
        self._moves_made: list[HexCoord] = []
    
    @property
    def triggers_animation(self) -> bool:
        """Movement triggers animation."""
        return True
    
    @property
    def requires_player_input(self) -> bool:
        """Movement is automated."""
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
            'type': 'b24_move',
            'aircraft_index': self._aircraft_index,
            'current_position': aircraft.position if aircraft else None,
            'moves': self._moves_made,
            'off_map': self._off_map
        }
    
    @property
    def aircraft_index(self) -> int:
        """Get the aircraft index."""
        return self._aircraft_index
    
    @property
    def off_map(self) -> bool:
        """Whether aircraft moved off map."""
        return self._off_map
    
    @property
    def moves_made(self) -> list[HexCoord]:
        """List of positions moved through."""
        return self._moves_made
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """Validate that aircraft can move.
        
        Args:
            game_state: Current game state with aircraft_list, hex_grid
        
        Returns:
            Tuple of (can_move, reason)
        """
        # Check aircraft exists
        if not hasattr(game_state, 'aircraft_list'):
            return (False, "No aircraft list in game state")
        
        if self._aircraft_index >= len(game_state.aircraft_list):
            return (False, f"Aircraft index {self._aircraft_index} out of range")
        
        aircraft = game_state.aircraft_list[self._aircraft_index]
        
        # Check hex grid
        if not hasattr(game_state, 'hex_grid'):
            return (False, "No hex grid in game state")
        
        # B-24 can always attempt to move (may fly off map)
        return (True, f"B-24 at [{aircraft.position.q},{aircraft.position.r}] can move")
    
    def execute(self, game_state: Any) -> ActionResult:
        """Execute B-24 movement.
        
        Moves B-24 2 hexes forward. If aircraft moves off map during either hex,
        it is removed from play.
        
        Args:
            game_state: Current game state (modified in place)
        
        Returns:
            ActionResult with success status and movement details
        """
        aircraft: Aircraft = game_state.aircraft_list[self._aircraft_index]
        hex_grid = game_state.hex_grid
        mission_hexes: Optional[set[HexCoord]] = getattr(hex_grid, 'mission_hexes', None)
        
        self._moves_made = []
        self._off_map = False
        
        # Move up to 2 hexes
        for move_num in range(1, 3):
            new_pos = aircraft.facing.forward(aircraft.position)
            
            # Check if off map
            if not hex_grid.is_valid_hex(new_pos, mission_hexes):
                self._off_map = True
                return ActionResult(
                    success=True,
                    message=f"B-24 moved off map after {move_num - 1} hex(es)",
                    ap_spent=0,
                    state_changes={}
                )
            
            # Move to new position
            aircraft.position = new_pos
            self._moves_made.append(new_pos)
        
        return ActionResult(
            success=True,
            message=f"B-24 moved to [{aircraft.position.q},{aircraft.position.r}]",
            ap_spent=0,
            state_changes={}
        )
    
    def execute_with_animation(self, game_state: Any) -> ActionResult:
        """Execute with animation trigger.
        
        Future enhancement: Add movement animation
        
        Args:
            game_state: Current game state
        
        Returns:
            ActionResult from execute()
        """
        return self.execute(game_state)
