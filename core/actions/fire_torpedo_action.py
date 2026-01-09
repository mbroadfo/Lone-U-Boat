"""
Fire torpedo action - Launch torpedoes in facing direction.

Torpedoes travel in a straight line until hitting a ship or map edge.
Front tubes fire forward, rear tube fires backward.
"""

from typing import List, Tuple, Dict, Any
from .base_action import Action, ActionResult
from ..models import UBoat, Ship, Depth, Facing, HexCoord
from ..torpedo_validator import TorpedoValidator
from ..los import LOSCalculator
from ..combat_resolver import CombatResolver
from ..action_costs import ActionCostLookup


class FireTorpedoAction(Action):
    """
    Fire torpedoes in a direction.
    
    Torpedoes travel straight until hitting a ship or leaving map.
    Can fire 1-3 torpedoes from front (tubes 1-4) OR rear (tube 5).
    Only at SURFACED or PERISCOPE depth.
    
    Detection effects:
    - Fire 3 torpedoes: +1 DL (noise)
    - Any hit: +1 DL per hit (max +2 total)
    """
    
    def __init__(
        self,
        tube_indices: List[int],
        fire_direction: Facing,
        cost_lookup: ActionCostLookup,
        validator: TorpedoValidator,
        los_calculator: LOSCalculator,
        combat_resolver: CombatResolver
    ):
        """
        Initialize fire torpedo action.
        
        Args:
            tube_indices: List of tube indices to fire (0-4, max 3 tubes)
            fire_direction: Direction torpedoes travel (forward or backward)
            cost_lookup: Action cost lookup for AP costs
            validator: Torpedo validator for validation
            los_calculator: LOS calculator for line of sight checks
            combat_resolver: Combat resolver for hit/damage rolls
        """
        super().__init__()
        self.tube_indices = tube_indices
        self.fire_direction = fire_direction
        self.cost_lookup = cost_lookup
        self.validator = validator
        self.los_calculator = los_calculator
        self.combat_resolver = combat_resolver
    
    def get_cost(self, u_boat: UBoat) -> int:
        """Get AP cost - only available at surface/periscope."""
        cost = self.cost_lookup.get_cost("FIRE TORPS", u_boat.depth)
        return cost if cost is not None else 2  # Default to 2 if cost not found
    
    def validate(self, game_state: Any) -> Tuple[bool, str]:
        """
        Validate torpedo firing is legal.
        
        Checks:
        - Depth (only SURFACED or PERISCOPE)
        - Tube count (1-3)
        - Tubes are loaded
        - Front OR rear (not both)
        """
        u_boat = game_state.u_boat
        
        # Check depth
        if u_boat.depth not in [Depth.SURFACED, Depth.PERISCOPE]:
            return False, "Can only fire torpedoes when Surfaced or at Periscope depth"
        
        # Use TorpedoValidator
        can_fire, reason = self.validator.can_fire_tubes(
            u_boat,
            self.tube_indices
        )
        
        return can_fire, reason
    
    def execute(self, game_state: Any) -> ActionResult:
        """Execute the torpedo attack."""
        u_boat = game_state.u_boat
        
        # Trace path in fire_direction until hitting a ship or leaving map
        current_hex = u_boat.position
        target_ship = None
        travel_distance = 0
        
        # Travel up to reasonable range (e.g., 20 hexes)
        for i in range(1, 21):
            next_hex = self.fire_direction.forward(current_hex)
            travel_distance = i
            
            # Check if hex is in mission area
            if next_hex not in game_state.mission_hexes:
                break  # Torpedo left map
            
            # Check if any ship is at this hex
            for ship in game_state.ships:
                if ship.position == next_hex:
                    target_ship = ship
                    break
            
            if target_ship:
                break  # Hit a ship
            
            current_hex = next_hex
        
        # If no target found, all torpedoes miss
        if not target_ship:
            # Unload fired tubes
            for tube_idx in self.tube_indices:
                u_boat.torpedo_tubes[tube_idx] = False
            
            ap_cost = self.get_cost(u_boat)
            
            return ActionResult(
                success=True,
                message=f"Fired {len(self.tube_indices)} torpedo(es) - No targets hit (travelled {travel_distance} hexes)",
                ap_spent=ap_cost,
                state_changes={
                    "tubes_fired": self.tube_indices,
                    "hits": 0,
                    "action_name": "Fire Torpedo"
                }
            )
        
        # Calculate aspect (simplified - always use side aspect for now)
        # TODO: Calculate actual aspect based on ship and u-boat facing
        aspect = "side"
        
        # Resolve attack
        result = self.combat_resolver.resolve_torpedo_attack(
            travel_distance,
            aspect,
            len(self.tube_indices)
        )
        
        # Unload fired tubes
        for tube_idx in self.tube_indices:
            u_boat.torpedo_tubes[tube_idx] = False
        
        # Calculate DL increase
        dl_increase = 0
        if len(self.tube_indices) == 3:
            dl_increase += 1  # Noise from firing 3 torpedoes
        
        hits = result.get("hits", 0)
        if hits > 0:
            dl_increase += min(hits, 2)  # +1 DL per hit (max +2)
        
        # Build message
        if hits > 0:
            message = f"Fired {len(self.tube_indices)} torpedo(es) at {target_ship.ship_type} (range {travel_distance}): {hits} HIT(s)!"
            if dl_increase > 0:
                message += f" (DL +{dl_increase})"
            # TODO: Apply damage to ship
        else:
            message = f"Fired {len(self.tube_indices)} torpedo(es) at {target_ship.ship_type} (range {travel_distance}): MISS"
            if dl_increase > 0:
                message += f" (DL +{dl_increase})"
        
        ap_cost = self.get_cost(u_boat)
        
        return ActionResult(
            success=True,
            message=message,
            ap_spent=ap_cost,
            state_changes={
                "tubes_fired": self.tube_indices,
                "target": target_ship,
                "hits": hits,
                "dl_increase": dl_increase,
                "action_name": "Fire Torpedo"
            }
        )
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for rendering."""
        # No preview for new direction-based firing
        return {
            "type": "fire_torpedoes",
            "tubes": self.tube_indices,
            "torpedo_count": len(self.tube_indices),
            "fire_direction": self.fire_direction.name,
            "valid": True,
            "cost": self.get_cost(game_state.u_boat)
        }
    
    def get_description(self) -> str:
        """Get action description."""
        direction = "Forward" if self.fire_direction == game_state.u_boat.facing else "Rear"
        return f"Fire {len(self.tube_indices)} torpedo(es) {direction}"
