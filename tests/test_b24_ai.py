"""
Tests for B-24 Aircraft AI

Test coverage:
- Movement (2 hexes forward, off-map removal)
- Turning (DL-based, toward U-boat, facing rules)
- Flak defense (surfaced only, 2d6 rolls, lookout bonus)
- Attack validation (range, depth requirements)
- Damage resolution (1d6 table, hull damage, damage chart)
"""

import sys
from pathlib import Path

# Add project root to path for imports (avoid pygame requirement)
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.b24_ai import B24AI
from core.models import Aircraft, UBoat, HexCoord, Facing, Depth
from core.hex_grid import HexGrid


class MockDice:
    """Mock dice roller for deterministic testing."""
    
    def __init__(self) -> None:
        self.roll_sequence: list[int] = []
        self.roll_index: int = 0
    
    def set_roll_sequence(self, rolls: list[int]) -> None:
        """Set sequence of rolls to return."""
        self.roll_sequence = rolls
        self.roll_index = 0
    
    def roll_1d6(self) -> int:
        """Return next roll in sequence."""
        if self.roll_index < len(self.roll_sequence):
            roll = self.roll_sequence[self.roll_index]
            self.roll_index += 1
            return roll
        return 3  # Default
    
    def roll_2d6(self) -> int:
        """Return sum of two 1d6 rolls."""
        roll1 = self.roll_1d6()
        roll2 = self.roll_1d6()
        return roll1 + roll2
    
    def roll(self, num_dice: int) -> int:
        """Roll num_dice d6 and return sum."""
        if num_dice == 1:
            return self.roll_1d6()
        elif num_dice == 2:
            return self.roll_2d6()
        else:
            total = 0
            for _ in range(num_dice):
                total += self.roll_1d6()
            return total
        return 7  # Default


def create_test_hex_grid():
    """Create a test hex grid (20x20 with positive coordinates)."""
    # Create mission hexes set covering the grid (0-19, 0-19)
    mission_hexes: set[HexCoord] = set()
    for q in range(0, 20):
        for r in range(0, 20):
            mission_hexes.add(HexCoord(q, r))
    
    grid = HexGrid(size=50, cols=20, rows=20, offset_x=100, offset_y=100)
    grid.mission_hexes = mission_hexes  # type: ignore[attr-defined]  # Store for is_valid_hex checks
    return grid


# ============================================================================
# MOVEMENT TESTS
# ============================================================================

def test_b24_moves_two_hexes():
    """B-24 moves 2 hexes in facing direction."""
    dice = MockDice()
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft = Aircraft(position=HexCoord(10, 10), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(15, 15), facing=Facing.SOUTH)
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=0)  # type: ignore[reportPrivateUsage]
    
    # Should move 2 hexes north: (10,10) -> (10,9) -> (10,8)
    assert aircraft.position == HexCoord(10, 8)
    assert not remove
    assert any("Move 1" in msg for msg in messages)
    assert any("Move 2" in msg for msg in messages)


def test_b24_can_enter_any_hex():
    """B-24 can enter land and occupied hexes."""
    dice = MockDice()
    grid = create_test_hex_grid()
    
    # B-24 can move through any hex type (no terrain blocking)
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    aircraft = Aircraft(position=HexCoord(10, 14), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(10, 13), facing=Facing.SOUTH, depth=Depth.DEEP)  # Out of attack range after movement
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=0)  # type: ignore[reportPrivateUsage]
    
    # Should move through U-boat hex: (10,14) -> (10,13) -> (10,12)
    # No attack since U-boat is deep and DL=0 (no turning)
    assert aircraft.position == HexCoord(10, 12)
    assert not remove


def test_b24_removed_when_exits_map():
    """B-24 removed if it flies off map."""
    dice = MockDice()
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    # Start near edge, facing off-map
    aircraft = Aircraft(position=HexCoord(1, 1), facing=Facing.NORTHWEST)
    u_boat = UBoat(position=HexCoord(10, 10), facing=Facing.SOUTH)
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=0)  # type: ignore[reportPrivateUsage]
    
    # Should be marked for removal
    assert remove
    assert any("flew off map" in msg.lower() or "off map" in msg.lower() for msg in messages)


def test_b24_stops_at_first_hex_off_map():
    """B-24 stops moving on first hex that's off map."""
    dice = MockDice()
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    # Position where first move is still on map, second is off
    aircraft = Aircraft(position=HexCoord(-4, -4), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(0, 0), facing=Facing.SOUTH)
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=0)  # type: ignore[reportPrivateUsage]
    
    # Should be removed
    assert remove


def test_multiple_b24s_processed():
    """Multiple B-24s are processed in order."""
    dice = MockDice()
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft_list = [
        Aircraft(position=HexCoord(10, 10), facing=Facing.NORTH),
        Aircraft(position=HexCoord(11, 10), facing=Facing.SOUTH)
    ]
    u_boat = UBoat(position=HexCoord(15, 15), facing=Facing.SOUTH)
    
    _messages, _new_dl = ai.execute_b24_phase(aircraft_list, u_boat, detection_level=0)
    
    # Both should have moved
    assert aircraft_list[0].position == HexCoord(10, 8)  # Moved north
    assert aircraft_list[1].position == HexCoord(11, 12)  # Moved south
    assert len(aircraft_list) == 2


# ============================================================================
# TURNING TESTS
# ============================================================================

def test_b24_no_turn_at_dl_0():
    """B-24 doesn't turn if DL is 0."""
    dice = MockDice()
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft = Aircraft(position=HexCoord(10, 10), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(12, 10), facing=Facing.SOUTH)  # To the east
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=0)  # type: ignore[reportPrivateUsage]
    
    # Should not turn (DL too low)
    assert aircraft.facing == Facing.NORTH
    assert aircraft.position == HexCoord(10, 8)


def test_b24_no_turn_at_dl_1():
    """B-24 doesn't turn if DL is 1."""
    dice = MockDice()
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft = Aircraft(position=HexCoord(0, 0), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(2, 0), facing=Facing.SOUTH)
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=1)  # type: ignore[reportPrivateUsage]
    
    # Should not turn
    assert aircraft.facing == Facing.NORTH


def test_b24_turns_toward_uboat_at_dl_2():
    """B-24 turns toward U-boat if DL is 2."""
    dice = MockDice()
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    # B-24 facing north, U-boat to the east
    aircraft = Aircraft(position=HexCoord(10, 10), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(13, 10), facing=Facing.SOUTH)
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=2)  # type: ignore[reportPrivateUsage]
    
    # Should turn clockwise (toward east)
    assert aircraft.facing == Facing.NORTHEAST


def test_b24_no_turn_if_facing_uboat():
    """B-24 doesn't turn if already facing U-boat directly."""
    dice = MockDice()
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    # B-24 facing north, U-boat directly north
    aircraft = Aircraft(position=HexCoord(10, 10), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(10, 7), facing=Facing.SOUTH)
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=2)  # type: ignore[reportPrivateUsage]
    
    # Should not turn (already facing target)
    assert aircraft.facing == Facing.NORTH
    assert any("facing U-boat directly" in msg for msg in messages)


def test_b24_turns_randomly_if_facing_away():
    """B-24 turns randomly if facing directly away from U-boat."""
    dice = MockDice()
    dice.set_roll_sequence([2])  # Clockwise
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    # B-24 facing south, U-boat to the north
    aircraft = Aircraft(position=HexCoord(10, 10), facing=Facing.SOUTH)
    u_boat = UBoat(position=HexCoord(10, 7), facing=Facing.SOUTH)
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=2)  # type: ignore[reportPrivateUsage]
    
    # Should turn randomly (clockwise in this case)
    assert aircraft.facing == Facing.SOUTHWEST
    assert any("facing away" in msg for msg in messages)


def test_b24_turns_randomly_in_same_hex_if_facing_off_map():
    """B-24 in same hex as U-boat turns randomly if facing off-map."""
    dice = MockDice()
    dice.set_roll_sequence([5])  # Counterclockwise
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    # B-24 at (0,0) facing NORTHWEST - next hex (-1, 0) is off-map
    # Same hex as U-boat
    aircraft = Aircraft(position=HexCoord(0, 0), facing=Facing.NORTHWEST)
    u_boat = UBoat(position=HexCoord(0, 0), facing=Facing.SOUTH)
    
    # Call turn directly to test the turning logic
    messages: list[str] = []
    ai._turn_aircraft(aircraft, u_boat, messages)  # type: ignore[reportPrivateUsage]
    
    # Should turn randomly counterclockwise: NORTHWEST (5) -> SOUTHWEST (4)
    assert aircraft.facing == Facing.SOUTHWEST
    assert any("facing off-map" in msg for msg in messages)
    assert any("same hex, facing off-map" in msg for msg in messages)


def test_b24_no_turn_in_same_hex_if_not_facing_off_map():
    """B-24 in same hex doesn't turn if not facing off-map."""
    dice = MockDice()
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    # Same hex, facing valid direction
    aircraft = Aircraft(position=HexCoord(0, 0), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(0, 0), facing=Facing.SOUTH)
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=2)  # type: ignore[reportPrivateUsage]
    
    # Should not turn
    assert aircraft.facing == Facing.NORTH


# ============================================================================
# ATTACK VALIDATION TESTS
# ============================================================================

def test_can_attack_at_range_0():
    """B-24 can attack at range 0 (same hex) if U-boat surfaced."""
    dice = MockDice()
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft = Aircraft(position=HexCoord(0, 0), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(0, 0), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    assert ai.can_attack(aircraft, u_boat)


def test_can_attack_at_range_1():
    """B-24 can attack at range 1 if U-boat surfaced."""
    dice = MockDice()
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft = Aircraft(position=HexCoord(0, 0), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(0, -1), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    assert ai.can_attack(aircraft, u_boat)


def test_cannot_attack_at_range_2():
    """B-24 cannot attack at range 2."""
    dice = MockDice()
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft = Aircraft(position=HexCoord(10, 10), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(10, 8), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    assert not ai.can_attack(aircraft, u_boat)


def test_can_attack_at_periscope_depth():
    """B-24 can attack U-boat at periscope depth."""
    dice = MockDice()
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft = Aircraft(position=HexCoord(10, 10), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(10, 10), facing=Facing.SOUTH, depth=Depth.PERISCOPE)
    
    assert ai.can_attack(aircraft, u_boat)


def test_cannot_attack_at_medium_depth():
    """B-24 cannot attack U-boat at medium depth."""
    dice = MockDice()
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft = Aircraft(position=HexCoord(10, 10), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(10, 10), facing=Facing.SOUTH, depth=Depth.MEDIUM)
    
    assert not ai.can_attack(aircraft, u_boat)


def test_cannot_attack_at_deep_depth():
    """B-24 cannot attack U-boat at deep depth."""
    dice = MockDice()
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft = Aircraft(position=HexCoord(10, 10), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(10, 10), facing=Facing.SOUTH, depth=Depth.DEEP)
    
    assert not ai.can_attack(aircraft, u_boat)


# ============================================================================
# FLAK DEFENSE TESTS
# ============================================================================

def test_flak_defense_destroys_b24_on_8_plus():
    """Flak gun destroys/drives off B-24 on roll of 8+."""
    dice = MockDice()
    dice.set_roll_sequence([4, 4])  # 2d6 rolls = 8 total
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft = Aircraft(position=HexCoord(10, 10), facing=Facing.NORTH)
    # U-boat at position where B-24 will be after moving: (10,10) -> (10,8)
    u_boat = UBoat(position=HexCoord(10, 8), facing=Facing.SOUTH, depth=Depth.SURFACED)
    u_boat.flak_gun_damaged = False
    u_boat.lookout_alive = False
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=2)  # type: ignore[reportPrivateUsage]
    
    # B-24 should be destroyed/driven off
    assert remove
    assert any("destroyed/driven off" in msg for msg in messages)


def test_flak_defense_with_lookout_bonus():
    """Flak gun with lookout needs 7+ instead of 8+."""
    dice = MockDice()
    dice.set_roll_sequence([3, 4])  # 2d6 rolls = 7 total
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft = Aircraft(position=HexCoord(10, 10), facing=Facing.NORTH)
    # U-boat at position where B-24 will be after moving: (10,10) -> (10,8)
    u_boat = UBoat(position=HexCoord(10, 8), facing=Facing.SOUTH, depth=Depth.SURFACED)
    u_boat.flak_gun_damaged = False
    u_boat.lookout_alive = True
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=2)  # type: ignore[reportPrivateUsage]
    
    # B-24 should be destroyed/driven off (7+ with lookout)
    assert remove
    assert any("destroyed/driven off" in msg for msg in messages)


def test_no_flak_if_gun_damaged():
    """Cannot use flak gun if it's damaged."""
    dice = MockDice()
    dice.set_roll_sequence([6])  # Attack roll (miss)
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft = Aircraft(position=HexCoord(10, 10), facing=Facing.NORTH)
    # U-boat at position where B-24 will be after moving: (10,10) -> (10,8)
    u_boat = UBoat(position=HexCoord(10, 8), facing=Facing.SOUTH, depth=Depth.SURFACED)
    u_boat.flak_gun_damaged = True
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=2)  # type: ignore[reportPrivateUsage]
    
    # B-24 attacks (flak not used)
    assert not remove
    assert any("Flak gun damaged" in msg or "cannot defend" in msg for msg in messages)
    assert any("Missed" in msg for msg in messages)


def test_no_flak_if_not_surfaced():
    """Cannot use flak gun if not surfaced."""
    dice = MockDice()
    dice.set_roll_sequence([6])  # Attack roll (miss)
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft = Aircraft(position=HexCoord(10, 10), facing=Facing.NORTH)
    # U-boat at position where B-24 will be after moving: (10,10) -> (10,8)
    u_boat = UBoat(position=HexCoord(10, 8), facing=Facing.SOUTH, depth=Depth.PERISCOPE)
    u_boat.flak_gun_damaged = False
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=2)  # type: ignore[reportPrivateUsage]
    
    # Flak not used, but B-24 can still attack at periscope depth
    assert any("not surfaced" in msg or "cannot use flak" in msg for msg in messages)


# ============================================================================
# ATTACK/DAMAGE TESTS
# ============================================================================

def test_b24_attack_critical_hit_on_1():
    """B-24 attack roll 1 causes Critical Hit (roll 2d6 on Critical Hit table)."""
    dice = MockDice()
    dice.set_roll_sequence([3, 3, 1, 2, 3])  # Flak fails (3+3=6 < 7), attack roll (1), critical roll (2+3=5)
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft = Aircraft(position=HexCoord(10, 10), facing=Facing.NORTH)
    # U-boat at position where B-24 will be after moving: (10,10) -> (10,8)
    u_boat = UBoat(position=HexCoord(10, 8), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=2)  # type: ignore[reportPrivateUsage]
    
    # Should roll on Critical Hit table (2d6=5 means Hull Breach +1)
    assert u_boat.hull_damage == 1
    assert any("CRITICAL HIT" in msg for msg in messages)
    assert new_dl == 3  # Successful attack reveals location


def test_b24_attack_general_damage_on_2_3():
    """B-24 attack roll 2-3 causes General Damage (roll 1d6 on General Damage table)."""
    dice = MockDice()
    dice.set_roll_sequence([3, 3, 2, 1])  # Flak fails (3+3=6), attack roll (2), general damage roll (1)
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft = Aircraft(position=HexCoord(10, 10), facing=Facing.NORTH)
    # U-boat at position where B-24 will be after moving: (10,10) -> (10,8)
    u_boat = UBoat(position=HexCoord(10, 8), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=2)  # type: ignore[reportPrivateUsage]
    
    # Should roll on General Damage table (1d6=1 means Hull damage +1)
    assert u_boat.hull_damage == 1
    assert any("General Damage" in msg for msg in messages)
    assert new_dl == 3  # Successful attack


def test_b24_attack_miss_on_4_6():
    """B-24 attack roll 4-6 misses."""
    dice = MockDice()
    dice.set_roll_sequence([3, 3, 5])  # Flak fails (3+3=6), attack miss (5)
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    aircraft = Aircraft(position=HexCoord(10, 10), facing=Facing.NORTH)
    # U-boat at position where B-24 will be after moving: (10,10) -> (10,8)
    u_boat = UBoat(position=HexCoord(10, 8), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=2)  # type: ignore[reportPrivateUsage]
    
    # Should miss
    assert u_boat.hull_damage == 0
    assert any("Missed!" in msg for msg in messages)
    assert new_dl == 2  # DL unchanged on miss


def test_b24_no_attack_if_out_of_range():
    """B-24 doesn't attack if out of range."""
    dice = MockDice()
    grid = create_test_hex_grid()
    ai = B24AI(dice, grid)  # type: ignore[arg-type]
    
    # B-24 moves away from U-boat
    aircraft = Aircraft(position=HexCoord(0, 5), facing=Facing.NORTH)
    u_boat = UBoat(position=HexCoord(0, 0), facing=Facing.SOUTH, depth=Depth.SURFACED)
    
    messages, new_dl, remove, destroyed = ai._activate_aircraft(aircraft, u_boat, detection_level=2)  # type: ignore[reportPrivateUsage]
    
    # Should not attack (out of range after movement)
    assert not any("ATTACK" in msg for msg in messages)


if __name__ == '__main__':
    # Run all tests
    import pytest
    pytest.main([__file__, '-v'])
