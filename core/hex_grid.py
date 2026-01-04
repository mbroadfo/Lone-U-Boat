"""
Hex grid geometry and calculations.
Handles hex-to-pixel conversions, neighbor finding, and coordinate validation.
"""

import math
from typing import Tuple, Optional, Set, List

from .models import HexCoord


class HexGrid:
    """Handles hex grid calculations and rendering."""
    
    def __init__(self, size: int, cols: int, rows: int, offset_x: float = 0, offset_y: float = 0, 
                 global_offset_x: float = 0, global_offset_y: float = 0):
        """Initialize hex grid.
        
        Args:
            size: Hex radius
            cols: Number of columns
            rows: Number of rows
            offset_x: X offset in screen space (set by layout engine)
            offset_y: Y offset in screen space (set by layout engine)
            global_offset_x: Legacy parameter, kept for backward compatibility (ignored if 0)
            global_offset_y: Legacy parameter, kept for backward compatibility (ignored if 0)
        """
        self.size = size
        self.cols = cols
        self.rows = rows
        self.offset_x = offset_x
        self.offset_y = offset_y
        # Legacy support: add global offset to main offset if non-zero
        if global_offset_x != 0 or global_offset_y != 0:
            self.offset_x += global_offset_x
            self.offset_y += global_offset_y
        
        # Flat-top hex math (pointy sides)
        self.width = 2 * size
        self.height = math.sqrt(3) * size
        self.horiz_spacing = self.width * 3/4
        
    def hex_to_pixel(self, coord: HexCoord) -> Tuple[float, float]:
        """Convert axial hex coordinates to pixel coordinates (flat-top hexes).
        
        Axial coordinates:
        - q axis: roughly horizontal (columns)
        - r axis: down-right diagonal
        """
        x = self.size * (3/2 * coord.q)
        y = self.size * (math.sqrt(3) * (coord.r + coord.q / 2))
        return (x + self.offset_x, y + self.offset_y)
    
    def pixel_to_hex(self, x: float, y: float) -> HexCoord:
        """Convert pixel coordinates to axial hex coordinates (flat-top hexes)."""
        # Adjust for offset
        x -= self.offset_x
        y -= self.offset_y
        
        # Inverse axial coordinate formulas
        q = (2/3 * x) / self.size
        r = (-1/3 * x + math.sqrt(3)/3 * y) / self.size
        
        # Round to nearest hex using cube coordinate rounding
        return self._round_hex(q, r)
    
    def _round_hex(self, q: float, r: float) -> HexCoord:
        """Round fractional axial coordinates to nearest integer hex using cube rounding.
        
        Converts axial (q,r) to cube (q,r,s) where s = -q-r, rounds all three,
        then fixes the component with largest rounding error to maintain q+r+s=0.
        """
        s = -q - r
        
        rq = round(q)
        rr = round(r)
        rs = round(s)
        
        q_diff = abs(rq - q)
        r_diff = abs(rr - r)
        s_diff = abs(rs - s)
        
        if q_diff > r_diff and q_diff > s_diff:
            rq = -rr - rs
        elif r_diff > s_diff:
            rr = -rq - rs
        
        return HexCoord(int(rq), int(rr))
    
    def get_hex_corners(self, coord: HexCoord) -> List[Tuple[float, float]]:
        """Get the pixel coordinates of a hex's 6 corners."""
        center_x, center_y = self.hex_to_pixel(coord)
        corners: List[Tuple[float, float]] = []
        
        for i in range(6):
            angle_deg = 60 * i  # Flat-top (pointy sides)
            angle_rad = math.pi / 180 * angle_deg
            corner_x = center_x + self.size * math.cos(angle_rad)
            corner_y = center_y + self.size * math.sin(angle_rad)
            corners.append((corner_x, corner_y))
        
        return corners
    
    def is_valid_hex(self, coord: HexCoord, mission_hexes: Optional[Set[HexCoord]] = None) -> bool:
        """Check if axial hex coordinate is valid for the mission.
        
        For missions, primarily rely on the mission_hexes set membership.
        The bounds check is kept as a quick rejection test.
        """
        # Quick rejection: basic bounds check
        if not (0 <= coord.q < self.cols and 0 <= coord.r < self.rows):
            return False
        
        # Primary validation: check mission-specific valid hexes if provided
        if mission_hexes is not None:
            return coord in mission_hexes
        
        return True
    
    @staticmethod
    def hex_distance(a: HexCoord, b: HexCoord) -> int:
        """
        Calculate distance between two hexes using axial coordinates.
        
        Uses cube coordinate conversion for accurate hex distance:
        - Convert axial (q, r) to cube (x, y, z) where z = -q - r
        - Distance = (|x1-x2| + |y1-y2| + |z1-z2|) / 2
        
        Args:
            a: First hex coordinate
            b: Second hex coordinate
            
        Returns:
            Distance in hex steps (0 = same hex, 1 = adjacent, etc.)
        """
        # Convert to cube coordinates
        # Axial: (q, r)
        # Cube: (x=q, y=r, z=-q-r)
        return (abs(a.q - b.q) 
                + abs(a.q + a.r - b.q - b.r)
                + abs(a.r - b.r)) // 2
    
    @staticmethod
    def hexes_in_range(
        center: HexCoord,
        range_value: int,
        valid_hexes: Optional[Set[HexCoord]] = None
    ) -> Set[HexCoord]:
        """
        Get all hexes within a given range of center hex.
        
        Args:
            center: Center hex coordinate
            range_value: Maximum distance (inclusive)
            valid_hexes: Optional set to filter results to valid hexes only
            
        Returns:
            Set of hex coordinates within range
        """
        results: Set[HexCoord] = set()
        
        # Iterate through a bounding box around the center
        for dq in range(-range_value, range_value + 1):
            for dr in range(-range_value, range_value + 1):
                # Only consider hexes where the third cube coordinate is in range
                if abs(dq + dr) <= range_value:
                    hex_coord = HexCoord(center.q + dq, center.r + dr)
                    
                    # Check distance to ensure it's within range
                    if HexGrid.hex_distance(center, hex_coord) <= range_value:
                        # Filter by valid hexes if provided
                        if valid_hexes is None or hex_coord in valid_hexes:
                            results.add(hex_coord)
        
        return results
    
    @staticmethod
    def get_neighbors(coord: HexCoord) -> List[HexCoord]:
        """
        Get all 6 neighboring hexes (axial coordinates).
        
        Flat-top hex neighbors (clockwise from right):
        - Right: (+1, 0)
        - Down-Right: (0, +1)
        - Down-Left: (-1, +1)
        - Left: (-1, 0)
        - Up-Left: (0, -1)
        - Up-Right: (+1, -1)
        
        Args:
            coord: Center hex coordinate
            
        Returns:
            List of 6 neighbor coordinates
        """
        return [
            HexCoord(coord.q + 1, coord.r),      # Right
            HexCoord(coord.q, coord.r + 1),      # Down-Right
            HexCoord(coord.q - 1, coord.r + 1),  # Down-Left
            HexCoord(coord.q - 1, coord.r),      # Left
            HexCoord(coord.q, coord.r - 1),      # Up-Left
            HexCoord(coord.q + 1, coord.r - 1),  # Up-Right
        ]
