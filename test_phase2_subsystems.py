"""
Quick tests for Phase 2 subsystems.

Run with: python -m pytest test_phase2_subsystems.py -v
Or just: python test_phase2_subsystems.py
"""

import sys
sys.path.insert(0, '.')

from core.dice import DiceRoller
from core.action_costs import ActionCostLookup
from core.models import Depth
from missions.mission_rules_loader import load_mission_rules


def test_dice_roller():
    """Test DiceRoller with deterministic seed."""
    print("\n=== Testing DiceRoller ===")
    
    # Create roller with seed for reproducibility
    dice = DiceRoller(seed=42)
    
    # Test 1d6
    roll = dice.roll_1d6("Test single die")
    print(f"1d6: {roll}")
    assert 1 <= roll <= 6, "1d6 out of range"
    
    # Test 2d6
    total = dice.roll_2d6("Test two dice")
    print(f"2d6: {total}")
    assert 2 <= total <= 12, "2d6 out of range"
    
    # Test roll_highest (AP rolling)
    highest, rolls = dice.roll_highest(3, context="Action Points")
    print(f"3d6 take highest: {rolls} → {highest}")
    assert highest == max(rolls), "Highest not correct"
    assert len(rolls) == 3, "Should roll 3 dice"
    
    # Test roll history
    history = dice.get_history_summary()
    print(f"\nRoll History ({len(history)} rolls):")
    for entry in history:
        print(f"  {entry}")
    
    assert len(history) == 3, "Should have 3 rolls logged"
    
    print("✅ DiceRoller tests passed!\n")


def test_action_cost_lookup():
    """Test ActionCostLookup reads from JSON correctly."""
    print("\n=== Testing ActionCostLookup ===")
    
    # Load mission rules
    rules = load_mission_rules(1)
    costs = ActionCostLookup(rules)
    
    # Test MOVE costs at all depths
    print("\nMOVE costs:")
    for depth in [Depth.SURFACED, Depth.PERISCOPE, Depth.MEDIUM, Depth.DEEP]:
        cost = costs.get_cost("MOVE", depth)
        print(f"  {depth.name}: {cost} AP")
        assert cost is not None, f"MOVE should have cost at {depth.name}"
    
    # Verify expected MOVE costs
    assert costs.get_cost("MOVE", Depth.SURFACED) == 1
    assert costs.get_cost("MOVE", Depth.PERISCOPE) == 2
    assert costs.get_cost("MOVE", Depth.MEDIUM) == 3
    assert costs.get_cost("MOVE", Depth.DEEP) == 3
    
    # Test TURN costs
    print("\nTURN costs:")
    for depth in [Depth.SURFACED, Depth.PERISCOPE, Depth.MEDIUM, Depth.DEEP]:
        cost = costs.get_cost("TURN", depth)
        print(f"  {depth.name}: {cost} AP")
    
    assert costs.get_cost("TURN", Depth.SURFACED) == 1
    assert costs.get_cost("TURN", Depth.PERISCOPE) == 1
    assert costs.get_cost("TURN", Depth.MEDIUM) == 2
    assert costs.get_cost("TURN", Depth.DEEP) == 3
    
    # Test FIRE DECK GUN (only at surface)
    print("\nFIRE DECK GUN availability:")
    for depth in [Depth.SURFACED, Depth.PERISCOPE, Depth.MEDIUM, Depth.DEEP]:
        cost = costs.get_cost("FIRE DECK GUN", depth)
        available = costs.is_available_at_depth("FIRE DECK GUN", depth)
        print(f"  {depth.name}: {cost} AP (available: {available})")
    
    assert costs.get_cost("FIRE DECK GUN", Depth.SURFACED) == 2
    assert costs.get_cost("FIRE DECK GUN", Depth.PERISCOPE) is None
    assert not costs.is_available_at_depth("FIRE DECK GUN", Depth.MEDIUM)
    
    # Test get_all_costs_at_depth
    print("\nAll actions at SURFACED:")
    surfaced_actions = costs.get_all_costs_at_depth(Depth.SURFACED)
    for action, cost in sorted(surfaced_actions.items()):
        print(f"  {action}: {cost} AP")
    
    assert len(surfaced_actions) == 7, "Should have 7 actions at surface"
    
    # Test format_action_summary
    print("\nFormatted summary at PERISCOPE:")
    summary = costs.format_action_summary(Depth.PERISCOPE)
    for line in summary:
        print(f"  {line}")
    
    # Test restrictions
    move_restrictions = costs.get_restrictions("MOVE")
    print(f"\nMOVE restrictions ({len(move_restrictions)}):")
    for restriction in move_restrictions:
        print(f"  - {restriction}")
    
    assert len(move_restrictions) == 3, "MOVE should have 3 restrictions"
    
    print("\n✅ ActionCostLookup tests passed!\n")


def test_integration():
    """Test TurnManager uses DiceRoller correctly."""
    print("\n=== Testing Integration ===")
    
    from core.turn_manager import TurnManager
    from core.models import UBoat, Facing, HexCoord
    
    # Load rules
    rules = load_mission_rules(1)
    
    # Create dice roller with seed
    dice = DiceRoller(seed=123)
    
    # Create turn manager with shared dice roller
    turn_mgr = TurnManager(rules, dice_roller=dice)
    
    # Create test U-boat
    u_boat = UBoat(
        position=HexCoord(5, 5),
        facing=Facing.NORTH,
        depth=Depth.SURFACED
    )
    
    # Roll AP
    ap = turn_mgr.start_new_turn(u_boat)
    print(f"Turn {turn_mgr.turn_number}: Rolled {ap} AP")
    
    assert 1 <= ap <= 7, "AP should be in valid range (1-7)"
    assert turn_mgr.ap_tracker is not None, "AP tracker should be initialized"
    
    # Check dice history
    history = dice.get_history_summary()
    print(f"\nDice rolls during turn start:")
    for entry in history:
        print(f"  {entry}")
    
    assert len(history) > 0, "Should have logged dice rolls"
    
    print("\n✅ Integration tests passed!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 2 Quick Tests - DiceRoller & ActionCostLookup")
    print("=" * 60)
    
    try:
        test_dice_roller()
        test_action_cost_lookup()
        test_integration()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
