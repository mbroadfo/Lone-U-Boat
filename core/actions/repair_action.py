"""
Repair action - Fix damaged U-boat systems.

Integrates with RepairValidator from Phase 2.
"""

from typing import Tuple, Dict, Any
from .base_action import Action, ActionResult
from ..models import UBoat, TubeState
from ..repair_validator import RepairValidator
from ..action_costs import ActionCostLookup


class RepairAction(Action):
    """
    Repair U-boat systems or torpedo tubes.
    
    Can repair:
    - 1 damage marker (engine, deck gun, flak gun)
    - Up to 2 torpedo tubes
    
    Restrictions enforced by RepairValidator.
    """
    
    def __init__(self, repair_target: str, cost_lookup: ActionCostLookup, validator: RepairValidator, tube_number: int = None, ap_cost_override: int = None):
        """
        Initialize repair action.
        
        Args:
            repair_target: What to repair ("Engine", "Deck Gun", "Flak Gun", "Torpedo Tubes")
            cost_lookup: Action cost lookup for AP costs
            validator: Repair validator for validation
            tube_number: For torpedo tubes, the specific tube to repair (1-5)
            ap_cost_override: Override the AP cost (used for free even-numbered tube repairs)
        """
        super().__init__()
        self.repair_target = repair_target
        self.cost_lookup = cost_lookup
        self.validator = validator
        self.tube_number = tube_number
        self.ap_cost_override = ap_cost_override
    
    def get_cost(self, u_boat: UBoat) -> int:
        """Get AP cost based on current depth or override."""
        if self.ap_cost_override is not None:
            return self.ap_cost_override
        cost = self.cost_lookup.get_cost("REPAIR", u_boat.depth)
        return cost if cost is not None else 2  # Default to 2 if cost not found
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """
        Validate repair is legal.
        
        Checks:
        - Target is damaged
        - Depth restrictions (guns only at surface)
        - Engineer alive for submerged repairs
        - Hull damage cannot be repaired
        """
        u_boat = game_state.u_boat
        
        # Use RepairValidator
        can_repair, reason = self.validator.can_repair_component(
            u_boat,
            self.repair_target
        )
        
        return can_repair, reason
    
    def execute(self, game_state: Any) -> ActionResult:
        """Execute the repair."""
        u_boat = game_state.u_boat
        
        # Repair the target
        if self.repair_target == "Engine":
            u_boat.engine_damaged = False
            message = "Repaired Engine"
        elif self.repair_target == "Deck Gun":
            u_boat.deck_gun_damaged = False
            message = "Repaired Deck Gun"
        elif self.repair_target == "Flak Gun":
            u_boat.flak_gun_damaged = False
            message = "Repaired Flak Gun"
        elif self.repair_target == "Torpedo Tubes":
            # Repair specific tube or up to 2 damaged tubes if no specific tube specified
            if self.tube_number is not None:
                # Repair specific tube
                tube_index = self.tube_number - 1
                if u_boat.torpedo_tubes[tube_index] == TubeState.DAMAGED:
                    u_boat.torpedo_tubes[tube_index] = TubeState.EMPTY  # Repaired tubes are empty, need loading
                    message = f"Repaired Torpedo {self.tube_number}"
                else:
                    message = f"Torpedo {self.tube_number} was not damaged"
            else:
                # Repair up to 2 damaged tubes (legacy behavior)
                repaired = 0
                for i in range(len(u_boat.torpedo_tubes)):
                    if u_boat.torpedo_tubes[i] == TubeState.DAMAGED and repaired < 2:
                        u_boat.torpedo_tubes[i] = TubeState.EMPTY  # Repaired tubes are empty, need loading
                        repaired += 1
                message = f"Repaired {repaired} torpedo tube{'s' if repaired != 1 else ''}"
        else:
            message = f"Unknown repair target: {self.repair_target}"
        
        ap_cost = self.get_cost(u_boat)
        
        return ActionResult(
            success=True,
            message=message,
            ap_spent=ap_cost,
            state_changes={
                "repair_target": self.repair_target
            }
        )
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for rendering."""
        can_repair, reason = self.validate(game_state)
        
        return {
            "type": "repair",
            "target": self.repair_target,
            "valid": can_repair,
            "reason": reason,
            "cost": self.get_cost(game_state.u_boat)
        }
    
    def get_description(self) -> str:
        """Get action description."""
        target_names = {
            "engine": "Engine",
            "deck_gun": "Deck Gun",
            "flak_gun": "Flak Gun",
            "torpedoes": "Torpedo Tubes"
        }
        target_name = target_names.get(self.repair_target, self.repair_target)
        return f"Repair {target_name}"
