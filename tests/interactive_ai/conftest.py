"""
Pytest fixtures for Interactive AI tests.

Provides shared test fixtures (mock objects, game state setup) for testing
the interactive AI action system.
"""

import pytest
import sys
from pathlib import Path
from typing import List, Tuple, Any, Dict
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.models import Ship, HexCoord, Facing, UBoat, Depth
from core.dice import DiceRoller
from core.hex_grid import HexGrid


class MockDice(DiceRoller):
    """Mock dice roller for deterministic testing."""
    
    def __init__(self):
        super().__init__()
        self.next_rolls: List[int] = []
    
    def set_next_roll(self, value: int):
        """Set the next roll value."""
        self.next_rolls = [value]
    
    def set_roll_sequence(self, values: List[int]) -> None:
        """Set a sequence of roll values."""
        self.next_rolls = values.copy()
    
    def roll_1d6(self, context: str = "") -> int:
        """Return predetermined roll value."""
        if self.next_rolls:
            result = self.next_rolls.pop(0)
        else:
            result = 6  # Default to success
        return result


class MockMissionConfig:
    """Mock mission config with merchant paths."""
    
    def __init__(self):
        # Simple merchant paths for testing
        self.MERCHANT_PATHS: List[Dict[str, Any]] = [
            {
                'ship_index': 0,
                'waypoints': [
                    (1, 4), (1, 5), (1, 6), (2, 6), (3, 6),
                    (4, 6), (4, 7), (5, 7), (5, 8), (6, 8), (6, 9)
                ],
                'exit_hex': (6, 9)
            },
            {
                'ship_index': 1,
                'waypoints': [
                    (1, 5), (1, 6), (2, 6), (3, 6), (4, 6),
                    (4, 7), (5, 7), (5, 8), (6, 8), (6, 9)
                ],
                'exit_hex': (6, 9)
            }
        ]


class MockMissionRules:
    """Mock mission rules for testing."""
    
    def get_section_by_id(self, section_id: str) -> Dict[str, Any]:
        """Return mock rules section."""
        if section_id == "merchant_movement":
            return {
                "rules": [
                    {
                        "condition": "UNDAMAGED",
                        "action": "MOVE",
                        "distance": 1
                    },
                    {
                        "condition": "DAMAGED",
                        "action": "ROLL_TO_MOVE",
                        "dice": "1d6",
                        "success": "4+",
                        "on_success": {"action": "MOVE", "distance": 1},
                        "on_fail": {"action": "NO_MOVE"}
                    }
                ]
            }
        elif section_id == "escort_activation_order":
            return {
                "dice_calculation": {
                    "destroyer": {"base": 3},
                    "corvette": {"base": 2}
                }
            }
        elif section_id == "destroyer_actions":
            return {
                "results": [
                    {"roll": 1, "sequence": [{"action": "FIRE"}]},
                    {"roll": 2, "sequence": [{"action": "MOVE"}, {"action": "TURN"}]},
                    {"roll": 3, "sequence": [{"action": "MOVE"}]},
                    {"roll": 4, "sequence": [{"action": "MOVE"}, {"action": "TURN"}]},
                    {"roll": 5, "sequence": [{"action": "TURN"}]},
                    {"roll": 6, "sequence": [{"action": "MOVE"}, {"action": "TURN"}]}
                ]
            }
        return {}


class MockAnimationManager:
    """Mock animation manager to track animation calls."""
    
    def __init__(self):
        self.ship_movements: List[Tuple[int, HexCoord, HexCoord]] = []  # Track (ship_idx, old_pos, new_pos)
        self.ship_rotations: List[Tuple[int, Facing, Facing]] = []  # Track (ship_idx, old_facing, new_facing)
        self.aircraft_movements: List[Tuple[int, HexCoord, HexCoord]] = []  # Track (aircraft_idx, old_pos, new_pos)
        self.aircraft_rotations: List[Tuple[int, Facing, Facing]] = []  # Track (aircraft_idx, old_facing, new_facing)
    
    def start_ship_movement(self, ship_idx: int, old_pos: HexCoord, new_pos: HexCoord):
        """Record ship movement animation."""
        self.ship_movements.append((ship_idx, old_pos, new_pos))
    
    def start_ship_rotation(self, ship_idx: int, old_facing: Facing, new_facing: Facing):
        """Record ship rotation animation."""
        self.ship_rotations.append((ship_idx, old_facing, new_facing))
    
    def start_aircraft_movement(self, aircraft_idx: int, old_pos: HexCoord, new_pos: HexCoord):
        """Record aircraft movement animation."""
        self.aircraft_movements.append((aircraft_idx, old_pos, new_pos))
    
    def start_aircraft_rotation(self, aircraft_idx: int, old_facing: Facing, new_facing: Facing):
        """Record aircraft rotation animation."""
        self.aircraft_rotations.append((aircraft_idx, old_facing, new_facing))


class MockGameState:
    """Mock game state for testing AI actions."""
    
    def __init__(self):
        self.ships = []
        self.uboat = UBoat(position=HexCoord(5, 5), facing=Facing.NORTH, depth=Depth.SURFACED)
        self.animation_manager = MockAnimationManager()
        self.hex_grid = HexGrid(size=50, cols=20, rows=20)
        self.mission_config = MockMissionConfig()
        self.mission_rules = MockMissionRules()
        self.land_hexes: set[HexCoord] = set()
        self.mission_hexes = {HexCoord(q, r) for q in range(20) for r in range(20)}
        self.shallow_hexes: set[HexCoord] = set()
        self.detection_level = 1
        self.turn_manager = None
        # B-24 test attributes
        self.aircraft = []
        self.u_boat = self.uboat  # Alias for B-24 tests
        self.dice_roller: Any = None
        self.damage_resolver: Any = None
        
        # Load mission paths
        from core.merchant_ai import MerchantAI
        self.merchant_ai = MerchantAI(
            mission_config=self.mission_config,
            mission_rules=self.mission_rules,
            dice_roller=MockDice()
        )
        
        # Load escort AI
        from core.escort_ai import EscortAI
        self.escort_ai = EscortAI(
            mission_rules=self.mission_rules,
            dice_roller=MockDice(),
            anchor_hex=HexCoord(10, 10)
        )


@pytest.fixture
def mock_dice():
    """Provide a mock dice roller."""
    return MockDice()


@pytest.fixture
def mission_config():
    """Provide mock mission configuration."""
    return MockMissionConfig()


@pytest.fixture
def mission_rules():
    """Provide mock mission rules."""
    return MockMissionRules()


@pytest.fixture
def mock_game_state():
    """Provide a mock game state with standard setup."""
    return MockGameState()


@pytest.fixture
def undamaged_merchant():
    """Create an undamaged merchant ship at starting position."""
    return Ship(
        position=HexCoord(1, 4),
        facing=Facing.SOUTH,
        ship_type='merchant',
        damaged=False
    )


@pytest.fixture
def damaged_merchant():
    """Create a damaged merchant ship."""
    return Ship(
        position=HexCoord(1, 4),
        facing=Facing.SOUTH,
        ship_type='merchant',
        damaged=True
    )


@pytest.fixture
def hex_grid():
    """Provide a hex grid for distance calculations."""
    return HexGrid(size=50, cols=20, rows=20)


@pytest.fixture
def destroyer():
    """Create an undamaged destroyer."""
    return Ship(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        ship_type='destroyer',
        damaged=False
    )


@pytest.fixture
def corvette():
    """Create an undamaged corvette."""
    return Ship(
        position=HexCoord(6, 6),
        facing=Facing.SOUTHEAST,
        ship_type='corvette',
        damaged=False
    )


@pytest.fixture
def damaged_destroyer():
    """Create a damaged destroyer."""
    return Ship(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        ship_type='destroyer',
        damaged=True
    )


@pytest.fixture
def surfaced_uboat():
    """Create a surfaced U-boat."""
    return UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED
    )


@pytest.fixture
def submerged_uboat():
    """Create a submerged U-boat."""
    return UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.MEDIUM
    )
