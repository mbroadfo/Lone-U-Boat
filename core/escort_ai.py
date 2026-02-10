"""
Escort Phase AI - handles escort movement and combat actions.
"""

from typing import List, Tuple, Set, Optional, Any, Dict, TYPE_CHECKING
from enum import Enum
from .models import Ship, UBoat, HexCoord, Facing, Depth
from .hex_grid import HexGrid
from .dice import DiceRoller
from .damage.uboat_damage import UBoatDamageResolver

if TYPE_CHECKING:
    from .turn_manager import TurnManager


class EscortAction(Enum):
    """Actions an escort can take during its activation."""
    MOVE = "move"
    TURN = "turn"
    FIRE = "fire"
    DEPTH_CHARGE = "depth_charge"


class EscortAI:
    """AI controller for escort ship movement and attacks during Escort Phase."""
    
    def __init__(self, mission_rules: Any, dice_roller: DiceRoller, anchor_hex: HexCoord):
        """
        Initialize escort AI.
        
        Args:
            mission_rules: Mission rules loaded from JSON (includes escort_ai_baseline)
            dice_roller: Dice roller for action rolls
            anchor_hex: Anchor hex for DL 0-1 turning (from mission config)
        """
        self.mission_rules: Any = mission_rules
        self.dice = dice_roller
        self.anchor_hex = anchor_hex
        
        # Initialize damage resolver for combat
        self.damage_resolver = UBoatDamageResolver(dice_roller, mission_rules)
        
        # Load escort action rules from mission_rules
        # Base dice counts (default values, will be loaded from JSON)
        self.destroyer_base_dice: int = 3
        self.corvette_base_dice: int = 2
        
        # Action table mapping (die result -> action)
        # Default table based on RULES.md Phase 4
        self.action_table: Dict[int, List[EscortAction]] = {
            1: [EscortAction.FIRE],
            2: [EscortAction.MOVE, EscortAction.TURN],
            3: [EscortAction.MOVE],
            4: [EscortAction.MOVE, EscortAction.TURN],
            5: [EscortAction.TURN],
            6: [EscortAction.MOVE, EscortAction.TURN],
        }
        
        # Load rules from JSON if available
        self._load_escort_rules()
    
    def _load_escort_rules(self) -> None:
        """Load escort rules from mission_rules JSON."""
        try:
            # Load dice counts
            activation_rules = self.mission_rules.get_section_by_id("escort_activation_order")
            if activation_rules and "dice_calculation" in activation_rules:
                dice_calc = activation_rules["dice_calculation"]
                
                if "destroyer" in dice_calc:
                    self.destroyer_base_dice = dice_calc["destroyer"].get("base", 3)
                
                if "corvette" in dice_calc:
                    self.corvette_base_dice = dice_calc["corvette"].get("base", 2)
            
            # Load action table (basic mapping - conditions handled in code)
            action_table_data = self.mission_rules.get_section_by_id("destroyer_actions")
            if action_table_data and "results" in action_table_data:
                for result in action_table_data["results"]:
                    roll = result.get("roll")
                    if roll is None:
                        continue
                    
                    # Extract primary actions from sequence
                    actions: List[EscortAction] = []
                    sequence = result.get("sequence", [])
                    for step in sequence:
                        action_str = step.get("action", "")
                        # Map string to EscortAction enum
                        if action_str == "MOVE":
                            actions.append(EscortAction.MOVE)
                        elif action_str == "TURN":
                            if step.get("always") or step.get("condition"):
                                if EscortAction.TURN not in actions:
                                    actions.append(EscortAction.TURN)
                        elif action_str == "FIRE":
                            if EscortAction.FIRE not in actions:
                                actions.append(EscortAction.FIRE)
                        elif action_str == "DEPTH_CHARGE":
                            # Depth charge is secondary action, add to end
                            if EscortAction.DEPTH_CHARGE not in actions:
                                actions.append(EscortAction.DEPTH_CHARGE)
                    
                    if actions:
                        self.action_table[roll] = actions
        
        except Exception:
            # Keep defaults if parsing fails
            pass
    
    def calculate_dice_count(self, escort: Ship, detection_level: int) -> int:
        """
        Calculate number of action dice for an escort.
        
        Args:
            escort: The escort ship
            detection_level: Current detection level (0-3)
            
        Returns:
            Number of dice to roll
        """
        # Base dice by ship type
        if escort.ship_type == 'destroyer':
            base_dice = self.destroyer_base_dice
        elif escort.ship_type == 'corvette':
            base_dice = self.corvette_base_dice
        else:
            return 0  # Merchants don't get action dice
        
        # If damaged, only roll base dice (no DL bonus)
        if escort.damaged:
            return base_dice
        
        # Undamaged: base + detection level
        return base_dice + detection_level
    
    def roll_escort_actions(self, escort: Ship, detection_level: int) -> List[int]:
        """
        Roll action dice for an escort and return sorted results.
        
        Args:
            escort: The escort ship
            detection_level: Current detection level (0-3)
            
        Returns:
            List of die results, sorted lowest to highest
        """
        dice_count = self.calculate_dice_count(escort, detection_level)
        
        if dice_count == 0:
            return []
        
        # Roll dice and sort lowest to highest
        rolls = [self.dice.roll_1d6() for _ in range(dice_count)]
        return sorted(rolls)
    
    def get_turn_target(self, escort: Ship, u_boat: UBoat, detection_level: int) -> HexCoord:
        """
        Determine which hex the escort should turn toward.
        
        Args:
            escort: The escort ship
            u_boat: The U-boat
            detection_level: Current detection level (0-3)
            
        Returns:
            Target hex to turn toward (either anchor or U-boat position)
        """
        # DL 0-1: Turn toward anchor hex
        # DL 2-3: Turn toward U-boat
        if detection_level <= 1:
            return self.anchor_hex
        else:
            return u_boat.position
    
    def calculate_turn_direction(
        self,
        escort: Ship,
        target: HexCoord,
        land_hexes: Set[HexCoord],
        ships: List[Ship],
        mission_hexes: Optional[Set[HexCoord]] = None
    ) -> Optional[Facing]:
        """
        Calculate which direction to turn (left or right).
        
        Args:
            escort: The escort ship
            target: Target hex (anchor or U-boat)
            land_hexes: Set of land hexes
            ships: List of all ships (for blocking check)
            mission_hexes: Set of valid mission hexes
            
        Returns:
            New facing direction or None if no turn needed
        """
        # Check if escort is on same hex as target
        if escort.position == target:
            # Only turn if blocked
            if self._is_hex_blocked(escort.facing.forward(escort.position), land_hexes, ships, mission_hexes):
                return self._random_turn(escort.facing)
            return None
        
        # Calculate angle to target
        angle = self._calculate_angle_to_target(escort.position, escort.facing, target)
        
        # If facing target (angle = 0), only turn if blocked
        if angle == 0:
            if self._is_hex_blocked(escort.facing.forward(escort.position), land_hexes, ships, mission_hexes):
                return self._random_turn(escort.facing)
            return None
        
        # If facing away (angle = 180), turn randomly
        if angle == 180:
            return self._random_turn(escort.facing)
        
        # Turn in direction with smallest angle to target
        if angle < 0:
            return escort.facing.rotate_counterclockwise()
        else:
            return escort.facing.rotate_clockwise()
    
    def _calculate_angle_to_target(self, position: HexCoord, facing: Facing, target: HexCoord) -> int:
        """
        Calculate angle from current facing to target hex.
        
        Returns:
            Angle in hex edges: 0 (facing), 60, 120, 180 (away), -60, -120
            Positive = clockwise, Negative = counterclockwise
        """
        # Get direction vector to target
        dq = target.q - position.q
        dr = target.r - position.r
        
        # Map to facing direction
        target_facing = self._vector_to_facing(dq, dr)
        
        if target_facing is None:
            # Target is at same position or non-adjacent - approximate
            return 0
        
        # Calculate angle difference (in hex edges = 60 degrees each)
        diff = (target_facing.value - facing.value) % 6
        
        # Convert to signed angle (-180 to +180)
        if diff <= 3:
            return diff * 60
        else:
            return (diff - 6) * 60
    
    def _vector_to_facing(self, dq: int, dr: int) -> Optional[Facing]:
        """Convert direction vector to facing direction."""
        # Normalize to unit vector (approximate)
        if dq == 0 and dr == 0:
            return None
        
        # Map dominant direction to facing
        # This is approximate for non-adjacent hexes
        if abs(dq) > abs(dr):
            if dq > 0:
                return Facing.SOUTHEAST if dr >= 0 else Facing.NORTHEAST
            else:
                return Facing.NORTHWEST if dr <= 0 else Facing.SOUTHWEST
        else:
            if dr > 0:
                return Facing.SOUTH if dq >= 0 else Facing.SOUTHWEST
            else:
                return Facing.NORTH if dq <= 0 else Facing.NORTHEAST
    
    def _random_turn(self, facing: Facing) -> Facing:
        """Turn randomly (50/50 left or right)."""
        if self.dice.roll_1d6() <= 3:
            return facing.rotate_counterclockwise()
        else:
            return facing.rotate_clockwise()
    
    def _is_hex_blocked(
        self,
        hex_coord: HexCoord,
        land_hexes: Set[HexCoord],
        ships: List[Ship],
        mission_hexes: Optional[Any] = None  # Can be Set[HexCoord] or HexGrid
    ) -> bool:
        """
        Check if a hex is blocked (land, ship, or off-map).
        
        Args:
            hex_coord: Hex to check
            land_hexes: Set of land hexes
            ships: List of all ships
            mission_hexes: Set of valid mission hexes or HexGrid (for off-map check)
            
        Returns:
            True if hex is blocked
        """
        # Check if land hex
        if hex_coord in land_hexes:
            return True
        
        # Check if another ship is in hex
        for ship in ships:
            if ship.position == hex_coord:
                return True
        
        # Check if off-map (using HexGrid's is_valid_hex if available)
        if mission_hexes is not None:
            # Handle both HexGrid and Set[HexCoord]
            if hasattr(mission_hexes, 'is_valid_hex'):
                # It's a HexGrid
                if not mission_hexes.is_valid_hex(hex_coord):
                    return True
            else:
                # It's a set
                if hex_coord not in mission_hexes:
                    return True
        
        return False
    
    def get_next_hex_toward_target(
        self,
        escort: Ship,
        target: HexCoord,
        land_hexes: Set[HexCoord],
        ships: List[Ship],
        mission_hexes: Optional[Set[HexCoord]] = None
    ) -> Optional[HexCoord]:
        """
        Get the next hex to move toward target.
        
        Args:
            escort: The escort ship
            target: Target position (U-boat)
            land_hexes: Set of land hexes
            ships: List of all ships
            mission_hexes: Set of valid mission hexes
            
        Returns:
            Next hex to move to, or None if can't move
        """
        # Try moving in facing direction first
        next_hex = escort.facing.forward(escort.position)
        
        # Check if blocked
        if self._is_hex_blocked(next_hex, land_hexes, ships, mission_hexes):
            return None
        
        return next_hex
    
    def check_forced_dive(
        self,
        escort: Ship,
        u_boat: UBoat,
        new_position: HexCoord,
        shallow_hexes: Set[HexCoord]
    ) -> Tuple[bool, str, bool]:
        """
        Check if escort movement forces U-boat to dive.
        
        Args:
            escort: The escort ship
            u_boat: The U-boat
            new_position: Escort's new position
            shallow_hexes: Set of shallow water hexes
            
        Returns:
            Tuple of (forced_dive_occurred, message, u_boat_destroyed)
        """
        # Check if escort moved into same hex as U-boat
        if new_position != u_boat.position:
            return False, "", False
        
        # Check U-boat depth
        if u_boat.depth in [Depth.SURFACED, Depth.PERISCOPE]:
            # Check if in shallow water
            # Forced dive sets depth to MEDIUM
            # In shallow water, max depth is PERISCOPE, so MEDIUM is not allowed
            # U-boat is destroyed if forced to dive to MEDIUM in shallow water
            if new_position in shallow_hexes:
                # U-boat is destroyed - cannot dive to MEDIUM in shallow water (max depth PERISCOPE)
                return True, "Escort forces U-boat to dive in shallow water - U-BOAT DESTROYED!", True
            
            # Check if hull damage prevents diving to MEDIUM
            # Hull damage limits: 0=DEEP, 1=MEDIUM, 2=PERISCOPE, 3+=SURFACED
            from .depth_validator import DepthValidator
            max_depth_for_hull = DepthValidator.max_depth_for_hull_damage(u_boat.hull_damage)
            if max_depth_for_hull.value < Depth.MEDIUM.value:
                # U-boat is destroyed - hull damage prevents diving to MEDIUM
                return True, f"Escort forces U-boat to dive to MEDIUM, but hull damage ({u_boat.hull_damage}) only allows {max_depth_for_hull.name} - U-BOAT DESTROYED!", True
            
            return True, f"Escort forces U-boat to dive from {u_boat.depth.name} to MEDIUM (+1 DL, -2 AP next turn)", False
        
        return False, "", False
    
    def check_forced_ascent(
        self,
        u_boat: UBoat,
        ships: List[Ship]
    ) -> Tuple[bool, str, bool]:
        """
        Check if U-boat must ascend due to hull damage exceeding max depth.
        If ship is in same hex, U-boat is destroyed (cannot ascend).
        
        Args:
            u_boat: The U-boat
            ships: List of all ships
            
        Returns:
            Tuple of (forced_ascent_occurred, message, u_boat_destroyed)
        """
        from .depth_validator import DepthValidator
        
        # Check if current depth exceeds max allowed for hull damage
        max_depth = DepthValidator.max_depth_for_hull_damage(u_boat.hull_damage)
        if u_boat.depth.value > max_depth.value:
            # Need to ascend
            # Check if ship in same hex blocks ascent
            for ship in ships:
                if ship.position == u_boat.position:
                    # Ship blocks forced ascent - U-boat destroyed
                    return True, f"Hull damage {u_boat.hull_damage} forces ascent to {max_depth.name}, but ship in hex blocks ascent - U-BOAT DESTROYED!", True
            
            # No ship blocking, force ascent
            old_depth = u_boat.depth
            u_boat.depth = max_depth
            return True, f"Hull damage {u_boat.hull_damage} forces ascent from {old_depth.name} to {max_depth.name}", False
        
        return False, "", False
    
    def can_use_fire(
        self,
        escort: Ship,
        u_boat: UBoat,
        detection_level: int,
        land_hexes: Set[HexCoord],
        hex_grid: HexGrid
    ) -> bool:
        """
        Check if escort can use FIRE action.
        
        Args:
            escort: The escort ship
            u_boat: The U-boat
            detection_level: Current detection level
            land_hexes: Set of land hexes
            hex_grid: Hex grid
            
        Returns:
            True if FIRE action is valid
        """
        # Must be at DL 1-3
        if detection_level < 1:
            return False
        
        # U-boat must be surfaced
        if u_boat.depth != Depth.SURFACED:
            return False
        
        # Must be in range 1-3
        distance = hex_grid.hex_distance(escort.position, u_boat.position)
        if distance < 1 or distance > 3:
            return False
        
        # Must have line of sight
        if not self._check_line_of_sight(escort.position, u_boat.position, land_hexes, hex_grid):
            return False
        
        return True
    
    def can_use_depth_charge(
        self,
        escort: Ship,
        u_boat: UBoat,
        detection_level: int,
        hex_grid: HexGrid
    ) -> bool:
        """
        Check if escort can use DEPTH_CHARGE action.
        
        Args:
            escort: The escort ship
            u_boat: The U-boat
            detection_level: Current detection level
            hex_grid: Hex grid
            
        Returns:
            True if DEPTH_CHARGE action is valid
        """
        # Must be at DL 1-3
        if detection_level < 1:
            return False
        
        # U-boat must NOT be surfaced
        if u_boat.depth == Depth.SURFACED:
            return False
        
        # Must be at range 0-1
        distance = hex_grid.hex_distance(escort.position, u_boat.position)
        if distance > 1:
            return False
        
        return True
    
    def _check_line_of_sight(
        self,
        from_hex: HexCoord,
        to_hex: HexCoord,
        land_hexes: Set[HexCoord],
        hex_grid: HexGrid
    ) -> bool:
        """
        Check if there is line of sight between two hexes.
        
        Args:
            from_hex: Starting hex
            to_hex: Target hex
            land_hexes: Set of land hexes that block LOS
            hex_grid: Hex grid
            
        Returns:
            True if line of sight exists
        """
        # Same hex always has LOS
        if from_hex == to_hex:
            return True
        
        # Use simple hex line algorithm
        distance = hex_grid.hex_distance(from_hex, to_hex)
        
        for i in range(1, distance):
            # Linear interpolation in axial coordinates
            t = i / distance
            lerp_q = from_hex.q + (to_hex.q - from_hex.q) * t
            lerp_r = from_hex.r + (to_hex.r - from_hex.r) * t
            
            # Round to nearest hex
            hex_coord = hex_grid.round_hex(lerp_q, lerp_r)
            
            # Check if this hex blocks LOS
            if hex_coord in land_hexes:
                return False
        
        return True
    
    def execute_escort_phase(
        self,
        ships: List[Ship],
        u_boat: UBoat,
        detection_level: int,
        land_hexes: Set[HexCoord],
        hex_grid: HexGrid,
        mission_hexes: Optional[Set[HexCoord]] = None,
        shallow_hexes: Optional[Set[HexCoord]] = None,
        turn_manager: Optional['TurnManager'] = None
    ) -> Tuple[int, List[str]]:
        """
        Execute the escort phase for all escort ships.

        Args:
            ships: List of all ships
            u_boat: The U-boat
            detection_level: Current detection level (0-3)
            land_hexes: Set of land hexes
            hex_grid: Hex grid
            mission_hexes: Set of valid mission hexes (for off-map check)
            shallow_hexes: Set of shallow water hexes (for forced dive destruction check)
            turn_manager: TurnManager instance for applying forced dive penalty

        Returns:
            Tuple of (new_detection_level, messages)
        """
        if shallow_hexes is None:
            shallow_hexes = set()
        
        messages: List[str] = []
        current_dl = detection_level
        
        # Filter to corvettes and destroyers only
        escorts = [ship for ship in ships if ship.ship_type in ['corvette', 'destroyer']]
        
        if not escorts:
            messages.append("No escorts on map")
            return current_dl, messages
        
        # Sort by distance to U-boat (closest first)
        escorts.sort(key=lambda s: hex_grid.hex_distance(s.position, u_boat.position))
        
        # Activate each escort
        for escort in escorts:
            messages.append(f"\n{escort.ship_type.upper()} at [{escort.position.q},{escort.position.r}] activates:")
            
            # Calculate and show dice count
            dice_count = self.calculate_dice_count(escort, current_dl)
            base_dice = self.corvette_base_dice if escort.ship_type == 'corvette' else self.destroyer_base_dice
            dice_calc_msg = f"  Dice count: {base_dice} (base)"
            if not escort.damaged and current_dl >= 1:
                dice_calc_msg += f" +{current_dl} (DL={current_dl})"
            elif escort.damaged and current_dl >= 1:
                dice_calc_msg += f" (damaged: no DL bonus)"
            dice_calc_msg += f" = {dice_count} dice"
            messages.append(dice_calc_msg)
            
            # Roll and execute dice one at a time, stopping if U-boat is destroyed
            for die_idx in range(1, dice_count + 1):
                # Roll this die
                die_result = self.dice.roll_1d6()
                messages.append(f"  Die {die_idx} (rolled {die_result}):")
                
                # UNIFIED action table for both corvettes and destroyers (escort_ai_baseline.json lines 77-200)
                # The only difference between ship types is dice count, not actions
                
                # Execute actions based on die result using unified table
                if die_result == 1:
                    # Die 1: FIRE (if surfaced + DL 1-3) or DEPTH CHARGE (if submerged + DL 1-3)
                    distance = hex_grid.hex_distance(escort.position, u_boat.position)
                    messages.append(f"    [Check: Range={distance}, U-boat depth={u_boat.depth.name}, DL={current_dl}]")
                    
                    if current_dl >= 1 and current_dl <= 3:
                        # Try FIRE first (if U-boat surfaced)
                        if self.can_use_fire(escort, u_boat, current_dl, land_hexes, hex_grid):
                            has_los = self._check_line_of_sight(escort.position, u_boat.position, land_hexes, hex_grid)
                            messages.append(f"    FIRE: Critical Hit on U-boat! (Range {distance}, LOS: {'Yes' if has_los else 'No'}, DL -> 3)")
                            current_dl = 3
                            
                            damage_result = self.damage_resolver.apply_escort_attack_damage(
                                u_boat, attack_type="gunfire", ship_type=escort.ship_type, ships=ships
                            )
                            for line in damage_result.description.split('\n'):
                                messages.append(f"      {line}")
                            
                            is_destroyed, _ = self.damage_resolver.check_destruction(u_boat)
                            if is_destroyed:
                                return current_dl, messages
                            
                            # Check if hull damage forces ascent
                            forced_ascent, ascent_msg, destroyed_by_ascent = self.check_forced_ascent(u_boat, ships)
                            if forced_ascent:
                                messages.append(f"      {ascent_msg}")
                                if destroyed_by_ascent:
                                    u_boat.hull_damage = 4
                                    return current_dl, messages
                        
                        # Otherwise try DEPTH CHARGE (if U-boat submerged)
                        elif self.can_use_depth_charge(escort, u_boat, current_dl, hex_grid):
                            messages.append(f"    DEPTH CHARGE: Attack U-boat (Range {distance})")
                            
                            damage_result = self.damage_resolver.apply_escort_attack_damage(
                                u_boat, attack_type="depth_charge", ship_type=escort.ship_type, ships=ships
                            )
                            for line in damage_result.description.split('\n'):
                                messages.append(f"      {line}")
                            
                            is_destroyed, _ = self.damage_resolver.check_destruction(u_boat)
                            if is_destroyed:
                                return current_dl, messages
                            
                            # Check if hull damage forces ascent
                            forced_ascent, ascent_msg, destroyed_by_ascent = self.check_forced_ascent(u_boat, ships)
                            if forced_ascent:
                                messages.append(f"      {ascent_msg}")
                                if destroyed_by_ascent:
                                    u_boat.hull_damage = 4
                                    return current_dl, messages
                        else:
                            # Explain why no attack is possible
                            if u_boat.depth == Depth.SURFACED:
                                has_los = self._check_line_of_sight(escort.position, u_boat.position, land_hexes, hex_grid)
                                messages.append(f"    FIRE not possible: Range={distance} (need ≤6), LOS={'Yes' if has_los else 'No'} (need Yes)")
                            else:
                                messages.append(f"    DEPTH CHARGE not possible: Range={distance} (need ≤1), Depth={u_boat.depth.name} (need submerged)")
                    else:
                        messages.append(f"    No action (DL must be 1-3 for FIRE/DEPTH CHARGE)")
                
                elif die_result == 2:
                    # Die 2: MOVE → (if blocked) TURN → (if DL 1-3) DEPTH CHARGE
                    next_hex = self.get_next_hex_toward_target(
                        escort, u_boat.position, land_hexes, ships, mission_hexes
                    )
                    
                    if next_hex:
                        old_pos = escort.position
                        escort.position = next_hex
                        distance = hex_grid.hex_distance(escort.position, u_boat.position)
                        messages.append(f"    MOVE: [{old_pos.q},{old_pos.r}] -> [{next_hex.q},{next_hex.r}] (Range: {distance})")
                        
                        forced, msg, destroyed = self.check_forced_dive(escort, u_boat, next_hex, shallow_hexes)
                        if forced:
                            messages.append(f"    {msg}")
                            if destroyed:
                                u_boat.hull_damage = 4
                                return current_dl, messages
                            u_boat.depth = Depth.MEDIUM
                            current_dl = min(3, current_dl + 1)
                    else:
                        messages.append(f"    MOVE: Blocked (facing hex obstructed)")
                        # If blocked, turn
                        target = self.get_turn_target(escort, u_boat, current_dl)
                        new_facing = self.calculate_turn_direction(
                            escort, target, land_hexes, ships, mission_hexes
                        )
                        if new_facing and new_facing != escort.facing:
                            old_facing = escort.facing
                            escort.facing = new_facing
                            messages.append(f"    TURN: {old_facing.name} -> {new_facing.name} (due to blocked movement)")
                    
                    # Then try depth charge if DL=1-3
                    distance = hex_grid.hex_distance(escort.position, u_boat.position)
                    if current_dl >= 1 and current_dl <= 3:
                        if self.can_use_depth_charge(escort, u_boat, current_dl, hex_grid):
                            messages.append(f"    DEPTH CHARGE: Attack U-boat (Range {distance}, Depth {u_boat.depth.name})")
                            
                            damage_result = self.damage_resolver.apply_escort_attack_damage(
                                u_boat, attack_type="depth_charge", ship_type=escort.ship_type, ships=ships
                            )
                            for line in damage_result.description.split('\n'):
                                messages.append(f"      {line}")
                            
                            is_destroyed, _ = self.damage_resolver.check_destruction(u_boat)
                            if is_destroyed:
                                return current_dl, messages
                            
                            # Check if hull damage forces ascent
                            forced_ascent, ascent_msg, destroyed_by_ascent = self.check_forced_ascent(u_boat, ships)
                            if forced_ascent:
                                messages.append(f"      {ascent_msg}")
                                if destroyed_by_ascent:
                                    u_boat.hull_damage = 4
                                    return current_dl, messages
                        else:
                            # Only log if reasonably close to possible
                            if distance <= 3 or u_boat.depth != Depth.SURFACED:
                                messages.append(f"      DEPTH CHARGE not possible: Range={distance} (need ≤1), Depth={u_boat.depth.name}")
                
                elif die_result == 3:
                    # Die 3: MOVE → TURN → (if DL 1-3) DEPTH CHARGE
                    next_hex = self.get_next_hex_toward_target(
                        escort, u_boat.position, land_hexes, ships, mission_hexes
                    )
                    
                    if next_hex:
                        old_pos = escort.position
                        escort.position = next_hex
                        distance = hex_grid.hex_distance(escort.position, u_boat.position)
                        messages.append(f"    MOVE: [{old_pos.q},{old_pos.r}] -> [{next_hex.q},{next_hex.r}] (Range: {distance})")
                        
                        forced, msg, destroyed = self.check_forced_dive(escort, u_boat, next_hex, shallow_hexes)
                        if forced:
                            messages.append(f"    {msg}")
                            if destroyed:
                                u_boat.hull_damage = 4
                                return current_dl, messages
                            u_boat.depth = Depth.MEDIUM
                            current_dl = min(3, current_dl + 1)
                            # Apply forced dive AP penalty
                            if turn_manager:
                                turn_manager.set_forced_dive_penalty()
                    else:
                        messages.append(f"    MOVE: Blocked (facing hex obstructed)")
                    
                    # Always turn
                    target = self.get_turn_target(escort, u_boat, current_dl)
                    target_name = "anchor" if current_dl <= 1 else "U-boat"
                    new_facing = self.calculate_turn_direction(
                        escort, target, land_hexes, ships, mission_hexes
                    )
                    if new_facing and new_facing != escort.facing:
                        old_facing = escort.facing
                        escort.facing = new_facing
                        messages.append(f"    TURN: {old_facing.name} -> {new_facing.name} (Die 3, turning toward {target_name})")
                    
                    # Then try depth charge if DL=1-3
                    distance = hex_grid.hex_distance(escort.position, u_boat.position)
                    if current_dl >= 1 and current_dl <= 3:
                        if self.can_use_depth_charge(escort, u_boat, current_dl, hex_grid):
                            messages.append(f"    DEPTH CHARGE: Attack U-boat (Range {distance}, Depth {u_boat.depth.name})")
                            
                            damage_result = self.damage_resolver.apply_escort_attack_damage(
                                u_boat, attack_type="depth_charge", ship_type=escort.ship_type, ships=ships
                            )
                            for line in damage_result.description.split('\n'):
                                messages.append(f"      {line}")
                            
                            is_destroyed, _ = self.damage_resolver.check_destruction(u_boat)
                            if is_destroyed:
                                return current_dl, messages
                            
                            # Check if hull damage forces ascent
                            forced_ascent, ascent_msg, destroyed_by_ascent = self.check_forced_ascent(u_boat, ships)
                            if forced_ascent:
                                messages.append(f"      {ascent_msg}")
                                if destroyed_by_ascent:
                                    u_boat.hull_damage = 4
                                    return current_dl, messages
                        else:
                            # Only log if reasonably close to possible
                            if distance <= 3 or u_boat.depth != Depth.SURFACED:
                                messages.append(f"      DEPTH CHARGE not possible: Range={distance} (need ≤1), Depth={u_boat.depth.name}")
                
                elif die_result == 4:
                    # Die 4: MOVE → (if blocked) TURN → (if DL 1-3) DEPTH CHARGE
                    next_hex = self.get_next_hex_toward_target(
                        escort, u_boat.position, land_hexes, ships, mission_hexes
                    )
                    
                    if next_hex:
                        old_pos = escort.position
                        escort.position = next_hex
                        distance = hex_grid.hex_distance(escort.position, u_boat.position)
                        messages.append(f"    MOVE: [{old_pos.q},{old_pos.r}] -> [{next_hex.q},{next_hex.r}] (Range: {distance})")
                        
                        forced, msg, destroyed = self.check_forced_dive(escort, u_boat, next_hex, shallow_hexes)
                        if forced:
                            messages.append(f"    {msg}")
                            if destroyed:
                                u_boat.hull_damage = 4
                                return current_dl, messages
                            u_boat.depth = Depth.MEDIUM
                            current_dl = min(3, current_dl + 1)
                            # Apply forced dive AP penalty
                            if turn_manager:
                                turn_manager.set_forced_dive_penalty()
                    else:
                        messages.append(f"    MOVE: Blocked (facing hex obstructed)")
                        # If blocked, turn
                        target = self.get_turn_target(escort, u_boat, current_dl)
                        target_name = "anchor" if current_dl <= 1 else "U-boat"
                        new_facing = self.calculate_turn_direction(
                            escort, target, land_hexes, ships, mission_hexes
                        )
                        if new_facing and new_facing != escort.facing:
                            old_facing = escort.facing
                            escort.facing = new_facing
                            messages.append(f"    TURN: {old_facing.name} -> {new_facing.name} (blocked, turning toward {target_name})")
                    
                    # Then try depth charge if DL=1-3
                    distance = hex_grid.hex_distance(escort.position, u_boat.position)
                    if current_dl >= 1 and current_dl <= 3:
                        if self.can_use_depth_charge(escort, u_boat, current_dl, hex_grid):
                            messages.append(f"    DEPTH CHARGE: Attack U-boat (Range {distance}, Depth {u_boat.depth.name})")
                            
                            damage_result = self.damage_resolver.apply_escort_attack_damage(
                                u_boat, attack_type="depth_charge", ship_type=escort.ship_type, ships=ships
                            )
                            for line in damage_result.description.split('\n'):
                                messages.append(f"      {line}")
                            
                            is_destroyed, _ = self.damage_resolver.check_destruction(u_boat)
                            if is_destroyed:
                                return current_dl, messages
                            
                            # Check if hull damage forces ascent
                            forced_ascent, ascent_msg, destroyed_by_ascent = self.check_forced_ascent(u_boat, ships)
                            if forced_ascent:
                                messages.append(f"      {ascent_msg}")
                                if destroyed_by_ascent:
                                    u_boat.hull_damage = 4
                                    return current_dl, messages
                        else:
                            # Only log if reasonably close to possible
                            if distance <= 3 or u_boat.depth != Depth.SURFACED:
                                messages.append(f"      DEPTH CHARGE not possible: Range={distance} (need ≤1), Depth={u_boat.depth.name}")
                
                elif die_result == 5:
                    # Die 5: MOVE → (if DL 1-3) DEPTH CHARGE
                    next_hex = self.get_next_hex_toward_target(
                        escort, u_boat.position, land_hexes, ships, mission_hexes
                    )
                    
                    if next_hex:
                        old_pos = escort.position
                        escort.position = next_hex
                        distance = hex_grid.hex_distance(escort.position, u_boat.position)
                        messages.append(f"    MOVE: [{old_pos.q},{old_pos.r}] -> [{next_hex.q},{next_hex.r}] (Range: {distance})")
                        
                        forced, msg, destroyed = self.check_forced_dive(escort, u_boat, next_hex, shallow_hexes)
                        if forced:
                            messages.append(f"    {msg}")
                            if destroyed:
                                u_boat.hull_damage = 4
                                return current_dl, messages
                            u_boat.depth = Depth.MEDIUM
                            current_dl = min(3, current_dl + 1)
                            # Apply forced dive AP penalty
                            if turn_manager:
                                turn_manager.set_forced_dive_penalty()
                    else:
                        distance = hex_grid.hex_distance(escort.position, u_boat.position)
                        messages.append(f"    MOVE: Blocked (facing hex obstructed, Range: {distance})")
                    
                    # Then try depth charge if DL=1-3
                    distance = hex_grid.hex_distance(escort.position, u_boat.position)
                    if current_dl >= 1 and current_dl <= 3:
                        if self.can_use_depth_charge(escort, u_boat, current_dl, hex_grid):
                            messages.append(f"    DEPTH CHARGE: Attack U-boat (Range {distance}, Depth {u_boat.depth.name})")
                            
                            damage_result = self.damage_resolver.apply_escort_attack_damage(
                                u_boat, attack_type="depth_charge", ship_type=escort.ship_type, ships=ships
                            )
                            for line in damage_result.description.split('\n'):
                                messages.append(f"      {line}")
                            
                            is_destroyed, _ = self.damage_resolver.check_destruction(u_boat)
                            if is_destroyed:
                                return current_dl, messages
                            
                            # Check if hull damage forces ascent
                            forced_ascent, ascent_msg, destroyed_by_ascent = self.check_forced_ascent(u_boat, ships)
                            if forced_ascent:
                                messages.append(f"      {ascent_msg}")
                                if destroyed_by_ascent:
                                    u_boat.hull_damage = 4
                                    return current_dl, messages
                        else:
                            # Only log if reasonably close to possible
                            if distance <= 3 or u_boat.depth != Depth.SURFACED:
                                messages.append(f"      DEPTH CHARGE not possible: Range={distance} (need ≤1), Depth={u_boat.depth.name}")
                
                elif die_result == 6:
                    # Die 6: MOVE → TURN → (if DL 1-3) DEPTH CHARGE
                    next_hex = self.get_next_hex_toward_target(
                        escort, u_boat.position, land_hexes, ships, mission_hexes
                    )
                    
                    if next_hex:
                        old_pos = escort.position
                        escort.position = next_hex
                        distance = hex_grid.hex_distance(escort.position, u_boat.position)
                        messages.append(f"    MOVE: [{old_pos.q},{old_pos.r}] -> [{next_hex.q},{next_hex.r}] (Range: {distance})")
                        
                        forced, msg, destroyed = self.check_forced_dive(escort, u_boat, next_hex, shallow_hexes)
                        if forced:
                            messages.append(f"    {msg}")
                            if destroyed:
                                u_boat.hull_damage = 4
                                return current_dl, messages
                            u_boat.depth = Depth.MEDIUM
                            current_dl = min(3, current_dl + 1)
                            # Apply forced dive AP penalty
                            if turn_manager:
                                turn_manager.set_forced_dive_penalty()
                    else:
                        messages.append(f"    MOVE: Blocked (facing hex obstructed)")
                    
                    # Always turn
                    target = self.get_turn_target(escort, u_boat, current_dl)
                    target_name = "anchor" if current_dl <= 1 else "U-boat"
                    new_facing = self.calculate_turn_direction(
                        escort, target, land_hexes, ships, mission_hexes
                    )
                    if new_facing and new_facing != escort.facing:
                        old_facing = escort.facing
                        escort.facing = new_facing
                        messages.append(f"    TURN: {old_facing.name} -> {new_facing.name} (Die 6, turning toward {target_name})")
                    
                    # Then try depth charge if DL=1-3
                    distance = hex_grid.hex_distance(escort.position, u_boat.position)
                    if current_dl >= 1 and current_dl <= 3:
                        if self.can_use_depth_charge(escort, u_boat, current_dl, hex_grid):
                            messages.append(f"    DEPTH CHARGE: Attack U-boat (Range {distance}, Depth {u_boat.depth.name})")
                            
                            damage_result = self.damage_resolver.apply_escort_attack_damage(
                                u_boat, attack_type="depth_charge", ship_type=escort.ship_type, ships=ships
                            )
                            for line in damage_result.description.split('\n'):
                                messages.append(f"      {line}")
                            
                            is_destroyed, _ = self.damage_resolver.check_destruction(u_boat)
                            if is_destroyed:
                                return current_dl, messages
                            
                            # Check if hull damage forces ascent
                            forced_ascent, ascent_msg, destroyed_by_ascent = self.check_forced_ascent(u_boat, ships)
                            if forced_ascent:
                                messages.append(f"      {ascent_msg}")
                                if destroyed_by_ascent:
                                    u_boat.hull_damage = 4
                                    return current_dl, messages
                        else:
                            # Only log if reasonably close to possible
                            if distance <= 3 or u_boat.depth != Depth.SURFACED:
                                messages.append(f"      DEPTH CHARGE not possible: Range={distance} (need ≤1), Depth={u_boat.depth.name}")
        
        # All escorts activated - return final DL and messages
        return current_dl, messages
