"""
Depth change action - U-boat depth adjustment.

Integrates with DepthValidator from Phase 2.
Enforces once-per-turn restriction.
"""

from typing import Tuple, Dict, Any
from .base_action import Action, ActionResult
from ..models import UBoat, Depth
from ..depth_validator import DepthValidator
from ..action_costs import ActionCostLookup


class DepthChangeAction(Action):
    """
    Change U-boat depth.
    
    Validates depth limits, hull damage restrictions, and once-per-turn rule.
    """
    
    def __init__(self, new_depth: Depth, cost_lookup: ActionCostLookup, validator: DepthValidator):
        """
        Initialize depth change action.
        
        Args:
            new_depth: Target depth (Depth enum)
            cost_lookup: Action cost lookup for AP costs
            validator: Depth validator for validation
        """
        super().__init__()
        self.new_depth = new_depth
        self.cost_lookup = cost_lookup
        self.validator = validator
    
    def get_cost(self, u_boat: UBoat) -> int:
        """Get AP cost based on current depth."""
        cost = self.cost_lookup.get_cost("CHANGE DEPTH", u_boat.depth)
        return cost if cost is not None else 1  # Default to 1 if cost not found
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """
        Validate depth change is legal.
        
        Checks:
        - Valid depth range (0-3)
        - Depth must change (can't stay same)
        """
        u_boat = game_state.u_boat
        
        # TODO: Check once-per-turn restriction when GameState tracks it
        # if game_state.has_changed_depth_this_turn:
        #     return False, "Already changed depth this turn"
        
        # Check if depth actually changes
        if self.new_depth == u_boat.depth:
            return False, "Must change depth (can't stay at current depth)"
        
        # Use DepthValidator with turn manager's depth_changed flag
        depth_changed_this_turn = game_state.turn_manager.depth_changed_this_turn
        can_change, reason = self.validator.can_change_depth(
            u_boat,
            self.new_depth,
            u_boat.position,
            game_state.ships,
            depth_changed_this_turn
        )
        
        return can_change, reason
    
    def execute(self, game_state: Any) -> ActionResult:
        """Execute the depth change."""
        old_depth = game_state.u_boat.depth
        
        # Calculate cost BEFORE changing depth (cost is based on CURRENT depth)
        ap_cost = self.get_cost(game_state.u_boat)
        
        # Now perform the depth change
        game_state.u_boat.depth = self.new_depth
        game_state.turn_manager.depth_changed_this_turn = True
        
        # Depth names for better messages
        depth_names = {
            Depth.SURFACED: "Surface",
            Depth.PERISCOPE: "Periscope Depth",
            Depth.MEDIUM: "Medium",
            Depth.DEEP: "Deep"
        }
        
        old_name = depth_names.get(old_depth, f"Depth {old_depth}")
        new_name = depth_names.get(self.new_depth, f"Depth {self.new_depth}")
        
        return ActionResult(
            success=True,
            message=f"Changed depth from {old_name} to {new_name}",
            ap_spent=ap_cost,
            state_changes={
                "old_depth": old_depth,
                "new_depth": self.new_depth
            }
        )
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for rendering."""
        can_change, reason = self.validate(game_state)
        
        depth_names = {
            Depth.SURFACED: "Surface",
            Depth.PERISCOPE: "Periscope Depth",
            Depth.MEDIUM: "Medium",
            Depth.DEEP: "Deep"
        }
        
        return {
            "type": "depth_change",
            "old_depth": game_state.u_boat.depth,
            "new_depth": self.new_depth,
            "old_depth_name": depth_names.get(game_state.u_boat.depth, f"Depth {game_state.u_boat.depth}"),
            "new_depth_name": depth_names.get(self.new_depth, f"Depth {self.new_depth}"),
            "valid": can_change,
            "reason": reason,
            "cost": self.get_cost(game_state.u_boat)
            # TODO: Add "already_changed": game_state.has_changed_depth_this_turn
        }
    
    def get_description(self) -> str:
        """Get action description."""
        depth_names = {
            Depth.SURFACED: "Surface",
            Depth.PERISCOPE: "Periscope Depth",
            Depth.MEDIUM: "Medium",
            Depth.DEEP: "Deep"
        }
        depth_name = depth_names.get(self.new_depth, f"Depth {self.new_depth}")
        return f"Change depth to {depth_name}"
