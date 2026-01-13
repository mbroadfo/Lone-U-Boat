"""
Tests for Detection Phase AI
Tests escort detection rolls against U-boat based on depth, range, and modifiers.
"""

import sys
from pathlib import Path
from typing import List
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.detection_ai import DetectionAI
from core.models import Ship, UBoat, HexCoord, Facing, Depth
from core.hex_grid import HexGrid
from core.dice import DiceRoller


class MockDice(DiceRoller):
    """Mock dice roller for deterministic testing."""
    
    def __init__(self):
        super().__init__()
        self.next_rolls = []
    
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


def test_detection_threshold_surfaced():
    """Test detection threshold for surfaced U-boat."""
    print("\n=== Test: Detection Threshold - Surfaced ===")
    
    mission_rules = MockMissionRules()
    dice = MockDice()
    ai = DetectionAI(mission_rules, dice)
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED
    )
    
    threshold = ai.calculate_detection_threshold(u_boat)
    assert threshold == 2, f"Expected 2 (1 base + 1 sonar), got {threshold}"
    print(f"✓ Surfaced U-boat with sonar operator: {threshold}+")


def test_detection_threshold_periscope():
    """Test detection threshold for periscope depth."""
    print("\n=== Test: Detection Threshold - Periscope ===")
    
    mission_rules = MockMissionRules()
    dice = MockDice()
    ai = DetectionAI(mission_rules, dice)
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE
    )
    
    threshold = ai.calculate_detection_threshold(u_boat)
    assert threshold == 3, f"Expected 3 (2 base + 1 sonar), got {threshold}"
    print(f"✓ Periscope depth with sonar operator: {threshold}+")


def test_detection_threshold_medium():
    """Test detection threshold for medium depth."""
    print("\n=== Test: Detection Threshold - Medium ===")
    
    mission_rules = MockMissionRules()
    dice = MockDice()
    ai = DetectionAI(mission_rules, dice)
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.MEDIUM
    )
    
    threshold = ai.calculate_detection_threshold(u_boat)
    assert threshold == 5, f"Expected 5 (4 base + 1 sonar), got {threshold}"
    print(f"✓ Medium depth with sonar operator: {threshold}+")


def test_detection_threshold_deep():
    """Test detection threshold for deep depth."""
    print("\n=== Test: Detection Threshold - Deep ===")
    
    mission_rules = MockMissionRules()
    dice = MockDice()
    ai = DetectionAI(mission_rules, dice)
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.DEEP
    )
    
    threshold = ai.calculate_detection_threshold(u_boat)
    assert threshold == 6, f"Expected 6 (5 base + 1 sonar), got {threshold}"
    print(f"✓ Deep depth with sonar operator: {threshold}+")


def test_detection_threshold_with_sonar_operator():
    """Test sonar operator modifier (increases threshold)."""
    print("\n=== Test: Detection Threshold - Sonar Operator Alive ===")
    
    mission_rules = MockMissionRules()
    dice = MockDice()
    ai = DetectionAI(mission_rules, dice)
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE
    )
    u_boat.sonar_operator_alive = True  # Alive
    
    threshold = ai.calculate_detection_threshold(u_boat)
    assert threshold == 3, f"Expected 3 (2+1), got {threshold}"
    print(f"✓ Periscope with sonar operator: {threshold}+ (harder to detect)")


def test_detection_threshold_with_engine_damage():
    """Test engine damage modifier (decreases threshold)."""
    print("\n=== Test: Detection Threshold - Engine Damaged ===")
    
    mission_rules = MockMissionRules()
    dice = MockDice()
    ai = DetectionAI(mission_rules, dice)
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.MEDIUM
    )
    u_boat.sonar_operator_alive = False  # Kill sonar operator for clean test
    u_boat.engine_damaged = True
    
    threshold = ai.calculate_detection_threshold(u_boat)
    assert threshold == 3, f"Expected 3 (4 base - 1 engine), got {threshold}"
    print(f"✓ Medium with engine damage (no sonar): {threshold}+ (easier to detect)")


def test_detection_threshold_both_modifiers():
    """Test both modifiers canceling each other out."""
    print("\n=== Test: Detection Threshold - Both Modifiers ===")
    
    mission_rules = MockMissionRules()
    dice = MockDice()
    ai = DetectionAI(mission_rules, dice)
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.MEDIUM
    )
    u_boat.sonar_operator_alive = True  # +1
    u_boat.engine_damaged = True          # -1
    
    threshold = ai.calculate_detection_threshold(u_boat)
    assert threshold == 4, f"Expected 4 (4+1-1), got {threshold}"
    print(f"✓ Both modifiers cancel out: {threshold}+")


def test_escort_can_detect_in_range():
    """Test escort within range can attempt detection."""
    print("\n=== Test: Escort Can Detect - In Range ===")
    
    mission_rules = MockMissionRules()
    dice = MockDice()
    ai = DetectionAI(mission_rules, dice)
    
    hex_grid = HexGrid(size=20, cols=10, rows=10, offset_x=0, offset_y=0)
    
    corvette = Ship(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        ship_type='corvette',
        damaged=False
    )
    
    u_boat = UBoat(
        position=HexCoord(5, 7),  # Range 2
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE
    )
    
    land_hexes = set()
    
    can_detect, reason = ai.check_escort_can_detect(corvette, u_boat, land_hexes, hex_grid)
    assert can_detect, f"Expected can detect, got: {reason}"
    assert "R2" in reason
    print(f"✓ Corvette at range 2 can detect: {reason}")


def test_escort_out_of_range():
    """Test escort beyond range 3 cannot detect."""
    print("\n=== Test: Escort Can Detect - Out of Range ===")
    
    mission_rules = MockMissionRules()
    dice = MockDice()
    ai = DetectionAI(mission_rules, dice)
    
    hex_grid = HexGrid(size=20, cols=10, rows=10, offset_x=0, offset_y=0)
    
    destroyer = Ship(
        position=HexCoord(1, 1),
        facing=Facing.NORTH,
        ship_type='destroyer',
        damaged=False
    )
    
    u_boat = UBoat(
        position=HexCoord(5, 5),  # Range 4
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE
    )
    
    land_hexes = set()
    
    can_detect, reason = ai.check_escort_can_detect(destroyer, u_boat, land_hexes, hex_grid)
    assert not can_detect, f"Expected cannot detect, got: {reason}"
    assert "Out of range" in reason
    print(f"✓ Destroyer at range 4+ cannot detect: {reason}")


def test_merchant_cannot_detect():
    """Test merchant ships cannot detect."""
    print("\n=== Test: Merchant Cannot Detect ===")
    
    mission_rules = MockMissionRules()
    dice = MockDice()
    ai = DetectionAI(mission_rules, dice)
    
    hex_grid = HexGrid(size=20, cols=10, rows=10, offset_x=0, offset_y=0)
    
    merchant = Ship(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        ship_type='merchant',
        damaged=False
    )
    
    u_boat = UBoat(
        position=HexCoord(5, 6),  # Range 1
        facing=Facing.NORTH,
        depth=Depth.SURFACED
    )
    
    land_hexes = set()
    
    can_detect, reason = ai.check_escort_can_detect(merchant, u_boat, land_hexes, hex_grid)
    assert not can_detect
    assert "Merchant cannot detect" in reason
    print(f"✓ Merchant cannot detect: {reason}")


def test_detection_roll_success():
    """Test successful detection roll increases DL."""
    print("\n=== Test: Detection Roll Success ===")
    
    mission_rules = MockMissionRules()
    dice = MockDice()
    dice.set_roll_sequence([5])  # Roll 5 vs threshold 5 = success
    
    ai = DetectionAI(mission_rules, dice)
    hex_grid = HexGrid(size=20, cols=10, rows=10, offset_x=0, offset_y=0)
    
    ships = [
        Ship(HexCoord(5, 5), Facing.NORTH, 'corvette', False)
    ]
    
    u_boat = UBoat(HexCoord(5, 7), Facing.NORTH, Depth.MEDIUM)  # Threshold 5 (with sonar)
    
    new_dl, messages = ai.execute_detection_phase(
        ships=ships,
        u_boat=u_boat,
        current_detection_level=0,
        land_hexes=set(),
        hex_grid=hex_grid
    )
    
    assert new_dl == 1, f"Expected DL 1, got {new_dl}"
    assert any("SUCCESS" in msg for msg in messages)
    print(f"✓ Detection success: DL 0 → {new_dl}")


def test_detection_roll_failure():
    """Test failed detection roll does not increase DL."""
    print("\n=== Test: Detection Roll Failure ===")
    
    mission_rules = MockMissionRules()
    dice = MockDice()
    dice.set_roll_sequence([4])  # Roll 4 vs threshold 5 = fail
    
    ai = DetectionAI(mission_rules, dice)
    hex_grid = HexGrid(size=20, cols=10, rows=10, offset_x=0, offset_y=0)
    
    ships = [
        Ship(HexCoord(5, 5), Facing.NORTH, 'corvette', False)
    ]
    
    u_boat = UBoat(HexCoord(5, 7), Facing.NORTH, Depth.MEDIUM)  # Threshold 5 (with sonar)
    
    new_dl, messages = ai.execute_detection_phase(
        ships=ships,
        u_boat=u_boat,
        current_detection_level=0,
        land_hexes=set(),
        hex_grid=hex_grid
    )
    
    assert new_dl == 0, f"Expected DL 0, got {new_dl}"
    assert any("failed" in msg for msg in messages)
    print(f"✓ Detection failed: DL remains at {new_dl}")


def test_multiple_escorts_detecting():
    """Test multiple escorts rolling for detection."""
    print("\n=== Test: Multiple Escorts Detecting ===")
    
    mission_rules = MockMissionRules()
    dice = MockDice()
    dice.set_roll_sequence([3, 4])  # Both succeed (vs threshold 3)
    
    ai = DetectionAI(mission_rules, dice)
    hex_grid = HexGrid(size=20, cols=10, rows=10, offset_x=0, offset_y=0)
    
    ships = [
        Ship(HexCoord(5, 5), Facing.NORTH, 'corvette', False),
        Ship(HexCoord(4, 6), Facing.NORTH, 'destroyer', False)
    ]
    
    u_boat = UBoat(HexCoord(5, 7), Facing.NORTH, Depth.PERISCOPE)  # Threshold 3 (with sonar)
    
    new_dl, messages = ai.execute_detection_phase(
        ships=ships,
        u_boat=u_boat,
        current_detection_level=0,
        land_hexes=set(),
        hex_grid=hex_grid
    )
    
    assert new_dl == 2, f"Expected DL 2, got {new_dl}"
    print(f"✓ Multiple escorts: 2 rolls, both success, DL 0 → {new_dl}")


def test_detection_capped_at_3():
    """Test detection level cannot exceed 3."""
    print("\n=== Test: Detection Level Capped at 3 ===")
    
    mission_rules = MockMissionRules()
    dice = MockDice()
    dice.set_roll_sequence([2, 3])  # Both succeed (vs threshold 2)
    
    ai = DetectionAI(mission_rules, dice)
    hex_grid = HexGrid(size=20, cols=10, rows=10, offset_x=0, offset_y=0)
    
    ships = [
        Ship(HexCoord(5, 5), Facing.NORTH, 'corvette', False),
        Ship(HexCoord(4, 6), Facing.NORTH, 'destroyer', False)
    ]
    
    u_boat = UBoat(HexCoord(5, 7), Facing.NORTH, Depth.SURFACED)  # Threshold 2 (with sonar)
    
    new_dl, messages = ai.execute_detection_phase(
        ships=ships,
        u_boat=u_boat,
        current_detection_level=2,  # Start at 2
        land_hexes=set(),
        hex_grid=hex_grid
    )
    
    assert new_dl == 3, f"Expected DL 3 (capped), got {new_dl}"
    print(f"✓ Detection capped: DL 2 + 2 successes = {new_dl} (max)")


def test_skip_detection_at_max_dl():
    """Test detection phase skipped when DL already at 3."""
    print("\n=== Test: Skip Detection at Max DL ===")
    
    mission_rules = MockMissionRules()
    dice = MockDice()
    
    ai = DetectionAI(mission_rules, dice)
    hex_grid = HexGrid(size=20, cols=10, rows=10, offset_x=0, offset_y=0)
    
    ships = [Ship(HexCoord(5, 5), Facing.NORTH, 'corvette', False)]
    u_boat = UBoat(HexCoord(5, 7), Facing.NORTH, Depth.SURFACED)
    
    new_dl, messages = ai.execute_detection_phase(
        ships=ships,
        u_boat=u_boat,
        current_detection_level=3,  # Already at max
        land_hexes=set(),
        hex_grid=hex_grid
    )
    
    assert new_dl == 3
    assert any("already at maximum" in msg for msg in messages)
    print(f"✓ Detection skipped when DL already at {new_dl}")


def test_no_escorts_in_range():
    """Test detection phase when no escorts can detect."""
    print("\n=== Test: No Escorts in Range ===")
    
    mission_rules = MockMissionRules()
    dice = MockDice()
    
    ai = DetectionAI(mission_rules, dice)
    hex_grid = HexGrid(size=20, cols=10, rows=10, offset_x=0, offset_y=0)
    
    # Escorts far away
    ships = [
        Ship(HexCoord(0, 0), Facing.NORTH, 'corvette', False),
        Ship(HexCoord(9, 9), Facing.NORTH, 'destroyer', False)
    ]
    
    u_boat = UBoat(HexCoord(5, 5), Facing.NORTH, Depth.SURFACED)
    
    new_dl, messages = ai.execute_detection_phase(
        ships=ships,
        u_boat=u_boat,
        current_detection_level=0,
        land_hexes=set(),
        hex_grid=hex_grid
    )
    
    assert new_dl == 0
    assert any("No escorts can attempt" in msg for msg in messages)
    print(f"✓ No escorts in range: DL remains {new_dl}")


def run_all_tests():
    """Run all detection AI tests."""
    print("="*60)
    print("DETECTION AI TESTS")
    print("="*60)
    
    test_functions = [
        test_detection_threshold_surfaced,
        test_detection_threshold_periscope,
        test_detection_threshold_medium,
        test_detection_threshold_deep,
        test_detection_threshold_with_sonar_operator,
        test_detection_threshold_with_engine_damage,
        test_detection_threshold_both_modifiers,
        test_escort_can_detect_in_range,
        test_escort_out_of_range,
        test_merchant_cannot_detect,
        test_detection_roll_success,
        test_detection_roll_failure,
        test_multiple_escorts_detecting,
        test_detection_capped_at_3,
        test_skip_detection_at_max_dl,
        test_no_escorts_in_range,
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
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
