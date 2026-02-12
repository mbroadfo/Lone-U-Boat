"""
EscortMoveAction - Moves escort one hex forward.

Moves escort in facing direction, checking for blocking, land hexes,
and mission boundaries. Triggers movement and rotation animations.
"""

from typing import Tuple, Dict, Any, Optional
from core.actions.ai.base_ai_action import AIAction
from core.actions.base_action import ActionResult
from core.models import Ship, HexCoord, Depth


class EscortMoveAction(AIAction):
    """Move escort one hex forward."""
    
    def __init__(
        self,
        entity_index: int,
        target_hex: Optional[HexCoord] = None
    ):
        """
        Initialize escort move action.
        
        Args:
            entity_index: Index of escort ship in game_state.ships
            target_hex: Destination hex (if None, calculates forward)
        """
        super().__init__(entity_index)
        self.target_hex = target_hex
        self.blocked_by: Optional[Ship] = None
        self.forced_dive_triggered: bool = False
        self.uboat_destroyed: bool = False
    
    @property
    def triggers_animation(self) -> bool:
        """Movement triggers animations."""
        return True
    
    @property
    def requires_player_input(self) -> bool:
        """Movement is automated."""
        return False
    
    def get_entity(self, game_state: Any) -> Optional[Ship]:
        """Get the escort ship."""
        if 0 <= self.entity_index < len(game_state.ships):
            ship = game_state.ships[self.entity_index]
            if ship.ship_type in ['corvette', 'destroyer']:
                return ship
        return None
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """Validate escort can move."""
        escort = self.get_entity(game_state)
        
        if escort is None:
            return False, f"Ship {self.entity_index} is not an escort"
        
        # Calculate target hex if not provided
        if self.target_hex is None:
            self.target_hex = escort.facing.forward(escort.position)
        
        # Check if target is blocked
        land_hexes: set[HexCoord] = getattr(game_state, 'land_hexes', set())
        mission_hexes = getattr(game_state, 'mission_hexes', None)
        
        # Check land
        if self.target_hex in land_hexes:
            return False, "Move blocked: land hex"
        
        # Check mission boundaries
        if mission_hexes is not None and self.target_hex not in mission_hexes:
            return False, "Move blocked: off map"
        
        # Check for blocking ships
        for ship in game_state.ships:
            if ship != escort and ship.position == self.target_hex:
                self.blocked_by = ship
                return False, f"Move blocked: {ship.ship_type} at destination"
        
        return True, "Can move forward"
    
    def execute_with_animation(self, game_state: Any) -> ActionResult:
        """
        Execute escort movement.
        
        Returns:
            ActionResult with movement details
        """
        escort = self.get_entity(game_state)
        if escort is None:
            return ActionResult(
                success=False,
                message=f"Cannot move ship {self.entity_index}",
                ap_spent=0,
                state_changes={}
            )
        
        old_position = escort.position
        
        # Move escort
        assert self.target_hex is not None, "target_hex must be set before execute"
        escort.position = self.target_hex
        
        # Trigger movement animation
        if hasattr(game_state, 'animation_manager') and game_state.animation_manager:
            game_state.animation_manager.ship_movements.append(
                (self.entity_index, old_position, self.target_hex)
            )
        
        # Check for forced dive (if U-boat at destination and surfaced)
        state_changes: Dict[str, Any] = {
            'old_position': old_position,
            'new_position': self.target_hex
        }
        
        if hasattr(game_state, 'uboat') and game_state.uboat.position == self.target_hex:
            u_boat = game_state.uboat
            if u_boat.depth == Depth.SURFACED:
                shallow_hexes: set[HexCoord] = getattr(game_state, 'shallow_hexes', set())
                
                # Check if forced dive destroys U-boat
                if self.target_hex in shallow_hexes:
                    self.uboat_destroyed = True
                    u_boat.hull_damage = 4
                    state_changes['forced_dive'] = True
                    state_changes['uboat_destroyed'] = True
                    return ActionResult(
                        success=True,
                        message=f"MOVE: [{old_position.q},{old_position.r}] -> [{self.target_hex.q},{self.target_hex.r}] - FORCED DIVE in shallow water, U-boat DESTROYED!",
                        ap_spent=0,
                        state_changes=state_changes
                    )
                else:
                    self.forced_dive_triggered = True
                    u_boat.depth = Depth.MEDIUM
                    state_changes['forced_dive'] = True
                    state_changes['new_depth'] = Depth.MEDIUM
                    
                    # Increase DL
                    if hasattr(game_state, 'detection_level'):
                        game_state.detection_level = min(3, game_state.detection_level + 1)
                        state_changes['detection_level_change'] = 1
                    
                    # Apply forced dive penalty
                    if hasattr(game_state, 'turn_manager') and game_state.turn_manager:
                        game_state.turn_manager.force_dive_penalty = 1
                        state_changes['dive_penalty_applied'] = True
        
        distance = 0
        if hasattr(game_state, 'hex_grid') and hasattr(game_state, 'uboat'):
            distance = game_state.hex_grid.hex_distance(self.target_hex, game_state.uboat.position)
            state_changes['distance_to_uboat'] = distance
        
        message = f"MOVE: [{old_position.q},{old_position.r}] -> [{self.target_hex.q},{self.target_hex.r}]"
        if distance > 0:
            message += f" (Range: {distance})"
        if self.forced_dive_triggered:
            message += " - FORCED DIVE!"
        
        return ActionResult(
            success=True,
            message=message,
            ap_spent=0,
            state_changes=state_changes
        )
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for UI."""
        escort = self.get_entity(game_state)
        
        return {
            'type': 'escort_move',
            'ship_index': self.entity_index,
            'current_position': escort.position if escort else None,
            'target_position': self.target_hex,
            'blocked_by': self.blocked_by.ship_type if self.blocked_by else None,
            'valid': escort is not None and self.target_hex is not None
        }
