"""
Tests for Merchant AI Phase
Tests merchant movement along predefined paths with damage rules.
"""

import sys
from pathlib import Path
from typing import List
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.merchant_ai import MerchantAI, MerchantPath
from core.models import Ship, HexCoord, Facing
from core.dice import DiceRoller
import importlib


class MockDice(DiceRoller):
    """Mock dice roller for deterministic testing."""
    
    def __init__(self):
        super().__init__()
        self.next_rolls = []
    
    def set_next_roll(self, value: int):
        """Set the next roll value."""
        self.next_rolls = [value]
    
    def set_roll_sequence(self, values: List[int]) -> None:
        """Set a sequence of roll values."""
        self.next_rolls = values.copy()
    
    def roll_1d6(self, context: str = "") -> int:
        """Return predetermined roll value."""
        if self.next_rolls:
            return self.next_rolls.pop(0)
        return 6  # Default to success


class MockMissionRules:
    """Mock mission rules for testing."""
    pass


def test_merchant_path_initialization():
    """Test creating a merchant path with waypoints."""
    print("\n=== Test: Merchant Path Initialization ===")
    
    waypoints = [(1, 4), (1, 5), (1, 6), (2, 6)]
    exit_hex = (3, 7)
    
    path = MerchantPath(waypoints, exit_hex)
    
    assert len(path.waypoints) == 4
    assert path.waypoints[0] == HexCoord(1, 4)
    assert path.exit_hex == HexCoord(3, 7)
    print("✓ Path initialized with correct waypoints and exit")


def test_merchant_path_next_waypoint():
    """Test getting next waypoint from current position."""
    print("\n=== Test: Get Next Waypoint ===")
    
    waypoints = [(1, 4), (1, 5), (1, 6), (2, 6)]
    path = MerchantPath(waypoints)
    
    # At first waypoint
    next_wp = path.get_next_waypoint(HexCoord(1, 4))
    assert next_wp == HexCoord(1, 5)
    print("✓ Next waypoint from start is (1, 5)")
    
    # At middle waypoint
    next_wp = path.get_next_waypoint(HexCoord(1, 5))
    assert next_wp == HexCoord(1, 6)
    print("✓ Next waypoint from (1, 5) is (1, 6)")
    
    # At last waypoint
    next_wp = path.get_next_waypoint(HexCoord(2, 6))
    assert next_wp is None
    print("✓ No next waypoint at end of path")


def test_merchant_path_facing_calculation():
    """Test calculating facing direction toward next waypoint."""
    print("\n=== Test: Calculate Facing Direction ===")
    
    path = MerchantPath([(0, 0)])
    
    # Test all 6 directions
    test_cases = [
        (HexCoord(0, 0), HexCoord(0, -1), Facing.NORTH),
        (HexCoord(0, 0), HexCoord(1, -1), Facing.NORTHEAST),
        (HexCoord(0, 0), HexCoord(1, 0), Facing.SOUTHEAST),
        (HexCoord(0, 0), HexCoord(0, 1), Facing.SOUTH),
        (HexCoord(0, 0), HexCoord(-1, 1), Facing.SOUTHWEST),
        (HexCoord(0, 0), HexCoord(-1, 0), Facing.NORTHWEST),
    ]
    
    for current, next_pos, expected_facing in test_cases:
        facing = path.get_facing_for_next_waypoint(current, next_pos)
        assert facing == expected_facing, f"Expected {expected_facing}, got {facing}"
        print(f"✓ Facing from {current.q},{current.r} to {next_pos.q},{next_pos.r} is {facing.name}")


def test_merchant_path_exit_detection():
    """Test detecting when merchant reaches exit hex."""
    print("\n=== Test: Exit Detection ===")
    
    waypoints = [(1, 4), (1, 5), (2, 5)]
    exit_hex = (2, 5)
    path = MerchantPath(waypoints, exit_hex)
    
    assert not path.is_at_exit(HexCoord(1, 4))
    print("✓ Not at exit when at start")
    
    assert not path.is_at_exit(HexCoord(1, 5))
    print("✓ Not at exit when in middle")
    
    assert path.is_at_exit(HexCoord(2, 5))
    print("✓ At exit when at exit hex")


def test_merchant_ai_initialization():
    """Test initializing merchant AI with mission config."""
    print("\n=== Test: Merchant AI Initialization ===")
    
    # Load actual mission 1 config
    mission_config = importlib.import_module('missions.mission_1_config')
    mission_rules = MockMissionRules()
    
    ai = MerchantAI(mission_config, mission_rules)
    
    assert 0 in ai.paths
    assert len(ai.paths[0].waypoints) == 12  # Mission 1 has 12 waypoints
    assert ai.paths[0].exit_hex == HexCoord(6, 10)
    print("✓ AI initialized with mission 1 merchant paths")


def test_merchant_undamaged_movement():
    """Test undamaged merchant always moves."""
    print("\n=== Test: Undamaged Merchant Movement ===")
    
    mission_config = importlib.import_module('missions.mission_1_config')
    mission_rules = MockMissionRules()
    dice = MockDice()
    
    ai = MerchantAI(mission_config, mission_rules, dice)
    
    # Create undamaged merchant at start
    merchant = Ship(
        position=HexCoord(1, 4),
        facing=Facing.SOUTH,
        ship_type='merchant',
        damaged=False
    )
    
    new_pos, new_facing, message = ai.get_merchant_movement(merchant, 0)
    
    assert new_pos == HexCoord(1, 5)
    assert new_facing == Facing.SOUTH
    assert "moves to 1,5" in message
    print("✓ Undamaged merchant moves to next waypoint")


def test_merchant_damaged_movement_success():
    """Test damaged merchant moves on roll of 4+."""
    print("\n=== Test: Damaged Merchant Movement (Success) ===")
    
    mission_config = importlib.import_module('missions.mission_1_config')
    mission_rules = MockMissionRules()
    dice = MockDice()
    dice.set_next_roll(4)  # Roll 4 = success
    
    ai = MerchantAI(mission_config, mission_rules, dice)
    
    merchant = Ship(
        position=HexCoord(1, 4),
        facing=Facing.SOUTH,
        ship_type='merchant',
        damaged=True
    )
    
    new_pos, new_facing, message = ai.get_merchant_movement(merchant, 0)
    
    assert new_pos == HexCoord(1, 5)
    assert new_facing == Facing.SOUTH
    assert "rolled 4" in message
    assert "moves to 1,5" in message
    print("✓ Damaged merchant with roll 4+ moves")


def test_merchant_damaged_movement_fail():
    """Test damaged merchant doesn't move on roll of 1-3."""
    print("\n=== Test: Damaged Merchant Movement (Fail) ===")
    
    mission_config = importlib.import_module('missions.mission_1_config')
    mission_rules = MockMissionRules()
    dice = MockDice()
    dice.set_next_roll(3)  # Roll 3 = fail
    
    ai = MerchantAI(mission_config, mission_rules, dice)
    
    merchant = Ship(
        position=HexCoord(1, 4),
        facing=Facing.NORTH,
        ship_type='merchant',
        damaged=True
    )
    
    new_pos, new_facing, message = ai.get_merchant_movement(merchant, 0)
    
    assert new_pos is None
    assert new_facing == Facing.SOUTH  # Still updates facing
    assert "rolled 3" in message
    assert "cannot move" in message
    print("✓ Damaged merchant with roll 1-3 doesn't move but updates facing")


def test_merchant_facing_changes_at_turns():
    """Test merchant changes facing when path turns."""
    print("\n=== Test: Merchant Facing Changes at Path Turns ===")
    
    mission_config = importlib.import_module('missions.mission_1_config')
    mission_rules = MockMissionRules()
    
    ai = MerchantAI(mission_config, mission_rules)
    
    merchant = Ship(
        position=HexCoord(1, 7),  # About to turn east
        facing=Facing.SOUTH,
        ship_type='merchant',
        damaged=False
    )
    
    new_pos, new_facing, _ = ai.get_merchant_movement(merchant, 0)
    
    assert new_pos == HexCoord(2, 7)
    assert new_facing == Facing.SOUTHEAST
    print("✓ Merchant changes facing from SOUTH to SOUTHEAST at turn")


def test_execute_merchant_phase_multiple_ships():
    """Test executing merchant phase with multiple ships."""
    print("\n=== Test: Execute Merchant Phase (Multiple Ships) ===")
    
    mission_config = importlib.import_module('missions.mission_1_config')
    mission_rules = MockMissionRules()
    
    ai = MerchantAI(mission_config, mission_rules)
    
    ships = [
        Ship(HexCoord(1, 4), Facing.SOUTH, 'merchant', False),
        Ship(HexCoord(2, 3), Facing.SOUTH, 'corvette', False),  # Should be ignored
    ]
    
    messages = ai.execute_merchant_phase(ships)
    
    assert len(messages) == 1  # Only merchant moved
    assert ships[0].position == HexCoord(1, 5)
    assert ships[1].position == HexCoord(2, 3)  # Corvette unchanged
    print("✓ Merchant phase only affects merchant ships")


def test_merchant_at_end_of_path():
    """Test merchant at last waypoint."""
    print("\n=== Test: Merchant at End of Path ===")
    
    mission_config = importlib.import_module('missions.mission_1_config')
    mission_rules = MockMissionRules()
    
    ai = MerchantAI(mission_config, mission_rules)
    
    merchant = Ship(
        position=HexCoord(6, 10),  # At exit
        facing=Facing.SOUTH,
        ship_type='merchant',
        damaged=False
    )
    
    new_pos, _, message = ai.get_merchant_movement(merchant, 0)
    
    assert new_pos is None
    assert "exited the map" in message
    print("✓ Merchant at exit doesn't move")


def test_check_merchant_exit():
    """Test checking which merchants have exited."""
    print("\n=== Test: Check Merchant Exit ===")
    
    mission_config = importlib.import_module('missions.mission_1_config')
    mission_rules = MockMissionRules()
    
    ai = MerchantAI(mission_config, mission_rules)
    
    ships = [
        Ship(HexCoord(6, 10), Facing.SOUTH, 'merchant', False),  # At exit
        Ship(HexCoord(1, 5), Facing.SOUTH, 'merchant', False),   # Not at exit
        Ship(HexCoord(2, 3), Facing.SOUTH, 'corvette', False),   # Not merchant
    ]
    
    exited = ai.check_merchant_exit(ships)
    
    assert len(exited) == 1
    assert exited[0][0] == 0  # Ship index 0
    assert exited[0][1] == ships[0]
    print("✓ Correctly identified exited merchant")


def test_merchant_full_path_simulation():
    """Test merchant moving through entire path."""
    print("\n=== Test: Full Path Simulation ===")
    
    mission_config = importlib.import_module('missions.mission_1_config')
    mission_rules = MockMissionRules()
    
    ai = MerchantAI(mission_config, mission_rules)
    
    merchant = Ship(
        position=HexCoord(1, 4),
        facing=Facing.SOUTH,
        ship_type='merchant',
        damaged=False
    )
    
    # Expected path from mission config
    expected_path = [
        HexCoord(1, 4), HexCoord(1, 5), HexCoord(1, 6), HexCoord(1, 7),
        HexCoord(2, 7), HexCoord(3, 7), HexCoord(4, 7), HexCoord(5, 7),
        HexCoord(6, 7), HexCoord(6, 8), HexCoord(6, 9), HexCoord(6, 10)
    ]
    
    ships = [merchant]
    positions_visited = [merchant.position]
    
    # Simulate 15 turns (path is 12 hexes, so should complete)
    for _ in range(15):
        messages = ai.execute_merchant_phase(ships)
        if "exited" in messages[0]:
            break
        positions_visited.append(merchant.position)
    
    # Should visit all waypoints
    assert positions_visited == expected_path
    print(f"✓ Merchant followed complete path through {len(positions_visited)} waypoints")


def test_damaged_merchant_variable_movement():
    """Test damaged merchant with multiple dice rolls."""
    print("\n=== Test: Damaged Merchant Variable Movement ===")
    
    mission_config = importlib.import_module('missions.mission_1_config')
    mission_rules = MockMissionRules()
    dice = MockDice()
    
    # Set sequence: fail, fail, success, success, fail
    dice.set_roll_sequence([2, 3, 5, 6, 1])
    
    ai = MerchantAI(mission_config, mission_rules, dice)
    
    merchant = Ship(
        position=HexCoord(1, 4),
        facing=Facing.SOUTH,
        ship_type='merchant',
        damaged=True
    )
    
    ships = [merchant]
    
    # Turn 1: Roll 2 (fail)
    ai.execute_merchant_phase(ships)
    assert ships[0].position == HexCoord(1, 4)  # No movement
    
    # Turn 2: Roll 3 (fail)
    ai.execute_merchant_phase(ships)
    assert ships[0].position == HexCoord(1, 4)  # Still no movement
    
    # Turn 3: Roll 5 (success)
    ai.execute_merchant_phase(ships)
    assert ships[0].position == HexCoord(1, 5)  # Moved
    
    # Turn 4: Roll 6 (success)
    ai.execute_merchant_phase(ships)
    assert ships[0].position == HexCoord(1, 6)  # Moved
    
    # Turn 5: Roll 1 (fail)
    ai.execute_merchant_phase(ships)
    assert ships[0].position == HexCoord(1, 6)  # No movement
    
    print("✓ Damaged merchant movement varies with dice rolls")


def run_all_tests():
    """Run all merchant AI tests."""
    print("="*60)
    print("MERCHANT AI TESTS")
    print("="*60)
    
    test_functions = [
        test_merchant_path_initialization,
        test_merchant_path_next_waypoint,
        test_merchant_path_facing_calculation,
        test_merchant_path_exit_detection,
        test_merchant_ai_initialization,
        test_merchant_undamaged_movement,
        test_merchant_damaged_movement_success,
        test_merchant_damaged_movement_fail,
        test_merchant_facing_changes_at_turns,
        test_execute_merchant_phase_multiple_ships,
        test_merchant_at_end_of_path,
        test_check_merchant_exit,
        test_merchant_full_path_simulation,
        test_damaged_merchant_variable_movement,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
