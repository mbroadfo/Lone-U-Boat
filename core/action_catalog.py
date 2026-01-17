"""
Action Catalog - Generates all available actions for current game state.

This centralizes action availability logic in one place, eliminating duplication
between AI, tests, and UI systems.
"""

from typing import List, Optional, Any
from dataclasses import dataclass
from .models import TubeState

from .models import UBoat, Facing, Depth, Ship, HexCoord
from .actions.move_action import MoveAction
from .actions.rotate_action import RotateAction
from .actions.repair_action import RepairAction
from .actions.deck_gun_action import DeckGunAction
from .actions.load_torpedo_action import LoadTorpedoAction
from .actions.fire_torpedo_action import FireTorpedoAction
from .action_costs import ActionCostLookup
from .los import LOSCalculator
from .combat_resolver import CombatResolver
from .damage.ship_damage import ShipDamageResolver


@dataclass
class AvailableAction:
    """Represents an action that can be taken."""
    action: Any  # The action instance
    cost: int
    description: str
    action_type: str  # "move", "rotate", "depth", "repair", "deck_gun", "load_torpedo", "fire_torpedo"


class ActionCatalog:
    """
    Generates all available actions for the current game state.
    
    Actions self-validate, so this catalog simply generates all possible
    action variants and filters to valid ones.
    """
    
    def __init__(
        self,
        cost_lookup: ActionCostLookup,
        movement_validator: Any,
        depth_validator: Any,
        torpedo_validator: Any,
        repair_validator: Any,
        mission_rules: Any,
        land_hexes: set[HexCoord],
        shallow_hexes: set[HexCoord],
        hex_grid: Any,
        dice_roller: Any,
        mission_hexes: Optional[set[HexCoord]] = None
    ):
        """
        Initialize action catalog.
        
        Args:
            cost_lookup: Action cost lookup
            movement_validator: Movement validator
            depth_validator: Depth validator
            torpedo_validator: Torpedo validator
            repair_validator: Repair validator
            mission_rules: Mission rules
            land_hexes: Set of land hexes
            shallow_hexes: Set of shallow hexes
            mission_hexes: Set of valid mission hexes
        """
        self.cost_lookup = cost_lookup
        self.movement_validator = movement_validator
        self.depth_validator = depth_validator
        self.torpedo_validator = torpedo_validator
        self.repair_validator = repair_validator
        self.mission_rules = mission_rules
        self.land_hexes = land_hexes
        self.shallow_hexes = shallow_hexes
        self.hex_grid = hex_grid
        self.mission_hexes: set[HexCoord] = mission_hexes if mission_hexes else set()
        
        # Create combat components
        self.los_calculator = LOSCalculator(land_hexes)
        self.combat_resolver = CombatResolver(dice_roller, mission_rules)
        self.ship_damage = ShipDamageResolver(dice_roller)
    
    def get_available_actions(self, game_state: Any) -> List[AvailableAction]:
        """
        Get all available actions for current game state.
        
        Args:
            game_state: Current game state
            
        Returns:
            List of available actions with costs and descriptions
        """
        available: List[AvailableAction] = []
        u_boat = game_state.u_boat
        
        # Get remaining AP
        remaining_ap = game_state.action_queue.get_remaining_ap(game_state)
        
        # Generate all possible move actions (6 adjacent hexes)
        available.extend(self._get_move_actions(u_boat, game_state, remaining_ap))
        
        # Generate rotation actions (clockwise and counter-clockwise)
        available.extend(self._get_rotation_actions(u_boat, game_state, remaining_ap))
        
        # Generate depth change actions
        available.extend(self._get_depth_actions(u_boat, game_state, remaining_ap))
        
        # Generate repair actions
        available.extend(self._get_repair_actions(u_boat, game_state, remaining_ap))
        
        # Generate deck gun actions
        available.extend(self._get_deck_gun_actions(u_boat, game_state, remaining_ap))
        
        # Generate torpedo load actions
        available.extend(self._get_load_torpedo_actions(u_boat, game_state, remaining_ap))
        
        # Generate fire torpedo actions
        available.extend(self._get_fire_torpedo_actions(u_boat, game_state, remaining_ap))
        
        return available
    
    def _get_move_actions(self, u_boat: UBoat, game_state: Any, remaining_ap: int) -> List[AvailableAction]:
        """Generate all valid move actions (all 6 adjacent hexes)."""
        actions: List[AvailableAction] = []
        
        for facing in Facing:
            target_hex = facing.forward(u_boat.position)
            action = MoveAction(target_hex, self.cost_lookup, self.movement_validator)
            
            # Check if affordable and valid
            cost = action.get_cost(u_boat)
            if cost <= remaining_ap:
                valid, _ = action.validate(game_state)
                if valid:
                    actions.append(AvailableAction(
                        action=action,
                        cost=cost,
                        description=f"Move to {target_hex}",
                        action_type="move"
                    ))
        
        return actions
    
    def _get_rotation_actions(self, u_boat: UBoat, game_state: Any, remaining_ap: int) -> List[AvailableAction]:
        """Generate rotation actions (clockwise and counter-clockwise)."""
        actions: List[AvailableAction] = []
        
        for clockwise in [True, False]:
            action = RotateAction(clockwise, self.cost_lookup)
            cost = action.get_cost(u_boat)
            
            if cost <= remaining_ap:
                valid, _ = action.validate(game_state)
                if valid:
                    direction = "clockwise" if clockwise else "counter-clockwise"
                    actions.append(AvailableAction(
                        action=action,
                        cost=cost,
                        description=f"Rotate {direction}",
                        action_type="rotate"
                    ))
        
        return actions
    
    def _get_depth_actions(self, u_boat: UBoat, game_state: Any, remaining_ap: int) -> List[AvailableAction]:
        """Generate depth change actions."""
        actions: List[AvailableAction] = []
        
        # Check if depth has already changed this turn (either executed or queued)
        depth_already_changed = game_state.turn_manager.depth_changed_this_turn
        
        # Also check if a depth change action is already in the queue
        from .actions.depth_change_action import DepthChangeAction
        if not depth_already_changed:
            for queued_action in game_state.action_queue.actions:
                if isinstance(queued_action, DepthChangeAction):
                    depth_already_changed = True
                    break
        
        # If depth already changed or is queued to change, don't offer more depth changes
        if depth_already_changed:
            return actions
        
        # Try each possible depth
        for new_depth in Depth:
            if new_depth == u_boat.depth:
                continue  # Skip current depth
            
            action = DepthChangeAction(new_depth, self.cost_lookup, self.depth_validator)
            cost = action.get_cost(u_boat)
            
            if cost <= remaining_ap:
                valid, _ = action.validate(game_state)
                if valid:
                    actions.append(AvailableAction(
                        action=action,
                        cost=cost,
                        description=f"Change depth to {new_depth.name}",
                        action_type="depth"
                    ))
        
        return actions
    
    def _get_repair_actions(self, u_boat: UBoat, game_state: Any, remaining_ap: int) -> List[AvailableAction]:
        """Generate repair actions."""
        actions: List[AvailableAction] = []
        
        # Get all repairable systems
        repairable_systems = self.repair_validator.get_repairable_components(u_boat)
        
        for system in repairable_systems:
            action = RepairAction(system, self.cost_lookup, self.repair_validator)
            cost = action.get_cost(u_boat)
            
            if cost <= remaining_ap:
                valid, _ = action.validate(game_state)
                if valid:
                    actions.append(AvailableAction(
                        action=action,
                        cost=cost,
                        description=f"Repair {system}",
                        action_type="repair"
                    ))
        
        return actions
    
    def _get_deck_gun_actions(self, u_boat: UBoat, game_state: Any, remaining_ap: int) -> List[AvailableAction]:
        """Generate deck gun actions."""
        actions: List[AvailableAction] = []
        
        # Find all ships in range (1-3 hexes) with LOS
        valid_targets: List[tuple[Ship, int]] = []
        for ship in game_state.ships:
            distance = self.hex_grid.hex_distance(u_boat.position, ship.position)
            if 1 <= distance <= 3:
                has_los = self.los_calculator.has_line_of_sight(
                    u_boat.position,
                    ship.position
                )
                if has_los:
                    valid_targets.append((ship, distance))
        
        if valid_targets:
            # Sort by distance
            valid_targets.sort(key=lambda t: t[1])
            
            # Create single deck gun action with all valid targets
            action = DeckGunAction(
                targets=valid_targets,
                cost_lookup=self.cost_lookup,
                los_calculator=self.los_calculator,
                combat_resolver=self.combat_resolver,
                ship_damage=self.ship_damage
            )
            cost = action.get_cost(u_boat)
            
            if cost <= remaining_ap:
                valid, _ = action.validate(game_state)
                if valid:
                    ship_types = ", ".join([s[0].ship_type for s in valid_targets[:2]])
                    actions.append(AvailableAction(
                        action=action,
                        cost=cost,
                        description=f"Fire deck gun ({len(valid_targets)} targets: {ship_types}...)",
                        action_type="deck_gun"
                    ))
        
        return actions
    
    def _get_load_torpedo_actions(self, u_boat: UBoat, game_state: Any, remaining_ap: int) -> List[AvailableAction]:
        """Generate torpedo load actions."""
        actions: List[AvailableAction] = []
        
        # Try loading each tube individually
        for tube_index in range(5):
            tube_state = u_boat.torpedo_tubes[tube_index]
            if tube_state == TubeState.EMPTY:  # Only load empty tubes (not damaged or loaded)
                action = LoadTorpedoAction([tube_index], self.cost_lookup, self.torpedo_validator)
                cost = action.get_cost(u_boat)
                
                if cost <= remaining_ap:
                    valid, _ = action.validate(game_state)
                    if valid:
                        actions.append(AvailableAction(
                            action=action,
                            cost=cost,
                            description=f"Load torpedo tube {tube_index + 1}",
                            action_type="load_torpedo"
                        ))
        
        return actions
    
    def _get_fire_torpedo_actions(self, u_boat: UBoat, game_state: Any, remaining_ap: int) -> List[AvailableAction]:
        """
        Generate fire torpedo actions.
        
        Torpedoes fire in a direction (u_boat facing for front tubes, opposite for rear).
        No target selection needed - they hit whatever is in their path.
        AI can fire any loaded tube regardless of targets.
        """
        actions: List[AvailableAction] = []
        
        # Check if depth is valid for firing
        if u_boat.depth not in [Depth.SURFACED, Depth.PERISCOPE]:
            return actions
        
        # Get fireable tubes (separated by front/rear)
        fireable = self.torpedo_validator.get_fireable_tubes(u_boat)
        
        # Generate actions for front tubes (fire in u_boat facing direction)
        front_tubes = fireable['front']
        if front_tubes:
            # Convert to 0-based indices
            tube_indices = [t - 1 for t in front_tubes]
            
            # Generate actions for firing 1, 2, or 3 front tubes
            for num_tubes in range(1, min(len(front_tubes) + 1, 4)):  # 1-3 tubes
                # For simplicity in AI, just use first N tubes
                tubes_to_fire = tube_indices[:num_tubes]
                
                action = FireTorpedoAction(
                    tube_indices=tubes_to_fire,
                    fire_direction=u_boat.facing,
                    cost_lookup=self.cost_lookup,
                    validator=self.torpedo_validator,
                    los_calculator=self.los_calculator,
                    combat_resolver=self.combat_resolver
                )
                cost = action.get_cost(u_boat)
                
                if cost <= remaining_ap:
                    # Validate that action is legal before offering it
                    valid, _ = action.validate(game_state)
                    if valid:
                        tube_nums = [t + 1 for t in tubes_to_fire]
                        actions.append(AvailableAction(
                            action=action,
                            cost=cost,
                            description=f"Fire {num_tubes} torpedo(es) forward: tubes {tube_nums}",
                            action_type="fire_torpedo"
                        ))
        
        # Generate action for rear tube (fires opposite u_boat facing)
        rear_tubes = fireable['rear']
        if rear_tubes:
            # Rear tube is always tube 5 (index 4)
            # Opposite direction = rotate 180 degrees (3 steps clockwise)
            rear_direction = u_boat.facing.rotate_clockwise().rotate_clockwise().rotate_clockwise()
            
            action = FireTorpedoAction(
                tube_indices=[4],  # Tube 5 (0-based index 4)
                fire_direction=rear_direction,
                cost_lookup=self.cost_lookup,
                validator=self.torpedo_validator,
                los_calculator=self.los_calculator,
                combat_resolver=self.combat_resolver
            )
            cost = action.get_cost(u_boat)
            
            if cost <= remaining_ap:
                # Validate that action is legal before offering it
                valid, _ = action.validate(game_state)
                if valid:
                    actions.append(AvailableAction(
                        action=action,
                        cost=cost,
                        description=f"Fire rear torpedo: tube 5",
                        action_type="fire_torpedo"
                    ))
        
        return actions
