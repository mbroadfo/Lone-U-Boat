"""
Fire torpedo action - Launch torpedoes at target ship.

Integrates with TorpedoValidator, LOSCalculator, and CombatResolver from Phase 2.
"""

from typing import List, Tuple, Dict, Any
from .base_action import Action, ActionResult
from ..models import UBoat, Ship, Depth
from ..torpedo_validator import TorpedoValidator
from ..los import LOSCalculator
from ..combat_resolver import CombatResolver
from ..action_costs import ActionCostLookup


class FireTorpedoAction(Action):
    """
    Fire torpedoes at target ship.
    
    Can fire 1-3 torpedoes from front (tubes 1-4) OR rear (tube 5).
    Only at SURFACED or PERISCOPE depth.
    
    Detection effects:
    - Fire 3 torpedoes: +1 DL (noise)
    - Any hit: +1 DL per hit (max +2 total)
    """
    
    def __init__(
        self,
        target_ship: Ship,
        tube_indices: List[int],
        cost_lookup: ActionCostLookup,
        validator: TorpedoValidator,
        los_calculator: LOSCalculator,
        combat_resolver: CombatResolver
    ):
        """
        Initialize fire torpedo action.
        
        Args:
            target_ship: Ship to target
            tube_indices: List of tube indices to fire (0-4, max 3 tubes)
            cost_lookup: Action cost lookup for AP costs
            validator: Torpedo validator for validation
            los_calculator: LOS calculator for line of sight checks
            combat_resolver: Combat resolver for hit/damage rolls
        """
        super().__init__()
        self.target_ship = target_ship
        self.tube_indices = tube_indices
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
        - Target in LOS
        """
        u_boat = game_state.u_boat
        
        # Check depth
        if u_boat.depth not in [Depth.SURFACED, Depth.PERISCOPE]:
            return False, "Can only fire torpedoes when Surfaced or at Periscope depth"
        
        # Check LOS
        has_los, reason = self.los_calculator.has_line_of_sight(
            u_boat.position,
            self.target_ship.position
        )
        
        if not has_los:
            return False, f"No line of sight: {reason}"
        
        # Use TorpedoValidator
        can_fire, reason = self.validator.can_fire_tubes(
            u_boat,
            self.tube_indices
        )
        
        return can_fire, reason
    
    def execute(self, game_state: Any) -> ActionResult:
        """Execute the torpedo attack."""
        u_boat = game_state.u_boat
        
        # Calculate range and aspect
        from ..hex_grid import HexGrid
        distance = HexGrid.hex_distance(u_boat.position, self.target_ship.position)
        
        # Calculate aspect (simplified - always use side aspect)
        # TODO: Implement proper aspect calculation based on facing angles
        aspect = "side"  # Default to side for now
        
        # Resolve attack (only needs range, aspect, num_torpedoes)
        result = self.combat_resolver.resolve_torpedo_attack(
            distance,
            aspect,
            len(self.tube_indices)
        )
        
        # Unload fired tubes (tube_indices are 1-based, convert to 0-based for array)
        for tube_num in self.tube_indices:
            u_boat.torpedo_tubes[tube_num - 1] = False
        
        # Calculate DL increase
        dl_increase = 0
        if len(self.tube_indices) == 3:
            dl_increase += 1  # Noise from 3 torpedoes
        if result["hits"] > 0:
            dl_increase += result["hits"]  # +1 per hit
            dl_increase = min(dl_increase, 2)  # Max +2 total
        
        # Build message
        tube_names = [f"Tube {i}" for i in self.tube_indices]
        if result["hits"] > 0:
            message = f"Torpedoes HIT! Fired {', '.join(tube_names)} - {result['hits']} hit(s)! {result['description']} (DL +{dl_increase})"
        else:
            message = f"Torpedoes MISS. Fired {', '.join(tube_names)} - {result['description']}"
            if dl_increase > 0:
                message += f" (DL +{dl_increase})"
        
        ap_cost = self.get_cost(u_boat)
        
        return ActionResult(
            success=True,
            message=message,
            ap_spent=ap_cost,
            state_changes={
                "target": self.target_ship,
                "tubes_fired": self.tube_indices,
                "hits": result["hits"],
                "rolls": result["rolls"],
                "range": distance,
                "aspect": aspect,
                "dl_increase": dl_increase
            }
        )
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for rendering."""
        can_fire, reason = self.validate(game_state)
        
        # Calculate range for hit chance
        from ..hex_grid import HexGrid
        distance = HexGrid.hex_distance(
            game_state.u_boat.position,
            self.target_ship.position
        )
        
        # TODO: Implement proper aspect calculation
        aspect = "side"  # Default for preview
        
        # Determine hit target
        if distance <= 2:
            hit_target = "3+ (side) / 4+ (front/rear)"
        elif distance <= 4:
            hit_target = "4+ (side) / 5+ (front/rear)"
        elif distance <= 6:
            hit_target = "5+ (side) / 6+ (front/rear)"
        else:
            hit_target = "6+"
        
        return {
            "type": "fire_torpedoes",
            "target": self.target_ship,
            "tubes": self.tube_indices,
            "torpedo_count": len(self.tube_indices),
            "range": distance,
            "aspect": aspect,
            "hit_target": hit_target,
            "valid": can_fire,
            "reason": reason,
            "cost": self.get_cost(game_state.u_boat)
        }
    
    def get_description(self) -> str:
        """Get action description."""
        tube_names = [f"Tube {i+1}" for i in self.tube_indices]
        return f"Fire {', '.join(tube_names)} at {self.target_ship.ship_type}"
