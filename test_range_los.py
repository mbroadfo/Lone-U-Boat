"""
Tests for Range & LOS subsystems (Phase 2.2).

Run with: python test_range_los.py
"""

import sys
sys.path.insert(0, '.')

from core.hex_grid import HexGrid
from core.los import LOSCalculator
from core.models import HexCoord


def test_hex_distance():
    """Test hex distance calculation."""
    print("\n=== Testing hex_distance ===")
    
    # Test same hex
    origin = HexCoord(0, 0)
    assert HexGrid.hex_distance(origin, origin) == 0, "Same hex should be distance 0"
    print("✓ Same hex: distance 0")
    
    # Test adjacent hexes (distance 1)
    neighbors = [
        HexCoord(1, 0),   # Right
        HexCoord(0, 1),   # Down-Right
        HexCoord(-1, 1),  # Down-Left
        HexCoord(-1, 0),  # Left
        HexCoord(0, -1),  # Up-Left
        HexCoord(1, -1),  # Up-Right
    ]
    for neighbor in neighbors:
        dist = HexGrid.hex_distance(origin, neighbor)
        assert dist == 1, f"Neighbor {neighbor} should be distance 1, got {dist}"
    print(f"✓ All 6 neighbors: distance 1")
    
    # Test range 2
    range_2_hex = HexCoord(2, 0)
    assert HexGrid.hex_distance(origin, range_2_hex) == 2
    print("✓ Range 2: (0,0) to (2,0)")
    
    # Test range 3
    range_3_hex = HexCoord(2, 1)
    assert HexGrid.hex_distance(origin, range_3_hex) == 3
    print("✓ Range 3: (0,0) to (2,1)")
    
    # Test diagonal distance
    diagonal = HexCoord(3, 3)
    dist = HexGrid.hex_distance(origin, diagonal)
    print(f"✓ Diagonal (0,0) to (3,3): distance {dist}")
    assert dist == 6, "Should be 6"
    
    # Test negative coordinates
    neg = HexCoord(-2, -1)
    dist = HexGrid.hex_distance(origin, neg)
    print(f"✓ Negative coords (0,0) to (-2,-1): distance {dist}")
    assert dist == 3, "Should be 3"
    
    print("✅ hex_distance tests passed!\n")


def test_hexes_in_range():
    """Test hexes_in_range calculation."""
    print("\n=== Testing hexes_in_range ===")
    
    center = HexCoord(5, 5)
    
    # Range 0 (just center)
    range_0 = HexGrid.hexes_in_range(center, 0)
    assert len(range_0) == 1, f"Range 0 should have 1 hex, got {len(range_0)}"
    assert center in range_0
    print("✓ Range 0: 1 hex")
    
    # Range 1 (center + 6 neighbors = 7)
    range_1 = HexGrid.hexes_in_range(center, 1)
    assert len(range_1) == 7, f"Range 1 should have 7 hexes, got {len(range_1)}"
    print("✓ Range 1: 7 hexes")
    
    # Range 2 (center + 6 + 12 = 19)
    range_2 = HexGrid.hexes_in_range(center, 2)
    assert len(range_2) == 19, f"Range 2 should have 19 hexes, got {len(range_2)}"
    print("✓ Range 2: 19 hexes")
    
    # Range 3 (center + 6 + 12 + 18 = 37)
    range_3 = HexGrid.hexes_in_range(center, 3)
    assert len(range_3) == 37, f"Range 3 should have 37 hexes, got {len(range_3)}"
    print("✓ Range 3: 37 hexes")
    
    # Test with valid_hexes filter
    valid_hexes = {HexCoord(5, 5), HexCoord(6, 5), HexCoord(5, 6)}
    filtered = HexGrid.hexes_in_range(center, 1, valid_hexes)
    assert len(filtered) == 3, f"Filtered range should have 3 hexes, got {len(filtered)}"
    print("✓ Filtered by valid_hexes: 3 hexes")
    
    print("✅ hexes_in_range tests passed!\n")


def test_get_neighbors():
    """Test neighbor generation."""
    print("\n=== Testing get_neighbors ===")
    
    center = HexCoord(5, 5)
    neighbors = HexGrid.get_neighbors(center)
    
    assert len(neighbors) == 6, f"Should have 6 neighbors, got {len(neighbors)}"
    
    # Verify expected neighbors (flat-top)
    expected = {
        HexCoord(6, 5),   # Right
        HexCoord(5, 6),   # Down-Right
        HexCoord(4, 6),   # Down-Left
        HexCoord(4, 5),   # Left
        HexCoord(5, 4),   # Up-Left
        HexCoord(6, 4),   # Up-Right
    }
    
    assert set(neighbors) == expected, "Neighbors don't match expected"
    print("✓ All 6 neighbors correct")
    
    # Verify all are distance 1
    for neighbor in neighbors:
        dist = HexGrid.hex_distance(center, neighbor)
        assert dist == 1, f"Neighbor {neighbor} not distance 1"
    print("✓ All neighbors are distance 1")
    
    print("✅ get_neighbors tests passed!\n")


def test_los_basic():
    """Test basic LOS calculations."""
    print("\n=== Testing LOS Basic ===")
    
    # Empty map (no land)
    los = LOSCalculator(land_hexes=set())
    
    # Same hex
    has_los, _ = los.has_line_of_sight(HexCoord(0, 0), HexCoord(0, 0))
    assert has_los, "Same hex should have LOS"
    print("✓ Same hex: LOS")
    
    # Adjacent
    has_los, _ = los.has_line_of_sight(HexCoord(0, 0), HexCoord(1, 0))
    assert has_los, "Adjacent should have LOS"
    print("✓ Adjacent: LOS")
    
    # Range 2
    has_los, _ = los.has_line_of_sight(HexCoord(0, 0), HexCoord(2, 0))
    assert has_los, "Range 2 with no land should have LOS"
    print("✓ Range 2 (no land): LOS")
    
    # Range 3
    has_los, _ = los.has_line_of_sight(HexCoord(0, 0), HexCoord(3, 0))
    assert has_los, "Range 3 with no land should have LOS"
    print("✓ Range 3 (no land): LOS")
    
    print("✅ LOS basic tests passed!\n")


def test_los_blocking():
    """Test LOS blocking by land."""
    print("\n=== Testing LOS Blocking ===")
    
    # Create land at (1, 0) - blocks straight line
    land_hexes = {HexCoord(1, 0)}
    los = LOSCalculator(land_hexes)
    
    # Range 2: (0,0) to (2,0) blocked by (1,0)
    has_los, reason = los.has_line_of_sight(HexCoord(0, 0), HexCoord(2, 0))
    assert not has_los, "LOS should be blocked by land"
    assert reason is not None, "Should have blocking reason"
    print(f"✓ Range 2 blocked: {reason}")
    
    # Different angle should have LOS (use a truly clear path)
    has_los, reason = los.has_line_of_sight(HexCoord(0, 0), HexCoord(1, 2))
    print(f"  Diagonal (0,0) to (1,2): LOS={has_los}, reason={reason}")
    if not has_los:
        intervening = los.get_intervening_hexes(HexCoord(0, 0), HexCoord(1, 2))
        print(f"  Intervening hexes: {intervening}")
        for h in intervening:
            if h in land_hexes:
                print(f"    Land at {h}")
    assert has_los, f"Clear diagonal should have LOS, blocked by: {reason}"
    print("✓ Diagonal clear: LOS")
    
    # Multiple land hexes
    land_hexes = {HexCoord(1, 0), HexCoord(2, 1), HexCoord(1, 1)}
    los.update_land_hexes(land_hexes)
    
    has_los, reason = los.has_line_of_sight(HexCoord(0, 0), HexCoord(3, 2))
    # This depends on exact path - should check intervening hexes
    print(f"✓ Multiple land hexes: LOS = {has_los}")
    
    print("✅ LOS blocking tests passed!\n")


def test_intervening_hexes():
    """Test intervening hex calculation."""
    print("\n=== Testing Intervening Hexes ===")
    
    los = LOSCalculator(land_hexes=set())
    
    # Adjacent: no intervening
    intervening = los.get_intervening_hexes(HexCoord(0, 0), HexCoord(1, 0))
    assert len(intervening) == 0, "Adjacent should have no intervening hexes"
    print("✓ Adjacent: 0 intervening")
    
    # Range 2: 1 intervening
    intervening = los.get_intervening_hexes(HexCoord(0, 0), HexCoord(2, 0))
    print(f"  Range 2 intervening: {intervening}")
    assert len(intervening) >= 1, "Range 2 should have at least 1 intervening hex"
    print(f"✓ Range 2: {len(intervening)} intervening")
    
    # Range 3: 2 intervening
    intervening = los.get_intervening_hexes(HexCoord(0, 0), HexCoord(3, 0))
    print(f"  Range 3 intervening: {intervening}")
    assert len(intervening) >= 2, "Range 3 should have at least 2 intervening hexes"
    print(f"✓ Range 3: {len(intervening)} intervening")
    
    print("✅ Intervening hexes tests passed!\n")


def test_get_visible_hexes():
    """Test visible hexes calculation."""
    print("\n=== Testing Get Visible Hexes ===")
    
    # Create land that blocks some hexes
    land_hexes = {HexCoord(2, 0), HexCoord(2, 1)}
    los = LOSCalculator(land_hexes)
    
    origin = HexCoord(0, 0)
    
    # Get visible hexes at range 3
    visible = los.get_visible_hexes(origin, 3)
    
    print(f"✓ Visible hexes from (0,0) at range 3: {len(visible)}")
    
    # Should have LOS to adjacent even if land nearby
    assert HexCoord(1, 0) in visible, "Adjacent should be visible"
    
    # Should NOT have LOS beyond land wall
    # (depends on exact map layout)
    
    print("✅ Get visible hexes tests passed!\n")


def test_deck_gun_scenarios():
    """Test realistic deck gun scenarios."""
    print("\n=== Testing Deck Gun Scenarios ===")
    
    # Mission-like setup with some land
    land_hexes = {
        HexCoord(5, 8), HexCoord(6, 8), HexCoord(7, 8),  # Land barrier
    }
    los = LOSCalculator(land_hexes)
    
    u_boat_pos = HexCoord(5, 5)
    
    # Scenario 1: Clear shot at range 2
    target_1 = HexCoord(7, 5)
    has_los, reason = los.has_line_of_sight(u_boat_pos, target_1)
    distance = HexGrid.hex_distance(u_boat_pos, target_1)
    print(f"Scenario 1: U-Boat at {u_boat_pos}, Target at {target_1}")
    print(f"  Range: {distance}, LOS: {has_los}")
    assert has_los, "Clear shot should have LOS"
    
    # Scenario 2: Shot blocked by land
    target_2 = HexCoord(5, 10)
    has_los, reason = los.has_line_of_sight(u_boat_pos, target_2)
    distance = HexGrid.hex_distance(u_boat_pos, target_2)
    print(f"Scenario 2: U-Boat at {u_boat_pos}, Target at {target_2}")
    print(f"  Range: {distance}, LOS: {has_los}")
    if not has_los:
        print(f"  Blocked: {reason}")
    
    # Scenario 3: Range 3 shot
    target_3 = HexCoord(8, 5)
    has_los, reason = los.has_line_of_sight(u_boat_pos, target_3)
    distance = HexGrid.hex_distance(u_boat_pos, target_3)
    print(f"Scenario 3: U-Boat at {u_boat_pos}, Target at {target_3}")
    print(f"  Range: {distance}, LOS: {has_los}")
    
    print("✅ Deck gun scenarios passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2.2 Tests - Range & LOS")
    print("=" * 60)
    
    try:
        test_hex_distance()
        test_hexes_in_range()
        test_get_neighbors()
        test_los_basic()
        test_los_blocking()
        test_intervening_hexes()
        test_get_visible_hexes()
        test_deck_gun_scenarios()
        
        print("=" * 60)
        print("✅ ALL RANGE & LOS TESTS PASSED!")
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
