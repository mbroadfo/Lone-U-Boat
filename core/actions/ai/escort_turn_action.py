"""
EscortTurnAction - Turns escort 45° left or right.

Turns escort toward target based on detection level (DL 0-1 = anchor, DL 2-3 = U-boat).
Handles blocked turns and facing calculations. Triggers rotation animations.
"""

from typing import Tuple, Dict, Any, Optional
from core.actions.ai.base_ai_action import AIAction
from core.actions.base_action import ActionResult
from core.models import Ship, HexCoord, Facing


class EscortTurnAction(AIAction):
    """Turn escort toward target."""
    
    def __init__(
        self,
        entity_index: int,
        target_hex: Optional[HexCoord] = None,
        detection_level: int = 0,
        new_facing: Optional[Facing] = None
    ):
        """
        Initialize escort turn action.
        
        Args:
            entity_index: Index of escort ship in game_state.ships
            target_hex: Target to turn toward (anchor or U-boat)
            detection_level: Current DL (determines anchor vs U-boat target)
            new_facing: Explicit facing (if None, calculates based on target)
        """
        super().__init__(entity_index)
        self.target_hex = target_hex
        self.detection_level = detection_level
        self.new_facing = new_facing
    
    @property
    def triggers_animation(self) -> bool:
        """Turning triggers rotation animation."""
        return True
    
    @property
    def requires_player_input(self) -> bool:
        """Turn is automated."""
        return False
    
    def get_entity(self, game_state: Any) -> Optional[Ship]:
        """Get the escort ship."""
        if 0 <= self.entity_index < len(game_state.ships):
            ship = game_state.ships[self.entity_index]
            if ship.ship_type in ['corvette', 'destroyer']:
                return ship
        return None
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """Validate escort can turn."""
        escort = self.get_entity(game_state)
        
        if escort is None:
            return False, f"Ship {self.entity_index} is not an escort"
        
        # Determine target if not provided
        if self.target_hex is None:
            if hasattr(game_state, 'escort_ai') and hasattr(game_state, 'u_boat'):
                self.target_hex = game_state.escort_ai.get_turn_target(
                    escort, game_state.u_boat, self.detection_level
                )
            else:
                return False, "Cannot determine turn target"
        
        # Calculate new facing if not provided
        if self.new_facing is None:
            self.new_facing = self._calculate_turn_direction(escort, game_state)
        
        # Check if already facing target
        if self.new_facing is None or self.new_facing == escort.facing:
            return False, "No turn needed - already facing target"
        
        return True, f"Can turn from {escort.facing.name} to {self.new_facing.name}"
    
    def _calculate_turn_direction(self, escort: Ship, game_state: Any) -> Optional[Facing]:
        """Calculate which direction to turn."""
        if not hasattr(game_state, 'escort_ai'):
            return None
        
        land_hexes: set[HexCoord] = getattr(game_state, 'land_hexes', set())
        mission_hexes = getattr(game_state, 'mission_hexes', None)
        
        return game_state.escort_ai.calculate_turn_direction(
            escort, self.target_hex, land_hexes, game_state.ships, mission_hexes
        )
    
    def execute_with_animation(self, game_state: Any) -> ActionResult:
        """
        Execute escort turn.
        
        Returns:
            ActionResult with turn details
        """
        escort = self.get_entity(game_state)
        if escort is None or self.new_facing is None:
            return ActionResult(
                success=False,
                message=f"Cannot turn ship {self.entity_index}",
                ap_spent=0,
                state_changes={}
            )
        
        old_facing = escort.facing
        
        # Turn escort
        escort.facing = self.new_facing
        
        # Trigger rotation animation
        if hasattr(game_state, 'animation_manager') and game_state.animation_manager:
            game_state.animation_manager.start_ship_rotation(
                self.entity_index,
                old_facing,
                self.new_facing
            )
        
        # Determine turn direction for message
        turn_dir = "clockwise" if self._is_clockwise_turn(old_facing, self.new_facing) else "counterclockwise"
        
        target_name = "anchor"
        if self.detection_level >= 2:
            target_name = "U-boat"
        
        return ActionResult(
            success=True,
            message=f"TURN: {old_facing.name} -> {self.new_facing.name} ({turn_dir}, toward {target_name})",
            ap_spent=0,
            state_changes={
                'old_facing': old_facing,
                'new_facing': self.new_facing,
                'target_hex': self.target_hex,
                'detection_level': self.detection_level
            }
        )
    
    def _is_clockwise_turn(self, old_facing: Facing, new_facing: Facing) -> bool:
        """Determine if turn is clockwise."""
        diff = (new_facing.value - old_facing.value) % 6
        return diff <= 3
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for UI."""
        escort = self.get_entity(game_state)
        
        return {
            'type': 'escort_turn',
            'ship_index': self.entity_index,
            'current_facing': escort.facing if escort else None,
            'new_facing': self.new_facing,
            'target_hex': self.target_hex,
            'detection_level': self.detection_level,
            'valid': escort is not None and self.new_facing is not None
        }
