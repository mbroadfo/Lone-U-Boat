"""
Core data models and structures for the Lone U-Boat game.
Contains pure data classes with no rendering or UI logic.
"""

from dataclasses import dataclass, field
from typing import List
from enum import Enum


class GamePhase(Enum):
    """Game turn phases."""
    MENU = 0
    BRIEFING = 1
    SETUP = 2
    UBOAT_PHASE = 3
    MERCHANT_PHASE = 4
    DETECTION_PHASE = 5
    ESCORT_PHASE = 6
    B24_PHASE = 7
    END_TURN_PHASE = 8
    GAME_OVER = 9


class Terrain(Enum):
    """Hex terrain types."""
    LAND = 0
    SHALLOW = 1
    DEEP = 2


class Facing(Enum):
    """Six possible facing directions for units (0-5, clockwise from top)."""
    NORTH = 0
    NORTHEAST = 1
    SOUTHEAST = 2
    SOUTH = 3
    SOUTHWEST = 4
    NORTHWEST = 5
    
    def rotate_clockwise(self) -> 'Facing':
        """Rotate one hex edge clockwise."""
        return Facing((self.value + 1) % 6)
    
    def rotate_counterclockwise(self) -> 'Facing':
        """Rotate one hex edge counterclockwise."""
        return Facing((self.value - 1) % 6)
    
    def forward(self, coord: 'HexCoord') -> 'HexCoord':
        """Get the hex coordinate in front of this facing (axial coordinates)."""
        # Constant axial direction vectors for flat-top hexes
        directions = [
            HexCoord(0, -1),   # N
            HexCoord(1, -1),   # NE
            HexCoord(1, 0),    # SE
            HexCoord(0, 1),    # S
            HexCoord(-1, 1),   # SW
            HexCoord(-1, 0),   # NW
        ]
        d = directions[self.value]
        return HexCoord(coord.q + d.q, coord.r + d.r)


class Depth(Enum):
    """U-Boat depth levels."""
    SURFACED = 0
    PERISCOPE = 1
    MEDIUM = 2
    DEEP = 3


@dataclass
class HexCoord:
    """Axial coordinate system for hexagons."""
    q: int  # column
    r: int  # row
    
    def __hash__(self) -> int:
        return hash((self.q, self.r))
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HexCoord):
            return NotImplemented
        return self.q == other.q and self.r == other.r
    
    def neighbors(self) -> List['HexCoord']:
        """Return all 6 neighboring hex coordinates (axial coordinates, flat-top)."""
        # Constant axial direction vectors for flat-top hexes
        directions = [
            HexCoord(0, -1),   # N
            HexCoord(1, -1),   # NE
            HexCoord(1, 0),    # SE
            HexCoord(0, 1),    # S
            HexCoord(-1, 1),   # SW
            HexCoord(-1, 0),   # NW
        ]
        return [HexCoord(self.q + d.q, self.r + d.r) for d in directions]


@dataclass
class UBoat:
    """The player's U-Boat."""
    position: HexCoord
    facing: Facing
    depth: Depth = Depth.SURFACED
    
    # Game state
    action_points: int = 0
    hull_damage: int = 0
    engine_damaged: bool = False
    
    # Crew (True = alive)
    captain_alive: bool = True
    engineer_alive: bool = True
    sonar_operator_alive: bool = True
    weapons_officer_alive: bool = True
    lookout_alive: bool = True
    medic_alive: bool = True
    
    # Weapons
    torpedo_tubes: List[bool] = field(default_factory=lambda: [True] * 5)  # True = loaded, 5 tubes: [0-3]=front (tubes 1-4), [4]=rear (tube 5)
    deck_gun_damaged: bool = False
    flak_gun_damaged: bool = False


@dataclass
class Ship:
    """An allied ship (merchant, corvette, or destroyer)."""
    position: HexCoord
    facing: Facing
    ship_type: str  # 'merchant', 'corvette', 'destroyer'
    damaged: bool = False


@dataclass
class Aircraft:
    """An allied aircraft (B-24 Liberator)."""
    position: HexCoord
    facing: Facing
    aircraft_type: str = 'b24'  # Future-proof for other aircraft types
