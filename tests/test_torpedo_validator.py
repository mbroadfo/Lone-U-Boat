"""
Tests for TorpedoValidator (Phase 2.8).

Run with: python test_torpedo_validator.py
"""

import sys
sys.path.insert(0, '.')

from core.torpedo_validator import TorpedoValidator
from core.models import HexCoord, UBoat, Depth, Facing, TubeState


def test_load_single_tube():
    """Test loading a single torpedo tube."""
    print("\n=== Testing Load Single Tube ===")
    
    validator = TorpedoValidator()
    
    # Empty tube at Surfaced
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        torpedo_tubes=[TubeState.EMPTY, TubeState.LOADED, TubeState.LOADED, TubeState.LOADED, TubeState.LOADED],  # Tube 1 empty
        weapons_officer_alive=True
    )
    
    # Can load empty tube
    can_load, reason = validator.can_load_torpedo(u_boat, 1)
    print(f"Load tube 1 (empty, Surfaced): can_load={can_load}")
    assert can_load, "Should be able to load empty tube"
    
    # Cannot load already loaded tube
    can_load, reason = validator.can_load_torpedo(u_boat, 2)
    print(f"Load tube 2 (loaded): can_load={can_load}, reason='{reason}'")
    assert not can_load, "Should not load already loaded tube"
    assert "already loaded" in reason.lower(), "Reason should mention already loaded"
    
    # Invalid tube number
    can_load, reason = validator.can_load_torpedo(u_boat, 6)
    print(f"Load tube 6 (invalid): can_load={can_load}, reason='{reason}'")
    assert not can_load, "Should reject invalid tube number"
    assert "Invalid" in reason or "must be 1-5" in reason, "Reason should mention invalid number"
    
    print("✅ Load single tube tests passed!\n")


def test_load_depth_restrictions():
    """Test depth restrictions for loading."""
    print("\n=== Testing Load Depth Restrictions ===")
    
    validator = TorpedoValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        torpedo_tubes=[TubeState.EMPTY, TubeState.EMPTY, TubeState.EMPTY, TubeState.EMPTY, TubeState.EMPTY],  # All empty
        weapons_officer_alive=True
    )
    
    # Surfaced: OK
    can_load, reason = validator.can_load_torpedo(u_boat, 1)
    print(f"Surfaced: can_load={can_load}")
    assert can_load, "Should load at Surfaced"
    
    # Periscope: OK
    u_boat.depth = Depth.PERISCOPE
    can_load, reason = validator.can_load_torpedo(u_boat, 1)
    print(f"Periscope: can_load={can_load}")
    assert can_load, "Should load at Periscope"
    
    # Medium: Blocked
    u_boat.depth = Depth.MEDIUM
    can_load, reason = validator.can_load_torpedo(u_boat, 1)
    print(f"Medium: can_load={can_load}, reason='{reason}'")
    assert not can_load, "Should block loading at Medium"
    assert "Surfaced or Periscope" in reason, "Reason should mention depth requirement"
    
    # Deep: Blocked
    u_boat.depth = Depth.DEEP
    can_load, reason = validator.can_load_torpedo(u_boat, 1)
    print(f"Deep: can_load={can_load}, reason='{reason}'")
    assert not can_load, "Should block loading at Deep"
    
    print("✅ Load depth restriction tests passed!\n")


def test_load_multiple_tubes_wo_alive():
    """Test loading multiple tubes with Weapons Officer alive."""
    print("\n=== Testing Load Multiple Tubes (WO Alive) ===")
    
    validator = TorpedoValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        torpedo_tubes=[TubeState.EMPTY, TubeState.EMPTY, TubeState.EMPTY, TubeState.LOADED, TubeState.LOADED],  # Tubes 1-3 empty
        weapons_officer_alive=True
    )
    
    # Can load 1 tube
    can_load, reason = validator.can_load_tubes(u_boat, [1])
    print(f"Load 1 tube (WO alive): can_load={can_load}")
    assert can_load, "Should load 1 tube with WO alive"
    
    # Can load 2 tubes
    can_load, reason = validator.can_load_tubes(u_boat, [1, 2])
    print(f"Load 2 tubes (WO alive): can_load={can_load}")
    assert can_load, "Should load 2 tubes with WO alive"
    
    # Cannot load 3 tubes
    can_load, reason = validator.can_load_tubes(u_boat, [1, 2, 3])
    print(f"Load 3 tubes (WO alive): can_load={can_load}, reason='{reason}'")
    assert not can_load, "Should not load 3 tubes even with WO alive"
    assert "max 2" in reason.lower(), "Reason should mention 2 tube limit"
    
    print("✅ Load multiple tubes (WO alive) tests passed!\n")


def test_load_multiple_tubes_wo_kia():
    """Test loading multiple tubes with Weapons Officer KIA."""
    print("\n=== Testing Load Multiple Tubes (WO KIA) ===")
    
    validator = TorpedoValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        torpedo_tubes=[TubeState.EMPTY, TubeState.EMPTY, TubeState.EMPTY, TubeState.LOADED, TubeState.LOADED],  # Tubes 1-3 empty
        weapons_officer_alive=False
    )
    
    # Can load 1 tube
    can_load, reason = validator.can_load_tubes(u_boat, [1])
    print(f"Load 1 tube (WO KIA): can_load={can_load}")
    assert can_load, "Should load 1 tube with WO KIA"
    
    # Cannot load 2 tubes
    can_load, reason = validator.can_load_tubes(u_boat, [1, 2])
    print(f"Load 2 tubes (WO KIA): can_load={can_load}, reason='{reason}'")
    assert not can_load, "Should not load 2 tubes with WO KIA"
    assert "max 1" in reason.lower(), "Reason should mention 1 tube limit"
    assert "KIA" in reason, "Reason should mention WO KIA"
    
    print("✅ Load multiple tubes (WO KIA) tests passed!\n")


def test_fire_single_tube():
    """Test firing a single torpedo tube."""
    print("\n=== Testing Fire Single Tube ===")
    
    validator = TorpedoValidator()
    
    # Loaded tube at Surfaced
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        torpedo_tubes=[TubeState.LOADED, TubeState.EMPTY, TubeState.EMPTY, TubeState.EMPTY, TubeState.EMPTY],  # Only tube 1 loaded
        weapons_officer_alive=True
    )
    
    # Can fire loaded tube
    can_fire, reason = validator.can_fire_torpedo(u_boat, 1)
    print(f"Fire tube 1 (loaded, Surfaced): can_fire={can_fire}")
    assert can_fire, "Should be able to fire loaded tube"
    
    # Cannot fire unloaded tube
    can_fire, reason = validator.can_fire_torpedo(u_boat, 2)
    print(f"Fire tube 2 (unloaded): can_fire={can_fire}, reason='{reason}'")
    assert not can_fire, "Should not fire unloaded tube"
    assert "not loaded" in reason.lower(), "Reason should mention not loaded"
    
    # Invalid tube number
    can_fire, reason = validator.can_fire_torpedo(u_boat, 0)
    print(f"Fire tube 0 (invalid): can_fire={can_fire}, reason='{reason}'")
    assert not can_fire, "Should reject invalid tube number"
    
    print("✅ Fire single tube tests passed!\n")


def test_fire_depth_restrictions():
    """Test depth restrictions for firing."""
    print("\n=== Testing Fire Depth Restrictions ===")
    
    validator = TorpedoValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        torpedo_tubes=[TubeState.LOADED, TubeState.LOADED, TubeState.LOADED, TubeState.LOADED, TubeState.LOADED],  # All loaded
        weapons_officer_alive=True
    )
    
    # Surfaced: OK
    can_fire, reason = validator.can_fire_torpedo(u_boat, 1)
    print(f"Surfaced: can_fire={can_fire}")
    assert can_fire, "Should fire at Surfaced"
    
    # Periscope: OK
    u_boat.depth = Depth.PERISCOPE
    can_fire, reason = validator.can_fire_torpedo(u_boat, 1)
    print(f"Periscope: can_fire={can_fire}")
    assert can_fire, "Should fire at Periscope"
    
    # Medium: Blocked
    u_boat.depth = Depth.MEDIUM
    can_fire, reason = validator.can_fire_torpedo(u_boat, 1)
    print(f"Medium: can_fire={can_fire}, reason='{reason}'")
    assert not can_fire, "Should block firing at Medium"
    assert "Surfaced or Periscope" in reason, "Reason should mention depth requirement"
    
    # Deep: Blocked
    u_boat.depth = Depth.DEEP
    can_fire, reason = validator.can_fire_torpedo(u_boat, 1)
    print(f"Deep: can_fire={can_fire}, reason='{reason}'")
    assert not can_fire, "Should block firing at Deep"
    
    print("✅ Fire depth restriction tests passed!\n")


def test_fire_front_rear_restriction():
    """Test front/rear firing restriction."""
    print("\n=== Testing Fire Front/Rear Restriction ===")
    
    validator = TorpedoValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        torpedo_tubes=[TubeState.LOADED, TubeState.LOADED, TubeState.LOADED, TubeState.LOADED, TubeState.LOADED],  # All loaded
        weapons_officer_alive=True
    )
    
    # Front only: OK
    can_fire, reason = validator.can_fire_tubes(u_boat, [1, 2])
    print(f"Fire front tubes 1,2: can_fire={can_fire}")
    assert can_fire, "Should fire front tubes only"
    
    # Rear only: OK
    can_fire, reason = validator.can_fire_tubes(u_boat, [5])
    print(f"Fire rear tube 5: can_fire={can_fire}")
    assert can_fire, "Should fire rear tube only"
    
    # Front + Rear: Blocked
    can_fire, reason = validator.can_fire_tubes(u_boat, [1, 5])
    print(f"Fire front 1 + rear 5: can_fire={can_fire}, reason='{reason}'")
    assert not can_fire, "Should block firing both front and rear"
    assert "front and rear" in reason.lower(), "Reason should mention front/rear restriction"
    
    # Multiple front tubes: OK
    can_fire, reason = validator.can_fire_tubes(u_boat, [1, 2, 3])
    print(f"Fire front tubes 1,2,3: can_fire={can_fire}")
    assert can_fire, "Should fire multiple front tubes"
    
    print("✅ Fire front/rear restriction tests passed!\n")


def test_fire_tube_count_limit():
    """Test maximum 3 torpedoes per action."""
    print("\n=== Testing Fire Tube Count Limit ===")
    
    validator = TorpedoValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        torpedo_tubes=[TubeState.LOADED, TubeState.LOADED, TubeState.LOADED, TubeState.LOADED, TubeState.LOADED],  # All loaded
        weapons_officer_alive=True
    )
    
    # 1 torpedo: OK
    can_fire, reason = validator.can_fire_tubes(u_boat, [1])
    print(f"Fire 1 torpedo: can_fire={can_fire}")
    assert can_fire, "Should fire 1 torpedo"
    
    # 2 torpedoes: OK
    can_fire, reason = validator.can_fire_tubes(u_boat, [1, 2])
    print(f"Fire 2 torpedoes: can_fire={can_fire}")
    assert can_fire, "Should fire 2 torpedoes"
    
    # 3 torpedoes: OK
    can_fire, reason = validator.can_fire_tubes(u_boat, [1, 2, 3])
    print(f"Fire 3 torpedoes: can_fire={can_fire}")
    assert can_fire, "Should fire 3 torpedoes"
    
    # 4 torpedoes: Blocked
    can_fire, reason = validator.can_fire_tubes(u_boat, [1, 2, 3, 4])
    print(f"Fire 4 torpedoes: can_fire={can_fire}, reason='{reason}'")
    assert not can_fire, "Should block firing 4 torpedoes"
    assert "maximum 3" in reason.lower(), "Reason should mention 3 torpedo limit"
    
    print("✅ Fire tube count limit tests passed!\n")


def test_get_loadable_tubes():
    """Test getting list of loadable tubes."""
    print("\n=== Testing Get Loadable Tubes ===")
    
    validator = TorpedoValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        torpedo_tubes=[TubeState.EMPTY, TubeState.LOADED, TubeState.EMPTY, TubeState.LOADED, TubeState.EMPTY],  # Tubes 1,3,5 empty
        weapons_officer_alive=True
    )
    
    # At Surfaced
    loadable = validator.get_loadable_tubes(u_boat)
    print(f"Loadable tubes (Surfaced): {loadable}")
    assert loadable == [1, 3, 5], "Should identify empty tubes"
    
    # At Medium (blocked)
    u_boat.depth = Depth.MEDIUM
    loadable = validator.get_loadable_tubes(u_boat)
    print(f"Loadable tubes (Medium): {loadable}")
    assert loadable == [], "Should return empty list at Medium depth"
    
    # All loaded
    u_boat.depth = Depth.SURFACED
    u_boat.torpedo_tubes = [TubeState.LOADED] * 5
    loadable = validator.get_loadable_tubes(u_boat)
    print(f"Loadable tubes (all loaded): {loadable}")
    assert loadable == [], "Should return empty list when all loaded"
    
    print("✅ Get loadable tubes tests passed!\n")


def test_get_fireable_tubes():
    """Test getting list of fireable tubes."""
    print("\n=== Testing Get Fireable Tubes ===")
    
    validator = TorpedoValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        torpedo_tubes=[TubeState.LOADED, TubeState.EMPTY, TubeState.LOADED, TubeState.EMPTY, TubeState.LOADED],  # Tubes 1,3,5 loaded
        weapons_officer_alive=True
    )
    
    # At Surfaced
    fireable = validator.get_fireable_tubes(u_boat)
    print(f"Fireable tubes (Surfaced): {fireable}")
    assert fireable['front'] == [1, 3], "Should identify loaded front tubes"
    assert fireable['rear'] == [5], "Should identify loaded rear tube"
    
    # At Medium (blocked)
    u_boat.depth = Depth.MEDIUM
    fireable = validator.get_fireable_tubes(u_boat)
    print(f"Fireable tubes (Medium): {fireable}")
    assert fireable['front'] == [], "Should return empty front list at Medium"
    assert fireable['rear'] == [], "Should return empty rear list at Medium"
    
    # All empty
    u_boat.depth = Depth.SURFACED
    u_boat.torpedo_tubes = [TubeState.EMPTY] * 5
    fireable = validator.get_fireable_tubes(u_boat)
    print(f"Fireable tubes (all empty): {fireable}")
    assert fireable['front'] == [], "Should return empty front list"
    assert fireable['rear'] == [], "Should return empty rear list"
    
    print("✅ Get fireable tubes tests passed!\n")


def test_tube_status_display():
    """Test tube status display."""
    print("\n=== Testing Tube Status Display ===")
    
    validator = TorpedoValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        torpedo_tubes=[TubeState.LOADED, TubeState.EMPTY, TubeState.LOADED, TubeState.EMPTY, TubeState.LOADED],  # Tubes 1,3,5 loaded
        weapons_officer_alive=True
    )
    
    status = validator.get_tube_status(u_boat)
    print(f"Tube status: {status}")
    assert "1:●" in status, "Should show tube 1 loaded"
    assert "2:○" in status, "Should show tube 2 empty"
    assert "3:●" in status, "Should show tube 3 loaded"
    assert "4:○" in status, "Should show tube 4 empty"
    assert "5): ●" in status or "5:●" in status, "Should show tube 5 loaded"
    assert "Front (1-4)" in status, "Should label front tubes"
    assert "Rear (5)" in status, "Should label rear tube"
    
    print("✅ Tube status display tests passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2.8 Tests - TorpedoValidator")
    print("=" * 60)
    
    try:
        test_load_single_tube()
        test_load_depth_restrictions()
        test_load_multiple_tubes_wo_alive()
        test_load_multiple_tubes_wo_kia()
        test_fire_single_tube()
        test_fire_depth_restrictions()
        test_fire_front_rear_restriction()
        test_fire_tube_count_limit()
        test_get_loadable_tubes()
        test_get_fireable_tubes()
        test_tube_status_display()
        
        print("=" * 60)
        print("✅ ALL TORPEDO VALIDATOR TESTS PASSED!")
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
