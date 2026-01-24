"""
Tests for EscortAI - escort movement and combat actions.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import directly from modules to avoid pygame dependency in core.__init__
from core.escort_ai import EscortAI, EscortAction
from core.models import Ship, UBoat, HexCoord, Facing, Depth
from core.hex_grid import HexGrid
from core.dice import DiceRoller

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


@pytest.fixture
def mock_dice():
    """Create mock dice roller."""
    return MockDice()


@pytest.fixture
def hex_grid():
    """Create hex grid for testing."""
    return HexGrid(size=30, cols=20, rows=15)


@pytest.fixture
def mission_rules():
    """Create mock mission rules."""
    return {"escort_movement": {}}  # Minimal rules for testing


@pytest.fixture
def escort_ai(mission_rules, mock_dice):
    """Create EscortAI with mock dice."""
    anchor_hex = HexCoord(10, 10)
    return EscortAI(mission_rules, mock_dice, anchor_hex)


@pytest.fixture
def destroyer():
    """Create a test destroyer."""
    return Ship(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        ship_type='destroyer',
        damaged=False
    )


@pytest.fixture
def corvette():
    """Create a test corvette."""
    return Ship(
        position=HexCoord(7, 7),
        facing=Facing.SOUTH,
        ship_type='corvette',
        damaged=False
    )


@pytest.fixture
def u_boat():
    """Create a test U-boat."""
    return UBoat(
        position=HexCoord(5, 8),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE
    )


# ===== Dice Rolling Tests =====

def test_calculate_dice_count_destroyer_undamaged(escort_ai, destroyer):
    """Destroyer undamaged rolls 3 + DL dice."""
    assert escort_ai.calculate_dice_count(destroyer, 0) == 3
    assert escort_ai.calculate_dice_count(destroyer, 1) == 4
    assert escort_ai.calculate_dice_count(destroyer, 2) == 5
    assert escort_ai.calculate_dice_count(destroyer, 3) == 6


def test_calculate_dice_count_corvette_undamaged(escort_ai, corvette):
    """Corvette undamaged rolls 2 + DL dice."""
    assert escort_ai.calculate_dice_count(corvette, 0) == 2
    assert escort_ai.calculate_dice_count(corvette, 1) == 3
    assert escort_ai.calculate_dice_count(corvette, 2) == 4
    assert escort_ai.calculate_dice_count(corvette, 3) == 5


def test_calculate_dice_count_destroyer_damaged(escort_ai, destroyer):
    """Destroyer damaged rolls only 3 dice (no DL bonus)."""
    destroyer.damaged = True
    assert escort_ai.calculate_dice_count(destroyer, 0) == 3
    assert escort_ai.calculate_dice_count(destroyer, 1) == 3
    assert escort_ai.calculate_dice_count(destroyer, 2) == 3
    assert escort_ai.calculate_dice_count(destroyer, 3) == 3


def test_calculate_dice_count_corvette_damaged(escort_ai, corvette):
    """Corvette damaged rolls only 2 dice (no DL bonus)."""
    corvette.damaged = True
    assert escort_ai.calculate_dice_count(corvette, 0) == 2
    assert escort_ai.calculate_dice_count(corvette, 1) == 2
    assert escort_ai.calculate_dice_count(corvette, 2) == 2
    assert escort_ai.calculate_dice_count(corvette, 3) == 2


def test_roll_escort_actions_returns_sorted(escort_ai, mock_dice, destroyer):
    """Action rolls are sorted lowest to highest."""
    mock_dice.set_roll_sequence([5, 2, 6, 1, 4])
    rolls = escort_ai.roll_escort_actions(destroyer, 2)
    assert rolls == [1, 2, 4, 5, 6]


def test_roll_escort_actions_correct_count(escort_ai, mock_dice, corvette):
    """Rolls correct number of dice based on ship and DL."""
    mock_dice.set_roll_sequence([1, 2, 3, 4])
    rolls = escort_ai.roll_escort_actions(corvette, 2)
    assert len(rolls) == 4  # 2 base + 2 DL


# ===== Turn Target Tests =====

def test_get_turn_target_dl_0_uses_anchor(escort_ai, destroyer, u_boat):
    """At DL 0, escorts turn toward anchor hex."""
    target = escort_ai.get_turn_target(destroyer, u_boat, 0)
    assert target == escort_ai.anchor_hex


def test_get_turn_target_dl_1_uses_anchor(escort_ai, destroyer, u_boat):
    """At DL 1, escorts turn toward anchor hex."""
    target = escort_ai.get_turn_target(destroyer, u_boat, 1)
    assert target == escort_ai.anchor_hex


def test_get_turn_target_dl_2_uses_uboat(escort_ai, destroyer, u_boat):
    """At DL 2, escorts turn toward U-boat."""
    target = escort_ai.get_turn_target(destroyer, u_boat, 2)
    assert target == u_boat.position


def test_get_turn_target_dl_3_uses_uboat(escort_ai, destroyer, u_boat):
    """At DL 3, escorts turn toward U-boat."""
    target = escort_ai.get_turn_target(destroyer, u_boat, 3)
    assert target == u_boat.position


# ===== Turn Direction Tests =====

def test_calculate_turn_direction_toward_target(escort_ai, destroyer, hex_grid):
    """Escort turns toward target hex."""
    # Destroyer at 5,5 facing NORTH, target at 5,8 (directly south)
    target = HexCoord(5, 8)
    new_facing = escort_ai.calculate_turn_direction(destroyer, target, set(), [], hex_grid)
    
    # Should turn toward south (either clockwise NE or counterclockwise NW works as a first turn)
    assert new_facing in [Facing.NORTHEAST, Facing.NORTHWEST]


def test_calculate_turn_direction_facing_target_not_blocked(escort_ai, destroyer, hex_grid):
    """Escort facing target and not blocked doesn't turn."""
    # Destroyer at 5,5 facing NORTH, target at 5,4 (directly north)
    target = HexCoord(5, 4)
    new_facing = escort_ai.calculate_turn_direction(destroyer, target, set(), [], hex_grid)
    
    # Should not turn
    assert new_facing is None


def test_calculate_turn_direction_facing_target_blocked(escort_ai, mock_dice, destroyer, hex_grid):
    """Escort facing target but blocked turns randomly."""
    mock_dice.set_roll_sequence([2])  # Roll <= 3 = counterclockwise
    
    # Destroyer at 5,5 facing NORTH, target at 5,4 (directly north), but blocked by land
    target = HexCoord(5, 4)
    land_hexes = {HexCoord(5, 4)}
    
    new_facing = escort_ai.calculate_turn_direction(destroyer, target, land_hexes, [], hex_grid)
    
    # Should turn randomly (counterclockwise in this case)
    assert new_facing == Facing.NORTHWEST


def test_calculate_turn_direction_facing_away_turns_randomly(escort_ai, mock_dice, destroyer, hex_grid):
    """Escort facing away from target turns randomly."""
    mock_dice.set_roll_sequence([5])  # Roll > 3 = clockwise
    
    # Destroyer at 5,5 facing NORTH, target at 5,8 (behind, south)
    # Angle should be ~180 degrees
    target = HexCoord(5, 8)
    new_facing = escort_ai.calculate_turn_direction(destroyer, target, set(), [], hex_grid)
    
    # Should turn clockwise
    assert new_facing == Facing.NORTHEAST


def test_calculate_turn_direction_same_hex_not_blocked(escort_ai, destroyer, hex_grid):
    """Escort in same hex as target and not blocked doesn't turn."""
    # Same position as target
    target = destroyer.position
    new_facing = escort_ai.calculate_turn_direction(destroyer, target, set(), [], hex_grid)
    
    # Should not turn
    assert new_facing is None


def test_calculate_turn_direction_same_hex_blocked(escort_ai, mock_dice, destroyer, hex_grid):
    """Escort in same hex as target and blocked turns randomly."""
    mock_dice.set_roll_sequence([1])  # Roll <= 3 = counterclockwise
    
    # Same position as target, but blocked ahead
    target = destroyer.position
    land_hexes = {HexCoord(5, 4)}  # Block forward hex
    
    new_facing = escort_ai.calculate_turn_direction(destroyer, target, land_hexes, [], hex_grid)
    
    # Should turn counterclockwise
    assert new_facing == Facing.NORTHWEST


# ===== Movement Tests =====

def test_get_next_hex_toward_target_not_blocked(escort_ai, destroyer, hex_grid):
    """Escort moves forward in facing direction if not blocked."""
    next_hex = escort_ai.get_next_hex_toward_target(destroyer, HexCoord(5, 3), set(), [], hex_grid)
    
    # Should move north (facing direction)
    assert next_hex == HexCoord(5, 4)


def test_get_next_hex_toward_target_blocked_by_land(escort_ai, destroyer, hex_grid):
    """Escort cannot move if forward hex is land."""
    land_hexes = {HexCoord(5, 4)}
    next_hex = escort_ai.get_next_hex_toward_target(destroyer, HexCoord(5, 3), land_hexes, [], hex_grid)
    
    # Cannot move
    assert next_hex is None


def test_get_next_hex_toward_target_blocked_by_ship(escort_ai, destroyer, corvette, hex_grid):
    """Escort cannot move if forward hex has another ship."""
    # Put corvette in front of destroyer
    corvette.position = HexCoord(5, 4)
    
    next_hex = escort_ai.get_next_hex_toward_target(destroyer, HexCoord(5, 3), set(), [corvette], hex_grid)
    
    # Cannot move
    assert next_hex is None


def test_get_next_hex_toward_target_blocked_off_map(escort_ai, destroyer, hex_grid):
    """Escort cannot move off map."""
    # Position at edge facing off map
    destroyer.position = HexCoord(0, 0)
    destroyer.facing = Facing.NORTH  # Would go to (0, -1)
    
    next_hex = escort_ai.get_next_hex_toward_target(destroyer, HexCoord(5, 5), set(), [], hex_grid)
    
    # Cannot move
    assert next_hex is None


# ===== Forced Dive Tests =====

def test_check_forced_dive_surfaced(escort_ai, destroyer, u_boat):
    """Moving into surfaced U-boat hex forces dive."""
    u_boat.depth = Depth.SURFACED
    
    forced, msg, destroyed = escort_ai.check_forced_dive(destroyer, u_boat, u_boat.position, set())
    
    assert forced is True
    assert "dive" in msg.lower()
    assert "MEDIUM" in msg
    assert destroyed is False


def test_check_forced_dive_periscope(escort_ai, destroyer, u_boat):
    """Moving into periscope depth U-boat hex forces dive."""
    u_boat.depth = Depth.PERISCOPE
    
    forced, msg, destroyed = escort_ai.check_forced_dive(destroyer, u_boat, u_boat.position, set())
    
    assert forced is True
    assert "dive" in msg.lower()
    assert destroyed is False


def test_check_forced_dive_medium_no_effect(escort_ai, destroyer, u_boat):
    """Moving into medium depth U-boat hex has no forced dive."""
    u_boat.depth = Depth.MEDIUM
    
    forced, msg, destroyed = escort_ai.check_forced_dive(destroyer, u_boat, u_boat.position, set())
    
    assert forced is False
    assert msg == ""
    assert destroyed is False


def test_check_forced_dive_deep_no_effect(escort_ai, destroyer, u_boat):
    """Moving into deep depth U-boat hex has no forced dive."""
    u_boat.depth = Depth.DEEP
    
    forced, msg, destroyed = escort_ai.check_forced_dive(destroyer, u_boat, u_boat.position, set())
    
    assert forced is False
    assert destroyed is False


def test_check_forced_dive_different_hex_no_effect(escort_ai, destroyer, u_boat):
    """Moving to different hex doesn't trigger forced dive."""
    forced, msg, destroyed = escort_ai.check_forced_dive(destroyer, u_boat, HexCoord(10, 10), set())
    
    assert forced is False
    assert destroyed is False


# ===== Combat Validation Tests =====

def test_can_use_fire_valid(escort_ai, destroyer, u_boat, hex_grid):
    """Escort can FIRE when conditions met."""
    u_boat.depth = Depth.SURFACED
    destroyer.position = HexCoord(5, 6)  # Range 2 from U-boat at 5,8
    
    can_fire = escort_ai.can_use_fire(destroyer, u_boat, 2, set(), hex_grid)
    
    assert can_fire is True


def test_can_use_fire_dl_too_low(escort_ai, destroyer, u_boat, hex_grid):
    """Cannot FIRE at DL 0."""
    u_boat.depth = Depth.SURFACED
    destroyer.position = HexCoord(5, 6)
    
    can_fire = escort_ai.can_use_fire(destroyer, u_boat, 0, set(), hex_grid)
    
    assert can_fire is False


def test_can_use_fire_not_surfaced(escort_ai, destroyer, u_boat, hex_grid):
    """Cannot FIRE if U-boat not surfaced."""
    u_boat.depth = Depth.PERISCOPE
    destroyer.position = HexCoord(5, 6)
    
    can_fire = escort_ai.can_use_fire(destroyer, u_boat, 2, set(), hex_grid)
    
    assert can_fire is False


def test_can_use_fire_out_of_range(escort_ai, destroyer, u_boat, hex_grid):
    """Cannot FIRE if out of range (1-3)."""
    u_boat.depth = Depth.SURFACED
    destroyer.position = HexCoord(10, 10)  # Far away
    
    can_fire = escort_ai.can_use_fire(destroyer, u_boat, 2, set(), hex_grid)
    
    assert can_fire is False


def test_can_use_fire_no_los(escort_ai, destroyer, u_boat, hex_grid):
    """Cannot FIRE if no line of sight."""
    u_boat.depth = Depth.SURFACED
    destroyer.position = HexCoord(5, 6)
    land_hexes = {HexCoord(5, 7)}  # Block LOS
    
    can_fire = escort_ai.can_use_fire(destroyer, u_boat, 2, land_hexes, hex_grid)
    
    assert can_fire is False


def test_can_use_depth_charge_valid(escort_ai, destroyer, u_boat, hex_grid):
    """Escort can use depth charge when conditions met."""
    u_boat.depth = Depth.PERISCOPE
    destroyer.position = HexCoord(5, 8)  # Same hex as U-boat
    
    can_dc = escort_ai.can_use_depth_charge(destroyer, u_boat, 2, hex_grid)
    
    assert can_dc is True


def test_can_use_depth_charge_dl_too_low(escort_ai, destroyer, u_boat, hex_grid):
    """Cannot use depth charge at DL 0."""
    u_boat.depth = Depth.PERISCOPE
    destroyer.position = HexCoord(5, 8)
    
    can_dc = escort_ai.can_use_depth_charge(destroyer, u_boat, 0, hex_grid)
    
    assert can_dc is False


def test_can_use_depth_charge_surfaced(escort_ai, destroyer, u_boat, hex_grid):
    """Cannot use depth charge if U-boat surfaced."""
    u_boat.depth = Depth.SURFACED
    destroyer.position = HexCoord(5, 8)
    
    can_dc = escort_ai.can_use_depth_charge(destroyer, u_boat, 2, hex_grid)
    
    assert can_dc is False


def test_can_use_depth_charge_out_of_range(escort_ai, destroyer, u_boat, hex_grid):
    """Cannot use depth charge if range > 1."""
    u_boat.depth = Depth.PERISCOPE
    destroyer.position = HexCoord(5, 5)  # Range 3 from U-boat
    
    can_dc = escort_ai.can_use_depth_charge(destroyer, u_boat, 2, hex_grid)
    
    assert can_dc is False


# ===== Activation Order Tests =====

def test_execute_escort_phase_activates_closest_first(escort_ai, mock_dice, destroyer, corvette, u_boat, hex_grid):
    """Escorts activate in order of distance to U-boat (closest first)."""
    # U-boat at 5,8
    # Destroyer at 5,5 (distance 3)
    # Corvette at 7,7 (distance closer - approximately 2)
    
    # Position corvette closer
    corvette.position = HexCoord(5, 7)  # Distance 1
    destroyer.position = HexCoord(5, 5)  # Distance 3
    
    mock_dice.set_roll_sequence([1, 2, 3, 4, 5, 6])  # Enough for both ships
    
    ships = [destroyer, corvette]
    current_dl, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # Check that corvette (closer) activated before destroyer
    corvette_msg_idx = next(i for i, m in enumerate(messages) if 'CORVETTE' in m)
    destroyer_msg_idx = next(i for i, m in enumerate(messages) if 'DESTROYER' in m)
    
    assert corvette_msg_idx < destroyer_msg_idx


def test_execute_escort_phase_ignores_merchants(escort_ai, mock_dice, u_boat, hex_grid):
    """Merchant ships are not activated in escort phase."""
    merchant = Ship(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        ship_type='merchant',
        damaged=False
    )
    
    mock_dice.set_roll_sequence([1, 2, 3])
    
    ships = [merchant]
    current_dl, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # Should have no activations
    assert len([m for m in messages if 'activates' in m]) == 0


def test_execute_escort_phase_no_escorts(escort_ai, u_boat, hex_grid):
    """Phase completes with message if no escorts on map."""
    ships: list[Ship] = []
    
    current_dl, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    assert any('no escorts' in m.lower() for m in messages)
    assert current_dl == 1  # DL unchanged


# ===== Integration Tests =====

def test_execute_escort_phase_full_activation(escort_ai, mock_dice, destroyer, u_boat, hex_grid):
    """Full escort activation with movement and turning."""
    # Position destroyer south of U-boat, facing north
    destroyer.position = HexCoord(5, 10)
    destroyer.facing = Facing.NORTH
    u_boat.position = HexCoord(5, 5)
    
    # Destroyer rolls 4 dice at DL 1: results 2, 3, 4, 5
    # 2 = MOVE (blocked -> TURN)
    # 3 = MOVE
    # 4 = MOVE (blocked -> TURN)
    # 5 = TURN
    mock_dice.set_roll_sequence([2, 3, 4, 5])
    
    ships = [destroyer]
    current_dl, messages = escort_ai.execute_escort_phase(ships, u_boat, 1, set(), hex_grid)
    
    # Destroyer should have moved toward U-boat
    assert destroyer.position != HexCoord(5, 10)  # Moved from start position
    assert len(messages) > 0


def test_execute_escort_phase_forced_dive(escort_ai, mock_dice, destroyer, u_boat, hex_grid):
    """Escort moving into U-boat hex triggers forced dive."""
    # Position destroyer adjacent to surfaced U-boat
    u_boat.position = HexCoord(5, 4)  # U-boat position
    u_boat.depth = Depth.SURFACED
    
    destroyer.position = HexCoord(5, 5)  # Destroyer starts one hex south
    destroyer.facing = Facing.NORTH  # Facing toward U-boat
    
    # Roll single die result that causes one move
    # With DL 0, destroyer rolls 3 dice
    # Use die result 1 which is FIRE (but can't fire at DL 0) x3
    # Actually, let's just verify the forced dive logic works independently
    # by using a minimal test case with DL 1 so we get fewer dice
    
    # Better: test with corvette at DL 0 (only 2 dice)
    corvette = Ship(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        ship_type='corvette',
        damaged=False
    )
    
    # Roll [2, 1]: 
    # Die 1 (result 2): MOVE into U-boat hex, triggers forced dive (DL 0->1), then depth charge
    # Die 2 (result 1): FIRE/DEPTH CHARGE only (no additional movement)
    # Need to provide dice for damage rolls from depth charges: [2, dmg1, dmg2, 1, dmg3, dmg4]
    mock_dice.set_roll_sequence([2, 4, 4, 1, 3, 3])
    
    ships = [corvette]
    current_dl, messages = escort_ai.execute_escort_phase(ships, u_boat, 0, set(), hex_grid)
    
    # Corvette should have moved into U-boat hex and stayed there
    assert corvette.position == u_boat.position, f"Expected corvette at {u_boat.position}, got {corvette.position}"
    
    # U-boat should be forced to medium depth
    assert u_boat.depth == Depth.MEDIUM, f"Expected depth MEDIUM, got {u_boat.depth}"
    
    # DL should increase by 1 from forced dive
    assert current_dl == 1, f"Expected DL 1, got {current_dl}"
    
    # Should have forced dive message
    assert any('dive' in m.lower() for m in messages), f"No dive message in: {messages}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
