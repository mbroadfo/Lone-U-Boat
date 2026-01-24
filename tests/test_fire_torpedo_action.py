"""
Tests for FireTorpedoAction to ensure it uses correct hit values from CombatResolver.

This test ensures the action's get_torpedo_hit_target() method uses the
combat resolver's table loaded from JSON, not hardcoded values.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.actions.fire_torpedo_action import FireTorpedoAction
from core.torpedo_validator import TorpedoValidator
from core.los import LOSCalculator
from core.combat_resolver import CombatResolver
from core.combat_resolver import CombatResolver
from core.dice import DiceRoller
from core.action_costs import ActionCostLookup
from missions.mission_rules_loader import load_mission_rules
from core.models import Facing


def test_torpedo_action_uses_combat_resolver_values():
    """
    Test that FireTorpedoAction.get_torpedo_hit_target() uses values from
    CombatResolver's table (loaded from JSON), not hardcoded values.
    
    This prevents regression of the bug where the action had hardcoded wrong values.
    """
    print("\n=== Testing FireTorpedoAction Hit Target Values ===")
    
    # Load mission rules (this loads correct values from JSON)
    mission_rules = load_mission_rules(1)
    
    # Create components
    dice = DiceRoller()
    combat_resolver = CombatResolver(dice, mission_rules)
    validator = TorpedoValidator()
    los_calculator = LOSCalculator(land_hexes=set())  # No land hexes for this test
    cost_lookup = ActionCostLookup(mission_rules)
    
    # Create action
    action = FireTorpedoAction(
        tube_indices=[0],
        fire_direction=Facing.NORTH,
        cost_lookup=cost_lookup,
        validator=validator,
        los_calculator=los_calculator,
        combat_resolver=combat_resolver
    )
    
    # Test Range 1-2: Side 3+, Front/Rear 4+
    assert action.get_torpedo_hit_target(1, "side") == 3, \
        "Range 1 side should need 3+ (from JSON)"
    assert action.get_torpedo_hit_target(2, "side") == 3, \
        "Range 2 side should need 3+ (from JSON)"
    assert action.get_torpedo_hit_target(1, "front_rear") == 4, \
        "Range 1 front/rear should need 4+ (from JSON)"
    assert action.get_torpedo_hit_target(2, "front_rear") == 4, \
        "Range 2 front/rear should need 4+ (from JSON)"
    print("✓ Range 1-2 correct")
    
    # Test Range 3-4: Side 4+, Front/Rear 5+
    assert action.get_torpedo_hit_target(3, "side") == 4, \
        "Range 3 side should need 4+ (from JSON)"
    assert action.get_torpedo_hit_target(4, "side") == 4, \
        "Range 4 side should need 4+ (from JSON)"
    assert action.get_torpedo_hit_target(3, "front_rear") == 5, \
        "Range 3 front/rear should need 5+ (from JSON)"
    assert action.get_torpedo_hit_target(4, "front_rear") == 5, \
        "Range 4 front/rear should need 5+ (from JSON)"
    print("✓ Range 3-4 correct")
    
    # Test Range 5-6: Side 5+, Front/Rear 6+
    assert action.get_torpedo_hit_target(5, "side") == 5, \
        "Range 5 side should need 5+ (from JSON)"
    assert action.get_torpedo_hit_target(6, "side") == 5, \
        "Range 6 side should need 5+ (from JSON)"
    assert action.get_torpedo_hit_target(5, "front_rear") == 6, \
        "Range 5 front/rear should need 6+ (from JSON)"
    assert action.get_torpedo_hit_target(6, "front_rear") == 6, \
        "Range 6 front/rear should need 6+ (from JSON)"
    print("✓ Range 5-6 correct")
    
    # Test Range 7-9: Side 6+, Front/Rear 6+
    assert action.get_torpedo_hit_target(7, "side") == 6, \
        "Range 7 side should need 6+ (from JSON)"
    assert action.get_torpedo_hit_target(9, "side") == 6, \
        "Range 9 side should need 6+ (from JSON)"
    assert action.get_torpedo_hit_target(7, "front_rear") == 6, \
        "Range 7 front/rear should need 6+ (from JSON)"
    assert action.get_torpedo_hit_target(9, "front_rear") == 6, \
        "Range 9 front/rear should need 6+ (from JSON)"
    print("✓ Range 7-9 correct")
    
    print("\n✅ FireTorpedoAction uses correct hit values from CombatResolver!\n")


if __name__ == '__main__':
    test_torpedo_action_uses_combat_resolver_values()
