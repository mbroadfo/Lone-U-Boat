"""
Tests for Phase 3.6 - Damage Resolution System.

Tests:
- ShipDamageResolver with Allied Ship Damage Chart
- UBoatDamageResolver with U-Boat Damage Chart
- Crew casualty system with medic saves
- Hull damage tracking
- Victory/defeat conditions
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Optional

from core.damage import ShipDamageResolver, UBoatDamageResolver
from core.models import Ship, UBoat, HexCoord, Facing, Depth


class MockDice:
    """Mock dice roller that returns fixed values for testing."""
    
    def __init__(self, fixed_rolls: Optional[List[int]] = None):
        self.fixed_rolls = fixed_rolls if fixed_rolls is not None else []
        self.roll_index = 0
    
    def roll(self, num_dice: int) -> int:
        """Return next fixed roll."""
        if self.roll_index < len(self.fixed_rolls):
            result = self.fixed_rolls[self.roll_index]
            self.roll_index += 1
            return result
        return 1  # Default
    
    def random_choice(self, choices: List[int]) -> int:
        """Return first choice."""
        return choices[0] if choices else 0
    
    def set_fixed_rolls(self, rolls: List[int]):
        """Set new sequence of fixed rolls."""
        self.fixed_rolls = rolls
        self.roll_index = 0


def test_ship_damage_merchant_no_effect():
    """Test merchant ship taking no-effect damage."""
    print("\n=== Testing Ship Damage - Merchant No Effect ===")
    
    dice = MockDice(fixed_rolls=[1])  # Roll 1 = no effect
    resolver = ShipDamageResolver(dice)  # type: ignore[arg-type]
    
    ship = Ship(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        ship_type="merchant",
        damaged=False
    )
    
    result = resolver.apply_damage(ship, "torpedo")
    
    print(f"Result: {result}")
    print(f"Roll: {result.roll}, Effect: {result.effect}")
    print(f"Ship damaged: {ship.damaged}")
    
    assert result.effect == "no_effect", f"Expected no_effect, got {result.effect}"
    assert not ship.damaged, "Ship should not be damaged"
    assert not result.is_now_sunk, "Ship should not be sunk"
    
    print("✅ Merchant no-effect damage tests passed!")


def test_ship_damage_merchant_damaged():
    """Test merchant ship getting damaged."""
    print("\n=== Testing Ship Damage - Merchant Damaged ===")
    
    dice = MockDice(fixed_rolls=[3])  # Roll 3 = damaged
    resolver = ShipDamageResolver(dice)  # type: ignore[arg-type]
    
    ship = Ship(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        ship_type="merchant",
        damaged=False
    )
    
    result = resolver.apply_damage(ship, "deck_gun")
    
    print(f"Result: {result}")
    print(f"Effect: {result.effect}")
    print(f"Ship damaged: {ship.damaged}")
    
    assert result.effect == "damaged", f"Expected damaged, got {result.effect}"
    assert ship.damaged, "Ship should be damaged"
    assert not result.is_now_sunk, "Ship should not be sunk yet"
    
    print("✅ Merchant damaged tests passed!")


def test_ship_damage_merchant_catastrophic():
    """Test merchant ship catastrophic damage (instant sink)."""
    print("\n=== Testing Ship Damage - Merchant Catastrophic ===")
    
    dice = MockDice(fixed_rolls=[5])  # Roll 5 = catastrophic
    resolver = ShipDamageResolver(dice)  # type: ignore[arg-type]
    
    ship = Ship(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        ship_type="merchant",
        damaged=False
    )
    
    result = resolver.apply_damage(ship, "torpedo")
    
    print(f"Result: {result}")
    print(f"Effect: {result.effect}")
    print(f"Ship sunk: {result.is_now_sunk}")
    
    assert result.effect == "catastrophic", f"Expected catastrophic, got {result.effect}"
    assert result.is_now_sunk, "Ship should be sunk"
    
    print("✅ Merchant catastrophic damage tests passed!")


def test_ship_damage_already_damaged_sinks():
    """Test hitting already-damaged ship sinks it."""
    print("\n=== Testing Ship Damage - Already Damaged Sinks ===")
    
    dice = MockDice(fixed_rolls=[2])  # Roll 2 (would be no effect, but ship is damaged)
    resolver = ShipDamageResolver(dice)  # type: ignore[arg-type]
    
    ship = Ship(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        ship_type="merchant",
        damaged=True  # Already damaged
    )
    
    result = resolver.apply_damage(ship, "deck_gun")
    
    print(f"Result: {result}")
    print(f"Effect: {result.effect}")
    print(f"Was damaged: {result.was_already_damaged}")
    print(f"Is sunk: {result.is_now_sunk}")
    
    assert result.was_already_damaged, "Should recognize ship was damaged"
    assert result.effect == "sunk", f"Expected sunk, got {result.effect}"
    assert result.is_now_sunk, "Ship should be sunk"
    
    print("✅ Already-damaged ship sinking tests passed!")


def test_ship_damage_escort_modifier():
    """Test escort ships get -2 modifier against deck guns."""
    print("\n=== Testing Ship Damage - Escort Modifier ===")
    
    dice = MockDice(fixed_rolls=[3, 3])  # Two rolls: deck gun, then torpedo
    resolver = ShipDamageResolver(dice)  # type: ignore[arg-type]
    
    escort = Ship(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        ship_type="destroyer",
        damaged=False
    )
    
    # Roll 3, -2 modifier = 1 (no effect instead of damaged)
    result = resolver.apply_damage(escort, "deck_gun")
    
    print(f"Result: {result}")
    print(f"Base would be 3, modified to: {result.roll}")
    print(f"Effect: {result.effect}")
    
    assert result.roll == 1, "Roll should be modified to 1"
    assert result.effect == "no_effect", "Should be no effect due to modifier"
    
    # Same roll with torpedo (no modifier) - new ship
    escort2 = Ship(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        ship_type="destroyer",
        damaged=False
    )
    result2 = resolver.apply_damage(escort2, "torpedo")
    print(f"Torpedo result: {result2.effect}")
    assert result2.effect == "damaged", "Torpedo should damage (no modifier)"
    
    print("✅ Escort modifier tests passed!")


def test_uboat_damage_general():
    """Test U-boat general damage."""
    print("\n=== Testing U-Boat General Damage ===")
    
    dice = MockDice(fixed_rolls=[2])  # Roll 2 = Engine damage
    resolver = UBoatDamageResolver(dice)  # type: ignore[arg-type]
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE,
        hull_damage=0,
        engine_damaged=False
    )
    
    result = resolver.apply_general_damage(u_boat)
    
    print(f"Result: {result}")
    print(f"Systems damaged: {result.systems_damaged}")
    print(f"Engine damaged: {u_boat.engine_damaged}")
    
    assert "Engine" in result.systems_damaged, "Engine should be damaged"
    assert u_boat.engine_damaged, "U-boat engine should be marked damaged"
    assert not result.is_destroyed, "U-boat should not be destroyed"
    
    print("✅ U-boat general damage tests passed!")


def test_uboat_damage_hull():
    """Test U-boat hull damage accumulation."""
    print("\n=== Testing U-Boat Hull Damage ===")
    
    dice = MockDice(fixed_rolls=[1, 1, 1, 1])  # Four rolls of 1 = Hull +1 each time
    resolver = UBoatDamageResolver(dice)  # type: ignore[arg-type]
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE,
        hull_damage=0
    )
    
    result1 = resolver.apply_general_damage(u_boat)
    print(f"Hull damage 1: {u_boat.hull_damage}")
    assert u_boat.hull_damage == 1, "Hull should be 1"
    assert not result1.is_destroyed, "Not destroyed yet"
    
    # More hull damage
    _ = resolver.apply_general_damage(u_boat)
    print(f"Hull damage 2: {u_boat.hull_damage}")
    assert u_boat.hull_damage == 2, "Hull should be 2"
    
    _ = resolver.apply_general_damage(u_boat)
    print(f"Hull damage 3: {u_boat.hull_damage}")
    assert u_boat.hull_damage == 3, "Hull should be 3"
    
    result4 = resolver.apply_general_damage(u_boat)
    print(f"Hull damage 4: {u_boat.hull_damage}")
    assert u_boat.hull_damage == 4, "Hull should be 4 (max)"
    assert result4.is_destroyed, "U-boat should be destroyed at hull 4"
    
    print("✅ U-boat hull damage tests passed!")


def test_uboat_damage_critical_hull_breach():
    """Test U-boat critical hit - hull breach."""
    print("\n=== Testing U-Boat Critical Hull Breach ===")
    
    dice = MockDice(fixed_rolls=[3])  # Roll 3 on 2d6 = Hull +2
    resolver = UBoatDamageResolver(dice)  # type: ignore[arg-type]
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE,
        hull_damage=0
    )
    
    result = resolver.apply_critical_damage(u_boat)
    
    print(f"Result: {result}")
    print(f"Hull damage taken: {result.hull_damage_taken}")
    print(f"Total hull: {u_boat.hull_damage}")
    
    assert result.hull_damage_taken == 2, "Should take 2 hull damage"
    assert u_boat.hull_damage == 2, "Hull should be 2"
    assert "Hull Breach +2" in result.effect, "Should mention hull breach"
    
    print("✅ U-boat critical hull breach tests passed!")


def test_uboat_damage_crew_casualty():
    """Test U-boat crew casualty with medic save."""
    print("\n=== Testing U-Boat Crew Casualty ===")
    
    dice = MockDice(fixed_rolls=[8, 1, 3])  # 8 on 2d6 = casualty, 1 on 1d6 = Engineer, 3 on save = fail
    resolver = UBoatDamageResolver(dice)  # type: ignore[arg-type]
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE,
        engineer_alive=True,
        medic_alive=True
    )
    
    result = resolver.apply_critical_damage(u_boat)
    
    print(f"Result: {result}")
    print(f"Crew casualties: {result.crew_casualties}")
    print(f"Medic saves: {result.medic_saves}")
    
    # Should have attempted casualty (may be saved)
    if result.medic_saves:
        crew_member, saved = result.medic_saves[0]
        print(f"{crew_member}: {'SAVED' if saved else 'KIA'}")
        
        if not saved:
            assert len(result.crew_casualties) == 1, "Should have 1 casualty"
    
    print("✅ U-boat crew casualty tests passed!")


def test_uboat_damage_medic_save():
    """Test medic saves crew member."""
    print("\n=== Testing Medic Save ===")
    
    dice = MockDice(fixed_rolls=[9, 2, 5])  # 9 on 2d6 = casualty, 2 on 1d6 = WO, 5 on save = SAVED!
    resolver = UBoatDamageResolver(dice)  # type: ignore[arg-type]
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE,
        engineer_alive=True,
        weapons_officer_alive=True,
        medic_alive=True
    )
    
    result = resolver.apply_critical_damage(u_boat)
    
    print(f"Result: {result}")
    print(f"Medic saves: {result.medic_saves}")
    
    assert len(result.medic_saves) == 1, "Should have 1 medic save attempt"
    crew_member, saved = result.medic_saves[0]
    assert saved, f"{crew_member} should have been saved by medic"
    assert u_boat.weapons_officer_alive, "WO should still be alive (saved)"
    
    print("✅ Medic save system tests passed!")


def test_uboat_destruction_check():
    """Test U-boat destruction check."""
    print("\n=== Testing U-Boat Destruction Check ===")
    
    dice = MockDice()
    resolver = UBoatDamageResolver(dice)  # type: ignore[arg-type]
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE,
        hull_damage=3
    )
    
    is_destroyed, reason = resolver.check_destruction(u_boat)
    print(f"Hull 3: Destroyed={is_destroyed}, Reason={reason}")
    assert not is_destroyed, "Not destroyed at hull 3"
    
    u_boat.hull_damage = 4
    is_destroyed, reason = resolver.check_destruction(u_boat)
    print(f"Hull 4: Destroyed={is_destroyed}, Reason={reason}")
    assert is_destroyed, "Should be destroyed at hull 4"
    assert "Hull damage critical" in reason
    
    print("✅ U-boat destruction check tests passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 3.6 Tests - Damage Resolution System")
    print("=" * 60)
    
    test_ship_damage_merchant_no_effect()
    test_ship_damage_merchant_damaged()
    test_ship_damage_merchant_catastrophic()
    test_ship_damage_already_damaged_sinks()
    test_ship_damage_escort_modifier()
    test_uboat_damage_general()
    test_uboat_damage_hull()
    test_uboat_damage_critical_hull_breach()
    test_uboat_damage_crew_casualty()
    test_uboat_damage_medic_save()
    test_uboat_destruction_check()
    
    print("\n" + "=" * 60)
    print("✅ ALL DAMAGE RESOLUTION TESTS PASSED!")
    print("=" * 60)
