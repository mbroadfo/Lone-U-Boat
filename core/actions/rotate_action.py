"""
Rotate action - U-boat rotation by 60 degrees.

Simple action - no special validation needed.
"""

from typing import Tuple, Dict, Any
from .base_action import Action, ActionResult
from ..models import UBoat
from ..action_costs import ActionCostLookup


class RotateAction(Action):
    """
    Rotate U-boat by 60 degrees (one hex facing).
    
    Can rotate clockwise or counter-clockwise.
    """
    
    def __init__(self, clockwise: bool, cost_lookup: ActionCostLookup):
        """
        Initialize rotate action.
        
        Args:
            clockwise: True to rotate clockwise, False for counter-clockwise
            cost_lookup: Action cost lookup for AP costs
        """
        super().__init__()
        self.clockwise = clockwise
        self.cost_lookup = cost_lookup
    
    def get_cost(self, u_boat: UBoat) -> int:
        """Get AP cost based on current depth."""
        cost = self.cost_lookup.get_cost("TURN", u_boat.depth)
        return cost if cost is not None else 1  # Default to 1 if cost not found
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """
        Validate rotation is legal.
        
        Rotation is always valid - no special restrictions.
        """
        return True, ""
    
    def execute(self, game_state: Any) -> ActionResult:
        """Execute the rotation."""
        old_facing = game_state.u_boat.facing
        
        # Rotate using Facing enum methods
        if self.clockwise:
            new_facing = old_facing.rotate_clockwise()
        else:
            new_facing = old_facing.rotate_counterclockwise()
        
        game_state.u_boat.facing = new_facing
        
        ap_cost = self.get_cost(game_state.u_boat)
        
        direction = "clockwise" if self.clockwise else "counter-clockwise"
        
        return ActionResult(
            success=True,
            message=f"Rotated {direction} from {old_facing.name} to {new_facing.name}",
            ap_spent=ap_cost,
            state_changes={
                "old_facing": old_facing,
                "new_facing": new_facing
            }
        )
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for rendering."""
        old_facing = game_state.u_boat.facing
        
        if self.clockwise:
            new_facing = old_facing.rotate_clockwise()
        else:
            new_facing = old_facing.rotate_counterclockwise()
        
        return {
            "type": "rotate",
            "clockwise": self.clockwise,
            "old_facing": old_facing,
            "new_facing": new_facing,
            "cost": self.get_cost(game_state.u_boat),
            "valid": True
        }
    
    def get_description(self) -> str:
        """Get action description."""
        direction = "clockwise" if self.clockwise else "counter-clockwise"
        return f"Rotate {direction}"
