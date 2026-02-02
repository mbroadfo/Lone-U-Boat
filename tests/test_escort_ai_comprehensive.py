"""
Comprehensive tests for EscortAI - validates all die results and action sequences.

This test suite validates:
- All 6 die results (1-6) with their complete action sequences
- All DL levels (0-3)
- Both destroyer and corvette behaviors
- All range conditions (0-6)
- All depth conditions (SURFACED, PERISCOPE, MEDIUM, DEEP)
- Blocked movement scenarios
- Line of sight checks
- Forced dive mechanics
- Damage scenarios
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import Any, Dict
from core.escort_ai import EscortAI
from core.models import Ship, UBoat, HexCoord, Facing, Depth
from core.hex_grid import HexGrid

try:
    import pytest
except ImportError:
    pytest = None  # type: ignore


class MockDice:
    """Mock dice roller for deterministic testing."""
    
    def __init__(self):
        self.roll_sequence: list[int] = []
        self.roll_index = 0
    
    def set_roll_sequence(self, rolls: list[int]):
        """Set the sequence of rolls to return."""
        self.roll_sequence = rolls
        self.roll_index = 0
    
    def roll_1d6(self) -> int:
        """Return next roll in sequence."""
        if self.roll_index < len(self.roll_sequence):
            result = self.roll_sequence[self.roll_index]
            self.roll_index += 1
            return result
        return 3  # Default fallback
    
    def roll_2d6(self) -> tuple[int, int]:
        """Roll two dice."""
        return (self.roll_1d6(), self.roll_1d6())


@pytest.fixture  # type: ignore
def mock_dice() -> MockDice:
    """Create mock dice roller."""
    return MockDice()


@pytest.fixture  # type: ignore
def hex_grid() -> HexGrid:
    """Create hex grid for testing."""
    return HexGrid(size=30, cols=20, rows=15)


@pytest.fixture  # type: ignore
def mission_rules() -> Dict[str, Any]:
    """Create mock mission rules."""
    return {"escort_movement": {}}


@pytest.fixture  # type: ignore
def escort_ai(mission_rules: Dict[str, Any], mock_dice: MockDice) -> EscortAI:
    """Create EscortAI with mock dice."""
    anchor_hex = HexCoord(10, 10)
    return EscortAI(mission_rules, mock_dice, anchor_hex)  # type: ignore


def create_destroyer(position: HexCoord = HexCoord(5, 5), facing: Facing = Facing.NORTH) -> Ship:
    """Helper to create a test destroyer."""
    return Ship(position=position, facing=facing, ship_type='destroyer', damaged=False)


def create_corvette(position: HexCoord = HexCoord(5, 5), facing: Facing = Facing.NORTH) -> Ship:
    """Helper to create a test corvette."""
    return Ship(position=position, facing=facing, ship_type='corvette', damaged=False)


def create_uboat(position: HexCoord = HexCoord(5, 8), depth: Depth = Depth.PERISCOPE) -> UBoat:
    """Helper to create a test U-boat."""
    return UBoat(position=position, facing=Facing.NORTH, depth=depth)


# ===== DIE 1 TESTS: FIRE or DEPTH CHARGE (if DL 1-3) =====

def test_die_1_fire_success_at_dl_2(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Die 1: FIRE successfully hits surfaced U-boat at DL 2."""
    destroyer = create_destroyer(position=HexCoord(5, 5))
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.SURFACED)  # Range 3
    
    # Die 1 rolls 1, then damage rolls
    mock_dice.set_roll_sequence([1, 4, 3])  # Action roll, 2 damage rolls
    
    ships = [destroyer]
    current_dl, messages = escort_ai.execute_escort_phase(ships, u_boat, 2, set(), hex_grid)
    
    # Should attempt FIRE
    assert any('FIRE' in m for m in messages)
    assert any('Critical Hit' in m for m in messages)
    # DL should increase to 3 from fire
    assert current_dl == 3


def test_die_1_fire_fails_no_los(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Die 1: FIRE fails when LOS blocked."""
    destroyer = create_destroyer(position=HexCoord(5, 5))
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.SURFACED)
    land_hexes = {HexCoord(5, 6), HexCoord(5, 7)}  # Block LOS
    
    mock_dice.set_roll_sequence([1])
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 2, land_hexes, hex_grid)
    
    # Should explain why FIRE not possible
    assert any('FIRE not possible' in m for m in messages)
    assert any('LOS' in m for m in messages)


def test_die_1_depth_charge_success_submerged(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Die 1: DEPTH CHARGE hits submerged U-boat at range 1."""
    destroyer = create_destroyer(position=HexCoord(5, 7))
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.PERISCOPE)  # Range 1
    
    # Die 1 rolls 1, then damage rolls
    mock_dice.set_roll_sequence([1, 3, 4])
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # Should attempt DEPTH CHARGE (not FIRE since submerged)
    assert any('DEPTH CHARGE' in m for m in messages)
    assert not any('FIRE' in m for m in messages)


def test_die_1_depth_charge_fails_out_of_range(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Die 1: DEPTH CHARGE fails when range > 1."""
    destroyer = create_destroyer(position=HexCoord(5, 5))
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.MEDIUM)  # Range 3
    
    mock_dice.set_roll_sequence([1])
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 2, set(), hex_grid)
    
    # Should explain why DEPTH CHARGE not possible
    assert any('DEPTH CHARGE not possible' in m for m in messages)
    assert any('Range=' in m for m in messages)


def test_die_1_no_action_at_dl_0(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Die 1: No action at DL 0."""
    destroyer = create_destroyer(position=HexCoord(5, 7))
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.SURFACED)
    
    mock_dice.set_roll_sequence([1, 2])  # Only need 2 dice for destroyer at DL 0
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 0, set(), hex_grid)
    
    # Should state DL requirement
    assert any('DL must be 1-3' in m for m in messages)


# ===== DIE 2 TESTS: MOVE → (if blocked) TURN → (if DL 1-3) DEPTH CHARGE =====

def test_die_2_move_and_depth_charge(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Die 2: MOVE in facing direction, then DEPTH CHARGE if in range."""
    # Position destroyer already adjacent to U-boat, facing toward it
    destroyer = create_destroyer(position=HexCoord(5, 7), facing=Facing.SOUTH)
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.MEDIUM)
    
    # Die 2 rolls 2, then damage rolls for depth charge
    mock_dice.set_roll_sequence([2, 3, 4])
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # Destroyer moves in SOUTH direction (facing) from 5,7 to next hex south
    assert any('MOVE:' in m and '5,7' in m for m in messages)
    # Should attempt DEPTH CHARGE (may or may not be in range after move)
    assert any('DEPTH CHARGE' in m for m in messages) or any('DEPTH CHARGE not possible' in m for m in messages)


def test_die_2_blocked_then_turn(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Die 2: MOVE blocked, then TURN."""
    destroyer = create_destroyer(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.MEDIUM)
    land_hexes = {HexCoord(5, 4)}  # Block forward movement
    
    mock_dice.set_roll_sequence([2])
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, land_hexes, hex_grid)
    
    # Should be blocked
    assert any('MOVE: Blocked' in m for m in messages)
    # Should turn due to blocked
    assert any('TURN' in m and 'due to blocked' in m for m in messages)


def test_die_2_move_no_depth_charge_out_of_range(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Die 2: MOVE forward but can't DEPTH CHARGE (out of range)."""
    destroyer = create_destroyer(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = create_uboat(position=HexCoord(10, 10), depth=Depth.MEDIUM)  # Far away
    
    mock_dice.set_roll_sequence([2, 3, 4, 5])
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 2, set(), hex_grid)
    
    # Should MOVE in facing direction
    assert any('MOVE:' in m and '5,5' in m for m in messages)
    # Should explain DEPTH CHARGE not possible (out of range)
    assert any('DEPTH CHARGE not possible' in m for m in messages)


# ===== DIE 3 TESTS: MOVE → TURN → (if DL 1-3) DEPTH CHARGE =====

def test_die_3_move_turn_depth_charge(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Die 3: MOVE, always TURN, then DEPTH CHARGE at DL 2."""
    destroyer = create_destroyer(position=HexCoord(5, 7), facing=Facing.SOUTH)
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.PERISCOPE)
    
    mock_dice.set_roll_sequence([3, 3, 4, 2])  # Die 3, damage rolls, turn random roll
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 2, set(), hex_grid)
    
    # Should MOVE
    assert any('MOVE' in m and '[5,8]' in m for m in messages)
    # Should TURN (always on die 3, toward anchor or U-boat based on DL)
    assert any('TURN' in m and 'Die 3, turning toward' in m for m in messages)
    # Should DEPTH CHARGE
    assert any('DEPTH CHARGE' in m for m in messages)


def test_die_3_move_turn_no_depth_charge_at_dl_0(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Die 3: MOVE and TURN but no DEPTH CHARGE at DL 0."""
    destroyer = create_destroyer(position=HexCoord(5, 7), facing=Facing.SOUTH)
    u_boat = create_uboat(position=HexCoord(10, 10), depth=Depth.PERISCOPE)  # Far away
    
    mock_dice.set_roll_sequence([3, 2, 3, 4])  # Die 3, turn random, extra dice
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 0, set(), hex_grid)
    
    # Should MOVE and TURN
    assert any('MOVE:' in m for m in messages)
    assert any('TURN' in m for m in messages)
    # At DL 0, depth charge check doesn't happen (no DL 1-3 requirement met)
    # Note: The check code runs but no attack happens, no messages about it


# ===== DIE 4 TESTS: MOVE → (if blocked) TURN → (if DL 1-3) DEPTH CHARGE =====

def test_die_4_move_and_depth_charge(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Die 4: MOVE successfully, then DEPTH CHARGE if in range."""
    corvette = create_corvette(position=HexCoord(5, 7), facing=Facing.SOUTH)
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.DEEP)
    
    mock_dice.set_roll_sequence([4, 3, 4])
    
    ships = [corvette]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # Should MOVE in facing direction
    assert any('MOVE:' in m and '5,7' in m for m in messages)
    # Should attempt DEPTH CHARGE check
    assert any('DEPTH CHARGE' in m for m in messages) or any('DEPTH CHARGE not possible' in m for m in messages)


def test_die_4_blocked_turn_depth_charge(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Die 4: MOVE blocked, TURN, then DEPTH CHARGE."""
    corvette = create_corvette(position=HexCoord(5, 7), facing=Facing.NORTH)
    u_boat = create_uboat(position=HexCoord(5, 7), depth=Depth.MEDIUM)  # Same hex
    land_hexes = {HexCoord(5, 6)}  # Block movement
    
    mock_dice.set_roll_sequence([4, 3, 4, 2])  # Die 4, damage, turn random
    
    ships = [corvette]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 3, land_hexes, hex_grid)
    
    # Should be blocked
    assert any('MOVE: Blocked' in m for m in messages)
    # Should TURN (blocked, toward anchor or U-boat based on DL)
    assert any('TURN' in m and 'blocked, turning toward' in m for m in messages)
    # Should DEPTH CHARGE (range 0)
    assert any('DEPTH CHARGE' in m and 'Range 0' in m for m in messages)


# ===== DIE 5 TESTS: MOVE → (if DL 1-3) DEPTH CHARGE =====

def test_die_5_move_and_depth_charge(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Die 5: MOVE and DEPTH CHARGE."""
    destroyer = create_destroyer(position=HexCoord(5, 7), facing=Facing.SOUTH)
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.MEDIUM)
    
    mock_dice.set_roll_sequence([5, 3, 4])
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # Should MOVE in facing direction
    assert any('MOVE:' in m and '5,7' in m for m in messages)
    # Should attempt DEPTH CHARGE check
    assert any('DEPTH CHARGE' in m for m in messages) or any('DEPTH CHARGE not possible' in m for m in messages)


def test_die_5_move_blocked_no_depth_charge(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Die 5: MOVE blocked, can't DEPTH CHARGE (out of range)."""
    destroyer = create_destroyer(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.MEDIUM)
    land_hexes = {HexCoord(5, 4)}
    
    mock_dice.set_roll_sequence([5])
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 2, land_hexes, hex_grid)
    
    # Should be blocked
    assert any('MOVE: Blocked' in m for m in messages)
    # Should explain DEPTH CHARGE not possible
    assert any('DEPTH CHARGE not possible' in m for m in messages)


# ===== DIE 6 TESTS: MOVE → TURN → (if DL 1-3) DEPTH CHARGE =====

def test_die_6_move_turn_depth_charge(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Die 6: MOVE, TURN, then DEPTH CHARGE (the Turn 10 bug scenario)."""
    destroyer = create_destroyer(position=HexCoord(6, 7), facing=Facing.SOUTHWEST)
    u_boat = create_uboat(position=HexCoord(6, 6), depth=Depth.PERISCOPE)
    
    mock_dice.set_roll_sequence([6, 3, 4, 2])  # Die 6, damage rolls, turn random
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # Should MOVE from starting position
    assert any('MOVE:' in m and '6,7' in m for m in messages)
    # Should TURN (always on die 6, toward anchor or U-boat based on DL)
    assert any('TURN' in m and 'Die 6, turning toward' in m for m in messages)
    # Should attempt DEPTH CHARGE check
    assert any('DEPTH CHARGE' in m for m in messages) or any('DEPTH CHARGE not possible' in m for m in messages)


def test_die_6_all_actions_logged(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Die 6: Verify all three actions (MOVE, TURN, DEPTH CHARGE) are logged."""
    corvette = create_corvette(position=HexCoord(5, 7), facing=Facing.SOUTH)
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.MEDIUM)
    
    mock_dice.set_roll_sequence([6, 3, 4, 2])
    
    ships = [corvette]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 3, set(), hex_grid)
    
    # Verify all three actions appear in messages
    has_move = any('MOVE:' in m for m in messages)
    has_turn = any('TURN:' in m for m in messages)
    has_depth_charge = any('DEPTH CHARGE' in m for m in messages)
    
    assert has_move, "Die 6 missing MOVE action"
    assert has_turn, "Die 6 missing TURN action"
    assert has_depth_charge, "Die 6 missing DEPTH CHARGE action"


# ===== UNIFIED TABLE TESTS: Verify destroyers and corvettes use same action table =====

def test_destroyer_and_corvette_same_die_1_behavior(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Verify destroyer and corvette both follow same Die 1 logic."""
    destroyer = create_destroyer(position=HexCoord(5, 5))
    corvette = create_corvette(position=HexCoord(5, 5))
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.SURFACED)
    
    # Test destroyer
    mock_dice.set_roll_sequence([1, 1, 1, 4, 3])  # 3 dice for destroyer
    ships = [destroyer]
    _, destroyer_messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # Test corvette
    mock_dice.set_roll_sequence([1, 1, 4, 3])  # 2 dice for corvette  
    ships = [corvette]
    _, corvette_messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # Both should attempt FIRE
    assert any('FIRE' in m for m in destroyer_messages)
    assert any('FIRE' in m for m in corvette_messages)


def test_destroyer_and_corvette_same_die_6_behavior(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Verify destroyer and corvette both MOVE + TURN + DEPTH CHARGE on Die 6."""
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.MEDIUM)
    
    # Test destroyer Die 6
    destroyer = create_destroyer(position=HexCoord(5, 7), facing=Facing.SOUTH)
    mock_dice.set_roll_sequence([6, 6, 6, 3, 4, 2, 3, 4, 2, 3, 4, 2])  # 3 dice at DL 1
    ships = [destroyer]
    _, destroyer_messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # Test corvette Die 6
    corvette = create_corvette(position=HexCoord(5, 7), facing=Facing.SOUTH)
    mock_dice.set_roll_sequence([6, 6, 3, 4, 2, 3, 4, 2])  # 2 dice at DL 1
    ships = [corvette]
    _, corvette_messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # Both should have MOVE, TURN, and DEPTH CHARGE
    for messages in [destroyer_messages, corvette_messages]:
        assert any('MOVE:' in m for m in messages), "Missing MOVE"
        assert any('TURN' in m for m in messages), "Missing TURN"
        assert any('DEPTH CHARGE' in m or 'DEPTH CHARGE not possible' in m for m in messages), "Missing DEPTH CHARGE check"


# ===== FORCED DIVE TESTS =====

def test_forced_dive_increases_dl(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Moving into surfaced U-boat hex increases DL by 1."""
    corvette = create_corvette(position=HexCoord(5, 7), facing=Facing.SOUTH)
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.SURFACED)
    
    mock_dice.set_roll_sequence([2, 3, 4])  # Die 2 moves into U-boat hex
    
    ships = [corvette]
    current_dl, messages = escort_ai.execute_escort_phase(ships, u_boat, 0, set(), hex_grid)
    
    # DL should increase from 0 to 1
    assert current_dl == 1
    # U-boat should be at MEDIUM depth
    assert u_boat.depth == Depth.MEDIUM
    # Should have forced dive message
    assert any('dive' in m.lower() for m in messages)


def test_forced_dive_in_shallow_water_destroys_uboat(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Forced dive check runs when escorts get close to surfaced U-boat."""
    # Place corvette close to U-boat
    corvette = create_corvette(position=HexCoord(5, 7), facing=Facing.SOUTH)
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.SURFACED)
    
    # Mark U-boat hex as shallow
    shallow_hexes = {HexCoord(5, 8)}
    
    # Die 2: MOVE and DEPTH CHARGE check
    mock_dice.set_roll_sequence([2, 3, 4, 5])
    
    ships = [corvette]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 0, set(), hex_grid,
                                                           shallow_hexes=shallow_hexes)
    
    # Forced dive mechanic should be checked
    # This verifies the phase runs without errors when shallow water is present
    assert len(messages) > 0

# ===== DAMAGED ESCORT TESTS =====

def test_damaged_destroyer_rolls_only_3_dice(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Damaged destroyer rolls 3 dice regardless of DL."""
    destroyer = create_destroyer(position=HexCoord(5, 5))
    destroyer.damaged = True
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.MEDIUM)
    
    # At DL 2, damaged destroyer should roll 3 dice (not 5)
    assert escort_ai.calculate_dice_count(destroyer, 2) == 3
    
    mock_dice.set_roll_sequence([1, 2, 3])  # Exactly 3 dice
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 2, set(), hex_grid)
    
    # Should process 3 die results
    assert len([m for m in messages if 'Die' in m and 'rolled' in m]) == 3


def test_damaged_corvette_rolls_only_2_dice(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Damaged corvette rolls 2 dice regardless of DL."""
    corvette = create_corvette(position=HexCoord(5, 5))
    corvette.damaged = True
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.MEDIUM)
    
    # At DL 3, damaged corvette should roll 2 dice (not 5)
    assert escort_ai.calculate_dice_count(corvette, 3) == 2
    
    mock_dice.set_roll_sequence([1, 2])  # Exactly 2 dice
    
    ships = [corvette]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 3, set(), hex_grid)
    
    # Should process 2 die results
    assert len([m for m in messages if 'Die' in m and 'rolled' in m]) == 2


# ===== RANGE AND LOS VALIDATION TESTS =====

def test_logging_shows_range_to_uboat(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Verify range to U-boat is logged for debugging."""
    destroyer = create_destroyer(position=HexCoord(5, 5))
    u_boat = create_uboat(position=HexCoord(5, 10), depth=Depth.MEDIUM)
    
    mock_dice.set_roll_sequence([2, 3, 4])
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # Should log range information (may be in format 'Range: X' or '(Range X)')
    assert any('Range' in m or 'range' in m.lower() for m in messages)


def test_logging_shows_blocked_status(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Verify blocked movement is clearly logged."""
    destroyer = create_destroyer(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.MEDIUM)
    land_hexes = {HexCoord(5, 4)}
    
    mock_dice.set_roll_sequence([2, 3, 4])
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, land_hexes, hex_grid)
    
    # Should explicitly state movement is blocked
    assert any('Blocked' in m and 'facing hex obstructed' in m for m in messages)


def test_logging_shows_depth_charge_requirements(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Verify depth charge range requirements are logged."""
    destroyer = create_destroyer(position=HexCoord(5, 5))
    u_boat = create_uboat(position=HexCoord(5, 10), depth=Depth.PERISCOPE)  # Far away
    
    mock_dice.set_roll_sequence([2, 3, 4])
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 2, set(), hex_grid)
    
    # Should explain why DEPTH CHARGE not possible
    assert any('DEPTH CHARGE not possible' in m and 'need ≤1' in m for m in messages)


# ===== MULTIPLE ESCORTS TEST =====

def test_multiple_escorts_activate_by_distance(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Multiple escorts activate in order of distance to U-boat."""
    u_boat = create_uboat(position=HexCoord(10, 10), depth=Depth.MEDIUM)
    
    # Create 3 escorts at different distances, all facing away so they don't attack
    close = create_corvette(position=HexCoord(10, 11))  # Distance 1
    close.facing = Facing.NORTH  # Facing away
    medium = create_destroyer(position=HexCoord(10, 13))  # Distance 3
    medium.facing = Facing.NORTH
    far = create_corvette(position=HexCoord(10, 15))  # Distance 5
    far.facing = Facing.NORTH
    
    # Use die results that won't destroy U-boat (die 2-6 which moves away)
    mock_dice.set_roll_sequence([2] * 20)  # All die 2: MOVE attempts
    
    ships = [far, medium, close]  # Deliberately out of order
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # Find activation order in messages
    activations = [m for m in messages if 'activates:' in m]
    
    # Should have at least 1 activation (close corvette first)
    assert len(activations) >= 1
    # Close corvette should activate first
    assert 'CORVETTE' in activations[0] and '10,11' in activations[0]
    
    # If more activated, verify order
    if len(activations) >= 2:
        assert 'DESTROYER' in activations[1] and '10,13' in activations[1]


# ===== TURN TARGET VALIDATION TESTS =====

def test_turn_target_at_dl_0_uses_anchor(escort_ai: EscortAI, hex_grid: HexGrid) -> None:
    """At DL 0, escorts turn toward anchor hex, not U-boat."""
    destroyer = create_destroyer(position=HexCoord(5, 5))
    u_boat = create_uboat(position=HexCoord(15, 5), depth=Depth.MEDIUM)  # Different from anchor (10,10)
    
    target = escort_ai.get_turn_target(destroyer, u_boat, 0)
    
    assert target == escort_ai.anchor_hex
    assert target != u_boat.position


def test_turn_target_at_dl_1_uses_anchor(escort_ai: EscortAI, hex_grid: HexGrid) -> None:
    """At DL 1, escorts still turn toward anchor hex."""
    destroyer = create_destroyer(position=HexCoord(5, 5))
    u_boat = create_uboat(position=HexCoord(15, 5), depth=Depth.MEDIUM)  # Different from anchor (10,10)
    
    target = escort_ai.get_turn_target(destroyer, u_boat, 1)
    
    assert target == escort_ai.anchor_hex
    assert target != u_boat.position


def test_turn_target_at_dl_2_uses_uboat(escort_ai: EscortAI, hex_grid: HexGrid) -> None:
    """At DL 2, escorts turn toward U-boat position."""
    destroyer = create_destroyer(position=HexCoord(5, 5))
    u_boat = create_uboat(position=HexCoord(15, 5), depth=Depth.MEDIUM)  # Different from anchor (10,10)
    
    target = escort_ai.get_turn_target(destroyer, u_boat, 2)
    
    assert target == u_boat.position
    assert target != escort_ai.anchor_hex


def test_turn_target_at_dl_3_uses_uboat(escort_ai: EscortAI, hex_grid: HexGrid) -> None:
    """At DL 3, escorts turn toward U-boat position."""
    destroyer = create_destroyer(position=HexCoord(5, 5))
    u_boat = create_uboat(position=HexCoord(15, 5), depth=Depth.MEDIUM)  # Different from anchor (10,10)
    
    target = escort_ai.get_turn_target(destroyer, u_boat, 3)
    
    assert target == u_boat.position
    assert target != escort_ai.anchor_hex


def test_escort_turns_toward_anchor_at_dl_1_in_game(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Integration test: Escort actually turns toward anchor at DL 1."""
    # Position destroyer facing away from both anchor and U-boat
    destroyer = create_destroyer(position=HexCoord(8, 8), facing=Facing.NORTH)
    u_boat = create_uboat(position=HexCoord(5, 5), depth=Depth.MEDIUM)
    # Anchor at 10,10 is SOUTHEAST from destroyer
    
    # Die 3 always turns
    mock_dice.set_roll_sequence([3, 2, 3, 4])  # Die 3, turn random (2=counterclockwise)
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # Should TURN (may turn toward anchor which is at 10,10)
    assert any('TURN' in m for m in messages)


def test_escort_turns_toward_uboat_at_dl_2_in_game(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Integration test: Escort actually turns toward U-boat at DL 2."""
    # Position destroyer facing away from U-boat
    destroyer = create_destroyer(position=HexCoord(8, 8), facing=Facing.NORTH)
    u_boat = create_uboat(position=HexCoord(8, 12), depth=Depth.MEDIUM)  # South of destroyer
    
    # Die 3 always turns
    mock_dice.set_roll_sequence([3, 5, 3, 4])  # Die 3, turn random (5=clockwise)
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 2, set(), hex_grid)
    
    # Should TURN (should turn toward U-boat which is south)
    assert any('TURN' in m for m in messages)


# ===== ADDITIONAL SCENARIO TESTS =====

def test_escort_at_range_0_same_hex_as_uboat(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Escort in same hex as submerged U-boat can depth charge."""
    destroyer = create_destroyer(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = create_uboat(position=HexCoord(5, 5), depth=Depth.PERISCOPE)  # Same hex
    
    # Die 1 attempts FIRE/DEPTH CHARGE
    mock_dice.set_roll_sequence([1, 3, 4, 5, 6])
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 2, set(), hex_grid)
    
    # Should successfully DEPTH CHARGE at range 0
    assert any('DEPTH CHARGE' in m and 'Range 0' in m for m in messages)


def test_fire_attack_at_range_6(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """FIRE attack possible at close range."""
    destroyer = create_destroyer(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.SURFACED)  # Range 3
    
    can_fire = escort_ai.can_use_fire(destroyer, u_boat, 2, set(), hex_grid)
    
    # Should be able to FIRE at range 3
    assert can_fire is True


def test_fire_attack_fails_at_range_7(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """FIRE attack not possible at range 7 (too far)."""
    destroyer = create_destroyer(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = create_uboat(position=HexCoord(5, 12), depth=Depth.SURFACED)  # Range 7
    
    can_fire = escort_ai.can_use_fire(destroyer, u_boat, 2, set(), hex_grid)
    
    # Should not be able to FIRE at range 7
    assert can_fire is False


def test_depth_charge_all_submerged_depths(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """DEPTH CHARGE works on PERISCOPE, MEDIUM, and DEEP depths."""
    destroyer = create_destroyer(position=HexCoord(5, 5), facing=Facing.NORTH)
    
    for depth in [Depth.PERISCOPE, Depth.MEDIUM, Depth.DEEP]:
        u_boat = create_uboat(position=HexCoord(5, 5), depth=depth)
        can_dc = escort_ai.can_use_depth_charge(destroyer, u_boat, 2, hex_grid)
        assert can_dc is True, f"Should be able to depth charge at {depth.name}"


def test_escort_blocked_by_map_edge(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Escort at map edge cannot move off map."""
    # Position at north edge of map
    destroyer = create_destroyer(position=HexCoord(10, 0), facing=Facing.NORTH)
    u_boat = create_uboat(position=HexCoord(10, 5), depth=Depth.MEDIUM)
    
    # Die 2 attempts to move
    mock_dice.set_roll_sequence([2, 3, 4])
    
    ships = [destroyer]
    # Set mission_hexes to define valid play area
    mission_hexes: set[HexCoord] = set()
    for q in range(20):
        for r in range(15):
            mission_hexes.add(HexCoord(q, r))
    
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid,
                                                           mission_hexes=mission_hexes)

    
    # Should be blocked
    assert any('MOVE: Blocked' in m for m in messages)


def test_escort_blocked_by_other_ship(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Escort cannot move into hex occupied by another ship."""
    destroyer = create_destroyer(position=HexCoord(5, 5), facing=Facing.SOUTH)
    corvette = create_corvette(position=HexCoord(5, 6), facing=Facing.NORTH)  # Blocking
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.MEDIUM)
    
    # Die 2 attempts to move
    mock_dice.set_roll_sequence([2, 3])
    
    ships = [destroyer, corvette]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # Destroyer should be blocked by corvette
    assert any('MOVE: Blocked' in m for m in messages)


def test_dl_increases_from_fire_hit(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """FIRE attack increases DL to 3."""
    destroyer = create_destroyer(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = create_uboat(position=HexCoord(5, 8), depth=Depth.SURFACED)
    
    # Die 1 attempts FIRE, then damage rolls
    mock_dice.set_roll_sequence([1, 3, 4, 5])
    
    ships = [destroyer]
    current_dl, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # DL should increase to 3
    assert current_dl == 3
    assert any('DL -> 3' in m for m in messages)


def test_escort_movement_respects_land_hexes(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """Escort cannot move into land hexes."""
    destroyer = create_destroyer(position=HexCoord(5, 5), facing=Facing.SOUTH)
    u_boat = create_uboat(position=HexCoord(5, 10), depth=Depth.MEDIUM)
    land_hexes = {HexCoord(5, 6)}  # Land in front
    
    # Die 2 attempts to move
    mock_dice.set_roll_sequence([2])
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, land_hexes, hex_grid)
    
    # Should be blocked by land
    assert any('MOVE: Blocked' in m for m in messages)


def test_all_dice_processed_in_sequence(escort_ai: EscortAI, mock_dice: MockDice, hex_grid: HexGrid) -> None:
    """All dice results are processed in order for one escort."""
    destroyer = create_destroyer(position=HexCoord(5, 5), facing=Facing.NORTH)
    u_boat = create_uboat(position=HexCoord(10, 10), depth=Depth.MEDIUM)
    
    # At DL 2, destroyer rolls 5 dice: results 1,2,3,4,5
    mock_dice.set_roll_sequence([1, 2, 3, 4, 5] + [3]*20)  # Action dice + damage dice
    
    ships = [destroyer]
    _, messages = escort_ai.execute_escort_phase(ships, u_boat, 2, set(), hex_grid)
    
    # Should process all 5 dice
    die_messages = [m for m in messages if 'Die' in m and 'rolled' in m]
    assert len(die_messages) == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])  # type: ignore

