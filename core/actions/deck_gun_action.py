"""
Deck gun action - Surface combat with deck gun.

Attacks ALL ships with LOS in range 1-3, from closest to furthest.
"""

from typing import Tuple, Dict, Any, List
from .base_action import Action, ActionResult
from ..models import UBoat, Ship, Depth
from ..los import LOSCalculator
from ..combat_resolver import CombatResolver
from ..action_costs import ActionCostLookup


class DeckGunAction(Action):
    """
    Fire deck gun at all valid targets.
    
    Requirements:
    - Must be surfaced
    - Deck gun not damaged
    - Targets in LOS and range 1-3
    
    On hit: Set DL to 3, roll damage
    Attacks all valid targets from closest to furthest.
    """
    
    def __init__(
        self,
        targets: List[Tuple[Ship, int]],  # List of (ship, distance) tuples
        cost_lookup: ActionCostLookup,
        los_calculator: LOSCalculator,
        combat_resolver: CombatResolver
    ):
        """
        Initialize deck gun action.
        
        Args:
            targets: List of (ship, distance) tuples, sorted by distance
            cost_lookup: Action cost lookup for AP costs
            los_calculator: LOS calculator for line of sight checks
            combat_resolver: Combat resolver for hit/damage rolls
        """
        super().__init__()
        self.targets = targets
        self.cost_lookup = cost_lookup
        self.los_calculator = los_calculator
        self.combat_resolver = combat_resolver
    
    def get_cost(self, u_boat: UBoat) -> int:
        """Get AP cost - only available at surface."""
        cost = self.cost_lookup.get_cost("FIRE DECK GUN", u_boat.depth)
        return cost if cost is not None else 2  # Default to 2 if cost not found
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """
        Validate deck gun attack is legal.
        
        Checks:
        - U-boat is surfaced
        - Deck gun not damaged
        - At least one valid target
        """
        u_boat = game_state.u_boat
        
        # Must be surfaced
        if u_boat.depth != Depth.SURFACED:
            return False, "Deck gun only available when surfaced"
        
        # Deck gun not damaged
        if u_boat.deck_gun_damaged:
            return False, "Deck gun is damaged"
        
        # Must have at least one target
        if not self.targets:
            return False, "No valid targets in range"
        
        return True, ""
    
    def execute(self, game_state: Any) -> ActionResult:
        """Execute the deck gun attack on all targets."""
        u_boat = game_state.u_boat
        
        results = []
        total_hits = 0
        
        # Attack each target in order (closest to furthest)
        for ship, distance in self.targets:
            # Resolve attack
            hit, roll_result, description = self.combat_resolver.resolve_deck_gun_attack(
                distance
            )
            
            if hit:
                total_hits += 1
                results.append(f"HIT {ship.ship_type} at range {distance}: {description}")
                # TODO: Apply damage to ship
            else:
                results.append(f"MISS {ship.ship_type} at range {distance}: {description}")
        
        # Build result message
        message = f"Deck gun fired at {len(self.targets)} ship(s): {total_hits} hit(s). " + "; ".join(results)
        
        # On any hit: Set detection level to 3
        if total_hits > 0:
            message += " (DL set to 3)"
            # TODO: Set game_state.detection_level = 3
        
        ap_cost = self.get_cost(u_boat)
        
        return ActionResult(
            success=True,
            message=message,
            ap_spent=ap_cost,
            state_changes={
                "targets": [ship for ship, _ in self.targets],
                "hits": total_hits,
                "action_name": "Deck Gun"
            }
        )
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for rendering."""
        can_fire, reason = self.validate(game_state)
        
        if not self.targets:
            return {
                "type": "deck_gun",
                "targets": [],
                "valid": False,
                "reason": "No valid targets",
                "cost": self.get_cost(game_state.u_boat)
            }
        
        # Get first target for display
        first_ship, distance = self.targets[0]
        
        # Get hit chance
        if distance <= 2:
            hit_target = "7+ on 2d6"
        else:  # range 3
            hit_target = "8+ on 2d6"
        
        return {
            "type": "deck_gun",
            "targets": [ship for ship, _ in self.targets],
            "range": distance,
            "hit_target": hit_target,
            "valid": can_fire,
            "reason": reason,
            "cost": self.get_cost(game_state.u_boat)
        }
    
    def get_description(self) -> str:
        """Get action description."""
        return f"Fire Deck Gun at {len(self.targets)} ship(s)"
