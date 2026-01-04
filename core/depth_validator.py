"""
Depth change validation for Lone U-Boat.

Validates depth changes based on:
- Once per turn limit
- One level at a time restriction
- Shallow water depth limits
- Ship overhead restrictions
- Hull damage depth limits

Rules from u_boat_ruleset_default.json -> CHANGE DEPTH restrictions
"""

from typing import Set, Tuple, List, Optional
from .models import HexCoord, UBoat, Ship, Depth


class DepthValidator:
    """
    Validate U-Boat depth changes.
    
    Checks all depth change rules from JSON.
    """
    
    # Depth ordering for level-by-level validation
    DEPTH_ORDER = [Depth.SURFACED, Depth.PERISCOPE, Depth.MEDIUM, Depth.DEEP]
    
    def __init__(self, shallow_hexes: Set[HexCoord]):
        """
        Initialize depth validator.
        
        Args:
            shallow_hexes: Set of hexes with shallow water (limits depth)
        """
        self.shallow_hexes = shallow_hexes
    
    def can_change_depth(
        self,
        u_boat: UBoat,
        new_depth: Depth,
        current_hex: HexCoord,
        ships: List[Ship],
        depth_changed_this_turn: bool
    ) -> Tuple[bool, str]:
        """
        Validate if U-Boat can change to new depth.
        
        Rules from u_boat_ruleset_default.json:
        1. Can only change depth once per turn
        2. Can only change by one level at a time
        3. Cannot go below Periscope in shallow water
        4. Cannot go above Medium beneath ships
        5. Hull damage limits max depth (3 dmg = Surfaced only, 2 = Periscope, 1 = Medium)
        
        Args:
            u_boat: The player's U-Boat
            new_depth: Target depth
            current_hex: U-Boat's current hex position
            ships: List of all ships in play
            depth_changed_this_turn: Whether depth already changed this turn
            
        Returns:
            (can_change, reason_if_not)
            - can_change: True if depth change is valid
            - reason_if_not: String explaining why depth change blocked
        """
        # Rule 1: Can only change depth once per turn
        if depth_changed_this_turn:
            return False, "Depth already changed this turn (once per turn limit)"
        
        # No change is always valid (but shouldn't be called)
        if new_depth == u_boat.depth:
            return True, ""
        
        # Rule 2: Can only change by one level at a time
        if not self._is_adjacent_depth(u_boat.depth, new_depth):
            return False, f"Can only change depth one level at a time (currently {u_boat.depth.name})"
        
        # Rule 3: Cannot go below Periscope in shallow water
        if current_hex in self.shallow_hexes:
            if new_depth in [Depth.MEDIUM, Depth.DEEP]:
                return False, "Shallow water: cannot go below Periscope depth"
        
        # Rule 4: Cannot go above Medium beneath ships
        ship_overhead = self._get_ship_at_hex(current_hex, ships)
        if ship_overhead is not None:
            if new_depth in [Depth.SURFACED, Depth.PERISCOPE]:
                return False, f"Ship overhead: cannot go above Medium (ship: {ship_overhead.ship_type})"
        
        # Rule 5: Hull damage limits max depth
        max_allowed = self.max_depth_for_hull_damage(u_boat.hull_damage)
        if self._depth_deeper_than(new_depth, max_allowed):
            return False, f"Hull damage ({u_boat.hull_damage}): max depth is {max_allowed.name}"
        
        # All checks passed
        return True, ""
    
    def get_valid_depths(
        self,
        u_boat: UBoat,
        current_hex: HexCoord,
        ships: List[Ship],
        depth_changed_this_turn: bool
    ) -> List[Depth]:
        """
        Get all valid depth changes from current state.
        
        Args:
            u_boat: The player's U-Boat
            current_hex: U-Boat's current hex position
            ships: List of all ships
            depth_changed_this_turn: Whether depth already changed this turn
            
        Returns:
            List of valid target depths (may be empty if already changed)
        """
        valid: List[Depth] = []
        
        for depth in self.DEPTH_ORDER:
            can_change, _ = self.can_change_depth(
                u_boat, depth, current_hex, ships, depth_changed_this_turn
            )
            if can_change and depth != u_boat.depth:
                valid.append(depth)
        
        return valid
    
    def get_depth_change_info(
        self,
        u_boat: UBoat,
        target_depth: Depth,
        current_hex: HexCoord,
        ships: List[Ship],
        depth_changed_this_turn: bool
    ) -> str:
        """
        Get detailed info about changing to target depth.
        
        Args:
            u_boat: The player's U-Boat
            target_depth: Target depth
            current_hex: U-Boat's current hex
            ships: List of all ships
            depth_changed_this_turn: Whether depth already changed
            
        Returns:
            Formatted string with depth info and validity
        """
        can_change, reason = self.can_change_depth(
            u_boat, target_depth, current_hex, ships, depth_changed_this_turn
        )
        
        info_parts: List[str] = []
        
        # Current and target
        info_parts.append(f"{u_boat.depth.name} → {target_depth.name}")
        
        # Environmental restrictions
        if current_hex in self.shallow_hexes:
            info_parts.append("Shallow Water")
        
        ship = self._get_ship_at_hex(current_hex, ships)
        if ship:
            info_parts.append(f"Ship Overhead ({ship.ship_type})")
        
        # Hull damage
        if u_boat.hull_damage > 0:
            max_depth = self.max_depth_for_hull_damage(u_boat.hull_damage)
            info_parts.append(f"Hull Dmg: max {max_depth.name}")
        
        # Validity
        if can_change:
            info_parts.append("✓ Valid")
        else:
            info_parts.append(f"✗ {reason}")
        
        return " | ".join(info_parts)
    
    @staticmethod
    def max_depth_for_hull_damage(hull_damage: int) -> Depth:
        """
        Calculate max allowed depth based on hull damage.
        
        Rules from core_system_rules.json (implicit in forced ascent):
        - 0 damage: Can go to Deep
        - 1 damage: Max Medium depth
        - 2 damage: Max Periscope depth
        - 3+ damage: Must stay Surfaced
        
        Args:
            hull_damage: Number of hull damage points (0-4)
            
        Returns:
            Maximum allowed depth
        """
        if hull_damage == 0:
            return Depth.DEEP
        elif hull_damage == 1:
            return Depth.MEDIUM
        elif hull_damage == 2:
            return Depth.PERISCOPE
        else:  # 3+ damage
            return Depth.SURFACED
    
    def _is_adjacent_depth(self, current: Depth, target: Depth) -> bool:
        """
        Check if two depths are adjacent (one level apart).
        
        Args:
            current: Current depth
            target: Target depth
            
        Returns:
            True if depths are adjacent
        """
        try:
            current_idx = self.DEPTH_ORDER.index(current)
            target_idx = self.DEPTH_ORDER.index(target)
            return abs(current_idx - target_idx) == 1
        except ValueError:
            return False
    
    def _depth_deeper_than(self, depth: Depth, max_depth: Depth) -> bool:
        """
        Check if depth is deeper than max allowed.
        
        Args:
            depth: Depth to check
            max_depth: Maximum allowed depth
            
        Returns:
            True if depth exceeds max
        """
        try:
            depth_idx = self.DEPTH_ORDER.index(depth)
            max_idx = self.DEPTH_ORDER.index(max_depth)
            return depth_idx > max_idx
        except ValueError:
            return False
    
    def _get_ship_at_hex(
        self,
        hex_coord: HexCoord,
        ships: List[Ship]
    ) -> Optional[Ship]:
        """
        Find ship at given hex, if any.
        
        Args:
            hex_coord: Hex to check
            ships: List of all ships
            
        Returns:
            Ship at hex, or None
        """
        for ship in ships:
            if ship.position == hex_coord:
                return ship
        return None
    
    def update_shallow_hexes(self, shallow_hexes: Set[HexCoord]):
        """
        Update shallow water hexes (if map changes dynamically).
        
        Args:
            shallow_hexes: New set of shallow hexes
        """
        self.shallow_hexes = shallow_hexes
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<DepthValidator: {len(self.shallow_hexes)} shallow hexes>"
