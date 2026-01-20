"""
B-24 Aircraft AI System

Manages automated B-24 Liberator behavior during the B-24 Phase:
- Movement: 2 hexes in facing direction
- Turning: Toward U-boat if DL 2-3
- Attack: Bombing/strafing at range 0-1
- Flak defense: U-boat can shoot down B-24
"""

from typing import List, Tuple, Optional, Any
from .models import Aircraft, UBoat, HexCoord, Facing
from .hex_grid import HexGrid
from .dice import DiceRoller
from .damage.uboat_damage import UBoatDamageResolver


class B24AI:
    """Automated B-24 aircraft behavior."""
    
    def __init__(self, dice_roller: DiceRoller, hex_grid: HexGrid, mission_rules: Optional[Any] = None):
        """Initialize B-24 AI system.
        
        Args:
            dice_roller: Dice rolling system
            hex_grid: Hex grid for range/validation
            mission_rules: Optional mission rules for damage tables
        """
        self.dice = dice_roller
        self.hex_grid = hex_grid
        self.damage_resolver = UBoatDamageResolver(dice_roller, mission_rules)
    
    def execute_b24_phase(self, aircraft_list: List[Aircraft], u_boat: UBoat, 
                          detection_level: int) -> Tuple[List[str], int]:
        """Execute B-24 phase for all aircraft.
        
        Args:
            aircraft_list: List of aircraft on map (modified in place)
            u_boat: The U-boat
            detection_level: Current detection level (0-3)
        
        Returns:
            Tuple of (messages, new_detection_level)
        """
        messages = []
        new_dl = detection_level
        
        if not aircraft_list:
            return messages, new_dl
        
        # Process each B-24 in any order (we'll process in list order)
        aircraft_to_remove = []
        
        for i, aircraft in enumerate(aircraft_list):
            msgs, dl_change, should_remove = self._activate_aircraft(
                aircraft, u_boat, detection_level
            )
            messages.extend(msgs)
            new_dl = max(new_dl, dl_change)
            
            if should_remove:
                aircraft_to_remove.append(i)
        
        # Remove aircraft that flew off map (in reverse order to maintain indices)
        for i in reversed(aircraft_to_remove):
            messages.append(f"B-24 at {aircraft_list[i].position} flew off map")
            aircraft_list.pop(i)
        
        return messages, new_dl
    
    def _activate_aircraft(self, aircraft: Aircraft, u_boat: UBoat, 
                          detection_level: int) -> Tuple[List[str], int, bool]:
        """Activate a single B-24.
        
        Args:
            aircraft: The B-24 to activate
            u_boat: The U-boat
            detection_level: Current detection level
        
        Returns:
            Tuple of (messages, new_detection_level, should_remove_aircraft)
        """
        messages = []
        messages.append(f"B-24 at {aircraft.position} facing {aircraft.facing.name}")
        
        # Step 1: Move 2 hexes
        moved_off_map = self._move_aircraft(aircraft, messages)
        if moved_off_map:
            return messages, detection_level, True
        
        # Step 2: Turn (only if DL 2-3)
        if detection_level >= 2:
            messages.append(f"  → Turn decision (DL={detection_level} >= 2):")
            self._turn_aircraft(aircraft, u_boat, messages)
        else:
            messages.append(f"  → No turn (DL={detection_level} < 2)")
        
        # Step 3: Attack (if in range and U-boat vulnerable)
        new_dl = detection_level
        if self.can_attack(aircraft, u_boat):
            # Flak defense first (if U-boat surfaced with undamaged flak gun)
            flak_destroyed = self._flak_defense(aircraft, u_boat, messages)
            if flak_destroyed:
                return messages, detection_level, True  # B-24 destroyed/scared off
            
            # B-24 attacks
            attack_result = self._execute_attack(aircraft, u_boat, messages)
            if attack_result:
                new_dl = 3  # Successful attack reveals U-boat location
        
        return messages, new_dl, False
    
    def _move_aircraft(self, aircraft: Aircraft, messages: List[str]) -> bool:
        """Move B-24 two hexes forward.
        
        Args:
            aircraft: The B-24 to move
            messages: List to append movement messages
        
        Returns:
            True if aircraft moved off map, False otherwise
        """
        for move_num in range(1, 3):
            new_pos = aircraft.facing.forward(aircraft.position)
            
            # Check if off map (use mission_hexes if available, otherwise just bounds)
            mission_hexes = getattr(self.hex_grid, 'mission_hexes', None)
            if not self.hex_grid.is_valid_hex(new_pos, mission_hexes):
                messages.append(f"  → Move {move_num}: Off map")
                return True
            
            aircraft.position = new_pos
            messages.append(f"  → Move {move_num}: to {new_pos}")
        
        return False
    
    def _turn_aircraft(self, aircraft: Aircraft, u_boat: UBoat, messages: List[str]) -> None:
        """Turn B-24 toward U-boat (DL 2-3 only).
        
        Rules:
        - Don't turn if facing U-boat directly
        - Turn randomly if facing away from U-boat
        - If same hex as U-boat, only turn if facing off-map
        
        Args:
            aircraft: The B-24 to turn
            u_boat: The U-boat
            messages: List to append turn messages
        """
        # Check if same hex
        if aircraft.position == u_boat.position:
            forward_hex = aircraft.facing.forward(aircraft.position)
            mission_hexes = getattr(self.hex_grid, 'mission_hexes', None)
            if not self.hex_grid.is_valid_hex(forward_hex, mission_hexes):
                # Turn randomly
                direction = self.dice.roll_1d6()
                if direction <= 3:
                    aircraft.facing = aircraft.facing.rotate_clockwise()
                    messages.append(f"  → Turn: Clockwise (same hex, facing off-map)")
                else:
                    aircraft.facing = aircraft.facing.rotate_counterclockwise()
                    messages.append(f"  → Turn: Counterclockwise (same hex, facing off-map)")
            else:
                messages.append(f"  → No turn (same hex as U-boat, not facing off-map)")
            return
        
        # Check if facing U-boat directly
        if self._is_facing_target(aircraft.position, aircraft.facing, u_boat.position):
            messages.append(f"  → No turn (facing U-boat directly)")
            return
        
        # Check if facing away from U-boat
        if self._is_facing_away(aircraft.position, aircraft.facing, u_boat.position):
            # Turn randomly
            direction = self.dice.roll_1d6()
            if direction <= 3:
                aircraft.facing = aircraft.facing.rotate_clockwise()
                messages.append(f"  → Turn: Clockwise (facing away from U-boat)")
            else:
                aircraft.facing = aircraft.facing.rotate_counterclockwise()
                messages.append(f"  → Turn: Counterclockwise (facing away from U-boat)")
            return
        
        # Turn toward U-boat (like escorts)
        turn_direction = self._calculate_turn_direction(
            aircraft.position, aircraft.facing, u_boat.position
        )
        
        if turn_direction == "clockwise":
            aircraft.facing = aircraft.facing.rotate_clockwise()
            messages.append(f"  → Turn: Clockwise toward U-boat")
        elif turn_direction == "counterclockwise":
            aircraft.facing = aircraft.facing.rotate_counterclockwise()
            messages.append(f"  → Turn: Counterclockwise toward U-boat")
        else:
            messages.append(f"  → No turn needed")
    
    def _is_facing_target(self, pos: HexCoord, facing: Facing, target: HexCoord) -> bool:
        """Check if facing directly toward target."""
        # Walk forward from position and see if we hit target
        current = pos
        mission_hexes = getattr(self.hex_grid, 'mission_hexes', None)
        for _ in range(20):  # Arbitrary max distance
            current = facing.forward(current)
            if current == target:
                return True
            if not self.hex_grid.is_valid_hex(current, mission_hexes):
                return False
        return False
    
    def _is_facing_away(self, pos: HexCoord, facing: Facing, target: HexCoord) -> bool:
        """Check if facing directly away from target."""
        # Check if opposite direction faces target
        opposite_facing = Facing((facing.value + 3) % 6)
        return self._is_facing_target(pos, opposite_facing, target)
    
    def _calculate_turn_direction(self, pos: HexCoord, facing: Facing, 
                                  target: HexCoord) -> str:
        """Calculate which direction to turn to face target.
        
        Uses same logic as escort AI.
        
        Returns:
            'clockwise', 'counterclockwise', or 'none'
        """
        # Calculate angle to target
        dq = target.q - pos.q
        dr = target.r - pos.r
        
        # Convert to angle (0-5 representing hex edges)
        target_direction = self._coords_to_facing(dq, dr)
        if target_direction is None:
            return 'none'
        
        # Calculate angular difference
        current = facing.value
        target = target_direction.value
        
        # Shortest rotation direction
        diff = (target - current + 6) % 6
        
        if diff == 0:
            return 'none'
        elif diff <= 3:
            return 'clockwise'
        else:
            return 'counterclockwise'
    
    def _coords_to_facing(self, dq: int, dr: int) -> Optional[Facing]:
        """Convert coordinate difference to facing direction."""
        # Map coordinate deltas to facing directions
        if dq == 0 and dr < 0:
            return Facing.NORTH
        elif dq > 0 and dr < 0:
            return Facing.NORTHEAST
        elif dq > 0 and dr >= 0:
            return Facing.SOUTHEAST
        elif dq == 0 and dr > 0:
            return Facing.SOUTH
        elif dq < 0 and dr > 0:
            return Facing.SOUTHWEST
        elif dq < 0 and dr <= 0:
            return Facing.NORTHWEST
        return None
    
    def can_attack(self, aircraft: Aircraft, u_boat: UBoat) -> bool:
        """Check if B-24 can attack U-boat.
        
        Requirements:
        - Range 0-1
        - U-boat Surfaced or Periscope depth
        
        Args:
            aircraft: The B-24
            u_boat: The U-boat
        
        Returns:
            True if can attack
        """
        # Check range
        distance = self.hex_grid.hex_distance(aircraft.position, u_boat.position)
        if distance > 1:
            return False
        
        # Check depth
        from .models import Depth
        if u_boat.depth not in [Depth.SURFACED, Depth.PERISCOPE]:
            return False
        
        return True
    
    def _flak_defense(self, aircraft: Aircraft, u_boat: UBoat, 
                     messages: List[str]) -> bool:
        """U-boat flak gun defense.
        
        Args:
            aircraft: The attacking B-24
            u_boat: The U-boat
            messages: List to append messages
        
        Returns:
            True if B-24 destroyed/scared off, False if it survives
        """
        from .models import Depth
        
        # Can only use flak if surfaced with undamaged flak gun
        if u_boat.depth != Depth.SURFACED or u_boat.flak_gun_damaged:
            if u_boat.depth != Depth.SURFACED:
                messages.append("  → U-boat not surfaced, cannot use flak gun")
            else:
                messages.append("  → Flak gun damaged, cannot defend")
            return False
        
        # Roll 2d6, need 8+ (7+ if lookout alive)
        roll1 = self.dice.roll_1d6()
        roll2 = self.dice.roll_1d6()
        roll = roll1 + roll2
        threshold = 7 if u_boat.lookout_alive else 8
        
        threshold_text = "7+ (Lookout)" if u_boat.lookout_alive else "8+"
        messages.append(f"  → Flak defense: Rolled [{roll1}]+[{roll2}]={roll} (need {threshold_text})")
        
        if roll >= threshold:
            messages.append("  → B-24 destroyed/scared off!")
            return True
        else:
            messages.append("  → B-24 survives flak fire")
            return False
    
    def _execute_attack(self, aircraft: Aircraft, u_boat: UBoat, 
                       messages: List[str]) -> bool:
        """Execute B-24 attack on U-boat.
        
        Damage table:
        - 1-2: +2 hull damage
        - 3-4: Roll on U-Boat Damage Chart
        - 5-6: Missed
        
        Args:
            aircraft: The attacking B-24
            u_boat: The U-boat
            messages: List to append messages
        
        Returns:
            True if attack succeeded (any damage), False if missed
        """
        messages.append(f"  → B-24 ATTACK at range {self.hex_grid.hex_distance(aircraft.position, u_boat.position)}")
        
        # Roll 1d6 for attack result
        roll = self.dice.roll_1d6()
        messages.append(f"      Attack roll: {roll} (1-2=+2 hull, 3-4=damage chart, 5-6=miss)")
        
        if roll <= 2:
            # +2 hull damage
            u_boat.hull_damage += 2
            messages.append(f"      +2 Hull Damage! U-boat at {u_boat.hull_damage}/4 hull")
            
            if u_boat.hull_damage >= 4:
                messages.append("      U-BOAT DESTROYED!")
            
            return True
        
        elif roll <= 4:
            # Roll on damage chart
            damage_result = self.damage_resolver.apply_escort_attack_damage(
                u_boat, attack_type="b24", ship_type=None
            )
            messages.append(f"      {damage_result.description}")
            return True
        
        else:
            # Missed
            messages.append("      Missed!")
            return False
