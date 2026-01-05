"""
Movement validation for Lone U-Boat.

Validates U-Boat movement based on:
- Terrain restrictions (Land, Shallow water)
- Ship collisions (can pass under at Medium/Deep)
- Current U-Boat state (depth)

Rules from u_boat_ruleset_default.json -> MOVE restrictions
"""

from typing import Set, Tuple, List, Optional
from .models import HexCoord, UBoat, Ship, Depth


class MovementValidator:
    """
    Validate U-Boat movement to target hexes.
    
    Checks terrain and ship collision rules from JSON.
    """
    
    def __init__(
        self,
        land_hexes: Set[HexCoord],
        shallow_hexes: Set[HexCoord],
        mission_hexes: Optional[Set[HexCoord]] = None
    ):
        """
        Initialize movement validator.
        
        Args:
            land_hexes: Set of hexes containing land (impassable)
            shallow_hexes: Set of hexes with shallow water (depth restrictions)
            mission_hexes: Set of valid hexes in the mission (play area). Optional for backward compatibility.
        """
        self.land_hexes = land_hexes
        self.shallow_hexes = shallow_hexes
        self.mission_hexes = mission_hexes
    
    def can_move_to(
        self,
        u_boat: UBoat,
        target_hex: HexCoord,
        ships: List[Ship]
    ) -> Tuple[bool, str]:
        """
        Validate if U-Boat can move to target hex.
        
        Rules from u_boat_ruleset_default.json:
        1. Cannot enter Land hexes
        2. Cannot enter Shallow unless Surfaced or Periscope
        3. Cannot enter Ship hex unless Medium or Deep (pass under)
        
        Args:
            u_boat: The player's U-Boat
            target_hex: Destination hex
            ships: List of all ships in play
            
        Returns:
            (can_move, reason_if_not)
            - can_move: True if movement is valid
            - reason_if_not: String explaining why movement blocked
        """
        # Rule 0: Must stay within mission hexes (play area)
        if self.mission_hexes is not None and target_hex not in self.mission_hexes:
            return False, "Cannot move outside play area"
        
        # Rule 1: Cannot enter Land hexes
        if target_hex in self.land_hexes:
            return False, "Cannot enter land"
        
        # Rule 2: Cannot enter Shallow unless Surfaced or Periscope
        if target_hex in self.shallow_hexes:
            if u_boat.depth not in [Depth.SURFACED, Depth.PERISCOPE]:
                return False, f"Shallow water requires Surfaced or Periscope (currently {u_boat.depth.name})"
        
        # Rule 3: Cannot enter Ship hex unless Medium or Deep
        ship_at_target = self._get_ship_at_hex(target_hex, ships)
        if ship_at_target is not None:
            if u_boat.depth not in [Depth.MEDIUM, Depth.DEEP]:
                return False, f"Cannot enter ship hex unless Medium or Deep (currently {u_boat.depth.name})"
        
        # All checks passed
        return True, ""
    
    def get_valid_moves(
        self,
        u_boat: UBoat,
        candidate_hexes: Set[HexCoord],
        ships: List[Ship]
    ) -> Set[HexCoord]:
        """
        Filter candidate hexes to only valid moves.
        
        Useful for highlighting valid movement hexes in UI.
        
        Args:
            u_boat: The player's U-Boat
            candidate_hexes: Set of hexes to check (e.g., all adjacent)
            ships: List of all ships in play
            
        Returns:
            Set of hexes where U-Boat can legally move
        """
        valid: Set[HexCoord] = set()
        
        for hex_coord in candidate_hexes:
            can_move, _ = self.can_move_to(u_boat, hex_coord, ships)
            if can_move:
                valid.add(hex_coord)
        
        return valid
    
    def get_movement_info(
        self,
        u_boat: UBoat,
        target_hex: HexCoord,
        ships: List[Ship]
    ) -> str:
        """
        Get detailed info about moving to target hex.
        
        Args:
            u_boat: The player's U-Boat
            target_hex: Destination hex
            ships: List of all ships
            
        Returns:
            Formatted string with terrain info and movement validity
        """
        can_move, reason = self.can_move_to(u_boat, target_hex, ships)
        
        info_parts: List[str] = []
        
        # Terrain info
        if target_hex in self.land_hexes:
            info_parts.append("Land")
        elif target_hex in self.shallow_hexes:
            info_parts.append("Shallow Water")
        else:
            info_parts.append("Deep Water")
        
        # Ship info
        ship = self._get_ship_at_hex(target_hex, ships)
        if ship:
            info_parts.append(f"Ship: {ship.ship_type}")
        
        # Movement validity
        if can_move:
            info_parts.append("✓ Can move here")
        else:
            info_parts.append(f"✗ {reason}")
        
        return " | ".join(info_parts)
    
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
    
    def update_terrain(
        self,
        land_hexes: Set[HexCoord],
        shallow_hexes: Set[HexCoord]
    ):
        """
        Update terrain sets (if map changes dynamically).
        
        Args:
            land_hexes: New set of land hexes
            shallow_hexes: New set of shallow hexes
        """
        self.land_hexes = land_hexes
        self.shallow_hexes = shallow_hexes
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<MovementValidator: {len(self.land_hexes)} land, {len(self.shallow_hexes)} shallow>"
