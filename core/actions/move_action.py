"""
Move action - U-boat movement to adjacent hex.

Integrates with MovementValidator from Phase 2.
"""

from typing import Tuple, Dict, Any
from .base_action import Action, ActionResult
from ..models import HexCoord, UBoat
from ..movement_validator import MovementValidator
from ..action_costs import ActionCostLookup



class MoveAction(Action):
    """
    Move U-boat to adjacent hex.
    
    Validates terrain, ship collisions, and depth restrictions.
    """
    
    def __init__(self, target_hex: HexCoord, cost_lookup: ActionCostLookup, validator: MovementValidator):
        """
        Initialize move action.
        
        Args:
            target_hex: Hex to move to
            cost_lookup: Action cost lookup for AP costs
            validator: Movement validator for validation
        """
        super().__init__()
        self.target_hex = target_hex
        self.cost_lookup = cost_lookup
        self.validator = validator
    
    def get_cost(self, u_boat: UBoat) -> int:
        """Get AP cost based on current depth."""
        cost = self.cost_lookup.get_cost("MOVE", u_boat.depth)
        return cost if cost is not None else 1  # Default to 1 if cost not found
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """
        Validate movement is legal.
        
        Checks:
        - Target is adjacent
        - Not blocked by terrain
        - Not blocked by ships (unless deep enough)
        - Not shallow water at wrong depth
        """
        u_boat = game_state.u_boat
        
        # Check if adjacent
        from ..hex_grid import HexGrid
        distance = HexGrid.hex_distance(u_boat.position, self.target_hex)
        if distance != 1:
            return False, f"Target hex is not adjacent (distance: {distance})"
        
        # Use MovementValidator
        can_move, reason = self.validator.can_move_to(
            u_boat,
            self.target_hex,
            game_state.ships
        )
        
        return can_move, reason
    
    def execute(self, game_state: Any) -> ActionResult:
        """Execute the move."""
        old_position = game_state.u_boat.position
        
        # Calculate cost BEFORE moving (in case future costs depend on position)
        ap_cost = self.get_cost(game_state.u_boat)
        
        # Now perform the move
        game_state.u_boat.position = self.target_hex
        
        return ActionResult(
            success=True,
            message=f"Moved from {old_position} to {self.target_hex}",
            ap_spent=ap_cost,
            state_changes={
                "old_position": old_position,
                "new_position": self.target_hex
            }
        )
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for rendering."""
        can_move, reason = self.validate(game_state)
        
        return {
            "type": "move",
            "target_hex": self.target_hex,
            "valid": can_move,
            "reason": reason,
            "cost": self.get_cost(game_state.u_boat),
            "highlight_color": (0, 255, 0) if can_move else (255, 0, 0)
        }
    
    def get_description(self) -> str:
        """Get action description."""
        return f"Move to [{self.target_hex.q},{self.target_hex.r}]"
