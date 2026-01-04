"""
Tests for DepthValidator (Phase 2.5).

Run with: python test_depth_validator.py
"""

import sys
sys.path.insert(0, '.')

from core.depth_validator import DepthValidator
from core.models import HexCoord, UBoat, Ship, Depth, Facing


def test_once_per_turn_limit():
    """Test that depth can only change once per turn."""
    print("\n=== Testing Once Per Turn Limit ===")
    
    validator = DepthValidator(shallow_hexes=set())
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED
    )
    
    # First change: should be allowed
    can_change, reason = validator.can_change_depth(
        u_boat, Depth.PERISCOPE, HexCoord(5, 5), ships=[], depth_changed_this_turn=False
    )
    print(f"First change (Surfaced → Periscope): can_change={can_change}")
    assert can_change, "First depth change should be allowed"
    
    # Second change: should be blocked
    can_change, reason = validator.can_change_depth(
        u_boat, Depth.PERISCOPE, HexCoord(5, 5), ships=[], depth_changed_this_turn=True
    )
    print(f"Second change (blocked): can_change={can_change}, reason='{reason}'")
    assert not can_change, "Second depth change should be blocked"
    assert "once per turn" in reason.lower(), "Reason should mention once per turn limit"
    
    print("✅ Once per turn limit tests passed!\n")


def test_one_level_at_a_time():
    """Test that depth can only change one level at a time."""
    print("\n=== Testing One Level at a Time ===")
    
    validator = DepthValidator(shallow_hexes=set())
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED
    )
    
    # Adjacent level: should be allowed
    can_change, reason = validator.can_change_depth(
        u_boat, Depth.PERISCOPE, HexCoord(5, 5), ships=[], depth_changed_this_turn=False
    )
    print(f"Adjacent (Surfaced → Periscope): can_change={can_change}")
    assert can_change, "Adjacent level should be allowed"
    
    # Skip level: should be blocked
    can_change, reason = validator.can_change_depth(
        u_boat, Depth.MEDIUM, HexCoord(5, 5), ships=[], depth_changed_this_turn=False
    )
    print(f"Skip level (Surfaced → Medium): can_change={can_change}, reason='{reason}'")
    assert not can_change, "Skipping level should be blocked"
    assert "one level at a time" in reason.lower(), "Reason should mention one level limit"
    
    # Skip two levels: should be blocked
    can_change, reason = validator.can_change_depth(
        u_boat, Depth.DEEP, HexCoord(5, 5), ships=[], depth_changed_this_turn=False
    )
    print(f"Skip two (Surfaced → Deep): can_change={can_change}, reason='{reason}'")
    assert not can_change, "Skipping two levels should be blocked"
    
    print("✅ One level at a time tests passed!\n")


def test_shallow_water_restrictions():
    """Test shallow water depth limits."""
    print("\n=== Testing Shallow Water Restrictions ===")
    
    shallow_hexes = {HexCoord(3, 3)}
    validator = DepthValidator(shallow_hexes)
    
    u_boat = UBoat(
        position=HexCoord(3, 3),
        facing=Facing.NORTH,
        depth=Depth.SURFACED
    )
    
    # Surfaced → Periscope: allowed in shallow
    can_change, reason = validator.can_change_depth(
        u_boat, Depth.PERISCOPE, HexCoord(3, 3), ships=[], depth_changed_this_turn=False
    )
    print(f"Surfaced → Periscope (shallow): can_change={can_change}")
    assert can_change, "Periscope should be allowed in shallow water"
    
    # Periscope → Medium: blocked in shallow
    u_boat.depth = Depth.PERISCOPE
    can_change, reason = validator.can_change_depth(
        u_boat, Depth.MEDIUM, HexCoord(3, 3), ships=[], depth_changed_this_turn=False
    )
    print(f"Periscope → Medium (shallow): can_change={can_change}, reason='{reason}'")
    assert not can_change, "Medium should be blocked in shallow water"
    assert "shallow water" in reason.lower(), "Reason should mention shallow water"
    assert "Periscope" in reason, "Reason should mention max depth"
    
    # Deep water: should allow deeper
    can_change, reason = validator.can_change_depth(
        u_boat, Depth.MEDIUM, HexCoord(5, 5), ships=[], depth_changed_this_turn=False
    )
    print(f"Periscope → Medium (deep water): can_change={can_change}")
    assert can_change, "Medium should be allowed in deep water"
    
    print("✅ Shallow water tests passed!\n")


def test_ship_overhead_restrictions():
    """Test ship overhead depth limits."""
    print("\n=== Testing Ship Overhead Restrictions ===")
    
    validator = DepthValidator(shallow_hexes=set())
    
    hex_pos = HexCoord(5, 5)
    ships = [
        Ship(position=hex_pos, facing=Facing.NORTH, ship_type="Merchant")
    ]
    
    u_boat = UBoat(
        position=hex_pos,
        facing=Facing.NORTH,
        depth=Depth.DEEP
    )
    
    # Deep → Medium: allowed under ship
    can_change, reason = validator.can_change_depth(
        u_boat, Depth.MEDIUM, hex_pos, ships, depth_changed_this_turn=False
    )
    print(f"Deep → Medium (under ship): can_change={can_change}")
    assert can_change, "Medium should be allowed under ship"
    
    # Medium → Periscope: blocked under ship
    u_boat.depth = Depth.MEDIUM
    can_change, reason = validator.can_change_depth(
        u_boat, Depth.PERISCOPE, hex_pos, ships, depth_changed_this_turn=False
    )
    print(f"Medium → Periscope (under ship): can_change={can_change}, reason='{reason}'")
    assert not can_change, "Periscope should be blocked under ship"
    assert "ship overhead" in reason.lower(), "Reason should mention ship overhead"
    
    # Medium → Surfaced: also blocked under ship
    can_change, reason = validator.can_change_depth(
        u_boat, Depth.SURFACED, hex_pos, ships, depth_changed_this_turn=False
    )
    print(f"Medium → Surfaced (under ship): can_change={can_change}, reason='{reason}'")
    assert not can_change, "Surfaced should be blocked under ship"
    
    # No ship: should allow surfacing
    can_change, reason = validator.can_change_depth(
        u_boat, Depth.PERISCOPE, HexCoord(6, 6), ships=[], depth_changed_this_turn=False
    )
    print(f"Medium → Periscope (no ship): can_change={can_change}")
    assert can_change, "Periscope should be allowed with no ship"
    
    print("✅ Ship overhead tests passed!\n")


def test_hull_damage_limits():
    """Test hull damage depth restrictions."""
    print("\n=== Testing Hull Damage Limits ===")
    
    validator = DepthValidator(shallow_hexes=set())
    hex_pos = HexCoord(5, 5)
    
    # No damage: all depths allowed
    print("\n0 Hull Damage:")
    u_boat = UBoat(
        position=hex_pos,
        facing=Facing.NORTH,
        depth=Depth.MEDIUM,
        hull_damage=0
    )
    max_depth = validator.max_depth_for_hull_damage(0)
    print(f"  Max depth: {max_depth.name}")
    assert max_depth == Depth.DEEP, "No damage should allow Deep"
    
    can_change, _ = validator.can_change_depth(
        u_boat, Depth.DEEP, hex_pos, ships=[], depth_changed_this_turn=False
    )
    print(f"  Medium → Deep: {can_change}")
    assert can_change, "Should allow Deep with no damage"
    
    # 1 damage: max Medium
    print("\n1 Hull Damage:")
    u_boat.hull_damage = 1
    u_boat.depth = Depth.MEDIUM
    max_depth = validator.max_depth_for_hull_damage(1)
    print(f"  Max depth: {max_depth.name}")
    assert max_depth == Depth.MEDIUM, "1 damage should limit to Medium"
    
    can_change, reason = validator.can_change_depth(
        u_boat, Depth.DEEP, hex_pos, ships=[], depth_changed_this_turn=False
    )
    print(f"  Medium → Deep: {can_change}, reason='{reason}'")
    assert not can_change, "Should block Deep with 1 damage"
    assert "Hull damage" in reason, "Reason should mention hull damage"
    
    # 2 damage: max Periscope
    print("\n2 Hull Damage:")
    u_boat.hull_damage = 2
    u_boat.depth = Depth.PERISCOPE
    max_depth = validator.max_depth_for_hull_damage(2)
    print(f"  Max depth: {max_depth.name}")
    assert max_depth == Depth.PERISCOPE, "2 damage should limit to Periscope"
    
    can_change, reason = validator.can_change_depth(
        u_boat, Depth.MEDIUM, hex_pos, ships=[], depth_changed_this_turn=False
    )
    print(f"  Periscope → Medium: {can_change}, reason='{reason}'")
    assert not can_change, "Should block Medium with 2 damage"
    
    # 3+ damage: must stay Surfaced
    print("\n3 Hull Damage:")
    u_boat.hull_damage = 3
    u_boat.depth = Depth.SURFACED
    max_depth = validator.max_depth_for_hull_damage(3)
    print(f"  Max depth: {max_depth.name}")
    assert max_depth == Depth.SURFACED, "3+ damage should force Surfaced"
    
    can_change, reason = validator.can_change_depth(
        u_boat, Depth.PERISCOPE, hex_pos, ships=[], depth_changed_this_turn=False
    )
    print(f"  Surfaced → Periscope: {can_change}, reason='{reason}'")
    assert not can_change, "Should block any dive with 3 damage"
    
    print("✅ Hull damage tests passed!\n")


def test_get_valid_depths():
    """Test getting all valid depth options."""
    print("\n=== Testing Get Valid Depths ===")
    
    validator = DepthValidator(shallow_hexes=set())
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE
    )
    
    # From Periscope with no restrictions
    valid = validator.get_valid_depths(
        u_boat, HexCoord(5, 5), ships=[], depth_changed_this_turn=False
    )
    print(f"Valid depths from Periscope (no restrictions): {[d.name for d in valid]}")
    assert Depth.SURFACED in valid, "Should allow Surfaced"
    assert Depth.MEDIUM in valid, "Should allow Medium"
    assert Depth.DEEP not in valid, "Should not allow Deep (two levels)"
    assert Depth.PERISCOPE not in valid, "Should not include current depth"
    
    # Already changed this turn
    valid = validator.get_valid_depths(
        u_boat, HexCoord(5, 5), ships=[], depth_changed_this_turn=True
    )
    print(f"Valid depths (already changed): {[d.name for d in valid]}")
    assert len(valid) == 0, "Should have no valid options after changing"
    
    # With hull damage
    u_boat.hull_damage = 2
    u_boat.depth = Depth.SURFACED
    valid = validator.get_valid_depths(
        u_boat, HexCoord(5, 5), ships=[], depth_changed_this_turn=False
    )
    print(f"Valid depths from Surfaced (2 hull dmg): {[d.name for d in valid]}")
    assert Depth.PERISCOPE in valid, "Should allow Periscope"
    assert Depth.MEDIUM not in valid, "Should block Medium (hull damage)"
    
    print("✅ Get valid depths tests passed!\n")


def test_complex_scenario():
    """Test complex scenario with multiple restrictions."""
    print("\n=== Testing Complex Scenario ===")
    
    shallow_hexes = {HexCoord(3, 3)}
    validator = DepthValidator(shallow_hexes)
    
    # Scenario: In shallow water, 1 hull damage, ship overhead
    hex_pos = HexCoord(3, 3)
    ships = [
        Ship(position=hex_pos, facing=Facing.NORTH, ship_type="Destroyer")
    ]
    
    u_boat = UBoat(
        position=hex_pos,
        facing=Facing.NORTH,
        depth=Depth.MEDIUM,
        hull_damage=1
    )
    
    # Test various depth changes
    test_cases = [
        (Depth.PERISCOPE, False, "Medium → Periscope (ship overhead blocks)"),
        (Depth.DEEP, False, "Medium → Deep (hull damage prevents)"),
        (Depth.SURFACED, False, "Medium → Surfaced (ship overhead + two levels)"),
    ]
    
    print("\nDepth validation:")
    for target, expected, description in test_cases:
        can_change, reason = validator.can_change_depth(
            u_boat, target, hex_pos, ships, depth_changed_this_turn=False
        )
        status = "✓" if can_change == expected else "✗"
        print(f"  {status} {description}: {can_change}")
        if not can_change:
            print(f"      Reason: {reason}")
        assert can_change == expected, f"Failed: {description}"
    
    print("✅ Complex scenario tests passed!\n")


def test_depth_change_info():
    """Test get_depth_change_info formatting."""
    print("\n=== Testing Depth Change Info ===")
    
    shallow_hexes = {HexCoord(2, 2)}
    validator = DepthValidator(shallow_hexes)
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE,
        hull_damage=1
    )
    
    # Valid change
    info = validator.get_depth_change_info(
        u_boat, Depth.MEDIUM, HexCoord(5, 5), ships=[], depth_changed_this_turn=False
    )
    print(f"Valid change: {info}")
    assert "PERISCOPE → MEDIUM" in info
    assert "✓" in info
    assert "Hull Dmg" in info
    
    # Invalid change (hull damage)
    info = validator.get_depth_change_info(
        u_boat, Depth.DEEP, HexCoord(5, 5), ships=[], depth_changed_this_turn=False
    )
    print(f"Invalid (hull damage): {info}")
    assert "✗" in info
    assert "Hull damage" in info or "Hull Dmg" in info
    
    # Shallow water
    info = validator.get_depth_change_info(
        u_boat, Depth.MEDIUM, HexCoord(2, 2), ships=[], depth_changed_this_turn=False
    )
    print(f"Shallow water: {info}")
    assert "Shallow Water" in info
    
    # Ship overhead
    ships = [Ship(position=HexCoord(5, 5), facing=Facing.NORTH, ship_type="Corvette")]
    u_boat.depth = Depth.MEDIUM
    info = validator.get_depth_change_info(
        u_boat, Depth.PERISCOPE, HexCoord(5, 5), ships, depth_changed_this_turn=False
    )
    print(f"Ship overhead: {info}")
    assert "Ship Overhead" in info
    assert "Corvette" in info
    
    print("✅ Depth change info tests passed!\n")


def test_all_depth_transitions():
    """Test all valid adjacent depth transitions."""
    print("\n=== Testing All Depth Transitions ===")
    
    validator = DepthValidator(shallow_hexes=set())
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED
    )
    
    # Test all adjacent transitions
    transitions = [
        (Depth.SURFACED, Depth.PERISCOPE, True),
        (Depth.PERISCOPE, Depth.SURFACED, True),
        (Depth.PERISCOPE, Depth.MEDIUM, True),
        (Depth.MEDIUM, Depth.PERISCOPE, True),
        (Depth.MEDIUM, Depth.DEEP, True),
        (Depth.DEEP, Depth.MEDIUM, True),
    ]
    
    print("\nAll adjacent transitions:")
    for from_depth, to_depth, should_work in transitions:
        u_boat.depth = from_depth
        can_change, _ = validator.can_change_depth(
            u_boat, to_depth, HexCoord(5, 5), ships=[], depth_changed_this_turn=False
        )
        status = "✓" if can_change == should_work else "✗"
        print(f"  {status} {from_depth.name} → {to_depth.name}: {can_change}")
        assert can_change == should_work, f"Failed transition {from_depth.name} → {to_depth.name}"
    
    print("✅ All depth transitions tests passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2.5 Tests - DepthValidator")
    print("=" * 60)
    
    try:
        test_once_per_turn_limit()
        test_one_level_at_a_time()
        test_shallow_water_restrictions()
        test_ship_overhead_restrictions()
        test_hull_damage_limits()
        test_get_valid_depths()
        test_complex_scenario()
        test_depth_change_info()
        test_all_depth_transitions()
        
        print("=" * 60)
        print("✅ ALL DEPTH VALIDATOR TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
