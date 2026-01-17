"""
Tests for RepairValidator (Phase 2.6).

Run with: python test_repair_validator.py
"""

import sys
sys.path.insert(0, '.')

from core.repair_validator import RepairValidator
from core.models import HexCoord, UBoat, Depth, Facing, TubeState


def test_engine_repair_surfaced():
    """Test engine repair when surfaced."""
    print("\n=== Testing Engine Repair (Surfaced) ===")
    
    validator = RepairValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        engine_damaged=True
    )
    
    # Can repair engine at surface
    can_repair, reason = validator.can_repair_component(u_boat, "Engine")
    print(f"Engine repair (Surfaced): can_repair={can_repair}")
    assert can_repair, "Should be able to repair engine when surfaced"
    
    # AP cost should be 2
    ap_cost = validator.get_repair_ap_cost("Engine", Depth.SURFACED, u_boat.engineer_alive)
    print(f"AP cost: {ap_cost}")
    assert ap_cost == 2, "Surfaced repair should cost 2 AP"
    
    # Cannot repair undamaged engine
    u_boat.engine_damaged = False
    can_repair, reason = validator.can_repair_component(u_boat, "Engine")
    print(f"Undamaged engine: can_repair={can_repair}, reason='{reason}'")
    assert not can_repair, "Should not repair undamaged component"
    assert "not damaged" in reason.lower(), "Reason should mention not damaged"
    
    print("✅ Engine repair (Surfaced) tests passed!\n")


def test_engine_repair_submerged_with_engineer():
    """Test engine repair when submerged with Engineer alive."""
    print("\n=== Testing Engine Repair (Submerged, Engineer Alive) ===")
    
    validator = RepairValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.MEDIUM,
        engine_damaged=True,
        engineer_alive=True
    )
    
    # Can repair submerged with Engineer
    can_repair, _ = validator.can_repair_component(u_boat, "Engine")
    print(f"Engine repair (Medium, Engineer alive): can_repair={can_repair}")
    assert can_repair, "Should be able to repair submerged with Engineer"
    
    # AP cost should be 4
    ap_cost = validator.get_repair_ap_cost("Engine", Depth.MEDIUM, u_boat.engineer_alive)
    print(f"AP cost: {ap_cost}")
    assert ap_cost == 4, "Submerged repair should cost 4 AP"
    
    # Test at different depths
    for depth in [Depth.PERISCOPE, Depth.DEEP]:
        ap_cost = validator.get_repair_ap_cost("Engine", depth, engineer_alive=True)
        print(f"AP cost at {depth.name}: {ap_cost}")
        assert ap_cost == 4, f"Should cost 4 AP at {depth.name}"
    
    print("✅ Engine repair (Submerged, Engineer) tests passed!\n")


def test_engine_repair_submerged_no_engineer():
    """Test engine repair blocked when submerged without Engineer."""
    print("\n=== Testing Engine Repair (Submerged, Engineer KIA) ===")
    
    validator = RepairValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.MEDIUM,
        engine_damaged=True,
        engineer_alive=False
    )
    
    # Cannot repair submerged without Engineer
    can_repair, reason = validator.can_repair_component(u_boat, "Engine")
    print(f"Engine repair (Medium, Engineer KIA): can_repair={can_repair}, reason='{reason}'")
    assert not can_repair, "Should block submerged repair without Engineer"
    assert "Engineer" in reason, "Reason should mention Engineer"
    assert "KIA" in reason, "Reason should mention KIA"
    
    # AP cost should be 0
    ap_cost = validator.get_repair_ap_cost("Engine", Depth.MEDIUM, engineer_alive=False)
    print(f"AP cost (no Engineer): {ap_cost}")
    assert ap_cost == 0, "Should return 0 AP when repair impossible"
    
    # Can still repair at surface
    u_boat.depth = Depth.SURFACED
    can_repair, _ = validator.can_repair_component(u_boat, "Engine")
    print(f"Engine repair (Surfaced, Engineer KIA): can_repair={can_repair}")
    assert can_repair, "Should still work at surface without Engineer"
    
    print("✅ Engine repair (Engineer KIA) tests passed!\n")


def test_deck_gun_surface_only():
    """Test Deck Gun repair (surface only)."""
    print("\n=== Testing Deck Gun Repair (Surface Only) ===")
    
    validator = RepairValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        deck_gun_damaged=True,
        engineer_alive=True
    )
    
    # Can repair at surface
    can_repair, reason = validator.can_repair_component(u_boat, "Deck Gun")
    print(f"Deck Gun (Surfaced): can_repair={can_repair}")
    assert can_repair, "Should repair Deck Gun when surfaced"
    
    # Cannot repair submerged (even with Engineer)
    u_boat.depth = Depth.PERISCOPE
    can_repair, reason = validator.can_repair_component(u_boat, "Deck Gun")
    print(f"Deck Gun (Periscope): can_repair={can_repair}, reason='{reason}'")
    assert not can_repair, "Should block Deck Gun repair when submerged"
    assert "Surfaced" in reason, "Reason should mention Surfaced requirement"
    
    # Test at deeper depths
    u_boat.depth = Depth.MEDIUM
    can_repair, reason = validator.can_repair_component(u_boat, "Deck Gun")
    print(f"Deck Gun (Medium): can_repair={can_repair}, reason='{reason}'")
    assert not can_repair, "Should block at Medium depth"
    
    u_boat.depth = Depth.DEEP
    can_repair, reason = validator.can_repair_component(u_boat, "Deck Gun")
    print(f"Deck Gun (Deep): can_repair={can_repair}, reason='{reason}'")
    assert not can_repair, "Should block at Deep depth"
    
    print("✅ Deck Gun repair tests passed!\n")


def test_flak_gun_surface_only():
    """Test Flak Gun repair (surface only)."""
    print("\n=== Testing Flak Gun Repair (Surface Only) ===")
    
    validator = RepairValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        flak_gun_damaged=True,
        engineer_alive=True
    )
    
    # Can repair at surface
    can_repair, reason = validator.can_repair_component(u_boat, "Flak Gun")
    print(f"Flak Gun (Surfaced): can_repair={can_repair}")
    assert can_repair, "Should repair Flak Gun when surfaced"
    
    # Cannot repair submerged (even with Engineer)
    u_boat.depth = Depth.PERISCOPE
    can_repair, reason = validator.can_repair_component(u_boat, "Flak Gun")
    print(f"Flak Gun (Periscope): can_repair={can_repair}, reason='{reason}'")
    assert not can_repair, "Should block Flak Gun repair when submerged"
    assert "Surfaced" in reason, "Reason should mention Surfaced requirement"
    
    print("✅ Flak Gun repair tests passed!\n")


def test_torpedo_tubes_repair():
    """Test torpedo tube repair."""
    print("\n=== Testing Torpedo Tube Repair ===")
    
    validator = RepairValidator()
    
    # Damage some torpedo tubes (indices 0, 2, 4 = tubes 1, 3, 5)
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        torpedo_tubes=[TubeState.DAMAGED, TubeState.LOADED, TubeState.DAMAGED, TubeState.LOADED, TubeState.DAMAGED],  # Tubes 1, 3, 5 damaged
        engineer_alive=True
    )
    
    # Can repair at surface
    can_repair, reason = validator.can_repair_component(u_boat, "Torpedo Tubes")
    print(f"Torpedo Tubes (3 damaged, Surfaced): can_repair={can_repair}")
    assert can_repair, "Should repair torpedo tubes when damaged"
    
    # Get damaged tube info (should return 1-based numbers)
    damaged_tubes = validator.get_damaged_torpedo_tubes(u_boat)
    print(f"Damaged tubes: {damaged_tubes}")
    assert damaged_tubes == [1, 3, 5], "Should identify damaged tubes with 1-based numbering"
    
    # Get repair options
    repair_info = validator.get_torpedo_tube_repair_options(u_boat)
    print(f"Repair info: {repair_info}")
    assert "[1, 3, 5]" in repair_info, "Should show tube numbers 1, 3, 5"
    assert "3 total" in repair_info, "Should show 3 damaged tubes"
    assert "Front (1-4): [1, 3]" in repair_info, "Should show front tubes 1 and 3"
    assert "Rear (5): [5]" in repair_info, "Should show rear tube 5"
    assert "up to 2" in repair_info, "Should mention 2 tube limit"
    
    # All tubes loaded
    u_boat.torpedo_tubes = [TubeState.LOADED] * 5
    can_repair, reason = validator.can_repair_component(u_boat, "Torpedo Tubes")
    print(f"All tubes loaded: can_repair={can_repair}, reason='{reason}'")
    assert not can_repair, "Should not repair when all tubes loaded"
    
    repair_info = validator.get_torpedo_tube_repair_options(u_boat)
    print(f"All loaded info: {repair_info}")
    assert "none need repair" in repair_info.lower(), "Should indicate no repairs needed"
    
    # Can repair submerged with Engineer
    u_boat.torpedo_tubes[1] = TubeState.DAMAGED  # Damage tube 2 (index 1)
    u_boat.depth = Depth.MEDIUM
    can_repair, reason = validator.can_repair_component(u_boat, "Torpedo Tubes")
    print(f"Torpedo Tubes (Medium, Engineer alive): can_repair={can_repair}")
    assert can_repair, "Should repair submerged with Engineer"
    
    print("✅ Torpedo tube repair tests passed!\n")


def test_hull_damage_cannot_repair():
    """Test that hull damage cannot be repaired."""
    print("\n=== Testing Hull Damage (Cannot Repair) ===")
    
    validator = RepairValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        hull_damage=2
    )
    
    # Hull damage is not in repairable components
    can_repair, reason = validator.can_repair_component(u_boat, "Hull")
    print(f"Hull damage: can_repair={can_repair}, reason='{reason}'")
    assert not can_repair, "Should not allow hull damage repair"
    assert "cannot be repaired" in reason.lower(), "Reason should mention cannot repair"
    
    # Hull damage should not appear in repairable list
    repairable = validator.get_repairable_components(u_boat)
    print(f"Repairable components: {repairable}")
    assert "Hull" not in repairable, "Hull should not be in repairable list"
    
    print("✅ Hull damage tests passed!\n")


def test_get_repairable_components():
    """Test getting list of repairable components."""
    print("\n=== Testing Get Repairable Components ===")
    
    validator = RepairValidator()
    
    # All components damaged, surfaced
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        engine_damaged=True,
        deck_gun_damaged=True,
        flak_gun_damaged=True,
        torpedo_tubes=[TubeState.DAMAGED, TubeState.DAMAGED, TubeState.LOADED, TubeState.LOADED, TubeState.LOADED],
        engineer_alive=True
    )
    
    repairable = validator.get_repairable_components(u_boat)
    print(f"Surfaced, all damaged: {repairable}")
    assert len(repairable) == 4, "Should list all 4 component types"
    assert "Engine" in repairable
    assert "Deck Gun" in repairable
    assert "Flak Gun" in repairable
    assert "Torpedo Tubes" in repairable
    
    # Submerged, Engineer alive (only Engine and Torpedo Tubes)
    u_boat.depth = Depth.MEDIUM
    repairable = validator.get_repairable_components(u_boat)
    print(f"Medium, Engineer alive: {repairable}")
    assert "Engine" in repairable, "Engine should be repairable submerged"
    assert "Torpedo Tubes" in repairable, "Torpedo Tubes should be repairable submerged"
    assert "Deck Gun" not in repairable, "Deck Gun needs surface"
    assert "Flak Gun" not in repairable, "Flak Gun needs surface"
    
    # Submerged, Engineer KIA (none)
    u_boat.engineer_alive = False
    repairable = validator.get_repairable_components(u_boat)
    print(f"Medium, Engineer KIA: {repairable}")
    assert len(repairable) == 0, "No repairs possible submerged without Engineer"
    
    # Nothing damaged
    u_boat.depth = Depth.SURFACED
    u_boat.engine_damaged = False
    u_boat.deck_gun_damaged = False
    u_boat.flak_gun_damaged = False
    u_boat.torpedo_tubes = [TubeState.LOADED] * 5
    repairable = validator.get_repairable_components(u_boat)
    print(f"Nothing damaged: {repairable}")
    assert len(repairable) == 0, "Should return empty list when nothing damaged"
    
    print("✅ Get repairable components tests passed!\n")


def test_repair_info_formatting():
    """Test get_repair_info formatting."""
    print("\n=== Testing Repair Info Formatting ===")
    
    validator = RepairValidator()
    
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED,
        engine_damaged=True,
        engineer_alive=True
    )
    
    # Valid repair at surface
    info = validator.get_repair_info(u_boat, "Engine")
    print(f"Engine (Surfaced): {info}")
    assert "Engine" in info
    assert "DAMAGED" in info
    assert "2 AP" in info
    assert "✓" in info
    
    # Invalid repair (not damaged)
    u_boat.engine_damaged = False
    info = validator.get_repair_info(u_boat, "Engine")
    print(f"Engine (not damaged): {info}")
    assert "OK" in info
    assert "✗" in info
    assert "not damaged" in info.lower()
    
    # Surface-only component
    u_boat.deck_gun_damaged = True
    info = validator.get_repair_info(u_boat, "Deck Gun")
    print(f"Deck Gun (Surfaced): {info}")
    assert "Surfaced Only" in info
    assert "✓" in info
    
    # Surface-only component submerged
    u_boat.depth = Depth.PERISCOPE
    info = validator.get_repair_info(u_boat, "Deck Gun")
    print(f"Deck Gun (Periscope): {info}")
    assert "Surfaced Only" in info
    assert "✗" in info
    
    # Submerged with Engineer
    u_boat.engine_damaged = True
    u_boat.depth = Depth.MEDIUM
    info = validator.get_repair_info(u_boat, "Engine")
    print(f"Engine (Medium, Engineer alive): {info}")
    assert "Engineer: Alive" in info
    assert "4 AP" in info
    assert "✓" in info
    
    # Submerged without Engineer
    u_boat.engineer_alive = False
    info = validator.get_repair_info(u_boat, "Engine")
    print(f"Engine (Medium, Engineer KIA): {info}")
    assert "Engineer: KIA" in info or "Engineer KIA" in info
    assert "✗" in info
    
    print("✅ Repair info formatting tests passed!\n")


def test_ap_costs():
    """Test AP cost calculation."""
    print("\n=== Testing AP Costs ===")
    
    validator = RepairValidator()
    
    # Surfaced: always 2 AP
    for component in ["Engine", "Torpedo Tubes", "Deck Gun", "Flak Gun"]:
        cost = validator.get_repair_ap_cost(component, Depth.SURFACED, engineer_alive=True)
        print(f"{component} (Surfaced): {cost} AP")
        assert cost == 2, f"{component} should cost 2 AP when surfaced"
    
    # Submerged with Engineer: 4 AP
    for depth in [Depth.PERISCOPE, Depth.MEDIUM, Depth.DEEP]:
        cost = validator.get_repair_ap_cost("Engine", depth, engineer_alive=True)
        print(f"Engine ({depth.name}, Engineer alive): {cost} AP")
        assert cost == 4, f"Should cost 4 AP at {depth.name} with Engineer"
    
    # Submerged without Engineer: 0 AP (not possible)
    for depth in [Depth.PERISCOPE, Depth.MEDIUM, Depth.DEEP]:
        cost = validator.get_repair_ap_cost("Engine", depth, engineer_alive=False)
        print(f"Engine ({depth.name}, Engineer KIA): {cost} AP")
        assert cost == 0, f"Should return 0 AP (impossible) at {depth.name} without Engineer"
    
    # Invalid component: 0 AP
    cost = validator.get_repair_ap_cost("Invalid", Depth.SURFACED, engineer_alive=True)
    print(f"Invalid component: {cost} AP")
    assert cost == 0, "Invalid component should return 0 AP"
    
    print("✅ AP cost tests passed!\n")


def test_complex_scenarios():
    """Test complex repair scenarios."""
    print("\n=== Testing Complex Scenarios ===")
    
    validator = RepairValidator()
    
    # Scenario 1: Multiple damage, submerged, Engineer alive
    print("\nScenario 1: Multiple damage, submerged, Engineer alive")
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.MEDIUM,
        engine_damaged=True,
        deck_gun_damaged=True,
        flak_gun_damaged=True,
        torpedo_tubes=[TubeState.DAMAGED, TubeState.LOADED, TubeState.DAMAGED, TubeState.LOADED, TubeState.LOADED],
        engineer_alive=True
    )
    
    repairable = validator.get_repairable_components(u_boat)
    print(f"  Repairable: {repairable}")
    assert "Engine" in repairable, "Engine should be repairable"
    assert "Torpedo Tubes" in repairable, "Torpedo Tubes should be repairable"
    assert "Deck Gun" not in repairable, "Deck Gun needs surface"
    assert "Flak Gun" not in repairable, "Flak Gun needs surface"
    
    # Scenario 2: Multiple damage, surfaced, Engineer KIA
    print("\nScenario 2: Multiple damage, surfaced, Engineer KIA")
    u_boat.depth = Depth.SURFACED
    u_boat.engineer_alive = False
    
    repairable = validator.get_repairable_components(u_boat)
    print(f"  Repairable: {repairable}")
    assert len(repairable) == 4, "All damaged components repairable at surface"
    
    # Scenario 3: Heavily damaged at deep depth
    print("\nScenario 3: Heavily damaged, deep, no Engineer")
    u_boat.depth = Depth.DEEP
    u_boat.hull_damage = 3
    
    repairable = validator.get_repairable_components(u_boat)
    print(f"  Repairable: {repairable}")
    assert len(repairable) == 0, "Nothing repairable deep without Engineer"
    assert u_boat.hull_damage == 3, "Hull damage should remain (cannot repair)"
    
    print("✅ Complex scenarios tests passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2.6 Tests - RepairValidator")
    print("=" * 60)
    
    try:
        test_engine_repair_surfaced()
        test_engine_repair_submerged_with_engineer()
        test_engine_repair_submerged_no_engineer()
        test_deck_gun_surface_only()
        test_flak_gun_surface_only()
        test_torpedo_tubes_repair()
        test_hull_damage_cannot_repair()
        test_get_repairable_components()
        test_repair_info_formatting()
        test_ap_costs()
        test_complex_scenarios()
        
        print("=" * 60)
        print("✅ ALL REPAIR VALIDATOR TESTS PASSED!")
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
