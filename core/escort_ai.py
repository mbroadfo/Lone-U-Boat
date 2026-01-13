"""
Escort Phase AI - handles escort movement and combat actions.
"""

from typing import List, Tuple, Set, Optional, Any
from enum import Enum
from .models import Ship, UBoat, HexCoord, Facing, Depth
from .hex_grid import HexGrid
from .dice import DiceRoller
from .damage.uboat_damage import UBoatDamageResolver


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
        self.damage_resolver = UBoatDamageResolver(dice_roller)
        
        # Load escort action rules from mission_rules
        # Base dice counts
        self.destroyer_base_dice = 3
        self.corvette_base_dice = 2
        
        # Action table mapping (die result -> action)
        # Based on RULES.md Phase 4 table
        self.action_table = {
            1: [EscortAction.FIRE],  # Or DEPTH_CHARGE if conditions met
            2: [EscortAction.MOVE, EscortAction.TURN],  # MOVE, if blocked TURN, then DEPTH_CHARGE
            3: [EscortAction.MOVE],  # Then DEPTH_CHARGE
            4: [EscortAction.MOVE, EscortAction.TURN],  # MOVE, if blocked TURN, then DEPTH_CHARGE
            5: [EscortAction.TURN],  # Then DEPTH_CHARGE
            6: [EscortAction.MOVE, EscortAction.TURN],  # MOVE, if blocked TURN (then DEPTH_CHARGE)
        }
    
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
        hex_grid: HexGrid
    ) -> Optional[Facing]:
        """
        Calculate which direction to turn (left or right).
        
        Args:
            escort: The escort ship
            target: Target hex (anchor or U-boat)
            land_hexes: Set of land hexes
            ships: List of all ships (for blocking check)
            hex_grid: Hex grid for distance calculations
            
        Returns:
            New facing direction or None if no turn needed
        """
        # Check if escort is on same hex as target
        if escort.position == target:
            # Only turn if blocked
            if self._is_hex_blocked(escort.facing.forward(escort.position), land_hexes, ships, hex_grid):
                return self._random_turn(escort.facing)
            return None
        
        # Calculate angle to target
        angle = self._calculate_angle_to_target(escort.position, escort.facing, target)
        
        # If facing target (angle = 0), only turn if blocked
        if angle == 0:
            if self._is_hex_blocked(escort.facing.forward(escort.position), land_hexes, ships, hex_grid):
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
        hex_grid: HexGrid
    ) -> bool:
        """
        Check if a hex is blocked (land, ship, or off-map).
        
        Args:
            hex_coord: Hex to check
            land_hexes: Set of land hexes
            ships: List of all ships
            hex_grid: Hex grid for validation
            
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
        
        # Check if off-map (not in valid mission hexes would be ideal, but we approximate)
        # For now, just use basic bounds check
        if not (0 <= hex_coord.q < hex_grid.cols and 0 <= hex_coord.r < hex_grid.rows):
            return True
        
        return False
    
    def get_next_hex_toward_target(
        self,
        escort: Ship,
        target: HexCoord,
        land_hexes: Set[HexCoord],
        ships: List[Ship],
        hex_grid: HexGrid
    ) -> Optional[HexCoord]:
        """
        Get the next hex to move toward target.
        
        Args:
            escort: The escort ship
            target: Target position (U-boat)
            land_hexes: Set of land hexes
            ships: List of all ships
            hex_grid: Hex grid
            
        Returns:
            Next hex to move to, or None if can't move
        """
        # Try moving in facing direction first
        next_hex = escort.facing.forward(escort.position)
        
        # Check if blocked
        if self._is_hex_blocked(next_hex, land_hexes, ships, hex_grid):
            return None
        
        return next_hex
    
    def check_forced_dive(
        self,
        escort: Ship,
        u_boat: UBoat,
        new_position: HexCoord
    ) -> Tuple[bool, str]:
        """
        Check if escort movement forces U-boat to dive.
        
        Args:
            escort: The escort ship
            u_boat: The U-boat
            new_position: Escort's new position
            
        Returns:
            Tuple of (forced_dive_occurred, message)
        """
        # Check if escort moved into same hex as U-boat
        if new_position != u_boat.position:
            return False, ""
        
        # Check U-boat depth
        if u_boat.depth in [Depth.SURFACED, Depth.PERISCOPE]:
            return True, f"Escort forces U-boat to dive from {u_boat.depth.name} to MEDIUM (+1 DL, -2 AP next turn)"
        
        return False, ""
    
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
            hex_coord = hex_grid._round_hex(lerp_q, lerp_r)
            
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
        hex_grid: HexGrid
    ) -> Tuple[int, List[str]]:
        """
        Execute the escort phase for all escort ships.
        
        Args:
            ships: List of all ships
            u_boat: The U-boat
            detection_level: Current detection level (0-3)
            land_hexes: Set of land hexes
            hex_grid: Hex grid
            
        Returns:
            Tuple of (new_detection_level, messages)
        """
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
            messages.append(f"\n{escort.ship_type.upper()} at {escort.position.q},{escort.position.r} activates:")
            
            # Roll action dice
            action_rolls = self.roll_escort_actions(escort, current_dl)
            messages.append(f"  Rolled {len(action_rolls)} dice: {action_rolls}")
            
            # Execute each die result in order
            for die_result in action_rolls:
                messages.append(f"  Die {die_result}:")
                
                # Get actions for this die result
                actions = self.action_table.get(die_result, [])
                
                # Execute actions
                for action in actions:
                    if action == EscortAction.MOVE:
                        # Try to move in facing direction
                        next_hex = self.get_next_hex_toward_target(
                            escort, u_boat.position, land_hexes, ships, hex_grid
                        )
                        
                        if next_hex:
                            old_pos = escort.position
                            escort.position = next_hex
                            messages.append(f"    MOVE: {old_pos.q},{old_pos.r} → {next_hex.q},{next_hex.r}")
                            
                            # Check for forced dive
                            forced, msg = self.check_forced_dive(escort, u_boat, next_hex)
                            if forced:
                                messages.append(f"    {msg}")
                                u_boat.depth = Depth.MEDIUM
                                current_dl = min(3, current_dl + 1)
                        else:
                            messages.append(f"    MOVE: Blocked")
                            
                            # If die 2, 4, or 6 and blocked, turn
                            if die_result in [2, 4, 6]:
                                target = self.get_turn_target(escort, u_boat, current_dl)
                                new_facing = self.calculate_turn_direction(
                                    escort, target, land_hexes, ships, hex_grid
                                )
                                if new_facing and new_facing != escort.facing:
                                    old_facing = escort.facing
                                    escort.facing = new_facing
                                    messages.append(f"    TURN: {old_facing.name} → {new_facing.name}")
                    
                    elif action == EscortAction.TURN:
                        # Turn toward anchor or U-boat based on DL
                        target = self.get_turn_target(escort, u_boat, current_dl)
                        new_facing = self.calculate_turn_direction(
                            escort, target, land_hexes, ships, hex_grid
                        )
                        
                        if new_facing and new_facing != escort.facing:
                            old_facing = escort.facing
                            escort.facing = new_facing
                            messages.append(f"    TURN: {old_facing.name} → {new_facing.name}")
                    
                    elif action == EscortAction.FIRE:
                        # Try FIRE, otherwise try DEPTH_CHARGE
                        if self.can_use_fire(escort, u_boat, current_dl, land_hexes, hex_grid):
                            messages.append(f"    FIRE: Critical Hit on U-boat! (DL → 3)")
                            current_dl = 3
                            
                            # Apply gunfire damage (automatic critical hit)
                            damage_result = self.damage_resolver.apply_escort_attack_damage(
                                u_boat, attack_type="gunfire", ship_type=escort.ship_type
                            )
                            messages.append(f"      {damage_result.description}")
                            
                        elif self.can_use_depth_charge(escort, u_boat, current_dl, hex_grid):
                            messages.append(f"    DEPTH CHARGE: Attack U-boat at range {hex_grid.hex_distance(escort.position, u_boat.position)}")
                            
                            # Apply depth charge damage
                            damage_result = self.damage_resolver.apply_escort_attack_damage(
                                u_boat, attack_type="depth_charge", ship_type=escort.ship_type
                            )
                            messages.append(f"      {damage_result.description}")
                
                # Check for DEPTH_CHARGE after movement (die results 2-6)
                if die_result in [2, 3, 4, 5, 6] and current_dl >= 1:
                    if self.can_use_depth_charge(escort, u_boat, current_dl, hex_grid):
                        messages.append(f"    DEPTH CHARGE: Attack U-boat at range {hex_grid.hex_distance(escort.position, u_boat.position)}")
                        
                        # Apply depth charge damage
                        damage_result = self.damage_resolver.apply_escort_attack_damage(
                            u_boat, attack_type="depth_charge", ship_type=escort.ship_type
                        )
                        messages.append(f"      {damage_result.description}")
        
        return current_dl, messages
