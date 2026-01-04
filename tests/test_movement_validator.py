"""
Tests for MovementValidator (Phase 2.4).

Run with: python test_movement_validator.py
"""

import sys
sys.path.insert(0, '.')

from typing import Set
from core.movement_validator import MovementValidator
from core.models import HexCoord, UBoat, Ship, Depth, Facing


def test_land_blocking():
    """Test that land hexes block movement."""
    print("\n=== Testing Land Blocking ===")
    
    # Setup: Land at (2, 0)
    land_hexes = {HexCoord(2, 0)}
    shallow_hexes: Set[HexCoord] = set()
    validator = MovementValidator(land_hexes, shallow_hexes)
    
    # U-boat at any depth
    u_boat = UBoat(
        position=HexCoord(1, 0),
        facing=Facing.NORTH,
        depth=Depth.SURFACED
    )
    
    # Try to move into land
    can_move, reason = validator.can_move_to(u_boat, HexCoord(2, 0), ships=[])
    print(f"Move into land: can_move={can_move}, reason='{reason}'")
    assert not can_move, "Should not be able to move into land"
    assert "land" in reason.lower(), "Reason should mention land"
    
    # Move to adjacent non-land hex
    can_move, reason = validator.can_move_to(u_boat, HexCoord(1, 1), ships=[])
    print(f"Move to water: can_move={can_move}")
    assert can_move, "Should be able to move to water"
    
    print("✅ Land blocking tests passed!\n")


def test_shallow_water_restrictions():
    """Test shallow water depth restrictions."""
    print("\n=== Testing Shallow Water Restrictions ===")
    
    # Setup: Shallow water at (3, 0)
    land_hexes: Set[HexCoord] = set()
    shallow_hexes = {HexCoord(3, 0)}
    validator = MovementValidator(land_hexes, shallow_hexes)
    
    target = HexCoord(3, 0)
    
    # Test 1: Surfaced - CAN enter shallow
    u_boat = UBoat(
        position=HexCoord(2, 0),
        facing=Facing.NORTH,
        depth=Depth.SURFACED
    )
    can_move, reason = validator.can_move_to(u_boat, target, ships=[])
    print(f"Surfaced into shallow: can_move={can_move}")
    assert can_move, "Surfaced should be able to enter shallow water"
    
    # Test 2: Periscope - CAN enter shallow
    u_boat.depth = Depth.PERISCOPE
    can_move, reason = validator.can_move_to(u_boat, target, ships=[])
    print(f"Periscope into shallow: can_move={can_move}")
    assert can_move, "Periscope should be able to enter shallow water"
    
    # Test 3: Medium - CANNOT enter shallow
    u_boat.depth = Depth.MEDIUM
    can_move, reason = validator.can_move_to(u_boat, target, ships=[])
    print(f"Medium into shallow: can_move={can_move}, reason='{reason}'")
    assert not can_move, "Medium should not be able to enter shallow water"
    assert "Shallow water" in reason, "Reason should mention shallow water"
    assert "Surfaced or Periscope" in reason, "Reason should mention valid depths"
    
    # Test 4: Deep - CANNOT enter shallow
    u_boat.depth = Depth.DEEP
    can_move, reason = validator.can_move_to(u_boat, target, ships=[])
    print(f"Deep into shallow: can_move={can_move}, reason='{reason}'")
    assert not can_move, "Deep should not be able to enter shallow water"
    
    print("✅ Shallow water tests passed!\n")


def test_ship_collision():
    """Test ship collision rules."""
    print("\n=== Testing Ship Collision ===")
    
    # Setup: No terrain restrictions
    validator = MovementValidator(land_hexes=set(), shallow_hexes=set())
    
    # Ship at (5, 5)
    target = HexCoord(5, 5)
    ships = [
        Ship(
            position=target,
            facing=Facing.NORTHEAST,
            ship_type="Merchant"
        )
    ]
    
    # Test 1: Surfaced - CANNOT enter ship hex
    u_boat = UBoat(
        position=HexCoord(4, 5),
        facing=Facing.NORTHEAST,
        depth=Depth.SURFACED
    )
    can_move, reason = validator.can_move_to(u_boat, target, ships)
    print(f"Surfaced into ship: can_move={can_move}, reason='{reason}'")
    assert not can_move, "Surfaced should not be able to enter ship hex"
    assert "ship hex" in reason.lower(), "Reason should mention ship hex"
    assert "Medium or Deep" in reason, "Reason should mention valid depths"
    
    # Test 2: Periscope - CANNOT enter ship hex
    u_boat.depth = Depth.PERISCOPE
    can_move, reason = validator.can_move_to(u_boat, target, ships)
    print(f"Periscope into ship: can_move={can_move}, reason='{reason}'")
    assert not can_move, "Periscope should not be able to enter ship hex"
    
    # Test 3: Medium - CAN enter ship hex (pass under)
    u_boat.depth = Depth.MEDIUM
    can_move, reason = validator.can_move_to(u_boat, target, ships)
    print(f"Medium into ship: can_move={can_move}")
    assert can_move, "Medium should be able to pass under ship"
    
    # Test 4: Deep - CAN enter ship hex (pass under)
    u_boat.depth = Depth.DEEP
    can_move, reason = validator.can_move_to(u_boat, target, ships)
    print(f"Deep into ship: can_move={can_move}")
    assert can_move, "Deep should be able to pass under ship"
    
    print("✅ Ship collision tests passed!\n")


def test_get_valid_moves():
    """Test filtering valid moves from candidates."""
    print("\n=== Testing Get Valid Moves ===")
    
    # Setup: Land at (1,1), Shallow at (2,0)
    land_hexes = {HexCoord(1, 1)}
    shallow_hexes = {HexCoord(2, 0)}
    validator = MovementValidator(land_hexes, shallow_hexes)
    
    # U-boat at (1,0) at Medium depth
    u_boat = UBoat(
        position=HexCoord(1, 0),
        facing=Facing.NORTH,
        depth=Depth.MEDIUM
    )
    
    # Candidate hexes (all adjacent)
    candidates = {
        HexCoord(2, 0),   # Shallow - blocked at Medium
        HexCoord(1, 1),   # Land - blocked
        HexCoord(0, 1),   # Water - OK
        HexCoord(0, 0),   # Water - OK
        HexCoord(1, -1),  # Water - OK
        HexCoord(2, -1),  # Water - OK
    }
    
    valid = validator.get_valid_moves(u_boat, candidates, ships=[])
    print(f"Valid moves: {len(valid)} of {len(candidates)}")
    for hex_coord in sorted(valid, key=lambda h: (h.q, h.r)):
        print(f"  {hex_coord}")
    
    # Should have 4 valid moves (all except land and shallow)
    assert len(valid) == 4, f"Expected 4 valid moves, got {len(valid)}"
    assert HexCoord(2, 0) not in valid, "Shallow should be blocked at Medium"
    assert HexCoord(1, 1) not in valid, "Land should be blocked"
    assert HexCoord(0, 1) in valid, "Clear water should be valid"
    
    print("✅ Get valid moves tests passed!\n")


def test_complex_scenario():
    """Test complex scenario with multiple restrictions."""
    print("\n=== Testing Complex Scenario ===")
    
    # Setup: Land, shallow, and ships
    land_hexes = {HexCoord(3, 3), HexCoord(4, 3)}
    shallow_hexes = {HexCoord(2, 2), HexCoord(3, 2)}
    validator = MovementValidator(land_hexes, shallow_hexes)
    
    ships = [
        Ship(position=HexCoord(2, 3), facing=Facing.NORTHEAST, ship_type="Merchant")
    ]
    
    # U-boat at Periscope depth
    u_boat = UBoat(
        position=HexCoord(2, 1),
        facing=Facing.NORTH,
        depth=Depth.PERISCOPE
    )
    
    # Test various hexes
    test_cases = [
        (HexCoord(2, 2), True, "Shallow OK at Periscope"),
        (HexCoord(3, 2), True, "Shallow OK at Periscope"),
        (HexCoord(3, 3), False, "Land always blocked"),
        (HexCoord(2, 3), False, "Ship blocked at Periscope"),
        (HexCoord(1, 1), True, "Clear water OK"),
    ]
    
    print("\nMovement validation:")
    for target, expected, description in test_cases:
        can_move, reason = validator.can_move_to(u_boat, target, ships)
        status = "✓" if can_move == expected else "✗"
        print(f"  {status} {target} -> {can_move} ({description})")
        if not can_move:
            print(f"      Reason: {reason}")
        assert can_move == expected, f"Failed: {description}"
    
    print("✅ Complex scenario tests passed!\n")


def test_movement_info():
    """Test get_movement_info formatting."""
    print("\n=== Testing Movement Info ===")
    
    land_hexes = {HexCoord(1, 0)}
    shallow_hexes = {HexCoord(2, 0)}
    validator = MovementValidator(land_hexes, shallow_hexes)
    
    ships = [
        Ship(position=HexCoord(3, 0), facing=Facing.NORTHEAST, ship_type="Merchant")
    ]
    
    u_boat = UBoat(
        position=HexCoord(0, 0),
        facing=Facing.NORTHEAST,
        depth=Depth.SURFACED
    )
    
    # Test different terrain types
    info = validator.get_movement_info(u_boat, HexCoord(1, 0), ships)
    print(f"Land hex: {info}")
    assert "Land" in info
    assert "✗" in info
    
    info = validator.get_movement_info(u_boat, HexCoord(2, 0), ships)
    print(f"Shallow hex: {info}")
    assert "Shallow Water" in info
    assert "✓" in info  # Surfaced can enter shallow
    
    info = validator.get_movement_info(u_boat, HexCoord(3, 0), ships)
    print(f"Ship hex: {info}")
    assert "Ship" in info
    assert "Merchant" in info
    assert "✗" in info  # Surfaced cannot enter ship hex
    
    info = validator.get_movement_info(u_boat, HexCoord(0, 1), ships)
    print(f"Deep water: {info}")
    assert "Deep Water" in info
    assert "✓" in info
    
    print("✅ Movement info tests passed!\n")


def test_update_terrain():
    """Test dynamic terrain updates."""
    print("\n=== Testing Update Terrain ===")
    
    # Start with no terrain
    validator = MovementValidator(land_hexes=set(), shallow_hexes=set())
    
    u_boat = UBoat(
        position=HexCoord(0, 0),
        facing=Facing.NORTH,
        depth=Depth.MEDIUM
    )
    
    # Should be able to move anywhere initially
    can_move, _ = validator.can_move_to(u_boat, HexCoord(1, 0), ships=[])
    assert can_move, "Should be able to move with no terrain"
    print("✓ Initial state: no restrictions")
    
    # Update to add land
    validator.update_terrain(
        land_hexes={HexCoord(1, 0)},
        shallow_hexes=set()
    )
    
    # Now should be blocked
    can_move, reason = validator.can_move_to(u_boat, HexCoord(1, 0), ships=[])
    assert not can_move, "Should be blocked after adding land"
    print(f"✓ After update: blocked by {reason}")
    
    print("✅ Update terrain tests passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2.4 Tests - MovementValidator")
    print("=" * 60)
    
    try:
        test_land_blocking()
        test_shallow_water_restrictions()
        test_ship_collision()
        test_get_valid_moves()
        test_complex_scenario()
        test_movement_info()
        test_update_terrain()
        
        print("=" * 60)
        print("✅ ALL MOVEMENT VALIDATOR TESTS PASSED!")
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
