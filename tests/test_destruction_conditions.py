"""Test the two new destruction conditions: forced dive in shallow water and ship blocking forced ascent."""

from typing import List, Dict, Any, Set
import pytest
from core.models import UBoat, Ship, Depth, Facing, HexCoord
from core.escort_ai import EscortAI
from core.damage.uboat_damage import UBoatDamageResolver
from core.dice import DiceRoller


class MockDice(DiceRoller):
    """Mock dice roller that returns predetermined values."""
    
    def __init__(self) -> None:
        self.roll_sequence: List[int] = []
        self.roll_index: int = 0
    
    def set_roll_sequence(self, rolls: List[int]) -> None:
        """Set sequence of rolls to return."""
        self.roll_sequence = rolls
        self.roll_index = 0
    
    def roll_1d6(self, context: str = "") -> int:
        """Return next roll in sequence."""
        if self.roll_index >= len(self.roll_sequence):
            return 4  # Default value
        
        result = self.roll_sequence[self.roll_index]
        self.roll_index += 1
        return result


@pytest.fixture
def mock_dice() -> MockDice:
    """Create a mock dice roller."""
    return MockDice()


@pytest.fixture
def mission_rules() -> Dict[str, Any]:
    """Create mock mission rules."""
    return {"escort_movement": {}}  # Minimal rules for testing


@pytest.fixture
def escort_ai(mission_rules: Dict[str, Any], mock_dice: MockDice) -> EscortAI:
    """Create an EscortAI instance with mock dice."""
    anchor_hex = HexCoord(10, 10)
    return EscortAI(mission_rules, mock_dice, anchor_hex)


@pytest.fixture
def u_boat() -> UBoat:
    """Create a test U-boat."""
    return UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE,
        action_points=0
    )


@pytest.fixture
def destroyer() -> Ship:
    """Create a test destroyer."""
    return Ship(
        position=HexCoord(5, 6),
        facing=Facing.NORTH,
        ship_type='destroyer',
        damaged=False
    )


def test_forced_dive_in_shallow_water_destroys_uboat(escort_ai: EscortAI, destroyer: Ship, u_boat: UBoat) -> None:
    """Test that forcing U-boat to dive in shallow water at periscope depth destroys it."""
    # U-boat at periscope depth
    u_boat.depth = Depth.PERISCOPE
    u_boat.position = HexCoord(3, 3)
    
    # Shallow hex at U-boat position
    shallow_hexes = {HexCoord(3, 3)}
    
    # Escort moves into U-boat hex - should force dive
    forced, msg, destroyed = escort_ai.check_forced_dive(
        destroyer, u_boat, u_boat.position, shallow_hexes
    )
    
    assert forced is True
    assert destroyed is True
    assert "DESTROYED" in msg
    assert "shallow water" in msg.lower()


def test_forced_dive_in_deep_water_does_not_destroy(escort_ai: EscortAI, destroyer: Ship, u_boat: UBoat) -> None:
    """Test that forcing U-boat to dive in deep water does not destroy it."""
    # U-boat at periscope depth
    u_boat.depth = Depth.PERISCOPE
    u_boat.position = HexCoord(3, 3)
    
    # No shallow hexes - all deep water
    shallow_hexes: Set[HexCoord] = set()
    
    # Escort moves into U-boat hex - should force dive but not destroy
    forced, msg, destroyed = escort_ai.check_forced_dive(
        destroyer, u_boat, u_boat.position, shallow_hexes
    )
    
    assert forced is True
    assert destroyed is False
    assert "DESTROYED" not in msg
    assert "shallow" not in msg.lower()


def test_forced_dive_at_surfaced_in_shallow_does_not_destroy(escort_ai: EscortAI, destroyer: Ship, u_boat: UBoat) -> None:
    """Test that forcing U-boat to dive from surfaced depth in shallow water does not destroy it."""
    # U-boat at surfaced depth
    u_boat.depth = Depth.SURFACED
    u_boat.position = HexCoord(3, 3)
    
    # Shallow hex at U-boat position
    shallow_hexes = {HexCoord(3, 3)}
    
    # Escort moves into U-boat hex - should force dive but not destroy (surfaced -> medium is ok)
    forced, msg, destroyed = escort_ai.check_forced_dive(
        destroyer, u_boat, u_boat.position, shallow_hexes
    )
    
    assert forced is True
    assert destroyed is False
    assert "DESTROYED" not in msg


def test_ship_blocks_forced_ascent_after_hull_damage(mock_dice: MockDice, u_boat: UBoat, destroyer: Ship) -> None:
    """Test that ship in same hex destroys U-boat when it must ascend due to hull damage."""
    # U-boat at medium depth with no damage
    u_boat.depth = Depth.MEDIUM
    u_boat.hull_damage = 0
    u_boat.position = HexCoord(5, 5)
    
    # Ship in same hex as U-boat
    destroyer.position = HexCoord(5, 5)
    ships = [destroyer]
    
    # Set mock dice to roll a critical hit (1) then roll for hull damage (+2 hull damage)
    # Critical roll: 1 = critical hit
    # Crit sub-roll: 2 = +2 hull damage
    mock_dice.set_roll_sequence([1, 2])
    
    # Create damage resolver
    damage_resolver = UBoatDamageResolver(dice=mock_dice)
    
    # Apply depth charge damage
    result = damage_resolver.apply_escort_attack_damage(
        u_boat, attack_type="depth_charge", ship_type="corvette", ships=ships
    )
    
    # U-boat should be destroyed because:
    # 1. Hull damage went from 0 to 2
    # 2. At 2 hull damage, max depth is PERISCOPE
    # 3. U-boat is at MEDIUM depth (deeper than allowed)
    # 4. Ship is in same hex, blocking forced ascent
    assert result.is_destroyed is True
    assert u_boat.hull_damage == 4
    assert "blocks forced ascent" in result.description.lower()
    assert "DESTROYED" in result.description


def test_forced_ascent_not_blocked_when_no_ship_in_hex(mock_dice: MockDice, u_boat: UBoat, destroyer: Ship) -> None:
    """Test that forced ascent succeeds when no ship blocks it."""
    # U-boat at medium depth with no damage
    u_boat.depth = Depth.MEDIUM
    u_boat.hull_damage = 0
    u_boat.position = HexCoord(5, 5)
    
    # Ship in different hex (not blocking)
    destroyer.position = HexCoord(6, 6)
    ships = [destroyer]
    
    # Set mock dice to roll a critical hit (1) then roll for hull damage (+2 hull damage)
    mock_dice.set_roll_sequence([1, 2])
    
    # Create damage resolver
    damage_resolver = UBoatDamageResolver(dice=mock_dice)
    
    # Apply depth charge damage
    result = damage_resolver.apply_escort_attack_damage(
        u_boat, attack_type="depth_charge", ship_type="corvette", ships=ships
    )
    
    # U-boat should NOT be destroyed because ship is not blocking
    assert result.is_destroyed is False
    assert u_boat.hull_damage == 2
    assert "blocks" not in result.description.lower()
    assert "DESTROYED" not in result.description


def test_no_forced_ascent_when_depth_is_allowed(mock_dice: MockDice, u_boat: UBoat, destroyer: Ship) -> None:
    """Test that no forced ascent check when U-boat depth is within limits."""
    # U-boat at periscope depth with no damage
    u_boat.depth = Depth.PERISCOPE
    u_boat.hull_damage = 0
    u_boat.position = HexCoord(5, 5)
    
    # Ship in same hex
    destroyer.position = HexCoord(5, 5)
    ships = [destroyer]
    
    # Set mock dice to roll a critical hit (1) then roll for hull damage (+1 hull damage)
    # This gives 1 hull damage, which allows PERISCOPE depth
    mock_dice.set_roll_sequence([1, 2])  # Crit, +2 hull damage
    
    # Create damage resolver
    damage_resolver = UBoatDamageResolver(dice=mock_dice)
    
    # Apply depth charge damage
    result = damage_resolver.apply_escort_attack_damage(
        u_boat, attack_type="depth_charge", ship_type="corvette", ships=ships
    )
    
    # U-boat at 2 hull damage can only be at PERISCOPE or SURFACED
    # Since it's at PERISCOPE, no forced ascent needed
    # But wait - with 2 hull damage, max is PERISCOPE, and we're at PERISCOPE, so it's OK
    # Ship shouldn't destroy it
    assert result.is_destroyed is False
    assert u_boat.hull_damage == 2


def test_ship_blocks_ascent_from_deep(mock_dice: MockDice, u_boat: UBoat, destroyer: Ship) -> None:
    """Test ship blocking ascent from deep depth."""
    # U-boat at deep depth with 1 hull damage (max allowed is MEDIUM)
    u_boat.depth = Depth.DEEP
    u_boat.hull_damage = 1
    u_boat.position = HexCoord(5, 5)
    
    # Ship in same hex
    destroyer.position = HexCoord(5, 5)
    ships = [destroyer]
    
    # Apply damage that will increase hull damage to 2 (max PERISCOPE)
    # U-boat at DEEP needs to ascend to PERISCOPE, but ship blocks it
    # Roll general damage (3-4 on chart), then roll for +1 hull damage (1 on damage sub-roll)
    mock_dice.set_roll_sequence([3, 1])  # Chart 3-4, then +1 hull
    
    # Create damage resolver
    damage_resolver = UBoatDamageResolver(dice=mock_dice)
    
    # Apply depth charge damage
    result = damage_resolver.apply_escort_attack_damage(
        u_boat, attack_type="depth_charge", ship_type="corvette", ships=ships
    )
    
    # U-boat should be destroyed:
    # - Started at 1 hull damage (max MEDIUM), at DEEP depth
    # - Took +1 hull damage -> 2 total (max PERISCOPE)
    # - Now at DEEP, needs to ascend to PERISCOPE
    # - Ship blocks ascent -> destroyed
    assert result.is_destroyed is True
    assert u_boat.hull_damage == 4
    assert "blocks forced ascent" in result.description.lower()
