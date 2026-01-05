"""
Deck gun action - Surface combat with deck gun.

Integrates with RangeLOSValidator and CombatResolver from Phase 2.
"""

from typing import Tuple, Dict, Any
from .base_action import Action, ActionResult
from ..models import UBoat, Ship, Depth
from ..los import LOSCalculator
from ..combat_resolver import CombatResolver
from ..action_costs import ActionCostLookup


class DeckGunAction(Action):
    """
    Fire deck gun at target ship.
    
    Requirements:
    - Must be surfaced
    - Deck gun not damaged
    - Target in LOS and range 1-3
    
    On hit: Set DL to 3, roll damage
    """
    
    def __init__(
        self,
        target_ship: Ship,
        cost_lookup: ActionCostLookup,
        los_calculator: LOSCalculator,
        combat_resolver: CombatResolver
    ):
        """
        Initialize deck gun action.
        
        Args:
            target_ship: Ship to target
            cost_lookup: Action cost lookup for AP costs
            los_calculator: LOS calculator for line of sight checks
            combat_resolver: Combat resolver for hit/damage rolls
        """
        super().__init__()
        self.target_ship = target_ship
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
        - Target in LOS
        - Range 1-3 hexes
        """
        u_boat = game_state.u_boat
        
        # Must be surfaced
        if u_boat.depth != Depth.SURFACED:
            return False, "Deck gun only available when surfaced"
        
        # Deck gun not damaged
        if u_boat.deck_gun_damaged:
            return False, "Deck gun is damaged"
        
        # Check range
        from ..hex_grid import HexGrid
        distance = HexGrid.hex_distance(u_boat.position, self.target_ship.position)
        
        if distance < 1 or distance > 3:
            return False, f"Target out of range (range: {distance}, need 1-3)"
        
        # Check LOS
        has_los, reason = self.los_calculator.has_line_of_sight(
            u_boat.position,
            self.target_ship.position
        )
        
        if not has_los:
            return False, f"No line of sight: {reason}"
        
        return True, ""
    
    def execute(self, game_state: Any) -> ActionResult:
        """Execute the deck gun attack."""
        u_boat = game_state.u_boat
        
        # Calculate range for hit roll
        from ..hex_grid import HexGrid
        distance = HexGrid.hex_distance(u_boat.position, self.target_ship.position)
        
        # Resolve attack
        hit, roll_result, description = self.combat_resolver.resolve_deck_gun_attack(
            distance
        )
        
        # On hit: Set detection level to 3
        if hit:
            # TODO: Set game_state.detection_level = 3 when GameState has it
            message = f"Deck gun HIT! {description} (DL set to 3)"
        else:
            message = f"Deck gun MISS. {description}"
        
        ap_cost = self.get_cost(u_boat)
        
        return ActionResult(
            success=True,
            message=message,
            ap_spent=ap_cost,
            state_changes={
                "target": self.target_ship,
                "hit": hit,
                "roll_result": roll_result,
                "range": distance
            }
        )
    
    def get_preview_data(self, game_state: Any) -> Dict[str, Any]:
        """Get preview data for rendering."""
        can_fire, reason = self.validate(game_state)
        
        # Calculate range
        from ..hex_grid import HexGrid
        distance = HexGrid.hex_distance(
            game_state.u_boat.position,
            self.target_ship.position
        )
        
        # Get hit chance
        if distance <= 2:
            hit_target = "7+ on 2d6"
        else:  # range 3
            hit_target = "8+ on 2d6"
        
        return {
            "type": "deck_gun",
            "target": self.target_ship,
            "range": distance,
            "hit_target": hit_target,
            "valid": can_fire,
            "reason": reason,
            "cost": self.get_cost(game_state.u_boat)
        }
    
    def get_description(self) -> str:
        """Get action description."""
        return f"Fire Deck Gun at {self.target_ship.ship_type}"
