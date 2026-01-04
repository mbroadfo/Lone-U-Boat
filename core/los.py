"""
Line of Sight (LOS) calculator for Lone U-Boat.

Handles LOS calculations for deck gun and torpedo attacks.
Rules: Land blocks LOS, ships/U-boats do not block LOS.
"""

from typing import Set, Tuple, Optional, List
from .models import HexCoord
from .hex_grid import HexGrid


class LOSCalculator:
    """
    Calculate line of sight between hexes.
    
    Rules from game:
    - Adjacent hexes (range 1): Always have LOS
    - Range 2: Check intervening hex(es) for Land
    - Range 3: Check 2 intervening hexes for Land
    - Land hexes block LOS
    - Ships and U-boats do NOT block LOS
    """
    
    def __init__(self, land_hexes: Set[HexCoord]):
        """
        Initialize LOS calculator.
        
        Args:
            land_hexes: Set of hexes that contain land (blocks LOS)
        """
        self.land_hexes = land_hexes
    
    def has_line_of_sight(
        self,
        from_hex: HexCoord,
        to_hex: HexCoord
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if line of sight exists between two hexes.
        
        Args:
            from_hex: Starting hex (attacker position)
            to_hex: Target hex
            
        Returns:
            (has_los, blocking_reason)
            - has_los: True if LOS exists
            - blocking_reason: String explaining why LOS blocked, or None
        """
        # Calculate distance
        distance = HexGrid.hex_distance(from_hex, to_hex)
        
        # Adjacent hexes always have LOS
        if distance == 0:
            return True, None  # Same hex
        if distance == 1:
            return True, None  # Adjacent
        
        # For range 2+, check intervening hexes
        intervening = self.get_intervening_hexes(from_hex, to_hex)
        
        # Check if any intervening hex is land
        for hex_coord in intervening:
            if hex_coord in self.land_hexes:
                return False, f"Land at {hex_coord.q},{hex_coord.r} blocks LOS"
        
        return True, None
    
    def get_intervening_hexes(
        self,
        from_hex: HexCoord,
        to_hex: HexCoord
    ) -> List[HexCoord]:
        """
        Get hexes between from_hex and to_hex (not including endpoints).
        
        Uses linear interpolation in cube coordinates for accurate hex traversal.
        
        Args:
            from_hex: Starting hex
            to_hex: Ending hex
            
        Returns:
            List of hexes along the line (excluding endpoints)
        """
        distance = HexGrid.hex_distance(from_hex, to_hex)
        
        if distance <= 1:
            return []  # No intervening hexes for adjacent or same hex
        
        # Convert to cube coordinates for interpolation
        # Axial (q, r) -> Cube (x=q, y=r, z=-q-r)
        start_x, start_y, start_z = from_hex.q, from_hex.r, -from_hex.q - from_hex.r
        end_x, end_y, end_z = to_hex.q, to_hex.r, -to_hex.q - to_hex.r
        
        intervening: List[HexCoord] = []
        
        # Sample points along the line
        for i in range(1, distance):
            # Linear interpolation
            t = i / distance
            x = start_x + (end_x - start_x) * t
            y = start_y + (end_y - start_y) * t
            z = start_z + (end_z - start_z) * t
            
            # Round to nearest hex
            rx = round(x)
            ry = round(y)
            rz = round(z)
            
            # Fix rounding errors (cube coordinates must sum to 0)
            x_diff = abs(rx - x)
            y_diff = abs(ry - y)
            z_diff = abs(rz - z)
            
            if x_diff > y_diff and x_diff > z_diff:
                rx = -ry - rz
            elif y_diff > z_diff:
                ry = -rx - rz
            else:
                rz = -rx - ry
            
            # Convert back to axial (q=x, r=y)
            hex_coord = HexCoord(rx, ry)
            
            # Avoid duplicates and endpoints
            if hex_coord != from_hex and hex_coord != to_hex:
                if hex_coord not in intervening:
                    intervening.append(hex_coord)
        
        return intervening
    
    def get_visible_hexes(
        self,
        from_hex: HexCoord,
        max_range: int,
        valid_hexes: Optional[Set[HexCoord]] = None
    ) -> Set[HexCoord]:
        """
        Get all hexes visible from a position within max range.
        
        Useful for highlighting valid targets or movement range.
        
        Args:
            from_hex: Observer position
            max_range: Maximum range to check
            valid_hexes: Optional set to filter results
            
        Returns:
            Set of hexes with LOS from from_hex
        """
        # Get all hexes in range
        in_range = HexGrid.hexes_in_range(from_hex, max_range, valid_hexes)
        
        # Filter by LOS
        visible: Set[HexCoord] = set()
        for hex_coord in in_range:
            has_los, _ = self.has_line_of_sight(from_hex, hex_coord)
            if has_los:
                visible.add(hex_coord)
        
        return visible
    
    def update_land_hexes(self, land_hexes: Set[HexCoord]):
        """
        Update the set of land hexes (if terrain changes dynamically).
        
        Args:
            land_hexes: New set of land hexes
        """
        self.land_hexes = land_hexes
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"<LOSCalculator: {len(self.land_hexes)} land hexes>"
