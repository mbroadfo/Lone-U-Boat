"""
Fire torpedo action - Launch torpedoes in facing direction.

Torpedoes travel in a straight line until hitting a ship or map edge.
Front tubes fire forward, rear tube fires backward.
"""

from typing import List, Tuple, Dict, Any
from .base_action import Action, ActionResult
from ..models import UBoat, Ship, Depth, Facing, HexCoord, TubeState
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
    
    def trace_torpedo_path(
        self,
        firing_position: HexCoord,
        fire_direction: Facing,
        ships: List[Ship],
        mission_hexes: set[HexCoord],
        land_hexes: set[HexCoord]
    ) -> List[Tuple[Ship, int, str]]:
        """
        Trace torpedo path and find all ships in line.
        
        Torpedoes stop when they hit land.
        
        Args:
            firing_position: The position where torpedoes are fired from
            fire_direction: The direction torpedoes are traveling
            ships: List of all ships in game
            mission_hexes: Set of valid mission hexes
            land_hexes: Set of land hexes (torpedo stops)
            
        Returns:
            List of (ship, distance, aspect) tuples, ordered by distance
            aspect is 'side' or 'front_rear'
        """
        targets: List[Tuple[Ship, int, str]] = []
        current_hex = firing_position
        
        # Travel up to max torpedo range (9 hexes per rules)
        for distance in range(1, 10):
            next_hex = fire_direction.forward(current_hex)
            
            # Check if hex is in mission area
            if next_hex not in mission_hexes:
                break  # Torpedo left map
            
            # Check if torpedo hit land
            if next_hex in land_hexes:
                break  # Torpedo stops at land
            
            # Check if any ship is at this hex
            for ship in ships:
                if ship.position == next_hex:
                    # Calculate aspect
                    aspect = self._calculate_aspect(ship, fire_direction)
                    targets.append((ship, distance, aspect))
                    # Don't break - continue to find all ships in line
            
            current_hex = next_hex
        
        # Ships are already ordered by distance (we traced in order)
        return targets
    
    def _calculate_aspect(self, ship: Ship, torpedo_direction: Facing) -> str:
        """
        Calculate aspect of torpedo approach.
        
        Side aspect: Torpedo approaches broadside (perpendicular to ship)
        Front/Rear aspect: Torpedo approaches bow or stern (parallel to ship)
        
        Args:
            ship: The target ship
            torpedo_direction: Direction torpedo is traveling
            
        Returns:
            'side' or 'front_rear'
        """
        # Calculate angle difference between torpedo direction and ship facing
        # Ship facing 0 (North) and torpedo from East (1) = side hit
        # Ship facing 0 (North) and torpedo from South (3) = front/rear hit
        
        angle_diff = abs((torpedo_direction.value - ship.facing.value) % 6)
        
        # Side aspect if torpedo approaches from ±60° or ±120° (perpendicular)
        # Hex directions: 0=N, 1=NE, 2=SE, 3=S, 4=SW, 5=NW
        # Perpendicular would be 1, 2, 4, 5 (60°, 120°, 240°, 300°)
        if angle_diff in [1, 2, 4, 5]:
            return 'side'
        else:
            # Front or rear (0° or 180°)
            return 'front_rear'
    
    def get_torpedo_hit_target(self, distance: int, aspect: str) -> int:
        """
        Get the target number needed on 1d6 to hit.
        
        Torpedo To-Hit Table:
        Range | Side Aspect | Front/Rear Aspect
        1-2   | 5+          | 6+
        3-4   | 6+          | 7+ (impossible)
        5-6   | 7+ (imp.)   | 8+ (impossible)
        7-8   | 8+ (imp.)   | 9+ (impossible)
        9     | 9+ (imp.)   | 10+ (impossible)
        
        Args:
            distance: Range to target in hexes (1-9)
            aspect: 'side' or 'front_rear'
            
        Returns:
            Target number (5-10)
        """
        if aspect == 'side':
            if distance <= 2:
                return 5
            elif distance <= 4:
                return 6
            elif distance <= 6:
                return 7
            elif distance <= 8:
                return 8
            else:  # distance == 9
                return 9
        else:  # front_rear
            if distance <= 2:
                return 6
            elif distance <= 4:
                return 7
            elif distance <= 6:
                return 8
            elif distance <= 8:
                return 9
            else:  # distance == 9
                return 10
    
    def execute(self, game_state: Any) -> ActionResult:
        """
        Execute the torpedo attack.
        
        NOTE: This method only prepares the torpedo state.
        Actual resolution happens interactively in the UI.
        """
        u_boat = game_state.u_boat
        
        # Determine actual fire direction at execution time based on tube and current facing
        if self.tube_indices[0] <= 4:
            # Front tubes fire forward using current facing
            fire_direction = u_boat.facing
        else:
            # Rear tube fires backward (opposite of current facing)
            fire_direction = Facing((u_boat.facing.value + 3) % 6)
        
        # Trace path and find all ships in line (use current u_boat position and facing)
        targets = self.trace_torpedo_path(
            u_boat.position,
            fire_direction,
            game_state.ships, 
            game_state.mission_hexes,
            game_state.land_hexes
        )
        
        # Unload fired tubes immediately (convert 1-based to 0-based)
        for tube_num in self.tube_indices:
            u_boat.torpedo_tubes[tube_num - 1] = TubeState.EMPTY
        
        ap_cost = self.get_cost(u_boat)
        
        # If no targets found, return immediately
        if not targets:
            return ActionResult(
                success=True,
                message=f"Fired {len(self.tube_indices)} torpedo(es) - No targets in path",
                ap_spent=ap_cost,
                state_changes={
                    "tubes_fired": self.tube_indices,
                    "torpedo_count": len(self.tube_indices),
                    "targets": [],
                    "action_name": "Fire Torpedo",
                    "needs_interactive_resolution": False
                }
            )
        
        # Return state for interactive resolution
        # UI will handle rolling for each torpedo against each ship
        return ActionResult(
            success=True,
            message=f"Firing {len(self.tube_indices)} torpedo(es)...",
            ap_spent=ap_cost,
            state_changes={
                "tubes_fired": self.tube_indices,
                "torpedo_count": len(self.tube_indices),
                "targets": targets,  # List of (ship, distance, aspect)
                "action_name": "Fire Torpedo",
                "needs_interactive_resolution": True
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
        # Determine direction based on tube indices: tubes 0-3 are front, tube 4 is rear
        direction = "Rear" if 4 in self.tube_indices else "Forward"
        tube_nums = [t + 1 for t in self.tube_indices]  # Convert to 1-based
        return f"Fire {len(self.tube_indices)} torpedo(es) {direction} (tubes {tube_nums})"
