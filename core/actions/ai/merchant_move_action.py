"""
Merchant Move Action - Move a single merchant ship along its path.

In interactive AI mode, each merchant moves individually with animation,
allowing players to see step-by-step movement just like the board game.
"""

from typing import Any, Dict, Optional, Tuple, List
from .base_ai_action import AIAction, ActionResult
from ...models import Ship, HexCoord, Facing


class MerchantMoveAction(AIAction):
    """
    Move a single merchant ship to its next waypoint.
    
    This action encapsulates one merchant's movement, including:
    - Path following logic
    - Collision detection
    - Facing changes
    - Animation triggers
    
    Attributes:
        entity_index: Index of the merchant ship in game.ships
        target_hex: Destination hex (from path)
        new_facing: Facing direction after move
        check_collisions: Whether to validate destination is unblocked
    """
    
    def __init__(
        self,
        entity_index: int,
        target_hex: Optional[HexCoord] = None,
        new_facing: Optional[Facing] = None,
        check_collisions: bool = True
    ):
        """
        Initialize merchant move action.
        
        Args:
            entity_index: Index of merchant in ships list
            target_hex: Destination hex (if None, calculated from path)
            new_facing: New facing (if None, calculated from path)
            check_collisions: Whether to check for blocking ships
        """
        super().__init__(entity_index)
        self.target_hex = target_hex
        self.new_facing = new_facing
        self.check_collisions = check_collisions
        self.triggers_animation = True
        self.blocked_by = None  # Will track blocking ship if any
    
    def get_entity(self, game_state: Any) -> Ship:
        """Get the merchant ship this action affects."""
        return game_state.ships[self.entity_index]
    
    def _calculate_movement(self, game_state: Any) -> Tuple[Optional[HexCoord], Optional[Facing], str]:
        """
        Calculate target hex and facing from merchant AI path logic.
        
        Args:
            game_state: Current game state
            
        Returns:
            (target_hex, new_facing, reason)
        """
        ship = self.get_entity(game_state)
        
        # Use merchant AI to get movement
        if hasattr(game_state, 'merchant_ai'):
            return game_state.merchant_ai.get_merchant_movement(ship, self.entity_index)
        
        # Fallback: just return provided values
        return self.target_hex, self.new_facing, "No merchant AI available"
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """
        Validate that merchant can move to target hex.
        
        Checks:
        - Ship exists and is a merchant
        - Target hex is on path
        - Destination not blocked by another ship
        - Not at exit hex
        
        Args:
            game_state: Current game state
            
        Returns:
            (can_perform, reason_if_not)
        """
        if self.entity_index >= len(game_state.ships):
            return False, f"Ship index {self.entity_index} out of range"
        
        ship = game_state.ships[self.entity_index]
        
        if ship.ship_type != 'merchant':
            return False, f"Ship is not a merchant (is {ship.ship_type})"
        
        # Calculate movement if not provided
        if self.target_hex is None:
            calc_target, calc_facing, message = self._calculate_movement(game_state)
            if calc_target is None:
                return False, message
            self.target_hex = calc_target
            self.new_facing = calc_facing
        
        # Check for blocking ships
        if self.check_collisions:
            for other_idx, other_ship in enumerate(game_state.ships):
                if other_idx != self.entity_index and other_ship.position == self.target_hex:
                    self.blocked_by = other_ship
                    return False, f"Destination blocked by {other_ship.ship_type}"
        
        return True, f"Can move to [{self.target_hex.q},{self.target_hex.r}]"
    
    def execute_with_animation(self, game_state: Any) -> ActionResult:
        """
        Execute merchant movement and trigger animations.
        
        Args:
            game_state: Current game state (will be modified)
            
        Returns:
            ActionResult with movement details
        """
        ship = self.get_entity(game_state)
        old_position = ship.position
        old_facing = ship.facing
        
        # Store old state for animation
        state_changes: Dict[str, Any] = {
            'ship_index': self.entity_index,
            'old_position': old_position,
            'old_facing': old_facing
        }
        
        # Apply movement
        if self.target_hex:
            ship.position = self.target_hex
            state_changes['new_position'] = self.target_hex
        
        if self.new_facing:
            ship.facing = self.new_facing
            state_changes['new_facing'] = self.new_facing
        
        # Trigger animations
        if hasattr(game_state, 'animation_manager'):
            # Rotation animation (if facing changed)
            if self.new_facing and old_facing != self.new_facing:
                game_state.animation_manager.start_ship_rotation(
                    self.entity_index,
                    old_facing,
                    self.new_facing
                )
            
            # Movement animation (if position changed)
            if self.target_hex and old_position != self.target_hex:
                game_state.animation_manager.start_ship_movement(
                    self.entity_index,
                    old_position,
                    self.target_hex
                )
        
        # Build message
        parts: List[str] = []
        if self.target_hex:
            parts.append(f"moved to [{self.target_hex.q},{self.target_hex.r}]")
        if self.new_facing and old_facing != self.new_facing:
            parts.append(f"facing {self.new_facing.name}")
        
        message = f"Merchant " + ", ".join(parts) if parts else "Merchant (no movement)"
        
        return ActionResult(
            success=True,
            message=message,
            ap_spent=0,
            state_changes=state_changes
        )
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """
        Get preview data for rendering.
        
        Shows path line and destination hex.
        """
        ship = self.get_entity(game_state)
        can_move, reason = self.validate(game_state)
        
        return {
            "type": "merchant_move",
            "ship_index": self.entity_index,
            "current_position": ship.position,
            "target_position": self.target_hex,
            "new_facing": self.new_facing,
            "valid": can_move,
            "reason": reason,
            "highlight_color": (0, 255, 100) if can_move else (255, 100, 0)
        }
    
    def get_description(self) -> str:
        """Get human-readable description."""
        if self.target_hex:
            return f"Merchant move to [{self.target_hex.q},{self.target_hex.r}]"
        return f"Merchant move (calculating path)"
