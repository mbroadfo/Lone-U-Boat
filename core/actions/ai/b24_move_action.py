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
            aircraft_index: Index of aircraft in game_state.aircraft
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
        if hasattr(game_state, 'aircraft') and 0 <= self._aircraft_index < len(game_state.aircraft):
            return game_state.aircraft[self._aircraft_index]
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
            game_state: Current game state with aircraft, hex_grid
        
        Returns:
            Tuple of (can_move, reason)
        """
        # Check aircraft exists
        if not hasattr(game_state, 'aircraft'):
            return (False, "No aircraft list in game state")
        
        if self._aircraft_index >= len(game_state.aircraft):
            return (False, f"Aircraft index {self._aircraft_index} out of range")
        
        aircraft = game_state.aircraft[self._aircraft_index]
        
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
        # Validate aircraft still exists (may have been removed by earlier action)
        if self._aircraft_index >= len(game_state.aircraft):
            return ActionResult(
                success=False,
                message=f"Aircraft no longer exists (removed earlier)",
                ap_spent=0,
                state_changes={}
            )
        
        aircraft: Aircraft = game_state.aircraft[self._aircraft_index]
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
                # Remove aircraft from game when it flies off map
                game_state.aircraft.pop(self._aircraft_index)
                return ActionResult(
                    success=True,
                    message=f"B-24 flew off map after {move_num - 1} hex(es)",
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
        
        Triggers aircraft movement animation.
        
        Args:
            game_state: Current game state
        
        Returns:
            ActionResult from execute()
        """
        # Validate aircraft still exists
        if self._aircraft_index >= len(game_state.aircraft):
            return ActionResult(
                success=False,
                message=f"Aircraft no longer exists (removed earlier)",
                ap_spent=0,
                state_changes={}
            )
        
        aircraft = game_state.aircraft[self._aircraft_index]
        old_position = aircraft.position
        
        # Execute the movement
        result = self.execute(game_state)
        
        # If successful and aircraft moved (not off map), trigger animation for each hex moved
        if result.success and not self._off_map and len(self._moves_made) > 0:
            if hasattr(game_state, 'animation_manager') and game_state.animation_manager:
                # Animate each movement step
                current_pos = old_position
                for new_pos in self._moves_made:
                    game_state.animation_manager.start_aircraft_movement(
                        self._aircraft_index,
                        current_pos,
                        new_pos
                    )
                    current_pos = new_pos
        
        return result
