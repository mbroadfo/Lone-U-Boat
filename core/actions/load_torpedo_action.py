"""
Torpedo load action - Load torpedo tubes.

Integrates with TorpedoValidator from Phase 2.
"""

from typing import List, Tuple, Dict, Any
from .base_action import Action, ActionResult
from ..models import UBoat, Depth
from ..torpedo_validator import TorpedoValidator
from ..action_costs import ActionCostLookup


class LoadTorpedoAction(Action):
    """
    Load torpedo tubes.
    
    Can load 2 tubes (1 if Weapons Officer KIA).
    Only at SURFACED (1 AP) or PERISCOPE (4 AP).
    """
    
    def __init__(
        self,
        tube_indices: List[int],
        cost_lookup: ActionCostLookup,
        validator: TorpedoValidator
    ):
        """
        Initialize load torpedo action.
        
        Args:
            tube_indices: List of tube indices to load (0-4)
            cost_lookup: Action cost lookup for AP costs
            validator: Torpedo validator for validation
        """
        super().__init__()
        self.tube_indices = tube_indices
        self.cost_lookup = cost_lookup
        self.validator = validator
    
    def get_cost(self, u_boat: UBoat) -> int:
        """Get AP cost - only available at surface/periscope."""
        cost = self.cost_lookup.get_cost("LOAD TORPS", u_boat.depth)
        return cost if cost is not None else 1  # Default to 1 if cost not found
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """
        Validate torpedo loading is legal.
        
        Checks:
        - Depth (only SURFACED or PERISCOPE)
        - Tube count (2 max, 1 if WO KIA)
        - Tubes are not already loaded
        - Tubes are not damaged
        """
        u_boat = game_state.u_boat
        
        # Check depth
        if u_boat.depth not in [Depth.SURFACED, Depth.PERISCOPE]:
            return False, "Can only load torpedoes when Surfaced or at Periscope depth"
        
        # Use TorpedoValidator
        can_load, reason = self.validator.can_load_tubes(
            u_boat,
            self.tube_indices
        )
        
        return can_load, reason
    
    def execute(self, game_state: Any) -> ActionResult:
        """Execute the torpedo loading."""
        u_boat = game_state.u_boat
        
        # Load the tubes (tube_indices are 1-based, convert to 0-based for array)
        for tube_num in self.tube_indices:
            u_boat.torpedo_tubes[tube_num - 1] = True
        
        tube_names = [f"Tube {i}" for i in self.tube_indices]
        message = f"Loaded {', '.join(tube_names)}"
        
        ap_cost = self.get_cost(u_boat)
        
        return ActionResult(
            success=True,
            message=message,
            ap_spent=ap_cost,
            state_changes={
                "loaded_tubes": self.tube_indices
            }
        )
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for rendering."""
        can_load, reason = self.validate(game_state)
        
        return {
            "type": "load_torpedoes",
            "tubes": self.tube_indices,
            "valid": can_load,
            "reason": reason,
            "cost": self.get_cost(game_state.u_boat)
        }
    
    def get_description(self) -> str:
        """Get action description."""
        tube_names = [f"Tube {i+1}" for i in self.tube_indices]
        return f"Load {', '.join(tube_names)}"
